"""Shieldio Data Plane Worker — standalone process for backup/restore execution.

This is the worker process that runs separately from the API server.
It polls Redis queues for jobs and executes them using BackupEngine/RestoreEngine.

Usage:
    python -m app.worker

Environment:
    REDIS_URL: Redis connection URL (required)
    DATABASE_URL: PostgreSQL connection URL (required)
    WORKER_CONCURRENCY: Number of concurrent tasks (default: 3)
    All storage/encryption env vars same as API server

Architecture:
    Control Plane (API)  →  Redis Queue  →  Data Plane (Worker)
    - Scheduler creates jobs              - Picks up from queue
    - API dispatches on-demand            - Executes BackupEngine
    - Analytics/reporting                 - Writes to storage

Durability:
    Every message in Redis has a matching WorkerQueueEntry in the DB.
    On startup the worker replays any QUEUED or interrupted (PROCESSING)
    entries so no jobs are lost across Redis restarts or worker crashes.

Dead-letter:
    On failure the entry's retry_count is incremented and the message is
    re-enqueued.  Once retry_count reaches max_retries the entry is
    marked DEAD_LETTER and the associated BackupJob/RestoreJob (if any)
    is updated to reflect that status.
"""
import asyncio
import json
import logging
import signal
from datetime import datetime

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shieldio.worker")

shutdown_event = asyncio.Event()


# ── Job execution ──────────────────────────────────────────────────────────

async def process_backup_message(data: dict):
    """Execute a backup message.  Raises on failure so the caller can retry."""
    from app.database import async_session
    from app.interfaces.job_message import BackupObjectMessage, BackupJobMessage

    job_type = data.get("job_type")

    async with async_session() as db:
        from app.services.backup_engine import BackupEngine
        engine = BackupEngine(db)

        if job_type == "backup_object":
            msg = BackupObjectMessage(**data)
            from app.models.protected_object import ProtectedObject
            from app.models.backup_job import BackupJob

            obj = await db.get(ProtectedObject, msg.protected_object_id)
            if not obj:
                raise ValueError(f"Protected object {msg.protected_object_id} not found")

            job = await db.get(BackupJob, msg.backup_job_id) if msg.backup_job_id else None
            snapshot = await engine.run_backup_for_object(obj, job=job)
            logger.info(
                f"Backup complete: {obj.display_name} → snapshot {snapshot.id} "
                f"({snapshot.item_count} items)"
            )

        elif job_type == "backup_job":
            msg = BackupJobMessage(**data)
            from app.models.backup_job import BackupJob

            job = await db.get(BackupJob, msg.backup_job_id)
            if not job:
                raise ValueError(f"Backup job {msg.backup_job_id} not found")

            await engine._execute_backup_job(job)
            logger.info(f"Job {job.id} complete: {job.objects_processed}/{job.objects_total} objects")

        else:
            raise ValueError(f"Unknown backup job_type: {job_type!r}")

        await db.commit()


async def process_restore_message(data: dict):
    """Execute a restore message.  Raises on failure so the caller can retry."""
    from app.database import async_session
    from app.interfaces.job_message import RestoreJobMessage

    msg = RestoreJobMessage(**data)

    async with async_session() as db:
        from app.services.restore_engine import RestoreEngine
        from app.models.restore_job import RestoreJob

        job = await db.get(RestoreJob, msg.restore_job_id)
        if not job:
            raise ValueError(f"Restore job {msg.restore_job_id} not found")

        engine = RestoreEngine(db)
        await engine.execute_restore(job)
        await db.commit()
        logger.info(f"Restore job {job.id} complete")


# ── WorkerQueueEntry lifecycle helpers ────────────────────────────────────

async def _mark_processing(entry_id: int):
    from app.database import async_session
    from app.models.worker_queue import WorkerQueueEntry, WorkerQueueStatus

    async with async_session() as db:
        entry = await db.get(WorkerQueueEntry, entry_id)
        if entry:
            entry.status = WorkerQueueStatus.PROCESSING
            entry.last_attempted_at = datetime.utcnow()
            await db.commit()


async def _mark_completed(entry_id: int):
    from app.database import async_session
    from app.models.worker_queue import WorkerQueueEntry, WorkerQueueStatus

    async with async_session() as db:
        entry = await db.get(WorkerQueueEntry, entry_id)
        if entry:
            entry.status = WorkerQueueStatus.COMPLETED
            await db.commit()


async def _handle_failure(entry_id: int, queue: str, raw: str, error: Exception, r):
    """Retry or dead-letter a failed job based on retry_count vs max_retries."""
    from app.database import async_session
    from app.models.worker_queue import WorkerQueueEntry, WorkerQueueStatus

    async with async_session() as db:
        entry = await db.get(WorkerQueueEntry, entry_id)
        if not entry:
            logger.error(f"WorkerQueueEntry {entry_id} not found during failure handling")
            return

        entry.retry_count += 1
        entry.error_message = str(error)[:2000]
        entry.last_attempted_at = datetime.utcnow()

        if entry.retry_count >= entry.max_retries:
            entry.status = WorkerQueueStatus.DEAD_LETTER
            await _dead_letter_linked_job(raw, db)
            logger.warning(
                f"Job entry {entry_id} dead-lettered after {entry.retry_count} attempts: {error}"
            )
        else:
            entry.status = WorkerQueueStatus.QUEUED
            # Re-enqueue the same raw message (already contains queue_entry_id)
            await r.lpush(queue, raw)
            logger.info(
                f"Job entry {entry_id} re-queued "
                f"(attempt {entry.retry_count}/{entry.max_retries}): {error}"
            )

        await db.commit()


async def _dead_letter_linked_job(raw: str, db):
    """Set DEAD_LETTER status on the BackupJob or RestoreJob linked to this message."""
    try:
        data = json.loads(raw)
        job_type = data.get("job_type")

        if job_type == "backup_job":
            from app.models.backup_job import BackupJob, JobStatus
            job = await db.get(BackupJob, data.get("backup_job_id"))
            if job and hasattr(JobStatus, "DEAD_LETTER"):
                job.status = JobStatus.DEAD_LETTER

        elif job_type == "restore":
            from app.models.restore_job import RestoreJob, RestoreStatus
            job = await db.get(RestoreJob, data.get("restore_job_id"))
            if job and hasattr(RestoreStatus, "DEAD_LETTER"):
                job.status = RestoreStatus.DEAD_LETTER

    except Exception as e:
        logger.warning(f"Could not update linked job status to dead_letter: {e}")


# ── Startup replay ─────────────────────────────────────────────────────────

async def replay_queued_jobs(r):
    """Re-push any QUEUED or interrupted PROCESSING entries into Redis.

    Called once at startup.  Handles two recovery scenarios:
    - QUEUED: Redis was restarted and lost its in-memory queue.
    - PROCESSING: Worker crashed mid-execution; we retry the job.
    """
    from app.database import async_session
    from app.models.worker_queue import WorkerQueueEntry, WorkerQueueStatus
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(
            select(WorkerQueueEntry).where(
                WorkerQueueEntry.status.in_([
                    WorkerQueueStatus.QUEUED,
                    WorkerQueueStatus.PROCESSING,
                ])
            ).order_by(WorkerQueueEntry.created_at)
        )
        entries = result.scalars().all()

        if not entries:
            return

        replayed = 0
        for entry in entries:
            # Embed entry id so the worker can update status
            payload = json.loads(entry.message_json)
            payload["queue_entry_id"] = entry.id
            await r.lpush(entry.queue, json.dumps(payload))
            # Reset to QUEUED so it's treated as a fresh attempt
            entry.status = WorkerQueueStatus.QUEUED
            replayed += 1

        await db.commit()
        logger.info(f"Replayed {replayed} durable job(s) from DB into Redis")


# ── Worker loop ────────────────────────────────────────────────────────────

async def worker_loop(worker_id: int):
    """Single worker coroutine — polls Redis and processes messages."""
    import redis.asyncio as aioredis
    from app.interfaces.redis_dispatcher import BACKUP_QUEUE, RESTORE_QUEUE

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info(f"Worker-{worker_id} started, listening on queues…")

    while not shutdown_event.is_set():
        try:
            result = await r.brpop([BACKUP_QUEUE, RESTORE_QUEUE], timeout=5)
            if result is None:
                continue  # Timeout — check shutdown flag

            queue, raw = result
            data = json.loads(raw)
            entry_id = data.get("queue_entry_id")

            # Mark as in-flight before execution
            if entry_id:
                await _mark_processing(entry_id)

            try:
                if queue == BACKUP_QUEUE:
                    await process_backup_message(data)
                elif queue == RESTORE_QUEUE:
                    await process_restore_message(data)

                if entry_id:
                    await _mark_completed(entry_id)

            except Exception as e:
                logger.error(f"Worker-{worker_id} job failed: {e}", exc_info=True)
                if entry_id:
                    await _handle_failure(entry_id, queue, raw, e, r)
                # If no entry_id (pre-durability message) we just log and move on

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker-{worker_id} loop error: {e}", exc_info=True)
            await asyncio.sleep(1)

    logger.info(f"Worker-{worker_id} shutting down")
    await r.aclose()


# ── Main ───────────────────────────────────────────────────────────────────

async def main():
    """Initialize and run worker processes."""
    logger.info("Shieldio Data Plane Worker starting…")
    logger.info(f"Redis: {settings.REDIS_URL}")
    logger.info(f"Concurrency: {settings.WORKER_CONCURRENCY}")

    # Initialize DB (creates tables including worker_queue)
    from app.database import init_db
    await init_db()
    logger.info("Database initialized")

    # Initialize storage backend
    from app.services.storage_factory import create_storage_backend
    from app.services import storage as storage_module
    backend = create_storage_backend()
    storage_module.storage_service = storage_module.StorageService(backend)
    logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")

    # Handle graceful shutdown signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: shutdown_event.set())

    # Replay any jobs that were queued/interrupted before this startup
    import redis.asyncio as aioredis
    r_startup = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await replay_queued_jobs(r_startup)
    except Exception as e:
        logger.warning(f"Startup replay failed (non-fatal): {e}")
    finally:
        await r_startup.aclose()

    # Run N concurrent worker loops
    concurrency = settings.WORKER_CONCURRENCY
    logger.info(f"Starting {concurrency} worker task(s)…")

    tasks = [asyncio.create_task(worker_loop(i)) for i in range(concurrency)]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass

    logger.info("All workers stopped. Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
