"""Workload Bootstrap — Auto-creates per-workload Entra app registrations.

On first startup, creates 5 multi-tenant Entra apps in KavachIQ's tenant:
- KavachIQ-EntraID
- KavachIQ-Exchange
- KavachIQ-SharePoint
- KavachIQ-OneDrive
- KavachIQ-Teams

Each app has ONLY the Graph API permissions that workload needs.
Credentials are stored in saas_workload_apps (encrypted).

Prerequisites:
- CONNECTOR_APP_ID must have Application.ReadWrite.OwnedBy permission
  (or Application.ReadWrite.All) in KavachIQ's home tenant
- CONNECTOR_APP_SECRET must be valid

This is fully automated — no manual az CLI commands needed.
"""
import json
import logging
from datetime import datetime, timedelta

import httpx

from app.config import settings
from app.services.encryption import encryption_service
from app.services.app_provisioning import WORKLOAD_PERMISSIONS, REQUIRED_APP_PERMISSIONS

logger = logging.getLogger(__name__)

# Microsoft Graph resource app ID (constant)
MS_GRAPH_RESOURCE_APP_ID = "00000003-0000-0000-c000-000000000000"

# Env var prefix for pre-provisioned workload apps (optional override)
# If WORKLOAD_ENTRA_ID_APP_ID is set, use it instead of auto-creating
ENV_PREFIX = "WORKLOAD_"


async def _get_management_token() -> str | None:
    """Get a token for managing app registrations in KavachIQ's home tenant.

    Uses the CONNECTOR app credentials with client_credentials flow.
    The connector app needs Application.ReadWrite.OwnedBy (to create/manage
    apps it owns) in KavachIQ's Entra tenant.
    """
    import msal

    if not settings.CONNECTOR_APP_ID or not settings.CONNECTOR_APP_SECRET:
        logger.debug("No connector credentials — cannot bootstrap workload apps")
        return None

    # Use a real tenant ID to avoid AADSTS53003 (Conditional Access blocks 'common'/'organizations')
    # Try to find a real tenant in the DB, fall back to 'organizations'
    authority_tenant = "organizations"
    try:
        from app.database import async_session as _session
        from app.models.tenant import Tenant
        from sqlalchemy import select as _select
        async with _session() as _db:
            result = await _db.execute(
                _select(Tenant).where(
                    ~Tenant.ms_tenant_id.like("demo-%")
                ).limit(1)
            )
            tenant = result.scalar_one_or_none()
            if tenant and tenant.ms_tenant_id and not tenant.ms_tenant_id.startswith("demo-"):
                authority_tenant = tenant.ms_tenant_id
    except Exception:
        pass

    app = msal.ConfidentialClientApplication(
        client_id=settings.CONNECTOR_APP_ID,
        client_credential=settings.CONNECTOR_APP_SECRET,
        authority=f"{settings.MS_AUTH_URL}/{authority_tenant}",
    )

    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )

    if "access_token" in result:
        return result["access_token"]

    error = result.get("error_description", result.get("error", "unknown"))
    logger.warning(f"Cannot get management token for workload bootstrap: {error}")
    return None


def _build_required_resource_access(workload: str) -> list[dict]:
    """Build the requiredResourceAccess payload for a workload's Entra app.

    Maps permission names to their Graph API role IDs.
    """
    wl_config = WORKLOAD_PERMISSIONS.get(workload)
    if not wl_config:
        return []

    # Combine backup + restore permissions for this workload
    all_perms = set(wl_config["backup"]) | set(wl_config.get("restore", []))

    resource_access = []
    for perm_name in sorted(all_perms):
        role_id = REQUIRED_APP_PERMISSIONS.get(perm_name)
        if role_id:
            resource_access.append({"id": role_id, "type": "Role"})

    return [{
        "resourceAppId": MS_GRAPH_RESOURCE_APP_ID,
        "resourceAccess": resource_access,
    }]


async def _create_entra_app(
    token: str,
    display_name: str,
    workload: str,
    redirect_uris: list[str],
) -> dict | None:
    """Create a multi-tenant Entra app registration via Graph API.

    Returns dict with app_id, object_id, or None on failure.
    """
    required_resource_access = _build_required_resource_access(workload)
    wl_config = WORKLOAD_PERMISSIONS.get(workload, {})
    perms = set(wl_config.get("backup", [])) | set(wl_config.get("restore", []))

    body = {
        "displayName": display_name,
        "signInAudience": "AzureADMultipleOrgs",
        "requiredResourceAccess": required_resource_access,
        "web": {
            "redirectUris": redirect_uris,
        },
        "notes": f"KavachIQ per-workload app for {workload}. Auto-created {datetime.utcnow().isoformat()}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Check if app already exists by display name
        check_resp = await client.get(
            f"https://graph.microsoft.com/v1.0/applications?$filter=displayName eq '{display_name}'&$select=appId,id",
            headers={"Authorization": f"Bearer {token}"},
        )
        if check_resp.status_code == 200:
            existing = check_resp.json().get("value", [])
            if existing:
                logger.info(f"Workload app '{display_name}' already exists: {existing[0]['appId']}")
                return {
                    "app_id": existing[0]["appId"],
                    "object_id": existing[0]["id"],
                    "already_existed": True,
                }

        # Create the app
        resp = await client.post(
            "https://graph.microsoft.com/v1.0/applications",
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        if resp.status_code not in (200, 201):
            error = resp.json().get("error", {}).get("message", resp.text[:200])
            logger.error(f"Failed to create '{display_name}': {error}")
            return None

        data = resp.json()
        logger.info(f"Created Entra app: {display_name} (appId={data['appId']})")
        return {
            "app_id": data["appId"],
            "object_id": data["id"],
            "already_existed": False,
        }


async def _create_client_secret(
    token: str,
    app_object_id: str,
    display_name: str,
) -> dict | None:
    """Create a client secret for an app registration. Returns secret_text + key_id."""
    body = {
        "passwordCredential": {
            "displayName": f"KavachIQ Auto-Generated ({display_name})",
            "endDateTime": (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://graph.microsoft.com/v1.0/applications/{app_object_id}/addPassword",
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        if resp.status_code not in (200, 201):
            error = resp.json().get("error", {}).get("message", resp.text[:200])
            logger.error(f"Failed to create secret for {display_name}: {error}")
            return None

        data = resp.json()
        return {
            "secret_text": data["secretText"],
            "key_id": data["keyId"],
            "end_date": data.get("endDateTime"),
        }


async def _rename_legacy_connector_app():
    """Rename the legacy connector app if it still has old branding (ShieldIO).

    Automatically renames to 'KavachIQ Connector' via Graph API.
    Idempotent — skips if already renamed.
    """
    token = await _get_management_token()
    if not token:
        return

    app_id = settings.CONNECTOR_APP_ID
    if not app_id:
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Look up the app registration
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/applications?$filter=appId eq '{app_id}'&$select=id,displayName",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                return

            apps = resp.json().get("value", [])
            if not apps:
                return

            app = apps[0]
            current_name = app.get("displayName", "")

            # Check if it needs renaming (contains old branding)
            needs_rename = any(old in current_name.lower() for old in ["shieldio", "shield.io", "shield io"])
            if not needs_rename:
                return

            new_name = "KavachIQ Connector"
            patch_resp = await client.patch(
                f"https://graph.microsoft.com/v1.0/applications/{app['id']}",
                json={"displayName": new_name},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            if patch_resp.status_code in (200, 204):
                logger.info(f"Renamed connector app from '{current_name}' to '{new_name}'")
            else:
                logger.warning(f"Failed to rename connector app: {patch_resp.status_code}")
    except Exception as e:
        logger.debug(f"Connector rename skipped: {e}")


async def bootstrap_workload_apps():
    """Auto-create per-workload Entra apps if they don't exist.

    Called during application startup. Idempotent — skips workloads that
    already have a SaaSWorkloadApp record in the database.

    Resolution order:
    1. Check DB (saas_workload_apps) — already bootstrapped?
    2. Check env vars (WORKLOAD_{WORKLOAD}_APP_ID) — pre-provisioned?
    3. Auto-create via Graph API using CONNECTOR credentials
    """
    # First, rename legacy connector app if it's still called "ShieldIO"
    await _rename_legacy_connector_app()

    from app.database import async_session
    from app.models.saas_workload_app import SaaSWorkloadApp
    from sqlalchemy import select

    # Build redirect URIs from config
    redirect_uris = [settings.CONNECTOR_REDIRECT_URI]
    if settings.FRONTEND_URL and settings.FRONTEND_URL != "http://localhost:5173":
        redirect_uris.append(f"{settings.FRONTEND_URL}/onboard/callback")

    async with async_session() as db:
        created_count = 0
        skipped_count = 0

        for workload, config in WORKLOAD_PERMISSIONS.items():
            display_name = config["display_name"]
            workload_upper = workload.upper()

            # 1. Check DB
            existing = await db.execute(
                select(SaaSWorkloadApp).where(SaaSWorkloadApp.workload == workload)
            )
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

            # 2. Check env vars (pre-provisioned)
            import os
            env_app_id = os.environ.get(f"{ENV_PREFIX}{workload_upper}_APP_ID", "")
            env_app_secret = os.environ.get(f"{ENV_PREFIX}{workload_upper}_APP_SECRET", "")
            env_object_id = os.environ.get(f"{ENV_PREFIX}{workload_upper}_APP_OBJECT_ID", "")

            if env_app_id and env_app_secret:
                logger.info(f"Using pre-provisioned env vars for {display_name}: {env_app_id[:8]}...")
                perms = set(config["backup"]) | set(config.get("restore", []))
                saas_app = SaaSWorkloadApp(
                    workload=workload,
                    display_name=display_name,
                    app_id=env_app_id,
                    app_object_id=env_object_id or None,
                    client_secret_encrypted=encryption_service.encrypt_string(env_app_secret),
                    permissions_configured=json.dumps(sorted(perms)),
                    redirect_uris=json.dumps(redirect_uris),
                    secret_expires_at=datetime.utcnow() + timedelta(days=365),
                    status="active",
                )
                db.add(saas_app)
                created_count += 1
                continue

            # 3. Auto-create via Graph API
            token = await _get_management_token()
            if not token:
                logger.info(f"Skipping auto-creation of {display_name} — no management token available")
                continue

            app_data = await _create_entra_app(token, display_name, workload, redirect_uris)
            if not app_data:
                continue

            # Create secret (only if we just created the app)
            secret_data = None
            if not app_data.get("already_existed"):
                secret_data = await _create_client_secret(
                    token, app_data["object_id"], display_name,
                )
            else:
                # App existed but we don't have the secret — need env var or manual step
                logger.warning(
                    f"{display_name} exists in Entra but no secret in DB or env. "
                    f"Set {ENV_PREFIX}{workload_upper}_APP_SECRET or delete + re-create."
                )
                continue

            if not secret_data:
                continue

            perms = set(config["backup"]) | set(config.get("restore", []))
            saas_app = SaaSWorkloadApp(
                workload=workload,
                display_name=display_name,
                app_id=app_data["app_id"],
                app_object_id=app_data["object_id"],
                client_secret_encrypted=encryption_service.encrypt_string(secret_data["secret_text"]),
                permissions_configured=json.dumps(sorted(perms)),
                redirect_uris=json.dumps(redirect_uris),
                secret_expires_at=datetime.fromisoformat(secret_data["end_date"].replace("Z", "+00:00")).replace(tzinfo=None)
                    if secret_data.get("end_date") else datetime.utcnow() + timedelta(days=365),
                secret_key_id=secret_data["key_id"],
                status="active",
            )
            db.add(saas_app)
            created_count += 1
            logger.info(f"Bootstrapped {display_name}: {app_data['app_id']}")

        if created_count > 0:
            await db.commit()
            logger.info(f"Workload bootstrap: created {created_count}, skipped {skipped_count}")
        elif skipped_count > 0:
            logger.info(f"Workload bootstrap: all {skipped_count} apps already exist")
        else:
            logger.info("Workload bootstrap: no apps created (no credentials available)")


async def get_saas_workload_app(db, workload: str):
    """Get the SaaS-level workload app for a given workload.

    Returns the SaaSWorkloadApp record or None.
    Used by onboarding to generate per-workload consent URLs and by
    enable_workloads to set the correct credentials on TenantWorkloadApp.
    """
    from app.models.saas_workload_app import SaaSWorkloadApp
    from sqlalchemy import select

    result = await db.execute(
        select(SaaSWorkloadApp).where(
            SaaSWorkloadApp.workload == workload,
            SaaSWorkloadApp.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def get_all_saas_workload_apps(db) -> dict:
    """Get all SaaS workload apps as a dict keyed by workload."""
    from app.models.saas_workload_app import SaaSWorkloadApp
    from sqlalchemy import select

    result = await db.execute(
        select(SaaSWorkloadApp).where(SaaSWorkloadApp.status == "active")
    )
    return {app.workload: app for app in result.scalars().all()}
