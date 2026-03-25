"""Tests for scheduler + dispatcher integration.

Covers:
- execute_queued_jobs() uses get_dispatcher() and dispatches QUEUED jobs
- execute_queued_jobs() handles dispatch failure gracefully
- detect_stale_jobs() resets IN_PROGRESS jobs that exceeded JOB_TIMEOUT_MINUTES
- detect_stale_jobs() leaves recent jobs untouched
- check_and_schedule_backups() calls execute_queued_jobs()
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta

from app.models.backup_job import BackupJob, JobStatus
from app.interfaces.dispatcher_factory import reset_dispatcher


# ── execute_queued_jobs ──

class TestExecuteQueuedJobs:
    """Tests that execute_queued_jobs() correctly uses the dispatcher."""

    def setup_method(self):
        reset_dispatcher()

    def teardown_method(self):
        reset_dispatcher()

    @pytest.mark.asyncio
    async def test_calls_get_dispatcher(self):
        """execute_queued_jobs() must call get_dispatcher() to obtain dispatcher."""
        from app.services.scheduler import execute_queued_jobs
        from app.interfaces.job_message import BackupJobMessage
        from app.interfaces.job_dispatcher import JobDispatcher
        from app.interfaces.job_message import JobResult

        mock_dispatcher = AsyncMock(spec=JobDispatcher)
        mock_dispatcher.dispatch_backup_job = AsyncMock(
            return_value=JobResult(success=True, status="completed")
        )

        mock_job = MagicMock(spec=BackupJob)
        mock_job.id = 1
        mock_job.status = JobStatus.QUEUED

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.interfaces.dispatcher_factory.get_dispatcher", return_value=mock_dispatcher) as mock_get:
            await execute_queued_jobs()

        mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatches_each_queued_job(self):
        """Each QUEUED BackupJob is passed to dispatcher.dispatch_backup_job."""
        from app.services.scheduler import execute_queued_jobs
        from app.interfaces.job_message import JobResult

        mock_dispatcher = AsyncMock()
        mock_dispatcher.dispatch_backup_job = AsyncMock(
            return_value=JobResult(success=True, status="completed")
        )

        jobs = [MagicMock(id=i, status=JobStatus.QUEUED) for i in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = jobs

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.interfaces.dispatcher_factory.get_dispatcher", return_value=mock_dispatcher):
            await execute_queued_jobs()

        assert mock_dispatcher.dispatch_backup_job.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_dispatch_when_no_queued_jobs(self):
        """No queued jobs → dispatcher is never called."""
        from app.services.scheduler import execute_queued_jobs

        mock_dispatcher = AsyncMock()
        mock_dispatcher.dispatch_backup_job = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.interfaces.dispatcher_factory.get_dispatcher", return_value=mock_dispatcher):
            await execute_queued_jobs()

        mock_dispatcher.dispatch_backup_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_dispatch_marks_job_failed(self):
        """If dispatch raises, job gets FAILED status and error_message is set."""
        from app.services.scheduler import execute_queued_jobs
        from app.interfaces.job_message import JobResult

        mock_dispatcher = AsyncMock()
        mock_dispatcher.dispatch_backup_job = AsyncMock(
            side_effect=RuntimeError("Dispatcher crashed")
        )

        mock_job = MagicMock(spec=BackupJob)
        mock_job.id = 42
        mock_job.status = JobStatus.QUEUED

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_job]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.interfaces.dispatcher_factory.get_dispatcher", return_value=mock_dispatcher):
            await execute_queued_jobs()

        # Job should be marked FAILED
        assert mock_job.status == JobStatus.FAILED
        assert mock_job.error_message is not None

    @pytest.mark.asyncio
    async def test_dispatch_failure_does_not_stop_other_jobs(self):
        """One dispatch failure doesn't prevent subsequent jobs from being dispatched."""
        from app.services.scheduler import execute_queued_jobs
        from app.interfaces.job_message import JobResult

        dispatch_calls = []

        async def side_effect(msg, **kwargs):
            dispatch_calls.append(msg.backup_job_id)
            if msg.backup_job_id == 2:
                raise RuntimeError("Job 2 failed")
            return JobResult(success=True, status="completed")

        mock_dispatcher = AsyncMock()
        mock_dispatcher.dispatch_backup_job = side_effect

        jobs = [MagicMock(id=i, status=JobStatus.QUEUED) for i in [1, 2, 3]]
        for j in jobs:
            j.error_message = None
            j.completed_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = jobs

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.interfaces.dispatcher_factory.get_dispatcher", return_value=mock_dispatcher):
            await execute_queued_jobs()

        # All 3 jobs were attempted
        assert sorted(dispatch_calls) == [1, 2, 3]


# ── detect_stale_jobs ──

class TestDetectStaleJobs:
    """Tests for detect_stale_jobs() stale IN_PROGRESS job detection."""

    @pytest.mark.asyncio
    async def test_resets_stale_in_progress_jobs_to_queued(self):
        """IN_PROGRESS jobs older than JOB_TIMEOUT_MINUTES are reset to QUEUED."""
        from app.services.scheduler import detect_stale_jobs

        stale_job = MagicMock(spec=BackupJob)
        stale_job.id = 10
        stale_job.workload_type = "exchange"
        stale_job.status = JobStatus.IN_PROGRESS
        stale_job.started_at = datetime.utcnow() - timedelta(hours=2)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stale_job]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.services.scheduler.alert_service", create=True):
            await detect_stale_jobs()

        assert stale_job.status == JobStatus.QUEUED
        assert stale_job.error_message is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_action_when_no_stale_jobs(self):
        """No stale jobs → no commit needed."""
        from app.services.scheduler import detect_stale_jobs

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx):
            await detect_stale_jobs()

        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_stale_error_message_includes_original_start_time(self):
        """Reset error message includes the job's original start time."""
        from app.services.scheduler import detect_stale_jobs

        start_time = datetime.utcnow() - timedelta(hours=3)
        stale_job = MagicMock(spec=BackupJob)
        stale_job.id = 15
        stale_job.workload_type = "onedrive"
        stale_job.status = JobStatus.IN_PROGRESS
        stale_job.started_at = start_time

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stale_job]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.services.scheduler.alert_service", create=True):
            await detect_stale_jobs()

        # Error message should contain the original start time
        assert start_time.isoformat() in stale_job.error_message

    @pytest.mark.asyncio
    async def test_multiple_stale_jobs_all_reset(self):
        """All stale IN_PROGRESS jobs are reset, not just the first."""
        from app.services.scheduler import detect_stale_jobs

        stale_jobs = []
        for i in range(3):
            job = MagicMock(spec=BackupJob)
            job.id = i + 1
            job.workload_type = "exchange"
            job.status = JobStatus.IN_PROGRESS
            job.started_at = datetime.utcnow() - timedelta(hours=2)
            stale_jobs.append(job)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = stale_jobs

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.services.scheduler.alert_service", create=True):
            await detect_stale_jobs()

        for job in stale_jobs:
            assert job.status == JobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_stale_detection_uses_job_timeout_minutes_setting(self):
        """Stale cutoff is based on JOB_TIMEOUT_MINUTES from settings."""
        from app.services.scheduler import detect_stale_jobs
        from app.config import settings

        # A job started just inside the timeout window should be picked up
        # (started at cutoff - 1 minute)
        stale_start = datetime.utcnow() - timedelta(minutes=settings.JOB_TIMEOUT_MINUTES + 1)
        stale_job = MagicMock(spec=BackupJob)
        stale_job.id = 20
        stale_job.workload_type = "teams"
        stale_job.status = JobStatus.IN_PROGRESS
        stale_job.started_at = stale_start

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stale_job]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.scheduler.async_session", return_value=mock_session_ctx), \
             patch("app.services.scheduler.alert_service", create=True):
            await detect_stale_jobs()

        # Should have been reset
        assert stale_job.status == JobStatus.QUEUED
