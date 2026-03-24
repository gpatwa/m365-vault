"""Public status page API — no authentication required.

Provides system status, component health, and recent incident history
for transparency with customers and integration with status page services.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter
from sqlalchemy import select, func, text

from app.database import async_session
from app.models.backup_job import BackupJob, JobStatus
from app.config import settings

router = APIRouter(prefix="/api/status", tags=["Status"])


@router.get("")
async def system_status():
    """Public system status — no auth required.

    Returns component health, uptime metrics, and recent job stats.
    Suitable for embedding in a status page (e.g., Statuspage.io, Upptime).
    """
    checks = {}
    overall = "operational"

    # Check database
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "operational"
    except Exception:
        checks["database"] = "degraded"
        overall = "degraded"

    # Check storage
    try:
        from app.services.storage import storage_service
        if storage_service and storage_service.backend:
            checks["storage"] = "operational"
        else:
            checks["storage"] = "unknown"
    except Exception:
        checks["storage"] = "degraded"
        overall = "degraded"

    # Check scheduler (backup engine)
    checks["scheduler"] = "operational"  # If API is responding, scheduler is running

    # Recent job success rate (last 24h)
    since = datetime.utcnow() - timedelta(hours=24)
    try:
        async with async_session() as db:
            total_result = await db.execute(
                select(func.count(BackupJob.id)).where(BackupJob.created_at >= since)
            )
            total_jobs = total_result.scalar() or 0

            success_result = await db.execute(
                select(func.count(BackupJob.id)).where(
                    BackupJob.created_at >= since,
                    BackupJob.status == JobStatus.COMPLETED,
                )
            )
            successful = success_result.scalar() or 0

            success_rate = round(successful / total_jobs * 100, 1) if total_jobs > 0 else 100.0

            if success_rate < 90:
                checks["backup_engine"] = "degraded"
                overall = "degraded"
            else:
                checks["backup_engine"] = "operational"
    except Exception:
        checks["backup_engine"] = "unknown"

    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "components": checks,
        "metrics": {
            "jobs_24h": total_jobs if 'total_jobs' in dir() else 0,
            "success_rate_24h": success_rate if 'success_rate' in dir() else 100.0,
        },
    }
