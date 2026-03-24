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
"""
import asyncio
import json
import logging
import signal
import sys

from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("shieldio.worker")

shutdown_event = asyncio.Event()


async def process_backup_message(raw: str):
    """Process a backup message from the queue."""
    from app.database import async_session
    from app.interfaces.job_message import BackupObjectMessage, BackupJobMessage

    data = json.loads(raw)
    job_type = data.get("job_type")

    async with async_session() as db:
        from app.services.backup_engine import BackupEngine
        engine = BackupEngine(db)

        try:
            if job_type == "backup_object":
                msg = BackupObjectMessage(**data)
                from app.models.protected_object import ProtectedObject
                from app.models.backup_job import BackupJob

                obj = await db.get(ProtectedObject, msg.protected_object_id)
                if not obj:
                    logger.error(f"Protected object {msg.protected_object_id} not found")
                    return

                job = await db.get(BackupJob, msg.backup_job_id) if msg.backup_job_id else None
                snapshot = await engine.run_backup_for_object(obj, job=job)
                logger.info(f"Backup complete: object {obj.display_name} → snapshot {snapshot.id} ({snapshot.item_count} items)")

            elif job_type == "backup_job":
                msg = BackupJobMessage(**data)
                from app.models.backup_job import BackupJob

                job = await db.get(BackupJob, msg.backup_job_id)
                if not job:
                    logger.error(f"Backup job {msg.backup_job_id} not found")
                    return

                await engine._execute_backup_job(job)
                logger.info(f"Job {job.id} complete: {job.objects_processed}/{job.objects_total} objects")

            await db.commit()

        except Exception as e:
            logger.error(f"Backup execution failed: {e}", exc_info=True)
            await db.rollback()


async def process_restore_message(raw: str):
    """Process a restore message from the queue."""
    from app.database import async_session
    from app.interfaces.job_message import RestoreJobMessage

    data = json.loads(raw)
    msg = RestoreJobMessage(**data)

    async with async_session() as db:
        try:
            from app.services.restore_engine import RestoreEngine
            from app.models.restore_job import RestoreJob

            job = await db.get(RestoreJob, msg.restore_job_id)
            if not job:
                logger.error(f"Restore job {msg.restore_job_id} not found")
                return

            engine = RestoreEngine(db)
            await engine.execute_restore(job)
            await db.commit()
            logger.info(f"Restore job {job.id} complete")

        except Exception as e:
            logger.error(f"Restore execution failed: {e}", exc_info=True)
            await db.rollback()


async def worker_loop(worker_id: int):
    """Single worker loop — polls Redis and processes messages."""
    import redis.asyncio as aioredis
    from app.interfaces.redis_dispatcher import BACKUP_QUEUE, RESTORE_QUEUE

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info(f"Worker-{worker_id} started, listening on queues...")

    while not shutdown_event.is_set():
        try:
            result = await r.brpop([BACKUP_QUEUE, RESTORE_QUEUE], timeout=5)
            if result is None:
                continue  # Timeout, check shutdown flag

            queue, raw = result

            if queue == BACKUP_QUEUE:
                await process_backup_message(raw)
            elif queue == RESTORE_QUEUE:
                await process_restore_message(raw)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker-{worker_id} error: {e}", exc_info=True)
            await asyncio.sleep(1)

    logger.info(f"Worker-{worker_id} shutting down")
    await r.close()


async def main():
    """Initialize and run worker processes."""
    logger.info(f"Shieldio Data Plane Worker starting...")
    logger.info(f"Redis: {settings.REDIS_URL}")
    logger.info(f"Concurrency: {settings.WORKER_CONCURRENCY}")

    # Initialize DB engine (same as API lifespan)
    from app.database import init_db
    await init_db()
    logger.info("Database initialized")

    # Initialize storage backend
    from app.services.storage_factory import create_storage_backend
    from app.services import storage as storage_module
    backend = create_storage_backend()
    storage_module.storage_service = storage_module.StorageService(backend)
    logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: shutdown_event.set())

    # Run N concurrent worker loops
    concurrency = settings.WORKER_CONCURRENCY
    logger.info(f"Starting {concurrency} worker task(s)...")

    tasks = [asyncio.create_task(worker_loop(i)) for i in range(concurrency)]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass

    logger.info("All workers stopped. Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
