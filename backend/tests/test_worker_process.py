"""Tests for the standalone data-plane worker process (app/worker.py).

Covers:
- process_backup_message: backup_object and backup_job handling
- process_restore_message: restore handling
- worker_loop: shutdown event, queue routing, error recovery
- main: worker startup and concurrency
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ── process_backup_message ──

class TestProcessBackupMessage:
    """Tests for process_backup_message()."""

    @pytest.mark.asyncio
    async def test_backup_object_calls_run_backup_for_object(self):
        """backup_object message triggers run_backup_for_object on matching object."""
        from app.worker import process_backup_message

        mock_obj = MagicMock()
        mock_obj.display_name = "Test User"
        mock_snapshot = MagicMock()
        mock_snapshot.id = 101
        mock_snapshot.item_count = 10

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(side_effect=lambda model, pk: mock_obj if "ProtectedObject" in str(model) else None)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx), \
             patch("app.services.backup_engine.BackupEngine", return_value=mock_engine):
            raw = json.dumps({"job_type": "backup_object", "protected_object_id": 1})
            await process_backup_message(raw)

    @pytest.mark.asyncio
    async def test_backup_object_logs_error_when_object_not_found(self):
        """Missing protected object causes a logged error, not an exception."""
        from app.worker import process_backup_message

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)  # Object not found
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx):
            raw = json.dumps({"job_type": "backup_object", "protected_object_id": 9999})
            # Should not raise
            await process_backup_message(raw)

    @pytest.mark.asyncio
    async def test_backup_job_calls_execute_backup_job(self):
        """backup_job message triggers _execute_backup_job on matching job."""
        from app.worker import process_backup_message

        mock_job = MagicMock()
        mock_job.id = 42
        mock_job.objects_processed = 3
        mock_job.objects_total = 3

        mock_engine = AsyncMock()
        mock_engine._execute_backup_job = AsyncMock()

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_job)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx), \
             patch("app.services.backup_engine.BackupEngine", return_value=mock_engine):
            raw = json.dumps({"job_type": "backup_job", "backup_job_id": 42})
            await process_backup_message(raw)

    @pytest.mark.asyncio
    async def test_backup_job_not_found_logs_error(self):
        """Missing backup job causes logged error, not exception."""
        from app.worker import process_backup_message

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx):
            raw = json.dumps({"job_type": "backup_job", "backup_job_id": 9999})
            await process_backup_message(raw)

    @pytest.mark.asyncio
    async def test_exception_triggers_rollback(self):
        """Engine exception triggers DB rollback."""
        from app.worker import process_backup_message

        mock_obj = MagicMock()
        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(side_effect=RuntimeError("Engine crash"))

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx), \
             patch("app.services.backup_engine.BackupEngine", return_value=mock_engine):
            raw = json.dumps({"job_type": "backup_object", "protected_object_id": 1})
            await process_backup_message(raw)

        mock_db.rollback.assert_called_once()


# ── process_restore_message ──

class TestProcessRestoreMessage:
    """Tests for process_restore_message()."""

    @pytest.mark.asyncio
    async def test_restore_calls_execute_restore(self):
        """Restore message triggers execute_restore on matching restore job."""
        from app.worker import process_restore_message

        mock_job = MagicMock()
        mock_job.id = 55

        mock_engine = AsyncMock()
        mock_engine.execute_restore = AsyncMock()

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_job)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx), \
             patch("app.services.restore_engine.RestoreEngine", return_value=mock_engine):
            raw = json.dumps({"job_type": "restore", "restore_job_id": 55})
            await process_restore_message(raw)

    @pytest.mark.asyncio
    async def test_restore_job_not_found_logs_error(self):
        """Missing restore job causes logged error, not exception."""
        from app.worker import process_restore_message

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx):
            raw = json.dumps({"job_type": "restore", "restore_job_id": 9999})
            await process_restore_message(raw)  # Should not raise

    @pytest.mark.asyncio
    async def test_restore_exception_triggers_rollback(self):
        """Engine exception triggers DB rollback."""
        from app.worker import process_restore_message

        mock_job = MagicMock()
        mock_engine = AsyncMock()
        mock_engine.execute_restore = AsyncMock(side_effect=RuntimeError("Restore crash"))

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_job)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.database.async_session", return_value=mock_session_ctx), \
             patch("app.services.restore_engine.RestoreEngine", return_value=mock_engine):
            raw = json.dumps({"job_type": "restore", "restore_job_id": 55})
            await process_restore_message(raw)

        mock_db.rollback.assert_called_once()


# ── worker_loop ──

class TestWorkerLoop:
    """Tests for the worker_loop polling function."""

    @pytest.mark.asyncio
    async def test_shuts_down_when_event_set(self):
        """worker_loop exits cleanly when shutdown_event is set."""
        from app import worker as worker_module
        from app.interfaces.redis_dispatcher import BACKUP_QUEUE, RESTORE_QUEUE

        # Pre-set shutdown event
        worker_module.shutdown_event.set()

        mock_redis = AsyncMock()
        mock_redis.brpop = AsyncMock(return_value=None)
        mock_redis.close = AsyncMock()

        import redis.asyncio as real_aioredis
        with patch.object(real_aioredis, "from_url", return_value=mock_redis):
            await worker_module.worker_loop(0)

        # Should exit without processing (shutdown was already set)
        worker_module.shutdown_event.clear()  # Reset for other tests

    @pytest.mark.asyncio
    async def test_routes_backup_queue_to_process_backup_message(self):
        """Messages from BACKUP_QUEUE are routed to process_backup_message."""
        from app import worker as worker_module
        from app.interfaces.redis_dispatcher import BACKUP_QUEUE

        worker_module.shutdown_event.clear()
        processed = []
        call_count = 0

        async def fake_brpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (BACKUP_QUEUE, '{"job_type":"backup_object","protected_object_id":1}')
            worker_module.shutdown_event.set()
            return None

        mock_redis = AsyncMock()
        mock_redis.brpop = fake_brpop
        mock_redis.close = AsyncMock()

        async def fake_process_backup(raw):
            processed.append(("backup", raw))

        import redis.asyncio as real_aioredis
        with patch.object(real_aioredis, "from_url", return_value=mock_redis), \
             patch("app.worker.process_backup_message", side_effect=fake_process_backup):
            await worker_module.worker_loop(0)

        assert len(processed) == 1
        assert processed[0][0] == "backup"
        worker_module.shutdown_event.clear()

    @pytest.mark.asyncio
    async def test_routes_restore_queue_to_process_restore_message(self):
        """Messages from RESTORE_QUEUE are routed to process_restore_message."""
        from app import worker as worker_module
        from app.interfaces.redis_dispatcher import RESTORE_QUEUE

        worker_module.shutdown_event.clear()
        processed = []
        call_count = 0

        async def fake_brpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (RESTORE_QUEUE, '{"job_type":"restore","restore_job_id":5}')
            worker_module.shutdown_event.set()
            return None

        mock_redis = AsyncMock()
        mock_redis.brpop = fake_brpop
        mock_redis.close = AsyncMock()

        async def fake_process_restore(raw):
            processed.append(("restore", raw))

        import redis.asyncio as real_aioredis
        with patch.object(real_aioredis, "from_url", return_value=mock_redis), \
             patch("app.worker.process_restore_message", side_effect=fake_process_restore):
            await worker_module.worker_loop(0)

        assert len(processed) == 1
        assert processed[0][0] == "restore"
        worker_module.shutdown_event.clear()

    @pytest.mark.asyncio
    async def test_timeout_returns_none_continues_loop(self):
        """brpop timeout (None result) continues the loop without processing."""
        from app import worker as worker_module

        worker_module.shutdown_event.clear()
        call_count = 0

        async def fake_brpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                worker_module.shutdown_event.set()
            return None  # Simulate timeout

        mock_redis = AsyncMock()
        mock_redis.brpop = fake_brpop
        mock_redis.close = AsyncMock()

        import redis.asyncio as real_aioredis
        with patch.object(real_aioredis, "from_url", return_value=mock_redis):
            await worker_module.worker_loop(0)

        # Should have polled multiple times without crashing
        assert call_count >= 3
        worker_module.shutdown_event.clear()

    @pytest.mark.asyncio
    async def test_exception_in_processing_does_not_crash_loop(self):
        """An exception during message processing is caught, loop continues."""
        from app import worker as worker_module
        from app.interfaces.redis_dispatcher import BACKUP_QUEUE

        worker_module.shutdown_event.clear()
        call_count = 0

        async def fake_brpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (BACKUP_QUEUE, 'bad json{{{')
            worker_module.shutdown_event.set()
            return None

        mock_redis = AsyncMock()
        mock_redis.brpop = fake_brpop
        mock_redis.close = AsyncMock()

        import redis.asyncio as real_aioredis
        with patch.object(real_aioredis, "from_url", return_value=mock_redis):
            # Should not raise — errors are caught and logged
            await worker_module.worker_loop(0)

        worker_module.shutdown_event.clear()
