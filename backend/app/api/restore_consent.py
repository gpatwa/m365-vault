"""Delegated Restore Consent — admin authenticates to grant write permissions.

Enterprise pattern: all state in Redis (survives pod restart, works cross-pod).
Tokens stored with TTL — auto-expire, no cleanup needed.
Zero standing write access — tokens discarded after restore completes.

Flow:
1. Admin clicks "Restore" → GET /restore-consent/authorize?tenant_id=X
2. Backend stores state in Redis, returns OAuth URL
3. Admin consents in popup → Microsoft redirects to callback
4. Backend exchanges code for tokens → stores in Redis (NOT DB)
5. Restore engine retrieves token from Redis → executes restore
6. After restore → token discarded from Redis
"""
import logging
import secrets
from datetime import datetime, timedelta

import msal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth import get_current_user
from app.services.audit import audit_log
from app.services.redis_state import set_state, get_state, delete_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/restore-consent", tags=["Restore Consent"])

# Redis key prefix and TTL
_PREFIX = "restore_consent:"
_TTL = 7200  # 2 hours (covers long restores with auto-refresh)

# Delegated scopes for restore (write permissions)
# Do NOT include 'offline_access' — MSAL adds it automatically
RESTORE_DELEGATED_SCOPES = [
    "Mail.ReadWrite",
    "Calendars.ReadWrite",
    "Contacts.ReadWrite",
    "User.ReadWrite.All",
    "Group.ReadWrite.All",
]


def _get_msal_app(tenant_id: str) -> msal.ConfidentialClientApplication:
    """Create MSAL app for delegated flow against a specific tenant."""
    return msal.ConfidentialClientApplication(
        client_id=settings.CONNECTOR_APP_ID,
        client_credential=settings.CONNECTOR_APP_SECRET,
        authority=f"{settings.MS_AUTH_URL}/{tenant_id}",
    )


@router.get("/authorize")
async def start_restore_consent(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start OAuth delegated consent flow for restore.

    Returns authorization URL for frontend popup.
    State stored in Redis with TTL (survives pod restart).
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.BACKEND_URL}/api/restore-consent/callback"

    app = _get_msal_app(tenant.ms_tenant_id)
    auth_url = app.get_authorization_request_url(
        scopes=RESTORE_DELEGATED_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )

    # Store state in Redis (not in-memory)
    await set_state(f"{_PREFIX}{state}", {
        "tenant_id": tenant_id,
        "ms_tenant_id": tenant.ms_tenant_id,
        "user_id": current_user.id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }, ttl_seconds=_TTL)

    await audit_log(
        db, action="restore.consent_started", resource_type="tenant",
        resource_id=tenant_id, user_id=current_user.id,
        details=f"Admin initiated restore consent for {tenant.name}",
        severity="warning",
    )
    await db.commit()

    return {"auth_url": auth_url, "state": state}


@router.get("/callback")
async def restore_consent_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth callback — exchange code for tokens, store in Redis.

    Supports both BFF (browser redirect) and API (JSON response).
    """
    from fastapi.responses import RedirectResponse
    from urllib.parse import urlencode

    is_browser = "text/html" in request.headers.get("accept", "")

    if error:
        logger.warning(f"Restore consent denied: {error} — {error_description}")
        if state:
            entry = await get_state(f"{_PREFIX}{state}")
            if entry:
                entry["status"] = "denied"
                await set_state(f"{_PREFIX}{state}", entry, ttl_seconds=_TTL)
        if is_browser:
            return RedirectResponse(f"{settings.FRONTEND_URL}/recovery?consent=denied")
        raise HTTPException(403, detail=f"Consent denied: {error_description or error}")

    if not state:
        raise HTTPException(400, detail="Missing state token")

    entry = await get_state(f"{_PREFIX}{state}")
    if not entry:
        raise HTTPException(400, detail="Invalid or expired state token")

    # Check expiry (10 min for consent flow)
    created = datetime.fromisoformat(entry["created_at"])
    if datetime.utcnow() - created > timedelta(minutes=10):
        await delete_state(f"{_PREFIX}{state}")
        raise HTTPException(410, detail="Consent flow expired. Please try again.")

    # Exchange code for tokens
    redirect_uri = f"{settings.BACKEND_URL}/api/restore-consent/callback"
    app = _get_msal_app(entry["ms_tenant_id"])

    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=RESTORE_DELEGATED_SCOPES,
        redirect_uri=redirect_uri,
    )

    if "access_token" not in result:
        error_desc = result.get("error_description", "Token acquisition failed")
        logger.error(f"Restore token acquisition failed: {error_desc}")
        entry["status"] = "failed"
        await set_state(f"{_PREFIX}{state}", entry, ttl_seconds=_TTL)
        raise HTTPException(500, detail=f"Token acquisition failed: {error_desc[:100]}")

    # Store tokens in Redis (NOT in DB — zero persistence of write tokens)
    entry["access_token"] = result["access_token"]
    entry["refresh_token"] = result.get("refresh_token")
    entry["expires_at"] = (datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))).isoformat()
    entry["status"] = "ready"
    await set_state(f"{_PREFIX}{state}", entry, ttl_seconds=_TTL)

    logger.info(
        f"Restore consent granted for tenant {entry['tenant_id']} "
        f"by user {entry['user_id']} — token expires in {result.get('expires_in', 3600)}s"
    )

    if is_browser:
        params = urlencode({"consent": "success", "state": state})
        return RedirectResponse(f"{settings.FRONTEND_URL}/recovery?{params}")

    return {
        "status": "ready",
        "tenant_id": entry["tenant_id"],
        "expires_in": result.get("expires_in", 3600),
        "scopes": result.get("scope", ""),
    }


@router.get("/status")
async def check_consent_status(
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Check if admin has completed consent (polled by frontend)."""
    entry = await get_state(f"{_PREFIX}{state}")
    if not entry:
        raise HTTPException(404, detail="State token not found or expired")

    return {
        "status": entry["status"],
        "tenant_id": entry["tenant_id"],
        "has_token": "access_token" in entry,
        "expires_at": entry.get("expires_at"),
    }


async def get_restore_token(state: str) -> str:
    """Get a valid delegated access token for restore operations.

    Called by restore engine. Auto-refreshes if near expiry.
    Raises ValueError if token not found, expired, or refresh fails.
    """
    entry = await get_state(f"{_PREFIX}{state}")
    if not entry:
        raise ValueError("No restore consent token found. Admin must authorize first.")

    if entry["status"] != "ready":
        raise ValueError(f"Restore consent not ready (status: {entry['status']})")

    # Check if token needs refresh (within 5 min of expiry)
    expires_at = datetime.fromisoformat(entry["expires_at"])
    if datetime.utcnow() >= expires_at - timedelta(minutes=5):
        if not entry.get("refresh_token"):
            raise ValueError("Access token expired and no refresh token. Admin must re-authorize.")

        logger.info(f"Refreshing restore token for tenant {entry['tenant_id']}")
        app = _get_msal_app(entry["ms_tenant_id"])
        result = app.acquire_token_by_refresh_token(
            refresh_token=entry["refresh_token"],
            scopes=RESTORE_DELEGATED_SCOPES,
        )

        if "access_token" not in result:
            entry["status"] = "expired"
            await set_state(f"{_PREFIX}{state}", entry, ttl_seconds=_TTL)
            raise ValueError(f"Token refresh failed: {result.get('error_description', 'unknown')}")

        entry["access_token"] = result["access_token"]
        entry["refresh_token"] = result.get("refresh_token", entry["refresh_token"])
        entry["expires_at"] = (datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))).isoformat()
        await set_state(f"{_PREFIX}{state}", entry, ttl_seconds=_TTL)
        logger.info(f"Restore token refreshed — new expiry in {result.get('expires_in', 3600)}s")

    return entry["access_token"]


async def discard_restore_token(state: str):
    """Discard restore token after job completes.

    Ensures zero standing write access — tokens never persist beyond the restore job.
    """
    entry = await get_state(f"{_PREFIX}{state}")
    if entry:
        tenant_id = entry.get("tenant_id")
        await delete_state(f"{_PREFIX}{state}")
        logger.info(f"Restore token discarded for tenant {tenant_id} — zero standing write access")


# cleanup_expired_tokens() is no longer needed — Redis TTL handles auto-expiry
