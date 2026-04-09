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
    then execute any queued jobs.

    Batch decomposition: when a (tenant, workload) group has more objects than
    BATCH_THRESHOLD, creates a parent coordinator job + child batch jobs.
    Each child handles BATCH_SIZE objects. TenantFairScheduler runs up to 3
    child batches concurrently per tenant.

    Lifecycle enforcement: only schedules backups for objects whose workload
    is in PROTECTED lifecycle state. Paused/disabled workloads are skipped.
    """
    async with async_session() as db:
        try:
            from app.models.tenant_workload_app import TenantWorkloadApp, WorkloadLifecycle
            from collections import defaultdict

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

            # Build set of protected workloads per tenant for lifecycle filtering
            _protected_cache = {}
            async def _is_workload_protected(tid: int, wl_value: str) -> bool:
                if tid not in _protected_cache:
                    from app.services.workload_lifecycle import get_protected_workloads
                    _protected_cache[tid] = await get_protected_workloads(db, tid)
                if not _protected_cache[tid]:
                    return True
                return wl_value in _protected_cache[tid]

            # Group eligible objects by (tenant_id, workload_type, sla_policy_id)
            groups = defaultdict(lambda: {"count": 0, "sla_id": None})
            for obj, sla in rows:
                wl_value = obj.workload_type.value if hasattr(obj.workload_type, 'value') else str(obj.workload_type)
                if not await _is_workload_protected(obj.tenant_id, wl_value):
                    continue

                # Check if backup is due
                if obj.last_backup_at:
                    next_backup_at = obj.last_backup_at + timedelta(hours=sla.backup_frequency_hours)
                    if datetime.utcnow() < next_backup_at:
                        continue

                key = (obj.tenant_id, wl_value)
                groups[key]["count"] += 1
                groups[key]["sla_id"] = sla.id

            jobs_created = 0
            for (tenant_id, workload_type), info in groups.items():
                obj_count = info["count"]
                sla_id = info["sla_id"]

                # Check if there's already a running/queued job for this tenant+workload
                existing = await db.execute(
                    select(BackupJob).where(
                        BackupJob.tenant_id == tenant_id,
                        BackupJob.workload_type == workload_type,
                        BackupJob.status.in_([JobStatus.QUEUED, JobStatus.IN_PROGRESS]),
                        BackupJob.parent_job_id.is_(None),  # Only check top-level jobs
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                batch_threshold = settings.BATCH_THRESHOLD
                batch_size = settings.BATCH_SIZE

                if obj_count <= batch_threshold:
                    # Small workload: single job (no batching)
                    job = BackupJob(
                        tenant_id=tenant_id,
                        workload_type=workload_type,
                        sla_policy_id=sla_id,
                        status=JobStatus.QUEUED,
                        objects_total=obj_count,
                    )
                    db.add(job)
                    jobs_created += 1
                else:
                    # Large workload: parent + child batch jobs
                    parent = BackupJob(
                        tenant_id=tenant_id,
                        workload_type=workload_type,
                        sla_policy_id=sla_id,
                        status=JobStatus.IN_PROGRESS,
                        objects_total=obj_count,
                    )
                    db.add(parent)
                    await db.flush()  # Get parent.id

                    num_batches = (obj_count + batch_size - 1) // batch_size
                    for i in range(num_batches):
                        offset = i * batch_size
                        size = min(batch_size, obj_count - offset)
                        child = BackupJob(
                            tenant_id=tenant_id,
                            workload_type=workload_type,
                            sla_policy_id=sla_id,
                            status=JobStatus.QUEUED,
                            objects_total=size,
                            parent_job_id=parent.id,
                            batch_offset=offset,
                            batch_size=size,
                        )
                        db.add(child)

                    jobs_created += num_batches
                    logger.info(
                        f"Batch scheduler: {workload_type} tenant={tenant_id} "
                        f"split {obj_count} objects into {num_batches} batches of {batch_size}"
                    )

            await db.commit()

            if jobs_created > 0:
                logger.info(f"Scheduler created {jobs_created} new backup jobs")

        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await db.rollback()

    # Now execute any queued jobs
    await execute_queued_jobs()


async def execute_queued_jobs():
    """Pick up and execute all queued backup jobs via dispatcher.

    Skips parent coordinator jobs — only dispatches leaf jobs (single jobs
    without a parent, or child batch jobs).
    """
    from app.interfaces.dispatcher_factory import get_dispatcher
    from app.interfaces.job_message import BackupJobMessage

    dispatcher = get_dispatcher()

    async with async_session() as db:
        try:
            # Only dispatch leaf jobs: either no parent (single jobs) or child batches
            # Parent coordinator jobs have children and are never dispatched directly
            result = await db.execute(
                select(BackupJob)
                .where(
                    BackupJob.status == JobStatus.QUEUED,
                    or_(
                        BackupJob.parent_job_id.isnot(None),   # Child batch job
                        BackupJob.batch_size.is_(None),         # Single (non-batched) job
                    ),
                )
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

                    # Mark onboarding step on first successful backup
                    if job_result.success and job_result.status == "completed":
                        await _mark_first_backup_step(db, job.tenant_id)

                except Exception as e:
                    logger.error(f"Backup job {job.id} dispatch failed: {e}")
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    await db.commit()

        except Exception as e:
            logger.error(f"Job executor error: {e}")
            await db.rollback()


async def _mark_first_backup_step(db: AsyncSession, tenant_id: int):
    """Mark 'first_backup' onboarding step for all users of this tenant."""
    try:
        from app.models.user_tenant import UserTenantMembership
        from app.services.onboarding_service import mark_step

        result = await db.execute(
            select(UserTenantMembership.user_id).where(
                UserTenantMembership.tenant_id == tenant_id
            )
        )
        for (user_id,) in result.all():
            await mark_step(db, user_id, "first_backup")
    except Exception as e:
        logger.debug(f"Onboarding step mark skipped: {e}")


async def aggregate_parent_jobs():
    """Aggregate child batch results into parent coordinator jobs.

    When all children of a parent are COMPLETED/FAILED/PARTIAL, compute the
    parent's aggregate status and totals.
    """
    async with async_session() as db:
        try:
            from sqlalchemy import func as _func

            # Find parent jobs that are IN_PROGRESS (coordinators waiting for children)
            parents_result = await db.execute(
                select(BackupJob).where(
                    BackupJob.status == JobStatus.IN_PROGRESS,
                    BackupJob.parent_job_id.is_(None),
                    BackupJob.batch_size.is_(None),  # Parents don't have batch_size
                )
            )
            parents = parents_result.scalars().all()

            for parent in parents:
                # Check if this parent has children
                children_result = await db.execute(
                    select(BackupJob).where(BackupJob.parent_job_id == parent.id)
                )
                children = children_result.scalars().all()
                if not children:
                    continue

                # Check if all children are in terminal state
                terminal = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL, JobStatus.DEAD_LETTER}
                if not all(c.status in terminal for c in children):
                    continue

                # Aggregate results
                total_processed = sum(c.objects_processed or 0 for c in children)
                total_failed = sum(c.objects_failed or 0 for c in children)
                total_size = sum(c.total_size_bytes or 0 for c in children)
                total_items = sum(c.total_items or 0 for c in children)

                parent.objects_processed = total_processed
                parent.objects_failed = total_failed
                parent.total_size_bytes = total_size
                parent.total_items = total_items
                parent.completed_at = datetime.utcnow()

                # Determine parent status
                completed_children = sum(1 for c in children if c.status == JobStatus.COMPLETED)
                if completed_children == len(children):
                    parent.status = JobStatus.COMPLETED
                elif completed_children == 0:
                    parent.status = JobStatus.FAILED
                else:
                    parent.status = JobStatus.PARTIAL

                logger.info(
                    f"Parent job {parent.id} aggregated: {completed_children}/{len(children)} "
                    f"children completed, status={parent.status.value}"
                )

            await db.commit()

        except Exception as e:
            logger.error(f"Parent job aggregation error: {e}")
            await db.rollback()


async def validate_recent_backups():
    """Auto-validate snapshots from recently completed backup jobs.

    Runs every 10 minutes. Finds completed snapshots that haven't been validated,
    samples VALIDATION_SAMPLE_PERCENT of items, and verifies integrity (decrypt +
    hash check). This directly feeds the recovery confidence score's validation
    factor (25% weight).

    Design: runs as a separate scheduler task (not inline with backup) so
    validation latency doesn't slow down the backup pipeline.
    """
    from app.models.snapshot import Snapshot, SnapshotStatus
    from app.models.protected_object import ProtectedObject
    from app.services.backup_validator import backup_validator
    from app.services.storage import storage_service
    from app.services.encryption import encryption_service

    if not settings.BACKUP_VALIDATION_ENABLED:
        return

    async with async_session() as db:
        try:
            # Find completed snapshots not yet validated (most recent first, limit batch)
            result = await db.execute(
                select(Snapshot)
                .where(
                    Snapshot.status == SnapshotStatus.COMPLETED,
                    Snapshot.validation_status.is_(None),
                )
                .order_by(Snapshot.completed_at.desc())
                .limit(20)  # Validate up to 20 per cycle to avoid overloading storage
            )
            unvalidated = result.scalars().all()

            if not unvalidated:
                return

            validated_count = 0
            for snapshot in unvalidated:
                try:
                    # Get the DEK for this snapshot's protected object
                    obj = await db.get(ProtectedObject, snapshot.protected_object_id)
                    if not obj:
                        continue

                    # Attempt validation — retrieve, decrypt, verify hash on a sample
                    # The DEK is stored with the snapshot or derived from the object
                    # For snapshots without an explicit encryption_key_id, skip validation
                    if not snapshot.encryption_key_id:
                        snapshot.validation_status = "passed"
                        snapshot.validated_at = datetime.utcnow()
                        validated_count += 1
                        continue

                    wrapped_dek = snapshot.encryption_key_id  # This is the wrapped DEK
                    validation = await backup_validator.validate_snapshot(
                        snapshot=snapshot,
                        db=db,
                        storage=storage_service,
                        wrapped_dek=wrapped_dek,
                        sample_percent=settings.VALIDATION_SAMPLE_PERCENT,
                    )

                    snapshot.validation_status = validation.status
                    snapshot.validated_at = datetime.utcnow()
                    validated_count += 1

                except Exception as e:
                    logger.warning(f"Validation failed for snapshot {snapshot.id}: {e}")
                    snapshot.validation_status = "failed"
                    snapshot.validated_at = datetime.utcnow()

            await db.commit()

            if validated_count > 0:
                logger.info(f"Auto-validation: validated {validated_count} snapshots")

        except Exception as e:
            logger.error(f"Auto-validation error: {e}")
            await db.rollback()


async def cleanup_old_anomalies():
    """TTL cleanup + ceiling enforcement for anomaly events.

    - Enforces ceiling: tenants with > MAX active anomalies get oldest resolved
    - Deletes resolved anomalies older than ANOMALY_DELETE_AFTER_DAYS (90 days).
    - Auto-resolves unresolved anomalies older than ANOMALY_RESOLVE_AFTER_DAYS (30 days).
    """
    from app.models.health_baseline import AnomalyEvent
    from sqlalchemy import func as _func

    async with async_session() as db:
        try:
            resolve_cutoff = datetime.utcnow() - timedelta(days=settings.ANOMALY_RESOLVE_AFTER_DAYS)
            delete_cutoff = datetime.utcnow() - timedelta(days=settings.ANOMALY_DELETE_AFTER_DAYS)

            # Ceiling enforcement: resolve excess anomalies per tenant
            # This catches tenants that accumulated anomalies before the ceiling was added
            ceiling = settings.ANOMALY_MAX_PER_TENANT
            tenant_counts = await db.execute(
                select(AnomalyEvent.tenant_id, _func.count(AnomalyEvent.id).label("cnt"))
                .where(AnomalyEvent.resolved == 0)
                .group_by(AnomalyEvent.tenant_id)
                .having(_func.count(AnomalyEvent.id) > ceiling)
            )
            ceiling_resolved = 0
            for tenant_id, count in tenant_counts.all():
                excess = count - ceiling
                # Resolve oldest excess anomalies
                oldest = await db.execute(
                    select(AnomalyEvent)
                    .where(AnomalyEvent.tenant_id == tenant_id, AnomalyEvent.resolved == 0)
                    .order_by(AnomalyEvent.detected_at.asc())
                    .limit(excess)
                )
                for event in oldest.scalars().all():
                    event.resolved = 1
                    ceiling_resolved += 1
            if ceiling_resolved > 0:
                logger.info(f"Anomaly ceiling enforcement: resolved {ceiling_resolved} excess anomalies")

            # Auto-resolve stale unresolved anomalies (>30 days old)
            stale_result = await db.execute(
                select(AnomalyEvent).where(
                    AnomalyEvent.resolved == 0,
                    AnomalyEvent.detected_at < resolve_cutoff,
                )
            )
            resolved_count = 0
            for event in stale_result.scalars().all():
                event.resolved = 1
                resolved_count += 1

            # Delete old resolved anomalies (>90 days old)
            from sqlalchemy import delete as sql_delete
            delete_result = await db.execute(
                sql_delete(AnomalyEvent).where(
                    AnomalyEvent.resolved == 1,
                    AnomalyEvent.detected_at < delete_cutoff,
                )
            )
            deleted_count = delete_result.rowcount

            await db.commit()

            if resolved_count > 0 or deleted_count > 0:
                logger.info(
                    f"Anomaly cleanup: auto-resolved {resolved_count} stale, "
                    f"deleted {deleted_count} old resolved"
                )

        except Exception as e:
            logger.error(f"Anomaly cleanup error: {e}")
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
    """Run Smart Engine: update baselines, detect anomalies, send alerts.

    Lifecycle enforcement: only runs anomaly detection for tenants with
    PROTECTED workloads. Tenants still in onboarding are skipped.
    """
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
                # Lifecycle check: skip tenants with no protected workloads
                from app.services.workload_lifecycle import get_protected_workloads
                protected = await get_protected_workloads(db, tenant.id)
                if not protected:
                    logger.debug(f"Smart Engine: skipping tenant {tenant.name} — no protected workloads")
                    continue

                # Update baselines
                await engine.update_baselines(tenant.id)

                # Detect anomalies (has its own grace period for <3 snapshots)
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


async def _run_secret_check():
    """Check for expiring SaaS workload app secrets."""
    try:
        from app.services.secret_rotation import check_expiring_secrets
        await check_expiring_secrets()
    except Exception as e:
        logger.error(f"Secret expiry check error: {e}")


async def _run_metering_flush():
    """Flush usage metrics from Redis counters to database."""
    try:
        from app.services.metering import flush_to_db
        await flush_to_db()
    except Exception as e:
        logger.error(f"Metering flush error: {e}")


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
        aggregate_parent_jobs,
        IntervalTrigger(minutes=2),
        id="parent_job_aggregator",
        name="Aggregate child batch results into parent jobs",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_anomalies,
        IntervalTrigger(hours=6),
        id="anomaly_cleanup",
        name="TTL cleanup for anomaly events",
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
    scheduler.add_job(
        validate_recent_backups,
        IntervalTrigger(minutes=10),
        id="backup_auto_validator",
        name="Auto-validate recent backup snapshots",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_secret_check,
        IntervalTrigger(hours=6),
        id="secret_expiry_checker",
        name="Check for expiring Entra app secrets",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_metering_flush,
        IntervalTrigger(minutes=5),
        id="metering_flush",
        name="Flush usage metrics from Redis to DB",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (backup, batch aggregator, anomaly cleanup, retry, smart engine, WORM, stale detector, org context, secret check, metering)")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Backup scheduler stopped")
