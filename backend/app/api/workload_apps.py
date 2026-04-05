"""Workload Management API — enable/disable per-workload Entra apps for tenants.

Each workload (Entra ID, Exchange, SharePoint, etc.) gets its own Entra app
registration with only the permissions that workload needs.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant
from app.models.tenant_workload_app import TenantWorkloadApp
from app.models.user import User
from app.services.auth import get_current_user, require_role
from app.models.user import UserRole
from app.services.encryption import encryption_service
from app.services.audit import audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenants", tags=["Workload Apps"])

require_admin = require_role(UserRole.ADMIN)

# Valid workloads
VALID_WORKLOADS = {"entra_id", "exchange", "sharepoint", "onedrive", "teams"}


class EnableWorkloadsRequest(BaseModel):
    workloads: list[str]  # ["entra_id", "exchange"]


@router.post("/{tenant_id}/workloads")
async def enable_workloads(
    tenant_id: int,
    req: EnableWorkloadsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Enable workloads for a tenant — creates per-workload Entra app registrations.

    For each requested workload, creates a TenantWorkloadApp record.
    In production, this would also create the actual Entra app registration
    via app_provisioning.create_workload_app(). For now, it stores the
    tenant's existing credentials as a placeholder until re-onboarding.
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    # Validate workloads
    invalid = set(req.workloads) - VALID_WORKLOADS
    if invalid:
        raise HTTPException(400, detail=f"Invalid workloads: {invalid}. Valid: {VALID_WORKLOADS}")

    from app.services.app_provisioning import WORKLOAD_PERMISSIONS, get_workload_permissions

    created = []
    consent_urls = {}

    for workload in req.workloads:
        # Check if already exists
        existing = await db.execute(
            select(TenantWorkloadApp).where(
                TenantWorkloadApp.tenant_id == tenant_id,
                TenantWorkloadApp.workload == workload,
            )
        )
        if existing.scalar_one_or_none():
            continue  # Already enabled

        # Get required permissions for this workload
        perms = get_workload_permissions(workload, include_restore=True)
        display_name = WORKLOAD_PERMISSIONS[workload]["display_name"]

        # Create workload app record
        # In production: call app_provisioning.create_workload_app() to create
        # a real Entra app. For now, use tenant's existing credentials.
        wl_app = TenantWorkloadApp(
            tenant_id=tenant_id,
            workload=workload,
            client_id=tenant.client_id,
            client_secret_encrypted=tenant.client_secret_encrypted,
            consent_status="consented" if tenant.client_id else "pending",
            permissions_requested=json.dumps(sorted(perms)),
            backup_ready=1 if tenant.client_id else 0,
            restore_ready=1 if tenant.client_id else 0,
            enabled=1,
        )
        db.add(wl_app)
        created.append(workload)

        # Generate consent URL
        from app.services.app_provisioning import app_provisioning
        consent_urls[workload] = app_provisioning.get_admin_consent_url(
            tenant_id=tenant.ms_tenant_id,
            client_id=tenant.client_id,
        )

    await db.flush()

    await audit_log(
        db, action="workload.enabled", resource_type="tenant",
        resource_id=tenant_id, user_id=current_user.id,
        details=f"Enabled workloads: {created}",
    )

    await db.commit()

    return {
        "tenant_id": tenant_id,
        "workloads_created": created,
        "consent_urls": consent_urls,
        "total_workload_apps": len(created),
    }


@router.get("/{tenant_id}/workloads")
async def list_workloads(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workload apps for a tenant with their consent status."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    from app.services.credential_resolver import get_workload_apps
    apps = await get_workload_apps(db, tenant_id, enabled_only=False)

    return {
        "tenant_id": tenant_id,
        "workloads": [
            {
                "id": app.id,
                "workload": app.workload,
                "consent_status": app.consent_status,
                "backup_ready": bool(app.backup_ready),
                "restore_ready": bool(app.restore_ready),
                "enabled": bool(app.enabled),
                "client_id": app.client_id[:8] + "..." if app.client_id else None,
                "secret_expires_at": app.secret_expires_at.isoformat() if app.secret_expires_at else None,
                "last_used_at": app.last_used_at.isoformat() if app.last_used_at else None,
                "error_message": app.error_message,
                "created_at": app.created_at.isoformat() if app.created_at else None,
            }
            for app in apps
        ],
    }


@router.post("/{tenant_id}/workloads/{workload}/check")
async def check_workload_consent(
    tenant_id: int,
    workload: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Verify consent status for a specific workload app.

    Checks Graph API permissions granted to the workload's Entra app
    and updates backup_ready/restore_ready flags.
    """
    if workload not in VALID_WORKLOADS:
        raise HTTPException(400, detail=f"Invalid workload: {workload}")

    from app.services.credential_resolver import get_workload_app
    wl_app = await get_workload_app(db, tenant_id, workload)
    if not wl_app:
        raise HTTPException(404, detail=f"Workload '{workload}' not configured for this tenant")

    tenant = await db.get(Tenant, tenant_id)

    try:
        from app.services.credential_resolver import get_graph_client
        from app.services.app_provisioning import app_provisioning, WORKLOAD_PERMISSIONS

        graph = await get_graph_client(db, tenant, workload)
        token = await graph._get_token()

        result = await app_provisioning.check_granted_permissions(
            access_token=token, app_id=wl_app.client_id,
        )

        # Update status based on granted permissions
        wl_perms = WORKLOAD_PERMISSIONS.get(workload, {})
        granted = set()
        for wl_data in result.get("workloads", {}).values():
            if wl_data.get("backup"):
                granted.update(wl_perms.get("backup", []))
            if wl_data.get("restore"):
                granted.update(wl_perms.get("restore", []))

        wl_app.permissions_granted = json.dumps(sorted(granted))
        wl_app.backup_ready = 1 if result.get("all_backup_ready") else 0
        wl_app.consent_status = "consented" if wl_app.backup_ready else "partial"
        wl_app.error_message = None
        await db.commit()

        return {
            "workload": workload,
            "consent_status": wl_app.consent_status,
            "backup_ready": bool(wl_app.backup_ready),
            "restore_ready": bool(wl_app.restore_ready),
            "permissions_granted": json.loads(wl_app.permissions_granted) if wl_app.permissions_granted else [],
        }

    except Exception as e:
        wl_app.consent_status = "error"
        wl_app.error_message = str(e)[:500]
        await db.commit()
        return {"workload": workload, "consent_status": "error", "error": str(e)}


@router.post("/{tenant_id}/workloads/{workload}/disable")
async def disable_workload(
    tenant_id: int,
    workload: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Disable a workload — stops backups but keeps the app."""
    from app.services.credential_resolver import get_workload_app
    wl_app = await get_workload_app(db, tenant_id, workload)
    if not wl_app:
        raise HTTPException(404, detail=f"Workload '{workload}' not configured")

    wl_app.enabled = 0
    await audit_log(
        db, action="workload.disabled", resource_type="tenant",
        resource_id=tenant_id, user_id=current_user.id,
        details=f"Disabled workload: {workload}",
    )
    await db.commit()
    return {"workload": workload, "enabled": False}


@router.delete("/{tenant_id}/workloads/{workload}")
async def remove_workload(
    tenant_id: int,
    workload: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Remove a workload app entirely."""
    from app.services.credential_resolver import get_workload_app
    wl_app = await get_workload_app(db, tenant_id, workload)
    if not wl_app:
        raise HTTPException(404, detail=f"Workload '{workload}' not configured")

    await db.delete(wl_app)
    await audit_log(
        db, action="workload.removed", resource_type="tenant",
        resource_id=tenant_id, user_id=current_user.id,
        details=f"Removed workload: {workload}",
    )
    await db.commit()
    return {"workload": workload, "removed": True}
