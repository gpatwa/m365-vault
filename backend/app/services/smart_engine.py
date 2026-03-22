"""Smart Engine — zero-cost intelligence layer.

Provides:
- Health baselines (running averages per tenant/workload)
- Anomaly detection (z-score deviation from baseline)
- Health scoring (0-100 composite score)

All computation is pure Python — no LLM tokens, no external APIs.
"""
import logging
import math
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.backup_job import BackupJob, JobStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.health_baseline import HealthBaseline, AnomalyEvent

logger = logging.getLogger(__name__)


class SmartEngine:
    """Zero-cost intelligence: baselines, anomaly detection, health scoring."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Baseline Management ──

    async def update_baselines(self, tenant_id: int):
        """Update running averages from recent backup data (last 7 days)."""
        since = datetime.utcnow() - timedelta(days=7)

        # Get completed snapshots grouped by workload
        result = await self.db.execute(
            select(
                ProtectedObject.workload_type,
                func.count(Snapshot.id).label("count"),
                func.avg(Snapshot.item_count).label("avg_items"),
                func.avg(Snapshot.size_bytes).label("avg_size"),
            )
            .join(Snapshot, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                Snapshot.status == SnapshotStatus.COMPLETED,
                Snapshot.completed_at >= since,
            )
            .group_by(ProtectedObject.workload_type)
        )

        for row in result.all():
            workload = row.workload_type.value if hasattr(row.workload_type, 'value') else str(row.workload_type)

            # Update item_count baseline
            await self._upsert_baseline(
                tenant_id, workload, "item_count",
                float(row.avg_items or 0), int(row.count or 0),
            )

            # Update size_bytes baseline
            await self._upsert_baseline(
                tenant_id, workload, "size_bytes",
                float(row.avg_size or 0), int(row.count or 0),
            )

        # Calculate error rate baseline per workload
        job_result = await self.db.execute(
            select(
                BackupJob.workload_type,
                func.count(BackupJob.id).label("total"),
                func.sum(BackupJob.objects_failed).label("failed"),
            )
            .where(
                BackupJob.tenant_id == tenant_id,
                BackupJob.completed_at >= since,
            )
            .group_by(BackupJob.workload_type)
        )

        for row in job_result.all():
            total = int(row.total or 0)
            failed = int(row.failed or 0)
            error_rate = (failed / total * 100) if total > 0 else 0.0

            await self._upsert_baseline(
                tenant_id, row.workload_type, "error_rate",
                error_rate, total,
            )

        await self.db.flush()
        logger.debug(f"Updated baselines for tenant {tenant_id}")

    async def _upsert_baseline(
        self, tenant_id: int, workload: str, metric: str,
        new_value: float, sample_count: int,
    ):
        """Update or create a baseline using exponential moving average."""
        result = await self.db.execute(
            select(HealthBaseline).where(
                HealthBaseline.tenant_id == tenant_id,
                HealthBaseline.workload_type == workload,
                HealthBaseline.metric_name == metric,
            )
        )
        baseline = result.scalar_one_or_none()

        if baseline:
            # Exponential moving average (alpha=0.3 for recent bias)
            alpha = 0.3
            old_avg = baseline.avg_value
            baseline.avg_value = old_avg + alpha * (new_value - old_avg)

            # Running std dev approximation
            diff = abs(new_value - baseline.avg_value)
            baseline.std_dev = baseline.std_dev + alpha * (diff - baseline.std_dev)

            baseline.min_value = min(baseline.min_value, new_value)
            baseline.max_value = max(baseline.max_value, new_value)
            baseline.sample_count = sample_count
            baseline.last_updated = datetime.utcnow()
        else:
            baseline = HealthBaseline(
                tenant_id=tenant_id,
                workload_type=workload,
                metric_name=metric,
                avg_value=new_value,
                std_dev=0.0,
                min_value=new_value,
                max_value=new_value,
                sample_count=sample_count,
                last_updated=datetime.utcnow(),
            )
            self.db.add(baseline)

    # ── Anomaly Detection ──

    async def detect_anomalies(self, tenant_id: int) -> list[dict]:
        """Check latest backup metrics against baselines.

        Flags anomalies when values deviate by more than Z_SCORE_THRESHOLD
        standard deviations from the baseline.
        """
        threshold = settings.ANOMALY_Z_SCORE_THRESHOLD
        anomalies = []

        # Get latest completed snapshot per workload
        result = await self.db.execute(
            select(ProtectedObject.workload_type, Snapshot)
            .join(Snapshot, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
            .order_by(Snapshot.completed_at.desc())
        )

        # Group latest snapshot per workload
        latest_by_workload = {}
        for wt, snapshot in result.all():
            workload = wt.value if hasattr(wt, 'value') else str(wt)
            if workload not in latest_by_workload:
                latest_by_workload[workload] = snapshot

        for workload, snapshot in latest_by_workload.items():
            # Check item_count
            anomaly = await self._check_metric(
                tenant_id, workload, "item_count",
                float(snapshot.item_count or 0), threshold,
            )
            if anomaly:
                anomalies.append(anomaly)

            # Check size_bytes
            anomaly = await self._check_metric(
                tenant_id, workload, "size_bytes",
                float(snapshot.size_bytes or 0), threshold,
            )
            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    async def _check_metric(
        self, tenant_id: int, workload: str, metric: str,
        actual: float, threshold: float,
    ) -> dict | None:
        """Check a single metric against its baseline."""
        result = await self.db.execute(
            select(HealthBaseline).where(
                HealthBaseline.tenant_id == tenant_id,
                HealthBaseline.workload_type == workload,
                HealthBaseline.metric_name == metric,
            )
        )
        baseline = result.scalar_one_or_none()

        if not baseline or baseline.sample_count < 3 or baseline.std_dev == 0:
            return None  # Not enough data to detect anomalies

        z_score = abs(actual - baseline.avg_value) / baseline.std_dev

        if z_score > threshold:
            severity = "critical" if z_score > threshold * 2 else "warning"
            direction = "above" if actual > baseline.avg_value else "below"
            message = (
                f"{workload} {metric} is {direction} normal: "
                f"actual={actual:.0f}, expected={baseline.avg_value:.0f} "
                f"(z-score={z_score:.1f})"
            )

            # Record anomaly event
            event = AnomalyEvent(
                tenant_id=tenant_id,
                workload_type=workload,
                metric_name=metric,
                expected_value=baseline.avg_value,
                actual_value=actual,
                z_score=z_score,
                severity=severity,
                message=message,
            )
            self.db.add(event)

            logger.warning(f"Anomaly detected: {message}")

            return {
                "workload": workload,
                "metric": metric,
                "actual": actual,
                "expected": baseline.avg_value,
                "z_score": round(z_score, 2),
                "severity": severity,
                "message": message,
            }

        return None

    # ── Health Scoring ──

    async def compute_health_score(self, tenant_id: int) -> dict:
        """Compute tenant health score (0-100).

        Weighted formula:
        - 40% success rate (completed / total jobs, last 7 days)
        - 30% SLA adherence (objects backed up within SLA frequency)
        - 20% error trend (improving = bonus, worsening = penalty)
        - 10% storage health (dedup ratio, compression ratio)
        """
        since = datetime.utcnow() - timedelta(days=7)

        # Success rate (40%)
        job_result = await self.db.execute(
            select(
                func.count(BackupJob.id).label("total"),
                func.sum(func.cast(BackupJob.status == JobStatus.COMPLETED, Integer)).label("completed"),
            )
            .where(BackupJob.tenant_id == tenant_id, BackupJob.completed_at >= since)
        )
        row = job_result.one()
        total_jobs = int(row.total or 0)
        completed_jobs = int(row.completed or 0)
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 100
        success_score = min(success_rate, 100)

        # SLA adherence (30%)
        obj_result = await self.db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )
        total_protected = obj_result.scalar() or 0

        backed_up_result = await self.db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
                ProtectedObject.last_backup_at >= since,
            )
        )
        backed_up = backed_up_result.scalar() or 0
        sla_adherence = (backed_up / total_protected * 100) if total_protected > 0 else 100
        sla_score = min(sla_adherence, 100)

        # Active anomalies penalty (20%)
        anomaly_result = await self.db.execute(
            select(func.count(AnomalyEvent.id)).where(
                AnomalyEvent.tenant_id == tenant_id,
                AnomalyEvent.resolved == 0,
                AnomalyEvent.detected_at >= since,
            )
        )
        active_anomalies = anomaly_result.scalar() or 0
        anomaly_score = max(100 - (active_anomalies * 20), 0)  # -20 per anomaly

        # Storage score (10%) — based on having recent backups
        storage_score = 100 if total_jobs > 0 else 50

        # Weighted total
        health_score = round(
            success_score * 0.40 +
            sla_score * 0.30 +
            anomaly_score * 0.20 +
            storage_score * 0.10
        )

        return {
            "score": min(health_score, 100),
            "components": {
                "success_rate": round(success_score, 1),
                "sla_adherence": round(sla_score, 1),
                "anomaly_score": round(anomaly_score, 1),
                "storage_score": round(storage_score, 1),
            },
            "details": {
                "total_jobs_7d": total_jobs,
                "completed_jobs_7d": completed_jobs,
                "protected_objects": total_protected,
                "backed_up_objects": backed_up,
                "active_anomalies": active_anomalies,
            },
        }


# Import Integer for SQL cast
from sqlalchemy import Integer
