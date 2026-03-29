"""Shared API dependencies — pre-flight checks, idempotency, tenant resolution."""

import logging
from typing import Optional

from fastapi import Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import (
    ShieldioError, BACKUP_TENANT_NOT_CONNECTED, CONNECTOR_GRAPH_UNREACHABLE,
    STORAGE_UNAVAILABLE, DATABASE_ERROR,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_current_user
from app.services.encryption import encryption_service
from app.services.resilience import (
    preflight_graph_api, preflight_storage, preflight_database,
    idempotency_store,
)

logger = logging.getLogger(__name__)


async def get_tenant_with_credentials(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve tenant and verify it has valid credentials."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise ShieldioError(BACKUP_TENANT_NOT_CONNECTED, detail="Tenant not found")
    if not tenant.client_id or not tenant.client_secret_encrypted:
        raise ShieldioError(BACKUP_TENANT_NOT_CONNECTED, detail="Tenant has no connector credentials")
    return tenant


async def run_backup_preflight(
    request: Request,
    tenant: Tenant = Depends(get_tenant_with_credentials),
) -> Tenant:
    """Pre-flight check: verify Graph API, storage, and DB before starting backup.

    Raises ShieldioError if any dependency is unhealthy.
    Returns the tenant on success.
    """
    # Decrypt credentials for Graph API check
    client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)

    # Run checks in parallel
    import asyncio
    graph_result, storage_result, db_result = await asyncio.gather(
        preflight_graph_api(tenant.ms_tenant_id, tenant.client_id, client_secret),
        preflight_storage(),
        preflight_database(),
    )

    if not graph_result.ok:
        logger.warning(f"Pre-flight FAILED: Graph API — {graph_result.detail}")
        raise ShieldioError(
            CONNECTOR_GRAPH_UNREACHABLE,
            detail=f"Graph API check failed: {graph_result.detail}",
        )

    if not storage_result.ok:
        logger.warning(f"Pre-flight FAILED: Storage — {storage_result.detail}")
        raise ShieldioError(
            STORAGE_UNAVAILABLE,
            detail=f"Storage check failed: {storage_result.detail}",
        )

    if not db_result.ok:
        logger.warning(f"Pre-flight FAILED: Database — {db_result.detail}")
        raise ShieldioError(
            DATABASE_ERROR,
            detail=f"Database check failed: {db_result.detail}",
        )

    logger.info(
        f"Pre-flight OK for tenant {tenant.id}: "
        f"graph={graph_result.latency_ms}ms, storage={storage_result.latency_ms}ms, "
        f"db={db_result.latency_ms}ms"
    )
    return tenant


def get_idempotency_key(
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> Optional[str]:
    """Extract idempotency key from request header."""
    return x_idempotency_key
