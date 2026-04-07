"""Agent Shield API — monitor AI agent activity in M365.

Endpoints:
- GET /api/agents/dashboard — summary stats
- GET /api/agents/profiles — known agent profiles with risk scores
- GET /api/agents/activity — paginated activity log
- GET /api/agents/shadow — shadow (unmanaged) agents
- POST /api/agents/scan — trigger manual scan
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user, require_tenant_access_dep
from app.services.agent_monitor import (
    get_agent_dashboard,
    get_agent_profiles,
    get_agent_activity,
    get_shadow_agents,
    scan_tenant_agents,
)
router = APIRouter(prefix="/api/agents", tags=["Agent Shield"], dependencies=[Depends(require_tenant_access_dep())])


@router.get("/dashboard")
async def agent_dashboard(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent Shield dashboard — summary stats for a tenant."""
    return await get_agent_dashboard(db, tenant_id)


@router.get("/profiles")
async def agent_profiles(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Known agent profiles with risk scores."""
    return {"profiles": await get_agent_profiles(db, tenant_id)}


@router.get("/activity")
async def agent_activity_log(
    tenant_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paginated agent activity log."""
    return await get_agent_activity(db, tenant_id, page, page_size)


@router.get("/shadow")
async def shadow_agents(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Shadow (unmanaged) agents detected in the tenant."""
    return {"shadow_agents": await get_shadow_agents(db, tenant_id)}


@router.post("/scan")
async def scan_agents(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a manual scan for agent activity."""
    return await scan_tenant_agents(db, tenant_id)
