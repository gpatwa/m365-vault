"""Dashboard API routes — overview stats and charts."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.backup_job import BackupJob, JobStatus
from app.models.restore_job import RestoreJob, RestoreStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.user import User
from app.services.auth import get_current_user
from app.services.storage import storage_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_summary(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard summary statistics for the user's accessible tenants."""
    from app.services.auth import resolve_tenant_filter

    # Resolve tenant scope: provided tenant_id OR user's assigned tenants OR [-1] (nothing)
    allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)
    tenant_count = len([t for t in allowed_ids if t > 0])

    # Get enabled workloads across user's tenants — only show workloads that are opted-in
    from app.services.workload_lifecycle import get_enabled_workloads
    all_enabled_workloads = set()
    for tid in [t for t in allowed_ids if t > 0]:
        enabled = await get_enabled_workloads(db, tid)
        all_enabled_workloads.update(enabled)

    # Map workload keys to WorkloadType enum values for filtering
    _workload_key_to_enum = {
        "exchange": WorkloadType.EXCHANGE,
        "onedrive": WorkloadType.ONEDRIVE,
        "sharepoint": WorkloadType.SHAREPOINT,
        "teams": WorkloadType.TEAMS,
        "entra_id": WorkloadType.ENTRA_ID,
    }

    # Protection stats by workload — only count ENABLED+ workloads
    # If no workloads enabled (new install), fall back to showing all (backward compat)
    workload_types_to_show = (
        [_workload_key_to_enum[k] for k in all_enabled_workloads if k in _workload_key_to_enum]
        if all_enabled_workloads
        else list(WorkloadType)
    )

    workload_stats = {}
    for wt in workload_types_to_show:
        stmt = select(ProtectedObject).where(ProtectedObject.workload_type == wt)
        stmt = stmt.where(ProtectedObject.tenant_id.in_(allowed_ids))

        total = (await db.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar()

        protected = (await db.execute(
            select(func.count()).select_from(
                stmt.where(ProtectedObject.status == ProtectionStatus.PROTECTED).subquery()
            )
        )).scalar()

        # Get last backup and total items for this workload
        last_backup_result = await db.execute(
            select(func.max(ProtectedObject.last_backup_at)).where(
                stmt.whereclause if hasattr(stmt, 'whereclause') else True,
                ProtectedObject.workload_type == wt,
            )
        )
        last_backup = last_backup_result.scalar()

        total_items_result = await db.execute(
            select(func.sum(ProtectedObject.total_items_backed_up)).where(
                ProtectedObject.workload_type == wt,
                ProtectedObject.tenant_id.in_(allowed_ids),
            )
        )
        total_items = total_items_result.scalar() or 0

        workload_stats[wt.value] = {
            "total": total,
            "protected": protected,
            "unprotected": total - protected,
            "protection_rate": round(protected / total * 100, 1) if total > 0 else 0,
            "last_backup": last_backup.isoformat() if last_backup else None,
            "item_count": total_items,
        }

    # Total protected objects
    total_protected = sum(ws["protected"] for ws in workload_stats.values())
    total_objects = sum(ws["total"] for ws in workload_stats.values())

    # Recent job stats (last 24h)
    since_24h = datetime.utcnow() - timedelta(hours=24)

    # Exclude internal states (dead_letter, cancelled) from customer-facing counts
    customer_visible = [JobStatus.QUEUED, JobStatus.IN_PROGRESS, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL]

    backup_jobs_24h = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.created_at >= since_24h,
            BackupJob.tenant_id.in_(allowed_ids),
            BackupJob.status.in_(customer_visible),
        )
    )).scalar()

    successful_backups_24h = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.created_at >= since_24h,
            BackupJob.status == JobStatus.COMPLETED,
            BackupJob.tenant_id.in_(allowed_ids),
        )
    )).scalar()

    failed_backups_24h = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.created_at >= since_24h,
            BackupJob.status == JobStatus.FAILED,
            BackupJob.tenant_id.in_(allowed_ids),
        )
    )).scalar()

    restore_jobs_24h = (await db.execute(
        select(func.count(RestoreJob.id)).where(RestoreJob.created_at >= since_24h, RestoreJob.tenant_id.in_(allowed_ids))
    )).scalar()

    # Snapshot stats — scoped to user's tenants via protected_object → tenant
    total_snapshots = (await db.execute(
        select(func.count(Snapshot.id))
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(Snapshot.status == SnapshotStatus.COMPLETED, ProtectedObject.tenant_id.in_(allowed_ids))
    )).scalar()

    total_backup_size = (await db.execute(
        select(func.sum(Snapshot.size_bytes))
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(Snapshot.status == SnapshotStatus.COMPLETED, ProtectedObject.tenant_id.in_(allowed_ids))
    )).scalar() or 0

    # Storage stats
    storage_stats = storage_service.get_storage_stats()

    return {
        "tenants": tenant_count,
        "total_objects": total_objects,
        "total_protected": total_protected,
        "protection_rate": round(total_protected / total_objects * 100, 1) if total_objects > 0 else 0,
        "workloads": workload_stats,
        "jobs_24h": {
            "backup_total": backup_jobs_24h,
            "backup_successful": successful_backups_24h,
            "backup_failed": failed_backups_24h,
            "restore_total": restore_jobs_24h,
        },
        "snapshots": {
            "total": total_snapshots,
            "total_size_bytes": total_backup_size,
            "total_size_gb": round(total_backup_size / (1024**3), 2),
        },
        "storage": storage_stats,
    }


@router.get("/activity")
async def get_activity(
    tenant_id: int = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get backup/restore activity over time for charts."""
    from app.services.auth import resolve_tenant_filter
    allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)

    activity = []

    for i in range(days):
        date = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())

        # Backup jobs for this day — scoped to user's tenants
        backup_count = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.created_at >= day_start,
                BackupJob.created_at <= day_end,
                BackupJob.tenant_id.in_(allowed_ids),
            )
        )).scalar()

        backup_success = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.created_at >= day_start,
                BackupJob.created_at <= day_end,
                BackupJob.status == JobStatus.COMPLETED,
                BackupJob.tenant_id.in_(allowed_ids),
            )
        )).scalar()

        # Restore jobs for this day
        restore_count = (await db.execute(
            select(func.count(RestoreJob.id)).where(
                RestoreJob.created_at >= day_start,
                RestoreJob.created_at <= day_end,
                RestoreJob.tenant_id.in_(allowed_ids),
            )
        )).scalar()

        # Data backed up this day
        data_size = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                Snapshot.created_at >= day_start,
                Snapshot.created_at <= day_end,
                Snapshot.status == SnapshotStatus.COMPLETED,
                ProtectedObject.tenant_id.in_(allowed_ids),
            )
        )).scalar() or 0

        activity.append({
            "date": date.isoformat(),
            "backups": backup_count,
            "backups_successful": backup_success,
            "restores": restore_count,
            "data_backed_up_bytes": data_size,
        })

    activity.reverse()
    return {"activity": activity}


@router.get("/compliance")
async def get_compliance(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get SLA compliance status."""
    from app.models.sla_policy import SLAPolicy
    from app.services.auth import resolve_tenant_filter
    allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)

    stmt = select(ProtectedObject, SLAPolicy).join(
        SLAPolicy, ProtectedObject.sla_policy_id == SLAPolicy.id
    ).where(ProtectedObject.status == ProtectionStatus.PROTECTED)

    stmt = stmt.where(ProtectedObject.tenant_id.in_(allowed_ids))

    result = await db.execute(stmt)
    rows = result.all()

    compliant = 0
    non_compliant = 0
    pending_first_backup = 0
    details = []

    for obj, sla in rows:
        if obj.last_backup_at:
            expected_next = obj.last_backup_at + timedelta(hours=sla.backup_frequency_hours)
            is_compliant = datetime.utcnow() <= expected_next
        else:
            # Object has never been successfully backed up.
            # If it was recently assigned (created within one SLA cycle), treat as
            # "pending first backup" rather than a violation — the scheduler hasn't
            # had a full cycle yet.
            grace_window = obj.created_at + timedelta(hours=sla.backup_frequency_hours)
            if datetime.utcnow() <= grace_window:
                # Still within the first SLA window — pending, not a violation
                pending_first_backup += 1
                compliant += 1
                continue
            else:
                is_compliant = False

        if is_compliant:
            compliant += 1
        else:
            non_compliant += 1
            reason = "overdue"
            if obj.last_backup_at is None and obj.last_backup_status == "failed":
                reason = "initial_backup_failed"
            elif obj.last_backup_at is None:
                reason = "never_backed_up"

            details.append({
                "object_name": obj.display_name,
                "workload": obj.workload_type.value,
                "sla_name": sla.name,
                "last_backup": obj.last_backup_at.isoformat() if obj.last_backup_at else "Never",
                "last_backup_status": obj.last_backup_status,
                "frequency_hours": sla.backup_frequency_hours,
                "reason": reason,
            })

    total = compliant + non_compliant
    return {
        "total": total,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "pending_first_backup": pending_first_backup,
        "compliance_rate": round(compliant / total * 100, 1) if total > 0 else 100,
        "violations": details[:20],  # Top 20 violations
    }


@router.get("/unprotected")
async def get_unprotected_items(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all unprotected items grouped by workload, with at-risk details."""
    from app.services.auth import resolve_tenant_filter
    allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)

    # Unprotected objects: no SLA assigned OR status is not PROTECTED
    stmt = select(ProtectedObject).where(
        or_(
            ProtectedObject.status != ProtectionStatus.PROTECTED,
            ProtectedObject.sla_policy_id.is_(None),
        )
    )
    stmt = stmt.where(ProtectedObject.tenant_id.in_(allowed_ids))

    stmt = stmt.order_by(ProtectedObject.workload_type, ProtectedObject.display_name)
    result = await db.execute(stmt)
    unprotected = result.scalars().all()

    # Also find protected objects whose last backup failed
    failed_stmt = select(ProtectedObject).where(
        ProtectedObject.status == ProtectionStatus.PROTECTED,
        ProtectedObject.last_backup_status == "failed",
    )
    failed_stmt = failed_stmt.where(ProtectedObject.tenant_id.in_(allowed_ids))

    failed_result = await db.execute(failed_stmt)
    at_risk = failed_result.scalars().all()

    # Group by workload
    by_workload: dict = {}
    for obj in unprotected:
        wl = obj.workload_type.value if hasattr(obj.workload_type, 'value') else str(obj.workload_type)
        if wl not in by_workload:
            by_workload[wl] = {"unprotected": [], "at_risk": []}
        by_workload[wl]["unprotected"].append(_serialize_object(obj))

    for obj in at_risk:
        wl = obj.workload_type.value if hasattr(obj.workload_type, 'value') else str(obj.workload_type)
        if wl not in by_workload:
            by_workload[wl] = {"unprotected": [], "at_risk": []}
        by_workload[wl]["at_risk"].append(_serialize_object(obj))

    return {
        "total_unprotected": len(unprotected),
        "total_at_risk": len(at_risk),
        "by_workload": by_workload,
        "items": [_serialize_object(o) for o in unprotected],
        "at_risk_items": [_serialize_object(o) for o in at_risk],
    }


def _serialize_object(obj: ProtectedObject) -> dict:
    return {
        "id": obj.id,
        "display_name": obj.display_name,
        "workload_type": obj.workload_type.value if hasattr(obj.workload_type, 'value') else str(obj.workload_type),
        "email": obj.email,
        "site_url": obj.site_url,
        "status": obj.status.value if hasattr(obj.status, 'value') else str(obj.status),
        "sla_policy_id": obj.sla_policy_id,
        "last_backup_at": obj.last_backup_at.isoformat() if obj.last_backup_at else None,
        "last_backup_status": obj.last_backup_status,
        "total_items_backed_up": obj.total_items_backed_up,
        "total_size_bytes": obj.total_size_bytes,
    }
