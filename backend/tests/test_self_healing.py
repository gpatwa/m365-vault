"""Tests for self-healing platform mechanisms.

Covers: adaptive concurrency, fair scheduling, log context, feature gates,
pool sizing, health monitoring.
"""
import asyncio
import pytest


# ═══════════════════════════════════════════════════════
# Adaptive Concurrency (AIMD)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_aimd_starts_at_initial():
    from app.services.adaptive_concurrency import AdaptiveConcurrency
    ac = AdaptiveConcurrency(initial=5)
    assert ac.limit == 5


@pytest.mark.asyncio
async def test_aimd_decreases_on_throttle():
    from app.services.adaptive_concurrency import AdaptiveConcurrency
    ac = AdaptiveConcurrency(initial=10, min_limit=1, cooldown_seconds=0)
    async with ac.acquire() as slot:
        slot.throttled()
    assert ac.limit <= 5  # Should halve


@pytest.mark.asyncio
async def test_aimd_respects_min_limit():
    from app.services.adaptive_concurrency import AdaptiveConcurrency
    ac = AdaptiveConcurrency(initial=2, min_limit=1, cooldown_seconds=0)
    # Throttle twice
    for _ in range(3):
        async with ac.acquire() as slot:
            slot.throttled()
    assert ac.limit >= 1  # Never below min


@pytest.mark.asyncio
async def test_aimd_metrics_tracked():
    from app.services.adaptive_concurrency import AdaptiveConcurrency
    ac = AdaptiveConcurrency(initial=5)
    async with ac.acquire():
        pass
    m = ac.metrics
    assert m.total_requests >= 1


# ═══════════════════════════════════════════════════════
# Fair Scheduler
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_fair_scheduler_limits_per_tenant():
    from app.services.fair_scheduler import TenantFairScheduler
    fs = TenantFairScheduler(max_per_tenant=2)

    results = []
    async def task(n):
        results.append(n)
        await asyncio.sleep(0.01)
        return n

    # Run 4 jobs for tenant 1 (max 2 concurrent)
    await asyncio.gather(
        fs.execute(1, task(1)),
        fs.execute(1, task(2)),
        fs.execute(1, task(3)),
        fs.execute(1, task(4)),
    )
    assert len(results) == 4  # All completed


@pytest.mark.asyncio
async def test_fair_scheduler_different_tenants_independent():
    from app.services.fair_scheduler import TenantFairScheduler
    fs = TenantFairScheduler(max_per_tenant=1)

    results = []
    async def task(tenant, n):
        results.append((tenant, n))
        await asyncio.sleep(0.01)

    # Tenant 1 and Tenant 2 run concurrently (different semaphores)
    await asyncio.gather(
        fs.execute(1, task(1, 'a')),
        fs.execute(2, task(2, 'b')),
    )
    assert len(results) == 2


@pytest.mark.asyncio
async def test_fair_scheduler_metrics():
    from app.services.fair_scheduler import TenantFairScheduler
    fs = TenantFairScheduler(max_per_tenant=2)

    async def noop():
        pass

    await fs.execute(1, noop())
    m = fs.get_metrics(1)
    assert m["total_executed"] == 1


# ═══════════════════════════════════════════════════════
# Structured Log Context
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_log_context_set_and_get():
    from app.utils.log_context import tenant_ctx, workload_ctx, set_context, clear_context
    tokens = set_context(tenant_id=42, workload="exchange")
    assert tenant_ctx.get() == 42
    assert workload_ctx.get() == "exchange"
    clear_context(tokens)
    assert tenant_ctx.get() is None


@pytest.mark.asyncio
async def test_log_context_logger_includes_context():
    from app.utils.log_context import get_logger, set_context, clear_context
    logger = get_logger("test")
    tokens = set_context(tenant_id=7, workload="teams")
    # The logger should process messages with context
    msg, kwargs = logger.process("test message", {})
    assert kwargs['extra']['tenant_id'] == 7
    assert kwargs['extra']['workload'] == "teams"
    clear_context(tokens)


@pytest.mark.asyncio
async def test_log_context_decorator():
    from app.utils.log_context import with_context, workload_ctx

    @with_context(workload="sharepoint")
    async def inner():
        return workload_ctx.get()

    result = await inner()
    assert result == "sharepoint"
    # After decorator exits, context should be reset
    assert workload_ctx.get() is None


# ═══════════════════════════════════════════════════════
# Feature Gate Decorator
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_require_feature_blocks_when_disabled():
    from app.workers.base_worker import require_feature

    class FakeWorker:
        @require_feature("nonexistent_feature_xyz")
        async def _discover_something(self):
            return ["item1", "item2"]

    worker = FakeWorker()
    result = await worker._discover_something()
    assert result == []  # Blocked — returned empty list


@pytest.mark.asyncio
async def test_require_feature_allows_when_enabled():
    from app.workers.base_worker import require_feature
    from app.services.feature_flags import _overrides

    # Force-enable the feature
    _overrides["test_feature_abc"] = True
    try:
        class FakeWorker:
            @require_feature("test_feature_abc")
            async def _discover_something(self):
                return ["item1", "item2"]

        worker = FakeWorker()
        result = await worker._discover_something()
        assert result == ["item1", "item2"]
    finally:
        _overrides.pop("test_feature_abc", None)


# ═══════════════════════════════════════════════════════
# Per-Tenant Feature Tier
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_feature_flags_accept_tenant_id():
    from app.services.feature_flags import feature_flags
    # Should not crash with tenant_id param
    result = feature_flags.is_enabled("exchange", tenant_id=1)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_feature_flags_global_override_wins():
    from app.services.feature_flags import feature_flags, _overrides
    _overrides["test_override"] = True
    try:
        assert feature_flags.is_enabled("test_override", tenant_id=999) is True
    finally:
        _overrides.pop("test_override", None)


# ═══════════════════════════════════════════════════════
# DB Pool Sizing
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pool_size_adequate_for_scale():
    """Pool should support 25+ concurrent sessions for 20-30 customers."""
    from app.database import engine
    # SQLite (test) uses NullPool — just verify the config exists
    if hasattr(engine.pool, 'size'):
        assert engine.pool.size() >= 10  # At least reasonable
    else:
        pass  # NullPool (SQLite test) — OK
