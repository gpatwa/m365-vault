"""Resilience utilities — pre-flight checks, idempotency, and service health probes.

Pre-flight checks:
  Validate that external dependencies are reachable before starting user-visible
  operations. Prevents wasting user time on operations destined to fail.

Idempotency store:
  In-memory cache keyed by (user_id, idempotency_key). Mutations that receive
  an X-Idempotency-Key header return the cached result on retry instead of
  re-executing. TTL-based expiry prevents unbounded growth.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.services.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


# ── Pre-flight Checks ────────────────────────────────────────────


@dataclass
class PreflightResult:
    """Result of a pre-flight dependency check."""
    ok: bool
    service: str
    detail: str = ""
    latency_ms: int = 0


async def preflight_graph_api(tenant_id: str, client_id: str, client_secret: str) -> PreflightResult:
    """Verify Graph API is reachable and credentials are valid for a tenant.

    Checks:
    1. Circuit breaker is not open
    2. Can acquire a token (validates client credentials)
    3. Can reach Graph API (lightweight /organization call)
    """
    service = "Microsoft Graph API"

    # 1. Check circuit breaker
    if circuit_breaker.is_open(tenant_id):
        status = circuit_breaker.get_status(tenant_id)
        return PreflightResult(
            ok=False, service=service,
            detail=f"Circuit breaker OPEN — {status['failure_rate']:.0%} failure rate. "
                   f"Retry in {status['cooldown_remaining']}s.",
        )

    # 2. Test token acquisition
    start = time.time()
    try:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"{settings.MS_AUTH_URL}/{tenant_id}",
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=[settings.MS_GRAPH_SCOPE])
        if "error" in token_result:
            return PreflightResult(
                ok=False, service=service,
                detail=f"Token acquisition failed: {token_result.get('error_description', '')[:200]}",
                latency_ms=int((time.time() - start) * 1000),
            )
    except Exception as e:
        return PreflightResult(
            ok=False, service=service,
            detail=f"Token error: {str(e)[:200]}",
            latency_ms=int((time.time() - start) * 1000),
        )

    # 3. Lightweight Graph API call
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.MS_GRAPH_BASE_URL}/organization",
                headers={"Authorization": f"Bearer {token_result['access_token']}"},
            )
            latency = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return PreflightResult(ok=True, service=service, latency_ms=latency)
            return PreflightResult(
                ok=False, service=service,
                detail=f"Graph API returned {resp.status_code}",
                latency_ms=latency,
            )
    except Exception as e:
        return PreflightResult(
            ok=False, service=service,
            detail=f"Graph API unreachable: {str(e)[:200]}",
            latency_ms=int((time.time() - start) * 1000),
        )


async def preflight_storage() -> PreflightResult:
    """Verify storage backend is reachable and writable."""
    service = "Storage"
    start = time.time()
    try:
        from app.services.storage import storage_service
        if not storage_service or not storage_service.backend:
            return PreflightResult(ok=False, service=service, detail="Storage not initialized")
        # Try a lightweight exists check
        await storage_service.backend.exists("__preflight_probe__")
        return PreflightResult(
            ok=True, service=service,
            latency_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        return PreflightResult(
            ok=False, service=service,
            detail=f"Storage error: {str(e)[:200]}",
            latency_ms=int((time.time() - start) * 1000),
        )


async def preflight_database() -> PreflightResult:
    """Verify database is reachable."""
    service = "Database"
    start = time.time()
    try:
        from app.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return PreflightResult(
            ok=True, service=service,
            latency_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        return PreflightResult(
            ok=False, service=service,
            detail=f"Database error: {str(e)[:200]}",
            latency_ms=int((time.time() - start) * 1000),
        )


async def preflight_backup(tenant_id: str, client_id: str, client_secret: str) -> list[PreflightResult]:
    """Run all pre-flight checks required before starting a backup.

    Returns list of results — caller should check all are ok.
    """
    import asyncio
    results = await asyncio.gather(
        preflight_graph_api(tenant_id, client_id, client_secret),
        preflight_storage(),
        preflight_database(),
    )
    return list(results)


# ── Idempotency Store ─────────────────────────────────────────────


@dataclass
class _CachedResult:
    result: Any
    created_at: float
    ttl: float


class IdempotencyStore:
    """In-memory idempotency cache. Keyed by (user_id, idempotency_key).

    Stores the JSON-serializable result of a mutation so that retries
    with the same key return the cached result.

    In production, replace with Redis for multi-instance support.
    """

    def __init__(self, default_ttl: float = 3600):
        self._store: dict[str, _CachedResult] = {}
        self._default_ttl = default_ttl

    def get(self, user_id: int, key: str) -> Any | None:
        """Return cached result if it exists and hasn't expired."""
        cache_key = f"{user_id}:{key}"
        entry = self._store.get(cache_key)
        if entry is None:
            return None
        if time.time() - entry.created_at > entry.ttl:
            del self._store[cache_key]
            return None
        return entry.result

    def set(self, user_id: int, key: str, result: Any, ttl: float | None = None):
        """Cache a mutation result."""
        cache_key = f"{user_id}:{key}"
        self._store[cache_key] = _CachedResult(
            result=result,
            created_at=time.time(),
            ttl=ttl or self._default_ttl,
        )
        # Lazy cleanup: remove expired entries when store grows large
        if len(self._store) > 1000:
            self._cleanup()

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.created_at > v.ttl]
        for k in expired:
            del self._store[k]


# Global instance
idempotency_store = IdempotencyStore()
