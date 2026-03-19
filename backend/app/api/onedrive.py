"""OneDrive API routes — browse, search, and restore files."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.user import User
from app.services.auth import get_current_user, require_backup_permission, require_restore_permission
from app.services.catalog import CatalogService
from app.services.backup_engine import BackupEngine

router = APIRouter(prefix="/api/onedrive", tags=["OneDrive"])


@router.get("/accounts")
async def list_accounts(
    tenant_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all OneDrive accounts for a tenant."""
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == tenant_id,
        ProtectedObject.workload_type == WorkloadType.ONEDRIVE,
    )
    if search:
        stmt = stmt.where(ProtectedObject.display_name.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    stmt = stmt.order_by(ProtectedObject.display_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": a.id,
                "display_name": a.display_name,
                "email": a.email,
                "status": a.status.value,
                "sla_policy_id": a.sla_policy_id,
                "last_backup_at": a.last_backup_at.isoformat() if a.last_backup_at else None,
                "last_backup_status": a.last_backup_status,
                "total_items": a.total_items_backed_up,
                "total_size_bytes": a.total_size_bytes,
            }
            for a in accounts
        ],
    }


@router.get("/accounts/{account_id}/snapshots")
async def list_snapshots(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all snapshots for a OneDrive account."""
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.protected_object_id == account_id)
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


@router.get("/accounts/{account_id}/snapshots/{snapshot_id}/browse")
async def browse_snapshot(
    account_id: int,
    snapshot_id: int,
    path: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse files/folders within a OneDrive snapshot."""
    catalog = CatalogService(db)
    items = await catalog.browse_snapshot(
        snapshot_id=snapshot_id,
        path=path,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {"items": items}


@router.get("/search")
async def search_files(
    tenant_id: int = Query(...),
    query: str = Query(..., min_length=1),
    account_id: int = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search files across all OneDrive snapshots."""
    catalog = CatalogService(db)
    results = await catalog.search_files(
        tenant_id=tenant_id,
        query=query,
        workload_type=WorkloadType.ONEDRIVE,
        object_id=account_id,
        limit=limit,
    )
    return {"results": results, "total": len(results)}


class RestoreRequest(BaseModel):
    snapshot_id: int
    restore_type: str = "full_inplace"
    item_ids: list[int] = None
    target_object_id: int = None


@router.post("/accounts/{account_id}/restore")
async def restore_account(
    account_id: int,
    req: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Restore OneDrive data. Requires ADMIN role (write access)."""
    obj = await db.get(ProtectedObject, account_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Account not found")

    snapshot = await db.get(Snapshot, req.snapshot_id)
    if not snapshot or snapshot.status != SnapshotStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Valid snapshot not found")

    restore_job = RestoreJob(
        tenant_id=obj.tenant_id,
        source_snapshot_id=req.snapshot_id,
        source_object_id=account_id,
        restore_type=RestoreType(req.restore_type),
        target_object_id=req.target_object_id,
        item_ids_json=json.dumps(req.item_ids) if req.item_ids else None,
        status=RestoreStatus.QUEUED,
    )
    db.add(restore_job)
    await db.flush()

    from app.services.restore_engine import RestoreEngine
    engine = RestoreEngine(db)
    await engine.execute_restore(restore_job)

    return {
        "restore_job_id": restore_job.id,
        "status": restore_job.status.value,
        "items_restored": restore_job.items_restored,
    }


@router.post("/accounts/{account_id}/backup")
async def trigger_backup(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Manually trigger a backup for a OneDrive account. Requires ADMIN or OPERATOR role."""
    obj = await db.get(ProtectedObject, account_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Account not found")

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
    current_user: User = Depends(require_backup_permission),
):
    """Trigger backup for ALL OneDrive accounts in a tenant. Requires ADMIN or OPERATOR role."""
    from app.models.backup_job import BackupJob, JobStatus

    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.ONEDRIVE,
            ProtectedObject.status != ProtectionStatus.ERROR,
        )
    )
    accounts = result.scalars().all()

    if not accounts:
        raise HTTPException(status_code=404, detail="No active OneDrive accounts found")

    job = BackupJob(
        tenant_id=tenant_id,
        workload_type="onedrive",
        status=JobStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        objects_total=len(accounts),
    )
    db.add(job)
    await db.flush()

    engine = BackupEngine(db)

    import json as _json
    progress = {"objects": {}, "summary": {"total": len(accounts), "completed": 0, "failed": 0, "in_progress": 0, "pending": len(accounts), "total_items": 0, "total_size_bytes": 0}}
    for obj in accounts:
        progress["objects"][str(obj.id)] = {"name": obj.display_name, "email": obj.email, "workload": "onedrive", "status": "pending"}
    job.progress_details = _json.dumps(progress)
    await db.commit()

    results = []
    succeeded = 0
    failed = 0

    # Cache object names before the loop (session may be invalidated on error)
    obj_names = {obj.id: (obj.display_name, obj.email) for obj in accounts}

    for obj in accounts:
        try:
            snapshot = await engine.run_backup_for_object(obj, job=job)
            results.append({"account": obj.display_name, "email": obj.email, "status": "success", "snapshot_id": snapshot.id, "item_count": snapshot.item_count, "size_bytes": snapshot.size_bytes})
            succeeded += 1
            job.objects_processed += 1
        except Exception as e:
            await db.rollback()
            name, email = obj_names.get(obj.id, (str(obj.id), ''))
            results.append({"account": name, "email": email, "status": "failed", "error": str(e)[:500]})
            failed += 1
            job.objects_failed += 1
        await db.commit()

    job.status = JobStatus.COMPLETED if failed == 0 else (JobStatus.PARTIAL if succeeded > 0 else JobStatus.FAILED)
    job.completed_at = datetime.utcnow()
    await db.commit()

    return {"total": len(accounts), "succeeded": succeeded, "failed": failed, "job_id": job.id, "results": results}
