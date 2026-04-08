"""Server-Side Session Manager — Redis-backed httpOnly cookie sessions.

Enterprise BFF (Backend-for-Frontend) pattern:
- Browser stores NOTHING (no tokens, no sessionStorage, no localStorage)
- Auth via httpOnly cookie containing opaque session_id
- Session data (user, tenants, preferences) stored in Redis
- Cookie: HttpOnly + Secure + SameSite=Lax

This module provides create/get/update/delete/refresh for sessions.
Used by auth.py (login/logout) and all API endpoints (via get_session dependency).
"""
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.redis_state import set_state, get_state, delete_state

logger = logging.getLogger(__name__)

# Session configuration
SESSION_TTL = getattr(settings, 'SESSION_TTL_HOURS', 24) * 3600  # Default 24 hours
COOKIE_NAME = "kavachiq_session"
COOKIE_DOMAIN = getattr(settings, 'COOKIE_DOMAIN', None)  # None = same origin
COOKIE_SECURE = not settings.DEBUG  # Secure=True in production (HTTPS only)
COOKIE_SAMESITE = "lax"  # Allows OAuth redirects back to our domain


async def create_session(
    user_id: int,
    username: str,
    role: str,
    tenant_ids: list[int],
    preferences: dict = None,
    extra: dict = None,
) -> str:
    """Create a new server-side session in Redis.

    Returns the opaque session_id to be set as httpOnly cookie.
    """
    session_id = secrets.token_urlsafe(32)

    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "username": username,
        "role": role,
        "tenant_ids": tenant_ids,
        "preferences": preferences or {},
        "is_platform_admin": username == "admin",
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
    }
    if extra:
        session_data.update(extra)

    await set_state(f"session:{session_id}", session_data, ttl_seconds=SESSION_TTL)
    logger.info(f"Session created: user={username} session={session_id[:8]}...")
    return session_id


async def get_session_data(session_id: str) -> Optional[dict]:
    """Get session data from Redis. Returns None if expired or not found."""
    if not session_id:
        return None
    data = await get_state(f"session:{session_id}")
    if data:
        # Update last_activity (touch session)
        data["last_activity"] = datetime.utcnow().isoformat()
        await set_state(f"session:{session_id}", data, ttl_seconds=SESSION_TTL)
    return data


async def update_session(session_id: str, updates: dict):
    """Update specific fields in an existing session."""
    data = await get_state(f"session:{session_id}")
    if not data:
        return False
    data.update(updates)
    data["last_activity"] = datetime.utcnow().isoformat()
    await set_state(f"session:{session_id}", data, ttl_seconds=SESSION_TTL)
    return True


async def destroy_session(session_id: str):
    """Delete session from Redis. Called on logout."""
    if session_id:
        await delete_state(f"session:{session_id}")
        logger.info(f"Session destroyed: {session_id[:8]}...")


def set_session_cookie(response: Response, session_id: str):
    """Set the httpOnly session cookie on a response."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_TTL,
        path="/",
        domain=COOKIE_DOMAIN,
    )


def clear_session_cookie(response: Response):
    """Delete the session cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        domain=COOKIE_DOMAIN,
    )


def get_session_id_from_request(request: Request) -> Optional[str]:
    """Extract session_id from cookie or Authorization header (backward compat)."""
    # Priority 1: httpOnly cookie (BFF pattern)
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        return session_id
    return None


async def get_session_or_401(request: Request) -> dict:
    """FastAPI dependency: get session from cookie or raise 401.

    Drop-in replacement for get_current_user where session context is needed.
    """
    session_id = get_session_id_from_request(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await get_session_data(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    return session
