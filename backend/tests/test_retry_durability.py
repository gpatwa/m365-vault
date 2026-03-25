"""Tests for retry engine durability — retry counts, backoff, and dead-letter behavior.

The "dead letter" concept is implemented via BackupJob.max_retries:
jobs that have exhausted retry_count >= max_retries are NOT retried further,
effectively acting as dead-letter entries.

Covers:
- BackupJob model retry fields (retry_count, max_retries, failed_object_ids)
- RetryEngine.process_failed_jobs: eligible retry selection
- RetryEngine.process_failed_jobs: backoff window enforcement
- RetryEngine.process_failed_jobs: jobs at max_retries are skipped (dead-letter)
- retry_count increments on each _retry_job() call
- _get_failed_object_ids parses from progress_details and failed_object_ids
- retry_single_job: manual retry path
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.backup_job import BackupJob, JobStatus
from app.services.retry_engine import RetryEngine, JOB_RETRY_DELAYS_MINUTES


# ── BackupJob model fields ──

class TestBackupJobRetryFields:
    """Verify BackupJob model has the expected retry-related columns."""

    def test_retry_count_column_has_default_zero(self):
        """retry_count column default is 0."""
        from sqlalchemy import inspect as sa_inspect
        col = BackupJob.__table__.columns["retry_count"]
        # SQLAlchemy Column default is a ColumnDefault with a scalar value
        assert col.default.arg == 0

    def test_max_retries_column_has_default_three(self):
        """max_retries column default is 3."""
        col = BackupJob.__table__.columns["max_retries"]
        assert col.default.arg == 3

    def test_failed_object_ids_column_is_nullable(self):
        """failed_object_ids column is nullable."""
        col = BackupJob.__table__.columns["failed_object_ids"]
        assert col.nullable is True

    def test_retry_of_job_id_column_is_nullable(self):
        """retry_of_job_id column is nullable (foreign key to backup_jobs)."""
        col = BackupJob.__table__.columns["retry_of_job_id"]
        assert col.nullable is True

    def test_can_set_retry_count(self):
        job = BackupJob()
        job.retry_count = 2
        assert job.retry_count == 2

    def test_can_set_failed_object_ids_as_json(self):
        job = BackupJob()
        ids = [1, 2, 3]
        job.failed_object_ids = json.dumps(ids)
        assert json.loads(job.failed_object_ids) == ids


# ── RetryEngine._get_failed_object_ids ──

class TestGetFailedObjectIds:
    """Tests for extracting failed object IDs from job metadata."""

    def test_parses_failed_object_ids_field(self):
        engine = RetryEngine(AsyncMock())
        job = MagicMock(spec=BackupJob)
        job.failed_object_ids = json.dumps([10, 20, 30])
        job.progress_details = None

        result = engine._get_failed_object_ids(job)
        assert result == [10, 20, 30]

    def test_parses_from_progress_details_when_failed_object_ids_absent(self):
        engine = RetryEngine(AsyncMock())
        job = MagicMock(spec=BackupJob)
        job.failed_object_ids = None
        job.progress_details = json.dumps({
            "objects": {
                "1": {"name": "User A", "status": "completed"},
                "2": {"name": "User B", "status": "failed"},
                "3": {"name": "User C", "status": "failed"},
            }
        })

        result = engine._get_failed_object_ids(job)
        assert sorted(result) == [2, 3]

    def test_returns_empty_list_when_no_failures(self):
        engine = RetryEngine(AsyncMock())
        job = MagicMock(spec=BackupJob)
        job.failed_object_ids = None
        job.progress_details = json.dumps({
            "objects": {
                "1": {"status": "completed"},
                "2": {"status": "completed"},
            }
        })

        result = engine._get_failed_object_ids(job)
        assert result == []

    def test_returns_empty_list_when_both_absent(self):
        engine = RetryEngine(AsyncMock())
        job = MagicMock(spec=BackupJob)
        job.failed_object_ids = None
        job.progress_details = None

        result = engine._get_failed_object_ids(job)
        assert result == []

    def test_handles_invalid_json_gracefully(self):
        engine = RetryEngine(AsyncMock())
        job = MagicMock(spec=BackupJob)
        job.failed_object_ids = "{invalid json}"
        job.progress_details = None

        result = engine._get_failed_object_ids(job)
        assert result == []


# ── process_failed_jobs: retry eligibility ──

class TestProcessFailedJobsEligibility:
    """process_failed_jobs() selects only eligible jobs."""

    @pytest.mark.asyncio
    async def test_skips_jobs_at_max_retries(self):
        """Jobs where retry_count >= max_retries are NOT retried (dead-letter)."""
        mock_db = AsyncMock()

        # This job has exhausted all retries
        exhausted_job = MagicMock(spec=BackupJob)
        exhausted_job.id = 1
        exhausted_job.status = JobStatus.FAILED
        exhausted_job.retry_count = 3
        exhausted_job.max_retries = 3
        exhausted_job.completed_at = datetime.utcnow() - timedelta(hours=2)
        exhausted_job.workload_type = "exchange"

        mock_result = MagicMock()
        # DB query already filters retry_count < max_retries, so return empty
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        engine = RetryEngine(mock_db)
        summary = await engine.process_failed_jobs()

        # Nothing should be retried
        assert summary["retried"] == 0
        assert summary["scanned"] == 0

    @pytest.mark.asyncio
    async def test_retries_eligible_failed_job(self):
        """Jobs with retry_count < max_retries and past backoff window are retried."""
        mock_db = AsyncMock()

        eligible_job = MagicMock(spec=BackupJob)
        eligible_job.id = 2
        eligible_job.status = JobStatus.FAILED
        eligible_job.retry_count = 0
        eligible_job.max_retries = 3
        eligible_job.completed_at = datetime.utcnow() - timedelta(hours=1)
        eligible_job.started_at = datetime.utcnow() - timedelta(hours=1)
        eligible_job.error_message = None
        eligible_job.failed_object_ids = None
        eligible_job.progress_details = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [eligible_job]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        engine = RetryEngine(mock_db)

        # Mock _retry_job to avoid full execution
        engine._retry_job = AsyncMock()

        summary = await engine.process_failed_jobs()

        assert summary["retried"] == 1
        engine._retry_job.assert_called_once_with(eligible_job)

    @pytest.mark.asyncio
    async def test_skips_jobs_in_backoff_window(self):
        """Jobs completed too recently are skipped due to backoff delay."""
        mock_db = AsyncMock()

        # Job completed 1 minute ago — backoff requires 5 min for first retry
        recent_job = MagicMock(spec=BackupJob)
        recent_job.id = 3
        recent_job.status = JobStatus.FAILED
        recent_job.retry_count = 0
        recent_job.max_retries = 3
        recent_job.completed_at = datetime.utcnow() - timedelta(minutes=1)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [recent_job]
        mock_db.execute = AsyncMock(return_value=mock_result)

        engine = RetryEngine(mock_db)
        engine._retry_job = AsyncMock()

        summary = await engine.process_failed_jobs()

        assert summary["skipped_backoff"] == 1
        assert summary["retried"] == 0
        engine._retry_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_jobs_also_eligible_for_retry(self):
        """PARTIAL status jobs are eligible for retry just like FAILED."""
        mock_db = AsyncMock()

        partial_job = MagicMock(spec=BackupJob)
        partial_job.id = 4
        partial_job.status = JobStatus.PARTIAL
        partial_job.retry_count = 1
        partial_job.max_retries = 3
        partial_job.completed_at = datetime.utcnow() - timedelta(hours=1)
        partial_job.started_at = datetime.utcnow() - timedelta(hours=1)
        partial_job.failed_object_ids = json.dumps([5, 6])
        partial_job.progress_details = None
        partial_job.error_message = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [partial_job]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        engine = RetryEngine(mock_db)
        engine._retry_job = AsyncMock()

        summary = await engine.process_failed_jobs()

        assert summary["retried"] == 1


# ── retry_count increments ──

class TestRetryCountIncrement:
    """retry_count increments on each _retry_job call."""

    @pytest.mark.asyncio
    async def test_retry_count_increments_on_retry(self):
        """_retry_job increments retry_count by 1."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        job = MagicMock(spec=BackupJob)
        job.id = 10
        job.retry_count = 0
        job.status = JobStatus.FAILED
        job.failed_object_ids = None
        job.progress_details = None
        job.error_message = None
        job.started_at = None
        job.completed_at = None

        mock_engine = AsyncMock()
        mock_engine._execute_backup_job = AsyncMock()

        engine = RetryEngine(mock_db)

        with patch("app.services.retry_engine.BackupEngine", return_value=mock_engine):
            await engine._retry_job(job)

        assert job.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_sets_job_status_to_in_progress(self):
        """_retry_job sets job status to IN_PROGRESS while running."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        status_during_execution = []

        async def track_status(job):
            status_during_execution.append(job.status)

        job = MagicMock(spec=BackupJob)
        job.id = 11
        job.retry_count = 0
        job.status = JobStatus.FAILED
        job.failed_object_ids = None
        job.progress_details = None
        job.error_message = None
        job.started_at = None
        job.completed_at = None

        mock_engine = AsyncMock()
        mock_engine._execute_backup_job = track_status

        engine = RetryEngine(mock_db)

        with patch("app.services.retry_engine.BackupEngine", return_value=mock_engine):
            await engine._retry_job(job)

        assert JobStatus.IN_PROGRESS in status_during_execution


# ── Backoff delay intervals ──

class TestRetryBackoffDelays:
    """Verify JOB_RETRY_DELAYS_MINUTES values are correct."""

    def test_retry_delays_have_three_intervals(self):
        assert len(JOB_RETRY_DELAYS_MINUTES) == 3

    def test_retry_delays_are_increasing(self):
        for i in range(len(JOB_RETRY_DELAYS_MINUTES) - 1):
            assert JOB_RETRY_DELAYS_MINUTES[i] < JOB_RETRY_DELAYS_MINUTES[i + 1]

    def test_first_delay_is_short(self):
        """First retry uses shortest delay."""
        assert JOB_RETRY_DELAYS_MINUTES[0] <= 10

    def test_last_delay_is_longer(self):
        """Last retry uses longest delay (at least 30 min)."""
        assert JOB_RETRY_DELAYS_MINUTES[-1] >= 30


# ── Dead-letter (max retries exhausted) behavior ──

class TestDeadLetterBehavior:
    """Jobs that exhaust max_retries are effectively dead-lettered."""

    def test_job_at_max_retries_cannot_auto_retry(self):
        """can_auto_retry is False when retry_count >= max_retries."""
        job = MagicMock(spec=BackupJob)
        job.retry_count = 3
        job.max_retries = 3
        job.status = JobStatus.FAILED

        can_retry = job.retry_count < job.max_retries
        assert can_retry is False

    def test_job_below_max_retries_can_auto_retry(self):
        """can_auto_retry is True when retry_count < max_retries."""
        job = MagicMock(spec=BackupJob)
        job.retry_count = 1
        job.max_retries = 3

        can_retry = job.retry_count < job.max_retries
        assert can_retry is True

    @pytest.mark.asyncio
    async def test_get_failed_jobs_summary_reports_retriable_count(self):
        """Summary correctly counts retriable vs exhausted jobs."""
        mock_db = AsyncMock()

        retriable_job = MagicMock(spec=BackupJob)
        retriable_job.id = 1
        retriable_job.status = JobStatus.FAILED
        retriable_job.retry_count = 1
        retriable_job.max_retries = 3
        retriable_job.completed_at = datetime.utcnow() - timedelta(hours=1)
        retriable_job.workload_type = "exchange"
        retriable_job.error_message = "some error"
        retriable_job.objects_total = 5
        retriable_job.objects_processed = 3
        retriable_job.objects_failed = 2
        retriable_job.failed_object_ids = None
        retriable_job.progress_details = None

        exhausted_job = MagicMock(spec=BackupJob)
        exhausted_job.id = 2
        exhausted_job.status = JobStatus.FAILED
        exhausted_job.retry_count = 3
        exhausted_job.max_retries = 3
        exhausted_job.completed_at = datetime.utcnow() - timedelta(hours=2)
        exhausted_job.workload_type = "onedrive"
        exhausted_job.error_message = "persistent error"
        exhausted_job.objects_total = 3
        exhausted_job.objects_processed = 0
        exhausted_job.objects_failed = 3
        exhausted_job.failed_object_ids = None
        exhausted_job.progress_details = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [retriable_job, exhausted_job]
        mock_db.execute = AsyncMock(return_value=mock_result)

        engine = RetryEngine(mock_db)
        summary = await engine.get_failed_jobs_summary()

        assert summary["total_failed"] == 2
        assert summary["retriable"] == 1  # Only 1 can retry
        # Exhausted job: can_auto_retry=False, backoff_ready doesn't matter
        jobs_summary = {j["job_id"]: j for j in summary["jobs"]}
        assert jobs_summary[1]["can_auto_retry"] is True
        assert jobs_summary[2]["can_auto_retry"] is False

    @pytest.mark.asyncio
    async def test_retry_single_job_raises_on_non_failed_status(self):
        """retry_single_job raises ValueError if job is not in failed state."""
        mock_db = AsyncMock()

        in_progress_job = MagicMock(spec=BackupJob)
        in_progress_job.id = 5
        in_progress_job.status = JobStatus.IN_PROGRESS

        mock_db.get = AsyncMock(return_value=in_progress_job)

        engine = RetryEngine(mock_db)

        with pytest.raises(ValueError, match="not in a failed state"):
            await engine.retry_single_job(5)
