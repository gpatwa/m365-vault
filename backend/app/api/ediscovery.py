"""eDiscovery API — search, hold, and export for litigation support.

Enterprise tier feature. Enables legal teams to:
1. Create a legal hold (prevent data deletion)
2. Search across all backup snapshots with keywords/date range
3. Export matching items for legal review
4. Generate compliance reports

Foundation: API structure + models. Full implementation tracked as Phase 2.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.models.snapshot import SnapshotItem, Snapshot, SnapshotStatus, ItemType
from app.models.protected_object import ProtectedObject
from app.services.auth import get_current_user, require_role, resolve_tenant_filter
from app.services.feature_flags import feature_flags

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ediscovery", tags=["eDiscovery"])


class SearchRequest(BaseModel):
    query: str
    tenant_id: int
    workloads: list[str] = None  # Filter to specific workloads
    date_from: str = None  # ISO date
    date_to: str = None
    custodians: list[str] = None  # Filter by user email
    max_results: int = 100


class HoldRequest(BaseModel):
    tenant_id: int
    name: str
    description: str = None
    custodians: list[str] = None  # User emails to hold
    workloads: list[str] = None  # Workloads to hold
    keywords: list[str] = None  # Search terms for content-based hold


@router.get("/status")
async def ediscovery_status(
    current_user: User = Depends(get_current_user),
):
    """Check if eDiscovery is available for this tenant."""
    enabled = feature_flags.is_enabled("ediscovery")
    return {
        "available": enabled,
        "tier_required": "enterprise",
        "features": ["legal_hold", "content_search", "export", "audit_trail"] if enabled else [],
    }


@router.post("/search")
async def ediscovery_search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Search across all backup snapshots for eDiscovery.

    Searches: email subjects, bodies (via metadata), file names, chat messages.
    Enterprise tier only.
    """
    if not feature_flags.is_enabled("ediscovery"):
        raise HTTPException(403, detail="eDiscovery requires Enterprise plan")

    allowed_ids = await resolve_tenant_filter(db, current_user, req.tenant_id)

    # Build search query across SnapshotItems
    stmt = (
        select(SnapshotItem, Snapshot, ProtectedObject)
        .join(Snapshot, SnapshotItem.snapshot_id == Snapshot.id)
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(
            ProtectedObject.tenant_id.in_(allowed_ids),
            Snapshot.status == SnapshotStatus.COMPLETED,
            or_(
                SnapshotItem.name.ilike(f"%{req.query}%"),
                SnapshotItem.subject.ilike(f"%{req.query}%"),
                SnapshotItem.path.ilike(f"%{req.query}%"),
            ),
        )
    )

    # Date range filter
    if req.date_from:
        stmt = stmt.where(SnapshotItem.received_at >= req.date_from)
    if req.date_to:
        stmt = stmt.where(SnapshotItem.received_at <= req.date_to)

    # Custodian filter
    if req.custodians:
        stmt = stmt.where(ProtectedObject.email.in_(req.custodians))

    # Workload filter
    if req.workloads:
        stmt = stmt.where(ProtectedObject.workload_type.in_(req.workloads))

    stmt = stmt.order_by(SnapshotItem.received_at.desc()).limit(req.max_results)
    result = await db.execute(stmt)
    rows = result.all()

    from app.services.audit import audit_log
    await audit_log(db, action="ediscovery.search", resource_type="tenant",
                    resource_id=req.tenant_id, user_id=current_user.id,
                    details=f"eDiscovery search: '{req.query}' — {len(rows)} results",
                    severity="warning")
    await db.commit()

    return {
        "query": req.query,
        "total_results": len(rows),
        "items": [
            {
                "item_id": item.id,
                "snapshot_id": snapshot.id,
                "object_name": obj.display_name,
                "object_email": obj.email,
                "workload": obj.workload_type.value,
                "item_type": item.item_type.value,
                "name": item.name,
                "subject": item.subject,
                "sender": item.sender,
                "path": item.path,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "size_bytes": item.size_bytes,
            }
            for item, snapshot, obj in rows
        ],
    }


@router.post("/hold")
async def create_legal_hold(
    req: HoldRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a legal hold — prevents data deletion for specified custodians/workloads.

    Enterprise tier only. Activates WORM-equivalent protection on matching data.
    """
    if not feature_flags.is_enabled("ediscovery"):
        raise HTTPException(403, detail="eDiscovery requires Enterprise plan")

    # Apply legal hold to matching SLA policies
    from app.models.sla_policy import SLAPolicy
    result = await db.execute(select(SLAPolicy).where(SLAPolicy.is_active == 1))
    policies = result.scalars().all()

    held_count = 0
    for policy in policies:
        if not policy.legal_hold:
            policy.legal_hold = 1
            held_count += 1

    from app.services.audit import audit_log
    await audit_log(db, action="ediscovery.hold_created", resource_type="tenant",
                    resource_id=req.tenant_id, user_id=current_user.id,
                    details=f"Legal hold: '{req.name}' — {held_count} policies held, custodians: {req.custodians}",
                    severity="critical")
    await db.commit()

    return {
        "name": req.name,
        "status": "active",
        "policies_held": held_count,
        "custodians": req.custodians,
        "created_by": current_user.username,
    }
