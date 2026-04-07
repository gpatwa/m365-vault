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
from app.errors import (
    KavachIQError, CONNECTOR_NOT_CONFIGURED, CONNECTOR_SECRET_INVALID,
    CONNECTOR_GRAPH_UNREACHABLE, CONNECTOR_TENANT_NOT_FOUND,
    VALIDATION_RESOURCE_NOT_FOUND,
)
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User
from app.services.auth import get_current_user
from app.services.encryption import encryption_service
from app.connectors.registry import get_connector, list_connectors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/onboard", tags=["Onboarding"])

# OAuth state store — Redis in production, in-memory fallback for dev
# Survives pod restarts, works across replicas
from app.services.redis_state import set_state as _set_state, get_state as _get_state, delete_state as _delete_state

# Microsoft Graph resource app ID
MS_GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"


async def _ensure_connector_permissions():
    """Ensure the connector app registration has all required Graph API permissions.

    Uses Azure CLI credentials (az login) to update the app registration.
    This is idempotent — only adds missing permissions.
    Called automatically during the onboarding /connect flow.
    """
    from app.services.app_provisioning import REQUIRED_APP_PERMISSIONS
    import httpx

    app_id = settings.CONNECTOR_APP_ID
    if not app_id:
        return

    # Get current app registration
    try:
        import msal
        # Use the connector's own credentials to check its registration
        # Note: this requires the app to have Application.ReadWrite.OwnedBy or similar
        # If it fails, we'll use the requiredResourceAccess from the Graph API
        app = msal.ConfidentialClientApplication(
            client_id=app_id,
            client_credential=settings.CONNECTOR_APP_SECRET,
            authority=f"{settings.MS_AUTH_URL}/3725cec5-3e2d-402c-a5a6-460c325d8f87",
        )
        token_result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in token_result:
            logger.debug("Cannot check connector permissions — token acquisition failed")
            return

        token = token_result["access_token"]

        # Check current permissions via Graph API
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/applications?$filter=appId eq '{app_id}'&$select=id,requiredResourceAccess",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                logger.debug(f"Cannot read app registration: {resp.status_code}")
                return

            apps = resp.json().get("value", [])
            if not apps:
                logger.debug("App registration not found")
                return

            app_obj = apps[0]
            app_object_id = app_obj["id"]

            # Check if Graph permissions are already configured
            current_perms = set()
            for rra in app_obj.get("requiredResourceAccess", []):
                if rra.get("resourceAppId") == MS_GRAPH_APP_ID:
                    for ra in rra.get("resourceAccess", []):
                        current_perms.add(ra["id"])

            # Build the required permissions (application type = Role)
            required = [
                {"id": perm_id, "type": "Role"}
                for perm_name, perm_id in REQUIRED_APP_PERMISSIONS.items()
                if perm_id not in current_perms
            ]

            if not required:
                logger.debug("Connector app already has all required permissions")
                return

            logger.info(f"Adding {len(required)} missing permissions to connector app")

            # Build the full requiredResourceAccess payload
            all_perms = [
                {"id": perm_id, "type": "Role"}
                for perm_id in REQUIRED_APP_PERMISSIONS.values()
            ]

            # Update the app registration
            update_resp = await client.patch(
                f"https://graph.microsoft.com/v1.0/applications/{app_object_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "requiredResourceAccess": [{
                        "resourceAppId": MS_GRAPH_APP_ID,
                        "resourceAccess": all_perms,
                    }]
                },
            )

            if update_resp.status_code in (200, 204):
                logger.info(f"Connector app permissions updated: {len(all_perms)} permissions configured")
            else:
                logger.warning(f"Failed to update app permissions: {update_resp.status_code} {update_resp.text[:200]}")

    except Exception as e:
        logger.debug(f"Auto-configure permissions skipped: {e}")


@router.get("/connector-health")
async def connector_health():
    """Check if the KavachIQ connector app is properly configured.

    Returns health status so the frontend can show appropriate guidance
    if the connector credentials are missing or invalid.
    """
    from app.connectors.registry import get_connector
    from app.config import settings
    import msal

    app_id = settings.CONNECTOR_APP_ID
    app_secret = settings.CONNECTOR_APP_SECRET

    if not app_id or not app_secret:
        return {
            "healthy": False,
            "error_code": "E1001",
            "error": "Connector app credentials not configured",
            "action": "Set CONNECTOR_APP_ID and CONNECTOR_APP_SECRET environment variables",
        }

    # Verify the app registration exists and secret format is valid
    try:
        import httpx
        # Use a known tenant for validation — 'common' fails with security defaults
        # Try to find a real tenant in the DB, fall back to 'organizations'
        from app.database import async_session
        from app.models.tenant import Tenant
        test_authority = "organizations"
        async with async_session() as _db:
            result = await _db.execute(
                select(Tenant).where(
                    ~Tenant.ms_tenant_id.like("demo-%")
                ).limit(1)
            )
            tenant = result.scalar_one_or_none()
            if tenant and tenant.ms_tenant_id and not tenant.ms_tenant_id.startswith("demo-"):
                test_authority = tenant.ms_tenant_id

        msal_app = msal.ConfidentialClientApplication(
            client_id=app_id,
            client_credential=app_secret,
            authority=f"https://login.microsoftonline.com/{test_authority}",
        )
        token = msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "error" in token:
            error_desc = token.get("error_description", "")
            # AADSTS7000215 = bad secret — this is a real problem
            if "AADSTS7000215" in error_desc:
                return {
                    "healthy": False,
                    "error_code": "E1002",
                    "error": "Invalid client secret",
                    "action": "Regenerate the client secret in Azure AD and update CONNECTOR_APP_SECRET",
                }
            # AADSTS7000229 = no SP in home tenant — OK for multi-tenant apps
            if "AADSTS7000229" in error_desc:
                return {"healthy": True, "app_id": app_id, "note": "Multi-tenant app ready for customer consent"}
            return {
                "healthy": False,
                "error": "Credential validation failed",
                "detail": error_desc[:200],
            }
        return {"healthy": True, "app_id": app_id}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:200]}


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
    mode: str = Query("fast", description="Onboarding mode: 'fast' (real customer) or 'demo' (prospect showcase)"),
    current_user: User = Depends(get_current_user),
):
    """Start OAuth connection flow for a platform.

    Returns the authorization URL to redirect the customer to.
    Mode determines the post-OAuth onboarding experience:
    - 'fast': 4-step flow (connect → discover → protect → done)
    - 'demo': 7-step flow with intelligence, backup story, cyber sim
    """
    # All users (including demo) go through real OAuth when connector is configured
    try:
        connector = get_connector(platform)
    except ValueError as e:
        raise KavachIQError(VALIDATION_RESOURCE_NOT_FOUND, detail=str(e))

    info = connector.info()
    if not info.available:
        raise KavachIQError(CONNECTOR_NOT_CONFIGURED, detail=f"{info.display_name} is not yet available")

    # Pre-flight check: verify connector secret works BEFORE sending user to Microsoft
    if platform == "microsoft365":
        from app.services.system_health import SystemHealthService
        health = SystemHealthService()
        check = await health.check_connector_secret()
        if not check.healthy:
            logger.error(f"Pre-flight connector check failed: {check.detail}")
            raise KavachIQError(
                CONNECTOR_SECRET_INVALID,
                detail=f"KavachIQ connector is not properly configured. {check.fix}",
            )

    # Note: Connector app permissions must be configured BEFORE onboarding.
    # Run: make configure-connector (one-time setup)
    # The _ensure_connector_permissions() function cannot auto-configure from
    # the app's own token (needs Application.Read.All which is chicken-and-egg).

    # Generate state token for CSRF protection (stored in Redis, survives pod restart)
    state = secrets.token_urlsafe(32)
    import asyncio
    asyncio.ensure_future(_set_state(f"onboard:{state}", {
        "platform": platform,
        "user_id": current_user.id,
        "mode": mode,
    }, ttl_seconds=600))  # 10 min TTL

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
    onboard_mode = "fast"  # Default mode
    connecting_user_id = None
    if state:
        state_data = await _get_state(f"onboard:{state}")
        if state_data:
            await _delete_state(f"onboard:{state}")  # One-time use
            platform = state_data.get("platform", "microsoft365")
            onboard_mode = state_data.get("mode", "fast")
        connecting_user_id = state_data.get("user_id")

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
            # Re-run discovery on reconnect to refresh counts
            # This ensures per-workload permissions are validated
            try:
                from app.services.discovery import DiscoveryService
                discovery = DiscoveryService(db)
                disc_result = await discovery.discover_all(existing_tenant)
                await db.commit()
                logger.info(f"Re-discovery for {existing_tenant.name}: {disc_result}")
            except Exception as e:
                logger.warning(f"Re-discovery failed for {existing_tenant.name}: {e}")
                disc_result = None

            from sqlalchemy import func as _func
            from app.models.protected_object import ProtectedObject
            obj_count = (await db.execute(
                select(_func.count(ProtectedObject.id)).where(ProtectedObject.tenant_id == existing_tenant.id)
            )).scalar() or 0

            return {
                "success": True,
                "existing": True,
                "mode": onboard_mode,
                "tenant_id": result.tenant_id,
                "tenant_name": existing_tenant.name,
                "db_tenant_id": existing_tenant.id,
                "discovery": {
                    "total_objects": obj_count,
                    "mailboxes": existing_tenant.total_mailboxes or 0,
                    "entra_objects": existing_tenant.total_entra_objects or 0,
                    "sites": existing_tenant.total_sites or 0,
                    "onedrives": existing_tenant.total_onedrives or 0,
                    "teams": existing_tenant.total_teams or 0,
                },
            }

        # Create tenant record
        tenant_record = Tenant(
            name=(result.tenant_name or f"Tenant {result.tenant_id[:8]}").strip(),
            ms_tenant_id=result.tenant_id,
            client_id=result.credentials["client_id"],
            client_secret_encrypted=encryption_service.encrypt_string(
                result.credentials["client_secret"]
            ),
            status=TenantStatus.ONBOARDING,
        )
        db.add(tenant_record)
        await db.flush()

        # Auto-assign connecting user to this tenant
        if connecting_user_id:
            from app.services.auth import assign_user_to_tenant
            await assign_user_to_tenant(db, connecting_user_id, tenant_record.id, role="owner", is_default=True)
            logger.info(f"Assigned user {connecting_user_id} to tenant {tenant_record.id} as owner")

        # Run discovery
        from app.services.discovery import DiscoveryService
        discovery = DiscoveryService(db)
        disc_result = await discovery.discover_all(tenant_record)

        await db.commit()

        return {
            "success": True,
            "new": True,
            "mode": onboard_mode,
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
    workload_types: list[str] = None  # Filter to specific workloads e.g. ['entra_id', 'exchange']


@router.post("/complete")
async def complete_onboarding(
    req: CompleteOnboardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize onboarding: assign SLA policy, activate tenant, start first backup."""
    tenant = await db.get(Tenant, req.tenant_id)
    if not tenant:
        raise KavachIQError(CONNECTOR_TENANT_NOT_FOUND, detail="Tenant not found in database")

    # Auto-create default SLA policy if none provided or doesn't exist
    sla_id = req.sla_policy_id
    if req.protect_all:
        from app.models.sla_policy import SLAPolicy
        if sla_id:
            existing_sla = await db.get(SLAPolicy, sla_id)
            if not existing_sla:
                sla_id = None  # Will create default below
        if not sla_id:
            # Create a default daily SLA policy for this tenant
            default_sla = SLAPolicy(
                name=f"Daily Backup - {tenant.name}",
                backup_frequency_hours=24,
                retention_days=30,
                is_active=1,
            )
            db.add(default_sla)
            await db.flush()  # Get the ID
            sla_id = default_sla.id
            logger.info(f"Created default SLA policy {sla_id} for tenant {req.tenant_id}")

    # Assign SLA policy to unprotected objects (optionally filtered by workload)
    if req.protect_all and sla_id:
        from app.models.protected_object import ProtectedObject, ProtectionStatus, WorkloadType
        stmt = select(ProtectedObject).where(
            ProtectedObject.tenant_id == req.tenant_id,
            ProtectedObject.status == ProtectionStatus.UNPROTECTED,
        )
        if req.workload_types:
            wl_enums = [WorkloadType(wt) for wt in req.workload_types]
            stmt = stmt.where(ProtectedObject.workload_type.in_(wl_enums))
        result = await db.execute(stmt)
        for obj in result.scalars().all():
            obj.sla_policy_id = sla_id
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
        raise KavachIQError(CONNECTOR_TENANT_NOT_FOUND, detail="Tenant not found in database")

    from app.services.discovery import DiscoveryService
    discovery = DiscoveryService(db)
    result = await discovery.discover_all(tenant, workloads=req.workloads)
    await db.commit()

    return {"status": "completed", "results": result}


@router.get("/workloads")
async def list_available_workloads(
    db: AsyncSession = Depends(get_db),
):
    """List available workloads with metadata for the discovery toggle UI.

    Includes per-workload app status (whether the SaaS app is provisioned).
    """
    from app.services.workload_bootstrap import get_all_saas_workload_apps

    saas_apps = await get_all_saas_workload_apps(db)

    workloads = [
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
            "key": "exchange",
            "label": "Exchange",
            "description": "Emails, calendar events, contacts",
            "icon": "mail",
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
            "recommended": False,
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

    # Enrich with per-workload app availability
    for wl in workloads:
        saas_app = saas_apps.get(wl["key"])
        wl["app_provisioned"] = saas_app is not None
        wl["app_id"] = saas_app.app_id[:8] + "..." if saas_app else None

    return {"workloads": workloads}


@router.get("/workload-consent-urls/{tenant_ms_id}")
async def get_workload_consent_urls(
    tenant_ms_id: str,
    workloads: str = Query(None, description="Comma-separated workload keys. None = all provisioned."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate per-workload admin consent URLs for a customer tenant.

    Each URL redirects the customer admin to consent to ONE workload's
    Entra app with only that workload's permissions. Customer picks which
    workloads to protect.

    Example: customer only needs Exchange + Entra ID → consent 2 apps.
    """
    from app.services.workload_bootstrap import get_all_saas_workload_apps

    saas_apps = await get_all_saas_workload_apps(db)
    if not saas_apps:
        raise HTTPException(
            503,
            detail="Per-workload apps not yet provisioned. Check startup logs.",
        )

    # Filter to requested workloads
    requested = set(workloads.split(",")) if workloads else set(saas_apps.keys())
    redirect_uri = settings.CONNECTOR_REDIRECT_URI

    consent_urls = {}
    for wl_key in sorted(requested):
        saas_app = saas_apps.get(wl_key)
        if not saas_app:
            continue

        url = (
            f"https://login.microsoftonline.com/{tenant_ms_id}/adminconsent"
            f"?client_id={saas_app.app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state=workload:{wl_key}"
        )
        consent_urls[wl_key] = {
            "url": url,
            "app_name": saas_app.display_name,
            "app_id": saas_app.app_id,
            "permissions": json.loads(saas_app.permissions_configured) if saas_app.permissions_configured else [],
        }

    return {
        "tenant_id": tenant_ms_id,
        "consent_urls": consent_urls,
        "total": len(consent_urls),
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
        raise KavachIQError(CONNECTOR_TENANT_NOT_FOUND, detail="Tenant not found in database")

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


@router.get("/intelligence")
async def get_onboard_intelligence(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return org intelligence for the onboarding wizard.

    For demo tenants, returns simulated hierarchy with criticality scores.
    For real tenants, calls the org-context service.
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise KavachIQError(CONNECTOR_TENANT_NOT_FOUND, detail="Tenant not found")

    # Demo tenants: return simulated org intelligence
    if tenant.ms_tenant_id and tenant.ms_tenant_id.startswith("demo-"):
        return _generate_demo_intelligence(tenant.name)

    # Real tenants: fetch from org-context service (auto-sync if empty)
    from app.models.org_context import UserContext
    result = await db.execute(
        select(UserContext).where(UserContext.tenant_id == tenant_id).order_by(UserContext.criticality_score.desc())
    )
    users = result.scalars().all()
    if not users:
        # No org context yet — auto-trigger sync from Graph API
        try:
            from app.services.context_collector import ContextCollectorService
            from app.services.criticality_scorer import CriticalityScorer
            logger.info(f"Auto-syncing org context for tenant {tenant_id} during onboarding")
            collector = ContextCollectorService(db)
            await collector.collect_all(tenant)
            scorer = CriticalityScorer(db)
            await scorer.score_all(tenant_id)
            await db.commit()
            # Re-fetch after sync
            result = await db.execute(
                select(UserContext).where(UserContext.tenant_id == tenant_id).order_by(UserContext.criticality_score.desc())
            )
            users = result.scalars().all()
        except Exception as e:
            logger.warning(f"Auto-sync failed for tenant {tenant_id}: {e}")
    if not users:
        # Still no data — fall back to demo intelligence
        return _generate_demo_intelligence(tenant.name)

    user_list = []
    for u in users:
        tier = "low"
        if u.criticality_score >= 90: tier = "critical"
        elif u.criticality_score >= 75: tier = "high"
        elif u.criticality_score >= 50: tier = "medium"
        user_list.append({
            "name": u.display_name or "Unknown",
            "title": u.job_title or "",
            "email": u.email or "",
            "score": u.criticality_score or 0,
            "tier": tier,
            "manager": getattr(u, 'manager_display_name', None) or (u.manager_ms_id if hasattr(u, 'manager_ms_id') else None),
            "reports_count": u.direct_reports_count or 0,
        })

    tiers = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for u in user_list:
        tiers[u["tier"]] += 1

    return {
        "users": user_list[:20],  # Top 20 by criticality
        "tiers": tiers,
        "total_users": len(user_list),
        "mvb_plan": {
            "phases": [
                {"name": "Identity Controls", "description": "Entra ID policies, roles, MFA", "objects": tiers["critical"], "est_minutes": 5},
                {"name": "Critical Users", "description": "CEO, CFO, privileged admins", "objects": tiers["critical"], "est_minutes": 10},
                {"name": "High Priority", "description": "VPs, directors, key departments", "objects": tiers["high"], "est_minutes": 15},
                {"name": "Full Recovery", "description": "All remaining users and data", "objects": tiers["medium"] + tiers["low"], "est_minutes": 30},
            ]
        },
    }


def _generate_demo_intelligence(tenant_name: str) -> dict:
    """Generate simulated org intelligence for demo tenants."""
    domain = tenant_name.lower().replace(" ", "") + ".com"
    users = [
        # Critical tier (score 90+)
        {"name": "Sarah Chen", "title": "Chief Executive Officer", "email": f"sarah.chen@{domain}", "score": 95, "tier": "critical", "manager": None, "reports_count": 4},
        # High tier (score 75-89)
        {"name": "Marcus Johnson", "title": "VP Engineering", "email": f"marcus.j@{domain}", "score": 88, "tier": "high", "manager": "Sarah Chen", "reports_count": 3},
        {"name": "Emily Rodriguez", "title": "VP Sales", "email": f"emily.r@{domain}", "score": 85, "tier": "high", "manager": "Sarah Chen", "reports_count": 2},
        {"name": "David Kim", "title": "CFO", "email": f"david.k@{domain}", "score": 82, "tier": "high", "manager": "Sarah Chen", "reports_count": 2},
        # Medium tier (score 50-74)
        {"name": "Lisa Thompson", "title": "Director of IT", "email": f"lisa.t@{domain}", "score": 72, "tier": "medium", "manager": "Marcus Johnson", "reports_count": 2},
        {"name": "James Wilson", "title": "Director of Product", "email": f"james.w@{domain}", "score": 68, "tier": "medium", "manager": "Marcus Johnson", "reports_count": 1},
        {"name": "Priya Patel", "title": "Director of Marketing", "email": f"priya.p@{domain}", "score": 65, "tier": "medium", "manager": "Emily Rodriguez", "reports_count": 1},
        {"name": "Alex Turner", "title": "Head of Finance", "email": f"alex.t@{domain}", "score": 62, "tier": "medium", "manager": "David Kim", "reports_count": 1},
        {"name": "Rachel Lee", "title": "Director of HR", "email": f"rachel.l@{domain}", "score": 60, "tier": "medium", "manager": "Sarah Chen", "reports_count": 2},
        # Low tier (score <50)
        {"name": "Tom Nakamura", "title": "Senior Engineer", "email": f"tom.n@{domain}", "score": 45, "tier": "low", "manager": "Lisa Thompson", "reports_count": 0},
        {"name": "Fatima Al-Zahra", "title": "Account Executive", "email": f"fatima.a@{domain}", "score": 42, "tier": "low", "manager": "Emily Rodriguez", "reports_count": 0},
        {"name": "Ben Cooper", "title": "DevOps Engineer", "email": f"ben.c@{domain}", "score": 40, "tier": "low", "manager": "Lisa Thompson", "reports_count": 0},
        {"name": "Mia Santos", "title": "Marketing Analyst", "email": f"mia.s@{domain}", "score": 38, "tier": "low", "manager": "Priya Patel", "reports_count": 0},
        {"name": "Jake Morrison", "title": "Financial Analyst", "email": f"jake.m@{domain}", "score": 35, "tier": "low", "manager": "Alex Turner", "reports_count": 0},
        {"name": "Olga Petrov", "title": "HR Coordinator", "email": f"olga.p@{domain}", "score": 32, "tier": "low", "manager": "Rachel Lee", "reports_count": 0},
    ]

    return {
        "users": users,
        "tiers": {"critical": 1, "high": 3, "medium": 5, "low": 6},
        "total_users": 15,
        "mvb_plan": {
            "phases": [
                {"name": "Phase 1: Identity Controls", "description": "Entra ID — roles, policies, MFA configs", "objects": 3, "est_minutes": 5, "users": ["Entra ID Config"]},
                {"name": "Phase 2: Critical Users", "description": "CEO and executive data restored first", "objects": 1, "est_minutes": 8, "users": ["Sarah Chen"]},
                {"name": "Phase 3: High Priority", "description": "VPs and key leadership", "objects": 3, "est_minutes": 12, "users": ["Marcus Johnson", "Emily Rodriguez", "David Kim"]},
                {"name": "Phase 4: Full Recovery", "description": "All directors and staff", "objects": 11, "est_minutes": 25, "users": ["Lisa Thompson", "James Wilson", "Priya Patel", "Alex Turner", "Rachel Lee", "+ 6 more"]},
            ]
        },
    }


# ═══════════════════════════════════════════════════════
# Invite Your Admin — OAuth delegation for non-admin users
# ═══════════════════════════════════════════════════════

class InviteAdminRequest(BaseModel):
    tenant_name: str
    admin_email: str


@router.post("/invite-admin")
async def invite_admin(
    req: InviteAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Send an invite to a Global Admin to complete OAuth consent.

    For prospects who aren't Global Admins — they can delegate the consent
    step to their IT admin via a secure, time-limited link.
    """
    from app.models.admin_invite import AdminInvite
    from datetime import timedelta

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    invite = AdminInvite(
        tenant_name=req.tenant_name,
        invited_by_user_id=current_user.id,
        admin_email=req.admin_email,
        token=token,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invite)
    await db.flush()

    # Build invite URL
    invite_url = f"{settings.FRONTEND_URL}/onboard/invite/{token}"

    # Send email to admin
    from app.services.email_service import email_service
    try:
        await email_service.send_email(
            to=req.admin_email,
            subject=f"{current_user.full_name or current_user.username} invited you to connect {req.tenant_name} to KavachIQ",
            html=f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 520px; margin: 0 auto;">
              <h2 style="color: #0d9488;">KavachIQ — Admin Consent Request</h2>
              <p><strong>{current_user.full_name or current_user.username}</strong> has invited you to connect
              <strong>{req.tenant_name}</strong> to KavachIQ for Microsoft 365 data protection.</p>

              <p>As a Global Admin, you can grant read-only access for backup:</p>
              <ul>
                <li>Mail.Read — backup mailbox data</li>
                <li>Directory.Read.All — backup Entra ID config</li>
                <li>No write or delete permissions requested</li>
              </ul>

              <div style="margin: 24px 0;">
                <a href="{invite_url}"
                   style="background: #0d9488; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                  Review &amp; Connect →
                </a>
              </div>

              <p style="color: #6b7280; font-size: 13px;">
                This link expires in 7 days. Only a Global Admin can complete this step.
                <br>Questions? Reply to this email.
              </p>
            </div>
            """,
        )
    except Exception as e:
        logger.error(f"Failed to send admin invite email: {e}")

    from app.services.audit import audit_log
    await audit_log(
        db, action="onboard.admin_invited", resource_type="admin_invite",
        resource_id=invite.id, user_id=current_user.id,
        details=f"Invited {req.admin_email} for {req.tenant_name}",
    )

    await db.commit()

    return {
        "invite_id": invite.id,
        "admin_email": req.admin_email,
        "invite_url": invite_url,
        "expires_at": expires_at.isoformat(),
        "status": "sent",
    }


@router.get("/invite/{token}")
async def get_invite_status(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Check invite status (public endpoint — admin clicks the link)."""
    from app.models.admin_invite import AdminInvite
    result = await db.execute(
        select(AdminInvite).where(AdminInvite.token == token)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(404, detail="Invite not found or expired")

    if invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        await db.commit()
        raise HTTPException(410, detail="This invite has expired. Ask the user to send a new one.")

    return {
        "tenant_name": invite.tenant_name,
        "status": invite.status,
        "admin_email": invite.admin_email,
    }


@router.get("/invite/{token}/connect")
async def start_invite_oauth(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin clicks invite link → starts OAuth consent flow."""
    from app.models.admin_invite import AdminInvite
    result = await db.execute(
        select(AdminInvite).where(
            AdminInvite.token == token,
            AdminInvite.status == "pending",
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(404, detail="Invite not found or already completed")

    if invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        await db.commit()
        raise HTTPException(410, detail="Invite expired")

    # Generate OAuth URL with invite token as state
    from app.connectors.m365_connector import M365Connector
    connector = M365Connector()
    state = f"invite:{token}"
    redirect_uri = settings.CONNECTOR_REDIRECT_URI

    auth_url = (
        f"https://login.microsoftonline.com/common/adminconsent"
        f"?client_id={connector.app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

    return {"auth_url": auth_url, "tenant_name": invite.tenant_name}


@router.get("/invite/status/{invite_id}")
async def check_invite_completion(
    invite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Check if the admin has completed the OAuth consent (polled by frontend)."""
    from app.models.admin_invite import AdminInvite
    invite = await db.get(AdminInvite, invite_id)
    if not invite:
        raise HTTPException(404, detail="Invite not found")

    return {
        "status": invite.status,
        "ms_tenant_id": invite.ms_tenant_id,
        "completed_at": invite.completed_at.isoformat() if invite.completed_at else None,
    }
