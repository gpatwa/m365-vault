"""Retry engine for failed backup jobs and snapshots.

Handles:
1. Automatic retry of failed backup jobs (up to max_retries)
2. Retry of only the failed objects within a partially-failed job
3. Manual retry via API endpoint
4. Exponential backoff between job-level retries
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backup_job import BackupJob, JobStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.services.backup_engine import BackupEngine

logger = logging.getLogger(__name__)

# Backoff intervals between job retries: 5min, 15min, 45min
JOB_RETRY_DELAYS_MINUTES = [5, 15, 45]


class RetryEngine:
    """Processes failed backup jobs and retries them with backoff."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_failed_jobs(self) -> dict:
        """Scan for failed/partial jobs eligible for retry and re-execute them.

        A job is eligible if:
        - status is FAILED or PARTIAL
        - retry_count < max_retries
        - enough time has elapsed since last attempt (backoff)

        Returns summary dict.
        """
        result = await self.db.execute(
            select(BackupJob).where(
                BackupJob.status.in_([JobStatus.FAILED, JobStatus.PARTIAL]),
                BackupJob.retry_count < BackupJob.max_retries,
            ).order_by(BackupJob.completed_at)
        )
        failed_jobs = result.scalars().all()

        retried = 0
        skipped = 0
        succeeded = 0
        still_failed = 0

        for job in failed_jobs:
            # Check backoff: wait longer between each retry
            delay_idx = min(job.retry_count, len(JOB_RETRY_DELAYS_MINUTES) - 1)
            required_delay = timedelta(minutes=JOB_RETRY_DELAYS_MINUTES[delay_idx])

            if job.completed_at and (datetime.utcnow() - job.completed_at) < required_delay:
                skipped += 1
                continue

            logger.info(
                f"Retrying job {job.id} (attempt {job.retry_count + 1}/{job.max_retries}) — "
                f"previous status: {job.status.value}"
            )

            try:
                await self._retry_job(job)
                retried += 1
                if job.status == JobStatus.COMPLETED:
                    succeeded += 1
                else:
                    still_failed += 1
            except Exception as e:
                logger.error(f"Retry of job {job.id} errored: {e}")
                still_failed += 1

        summary = {
            "scanned": len(failed_jobs),
            "retried": retried,
            "skipped_backoff": skipped,
            "succeeded": succeeded,
            "still_failed": still_failed,
        }
        logger.info(f"Retry engine summary: {summary}")

        # Send alert if there are persistent failures after retries
        if still_failed > 0:
            try:
                from app.services.alert_service import alert_service
                failed_workloads = set()
                for job in failed_jobs:
                    if job.status in (JobStatus.FAILED, JobStatus.PARTIAL) and job.retry_count >= job.max_retries:
                        failed_workloads.add(job.workload_type)

                if failed_workloads:
                    await alert_service.notify(
                        event_type="backup.failed",
                        title=f"{len(failed_workloads)} workload(s) have persistent backup failures",
                        details=f"Workloads: {', '.join(failed_workloads)}. {still_failed} job(s) failed after all retry attempts.",
                        severity="error",
                    )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

        return summary

    async def _retry_job(self, job: BackupJob):
        """Retry a single failed/partial job.

        For PARTIAL jobs: only retry the objects that failed.
        For FAILED jobs: retry all objects.
        """
        job.retry_count += 1
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        job.completed_at = None
        job.error_message = None

        # Determine which objects to retry
        failed_object_ids = self._get_failed_object_ids(job)
        await self.db.commit()

        engine = BackupEngine(self.db)

        if failed_object_ids:
            # Targeted retry: only the failed objects
            await self._retry_specific_objects(engine, job, failed_object_ids)
        else:
            # Full retry
            await engine._execute_backup_job(job)

    def _get_failed_object_ids(self, job: BackupJob) -> list[int]:
        """Extract the IDs of objects that failed in a previous run."""
        if job.failed_object_ids:
            try:
                return json.loads(job.failed_object_ids)
            except (json.JSONDecodeError, TypeError):
                pass

        if not job.progress_details:
            return []

        try:
            progress = json.loads(job.progress_details)
            failed_ids = []
            for obj_id, info in progress.get("objects", {}).items():
                if info.get("status") == "failed":
                    failed_ids.append(int(obj_id))
            return failed_ids
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    async def _retry_specific_objects(
        self, engine: BackupEngine, job: BackupJob, object_ids: list[int]
    ):
        """Retry backup for specific failed objects within a job."""
        result = await self.db.execute(
            select(ProtectedObject).where(ProtectedObject.id.in_(object_ids))
        )
        objects = result.scalars().all()

        if not objects:
            job.status = JobStatus.FAILED
            job.error_message = "No matching objects found for retry"
            job.completed_at = datetime.utcnow()
            await self.db.commit()
            return

        new_failed_ids = []
        succeeded = 0

        for obj in objects:
            try:
                await engine.run_backup_for_object(obj, job=job)
                job.objects_processed += 1
                succeeded += 1
            except Exception as e:
                job.objects_failed += 1
                new_failed_ids.append(obj.id)
                logger.error(f"Retry failed for {obj.display_name}: {e}")
            await self.db.commit()

        # Update failed_object_ids for next retry
        job.failed_object_ids = json.dumps(new_failed_ids) if new_failed_ids else None

        # Determine final status
        if not new_failed_ids:
            job.status = JobStatus.COMPLETED
        elif succeeded > 0:
            job.status = JobStatus.PARTIAL
        else:
            job.status = JobStatus.FAILED

        job.completed_at = datetime.utcnow()
        await self.db.commit()

    async def retry_single_job(self, job_id: int) -> dict:
        """Manually retry a specific failed job. Called from API endpoint."""
        job = await self.db.get(BackupJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status not in (JobStatus.FAILED, JobStatus.PARTIAL):
            raise ValueError(f"Job {job_id} is not in a failed state (status: {job.status.value})")

        await self._retry_job(job)

        return {
            "job_id": job.id,
            "status": job.status.value,
            "retry_count": job.retry_count,
            "objects_processed": job.objects_processed,
            "objects_failed": job.objects_failed,
        }

    async def retry_failed_snapshot(self, snapshot_id: int) -> dict:
        """Retry a single failed snapshot backup."""
        snapshot = await self.db.get(Snapshot, snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        if snapshot.status != SnapshotStatus.FAILED:
            raise ValueError(f"Snapshot {snapshot_id} is not failed (status: {snapshot.status.value})")

        obj = await self.db.get(ProtectedObject, snapshot.protected_object_id)
        if not obj:
            raise ValueError(f"Protected object for snapshot {snapshot_id} not found")

        engine = BackupEngine(self.db)
        new_snapshot = await engine.run_backup_for_object(obj)

        return {
            "original_snapshot_id": snapshot_id,
            "new_snapshot_id": new_snapshot.id,
            "status": new_snapshot.status.value,
            "item_count": new_snapshot.item_count,
            "size_bytes": new_snapshot.size_bytes,
        }

    async def get_failed_jobs_summary(self) -> dict:
        """Get a summary of all failed/partial jobs and their retry eligibility."""
        result = await self.db.execute(
            select(BackupJob).where(
                BackupJob.status.in_([JobStatus.FAILED, JobStatus.PARTIAL])
            ).order_by(BackupJob.completed_at.desc())
        )
        failed_jobs = result.scalars().all()

        jobs_info = []
        for job in failed_jobs:
            can_retry = job.retry_count < job.max_retries

            # Check backoff
            backoff_ready = True
            next_retry_at = None
            if can_retry and job.completed_at:
                delay_idx = min(job.retry_count, len(JOB_RETRY_DELAYS_MINUTES) - 1)
                required_delay = timedelta(minutes=JOB_RETRY_DELAYS_MINUTES[delay_idx])
                next_retry_at = job.completed_at + required_delay
                backoff_ready = datetime.utcnow() >= next_retry_at

            failed_objects = self._get_failed_object_ids(job)

            jobs_info.append({
                "job_id": job.id,
                "workload_type": job.workload_type,
                "status": job.status.value,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "can_auto_retry": can_retry,
                "backoff_ready": backoff_ready,
                "next_retry_at": next_retry_at.isoformat() if next_retry_at else None,
                "objects_total": job.objects_total,
                "objects_processed": job.objects_processed,
                "objects_failed": job.objects_failed,
                "failed_object_ids": failed_objects,
                "error_message": job.error_message,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            })

        return {
            "total_failed": len(jobs_info),
            "retriable": sum(1 for j in jobs_info if j["can_auto_retry"]),
            "ready_now": sum(1 for j in jobs_info if j["can_auto_retry"] and j["backoff_ready"]),
            "jobs": jobs_info,
        }
