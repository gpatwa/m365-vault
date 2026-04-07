"""Adaptive Concurrency Control — AIMD algorithm (like TCP congestion control).

Dynamically adjusts the number of concurrent Graph API requests based on
throttling signals. When the API is healthy, concurrency increases. When
throttled (429), concurrency halves immediately.

This is the same Additive Increase / Multiplicative Decrease algorithm
that TCP uses for congestion control — proven at internet scale.

Usage:
    limiter = AdaptiveConcurrency(initial=5, min_limit=1, max_limit=50)

    async with limiter.acquire() as slot:
        response = await graph.get("/users")
        if response.status_code == 429:
            slot.throttled()
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyMetrics:
    """Track concurrency behavior for observability."""
    current_limit: int = 5
    inflight: int = 0
    total_requests: int = 0
    total_throttled: int = 0
    last_adjustment: float = 0
    adjustments: int = 0


class AdaptiveConcurrency:
    """AIMD concurrency limiter for Graph API requests.

    - Additive Increase: +1 slot when a full batch completes without throttling
    - Multiplicative Decrease: halve slots immediately on any 429 response
    - Bounded: [min_limit, max_limit] to prevent runaway or starvation
    """

    def __init__(
        self,
        initial: int = 5,
        min_limit: int = 1,
        max_limit: int = 50,
        cooldown_seconds: float = 5.0,
    ):
        self._limit = initial
        self._min = min_limit
        self._max = max_limit
        self._cooldown = cooldown_seconds
        self._semaphore = asyncio.Semaphore(initial)
        self._inflight = 0
        self._last_decrease = 0.0
        self._metrics = ConcurrencyMetrics(current_limit=initial)
        self._lock = asyncio.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def inflight(self) -> int:
        return self._inflight

    @property
    def metrics(self) -> ConcurrencyMetrics:
        self._metrics.current_limit = self._limit
        self._metrics.inflight = self._inflight
        return self._metrics

    def acquire(self):
        """Return a context manager that acquires a concurrency slot."""
        return _ConcurrencySlot(self)

    async def _acquire(self):
        await self._semaphore.acquire()
        self._inflight += 1
        self._metrics.total_requests += 1

    async def _release(self, was_throttled: bool = False):
        self._inflight -= 1
        self._semaphore.release()

        if was_throttled:
            await self._decrease()
        elif self._inflight == 0:
            await self._increase()

    async def _decrease(self):
        """Multiplicative decrease: halve the limit."""
        now = time.monotonic()
        if now - self._last_decrease < self._cooldown:
            return  # Don't decrease too frequently

        async with self._lock:
            new_limit = max(self._limit // 2, self._min)
            if new_limit < self._limit:
                old = self._limit
                self._limit = new_limit
                self._last_decrease = now
                self._metrics.total_throttled += 1
                self._metrics.adjustments += 1
                logger.info(f"AIMD decrease: {old} → {new_limit} (throttled)")

    async def _increase(self):
        """Additive increase: grow by 1 when batch completes cleanly."""
        async with self._lock:
            if self._limit < self._max:
                new_limit = self._limit + 1
                # Add one permit to semaphore
                self._semaphore.release()
                old = self._limit
                self._limit = new_limit
                self._metrics.adjustments += 1
                logger.debug(f"AIMD increase: {old} → {new_limit}")


class _ConcurrencySlot:
    """Async context manager for a single concurrency slot."""

    def __init__(self, controller: AdaptiveConcurrency):
        self._controller = controller
        self._was_throttled = False

    async def __aenter__(self):
        await self._controller._acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._controller._release(self._was_throttled)
        return False

    def throttled(self):
        """Mark this request as throttled (429). Called by the consumer."""
        self._was_throttled = True


# Singleton per-tenant concurrency controllers
_tenant_limiters: dict[str, AdaptiveConcurrency] = {}


def get_tenant_limiter(tenant_id: str, initial: int = 10) -> AdaptiveConcurrency:
    """Get or create an adaptive concurrency limiter for a tenant."""
    if tenant_id not in _tenant_limiters:
        _tenant_limiters[tenant_id] = AdaptiveConcurrency(initial=initial)
    return _tenant_limiters[tenant_id]
