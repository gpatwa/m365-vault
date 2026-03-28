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
    """Pick up and execute all queued backup jobs via dispatcher."""
    from app.interfaces.dispatcher_factory import get_dispatcher
    from app.interfaces.job_message import BackupJobMessage

    dispatcher = get_dispatcher()

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

            logger.info(f"Dispatching {len(jobs)} queued backup jobs")

            for job in jobs:
                try:
                    job_result = await dispatcher.dispatch_backup_job(
                        BackupJobMessage(backup_job_id=job.id), db=db
                    )
                    if job_result.success:
                        logger.info(f"Job {job.id} completed: status={job_result.status}")
                    else:
                        logger.error(f"Job {job.id} failed: {job_result.error}")
                except Exception as e:
                    logger.error(f"Backup job {job.id} dispatch failed: {e}")
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


async def detect_stale_jobs():
    """Reset IN_PROGRESS jobs that haven't updated within JOB_TIMEOUT_MINUTES.

    Handles worker crashes: if a job is stuck IN_PROGRESS for too long,
    reset it to QUEUED so it gets re-dispatched to another worker.
    """
    async with async_session() as db:
        try:
            stale_cutoff = datetime.utcnow() - timedelta(minutes=settings.JOB_TIMEOUT_MINUTES)
            result = await db.execute(
                select(BackupJob).where(
                    BackupJob.status == JobStatus.IN_PROGRESS,
                    BackupJob.started_at < stale_cutoff,
                )
            )
            stale_jobs = result.scalars().all()

            for job in stale_jobs:
                logger.warning(
                    f"Stale job detected: job {job.id} (workload={job.workload_type}) "
                    f"started at {job.started_at}, resetting to QUEUED"
                )
                job.status = JobStatus.QUEUED
                job.error_message = f"Reset: worker unresponsive since {job.started_at.isoformat()}"

            if stale_jobs:
                await db.commit()
                logger.info(f"Reset {len(stale_jobs)} stale jobs to QUEUED")

                # Alert
                try:
                    from app.services.alert_service import alert_service
                    await alert_service.notify(
                        event_type="job.stale",
                        title=f"{len(stale_jobs)} backup job(s) reset — worker may have crashed",
                        details=f"Jobs stuck IN_PROGRESS for >{settings.JOB_TIMEOUT_MINUTES} minutes were reset to QUEUED for retry.",
                        severity="warning",
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Stale job detection error: {e}")
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


async def refresh_mvb_plans():
    """Refresh pre-computed MVB recovery plans for all active tenants."""
    from app.services.mvb_plan_generator import MVBPlanGenerator

    async with async_session() as db:
        try:
            result = await db.execute(
                select(Tenant).where(Tenant.status == TenantStatus.ACTIVE)
            )
            tenants = result.scalars().all()

            for tenant in tenants:
                try:
                    generator = MVBPlanGenerator(db)
                    plan = await generator.generate_plan(tenant)
                    await db.commit()
                    logger.info(f"MVB plan refreshed for tenant {tenant.name}: {plan.total_object_count} objects, {plan.estimated_minutes} min est.")
                except Exception as e:
                    logger.error(f"MVB plan refresh failed for tenant {tenant.name}: {e}")
                    await db.rollback()
        except Exception as e:
            logger.error(f"MVB plan refresh scheduler error: {e}")


async def collect_org_context():
    """Collect organizational context (hierarchy, departments) from Graph for all tenants."""
    from app.services.context_collector import ContextCollectorService
    from app.services.criticality_scorer import CriticalityScorer

    async with async_session() as db:
        try:
            result = await db.execute(
                select(Tenant).where(Tenant.status == TenantStatus.ACTIVE)
            )
            tenants = result.scalars().all()

            for tenant in tenants:
                try:
                    collector = ContextCollectorService(db)
                    await collector.collect_all(tenant)

                    scorer = CriticalityScorer(db)
                    await scorer.score_all(tenant.id)

                    logger.info(f"Org context collected for tenant {tenant.name}")
                except Exception as e:
                    logger.error(f"Org context collection failed for tenant {tenant.name}: {e}")
                    await db.rollback()
        except Exception as e:
            logger.error(f"Org context scheduler error: {e}")


async def collect_security_signals():
    """Collect privileged roles and security signals (runs more frequently than full sync)."""
    from app.services.context_collector import ContextCollectorService
    from app.services.criticality_scorer import CriticalityScorer

    async with async_session() as db:
        try:
            result = await db.execute(
                select(Tenant).where(Tenant.status == TenantStatus.ACTIVE)
            )
            tenants = result.scalars().all()

            for tenant in tenants:
                try:
                    collector = ContextCollectorService(db)
                    graph = collector._get_graph_client(tenant)
                    await collector._collect_privileged_roles(tenant, graph)
                    await db.commit()

                    scorer = CriticalityScorer(db)
                    await scorer.score_all(tenant.id)

                    logger.info(f"Security signals updated for tenant {tenant.name}")
                except Exception as e:
                    logger.warning(f"Security signal collection failed for tenant {tenant.name}: {e}")
                    await db.rollback()
        except Exception as e:
            logger.error(f"Security signal scheduler error: {e}")


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
    scheduler.add_job(
        detect_stale_jobs,
        IntervalTrigger(minutes=15),
        id="stale_job_detector",
        name="Detect and reset stale IN_PROGRESS jobs",
        replace_existing=True,
    )
    scheduler.add_job(
        refresh_mvb_plans,
        IntervalTrigger(hours=6),
        id="mvb_plan_refresh",
        name="Refresh pre-computed MVB recovery plans",
        replace_existing=True,
    )
    scheduler.add_job(
        collect_org_context,
        IntervalTrigger(hours=24),
        id="org_context_collector",
        name="Collect org context from Microsoft Graph",
        replace_existing=True,
    )
    scheduler.add_job(
        collect_security_signals,
        IntervalTrigger(hours=6),
        id="security_signal_collector",
        name="Collect privileged roles and security signals",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (backup, retry, smart engine, WORM, stale detector, org context)")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Backup scheduler stopped")
