"""Global search API — search across all workloads with intent awareness."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.catalog import CatalogService
from app.services.intent_search import IntentSearchService, classify_intent

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


@router.get("/intent")
async def intent_search(
    q: str = Query(..., min_length=1, description="Search query"),
    tenant_id: int = Query(...),
    workload: str = Query(None, description="Pre-filter by workload"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Intent-aware search — classifies query and routes to appropriate data sources.

    Returns categorized results (Emails, Files, Messages, Identity, Failures,
    Audit Trail, Anomalies, Compliance) with inline actions per result.
    """
    service = IntentSearchService(db)
    return await service.search(
        query=q,
        tenant_id=tenant_id,
        workload=workload,
        limit=limit,
    )


@router.get("/classify")
async def classify_search_intent(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
):
    """Classify a search query into intents (for debugging/testing)."""
    return {"query": q, "intents": classify_intent(q)}
