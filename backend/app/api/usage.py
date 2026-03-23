"""Usage & License Tracking API — tenant usage, platform metrics, license enforcement."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.backup_job import BackupJob, JobStatus
from app.models.restore_job import RestoreJob
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.sla_policy import SLAPolicy
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/usage", tags=["Usage & License"])

# License tier limits
LICENSE_TIERS = {
    "community": {
        "label": "Community (Free)",
        "max_protected_objects": 25,
        "max_tenants": 1,
        "max_workloads": 3,
        "features": ["exchange", "onedrive", "sharepoint"],
        "smart_engine": "basic",
        "support": "community",
    },
    "professional": {
        "label": "Professional ($1.50/user/mo)",
        "max_protected_objects": None,  # unlimited
        "max_tenants": 10,
        "max_workloads": 5,
        "features": ["exchange", "onedrive", "sharepoint", "teams", "entra_id"],
        "smart_engine": "full",
        "support": "email",
    },
    "enterprise": {
        "label": "Enterprise ($3.00/user/mo)",
        "max_protected_objects": None,
        "max_tenants": None,
        "max_workloads": None,
        "features": ["exchange", "onedrive", "sharepoint", "teams", "entra_id", "power_platform"],
        "smart_engine": "full_custom",
        "support": "priority",
    },
}


@router.get("/tenant/{tenant_id}")
async def tenant_usage(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-tenant usage metrics."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    since_30d = datetime.utcnow() - timedelta(days=30)

    # Protected objects count
    protected_count = (await db.execute(
        select(func.count(ProtectedObject.id)).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )).scalar() or 0

    total_objects = (await db.execute(
        select(func.count(ProtectedObject.id)).where(ProtectedObject.tenant_id == tenant_id)
    )).scalar() or 0

    # Storage consumed
    storage_bytes = (await db.execute(
        select(func.sum(Snapshot.size_bytes))
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(ProtectedObject.tenant_id == tenant_id, Snapshot.status == SnapshotStatus.COMPLETED)
    )).scalar() or 0

    # Jobs in last 30 days
    backup_jobs = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.tenant_id == tenant_id, BackupJob.created_at >= since_30d
        )
    )).scalar() or 0

    restore_jobs = (await db.execute(
        select(func.count(RestoreJob.id)).where(
            RestoreJob.tenant_id == tenant_id, RestoreJob.created_at >= since_30d
        )
    )).scalar() or 0

    # Active workloads
    wl_result = await db.execute(
        select(distinct(ProtectedObject.workload_type)).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )
    active_workloads = [row[0].value for row in wl_result.all()]

    # Features used
    features_used = []
    if active_workloads:
        features_used.append("backup")
    if restore_jobs > 0:
        features_used.append("restore")

    worm_count = (await db.execute(
        select(func.count(SLAPolicy.id)).where(SLAPolicy.worm_enabled == 1)
    )).scalar() or 0
    if worm_count > 0:
        features_used.append("worm")

    # Per-workload breakdown
    wl_breakdown = {}
    for wl in WorkloadType:
        count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wl,
            )
        )).scalar() or 0
        if count > 0:
            wl_breakdown[wl.value] = count

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.name,
        "status": tenant.status.value,
        "protected_objects": protected_count,
        "total_objects": total_objects,
        "storage_bytes": storage_bytes,
        "storage_gb": round(storage_bytes / (1024 ** 3), 3),
        "backup_jobs_30d": backup_jobs,
        "restore_jobs_30d": restore_jobs,
        "active_workloads": active_workloads,
        "workload_count": len(active_workloads),
        "features_used": features_used,
        "by_workload": wl_breakdown,
        "last_discovery": tenant.last_discovery_at.isoformat() if tenant.last_discovery_at else None,
        "last_active": tenant.updated_at.isoformat() if tenant.updated_at else None,
    }


@router.get("/platform")
async def platform_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Platform-wide usage summary."""
    total_tenants = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.status == TenantStatus.ACTIVE)
    )).scalar() or 0

    total_users = (await db.execute(
        select(func.count(ProtectedObject.id)).where(
            ProtectedObject.status == ProtectionStatus.PROTECTED
        )
    )).scalar() or 0

    total_storage = (await db.execute(
        select(func.sum(Snapshot.size_bytes)).where(Snapshot.status == SnapshotStatus.COMPLETED)
    )).scalar() or 0

    total_snapshots = (await db.execute(
        select(func.count(Snapshot.id)).where(Snapshot.status == SnapshotStatus.COMPLETED)
    )).scalar() or 0

    since_30d = datetime.utcnow() - timedelta(days=30)
    jobs_30d = (await db.execute(
        select(func.count(BackupJob.id)).where(BackupJob.created_at >= since_30d)
    )).scalar() or 0

    # Active workloads platform-wide
    wl_result = await db.execute(
        select(distinct(ProtectedObject.workload_type)).where(
            ProtectedObject.status == ProtectionStatus.PROTECTED
        )
    )
    active_workloads = [row[0].value for row in wl_result.all()]

    # Cost estimate
    storage_gb = total_storage / (1024 ** 3)
    infra_cost = 65 + (storage_gb * 0.02)  # Base $65 + $0.02/GB storage

    return {
        "total_tenants": total_tenants,
        "total_protected_users": total_users,
        "total_storage_bytes": total_storage,
        "total_storage_gb": round(storage_gb, 2),
        "total_snapshots": total_snapshots,
        "backup_jobs_30d": jobs_30d,
        "active_workloads": active_workloads,
        "workload_count": len(active_workloads),
        "estimated_monthly_cost": round(infra_cost, 2),
        "cost_per_user": round(infra_cost / total_users, 2) if total_users > 0 else 0,
    }


@router.get("/license")
async def license_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Current license tier, usage vs limits, alerts."""
    tier_name = settings.LICENSE_TIER
    tier = LICENSE_TIERS.get(tier_name, LICENSE_TIERS["community"])

    # Current usage
    total_protected = (await db.execute(
        select(func.count(ProtectedObject.id)).where(ProtectedObject.status == ProtectionStatus.PROTECTED)
    )).scalar() or 0

    total_tenants = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.status == TenantStatus.ACTIVE)
    )).scalar() or 0

    wl_result = await db.execute(
        select(distinct(ProtectedObject.workload_type)).where(ProtectedObject.status == ProtectionStatus.PROTECTED)
    )
    active_workloads = len(wl_result.all())

    # Calculate usage percentages
    dimensions = []

    # Protected objects
    max_obj = tier["max_protected_objects"]
    obj_pct = round(total_protected / max_obj * 100, 1) if max_obj else 0
    dimensions.append({
        "name": "Protected Objects",
        "current": total_protected,
        "limit": max_obj or "Unlimited",
        "usage_percent": obj_pct if max_obj else 0,
        "exceeded": total_protected > max_obj if max_obj else False,
        "approaching": obj_pct >= 80 if max_obj else False,
    })

    # Tenants
    max_tenants = tier["max_tenants"]
    tenant_pct = round(total_tenants / max_tenants * 100, 1) if max_tenants else 0
    dimensions.append({
        "name": "Tenants",
        "current": total_tenants,
        "limit": max_tenants or "Unlimited",
        "usage_percent": tenant_pct if max_tenants else 0,
        "exceeded": total_tenants > max_tenants if max_tenants else False,
        "approaching": tenant_pct >= 80 if max_tenants else False,
    })

    # Workloads
    max_wl = tier["max_workloads"]
    wl_pct = round(active_workloads / max_wl * 100, 1) if max_wl else 0
    dimensions.append({
        "name": "Workloads",
        "current": active_workloads,
        "limit": max_wl or "Unlimited",
        "usage_percent": wl_pct if max_wl else 0,
        "exceeded": active_workloads > max_wl if max_wl else False,
        "approaching": wl_pct >= 80 if max_wl else False,
    })

    alerts = []
    for d in dimensions:
        if d["exceeded"]:
            alerts.append({"level": "error", "message": f"{d['name']}: {d['current']} exceeds {d['limit']} limit. Upgrade to Professional."})
        elif d["approaching"]:
            alerts.append({"level": "warning", "message": f"{d['name']}: {d['current']}/{d['limit']} ({d['usage_percent']}%). Approaching limit."})

    return {
        "tier": tier_name,
        "tier_label": tier["label"],
        "features": tier["features"],
        "smart_engine": tier["smart_engine"],
        "support": tier["support"],
        "usage": dimensions,
        "alerts": alerts,
        "has_alerts": len(alerts) > 0,
        "upgrade_available": tier_name != "enterprise",
    }


@router.get("/trends")
async def usage_trends(
    period: str = Query("30d"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Usage trends over time: users, storage, jobs."""
    days = int(period.rstrip("d")) if period.endswith("d") else 30
    days = max(1, min(days, 90))
    trend = []

    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - 1 - i)).date()
        day_end = datetime.combine(date, datetime.max.time())

        # Cumulative protected objects as of this date
        users = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.status == ProtectionStatus.PROTECTED,
                ProtectedObject.created_at <= day_end,
            )
        )).scalar() or 0

        # Cumulative storage
        storage = (await db.execute(
            select(func.sum(Snapshot.size_bytes)).where(
                Snapshot.status == SnapshotStatus.COMPLETED,
                Snapshot.created_at <= day_end,
            )
        )).scalar() or 0

        # Jobs on this day
        day_start = datetime.combine(date, datetime.min.time())
        jobs = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.created_at >= day_start, BackupJob.created_at <= day_end,
            )
        )).scalar() or 0

        trend.append({
            "date": date.isoformat(),
            "protected_users": users,
            "storage_bytes": int(storage),
            "jobs": jobs,
        })

    return {"period": period, "trend": trend}
