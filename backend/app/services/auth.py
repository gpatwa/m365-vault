"""Authentication and authorization service."""
from datetime import datetime, timedelta
from typing import Optional

import hashlib
import os
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
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
        # Legacy bcrypt hash — use bcrypt library
        try:
            import bcrypt
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
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
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


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
