"""Authentication API routes."""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    verify_refresh_token, validate_password, get_current_user
)

logger = logging.getLogger(__name__)
from app.config import settings
from app.errors import (
    KavachIQError, AUTH_INVALID_CREDENTIALS, AUTH_ACCOUNT_DISABLED,
    AUTH_TOKEN_EXPIRED, VALIDATION_INVALID_INPUT, VALIDATION_DUPLICATE,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = None
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None
    role: str
    is_active: int

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = None
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=UserResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Validate password
    is_valid, error_msg = validate_password(req.password)
    if not is_valid:
        raise KavachIQError(VALIDATION_INVALID_INPUT, detail=error_msg)

    # Check existing
    result = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if result.scalar_one_or_none():
        raise KavachIQError(VALIDATION_DUPLICATE, detail="Username or email already exists")

    import secrets
    verification_token = secrets.token_urlsafe(32)

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        email_verified=0,
        email_verification_token=verification_token,
    )
    db.add(user)
    await db.flush()

    # Send welcome + verification email (non-blocking, don't fail registration)
    try:
        from app.services.email_service import email_service
        await email_service.send_welcome(user.email, user.full_name or user.username)
        await email_service.send_email_verification(user.email, verification_token)
    except Exception as e:
        logger.warning(f"Failed to send registration emails to {user.email}: {e}")

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and get JWT token. Accepts username or email."""
    from sqlalchemy import or_
    result = await db.execute(
        select(User).where(
            or_(User.username == form_data.username, User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise KavachIQError(AUTH_INVALID_CREDENTIALS)

    if not user.is_active:
        raise KavachIQError(AUTH_ACCOUNT_DISABLED)

    token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh = create_refresh_token(data={"sub": user.username, "role": user.role.value})

    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange refresh token for new access + refresh tokens."""
    username = verify_refresh_token(req.refresh_token)
    if not username:
        raise KavachIQError(AUTH_TOKEN_EXPIRED, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise KavachIQError(AUTH_ACCOUNT_DISABLED, detail="User not found or disabled")

    new_access = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh = create_refresh_token(data={"sub": user.username, "role": user.role.value})

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserResponse(
            id=user.id, username=user.username, email=user.email,
            full_name=user.full_name, role=user.role.value, is_active=user.is_active,
        ),
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user info + tenant context + onboarding status.

    Enterprise pattern: server is the source of truth for routing.
    Frontend uses this response to decide: dashboard vs onboard vs demo.
    No sessionStorage hacks needed.
    """
    from app.services.auth import get_user_tenant_ids

    tenant_ids = await get_user_tenant_ids(db, current_user)
    has_tenants = len(tenant_ids) > 0

    # Server decides the routing — client just follows
    if has_tenants:
        onboarding_status = "complete"
        redirect = None
    elif current_user.username == "demo":
        onboarding_status = "demo"
        redirect = "/onboard/demo"
    else:
        onboarding_status = "pending"
        redirect = "/onboard"

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_platform_admin": current_user.username == "admin",
        "has_tenants": has_tenants,
        "tenant_count": len(tenant_ids),
        "onboarding_status": onboarding_status,
        "redirect": redirect,
    }


@router.get("/session")
async def get_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete user session — ONE call, ALL state.

    Enterprise pattern: server owns all state. Browser stores only JWT.
    Frontend calls this once on app load and renders based on response.
    No localStorage, no sessionStorage (except JWT token).

    Returns: user info, routing decision, active tenant, all preferences,
    and feature flags for the active tenant.
    """
    from app.services.auth import get_user_tenant_ids
    from app.models.user_preference import UserPreference
    from app.models.tenant import Tenant

    # 1. Get user's tenants
    tenant_ids = await get_user_tenant_ids(db, current_user)
    has_tenants = len(tenant_ids) > 0

    # 2. Routing decision (server is truth)
    if has_tenants:
        onboarding_status = "complete"
        redirect = None
    elif current_user.username == "demo":
        onboarding_status = "demo"
        redirect = "/onboard/demo"
    else:
        onboarding_status = "pending"
        redirect = "/onboard"

    # 3. Load all preferences
    pref_result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    prefs = {p.key: p.value for p in pref_result.scalars().all()}

    # 4. Resolve active tenant
    selected_tenant_id = prefs.get("selected_tenant")
    active_tenant = None
    if selected_tenant_id and int(selected_tenant_id) in tenant_ids:
        t = await db.get(Tenant, int(selected_tenant_id))
        if t:
            active_tenant = {"id": t.id, "name": t.name, "ms_tenant_id": t.ms_tenant_id}
    elif tenant_ids:
        # Default to first tenant
        t = await db.get(Tenant, tenant_ids[0])
        if t:
            active_tenant = {"id": t.id, "name": t.name, "ms_tenant_id": t.ms_tenant_id}

    # 5. Feature flags for active tenant tier
    from app.services.feature_flags import feature_flags
    features = {}
    for category in ["workloads", "intelligence", "recovery", "compliance"]:
        features[category] = [f for f in feature_flags.tier_config.get(category, [])
                              if feature_flags.is_enabled(f)]

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "is_platform_admin": current_user.username == "admin",
        },
        "routing": {
            "onboarding_status": onboarding_status,
            "redirect": redirect,
        },
        "tenant": active_tenant,
        "tenant_count": len(tenant_ids),
        "preferences": {
            "theme": prefs.get("theme", "dark"),
            "selected_tenant": prefs.get("selected_tenant"),
            "tour_completed": prefs.get("tour_completed") == "true",
            "checklist_dismissed": prefs.get("checklist_dismissed") == "true",
            "recent_commands": prefs.get("recent_commands", "[]"),
        },
        "feature_flags": features,
    }


class PreferenceValue(BaseModel):
    value: str = ""


@router.put("/preferences/{key}")
async def set_preference(
    key: str,
    body: PreferenceValue = PreferenceValue(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a user preference. Replaces localStorage/sessionStorage.

    Preferences are stored in DB and follow the user across devices.
    Frontend calls this when user changes theme, switches tenant,
    dismisses tour, etc.
    """
    from app.models.user_preference import UserPreference, PREF_KEYS

    # Validate key (optional — allow any key for extensibility)
    value = body.value
    if len(key) > 100:
        raise HTTPException(400, detail="Preference key too long (max 100 chars)")

    # Upsert: insert or update
    existing = await db.execute(
        select(UserPreference).where(
            UserPreference.user_id == current_user.id,
            UserPreference.key == key,
        )
    )
    pref = existing.scalar_one_or_none()
    if pref:
        pref.value = value
    else:
        pref = UserPreference(user_id=current_user.id, key=key, value=value)
        db.add(pref)

    await db.commit()
    return {"key": key, "value": value}


@router.get("/preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all preferences for the current user."""
    from app.models.user_preference import UserPreference

    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    return {p.key: p.value for p in result.scalars().all()}


# ── Password Reset + Email Verification ──


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send password reset email. Always returns 200 (don't reveal if email exists)."""
    import secrets
    from datetime import timedelta
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if user:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()
        # Send email
        try:
            from app.services.email_service import email_service
            await email_service.send_password_reset(user.email, token)
        except Exception as e:
            logger.warning(f"Failed to send reset email: {e}")
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using token from email."""
    result = await db.execute(
        select(User).where(User.password_reset_token == req.token)
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        raise HTTPException(400, detail="Invalid or expired reset token")

    is_valid, error = validate_password(req.new_password)
    if not is_valid:
        raise HTTPException(400, detail=error)

    user.password_hash = hash_password(req.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()
    return {"message": "Password reset successfully. You can now log in."}


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify email address using token from email."""
    result = await db.execute(
        select(User).where(User.email_verification_token == req.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(400, detail="Invalid verification token")

    user.email_verified = 1
    user.email_verification_token = None
    await db.commit()
    return {"message": "Email verified successfully."}


# ── SSO / OIDC Endpoints ──

_sso_flows: dict = {}  # In-memory flow cache (use Redis in production)


@router.get("/sso/config")
async def sso_config():
    """Check if SSO is enabled and available."""
    from app.services.oidc_auth import oidc_service
    return {"enabled": oidc_service.enabled, "provider": "entra_id" if oidc_service.enabled else None}


@router.get("/sso/login")
async def sso_login():
    """Start SSO login flow — returns Entra ID authorization URL."""
    from app.services.oidc_auth import oidc_service

    if not oidc_service.enabled:
        raise HTTPException(status_code=400, detail="SSO is not enabled. Set SSO_ENABLED=true and configure SSO_* settings.")

    import secrets
    state = secrets.token_urlsafe(32)
    result = oidc_service.get_authorization_url(state=state)

    # Store flow for callback validation
    _sso_flows[state] = result["flow"]

    return {"auth_url": result["auth_url"], "state": state}


@router.post("/sso/callback")
async def sso_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle SSO callback — exchange code for token, provision user, return JWT."""
    from app.services.oidc_auth import oidc_service

    flow = _sso_flows.pop(state, None)
    if not flow:
        raise HTTPException(status_code=400, detail="Invalid or expired SSO state")

    try:
        token_result = await oidc_service.exchange_code(code, flow)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    claims = oidc_service.get_user_info(token_result["id_token_claims"])
    if not claims.get("subject_id"):
        raise HTTPException(status_code=400, detail="Could not extract user identity from SSO token")

    # Provision or lookup user
    user = await oidc_service.provision_user(claims, db)
    await db.commit()

    # Issue JWT
    token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


# ── GDPR: Data Export + Account Deletion ──


@router.post("/export-my-data")
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all user data as JSON (GDPR Article 20 — right to data portability)."""
    from app.models.tenant import Tenant

    profile = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "email_verified": bool(getattr(current_user, 'email_verified', 0)),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }

    tenants_result = await db.execute(select(Tenant))
    tenants = [{"id": t.id, "name": t.name, "status": t.status.value} for t in tenants_result.scalars().all()]

    return {
        "export_date": datetime.utcnow().isoformat(),
        "user": profile,
        "tenants": tenants,
        "note": "For full backup data, use the Exchange/Entra ID browse and export APIs.",
    }


class DeleteAccountRequest(BaseModel):
    confirm_username: str


@router.delete("/account")
async def delete_account(
    req: DeleteAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete user account (GDPR Article 17). Soft-deletes immediately, purge after 7 days."""
    if req.confirm_username != current_user.username:
        raise HTTPException(400, detail="Username confirmation doesn't match.")

    current_user.is_active = 0
    current_user.updated_at = datetime.utcnow()
    await db.commit()

    try:
        from app.services.email_service import email_service
        await email_service.provider.send(
            to=current_user.email,
            subject="Account Deleted — KavachIQ",
            html=f"<p>Your KavachIQ account ({current_user.username}) has been deactivated. Data purge in 7 days.</p>",
        )
    except Exception:
        pass

    return {"message": "Account deactivated. Data purge in 7 days.", "grace_period_days": 7}
