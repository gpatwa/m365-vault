"""Job monitoring API routes."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import String, select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backup_job import BackupJob, JobStatus
from app.models.restore_job import RestoreJob, RestoreStatus
from app.models.user import User
from app.services.auth import get_current_user, require_backup_permission, require_restore_permission, require_tenant_access_dep
from app.utils.query import ListParams, apply_sorting, apply_pagination

router = APIRouter(prefix="/api/jobs", tags=["Jobs"], dependencies=[Depends(require_tenant_access_dep())])


@router.get("/backup")
async def list_backup_jobs(
    tenant_id: int = Query(None),
    status: str = Query(None),
    workload_type: str = Query(None),
    params: ListParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List backup jobs with filtering, sorting, search, and pagination."""
    stmt = select(BackupJob)
    if tenant_id:
        stmt = stmt.where(BackupJob.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(BackupJob.status == status)
    if workload_type:
        stmt = stmt.where(BackupJob.workload_type == workload_type)
    if params.search:
        stmt = stmt.where(
            or_(
                BackupJob.workload_type.ilike(f"%{params.search}%"),
                BackupJob.error_message.ilike(f"%{params.search}%"),
                BackupJob.status.cast(String).ilike(f"%{params.search}%"),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    # Sort — default to created_at desc
    stmt = apply_sorting(
        stmt, BackupJob,
        params.sort_by or "created_at",
        params.sort_order if params.sort_by else "desc",
    )
    stmt = apply_pagination(stmt, params.page, params.page_size)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "items": [
            {
                "id": j.id,
                "tenant_id": j.tenant_id,
                "workload_type": j.workload_type,
                "sla_policy_id": j.sla_policy_id,
                "status": j.status.value,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "objects_total": j.objects_total,
                "objects_processed": j.objects_processed,
                "objects_failed": j.objects_failed,
                "total_size_bytes": j.total_size_bytes,
                "total_items": j.total_items,
                "error_message": j.error_message,
                "retry_count": j.retry_count,
                "max_retries": j.max_retries,
                "progress_details": json.loads(j.progress_details) if j.progress_details else None,
            }
            for j in jobs
        ],
    }


@router.get("/restore")
async def list_restore_jobs(
    tenant_id: int = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List restore jobs with filtering."""
    stmt = select(RestoreJob)
    if tenant_id:
        stmt = stmt.where(RestoreJob.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(RestoreJob.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    stmt = stmt.order_by(desc(RestoreJob.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": j.id,
                "tenant_id": j.tenant_id,
                "source_snapshot_id": j.source_snapshot_id,
                "source_object_id": j.source_object_id,
                "restore_type": j.restore_type.value,
                "target_object_id": j.target_object_id,
                "status": j.status.value,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "items_total": j.items_total,
                "items_restored": j.items_restored,
                "items_failed": j.items_failed,
                "error_message": j.error_message,
            }
            for j in jobs
        ],
    }


@router.get("/backup/{job_id}")
async def get_backup_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific backup job."""
    job = await db.get(BackupJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "workload_type": job.workload_type,
        "status": job.status.value,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "objects_total": job.objects_total,
        "objects_processed": job.objects_processed,
        "objects_failed": job.objects_failed,
        "total_size_bytes": job.total_size_bytes,
        "total_items": job.total_items,
        "error_message": job.error_message,
        "progress_details": json.loads(job.progress_details) if job.progress_details else None,
    }


@router.get("/restore/{job_id}")
async def get_restore_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific restore job."""
    job = await db.get(RestoreJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "restore_type": job.restore_type.value,
        "status": job.status.value,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "items_restored": job.items_restored,
        "items_failed": job.items_failed,
        "error_message": job.error_message,
    }


@router.get("/failed-summary")
async def get_failed_jobs_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary of all failed/partial jobs and their retry eligibility."""
    from app.services.retry_engine import RetryEngine
    engine = RetryEngine(db)
    return await engine.get_failed_jobs_summary()


@router.post("/backup/{job_id}/retry")
async def retry_backup_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Manually retry a failed backup job. Requires ADMIN or OPERATOR role."""
    from app.services.retry_engine import RetryEngine
    engine = RetryEngine(db)
    try:
        return await engine.retry_single_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retry-all-failed")
async def retry_all_failed_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Trigger immediate retry of all eligible failed jobs. Requires ADMIN or OPERATOR role."""
    from app.services.retry_engine import RetryEngine
    engine = RetryEngine(db)
    return await engine.process_failed_jobs()


@router.post("/snapshots/{snapshot_id}/retry")
async def retry_failed_snapshot(
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Retry a specific failed snapshot by creating a new backup. Requires ADMIN or OPERATOR role."""
    from app.services.retry_engine import RetryEngine
    engine = RetryEngine(db)
    try:
        return await engine.retry_failed_snapshot(snapshot_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class MassRecoveryRequest(BaseModel):
    tenant_id: int
    object_ids: list[int]
    restore_type: str = "full_inplace"


@router.post("/mass-recovery")
async def mass_recovery(
    req: MassRecoveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Trigger mass recovery for multiple objects. Requires ADMIN role (write access)."""
    from app.services.restore_engine import RestoreEngine
    from app.models.restore_job import RestoreType

    engine = RestoreEngine(db)
    jobs = await engine.mass_recovery(
        tenant_id=req.tenant_id,
        object_ids=req.object_ids,
        restore_type=RestoreType(req.restore_type),
    )
    return {
        "status": "completed",
        "total_jobs": len(jobs),
        "jobs": [
            {"id": j.id, "status": j.status.value, "items_restored": j.items_restored}
            for j in jobs
        ],
    }


@router.get("/snapshots")
async def list_snapshots(
    protected_object_id: int = Query(...),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List snapshots for a specific protected object (unified across all workloads)."""
    from app.models.snapshot import Snapshot, SnapshotStatus

    stmt = select(Snapshot).where(Snapshot.protected_object_id == protected_object_id)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(
        stmt.order_by(desc(Snapshot.started_at)).limit(page_size)
    )
    snapshots = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": s.id,
                "snapshot_type": s.snapshot_type.value,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "item_count": s.item_count,
                "size_bytes": s.size_bytes,
                "items_failed": s.items_failed or 0,
                "items_skipped": s.items_skipped or 0,
            }
            for s in snapshots
        ],
    }
