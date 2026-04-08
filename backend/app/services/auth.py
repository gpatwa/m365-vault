"""Authentication and authorization service."""
from datetime import datetime, timedelta
from typing import Optional

import hashlib
import os
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password against policy. Returns (is_valid, error_message)."""
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, ""


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256 (no native dependency, works everywhere)."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260000)
    return f"pbkdf2:sha256:260000${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against PBKDF2-SHA256 or legacy bcrypt hash."""
    if hashed_password.startswith("pbkdf2:"):
        # New PBKDF2 format: pbkdf2:sha256:iterations$salt_hex$key_hex
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        header = parts[0]  # pbkdf2:sha256:260000
        salt = bytes.fromhex(parts[1])
        stored_key = parts[2]
        iterations = int(header.split(":")[-1])
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return key.hex() == stored_key
    elif hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        # Legacy bcrypt hash — try bcrypt, fall back to passlib
        try:
            import bcrypt as _bcrypt
            return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            try:
                from passlib.hash import bcrypt as _pbcrypt
                return _pbcrypt.verify(plain_password, hashed_password)
            except Exception:
                return False
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_refresh_token(token: str) -> Optional[str]:
    """Verify refresh token, return username if valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user — dual-mode (cookie + JWT).

    Enterprise BFF pattern: checks httpOnly session cookie first,
    falls back to Authorization: Bearer JWT for API clients.

    Priority:
    1. httpOnly cookie (kavachiq_session) → Redis session → user
    2. Authorization: Bearer JWT → decode → user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Priority 1: httpOnly cookie session (BFF pattern)
    from app.services.session import get_session_data, COOKIE_NAME
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        session = await get_session_data(session_id)
        if session and session.get("user_id"):
            result = await db.execute(select(User).where(User.id == session["user_id"]))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                # Attach session to request for downstream use
                request.state.session = session
                return user

    # Priority 2: JWT Bearer token (backward compat for API clients)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user

    raise credentials_exception


def require_role(*roles: UserRole):
    """Dependency factory: require specific user roles."""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in roles)}",
            )
        return current_user
    return role_checker


# Pre-built permission dependencies for least-privilege access
# Backup operations: read-only access — ADMIN and OPERATOR can trigger
require_backup_permission = require_role(UserRole.ADMIN, UserRole.OPERATOR)

# Restore/recovery operations: write access — ADMIN and RESTORE_OPERATOR
require_restore_permission = require_role(UserRole.ADMIN, UserRole.RESTORE_OPERATOR)

# MSP operations: dashboard, billing, branding — ADMIN and MSP_ADMIN
require_msp_permission = require_role(UserRole.ADMIN, UserRole.MSP_ADMIN)


# ── Tenant-scoped access control ──────────────────────────────────

async def get_user_tenant_ids(db: AsyncSession, user: User) -> list[int]:
    """Return the list of tenant IDs this user can access.

    Uses the user_tenants membership table. If a user has no explicit
    memberships (legacy/migration), falls back to showing all tenants
    for ADMIN users and no tenants for others.
    """
    from app.models.user_tenant import UserTenant

    result = await db.execute(
        select(UserTenant.tenant_id).where(UserTenant.user_id == user.id)
    )
    tenant_ids = [r[0] for r in result.all()]

    # Fallback for legacy: platform superadmin (username=admin) sees all tenants
    # if they have no explicit memberships. Other ADMIN users must be assigned.
    if not tenant_ids and user.role == UserRole.ADMIN and user.username == "admin":
        from app.models.tenant import Tenant
        result = await db.execute(select(Tenant.id))
        tenant_ids = [r[0] for r in result.all()]

    return tenant_ids


async def require_tenant_access(
    db: AsyncSession,
    tenant_id: int,
    user: User,
) -> None:
    """Raise 403 if user cannot access this tenant.

    Call this in any endpoint that accepts tenant_id as a parameter.
    """
    allowed = await get_user_tenant_ids(db, user)
    if tenant_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have access to this tenant",
        )


def require_tenant_access_dep(tenant_id_param: str = "tenant_id"):
    """FastAPI dependency factory for tenant access validation.

    Usage in any endpoint:
        @router.get("/data")
        async def get_data(
            tenant_id: int = Query(...),
            _ta = Depends(require_tenant_access_dep()),
            db = Depends(get_db),
            current_user = Depends(get_current_user),
        ):

    Validates that the current user can access the tenant_id in the request.
    Skips validation if tenant_id is None (optional parameter not provided).
    """
    async def _check(
        request: "Request",
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        from starlette.requests import Request as _Req
        # Extract tenant_id from query params or path params
        tid = request.query_params.get(tenant_id_param) or request.path_params.get(tenant_id_param)
        if tid:
            try:
                await require_tenant_access(db, int(tid), current_user)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: you do not have access to this tenant",
                )
    return _check


async def resolve_tenant_filter(
    db: AsyncSession,
    user: User,
    tenant_id: int = None,
) -> list[int]:
    """Resolve which tenant IDs to filter by.

    Use this in EVERY endpoint with optional tenant_id to prevent data leakage.
    Returns list of allowed tenant IDs for the query WHERE clause.

    - If tenant_id provided: validates access, returns [tenant_id]
    - If not provided: returns user's assigned tenant IDs
    - If user has no tenants: returns [-1] (matches nothing)
    """
    if tenant_id:
        await require_tenant_access(db, tenant_id, user)
        return [tenant_id]

    allowed = await get_user_tenant_ids(db, user)
    return allowed if allowed else [-1]


async def assign_user_to_tenant(
    db: AsyncSession,
    user_id: int,
    tenant_id: int,
    role: str = "member",
    is_default: bool = False,
) -> None:
    """Assign a user to a tenant. Idempotent — skips if already assigned."""
    from app.models.user_tenant import UserTenant

    existing = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
    )
    if existing.scalar_one_or_none():
        return  # Already assigned

    db.add(UserTenant(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        is_default=1 if is_default else 0,
    ))
    await db.flush()
