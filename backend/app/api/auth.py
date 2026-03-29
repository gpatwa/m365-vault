"""Authentication API routes."""
from datetime import timedelta

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
from app.config import settings
from app.errors import (
    ShieldioError, AUTH_INVALID_CREDENTIALS, AUTH_ACCOUNT_DISABLED,
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
        raise ShieldioError(VALIDATION_INVALID_INPUT, detail=error_msg)

    # Check existing
    result = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if result.scalar_one_or_none():
        raise ShieldioError(VALIDATION_DUPLICATE, detail="Username or email already exists")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
    )
    db.add(user)
    await db.flush()
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
        raise ShieldioError(AUTH_INVALID_CREDENTIALS)

    if not user.is_active:
        raise ShieldioError(AUTH_ACCOUNT_DISABLED)

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
        raise ShieldioError(AUTH_TOKEN_EXPIRED, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ShieldioError(AUTH_ACCOUNT_DISABLED, detail="User not found or disabled")

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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


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
