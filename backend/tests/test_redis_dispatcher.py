"""Tests for RedisDispatcher — enqueue behavior and fallback."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.interfaces.job_message import (
    BackupObjectMessage, BackupJobMessage, RestoreJobMessage, JobResult, JobType
)
from app.interfaces.redis_dispatcher import RedisDispatcher, BACKUP_QUEUE, RESTORE_QUEUE


# ── Helpers ──

def make_redis_dispatcher(mock_redis=None):
    """Create a RedisDispatcher with an injected mock Redis client."""
    dispatcher = RedisDispatcher.__new__(RedisDispatcher)
    dispatcher.redis = mock_redis or AsyncMock()
    from app.interfaces.job_dispatcher import InProcessDispatcher
    dispatcher._fallback = InProcessDispatcher()
    return dispatcher


# ── Queue name constants ──

class TestQueueNames:
    """Verify queue name constants match expected values."""

    def test_backup_queue_name(self):
        assert BACKUP_QUEUE == "kavachiq:backup_queue"

    def test_restore_queue_name(self):
        assert RESTORE_QUEUE == "kavachiq:restore_queue"

    def test_queue_names_distinct(self):
        assert BACKUP_QUEUE != RESTORE_QUEUE


# ── dispatch_backup_object ──

class TestRedisDispatchBackupObject:
    """Tests for dispatch_backup_object() enqueue behavior."""

    @pytest.mark.asyncio
    async def test_enqueues_to_backup_queue(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        dispatcher = make_redis_dispatcher(mock_redis)

        msg = BackupObjectMessage(protected_object_id=42)
        result = await dispatcher.dispatch_backup_object(msg)

        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == BACKUP_QUEUE

    @pytest.mark.asyncio
    async def test_message_payload_is_valid_json(self):
        mock_redis = AsyncMock()
        captured = {}

        async def capture_lpush(queue, payload):
            captured["queue"] = queue
            captured["payload"] = payload
            return 1

        mock_redis.lpush = capture_lpush
        dispatcher = make_redis_dispatcher(mock_redis)

        msg = BackupObjectMessage(protected_object_id=99, backup_job_id=7)
        await dispatcher.dispatch_backup_object(msg)

        data = json.loads(captured["payload"])
        assert data["protected_object_id"] == 99
        assert data["backup_job_id"] == 7
        assert data["job_type"] == JobType.BACKUP_OBJECT

    @pytest.mark.asyncio
    async def test_returns_queued_status(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        dispatcher = make_redis_dispatcher(mock_redis)

        result = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=1)
        )

        assert result.success is True
        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_fallback_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(side_effect=ConnectionError("Redis down"))
        dispatcher = make_redis_dispatcher(mock_redis)

        # Fallback dispatcher gets a db that returns None (object not found)
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=999), db=mock_db
        )

        # Should get a result from InProcessDispatcher (not an exception)
        assert isinstance(result, JobResult)
        assert result.success is False  # Object not found fallback

    @pytest.mark.asyncio
    async def test_fallback_returns_job_result_not_exception(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(side_effect=OSError("network error"))
        dispatcher = make_redis_dispatcher(mock_redis)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=1), db=mock_db
        )
        assert isinstance(result, JobResult)


# ── dispatch_backup_job ──

class TestRedisDispatchBackupJob:
    """Tests for dispatch_backup_job() enqueue behavior."""

    @pytest.mark.asyncio
    async def test_enqueues_to_backup_queue(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        dispatcher = make_redis_dispatcher(mock_redis)

        msg = BackupJobMessage(backup_job_id=55)
        await dispatcher.dispatch_backup_job(msg)

        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == BACKUP_QUEUE

    @pytest.mark.asyncio
    async def test_message_contains_job_id(self):
        mock_redis = AsyncMock()
        captured_payload = {}

        async def capture(queue, payload):
            captured_payload["data"] = payload
            return 1

        mock_redis.lpush = capture
        dispatcher = make_redis_dispatcher(mock_redis)

        msg = BackupJobMessage(backup_job_id=77)
        await dispatcher.dispatch_backup_job(msg)

        data = json.loads(captured_payload["data"])
        assert data["backup_job_id"] == 77
        assert data["job_type"] == JobType.BACKUP_JOB

    @pytest.mark.asyncio
    async def test_returns_queued_with_job_id(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        dispatcher = make_redis_dispatcher(mock_redis)

        result = await dispatcher.dispatch_backup_job(BackupJobMessage(backup_job_id=33))
        assert result.success is True
        assert result.job_id == 33
        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_fallback_on_connection_error(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        dispatcher = make_redis_dispatcher(mock_redis)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_backup_job(
            BackupJobMessage(backup_job_id=99), db=mock_db
        )
        assert isinstance(result, JobResult)


# ── dispatch_restore ──

class TestRedisDispatchRestore:
    """Tests for dispatch_restore() enqueue to restore queue."""

    @pytest.mark.asyncio
    async def test_enqueues_to_restore_queue(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        dispatcher = make_redis_dispatcher(mock_redis)

        msg = RestoreJobMessage(restore_job_id=10)
        await dispatcher.dispatch_restore(msg)

        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == RESTORE_QUEUE

    @pytest.mark.asyncio
    async def test_does_not_enqueue_to_backup_queue(self):
        queues_used = []
        mock_redis = AsyncMock()

        async def track_queue(queue, payload):
            queues_used.append(queue)
            return 1

        mock_redis.lpush = track_queue
        dispatcher = make_redis_dispatcher(mock_redis)

        await dispatcher.dispatch_restore(RestoreJobMessage(restore_job_id=5))

        assert BACKUP_QUEUE not in queues_used
        assert RESTORE_QUEUE in queues_used

    @pytest.mark.asyncio
    async def test_returns_queued_with_restore_job_id(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        dispatcher = make_redis_dispatcher(mock_redis)

        result = await dispatcher.dispatch_restore(RestoreJobMessage(restore_job_id=20))
        assert result.success is True
        assert result.job_id == 20
        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_fallback_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(side_effect=RuntimeError("timeout"))
        dispatcher = make_redis_dispatcher(mock_redis)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_restore(
            RestoreJobMessage(restore_job_id=88), db=mock_db
        )
        assert isinstance(result, JobResult)


# ── queue_length ──

class TestRedisQueueLength:
    """Tests for queue_length health check."""

    @pytest.mark.asyncio
    async def test_returns_queue_lengths(self):
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(side_effect=[5, 3])
        dispatcher = make_redis_dispatcher(mock_redis)

        lengths = await dispatcher.queue_length()

        assert lengths["backup_queue"] == 5
        assert lengths["restore_queue"] == 3

    @pytest.mark.asyncio
    async def test_returns_negative_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
        dispatcher = make_redis_dispatcher(mock_redis)

        lengths = await dispatcher.queue_length()

        assert lengths["backup_queue"] == -1
        assert lengths["restore_queue"] == -1

    @pytest.mark.asyncio
    async def test_empty_queues_return_zero(self):
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(side_effect=[0, 0])
        dispatcher = make_redis_dispatcher(mock_redis)

        lengths = await dispatcher.queue_length()
        assert lengths["backup_queue"] == 0
        assert lengths["restore_queue"] == 0
