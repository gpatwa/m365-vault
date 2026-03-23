"""Global search API — search across all workloads."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.catalog import CatalogService

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, description="Search query"),
    tenant_id: int = Query(...),
    workload: str = Query(None, description="Filter by workload: exchange, onedrive, sharepoint, teams, entra_id"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search across all workloads — emails, files, Teams messages, Entra ID objects.

    Returns deduplicated results from the latest snapshot of each item,
    grouped by workload with unified result format.
    """
    catalog = CatalogService(db)
    return await catalog.search_all(
        tenant_id=tenant_id,
        query=q,
        workload_filter=workload,
        limit=limit,
    )
