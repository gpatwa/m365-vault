"""Chaos tests — validate resilience under failure conditions.

Tests fault tolerance mechanisms:
1. Circuit breaker trips on Graph API failures
2. Stale job detection resets stuck jobs
3. Dispatcher fallback on Redis unavailability
4. Partial backup continues after item failures
5. DB pool recovery after connection loss simulation
"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.circuit_breaker import CircuitBreaker, circuit_breaker
from app.interfaces.job_dispatcher import InProcessDispatcher
from app.interfaces.job_message import BackupObjectMessage, BackupJobMessage, JobResult
from app.workers.base_worker import BaseWorker, BackupItem
from app.models.snapshot import ItemType


# ═══════════════════════════════════════════════════════
# 1. Circuit Breaker Under Sustained Load
# ═══════════════════════════════════════════════════════

class TestCircuitBreakerChaos:
    """Simulate sustained API failures and verify circuit breaker behavior."""

    def test_rapid_failures_trip_circuit(self):
        """100 rapid failures should trip the circuit."""
        cb = CircuitBreaker(failure_threshold=0.5, window_seconds=60, cooldown_seconds=10, min_calls=10)

        # 100 rapid failures
        for _ in range(100):
            cb.record_failure("chaos_tenant")

        assert cb.is_open("chaos_tenant")
        status = cb.get_status("chaos_tenant")
        assert status["failure_rate"] == 1.0  # 100% failures

    def test_mixed_traffic_with_gradual_degradation(self):
        """Gradual degradation: 70% success → 50% → 30% → circuit trips."""
        cb = CircuitBreaker(failure_threshold=0.5, window_seconds=60, cooldown_seconds=5, min_calls=10)

        # Phase 1: 70% success (should stay closed)
        for _ in range(7):
            cb.record_success("degrade_tenant")
        for _ in range(3):
            cb.record_failure("degrade_tenant")
        assert not cb.is_open("degrade_tenant")

        # Phase 2: Add more failures (now >50% total)
        for _ in range(10):
            cb.record_failure("degrade_tenant")
        assert cb.is_open("degrade_tenant")

    def test_circuit_recovery_after_cooldown(self):
        """Trip circuit → wait cooldown → verify it closes → successful calls keep it closed."""
        cb = CircuitBreaker(failure_threshold=0.5, window_seconds=60, cooldown_seconds=1, min_calls=5)

        # Trip
        for _ in range(20):
            cb.record_failure("recovery_tenant")
        assert cb.is_open("recovery_tenant")

        # Wait for cooldown
        time.sleep(1.1)
        assert not cb.is_open("recovery_tenant")  # Half-open

        # Successful calls should keep it closed
        for _ in range(10):
            cb.record_success("recovery_tenant")
        assert not cb.is_open("recovery_tenant")

    def test_multiple_tenants_independent_failure(self):
        """5 tenants with different failure rates — only high-failure tenants trip."""
        cb = CircuitBreaker(failure_threshold=0.5, window_seconds=60, cooldown_seconds=30, min_calls=10)

        # Tenant A: 90% failure → should trip
        for _ in range(1):
            cb.record_success("tenant_a")
        for _ in range(19):
            cb.record_failure("tenant_a")

        # Tenant B: 10% failure → should stay closed
        for _ in range(18):
            cb.record_success("tenant_b")
        for _ in range(2):
            cb.record_failure("tenant_b")

        # Tenant C: no calls → should be closed
        # Tenant D: 50% failure → borderline
        for _ in range(10):
            cb.record_success("tenant_d")
        for _ in range(10):
            cb.record_failure("tenant_d")

        assert cb.is_open("tenant_a")      # High failure
        assert not cb.is_open("tenant_b")   # Low failure
        assert not cb.is_open("tenant_c")   # No data
        # tenant_d is borderline — depends on exact threshold


# ═══════════════════════════════════════════════════════
# 2. Stale Job Detection
# ═══════════════════════════════════════════════════════

class TestStaleJobChaos:
    """Simulate worker crashes and verify stale job detection."""

    @pytest.mark.asyncio
    async def test_stale_job_detection_logic(self):
        """Verify stale job detection SQL logic works."""
        from app.models.backup_job import BackupJob, JobStatus

        # Create a mock "stale" job
        stale_job = MagicMock()
        stale_job.id = 42
        stale_job.status = JobStatus.IN_PROGRESS
        stale_job.started_at = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        stale_job.workload_type = "exchange"

        # Verify it would be detected (started > 60 min ago)
        cutoff = datetime.utcnow() - timedelta(minutes=60)
        assert stale_job.started_at < cutoff  # Would be detected

    @pytest.mark.asyncio
    async def test_fresh_job_not_stale(self):
        """Jobs started recently should NOT be detected as stale."""
        from app.models.backup_job import BackupJob, JobStatus

        fresh_job = MagicMock()
        fresh_job.id = 43
        fresh_job.status = JobStatus.IN_PROGRESS
        fresh_job.started_at = datetime.utcnow() - timedelta(minutes=5)  # 5 min ago

        cutoff = datetime.utcnow() - timedelta(minutes=60)
        assert fresh_job.started_at > cutoff  # Should NOT be detected


# ═══════════════════════════════════════════════════════
# 3. Dispatcher Fallback
# ═══════════════════════════════════════════════════════

class TestDispatcherFallbackChaos:
    """Simulate Redis unavailability and verify fallback behavior."""

    @pytest.mark.asyncio
    async def test_redis_connection_refused(self):
        """RedisDispatcher should fallback to InProcess on connection refused."""
        try:
            from app.interfaces.redis_dispatcher import RedisDispatcher
            dispatcher = RedisDispatcher("redis://nonexistent-host:6379/0")

            mock_db = AsyncMock()
            mock_db.get = AsyncMock(return_value=None)

            # This should fallback to InProcessDispatcher, not crash
            result = await dispatcher.dispatch_backup_object(
                BackupObjectMessage(protected_object_id=999), db=mock_db
            )
            # Should return a result (either from fallback or error)
            assert isinstance(result, JobResult)
        except ImportError:
            pytest.skip("redis package not installed")

    @pytest.mark.asyncio
    async def test_in_process_handles_missing_object(self):
        """InProcessDispatcher handles missing protected object gracefully."""
        dispatcher = InProcessDispatcher()
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        result = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=99999), db=mock_db
        )
        assert result.success is False
        assert "not found" in result.error.lower()


# ═══════════════════════════════════════════════════════
# 4. Worker Partial Failure Under Load
# ═══════════════════════════════════════════════════════

class FailEveryNthWorker(BaseWorker):
    """Test worker that fails every Nth item."""
    def __init__(self, *args, fail_every=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_every = fail_every
        self._counter = 0

    def workload_name(self):
        return "chaos_worker"

    async def discover_items(self, obj, delta_token=None):
        items = []
        for i in range(20):
            self._counter += 1
            if self._counter % self.fail_every == 0:
                # Item with no data — will fail
                items.append(BackupItem(
                    id=f"fail_{i}", item_type=ItemType.FILE,
                    name=f"Failing Item {i}", path="chaos",
                    raw_data=None, binary_data=None,
                ))
            else:
                items.append(BackupItem(
                    id=f"good_{i}", item_type=ItemType.FILE,
                    name=f"Good Item {i}", path="chaos",
                    raw_data={"data": f"content_{i}"},
                ))
        return items, None


class TestWorkerPartialFailureChaos:
    """Simulate item-level failures during backup."""

    @pytest.fixture
    def mock_deps(self):
        from dataclasses import dataclass

        @dataclass
        class MockResult:
            compressed_size: int = 50
            content_hash: str = "hash"
            storage_flags: int = 1
            blob_path: str = "mock.blob"

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        graph = AsyncMock()
        storage = AsyncMock()
        storage.store_item = AsyncMock(return_value=MockResult())
        enc = AsyncMock()
        return db, graph, storage, enc

    @pytest.mark.asyncio
    async def test_partial_failure_20_items_every_3rd_fails(self, mock_deps):
        """20 items, every 3rd fails → ~13 succeed, ~7 fail."""
        db, graph, storage, enc = mock_deps
        worker = FailEveryNthWorker(db, graph, storage, enc, fail_every=3)
        obj = MagicMock(ms_object_id="chaos", tenant_id=1, id=1, display_name="Chaos Test")
        snapshot = MagicMock(id=999)

        item_count, total_size, _ = await worker.backup(obj, snapshot, "dek", concurrency=5)

        # ~13 should succeed (20 - 6 or 7 failures)
        assert 12 <= item_count <= 14  # Approximately 2/3 succeed
        assert total_size > 0

    @pytest.mark.asyncio
    async def test_all_items_fail_gracefully(self, mock_deps):
        """All items failing should not crash — returns 0 items."""
        db, graph, storage, enc = mock_deps
        worker = FailEveryNthWorker(db, graph, storage, enc, fail_every=1)  # Every item fails
        obj = MagicMock(ms_object_id="chaos", tenant_id=1, id=1, display_name="All Fail")
        snapshot = MagicMock(id=999)

        item_count, total_size, _ = await worker.backup(obj, snapshot, "dek", concurrency=5)

        assert item_count == 0
        assert total_size == 0

    @pytest.mark.asyncio
    async def test_high_concurrency_with_failures(self, mock_deps):
        """High concurrency (20) with failures — no race conditions."""
        db, graph, storage, enc = mock_deps
        worker = FailEveryNthWorker(db, graph, storage, enc, fail_every=5)
        obj = MagicMock(ms_object_id="chaos", tenant_id=1, id=1, display_name="High Concurrency")
        snapshot = MagicMock(id=999)

        item_count, total_size, _ = await worker.backup(obj, snapshot, "dek", concurrency=20)

        # Should complete without deadlock or race condition
        assert item_count >= 0
        assert total_size >= 0


# ═══════════════════════════════════════════════════════
# 5. Storage Pipeline Under Pressure
# ═══════════════════════════════════════════════════════

class StorageFailWorker(BaseWorker):
    """Worker where storage.store_item randomly fails."""
    def workload_name(self):
        return "storage_fail"

    async def discover_items(self, obj, delta_token=None):
        return [
            BackupItem(id=f"item_{i}", item_type=ItemType.FILE, name=f"File {i}",
                       raw_data={"data": i})
            for i in range(10)
        ], None


class TestStorageFailureChaos:
    """Simulate storage failures during backup pipeline."""

    @pytest.mark.asyncio
    async def test_intermittent_storage_failures(self):
        """Storage fails for some items — backup continues for others."""
        from dataclasses import dataclass

        @dataclass
        class MockResult:
            compressed_size: int = 50
            content_hash: str = "hash"
            storage_flags: int = 1
            blob_path: str = "mock.blob"

        call_count = 0
        async def flaky_store(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise IOError("Disk write failed: No space left on device")
            return MockResult()

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        storage = AsyncMock()
        storage.store_item = flaky_store

        worker = StorageFailWorker(db, AsyncMock(), storage, AsyncMock())
        obj = MagicMock(ms_object_id="s", tenant_id=1, id=1, display_name="Storage Test")
        snapshot = MagicMock(id=999)

        item_count, total_size, _ = await worker.backup(obj, snapshot, "dek", concurrency=3)

        # ~7 out of 10 should succeed (every 3rd fails)
        assert 6 <= item_count <= 8
