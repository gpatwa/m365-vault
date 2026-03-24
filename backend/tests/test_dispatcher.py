"""Tests for dispatcher interface and factory."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.interfaces.job_message import (
    BackupObjectMessage, BackupJobMessage, RestoreJobMessage, JobResult, JobType
)
from app.interfaces.job_dispatcher import InProcessDispatcher
from app.interfaces.dispatcher_factory import get_dispatcher, reset_dispatcher


# ── Job Message Tests ──

class TestJobMessages:
    """Tests for job message schemas."""

    def test_backup_object_message(self):
        msg = BackupObjectMessage(protected_object_id=42)
        assert msg.job_type == JobType.BACKUP_OBJECT
        assert msg.protected_object_id == 42
        assert msg.backup_job_id is None

    def test_backup_object_with_job(self):
        msg = BackupObjectMessage(protected_object_id=42, backup_job_id=10)
        assert msg.backup_job_id == 10

    def test_backup_job_message(self):
        msg = BackupJobMessage(backup_job_id=99)
        assert msg.job_type == JobType.BACKUP_JOB
        assert msg.backup_job_id == 99

    def test_restore_message(self):
        msg = RestoreJobMessage(restore_job_id=55)
        assert msg.job_type == JobType.RESTORE
        assert msg.restore_job_id == 55

    def test_job_result_success(self):
        result = JobResult(success=True, snapshot_id=100, item_count=50)
        assert result.success is True
        assert result.snapshot_id == 100
        assert result.error is None

    def test_job_result_failure(self):
        result = JobResult(success=False, error="Connection timeout")
        assert result.success is False
        assert result.error == "Connection timeout"

    def test_message_serialization(self):
        msg = BackupObjectMessage(protected_object_id=42, backup_job_id=10)
        json_str = msg.model_dump_json()
        assert '"protected_object_id":42' in json_str
        assert '"backup_job_id":10' in json_str

    def test_message_deserialization(self):
        msg = BackupObjectMessage.model_validate_json(
            '{"protected_object_id": 42, "backup_job_id": 10}'
        )
        assert msg.protected_object_id == 42


# ── Dispatcher Factory Tests ──

class TestDispatcherFactory:
    """Tests for dispatcher factory."""

    def setup_method(self):
        reset_dispatcher()

    def teardown_method(self):
        reset_dispatcher()

    @patch("app.interfaces.dispatcher_factory.settings")
    def test_default_in_process(self, mock_settings):
        mock_settings.DISPATCH_MODE = "in_process"
        dispatcher = get_dispatcher()
        assert isinstance(dispatcher, InProcessDispatcher)

    @patch("app.interfaces.dispatcher_factory.settings")
    def test_redis_mode_creates_redis_dispatcher(self, mock_settings):
        mock_settings.DISPATCH_MODE = "redis"
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        dispatcher = get_dispatcher()
        # RedisDispatcher is now available
        from app.interfaces.redis_dispatcher import RedisDispatcher
        assert isinstance(dispatcher, RedisDispatcher)

    @patch("app.interfaces.dispatcher_factory.settings")
    def test_singleton_pattern(self, mock_settings):
        mock_settings.DISPATCH_MODE = "in_process"
        d1 = get_dispatcher()
        d2 = get_dispatcher()
        assert d1 is d2  # Same instance

    @patch("app.interfaces.dispatcher_factory.settings")
    def test_reset_clears_singleton(self, mock_settings):
        mock_settings.DISPATCH_MODE = "in_process"
        d1 = get_dispatcher()
        reset_dispatcher()
        d2 = get_dispatcher()
        assert d1 is not d2  # Different instance after reset


# ── InProcessDispatcher Tests ──

class TestInProcessDispatcher:
    """Tests for InProcessDispatcher."""

    @pytest.mark.asyncio
    async def test_backup_object_not_found(self):
        dispatcher = InProcessDispatcher()
        msg = BackupObjectMessage(protected_object_id=99999)

        # Mock DB that returns None for get()
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_backup_object(msg, db=mock_db)
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_backup_job_not_found(self):
        dispatcher = InProcessDispatcher()
        msg = BackupJobMessage(backup_job_id=99999)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_backup_job(msg, db=mock_db)
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_restore_not_found(self):
        dispatcher = InProcessDispatcher()
        msg = RestoreJobMessage(restore_job_id=99999)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_restore(msg, db=mock_db)
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_exception_returns_failure(self):
        dispatcher = InProcessDispatcher()
        msg = BackupObjectMessage(protected_object_id=1)

        # DB that raises exception
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(side_effect=ConnectionError("DB down"))

        result = await dispatcher.dispatch_backup_object(msg, db=mock_db)
        assert result.success is False
        assert "DB down" in result.error
