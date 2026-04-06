"""Delegated Restore Consent — admin authenticates to grant write permissions for restore.

Flow:
1. Admin clicks "Restore" → frontend calls GET /api/restore-consent/authorize?tenant_id=X
2. Backend returns OAuth URL → frontend opens popup
3. Admin signs in + consents to write scopes (Mail.ReadWrite, etc.)
4. Microsoft redirects to /api/restore-consent/callback with auth code
5. Backend exchanges code for access_token + refresh_token
6. Tokens stored in-memory (tied to restore job) — NOT persisted
7. Restore engine uses delegated token for write operations
8. After restore completes, tokens discarded — zero standing write access
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/restore-consent", tags=["Restore Consent"])

# In-memory token store — keyed by state token, auto-expires
# Format: { state: { tenant_id, user_id, access_token, refresh_token, expires_at, created_at } }
_restore_tokens: dict[str, dict] = {}

# Delegated scopes for restore (write permissions)
RESTORE_DELEGATED_SCOPES = [
    "Mail.ReadWrite",
    "Calendars.ReadWrite",
    "Contacts.ReadWrite",
    "User.ReadWrite.All",
    "Group.ReadWrite.All",
    "offline_access",  # Required to get refresh_token
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
    """Start the OAuth delegated consent flow for restore.

    Returns an authorization URL that the frontend opens in a popup.
    The admin signs in and consents to write permissions.
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.FRONTEND_URL}/restore/callback"

    app = _get_msal_app(tenant.ms_tenant_id)
    auth_url = app.get_authorization_request_url(
        scopes=RESTORE_DELEGATED_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )

    # Store state for callback validation
    _restore_tokens[state] = {
        "tenant_id": tenant_id,
        "ms_tenant_id": tenant.ms_tenant_id,
        "user_id": current_user.id,
        "created_at": datetime.utcnow(),
        "status": "pending",
    }

    await audit_log(
        db, action="restore.consent_started", resource_type="tenant",
        resource_id=tenant_id, user_id=current_user.id,
        details=f"Admin initiated restore consent for {tenant.name}",
        severity="warning",
    )
    await db.commit()

    return {
        "auth_url": auth_url,
        "state": state,
    }


@router.get("/callback")
async def restore_consent_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth callback after admin consents.

    Exchanges the auth code for access_token + refresh_token.
    Tokens are stored in-memory only — never persisted to DB.
    """
    if error:
        logger.warning(f"Restore consent denied: {error} — {error_description}")
        if state and state in _restore_tokens:
            _restore_tokens[state]["status"] = "denied"
        raise HTTPException(403, detail=f"Consent denied: {error_description or error}")

    if not state or state not in _restore_tokens:
        raise HTTPException(400, detail="Invalid or expired state token")

    token_entry = _restore_tokens[state]

    # Check expiry (10 min max for consent flow)
    if datetime.utcnow() - token_entry["created_at"] > timedelta(minutes=10):
        del _restore_tokens[state]
        raise HTTPException(410, detail="Consent flow expired. Please try again.")

    # Exchange code for tokens
    redirect_uri = f"{settings.FRONTEND_URL}/restore/callback"
    app = _get_msal_app(token_entry["ms_tenant_id"])

    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=RESTORE_DELEGATED_SCOPES,
        redirect_uri=redirect_uri,
    )

    if "access_token" not in result:
        error_desc = result.get("error_description", "Token acquisition failed")
        logger.error(f"Restore token acquisition failed: {error_desc}")
        token_entry["status"] = "failed"
        raise HTTPException(500, detail=f"Token acquisition failed: {error_desc[:100]}")

    # Store tokens in-memory (NOT in DB)
    token_entry["access_token"] = result["access_token"]
    token_entry["refresh_token"] = result.get("refresh_token")
    token_entry["expires_at"] = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
    token_entry["status"] = "ready"

    logger.info(
        f"Restore consent granted for tenant {token_entry['tenant_id']} "
        f"by user {token_entry['user_id']} — token expires in {result.get('expires_in', 3600)}s"
    )

    return {
        "status": "ready",
        "tenant_id": token_entry["tenant_id"],
        "expires_in": result.get("expires_in", 3600),
        "scopes": result.get("scope", ""),
    }


@router.get("/status")
async def check_consent_status(
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Check if the admin has completed the consent flow (polled by frontend)."""
    if state not in _restore_tokens:
        raise HTTPException(404, detail="State token not found or expired")

    entry = _restore_tokens[state]
    return {
        "status": entry["status"],
        "tenant_id": entry["tenant_id"],
        "has_token": "access_token" in entry,
        "expires_at": entry.get("expires_at", "").isoformat() if entry.get("expires_at") else None,
    }


async def get_restore_token(state: str) -> str:
    """Get a valid delegated access token for restore operations.

    Called by the restore engine. Automatically refreshes if expired.
    Returns the access_token string or raises an error.
    """
    if state not in _restore_tokens:
        raise ValueError("No restore consent token found. Admin must authorize first.")

    entry = _restore_tokens[state]
    if entry["status"] != "ready":
        raise ValueError(f"Restore consent not ready (status: {entry['status']})")

    # Check if token needs refresh
    if datetime.utcnow() >= entry["expires_at"] - timedelta(minutes=5):
        if not entry.get("refresh_token"):
            raise ValueError("Access token expired and no refresh token available. Admin must re-authorize.")

        logger.info(f"Refreshing restore token for tenant {entry['tenant_id']}")
        app = _get_msal_app(entry["ms_tenant_id"])
        result = app.acquire_token_by_refresh_token(
            refresh_token=entry["refresh_token"],
            scopes=RESTORE_DELEGATED_SCOPES,
        )

        if "access_token" not in result:
            entry["status"] = "expired"
            raise ValueError(f"Token refresh failed: {result.get('error_description', 'unknown')}")

        entry["access_token"] = result["access_token"]
        entry["refresh_token"] = result.get("refresh_token", entry["refresh_token"])
        entry["expires_at"] = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        logger.info(f"Restore token refreshed — new expiry in {result.get('expires_in', 3600)}s")

    return entry["access_token"]


def discard_restore_token(state: str):
    """Discard the restore token after job completes.

    Called by the restore engine when done. Ensures zero standing write access.
    """
    if state in _restore_tokens:
        tenant_id = _restore_tokens[state].get("tenant_id")
        del _restore_tokens[state]
        logger.info(f"Restore token discarded for tenant {tenant_id} — zero standing write access")


def cleanup_expired_tokens():
    """Remove expired token entries. Called periodically by scheduler."""
    now = datetime.utcnow()
    expired = [
        state for state, entry in _restore_tokens.items()
        if now - entry["created_at"] > timedelta(hours=2)
    ]
    for state in expired:
        del _restore_tokens[state]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired restore consent tokens")
