"""Onboarding API — multi-platform OAuth connector flow.

Endpoints:
- GET /api/onboard/platforms — list available platforms
- GET /api/onboard/connect/{platform} — start OAuth flow
- GET /api/onboard/callback — handle OAuth callback
- POST /api/onboard/complete — finalize tenant creation + discovery
"""
import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User
from app.services.auth import get_current_user
from app.services.encryption import encryption_service
from app.connectors.registry import get_connector, list_connectors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/onboard", tags=["Onboarding"])

# In-memory state store (use Redis in production)
_onboard_states: dict[str, dict] = {}


@router.get("/platforms")
async def list_platforms():
    """List all available SaaS platforms for connection."""
    connectors = list_connectors()
    return {
        "platforms": [
            {
                "key": c.platform_key,
                "name": c.display_name,
                "description": c.description,
                "icon": c.icon,
                "available": c.available,
                "auth_type": c.auth_type,
            }
            for c in connectors
        ]
    }


@router.get("/connect/{platform}")
async def start_connection(
    platform: str,
    current_user: User = Depends(get_current_user),
):
    """Start OAuth connection flow for a platform.

    Returns the authorization URL to redirect the customer to.
    """
    try:
        connector = get_connector(platform)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    info = connector.info()
    if not info.available:
        raise HTTPException(status_code=400, detail=f"{info.display_name} is not yet available")

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    _onboard_states[state] = {
        "platform": platform,
        "user_id": current_user.id,
    }

    redirect_uri = settings.CONNECTOR_REDIRECT_URI
    auth_url = connector.get_auth_url(redirect_uri=redirect_uri, state=state)

    return {
        "auth_url": auth_url,
        "state": state,
        "platform": platform,
        "redirect_uri": redirect_uri,
    }


@router.get("/callback")
async def oauth_callback(
    request: Request,
    admin_consent: str = Query(None),
    tenant: str = Query(None),
    state: str = Query(None),
    code: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth callback from any platform.

    Called from frontend after Microsoft redirects back.
    Returns JSON (frontend handles the result).
    """
    # Check for OAuth errors
    if error:
        logger.warning(f"OAuth error: {error} — {error_description}")
        return {"success": False, "error": error, "detail": error_description}

    # Skip state validation for admin consent (Microsoft doesn't always return state)
    platform = "microsoft365"  # Default for admin consent flow
    if state and state in _onboard_states:
        state_data = _onboard_states.pop(state)
        platform = state_data["platform"]

    try:
        connector = get_connector(platform)
        result = await connector.handle_callback(
            code=code,
            state=state,
            admin_consent=(admin_consent == "True"),
            tenant=tenant,
        )

        if not result.success:
            return {"success": False, "error": "connection_failed", "detail": result.error}

        # Check if tenant already exists
        existing = await db.execute(
            select(Tenant).where(Tenant.ms_tenant_id == result.tenant_id)
        )
        existing_tenant = existing.scalar_one_or_none()
        if existing_tenant:
            return {
                "success": True,
                "existing": True,
                "tenant_id": result.tenant_id,
                "tenant_name": result.tenant_name,
                "db_tenant_id": existing_tenant.id,
            }

        # Create tenant record
        tenant_record = Tenant(
            name=result.tenant_name or f"Tenant {result.tenant_id[:8]}",
            ms_tenant_id=result.tenant_id,
            client_id=result.credentials["client_id"],
            client_secret_encrypted=encryption_service.encrypt_string(
                result.credentials["client_secret"]
            ),
            status=TenantStatus.ONBOARDING,
        )
        db.add(tenant_record)
        await db.flush()

        # Run discovery
        from app.services.discovery import DiscoveryService
        discovery = DiscoveryService(db)
        disc_result = await discovery.discover_all(tenant_record)

        await db.commit()

        return {
            "success": True,
            "new": True,
            "tenant_id": result.tenant_id,
            "tenant_name": result.tenant_name,
            "db_tenant_id": tenant_record.id,
            "discovery": disc_result,
        }

    except Exception as e:
        logger.error(f"Onboarding callback failed: {e}", exc_info=True)
        return {"success": False, "error": "server_error", "detail": str(e)[:200]}


class CompleteOnboardRequest(BaseModel):
    tenant_id: int
    sla_policy_id: int = None
    protect_all: bool = True


@router.post("/complete")
async def complete_onboarding(
    req: CompleteOnboardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize onboarding: assign SLA policy, activate tenant, start first backup."""
    tenant = await db.get(Tenant, req.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Assign SLA policy if requested
    if req.protect_all and req.sla_policy_id:
        from app.models.protected_object import ProtectedObject, ProtectionStatus
        result = await db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == req.tenant_id,
                ProtectedObject.status == ProtectionStatus.UNPROTECTED,
            )
        )
        for obj in result.scalars().all():
            obj.sla_policy_id = req.sla_policy_id
            obj.status = ProtectionStatus.PROTECTED

    # Activate tenant
    tenant.status = TenantStatus.ACTIVE
    await db.commit()

    return {
        "status": "active",
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
    }


class DiscoverRequest(BaseModel):
    tenant_id: int
    workloads: list[str] = None  # None = all, or ["exchange", "entra_id", ...]


@router.post("/discover")
async def selective_discovery(
    req: DiscoverRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run workload-selective discovery.

    If workloads is None, discovers all workloads.
    If workloads is a list, only discovers the specified workloads.

    Speed guide:
    - exchange: ~2s (validates mailbox per user)
    - entra_id: ~2s (counts directory objects)
    - sharepoint: ~5s (multiple discovery methods)
    - onedrive: ~5s (checks drive per user)
    - teams: ~10s (groups filter + per-user chat probe)
    """
    tenant = await db.get(Tenant, req.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from app.services.discovery import DiscoveryService
    discovery = DiscoveryService(db)
    result = await discovery.discover_all(tenant, workloads=req.workloads)
    await db.commit()

    return {"status": "completed", "results": result}


@router.get("/workloads")
async def list_available_workloads():
    """List available workloads with metadata for the discovery toggle UI."""
    return {
        "workloads": [
            {
                "key": "exchange",
                "label": "Exchange",
                "description": "Emails, calendar events, contacts",
                "icon": "mail",
                "speed": "fast",
                "est_seconds": 2,
                "recommended": True,
            },
            {
                "key": "entra_id",
                "label": "Entra ID",
                "description": "Users, groups, roles, policies, apps",
                "icon": "key",
                "speed": "fast",
                "est_seconds": 2,
                "recommended": True,
            },
            {
                "key": "sharepoint",
                "label": "SharePoint",
                "description": "Sites, document libraries, lists",
                "icon": "globe",
                "speed": "medium",
                "est_seconds": 5,
                "recommended": True,
            },
            {
                "key": "onedrive",
                "label": "OneDrive",
                "description": "Personal files and folders",
                "icon": "hard-drive",
                "speed": "medium",
                "est_seconds": 5,
                "recommended": False,
            },
            {
                "key": "teams",
                "label": "Teams",
                "description": "Channels, messages, chats, files",
                "icon": "message-square",
                "speed": "slow",
                "est_seconds": 10,
                "recommended": False,
            },
        ]
    }


@router.get("/status/{platform}/{tenant_ms_id}")
async def check_connection_status(
    platform: str,
    tenant_ms_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a platform connection is still healthy."""
    result = await db.execute(
        select(Tenant).where(Tenant.ms_tenant_id == tenant_ms_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        connector = get_connector(platform)
        credentials = {
            "ms_tenant_id": tenant.ms_tenant_id,
            "client_id": tenant.client_id,
            "client_secret": encryption_service.decrypt_string(tenant.client_secret_encrypted),
        }
        healthy = await connector.test_connection(credentials)

        return {
            "platform": platform,
            "tenant_id": tenant_ms_id,
            "healthy": healthy,
            "tenant_name": tenant.name,
        }
    except Exception as e:
        return {
            "platform": platform,
            "tenant_id": tenant_ms_id,
            "healthy": False,
            "error": str(e),
        }
