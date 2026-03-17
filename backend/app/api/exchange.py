"""Exchange API routes — browse, search, and restore mailbox data."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.user import User
from app.services.auth import get_current_user
from app.services.catalog import CatalogService
from app.services.backup_engine import BackupEngine

router = APIRouter(prefix="/api/exchange", tags=["Exchange"])


@router.get("/mailboxes")
async def list_mailboxes(
    tenant_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Exchange mailboxes for a tenant."""
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == tenant_id,
        ProtectedObject.workload_type == WorkloadType.EXCHANGE,
    )
    if search:
        stmt = stmt.where(ProtectedObject.display_name.ilike(f"%{search}%"))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    # Paginate
    stmt = stmt.order_by(ProtectedObject.display_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    mailboxes = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "email": m.email,
                "status": m.status.value,
                "sla_policy_id": m.sla_policy_id,
                "last_backup_at": m.last_backup_at.isoformat() if m.last_backup_at else None,
                "last_backup_status": m.last_backup_status,
                "total_items": m.total_items_backed_up,
                "total_size_bytes": m.total_size_bytes,
            }
            for m in mailboxes
        ],
    }


@router.get("/mailboxes/{mailbox_id}/snapshots")
async def list_snapshots(
    mailbox_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all snapshots for a mailbox."""
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.protected_object_id == mailbox_id)
        .order_by(desc(Snapshot.created_at))
    )
    snapshots = result.scalars().all()
    return [
        {
            "id": s.id,
            "snapshot_type": s.snapshot_type.value,
            "status": s.status.value,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "item_count": s.item_count,
            "size_bytes": s.size_bytes,
        }
        for s in snapshots
    ]


@router.get("/mailboxes/{mailbox_id}/snapshots/{snapshot_id}/browse")
async def browse_snapshot(
    mailbox_id: int,
    snapshot_id: int,
    path: str = Query(None),
    item_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse items within a snapshot."""
    catalog = CatalogService(db)
    it = ItemType(item_type) if item_type else None
    items = await catalog.browse_snapshot(
        snapshot_id=snapshot_id,
        path=path,
        item_type=it,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {"items": items}


@router.get("/search")
async def search_emails(
    tenant_id: int = Query(...),
    query: str = Query(..., min_length=1),
    mailbox_id: int = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search emails across all snapshots."""
    catalog = CatalogService(db)
    results = await catalog.search_emails(
        tenant_id=tenant_id,
        query=query,
        object_id=mailbox_id,
        limit=limit,
    )
    return {"results": results, "total": len(results)}


class RestoreRequest(BaseModel):
    snapshot_id: int
    restore_type: str = "full_inplace"  # full_inplace, item_level, cross_user, export
    item_ids: list[int] = None
    target_object_id: int = None


@router.post("/mailboxes/{mailbox_id}/restore")
async def restore_mailbox(
    mailbox_id: int,
    req: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore Exchange mailbox data."""
    obj = await db.get(ProtectedObject, mailbox_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    snapshot = await db.get(Snapshot, req.snapshot_id)
    if not snapshot or snapshot.status != SnapshotStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Valid snapshot not found")

    restore_job = RestoreJob(
        tenant_id=obj.tenant_id,
        source_snapshot_id=req.snapshot_id,
        source_object_id=mailbox_id,
        restore_type=RestoreType(req.restore_type),
        target_object_id=req.target_object_id,
        item_ids_json=json.dumps(req.item_ids) if req.item_ids else None,
        status=RestoreStatus.QUEUED,
    )
    db.add(restore_job)
    await db.flush()

    # Execute restore in background
    from app.services.restore_engine import RestoreEngine
    engine = RestoreEngine(db)
    await engine.execute_restore(restore_job)

    return {
        "restore_job_id": restore_job.id,
        "status": restore_job.status.value,
        "items_restored": restore_job.items_restored,
    }


@router.post("/mailboxes/{mailbox_id}/backup")
async def trigger_backup(
    mailbox_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a backup for a mailbox."""
    obj = await db.get(ProtectedObject, mailbox_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    engine = BackupEngine(db)
    snapshot = await engine.run_backup_for_object(obj)
    return {
        "snapshot_id": snapshot.id,
        "status": snapshot.status.value,
        "item_count": snapshot.item_count,
        "size_bytes": snapshot.size_bytes,
    }


@router.post("/backup-all")
async def trigger_backup_all(
    tenant_id: int = Query(1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger backup for ALL Exchange mailboxes in a tenant with progress tracking."""
    from app.models.backup_job import BackupJob, JobStatus

    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.EXCHANGE,
        )
    )
    mailboxes = result.scalars().all()

    if not mailboxes:
        raise HTTPException(status_code=404, detail="No Exchange mailboxes found")

    # Create a BackupJob for tracking
    job = BackupJob(
        tenant_id=tenant_id,
        workload_type="exchange",
        status=JobStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        objects_total=len(mailboxes),
    )
    db.add(job)
    await db.flush()

    engine = BackupEngine(db)

    # Initialize progress with all objects as pending
    import json as _json
    progress = {"objects": {}, "summary": {"total": len(mailboxes), "completed": 0, "failed": 0, "in_progress": 0, "pending": len(mailboxes), "total_items": 0, "total_size_bytes": 0}}
    for obj in mailboxes:
        progress["objects"][str(obj.id)] = {
            "name": obj.display_name,
            "email": obj.email,
            "workload": "exchange",
            "status": "pending",
        }
    job.progress_details = _json.dumps(progress)
    await db.commit()

    results = []
    succeeded = 0
    failed = 0

    for obj in mailboxes:
        try:
            snapshot = await engine.run_backup_for_object(obj, job=job)
            results.append({
                "mailbox": obj.display_name,
                "email": obj.email,
                "status": "success",
                "snapshot_id": snapshot.id,
                "item_count": snapshot.item_count,
                "size_bytes": snapshot.size_bytes,
            })
            succeeded += 1
            job.objects_processed += 1
        except Exception as e:
            results.append({
                "mailbox": obj.display_name,
                "email": obj.email,
                "status": "failed",
                "error": str(e),
            })
            failed += 1
            job.objects_failed += 1
        await db.commit()

    # Final job status
    if failed == 0:
        job.status = JobStatus.COMPLETED
    elif succeeded > 0:
        job.status = JobStatus.PARTIAL
    else:
        job.status = JobStatus.FAILED
    job.completed_at = datetime.utcnow()
    await db.commit()

    return {
        "total": len(mailboxes),
        "succeeded": succeeded,
        "failed": failed,
        "job_id": job.id,
        "results": results,
    }
