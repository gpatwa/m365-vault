"""Circuit breaker for Graph API resilience.

Prevents hammering a failing API by tracking failure rates per tenant.
When failure rate exceeds threshold (default 50%) within a window (5 min),
the circuit opens and all requests are rejected for a cooldown period (15 min).

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests rejected
- HALF-OPEN: After cooldown, allow one test request
"""
import logging
import time
from collections import defaultdict

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Per-tenant circuit breaker for API calls."""

    def __init__(
        self,
        failure_threshold: float = None,
        window_seconds: int = None,
        cooldown_seconds: int = None,
        min_calls: int = 10,
    ):
        self.threshold = failure_threshold or settings.CIRCUIT_BREAKER_THRESHOLD
        self.window = window_seconds or settings.CIRCUIT_BREAKER_WINDOW
        self.cooldown = cooldown_seconds or settings.CIRCUIT_BREAKER_COOLDOWN
        self.min_calls = min_calls  # Minimum calls before evaluating

        # Per-tenant state
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._successes: dict[str, list[float]] = defaultdict(list)
        self._open_until: dict[str, float] = {}

    def record_success(self, tenant_id: str):
        """Record a successful API call."""
        self._successes[tenant_id].append(time.time())

    def record_failure(self, tenant_id: str):
        """Record a failed API call."""
        self._failures[tenant_id].append(time.time())
        self._check_and_trip(tenant_id)

    def is_open(self, tenant_id: str) -> bool:
        """Check if circuit is open (requests should be rejected)."""
        open_until = self._open_until.get(tenant_id)
        if open_until:
            if time.time() < open_until:
                return True
            else:
                # Cooldown expired — half-open, allow requests
                del self._open_until[tenant_id]
                return False
        return False

    def _check_and_trip(self, tenant_id: str):
        """Check failure rate and trip circuit if threshold exceeded."""
        now = time.time()

        # Clean old entries
        self._failures[tenant_id] = [t for t in self._failures[tenant_id] if now - t < self.window]
        self._successes[tenant_id] = [t for t in self._successes[tenant_id] if now - t < self.window]

        failures = len(self._failures[tenant_id])
        successes = len(self._successes[tenant_id])
        total = failures + successes

        if total < self.min_calls:
            return  # Not enough data to evaluate

        failure_rate = failures / total

        if failure_rate > self.threshold:
            self._open_until[tenant_id] = now + self.cooldown
            logger.warning(
                f"Circuit breaker OPEN for tenant {tenant_id}: "
                f"{failure_rate:.0%} failure rate ({failures}/{total}) in last {self.window}s. "
                f"Cooldown: {self.cooldown}s"
            )

            # Trigger alert
            try:
                import asyncio
                from app.services.alert_service import alert_service
                asyncio.get_event_loop().create_task(
                    alert_service.notify(
                        event_type="circuit_breaker.open",
                        title=f"Circuit breaker activated for tenant {tenant_id}",
                        details=f"Graph API failure rate: {failure_rate:.0%} ({failures}/{total} calls failed). Backups paused for {self.cooldown // 60} minutes.",
                        severity="critical",
                        tenant_name=tenant_id,
                    )
                )
            except Exception:
                pass  # Alert is best-effort

    def get_status(self, tenant_id: str) -> dict:
        """Get circuit breaker status for a tenant."""
        now = time.time()
        failures = len([t for t in self._failures.get(tenant_id, []) if now - t < self.window])
        successes = len([t for t in self._successes.get(tenant_id, []) if now - t < self.window])
        total = failures + successes
        open_until = self._open_until.get(tenant_id)

        return {
            "state": "open" if self.is_open(tenant_id) else "closed",
            "failure_rate": round(failures / total, 2) if total > 0 else 0,
            "failures": failures,
            "successes": successes,
            "total_calls": total,
            "open_until": open_until,
            "cooldown_remaining": max(0, int(open_until - now)) if open_until and open_until > now else 0,
        }


# Global instance
circuit_breaker = CircuitBreaker()
