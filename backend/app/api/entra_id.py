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
from app.interfaces.job_message import BackupObjectMessage, RestoreJobMessage
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.services.auth import require_restore_permission
from app.utils.query import ListParams, apply_sorting, apply_pagination
from pydantic import BaseModel

router = APIRouter(prefix="/api/entra-id", tags=["Entra ID"])

# Entra ID item types for filtering
ENTRA_ITEM_TYPES = [
    ItemType.USER, ItemType.GROUP, ItemType.DIRECTORY_ROLE,
    ItemType.ROLE_ASSIGNMENT, ItemType.CONDITIONAL_ACCESS_POLICY,
    ItemType.APP_REGISTRATION, ItemType.NAMED_LOCATION,
    ItemType.SERVICE_PRINCIPAL, ItemType.ADMINISTRATIVE_UNIT,
    ItemType.OAUTH_PERMISSION_GRANT, ItemType.DEVICE, ItemType.DOMAIN,
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


@router.get("/compare")
async def compare_snapshots(
    snapshot_a: int = Query(..., description="Older snapshot ID"),
    snapshot_b: int = Query(..., description="Newer snapshot ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare two Entra ID snapshots — show added, removed, and changed objects.

    Useful for:
    - Audit: what changed between two backup points
    - Incident response: what was modified during a breach
    - Compliance: verify no unauthorized changes
    """
    # Get items from both snapshots
    items_a_result = await db.execute(
        select(SnapshotItem).where(
            SnapshotItem.snapshot_id == snapshot_a,
            SnapshotItem.item_type.in_(ENTRA_ITEM_TYPES),
        )
    )
    items_b_result = await db.execute(
        select(SnapshotItem).where(
            SnapshotItem.snapshot_id == snapshot_b,
            SnapshotItem.item_type.in_(ENTRA_ITEM_TYPES),
        )
    )

    items_a = {i.ms_item_id: i for i in items_a_result.scalars().all()}
    items_b = {i.ms_item_id: i for i in items_b_result.scalars().all()}

    ids_a = set(items_a.keys())
    ids_b = set(items_b.keys())

    added = ids_b - ids_a  # In B but not A (new objects)
    removed = ids_a - ids_b  # In A but not B (deleted objects)
    common = ids_a & ids_b  # In both

    # Detect changes by comparing content hash
    changed = []
    unchanged = 0
    for item_id in common:
        a = items_a[item_id]
        b = items_b[item_id]
        if a.content_hash != b.content_hash:
            changed.append({
                "ms_item_id": item_id,
                "item_type": b.item_type.value,
                "name": b.name,
                "old_size": a.size_bytes,
                "new_size": b.size_bytes,
                "old_hash": a.content_hash,
                "new_hash": b.content_hash,
            })
        else:
            unchanged += 1

    return {
        "snapshot_a": snapshot_a,
        "snapshot_b": snapshot_b,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": unchanged,
            "total_a": len(items_a),
            "total_b": len(items_b),
        },
        "added": [
            {"ms_item_id": id, "item_type": items_b[id].item_type.value, "name": items_b[id].name}
            for id in added
        ],
        "removed": [
            {"ms_item_id": id, "item_type": items_a[id].item_type.value, "name": items_a[id].name}
            for id in removed
        ],
        "changed": changed,
    }


class EntraRestoreRequest(BaseModel):
    snapshot_id: int
    restore_type: str = "item_level"
    item_ids: list[int] = None


@router.post("/restore")
async def restore_entra_id(
    tenant_id: int = Query(...),
    req: EntraRestoreRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Restore Entra ID objects from a snapshot. Requires ADMIN role.

    Supports: Conditional Access policies, groups, app registrations, named locations.
    Users and directory roles are read-only and will be skipped.
    """
    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.ENTRA_ID,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Entra ID object not found")

    if not req:
        raise HTTPException(status_code=400, detail="Request body required")

    snapshot = await db.get(Snapshot, req.snapshot_id)
    if not snapshot or snapshot.status != SnapshotStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Valid snapshot not found")

    restore_job = RestoreJob(
        tenant_id=obj.tenant_id,
        source_snapshot_id=req.snapshot_id,
        source_object_id=obj.id,
        restore_type=RestoreType(req.restore_type),
        item_ids_json=json.dumps(req.item_ids) if req.item_ids else None,
        status=RestoreStatus.QUEUED,
    )
    db.add(restore_job)
    await db.flush()

    disp_result = await get_dispatcher().dispatch_restore(
        RestoreJobMessage(restore_job_id=restore_job.id), db=db
    )

    return {
        "restore_job_id": restore_job.id,
        "status": disp_result.status or restore_job.status.value,
        "items_restored": restore_job.items_restored,
    }
