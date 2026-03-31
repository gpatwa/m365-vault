"""MSP Multi-Tenant Dashboard API — overview of all client tenants for managed service providers.

Provides a single-pane-of-glass view across all tenants with per-tenant
health scores, protection status, backup activity, and alerts.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus, WorkloadType
from app.models.backup_job import BackupJob, JobStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.user import User
from app.services.auth import require_msp_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/msp", tags=["MSP Dashboard"])


@router.get("/overview")
async def msp_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """MSP overview — all tenants with per-tenant health summary.

    Returns a list of tenants with protection stats, backup activity,
    storage usage, and health indicators for the MSP dashboard.
    """
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)

    # Get all tenants
    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()

    tenant_summaries = []
    total_users = 0
    total_storage = 0
    total_alerts = 0

    for tenant in tenants:
        tid = tenant.id

        # Protected objects
        protected_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )).scalar() or 0

        total_objects = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
            )
        )).scalar() or 0

        protection_pct = round(protected_count / total_objects * 100) if total_objects > 0 else 0

        # Active workloads
        wl_result = await db.execute(
            select(func.count(func.distinct(ProtectedObject.workload_type))).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )
        workload_count = wl_result.scalar() or 0

        # Backup jobs (24h)
        jobs_24h = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.tenant_id == tid,
                BackupJob.created_at >= since_24h,
            )
        )).scalar() or 0

        jobs_failed_24h = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.tenant_id == tid,
                BackupJob.created_at >= since_24h,
                BackupJob.status == JobStatus.FAILED,
            )
        )).scalar() or 0

        # Storage
        storage_bytes = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tid,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
        )).scalar() or 0

        # Last backup time
        last_backup = (await db.execute(
            select(func.max(BackupJob.completed_at)).where(
                BackupJob.tenant_id == tid,
                BackupJob.status == JobStatus.COMPLETED,
            )
        )).scalar()

        # Simple health score (0-100)
        health = 100
        alerts = []

        if protection_pct < 100:
            health -= 20
            alerts.append(f"{total_objects - protected_count} unprotected objects")
        if jobs_failed_24h > 0:
            health -= 30
            alerts.append(f"{jobs_failed_24h} failed backups in 24h")
        if last_backup and (now - last_backup).total_seconds() > 86400:
            health -= 15
            alerts.append("No backup in 24+ hours")
        if total_objects == 0:
            health = 0
            alerts.append("No objects discovered")

        health = max(0, health)
        total_users += protected_count
        total_storage += storage_bytes
        total_alerts += len(alerts)

        tenant_summaries.append({
            "id": tenant.id,
            "name": tenant.name,
            "status": tenant.status.value,
            "ms_tenant_id": tenant.ms_tenant_id,
            "protected_objects": protected_count,
            "total_objects": total_objects,
            "protection_pct": protection_pct,
            "workload_count": workload_count,
            "backups_24h": jobs_24h,
            "failed_24h": jobs_failed_24h,
            "storage_bytes": storage_bytes,
            "storage_gb": round(storage_bytes / (1024 ** 3), 3),
            "last_backup": last_backup.isoformat() if last_backup else None,
            "health_score": health,
            "health_status": "healthy" if health >= 80 else ("at_risk" if health >= 50 else "critical"),
            "alerts": alerts,
            "alert_count": len(alerts),
        })

    # Sort by health (worst first for attention)
    tenant_summaries.sort(key=lambda t: t["health_score"])

    return {
        "summary": {
            "total_tenants": len(tenants),
            "active_tenants": sum(1 for t in tenants if t.status == TenantStatus.ACTIVE),
            "total_protected_users": total_users,
            "total_storage_bytes": total_storage,
            "total_storage_gb": round(total_storage / (1024 ** 3), 3),
            "total_alerts": total_alerts,
            "overall_health": round(sum(t["health_score"] for t in tenant_summaries) / len(tenant_summaries)) if tenant_summaries else 0,
        },
        "tenants": tenant_summaries,
    }
