"""Redis-backed job dispatcher for distributed worker deployment.

Enqueues backup/restore jobs into Redis lists for separate worker
processes to pick up.  Every message is first written to the worker_queue
DB table so Redis is purely a transport — jobs survive Redis restarts and
are replayed by the worker on startup.

Falls back to InProcessDispatcher on Redis failure (DB entry is already
persisted so the worker will replay it on next startup if needed).

Queues:
- kavachiq:backup_queue — backup object and backup job messages
- kavachiq:restore_queue — restore job messages
"""
import json
import logging

from app.interfaces.job_dispatcher import JobDispatcher, InProcessDispatcher
from app.interfaces.job_message import (
    BackupObjectMessage, BackupJobMessage, RestoreJobMessage, JobResult
)

logger = logging.getLogger(__name__)

BACKUP_QUEUE = "kavachiq:backup_queue"
RESTORE_QUEUE = "kavachiq:restore_queue"


class RedisDispatcher(JobDispatcher):
    """Dispatch jobs via Redis queue for separate worker processes.

    Persistence guarantee: every dispatch first writes a WorkerQueueEntry
    to the DB before touching Redis.  The worker embeds the entry id in
    the Redis message so it can update the entry status.

    On Redis failure, falls back to InProcessDispatcher and marks the DB
    entry as completed/failed inline.
    """

    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self._fallback = InProcessDispatcher()

    # ── Public dispatch interface ──────────────────────────────────────────

    async def dispatch_backup_object(self, msg: BackupObjectMessage, **kwargs) -> JobResult:
        entry_id = await self._persist(BACKUP_QUEUE, msg.model_dump_json())
        payload = msg.model_dump()
        payload["queue_entry_id"] = entry_id

        try:
            await self.redis.lpush(BACKUP_QUEUE, json.dumps(payload))
            logger.debug(f"Enqueued backup_object {msg.protected_object_id} (entry={entry_id})")
            return JobResult(success=True, status="queued")
        except Exception as e:
            logger.warning(f"Redis push failed (entry {entry_id} durable in DB), falling back: {e}")
            return await self._fallback_and_finish(
                entry_id, self._fallback.dispatch_backup_object, msg, **kwargs
            )

    async def dispatch_backup_job(self, msg: BackupJobMessage, **kwargs) -> JobResult:
        entry_id = await self._persist(BACKUP_QUEUE, msg.model_dump_json())
        payload = msg.model_dump()
        payload["queue_entry_id"] = entry_id

        try:
            await self.redis.lpush(BACKUP_QUEUE, json.dumps(payload))
            logger.debug(f"Enqueued backup_job {msg.backup_job_id} (entry={entry_id})")
            return JobResult(success=True, job_id=msg.backup_job_id, status="queued")
        except Exception as e:
            logger.warning(f"Redis push failed (entry {entry_id} durable in DB), falling back: {e}")
            return await self._fallback_and_finish(
                entry_id, self._fallback.dispatch_backup_job, msg, **kwargs
            )

    async def dispatch_restore(self, msg: RestoreJobMessage, **kwargs) -> JobResult:
        entry_id = await self._persist(RESTORE_QUEUE, msg.model_dump_json())
        payload = msg.model_dump()
        payload["queue_entry_id"] = entry_id

        try:
            await self.redis.lpush(RESTORE_QUEUE, json.dumps(payload))
            logger.debug(f"Enqueued restore {msg.restore_job_id} (entry={entry_id})")
            return JobResult(success=True, job_id=msg.restore_job_id, status="queued")
        except Exception as e:
            logger.warning(f"Redis push failed (entry {entry_id} durable in DB), falling back: {e}")
            return await self._fallback_and_finish(
                entry_id, self._fallback.dispatch_restore, msg, **kwargs
            )

    async def queue_length(self) -> dict:
        """Get current queue lengths (for health checks)."""
        try:
            backup_len = await self.redis.llen(BACKUP_QUEUE)
            restore_len = await self.redis.llen(RESTORE_QUEUE)
            return {"backup_queue": backup_len, "restore_queue": restore_len}
        except Exception:
            return {"backup_queue": -1, "restore_queue": -1}

    # ── Internal helpers ───────────────────────────────────────────────────

    async def _persist(self, queue: str, message_json: str) -> int:
        """Write a WorkerQueueEntry to DB and return its id."""
        from app.database import async_session
        from app.models.worker_queue import WorkerQueueEntry

        async with async_session() as db:
            entry = WorkerQueueEntry(queue=queue, message_json=message_json)
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return entry.id

    async def _fallback_and_finish(self, entry_id: int, fallback_fn, msg, **kwargs) -> JobResult:
        """Execute inline via fallback and update the DB entry with the outcome."""
        from app.database import async_session
        from app.models.worker_queue import WorkerQueueEntry, WorkerQueueStatus
        from datetime import datetime

        result = await fallback_fn(msg, **kwargs)

        async with async_session() as db:
            entry = await db.get(WorkerQueueEntry, entry_id)
            if entry:
                entry.status = (
                    WorkerQueueStatus.COMPLETED if result.success
                    else WorkerQueueStatus.DEAD_LETTER
                )
                entry.last_attempted_at = datetime.utcnow()
                if not result.success:
                    entry.error_message = result.error
                await db.commit()

        return result
