"""Health monitoring API routes — Smart Engine endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.health_baseline import HealthBaseline, AnomalyEvent
from app.services.auth import get_current_user
from app.services.smart_engine import SmartEngine

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/score")
async def get_health_score(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tenant health score (0-100) with component breakdown."""
    engine = SmartEngine(db)
    return await engine.compute_health_score(tenant_id)


@router.get("/anomalies")
async def get_anomalies(
    tenant_id: int = Query(...),
    active_only: bool = Query(True),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent anomaly events for a tenant."""
    stmt = select(AnomalyEvent).where(AnomalyEvent.tenant_id == tenant_id)
    if active_only:
        stmt = stmt.where(AnomalyEvent.resolved == 0)
    stmt = stmt.order_by(desc(AnomalyEvent.detected_at)).limit(page_size)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "total": len(events),
        "items": [
            {
                "id": e.id,
                "workload": e.workload_type,
                "metric": e.metric_name,
                "expected": e.expected_value,
                "actual": e.actual_value,
                "z_score": round(e.z_score, 2),
                "severity": e.severity,
                "message": e.message,
                "resolved": bool(e.resolved),
                "detected_at": e.detected_at.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/baselines")
async def get_baselines(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current health baselines for a tenant."""
    result = await db.execute(
        select(HealthBaseline).where(HealthBaseline.tenant_id == tenant_id)
        .order_by(HealthBaseline.workload_type, HealthBaseline.metric_name)
    )
    baselines = result.scalars().all()

    return {
        "total": len(baselines),
        "items": [
            {
                "workload": b.workload_type,
                "metric": b.metric_name,
                "avg": round(b.avg_value, 2),
                "std_dev": round(b.std_dev, 2),
                "min": round(b.min_value, 2),
                "max": round(b.max_value, 2),
                "samples": b.sample_count,
                "last_updated": b.last_updated.isoformat(),
            }
            for b in baselines
        ],
    }


@router.post("/check")
async def run_health_check(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger health check: update baselines + detect anomalies."""
    engine = SmartEngine(db)
    await engine.update_baselines(tenant_id)
    anomalies = await engine.detect_anomalies(tenant_id)
    score = await engine.compute_health_score(tenant_id)
    await db.commit()

    return {
        "score": score["score"],
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
    }
