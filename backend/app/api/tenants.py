"""Tenant management API routes."""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, UserRole
from app.services.auth import get_current_user, require_role
from app.services.encryption import encryption_service
from app.services.discovery import DiscoveryService

router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


class TenantCreateRequest(BaseModel):
    name: str
    ms_tenant_id: str
    client_id: str
    client_secret: str


class TenantResponse(BaseModel):
    id: int
    name: str
    ms_tenant_id: str
    client_id: str
    status: str
    total_mailboxes: int
    total_onedrives: int
    total_sites: int
    total_entra_objects: int = 0
    last_discovery_at: str | None
    created_at: str

    class Config:
        from_attributes = True


class TenantTestResponse(BaseModel):
    success: bool
    message: str
    user_count: int = 0


@router.get("/", response_model=list[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all configured M365 tenants."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return [
        TenantResponse(
            id=t.id, name=t.name, ms_tenant_id=t.ms_tenant_id,
            client_id=t.client_id, status=t.status.value,
            total_mailboxes=t.total_mailboxes, total_onedrives=t.total_onedrives,
            total_sites=t.total_sites, total_entra_objects=t.total_entra_objects or 0,
            last_discovery_at=t.last_discovery_at.isoformat() if t.last_discovery_at else None,
            created_at=t.created_at.isoformat(),
        )
        for t in tenants
    ]


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    req: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Onboard a new M365 tenant."""
    # Check for duplicates
    existing = await db.execute(
        select(Tenant).where(Tenant.ms_tenant_id == req.ms_tenant_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tenant already exists")

    # Encrypt client secret
    encrypted_secret = encryption_service.encrypt_string(req.client_secret)

    tenant = Tenant(
        name=req.name,
        ms_tenant_id=req.ms_tenant_id,
        client_id=req.client_id,
        client_secret_encrypted=encrypted_secret,
        status=TenantStatus.ONBOARDING,
    )
    db.add(tenant)
    await db.flush()

    return TenantResponse(
        id=tenant.id, name=tenant.name, ms_tenant_id=tenant.ms_tenant_id,
        client_id=tenant.client_id, status=tenant.status.value,
        total_mailboxes=0, total_onedrives=0, total_sites=0,
        last_discovery_at=None, created_at=tenant.created_at.isoformat(),
    )


@router.post("/{tenant_id}/test", response_model=TenantTestResponse)
async def test_connection(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Test connectivity to M365 tenant."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        from app.services.graph_client import GraphClient
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        graph = GraphClient(tenant.ms_tenant_id, tenant.client_id, client_secret)
        users = await graph.get("/users", params={"$top": "1", "$select": "id"})
        user_count = len(users.get("value", []))
        return TenantTestResponse(
            success=True, message="Connection successful", user_count=user_count
        )
    except Exception as e:
        return TenantTestResponse(success=False, message=str(e))


@router.post("/{tenant_id}/discover")
async def run_discovery(
    tenant_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Run object discovery for a tenant."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    discovery = DiscoveryService(db)
    try:
        results = await discovery.discover_all(tenant)
    except Exception as e:
        import traceback
        logger.error(f"Discovery failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")
    return {
        "status": "completed",
        "results": results,
    }


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Remove a tenant configuration."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.delete(tenant)
    return {"status": "deleted"}


@router.post("/{tenant_id}/setup")
async def setup_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Combined test + discover + activate for onboarding wizard.

    Step 1: Tests Graph API connection
    Step 2: If test passes, runs full workload discovery
    Step 3: Updates tenant status to ACTIVE
    Returns combined result for the wizard UI.
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = {"test": None, "discovery": None, "status": "failed"}

    # Test connection
    try:
        from app.services.graph_client import GraphClient
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        graph = GraphClient(tenant.ms_tenant_id, tenant.client_id, client_secret)
        users = await graph.get("/users", params={"$top": "1", "$select": "id"})
        result["test"] = {"success": True, "message": "Connection successful"}
    except Exception as e:
        result["test"] = {"success": False, "message": str(e)}
        return result

    # Run discovery
    try:
        discovery = DiscoveryService(db)
        discovery_results = await discovery.discover_all(tenant)
        result["discovery"] = discovery_results
        result["status"] = "completed"

        # Refresh tenant from DB (discovery updated it)
        await db.refresh(tenant)
        tenant.status = TenantStatus.ACTIVE
        await db.commit()
    except Exception as e:
        logger.error(f"Setup discovery failed for tenant {tenant_id}: {e}")
        result["discovery"] = {"error": str(e)}
        result["status"] = "partial"

    return result
