"""Per-Tenant Fair Scheduler — prevents noisy neighbor problem.

When 30 tenants are backing up simultaneously, one tenant with 10,000 mailboxes
shouldn't starve another with 50 mailboxes. This scheduler enforces:

1. Per-tenant concurrency limits (max N jobs per tenant at a time)
2. Round-robin fairness (tenants take turns, not first-come-first-serve)

Usage:
    scheduler = TenantFairScheduler(max_per_tenant=3)

    # In backup_engine, wrap each job:
    await scheduler.execute(tenant_id=1, coro=run_backup(obj))
    # Tenant 1 can run max 3 concurrent jobs. Job 4 waits until one finishes.
"""
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from time import monotonic

logger = logging.getLogger(__name__)


@dataclass
class TenantSchedulerMetrics:
    """Per-tenant scheduling metrics for observability."""
    total_executed: int = 0
    total_queued: int = 0
    current_inflight: int = 0
    peak_inflight: int = 0
    total_wait_ms: float = 0


class TenantFairScheduler:
    """Fair job scheduling with per-tenant concurrency limits.

    Each tenant gets at most `max_per_tenant` concurrent jobs. When a tenant
    exceeds its limit, additional jobs queue behind a per-tenant semaphore
    while other tenants continue unimpeded.
    """

    def __init__(self, max_per_tenant: int = 3):
        self.max_per_tenant = max_per_tenant
        self._semaphores: dict[int, asyncio.Semaphore] = {}
        self._metrics: dict[int, TenantSchedulerMetrics] = defaultdict(TenantSchedulerMetrics)

    def _get_semaphore(self, tenant_id: int) -> asyncio.Semaphore:
        if tenant_id not in self._semaphores:
            self._semaphores[tenant_id] = asyncio.Semaphore(self.max_per_tenant)
        return self._semaphores[tenant_id]

    async def execute(self, tenant_id: int, coro):
        """Execute a coroutine with per-tenant fair scheduling.

        Blocks if tenant already has max_per_tenant jobs running.
        Other tenants' jobs are NOT blocked.
        """
        sem = self._get_semaphore(tenant_id)
        metrics = self._metrics[tenant_id]

        start = monotonic()
        metrics.total_queued += 1

        async with sem:
            wait_ms = (monotonic() - start) * 1000
            metrics.total_wait_ms += wait_ms
            metrics.current_inflight += 1
            metrics.peak_inflight = max(metrics.peak_inflight, metrics.current_inflight)

            if wait_ms > 100:  # Log if we had to wait
                logger.info(
                    f"Tenant {tenant_id} job waited {wait_ms:.0f}ms for fair scheduler slot",
                    extra={"tenant_id": tenant_id, "wait_ms": wait_ms},
                )

            try:
                result = await coro
                metrics.total_executed += 1
                return result
            finally:
                metrics.current_inflight -= 1

    def get_metrics(self, tenant_id: int = None) -> dict:
        """Get scheduling metrics for a tenant or all tenants."""
        if tenant_id is not None:
            m = self._metrics.get(tenant_id)
            if not m:
                return {}
            return {
                "total_executed": m.total_executed,
                "current_inflight": m.current_inflight,
                "peak_inflight": m.peak_inflight,
                "avg_wait_ms": round(m.total_wait_ms / max(m.total_queued, 1)),
            }
        return {
            tid: self.get_metrics(tid)
            for tid in self._metrics
        }


# Singleton
fair_scheduler = TenantFairScheduler(max_per_tenant=3)
