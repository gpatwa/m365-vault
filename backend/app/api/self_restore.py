"""Self-Service Restore API — end users restore their own items."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/self-restore", tags=["Self-Service Restore"])


@router.get("/search")
async def search_my_items(
    query: str = Query(..., min_length=2),
    workload: str = Query(None, description="Filter by workload: exchange, onedrive, sharepoint"),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search backed-up items across all workloads.

    For self-service, the user can search their own items.
    Admins can search all items.
    """
    stmt = (
        select(SnapshotItem, Snapshot, ProtectedObject)
        .join(Snapshot, SnapshotItem.snapshot_id == Snapshot.id)
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(
            Snapshot.status == SnapshotStatus.COMPLETED,
            SnapshotItem.name.ilike(f"%{query}%"),
        )
    )

    if workload:
        from app.models.protected_object import WorkloadType
        try:
            wt = WorkloadType(workload)
            stmt = stmt.where(ProtectedObject.workload_type == wt)
        except ValueError:
            pass

    # For non-admin users, filter to their own items
    if current_user.role.value != "admin":
        stmt = stmt.where(ProtectedObject.email == current_user.email)

    # Get latest snapshot per object (avoid duplicates from multiple backups)
    stmt = stmt.order_by(desc(Snapshot.completed_at)).limit(page_size)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    seen = set()  # Deduplicate by ms_item_id
    for item, snapshot, obj in rows:
        if item.ms_item_id in seen:
            continue
        seen.add(item.ms_item_id)

        items.append({
            "id": item.id,
            "snapshot_id": snapshot.id,
            "item_type": item.item_type.value,
            "name": item.name,
            "path": item.path,
            "size_bytes": item.size_bytes,
            "workload": obj.workload_type.value,
            "protected_object": obj.display_name,
            "backed_up_at": snapshot.completed_at.isoformat() if snapshot.completed_at else None,
            # Email-specific
            "subject": item.subject,
            "sender": item.sender,
            "received_at": item.received_at.isoformat() if item.received_at else None,
            # File-specific
            "file_name": item.file_name,
            "mime_type": item.mime_type,
        })

    return {"total": len(items), "query": query, "items": items}


@router.post("/restore")
async def restore_my_item(
    snapshot_id: int = Query(...),
    item_ids: str = Query(..., description="Comma-separated item IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore specific items from a snapshot.

    Creates a RestoreJob for the requested items.
    """
    from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus

    ids = [int(x.strip()) for x in item_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid item IDs provided")

    # Verify snapshot exists
    snapshot = await db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    obj = await db.get(ProtectedObject, snapshot.protected_object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protected object not found")

    # Non-admin/non-restore_operator: verify items belong to user + in-place only
    from app.models.user import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.RESTORE_OPERATOR):
        if obj.email != current_user.email:
            raise HTTPException(status_code=403, detail="You can only restore your own items")

    # Create restore job
    restore_job = RestoreJob(
        tenant_id=obj.tenant_id,
        restore_type=RestoreType.ITEM_LEVEL,
        status=RestoreStatus.QUEUED,
        source_snapshot_id=snapshot.id,
        source_object_id=obj.id,
        item_ids_json=json.dumps(ids),
        initiated_by_user_id=current_user.id,
    )
    db.add(restore_job)
    await db.flush()

    # Audit log
    from app.services.audit import audit_log
    await audit_log(
        db, action="restore.self_service", resource_type="protected_object",
        resource_id=obj.id, user_id=current_user.id,
        details=f"Self-restore: {len(ids)} items from {obj.display_name} by {current_user.email}",
        severity="info",
    )

    # Execute restore
    from app.services.restore_engine import RestoreEngine
    engine = RestoreEngine(db)
    await engine.execute_restore(restore_job)
    await db.commit()

    return {
        "restore_job_id": restore_job.id,
        "status": restore_job.status.value,
        "items_requested": len(ids),
        "items_restored": restore_job.items_restored,
    }
