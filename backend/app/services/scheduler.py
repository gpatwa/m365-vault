"""SLA-based backup scheduler using APScheduler.

Reads SLA policies and automatically schedules backup jobs
for protected objects based on their assigned SLA frequency.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.sla_policy import SLAPolicy
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.models.backup_job import BackupJob, JobStatus
from app.models.tenant import Tenant, TenantStatus

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_and_schedule_backups():
    """Check all protected objects and create backup jobs as needed per SLA,
    then execute any queued jobs."""
    async with async_session() as db:
        try:
            # Get all active protected objects with SLA policies (skip inactive tenants)
            result = await db.execute(
                select(ProtectedObject, SLAPolicy)
                .join(SLAPolicy, ProtectedObject.sla_policy_id == SLAPolicy.id)
                .join(Tenant, ProtectedObject.tenant_id == Tenant.id)
                .where(
                    ProtectedObject.status == ProtectionStatus.PROTECTED,
                    SLAPolicy.is_active == 1,
                    Tenant.status == TenantStatus.ACTIVE,
                )
            )
            rows = result.all()

            jobs_created = 0
            for obj, sla in rows:
                # Check if backup is due
                if obj.last_backup_at:
                    next_backup_at = obj.last_backup_at + timedelta(hours=sla.backup_frequency_hours)
                    if datetime.utcnow() < next_backup_at:
                        continue

                # Check if there's already a running/queued job for this object
                existing = await db.execute(
                    select(BackupJob).where(
                        BackupJob.tenant_id == obj.tenant_id,
                        BackupJob.workload_type == obj.workload_type.value,
                        BackupJob.status.in_([JobStatus.QUEUED, JobStatus.IN_PROGRESS]),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Create a new backup job
                job = BackupJob(
                    tenant_id=obj.tenant_id,
                    workload_type=obj.workload_type.value,
                    sla_policy_id=sla.id,
                    status=JobStatus.QUEUED,
                    objects_total=1,
                )
                db.add(job)
                jobs_created += 1

            await db.commit()

            if jobs_created > 0:
                logger.info(f"Scheduler created {jobs_created} new backup jobs")

        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await db.rollback()

    # Now execute any queued jobs
    await execute_queued_jobs()


async def execute_queued_jobs():
    """Pick up and execute all queued backup jobs."""
    from app.services.backup_engine import BackupEngine

    async with async_session() as db:
        try:
            result = await db.execute(
                select(BackupJob)
                .where(BackupJob.status == JobStatus.QUEUED)
                .order_by(BackupJob.created_at)
            )
            jobs = result.scalars().all()

            if not jobs:
                return

            logger.info(f"Executing {len(jobs)} queued backup jobs")
            engine = BackupEngine(db)

            for job in jobs:
                try:
                    await engine._execute_backup_job(job)
                    logger.info(
                        f"Job {job.id} completed: {job.objects_processed}/{job.objects_total} objects, "
                        f"{job.objects_failed} failed"
                    )
                except Exception as e:
                    logger.error(f"Backup job {job.id} failed: {e}")
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    await db.commit()

        except Exception as e:
            logger.error(f"Job executor error: {e}")
            await db.rollback()


async def cleanup_expired_snapshots():
    """Remove snapshots that have exceeded their SLA retention period."""
    from app.models.snapshot import Snapshot, SnapshotStatus
    from app.services.storage import storage_service

    async with async_session() as db:
        try:
            result = await db.execute(
                select(Snapshot, ProtectedObject, SLAPolicy)
                .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
                .join(SLAPolicy, ProtectedObject.sla_policy_id == SLAPolicy.id)
                .where(Snapshot.status == SnapshotStatus.COMPLETED)
            )
            rows = result.all()

            expired_count = 0
            for snapshot, obj, sla in rows:
                expiry_date = snapshot.created_at + timedelta(days=sla.retention_days)
                # Block deletion if WORM locked or legal hold
                if snapshot.locked_until and datetime.utcnow() < snapshot.locked_until:
                    continue  # WORM: immutable until locked_until
                if sla.legal_hold:
                    continue  # Legal hold: never delete
                if datetime.utcnow() > expiry_date and not sla.is_locked:
                    # Mark as expired
                    snapshot.status = SnapshotStatus.EXPIRED

                    # Clean up storage
                    await storage_service.delete_snapshot_storage(
                        tenant_id=obj.tenant_id,
                        workload=obj.workload_type.value,
                        object_id=obj.ms_object_id,
                        snapshot_id=snapshot.id,
                    )
                    expired_count += 1

            await db.commit()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired snapshots")

        except Exception as e:
            logger.error(f"Retention cleanup error: {e}")
            await db.rollback()


async def retry_failed_jobs():
    """Automatically retry failed backup jobs with exponential backoff."""
    from app.services.retry_engine import RetryEngine

    async with async_session() as db:
        try:
            engine = RetryEngine(db)
            summary = await engine.process_failed_jobs()
            if summary["retried"] > 0:
                logger.info(
                    f"Retry engine: retried {summary['retried']} jobs — "
                    f"{summary['succeeded']} succeeded, {summary['still_failed']} still failed"
                )
        except Exception as e:
            logger.error(f"Retry engine error: {e}")
            await db.rollback()


async def run_smart_engine():
    """Run Smart Engine: update baselines, detect anomalies, send alerts."""
    from app.services.smart_engine import SmartEngine
    from app.services.alert_service import alert_service

    async with async_session() as db:
        try:
            # Get all active tenants
            result = await db.execute(
                select(Tenant).where(Tenant.status == TenantStatus.ACTIVE)
            )
            tenants = result.scalars().all()

            engine = SmartEngine(db)
            total_anomalies = 0

            for tenant in tenants:
                # Update baselines
                await engine.update_baselines(tenant.id)

                # Detect anomalies
                anomalies = await engine.detect_anomalies(tenant.id)
                total_anomalies += len(anomalies)

                # Alert on critical anomalies
                for anomaly in anomalies:
                    if anomaly["severity"] == "critical":
                        await alert_service.notify(
                            event_type="anomaly.detected",
                            title=f"Critical anomaly: {anomaly['workload']} {anomaly['metric']}",
                            details=anomaly["message"],
                            severity="critical",
                            tenant_name=tenant.name,
                            workload=anomaly["workload"],
                        )

            await db.commit()
            if total_anomalies > 0:
                logger.warning(f"Smart Engine: {total_anomalies} anomalies detected across {len(tenants)} tenants")

        except Exception as e:
            logger.error(f"Smart Engine error: {e}")
            await db.rollback()


async def apply_worm_locks():
    """Apply WORM locks to snapshots in WORM-enabled SLA policies."""
    from app.models.snapshot import Snapshot, SnapshotStatus

    async with async_session() as db:
        try:
            # Find completed snapshots without locked_until in WORM-enabled policies
            result = await db.execute(
                select(Snapshot, SLAPolicy)
                .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
                .join(SLAPolicy, ProtectedObject.sla_policy_id == SLAPolicy.id)
                .where(
                    Snapshot.status == SnapshotStatus.COMPLETED,
                    Snapshot.locked_until.is_(None),
                    SLAPolicy.worm_enabled == 1,
                )
            )
            rows = result.all()

            locked_count = 0
            for snapshot, sla in rows:
                snapshot.locked_until = snapshot.created_at + timedelta(days=sla.retention_days)
                locked_count += 1

            await db.commit()
            if locked_count > 0:
                logger.info(f"WORM: Applied retention locks to {locked_count} snapshots")

        except Exception as e:
            logger.error(f"WORM lock error: {e}")
            await db.rollback()


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        check_and_schedule_backups,
        IntervalTrigger(seconds=settings.SCHEDULER_CHECK_INTERVAL_SECONDS),
        id="backup_scheduler",
        name="Check and schedule backups per SLA",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_expired_snapshots,
        IntervalTrigger(hours=6),
        id="retention_cleanup",
        name="Clean up expired snapshots",
        replace_existing=True,
    )
    scheduler.add_job(
        retry_failed_jobs,
        IntervalTrigger(minutes=10),
        id="retry_failed_jobs",
        name="Retry failed backup jobs with backoff",
        replace_existing=True,
    )
    scheduler.add_job(
        run_smart_engine,
        IntervalTrigger(minutes=settings.HEALTH_CHECK_INTERVAL_MINUTES),
        id="smart_engine",
        name="Smart Engine: baselines + anomaly detection",
        replace_existing=True,
    )
    scheduler.add_job(
        apply_worm_locks,
        IntervalTrigger(hours=1),
        id="worm_locks",
        name="Apply WORM retention locks to new snapshots",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Backup scheduler started (with retry engine, smart engine, WORM)")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Backup scheduler stopped")
