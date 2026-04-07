"""Failed Items API — visibility into skipped/failed backup items with resolution guidance."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.snapshot import (
    FailedItem, ErrorCategory, ERROR_RESOLUTION_GUIDE,
    Snapshot, SnapshotStatus, ItemType,
)
from app.models.protected_object import ProtectedObject
from app.models.user import User
from app.services.auth import get_current_user, require_tenant_access_dep
from app.utils.query import ListParams, apply_sorting, apply_pagination

router = APIRouter(prefix="/api/failed-items", tags=["Failed Items"], dependencies=[Depends(require_tenant_access_dep())])


@router.get("")
async def list_failed_items(
    params: ListParams = Depends(),
    snapshot_id: int = Query(None),
    protected_object_id: int = Query(None),
    error_category: str = Query(None),
    is_resolved: bool = Query(None),
    can_retry: bool = Query(None),
    workload_type: str = Query(None),
    include_transient: bool = Query(False, description="Include internal/transient errors (hidden by default)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List failed items with filtering, sorting, and pagination.

    By default, hides internal transient errors (DB pool, connection issues)
    that are auto-retried. Only shows customer-actionable protection gaps.
    Pass include_transient=true to see all errors (admin debugging).
    """
    stmt = select(FailedItem)

    # Hide internal/transient errors by default — customers shouldn't see DB pool errors
    if not include_transient:
        # Filter out internal error messages that are not customer-actionable
        stmt = stmt.where(
            ~FailedItem.error_message.ilike("%sqlalchemy%")
            & ~FailedItem.error_message.ilike("%connection pool%")
            & ~FailedItem.error_message.ilike("%concurrent operations%")
            & ~FailedItem.error_message.ilike("%session is provisioning%")
            & ~FailedItem.error_message.ilike("%no active connection%")
            & ~FailedItem.error_message.ilike("%asyncpg%")
        )

    if workload_type:
        stmt = stmt.join(ProtectedObject, FailedItem.protected_object_id == ProtectedObject.id).where(
            ProtectedObject.workload_type == workload_type
        )
    if snapshot_id:
        stmt = stmt.where(FailedItem.snapshot_id == snapshot_id)
    if protected_object_id:
        stmt = stmt.where(FailedItem.protected_object_id == protected_object_id)
    if error_category:
        stmt = stmt.where(FailedItem.error_category == error_category)
    if is_resolved is not None:
        stmt = stmt.where(FailedItem.is_resolved == is_resolved)
    if can_retry is not None:
        stmt = stmt.where(FailedItem.can_retry == can_retry)
    if params.search:
        pattern = f"%{params.search}%"
        stmt = stmt.where(
            FailedItem.item_name.ilike(pattern)
            | FailedItem.error_message.ilike(pattern)
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    stmt = apply_sorting(stmt, FailedItem, params.sort_by, params.sort_order)
    if not params.sort_by:
        stmt = stmt.order_by(desc(FailedItem.created_at))
    stmt = apply_pagination(stmt, params.page, params.page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "items": [_serialize_failed_item(fi) for fi in items],
    }


@router.get("/summary")
async def failed_items_summary(
    snapshot_id: int = Query(None),
    protected_object_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated summary of failed items grouped by error category.

    Excludes internal transient errors — only shows customer-actionable gaps.
    """
    stmt = select(
        FailedItem.error_category,
        func.count(FailedItem.id).label("count"),
        func.sum(case((FailedItem.is_resolved == True, 1), else_=0)).label("resolved"),
        func.sum(case((FailedItem.can_retry == True, 1), else_=0)).label("retriable"),
    ).where(
        ~FailedItem.error_message.ilike("%sqlalchemy%"),
        ~FailedItem.error_message.ilike("%concurrent operations%"),
        ~FailedItem.error_message.ilike("%session is provisioning%"),
        ~FailedItem.error_message.ilike("%no active connection%"),
        ~FailedItem.error_message.ilike("%asyncpg%"),
    ).group_by(FailedItem.error_category)

    if snapshot_id:
        stmt = stmt.where(FailedItem.snapshot_id == snapshot_id)
    if protected_object_id:
        stmt = stmt.where(FailedItem.protected_object_id == protected_object_id)

    result = await db.execute(stmt)
    rows = result.all()

    categories = []
    total_failed = 0
    total_unresolved = 0
    for row in rows:
        cat = row.error_category.value if hasattr(row.error_category, 'value') else str(row.error_category)
        count = row.count
        resolved = row.resolved or 0
        retriable = row.retriable or 0
        total_failed += count
        total_unresolved += (count - resolved)

        try:
            cat_enum = ErrorCategory(cat)
        except ValueError:
            cat_enum = ErrorCategory.UNKNOWN

        categories.append({
            "category": cat,
            "count": count,
            "resolved": resolved,
            "unresolved": count - resolved,
            "retriable": retriable,
            "resolution_hint": ERROR_RESOLUTION_GUIDE.get(cat_enum, ""),
        })

    # Sort by unresolved count descending
    categories.sort(key=lambda x: x["unresolved"], reverse=True)

    # Per-workload breakdown
    wl_stmt = (
        select(
            ProtectedObject.workload_type,
            func.count(FailedItem.id).label("total"),
            func.sum(case((FailedItem.is_resolved == False, 1), else_=0)).label("unresolved"),
            func.sum(case((FailedItem.can_retry == True, 1), else_=0)).label("retriable"),
        )
        .join(ProtectedObject, FailedItem.protected_object_id == ProtectedObject.id)
        .group_by(ProtectedObject.workload_type)
    )
    wl_result = await db.execute(wl_stmt)
    by_workload = {}
    for row in wl_result.all():
        wl = row.workload_type.value if hasattr(row.workload_type, 'value') else str(row.workload_type)
        total = int(row.total or 0)
        unresolved = int(row.unresolved or 0)
        retriable = int(row.retriable or 0)

        # Find top error category for this workload
        top_stmt = (
            select(FailedItem.error_category, func.count(FailedItem.id).label("cnt"))
            .join(ProtectedObject, FailedItem.protected_object_id == ProtectedObject.id)
            .where(ProtectedObject.workload_type == row.workload_type, FailedItem.is_resolved == False)
            .group_by(FailedItem.error_category)
            .order_by(desc(func.count(FailedItem.id)))
            .limit(1)
        )
        top_result = await db.execute(top_stmt)
        top_row = top_result.first()
        top_cat = top_row.error_category.value if top_row and hasattr(top_row.error_category, 'value') else (str(top_row.error_category) if top_row else None)
        top_cnt = int(top_row.cnt) if top_row else 0

        by_workload[wl] = {
            "total": total,
            "unresolved": unresolved,
            "retriable": retriable,
            "top_category": top_cat,
            "top_category_count": top_cnt,
        }

    return {
        "total_failed": total_failed,
        "total_unresolved": total_unresolved,
        "categories": categories,
        "by_workload": by_workload,
    }


@router.get("/by-snapshot/{snapshot_id}")
async def failed_items_for_snapshot(
    snapshot_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all failed items for a specific snapshot with category breakdown."""
    # Get items
    stmt = (
        select(FailedItem)
        .where(FailedItem.snapshot_id == snapshot_id)
        .order_by(FailedItem.error_category, desc(FailedItem.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # Get counts
    count_result = await db.execute(
        select(func.count()).where(FailedItem.snapshot_id == snapshot_id)
    )
    total = count_result.scalar()

    # Category breakdown
    cat_result = await db.execute(
        select(FailedItem.error_category, func.count(FailedItem.id))
        .where(FailedItem.snapshot_id == snapshot_id)
        .group_by(FailedItem.error_category)
    )
    category_counts = {
        (row[0].value if hasattr(row[0], 'value') else str(row[0])): row[1]
        for row in cat_result.all()
    }

    return {
        "snapshot_id": snapshot_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "category_counts": category_counts,
        "items": [_serialize_failed_item(fi) for fi in items],
    }


class ResolveRequest(BaseModel):
    item_ids: list[int]
    notes: str = None


@router.post("/resolve")
async def resolve_failed_items(
    req: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark failed items as resolved/acknowledged by admin."""
    result = await db.execute(
        select(FailedItem).where(FailedItem.id.in_(req.item_ids))
    )
    items = result.scalars().all()

    resolved_count = 0
    for item in items:
        item.is_resolved = True
        item.resolved_at = datetime.utcnow()
        item.resolved_by = current_user.username
        if req.notes:
            item.resolution_hint = req.notes
        resolved_count += 1

    await db.commit()
    return {"resolved": resolved_count}


@router.post("/dismiss-category")
async def dismiss_by_category(
    snapshot_id: int = Query(...),
    category: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss (resolve) all failed items of a specific error category within a snapshot."""
    try:
        cat_enum = ErrorCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    result = await db.execute(
        select(FailedItem).where(
            FailedItem.snapshot_id == snapshot_id,
            FailedItem.error_category == cat_enum,
            FailedItem.is_resolved == False,
        )
    )
    items = result.scalars().all()

    for item in items:
        item.is_resolved = True
        item.resolved_at = datetime.utcnow()
        item.resolved_by = current_user.username

    await db.commit()
    return {"dismissed": len(items), "category": category}


@router.post("/retry")
async def retry_failed_items(
    item_ids: list[int] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry specific failed items by re-running backup for their parent snapshot/object.

    This creates a new targeted backup for just the failed items.
    """
    result = await db.execute(
        select(FailedItem).where(
            FailedItem.id.in_(item_ids),
            FailedItem.can_retry == True,
            FailedItem.is_resolved == False,
        )
    )
    items = result.scalars().all()

    if not items:
        raise HTTPException(status_code=404, detail="No retriable failed items found")

    # Group by protected_object_id
    objects_to_retry = {}
    for item in items:
        if item.protected_object_id not in objects_to_retry:
            objects_to_retry[item.protected_object_id] = []
        objects_to_retry[item.protected_object_id].append(item)

    from app.services.backup_engine import BackupEngine
    engine = BackupEngine(db)

    results = []
    for obj_id, failed_items in objects_to_retry.items():
        obj = await db.get(ProtectedObject, obj_id)
        if not obj:
            results.append({"object_id": obj_id, "status": "not_found"})
            continue

        try:
            new_snapshot = await engine.run_backup_for_object(obj)
            # Mark the original failed items as resolved via retry
            for fi in failed_items:
                fi.is_resolved = True
                fi.resolved_at = datetime.utcnow()
                fi.resolved_by = current_user.username
                fi.retry_snapshot_id = new_snapshot.id
            await db.commit()

            results.append({
                "object_id": obj_id,
                "object_name": obj.display_name,
                "status": "success",
                "new_snapshot_id": new_snapshot.id,
                "items_retried": len(failed_items),
            })
        except Exception as e:
            results.append({
                "object_id": obj_id,
                "object_name": obj.display_name,
                "status": "failed",
                "error": str(e),
            })

    return {
        "total_items": len(items),
        "objects_retried": len(objects_to_retry),
        "results": results,
    }


def _serialize_failed_item(fi: FailedItem) -> dict:
    cat = fi.error_category.value if hasattr(fi.error_category, 'value') else str(fi.error_category)
    try:
        cat_enum = ErrorCategory(cat)
    except ValueError:
        cat_enum = ErrorCategory.UNKNOWN

    return {
        "id": fi.id,
        "snapshot_id": fi.snapshot_id,
        "protected_object_id": fi.protected_object_id,
        "ms_item_id": fi.ms_item_id,
        "item_type": fi.item_type.value if fi.item_type else None,
        "item_name": fi.item_name,
        "item_path": fi.item_path,
        "error_category": cat,
        "error_message": fi.error_message,
        "error_code": fi.error_code,
        "http_status": fi.http_status,
        "retries_attempted": fi.retries_attempted,
        "resolution_hint": fi.resolution_hint or ERROR_RESOLUTION_GUIDE.get(cat_enum, ""),
        "is_resolved": fi.is_resolved,
        "resolved_at": fi.resolved_at.isoformat() if fi.resolved_at else None,
        "resolved_by": fi.resolved_by,
        "can_retry": fi.can_retry,
        "retry_snapshot_id": fi.retry_snapshot_id,
        "created_at": fi.created_at.isoformat() if fi.created_at else None,
    }
