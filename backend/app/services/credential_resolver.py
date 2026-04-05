"""Credential Resolver — routes Graph API calls to per-workload Entra apps.

This is the ONLY place that resolves tenant credentials to a GraphClient.
All engines (backup, restore, discovery, context) call this instead of
directly decrypting tenant.client_secret_encrypted.

Each workload (entra_id, exchange, sharepoint, onedrive, teams) has its own
Entra app registration with only the permissions that workload needs.
"""
import logging
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.tenant_workload_app import TenantWorkloadApp
from app.services.graph_client import GraphClient
from app.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class WorkloadNotConfiguredError(Exception):
    """Raised when a workload has no configured app for a tenant."""
    def __init__(self, tenant_id: int, workload: str):
        self.tenant_id = tenant_id
        self.workload = workload
        super().__init__(
            f"Workload '{workload}' is not configured for tenant {tenant_id}. "
            f"Enable it via POST /api/tenants/{tenant_id}/workloads"
        )


async def get_graph_client(
    db: AsyncSession,
    tenant: Tenant,
    workload: str,
    access_mode: Literal["backup", "restore", "default"] = "default",
) -> GraphClient:
    """Resolve per-workload Entra app credentials and return a GraphClient.

    Looks up tenant_workload_apps for the given (tenant_id, workload).
    If found and consented, uses workload-specific credentials.
    If not found, falls back to legacy tenant.client_id (for backward compat
    during migration — will be removed once all tenants re-onboard).

    Args:
        db: Database session
        tenant: Tenant model instance
        workload: Workload key (entra_id, exchange, sharepoint, onedrive, teams)
        access_mode: "backup" (read-only), "restore" (read-write), or "default"

    Returns:
        GraphClient configured with the correct credentials and access mode
    """
    # Try per-workload app
    result = await db.execute(
        select(TenantWorkloadApp).where(
            TenantWorkloadApp.tenant_id == tenant.id,
            TenantWorkloadApp.workload == workload,
            TenantWorkloadApp.enabled == 1,
        )
    )
    workload_app = result.scalar_one_or_none()

    if workload_app and workload_app.consent_status in ("consented", "partial"):
        client_secret = encryption_service.decrypt_string(workload_app.client_secret_encrypted)
        # Update last_used_at
        workload_app.last_used_at = datetime.utcnow()
        logger.debug(
            f"Using per-workload app for tenant={tenant.id} workload={workload} "
            f"client_id={workload_app.client_id[:8]}..."
        )
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=workload_app.client_id,
            client_secret=client_secret,
            access_mode=access_mode,
        )

    # Fallback: legacy single-app credentials (during migration period)
    if tenant.client_id and tenant.client_secret_encrypted:
        logger.debug(
            f"Fallback to legacy app for tenant={tenant.id} workload={workload} "
            f"(no per-workload app configured)"
        )
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret,
            access_mode=access_mode,
        )

    raise WorkloadNotConfiguredError(tenant.id, workload)


async def get_workload_apps(
    db: AsyncSession,
    tenant_id: int,
    enabled_only: bool = True,
) -> list[TenantWorkloadApp]:
    """Get all workload apps for a tenant."""
    stmt = select(TenantWorkloadApp).where(
        TenantWorkloadApp.tenant_id == tenant_id,
    )
    if enabled_only:
        stmt = stmt.where(TenantWorkloadApp.enabled == 1)
    result = await db.execute(stmt.order_by(TenantWorkloadApp.workload))
    return list(result.scalars().all())


async def get_workload_app(
    db: AsyncSession,
    tenant_id: int,
    workload: str,
) -> TenantWorkloadApp | None:
    """Get a specific workload app for a tenant."""
    result = await db.execute(
        select(TenantWorkloadApp).where(
            TenantWorkloadApp.tenant_id == tenant_id,
            TenantWorkloadApp.workload == workload,
        )
    )
    return result.scalar_one_or_none()
