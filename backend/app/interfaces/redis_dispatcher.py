"""Redis-backed job dispatcher for distributed worker deployment.

Enqueues backup/restore jobs into Redis lists for separate worker
processes to pick up. Falls back to InProcessDispatcher on Redis failure.

Queues:
- shieldio:backup_queue — backup object and backup job messages
- shieldio:restore_queue — restore job messages
"""
import json
import logging

from app.interfaces.job_dispatcher import JobDispatcher, InProcessDispatcher
from app.interfaces.job_message import (
    BackupObjectMessage, BackupJobMessage, RestoreJobMessage, JobResult
)

logger = logging.getLogger(__name__)

BACKUP_QUEUE = "shieldio:backup_queue"
RESTORE_QUEUE = "shieldio:restore_queue"


class RedisDispatcher(JobDispatcher):
    """Dispatch jobs via Redis queue for separate worker processes.

    On Redis failure, automatically falls back to in-process execution.
    """

    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self._fallback = InProcessDispatcher()

    async def dispatch_backup_object(self, msg: BackupObjectMessage, **kwargs) -> JobResult:
        try:
            await self.redis.lpush(BACKUP_QUEUE, msg.model_dump_json())
            logger.debug(f"Enqueued backup object {msg.protected_object_id}")
            return JobResult(success=True, status="queued")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-process: {e}")
            return await self._fallback.dispatch_backup_object(msg, **kwargs)

    async def dispatch_backup_job(self, msg: BackupJobMessage, **kwargs) -> JobResult:
        try:
            await self.redis.lpush(BACKUP_QUEUE, msg.model_dump_json())
            logger.debug(f"Enqueued backup job {msg.backup_job_id}")
            return JobResult(success=True, job_id=msg.backup_job_id, status="queued")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-process: {e}")
            return await self._fallback.dispatch_backup_job(msg, **kwargs)

    async def dispatch_restore(self, msg: RestoreJobMessage, **kwargs) -> JobResult:
        try:
            await self.redis.lpush(RESTORE_QUEUE, msg.model_dump_json())
            logger.debug(f"Enqueued restore job {msg.restore_job_id}")
            return JobResult(success=True, job_id=msg.restore_job_id, status="queued")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-process: {e}")
            return await self._fallback.dispatch_restore(msg, **kwargs)

    async def queue_length(self) -> dict:
        """Get current queue lengths (for health checks)."""
        try:
            backup_len = await self.redis.llen(BACKUP_QUEUE)
            restore_len = await self.redis.llen(RESTORE_QUEUE)
            return {"backup_queue": backup_len, "restore_queue": restore_len}
        except Exception:
            return {"backup_queue": -1, "restore_queue": -1}
