"""Reports & Analytics API — comprehensive backup reporting and CSV export."""
import csv
import io
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backup_job import BackupJob, JobStatus
from app.models.restore_job import RestoreJob
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotItem, FailedItem, ErrorCategory
from app.models.sla_policy import SLAPolicy
from app.models.health_baseline import AnomalyEvent
from app.models.user import User
from app.services.auth import get_current_user, require_tenant_access_dep

router = APIRouter(prefix="/api/reports", tags=["Reports"], dependencies=[Depends(require_tenant_access_dep())])


def _parse_period(period: str) -> timedelta:
    """Parse period string like '7d', '30d', '90d' into timedelta."""
    try:
        days = int(period.rstrip("d"))
        return timedelta(days=max(1, min(days, 365)))
    except (ValueError, TypeError):
        return timedelta(days=30)


# ── 1. Backup Performance ──

@router.get("/backup-performance")
async def backup_performance(
    period: str = Query("30d"),
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backup performance metrics: success rate, duration, throughput by workload."""
    delta = _parse_period(period)
    since = datetime.utcnow() - delta
    days = int(delta.total_seconds() / 86400)

    filters = [BackupJob.created_at >= since]
    if tenant_id:
        filters.append(BackupJob.tenant_id == tenant_id)

    # Overall stats
    total = (await db.execute(select(func.count(BackupJob.id)).where(*filters))).scalar() or 0
    completed = (await db.execute(select(func.count(BackupJob.id)).where(*filters, BackupJob.status == JobStatus.COMPLETED))).scalar() or 0
    failed = (await db.execute(select(func.count(BackupJob.id)).where(*filters, BackupJob.status == JobStatus.FAILED))).scalar() or 0
    partial = (await db.execute(select(func.count(BackupJob.id)).where(*filters, BackupJob.status == JobStatus.PARTIAL))).scalar() or 0

    # Average duration (completed jobs only)
    avg_duration_result = await db.execute(
        select(func.avg(
            extract("epoch", BackupJob.completed_at) - extract("epoch", BackupJob.started_at)
        )).where(*filters, BackupJob.status == JobStatus.COMPLETED, BackupJob.completed_at.isnot(None))
    )
    avg_duration_sec = round(avg_duration_result.scalar() or 0, 1)

    # Total items and size
    total_items = (await db.execute(select(func.sum(BackupJob.total_items)).where(*filters))).scalar() or 0
    total_size = (await db.execute(select(func.sum(BackupJob.total_size_bytes)).where(*filters))).scalar() or 0

    # By workload
    wl_result = await db.execute(
        select(
            BackupJob.workload_type,
            func.count(BackupJob.id).label("total"),
            func.sum(case((BackupJob.status == JobStatus.COMPLETED, 1), else_=0)).label("completed"),
            func.sum(case((BackupJob.status == JobStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(BackupJob.total_items).label("items"),
            func.sum(BackupJob.total_size_bytes).label("size"),
        ).where(*filters).group_by(BackupJob.workload_type)
    )
    by_workload = {}
    for row in wl_result.all():
        wl = row.workload_type
        wl_total = int(row.total or 0)
        wl_completed = int(row.completed or 0)
        by_workload[wl] = {
            "total": wl_total,
            "completed": wl_completed,
            "failed": int(row.failed or 0),
            "success_rate": round(wl_completed / wl_total * 100, 1) if wl_total > 0 else 0,
            "items": int(row.items or 0),
            "size_bytes": int(row.size or 0),
        }

    # Daily trend
    trend = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - 1 - i)).date()
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())
        day_filters = [BackupJob.created_at >= day_start, BackupJob.created_at <= day_end]
        if tenant_id:
            day_filters.append(BackupJob.tenant_id == tenant_id)

        day_total = (await db.execute(select(func.count(BackupJob.id)).where(*day_filters))).scalar() or 0
        day_completed = (await db.execute(select(func.count(BackupJob.id)).where(*day_filters, BackupJob.status == JobStatus.COMPLETED))).scalar() or 0
        day_failed = (await db.execute(select(func.count(BackupJob.id)).where(*day_filters, BackupJob.status == JobStatus.FAILED))).scalar() or 0

        trend.append({
            "date": date.isoformat(),
            "total": day_total,
            "completed": day_completed,
            "failed": day_failed,
            "success_rate": round(day_completed / day_total * 100, 1) if day_total > 0 else 100,
        })

    return {
        "period": period,
        "summary": {
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "partial": partial,
            "success_rate": round(completed / total * 100, 1) if total > 0 else 100,
            "avg_duration_sec": avg_duration_sec,
            "total_items": total_items,
            "total_size_bytes": total_size,
        },
        "by_workload": by_workload,
        "trend": trend,
    }


# ── 2. Storage Analytics ──

@router.get("/storage-analytics")
async def storage_analytics(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Storage usage, dedup savings, compression ratio, growth trend."""
    from app.models.dedup import DedupEntry

    filters = [Snapshot.status == SnapshotStatus.COMPLETED]
    if tenant_id:
        filters.append(ProtectedObject.tenant_id == tenant_id)

    # Total storage
    if tenant_id:
        size_result = await db.execute(
            select(func.sum(Snapshot.size_bytes), func.count(Snapshot.id))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(*filters)
        )
    else:
        size_result = await db.execute(
            select(func.sum(Snapshot.size_bytes), func.count(Snapshot.id))
            .where(Snapshot.status == SnapshotStatus.COMPLETED)
        )
    row = size_result.one()
    total_size = int(row[0] or 0)
    total_snapshots = int(row[1] or 0)

    # Dedup stats
    dedup_result = await db.execute(
        select(
            func.count(DedupEntry.id),
            func.sum(DedupEntry.size_bytes),
            func.sum(DedupEntry.original_size),
            func.sum(DedupEntry.ref_count),
        )
    )
    dedup_row = dedup_result.one()
    dedup_entries = int(dedup_row[0] or 0)
    compressed_total = int(dedup_row[1] or 0)
    original_total = int(dedup_row[2] or 0)
    total_refs = int(dedup_row[3] or 0)

    dedup_ratio = round(original_total / compressed_total, 2) if compressed_total > 0 else 1.0
    compression_ratio = round(original_total / compressed_total, 2) if compressed_total > 0 else 1.0
    space_saved = max(0, original_total - compressed_total)
    space_saved_pct = round(space_saved / original_total * 100, 1) if original_total > 0 else 0

    # By workload
    wl_result = await db.execute(
        select(
            ProtectedObject.workload_type,
            func.sum(Snapshot.size_bytes).label("size"),
            func.count(Snapshot.id).label("snapshots"),
        )
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(Snapshot.status == SnapshotStatus.COMPLETED)
        .group_by(ProtectedObject.workload_type)
    )
    by_workload = {}
    for row in wl_result.all():
        wl = row.workload_type.value if hasattr(row.workload_type, 'value') else str(row.workload_type)
        by_workload[wl] = {"size_bytes": int(row.size or 0), "snapshots": int(row.snapshots or 0)}

    # Growth trend (daily for last 30 days)
    growth = []
    for i in range(30):
        date = (datetime.utcnow() - timedelta(days=29 - i)).date()
        day_end = datetime.combine(date, datetime.max.time())
        cumulative = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .where(Snapshot.status == SnapshotStatus.COMPLETED, Snapshot.created_at <= day_end)
        )).scalar() or 0
        growth.append({"date": date.isoformat(), "cumulative_bytes": int(cumulative)})

    # Cost projection ($0.02/GB/month for Azure Blob)
    size_gb = total_size / (1024 ** 3)
    monthly_cost = round(size_gb * 0.02, 2)

    return {
        "total_size_bytes": total_size,
        "total_size_gb": round(size_gb, 2),
        "total_snapshots": total_snapshots,
        "dedup": {
            "entries": dedup_entries,
            "ratio": dedup_ratio,
            "space_saved_bytes": space_saved,
            "space_saved_pct": space_saved_pct,
            "total_references": total_refs,
        },
        "compression_ratio": compression_ratio,
        "by_workload": by_workload,
        "growth_trend": growth,
        "cost_projection": {
            "monthly_storage_cost": monthly_cost,
            "annual_storage_cost": round(monthly_cost * 12, 2),
            "cost_per_gb_month": 0.02,
        },
    }


# ── 3. Failure Analysis ──

@router.get("/failure-analysis")
async def failure_analysis(
    period: str = Query("30d"),
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Failed items by category, workload, resolution rate, MTTR."""
    delta = _parse_period(period)
    since = datetime.utcnow() - delta

    # Total failed items
    total_count = (await db.execute(
        select(func.count(FailedItem.id)).where(FailedItem.created_at >= since)
    )).scalar() or 0

    resolved_count = (await db.execute(
        select(func.count(FailedItem.id)).where(
            FailedItem.created_at >= since, FailedItem.is_resolved == True
        )
    )).scalar() or 0

    resolution_rate = round(resolved_count / total_count * 100, 1) if total_count > 0 else 100

    # By error category
    cat_result = await db.execute(
        select(FailedItem.error_category, func.count(FailedItem.id))
        .where(FailedItem.created_at >= since)
        .group_by(FailedItem.error_category)
        .order_by(func.count(FailedItem.id).desc())
    )
    by_category = {row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1] for row in cat_result.all()}

    # By workload
    wl_result = await db.execute(
        select(ProtectedObject.workload_type, func.count(FailedItem.id))
        .join(ProtectedObject, FailedItem.protected_object_id == ProtectedObject.id)
        .where(FailedItem.created_at >= since)
        .group_by(ProtectedObject.workload_type)
    )
    by_workload = {row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1] for row in wl_result.all()}

    # Failed jobs trend
    days = int(delta.total_seconds() / 86400)
    trend = []
    for i in range(min(days, 30)):
        date = (datetime.utcnow() - timedelta(days=min(days, 30) - 1 - i)).date()
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())
        count = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.created_at >= day_start, BackupJob.created_at <= day_end,
                BackupJob.status.in_([JobStatus.FAILED, JobStatus.PARTIAL]),
            )
        )).scalar() or 0
        trend.append({"date": date.isoformat(), "failed_jobs": count})

    return {
        "period": period,
        "total_failed_items": total_count,
        "resolved": resolved_count,
        "unresolved": total_count - resolved_count,
        "resolution_rate": resolution_rate,
        "by_category": by_category,
        "by_workload": by_workload,
        "trend": trend,
    }


# ── 4. SLA Compliance ──

@router.get("/sla-compliance")
async def sla_compliance(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SLA compliance: adherence %, violations, per-policy breakdown."""
    stmt = select(ProtectedObject, SLAPolicy).join(
        SLAPolicy, ProtectedObject.sla_policy_id == SLAPolicy.id
    ).where(ProtectedObject.status == ProtectionStatus.PROTECTED)
    if tenant_id:
        stmt = stmt.where(ProtectedObject.tenant_id == tenant_id)

    result = await db.execute(stmt)
    rows = result.all()

    compliant = 0
    non_compliant = 0
    by_policy = {}
    violations = []

    for obj, sla in rows:
        policy_name = sla.name
        if policy_name not in by_policy:
            by_policy[policy_name] = {"total": 0, "compliant": 0, "non_compliant": 0, "frequency_hours": sla.backup_frequency_hours, "retention_days": sla.retention_days}

        by_policy[policy_name]["total"] += 1

        if obj.last_backup_at:
            expected_next = obj.last_backup_at + timedelta(hours=sla.backup_frequency_hours)
            is_compliant = datetime.utcnow() <= expected_next
        else:
            grace = obj.created_at + timedelta(hours=sla.backup_frequency_hours)
            is_compliant = datetime.utcnow() <= grace

        if is_compliant:
            compliant += 1
            by_policy[policy_name]["compliant"] += 1
        else:
            non_compliant += 1
            by_policy[policy_name]["non_compliant"] += 1
            violations.append({
                "object": obj.display_name,
                "workload": obj.workload_type.value,
                "policy": sla.name,
                "last_backup": obj.last_backup_at.isoformat() if obj.last_backup_at else "Never",
                "hours_overdue": round((datetime.utcnow() - (obj.last_backup_at or obj.created_at)).total_seconds() / 3600, 1),
            })

    total = compliant + non_compliant
    # Add compliance_rate to each policy
    for pn, pd in by_policy.items():
        pd["compliance_rate"] = round(pd["compliant"] / pd["total"] * 100, 1) if pd["total"] > 0 else 100

    return {
        "total_protected": total,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "compliance_rate": round(compliant / total * 100, 1) if total > 0 else 100,
        "by_policy": by_policy,
        "violations": sorted(violations, key=lambda v: v["hours_overdue"], reverse=True)[:20],
    }


# ── 5. Security Summary ──

@router.get("/security-summary")
async def security_summary(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Security overview: sensitive data, malware scans, WORM status, anomalies."""
    # Sensitive data findings (from snapshot items metadata)
    sensitive_items = (await db.execute(
        select(func.count(SnapshotItem.id)).where(
            SnapshotItem.metadata_json.like('%sensitive_data%')
        )
    )).scalar() or 0

    # WORM status
    worm_policies = (await db.execute(
        select(func.count(SLAPolicy.id)).where(SLAPolicy.worm_enabled == 1)
    )).scalar() or 0

    legal_hold_policies = (await db.execute(
        select(func.count(SLAPolicy.id)).where(SLAPolicy.legal_hold == 1)
    )).scalar() or 0

    locked_snapshots = (await db.execute(
        select(func.count(Snapshot.id)).where(
            Snapshot.locked_until.isnot(None),
            Snapshot.locked_until > datetime.utcnow(),
        )
    )).scalar() or 0

    # Malware scan results
    from app.models.restore_job import RestoreJob
    scanned_restores = (await db.execute(
        select(func.count(RestoreJob.id)).where(RestoreJob.scan_status.isnot(None))
    )).scalar() or 0

    blocked_restores = (await db.execute(
        select(func.count(RestoreJob.id)).where(RestoreJob.scan_status == "blocked")
    )).scalar() or 0

    # Active anomalies
    active_anomalies = (await db.execute(
        select(func.count(AnomalyEvent.id)).where(AnomalyEvent.resolved == 0)
    )).scalar() or 0

    critical_anomalies = (await db.execute(
        select(func.count(AnomalyEvent.id)).where(AnomalyEvent.resolved == 0, AnomalyEvent.severity == "critical")
    )).scalar() or 0

    return {
        "sensitive_data": {"flagged_items": sensitive_items},
        "worm": {
            "policies_enabled": worm_policies,
            "legal_hold_policies": legal_hold_policies,
            "locked_snapshots": locked_snapshots,
        },
        "malware_scans": {
            "total_scanned": scanned_restores,
            "blocked": blocked_restores,
            "clean": scanned_restores - blocked_restores,
        },
        "anomalies": {
            "active": active_anomalies,
            "critical": critical_anomalies,
        },
    }


# ── 6. CSV/JSON Export ──

@router.get("/export")
async def export_report(
    report: str = Query(..., description="Report name: backup-performance, storage-analytics, failure-analysis, sla-compliance"),
    format: str = Query("csv", description="Export format: csv or json"),
    period: str = Query("30d"),
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export report data as CSV or JSON download."""
    # Fetch the report data
    if report == "backup-performance":
        data = await backup_performance(period=period, tenant_id=tenant_id, db=db, current_user=current_user)
        rows = data["trend"]
        filename = f"backup_performance_{period}"
    elif report == "storage-analytics":
        data = await storage_analytics(tenant_id=tenant_id, db=db, current_user=current_user)
        rows = data["growth_trend"]
        filename = "storage_analytics"
    elif report == "failure-analysis":
        data = await failure_analysis(period=period, tenant_id=tenant_id, db=db, current_user=current_user)
        rows = data["trend"]
        filename = f"failure_analysis_{period}"
    elif report == "sla-compliance":
        data = await sla_compliance(tenant_id=tenant_id, db=db, current_user=current_user)
        rows = data["violations"]
        filename = "sla_compliance"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report: {report}. Available: backup-performance, storage-analytics, failure-analysis, sla-compliance")

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(data, indent=2, default=str).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )

    # CSV
    if not rows:
        return StreamingResponse(
            io.BytesIO(b"No data\n"),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
    )
