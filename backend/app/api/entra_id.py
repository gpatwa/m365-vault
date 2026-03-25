"""Entra ID API routes — browse and search backed-up directory objects."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.user import User
from app.services.auth import get_current_user
from app.interfaces.dispatcher_factory import get_dispatcher
from app.interfaces.job_message import BackupObjectMessage
from app.utils.query import ListParams, apply_sorting, apply_pagination

router = APIRouter(prefix="/api/entra-id", tags=["Entra ID"])

# Entra ID item types for filtering
ENTRA_ITEM_TYPES = [
    ItemType.USER, ItemType.GROUP, ItemType.DIRECTORY_ROLE,
    ItemType.ROLE_ASSIGNMENT, ItemType.CONDITIONAL_ACCESS_POLICY,
    ItemType.APP_REGISTRATION, ItemType.NAMED_LOCATION,
]


@router.get("/summary")
async def entra_id_summary(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary of backed-up Entra ID objects for a tenant."""
    # Get the Entra ID protected object
    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.ENTRA_ID,
        )
    )
    entra_obj = result.scalar_one_or_none()
    if not entra_obj:
        return {"protected": False, "message": "Entra ID not discovered for this tenant"}

    # Get latest completed snapshot
    snap_result = await db.execute(
        select(Snapshot).where(
            Snapshot.protected_object_id == entra_obj.id,
            Snapshot.status == SnapshotStatus.COMPLETED,
        ).order_by(desc(Snapshot.completed_at)).limit(1)
    )
    latest_snapshot = snap_result.scalar_one_or_none()

    if not latest_snapshot:
        return {
            "protected": True,
            "object_id": entra_obj.id,
            "status": entra_obj.status.value,
            "last_backup": None,
            "counts": {},
        }

    # Count items by type in latest snapshot
    counts = {}
    for item_type in ENTRA_ITEM_TYPES:
        count_result = await db.execute(
            select(func.count()).where(
                SnapshotItem.snapshot_id == latest_snapshot.id,
                SnapshotItem.item_type == item_type,
            )
        )
        count = count_result.scalar() or 0
        if count > 0:
            counts[item_type.value] = count

    return {
        "protected": True,
        "object_id": entra_obj.id,
        "status": entra_obj.status.value,
        "last_backup": latest_snapshot.completed_at.isoformat() if latest_snapshot.completed_at else None,
        "snapshot_id": latest_snapshot.id,
        "item_count": latest_snapshot.item_count,
        "size_bytes": latest_snapshot.size_bytes,
        "counts": counts,
    }


@router.get("/snapshots")
async def list_snapshots(
    tenant_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Entra ID backup snapshots for a tenant."""
    # Find the Entra ID protected object
    obj_result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.ENTRA_ID,
        )
    )
    entra_obj = obj_result.scalar_one_or_none()
    if not entra_obj:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    # Count snapshots
    count_result = await db.execute(
        select(func.count()).where(Snapshot.protected_object_id == entra_obj.id)
    )
    total = count_result.scalar() or 0

    # Fetch snapshots
    snap_result = await db.execute(
        select(Snapshot).where(
            Snapshot.protected_object_id == entra_obj.id,
        ).order_by(desc(Snapshot.started_at))
        .offset((page - 1) * page_size).limit(page_size)
    )
    snapshots = snap_result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": s.id,
                "snapshot_type": s.snapshot_type.value,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "item_count": s.item_count,
                "size_bytes": s.size_bytes,
                "items_failed": s.items_failed,
            }
            for s in snapshots
        ],
    }


@router.get("/snapshot/{snapshot_id}/items")
async def list_snapshot_items(
    snapshot_id: int,
    item_type: str = Query(None, description="Filter by item type: user, group, conditional_access_policy, etc."),
    params: ListParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse items in an Entra ID snapshot with sorting, search, and pagination."""
    # Verify snapshot exists
    snapshot = await db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    stmt = select(SnapshotItem).where(
        SnapshotItem.snapshot_id == snapshot_id,
        SnapshotItem.item_type.in_(ENTRA_ITEM_TYPES),
    )

    if item_type:
        try:
            filter_type = ItemType(item_type)
            stmt = stmt.where(SnapshotItem.item_type == filter_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid item_type: {item_type}")

    if params.search:
        stmt = stmt.where(SnapshotItem.name.ilike(f"%{params.search}%"))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Sort — default to item_type, name
    if params.sort_by:
        stmt = apply_sorting(stmt, SnapshotItem, params.sort_by, params.sort_order)
    else:
        stmt = stmt.order_by(SnapshotItem.item_type, SnapshotItem.name)

    stmt = apply_pagination(stmt, params.page, params.page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "items": [
            {
                "id": item.id,
                "item_type": item.item_type.value,
                "ms_item_id": item.ms_item_id,
                "name": item.name,
                "path": item.path,
                "size_bytes": item.size_bytes,
                "metadata": json.loads(item.metadata_json) if item.metadata_json else None,
            }
            for item in items
        ],
    }


@router.get("/snapshot/{snapshot_id}/item/{item_id}")
async def get_snapshot_item(
    snapshot_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a single backed-up Entra ID object."""
    result = await db.execute(
        select(SnapshotItem).where(
            SnapshotItem.id == item_id,
            SnapshotItem.snapshot_id == snapshot_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return {
        "id": item.id,
        "item_type": item.item_type.value,
        "ms_item_id": item.ms_item_id,
        "name": item.name,
        "path": item.path,
        "size_bytes": item.size_bytes,
        "compressed_size": item.compressed_size,
        "content_hash": item.content_hash,
        "blob_path": item.blob_path,
        "metadata": json.loads(item.metadata_json) if item.metadata_json else None,
        "created_at": item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
    }


@router.post("/backup")
async def backup_entra_id(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger on-demand backup of Entra ID directory."""
    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.ENTRA_ID,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="No Entra ID object found for this tenant. Run discovery first.")

    result = await get_dispatcher().dispatch_backup_object(
        BackupObjectMessage(protected_object_id=obj.id), db=db
    )
    if not result.success and result.status != "queued":
        raise HTTPException(status_code=500, detail=result.error or "Backup failed")
    if result.status != "queued":
        await db.commit()

    return {
        "status": result.status,
        "snapshot_id": result.snapshot_id,
        "item_count": result.item_count,
        "size_bytes": result.size_bytes,
        "snapshot_status": result.status,
    }
