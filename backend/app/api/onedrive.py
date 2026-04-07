"""OneDrive API routes — browse, search, and restore files."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import KavachIQError, BACKUP_NO_OBJECTS
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.user import User
from app.services.auth import get_current_user, require_backup_permission, require_restore_permission, require_tenant_access_dep
from app.services.catalog import CatalogService
from app.services.resilience import idempotency_store
from app.api.dependencies import get_idempotency_key
from app.interfaces.dispatcher_factory import get_dispatcher
from app.interfaces.job_message import BackupObjectMessage, RestoreJobMessage
from app.utils.query import ListParams, apply_sorting, apply_pagination

router = APIRouter(prefix="/api/onedrive", tags=["OneDrive"], dependencies=[Depends(require_tenant_access_dep())])


@router.get("/accounts")
async def list_accounts(
    tenant_id: int = Query(...),
    params: ListParams = Depends(),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all OneDrive accounts for a tenant with sorting and pagination."""
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == tenant_id,
        ProtectedObject.workload_type == WorkloadType.ONEDRIVE,
    )
    if params.search:
        pattern = f"%{params.search}%"
        stmt = stmt.where(
            ProtectedObject.display_name.ilike(pattern)
            | ProtectedObject.email.ilike(pattern)
        )
    if status:
        stmt = stmt.where(ProtectedObject.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    stmt = apply_sorting(stmt, ProtectedObject, params.sort_by, params.sort_order)
    if not params.sort_by:
        stmt = stmt.order_by(ProtectedObject.display_name)
    stmt = apply_pagination(stmt, params.page, params.page_size)
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
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
                "criticality_score": a.criticality_score,
                "criticality_tier": a.criticality_tier,
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

    result = await get_dispatcher().dispatch_restore(
        RestoreJobMessage(restore_job_id=restore_job.id), db=db
    )

    return {
        "restore_job_id": restore_job.id,
        "status": result.status or restore_job.status.value,
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

    result = await get_dispatcher().dispatch_backup_object(
        BackupObjectMessage(protected_object_id=obj.id), db=db
    )
    if not result.success and result.status != "queued":
        raise HTTPException(status_code=500, detail=result.error or "Backup failed")
    return {
        "snapshot_id": result.snapshot_id,
        "status": result.status,
        "item_count": result.item_count,
        "size_bytes": result.size_bytes,
    }


@router.post("/backup-all")
async def trigger_backup_all(
    tenant_id: int = Query(..., description="Tenant ID to backup"),
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
        objects_processed=0,
        objects_failed=0,
    )
    db.add(job)
    await db.flush()

    import json as _json
    progress = {"objects": {}, "summary": {"total": len(accounts), "completed": 0, "failed": 0, "in_progress": 0, "pending": len(accounts), "total_items": 0, "total_size_bytes": 0}}
    for obj in accounts:
        progress["objects"][str(obj.id)] = {"name": obj.display_name, "email": obj.email, "workload": "onedrive", "status": "pending"}
    job.progress_details = _json.dumps(progress)
    await db.commit()

    dispatcher = get_dispatcher()
    results = []
    succeeded = 0
    failed = 0
    queued_count = 0

    for obj in accounts:
        r = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=obj.id, backup_job_id=job.id), db=db
        )
        if r.status == "queued":
            queued_count += 1
        elif r.success:
            results.append({"account": obj.display_name, "email": obj.email, "status": "success", "snapshot_id": r.snapshot_id, "item_count": r.item_count, "size_bytes": r.size_bytes})
            succeeded += 1
            job.objects_processed += 1
            await db.commit()
        else:
            results.append({"account": obj.display_name, "email": obj.email, "status": "failed", "error": r.error})
            failed += 1
            job.objects_failed += 1
            await db.commit()

    if queued_count:
        job.status = JobStatus.QUEUED
        await db.commit()
        return {"job_id": job.id, "status": "queued", "total": len(accounts)}

    job.status = JobStatus.COMPLETED if failed == 0 else (JobStatus.PARTIAL if succeeded > 0 else JobStatus.FAILED)
    job.completed_at = datetime.utcnow()
    await db.commit()

    return {"total": len(accounts), "succeeded": succeeded, "failed": failed, "job_id": job.id, "results": results}
