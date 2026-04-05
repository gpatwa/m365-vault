"""Microsoft Graph API client with OAuth2, throttling, retries, and batching.

Features:
- Client credentials OAuth2 flow via MSAL
- Automatic token caching and refresh
- Exponential backoff with jitter for throttling (429)
- Request batching via $batch endpoint
- Concurrent request limiting with auto-adjustment on throttling
- Least-privilege access modes: backup (read-only) vs restore (read-write)
- Per-workload API call metrics and budget tracking
"""
import asyncio
import json
import logging
import time
import random
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal, Optional

import httpx
import msal

from app.config import settings

logger = logging.getLogger(__name__)


# ── Graph API Metrics (singleton, shared across all clients) ──

class GraphAPIMetrics:
    """Track Graph API usage per tenant per workload.

    Provides visibility into:
    - API call volume and rate
    - Throttle (429) frequency
    - Per-workload breakdown
    - Latency percentiles
    - Budget utilization
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # Per-tenant metrics
        self._calls: dict[str, list] = defaultdict(list)  # tenant_id -> call records
        self._throttle_counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))  # tenant -> workload -> count
        self._max_records = 2000  # Keep last N records per tenant

    def _classify_workload(self, path: str) -> str:
        """Classify a Graph API path to a KavachIQ workload."""
        path_lower = path.lower()
        if '/messages' in path_lower or '/mailfolders' in path_lower or '/calendar' in path_lower or '/contacts' in path_lower:
            return 'exchange'
        if '/drive' in path_lower or '/driveitem' in path_lower:
            return 'onedrive'
        if '/sites' in path_lower or '/lists' in path_lower:
            return 'sharepoint'
        if '/teams' in path_lower or '/channels' in path_lower or '/chats' in path_lower:
            return 'teams'
        if '/directoryroles' in path_lower or '/rolemanagement' in path_lower or '/conditionalaccesspolicies' in path_lower or '/applications' in path_lower or '/serviceprincipals' in path_lower:
            return 'entra_id'
        if '/users' in path_lower or '/organization' in path_lower or '/groups' in path_lower:
            return 'directory'
        return 'other'

    def record(self, tenant_id: str, method: str, path: str, status: int,
               duration_ms: int, retry_after: int = 0, response_headers: dict = None):
        """Record a single Graph API call."""
        workload = self._classify_workload(path)
        record = {
            "ts": datetime.utcnow().isoformat(),
            "method": method,
            "path": path[:120],  # Truncate long paths
            "workload": workload,
            "status": status,
            "duration_ms": duration_ms,
            "retry_after": retry_after,
        }

        # Extract rate limit headers from Microsoft response
        if response_headers:
            for header in ['RateLimit-Limit', 'RateLimit-Remaining', 'RateLimit-Reset']:
                val = response_headers.get(header) or response_headers.get(header.lower())
                if val:
                    record[header.lower().replace('-', '_')] = val

        self._calls[tenant_id].append(record)
        # Trim to max records
        if len(self._calls[tenant_id]) > self._max_records:
            self._calls[tenant_id] = self._calls[tenant_id][-self._max_records:]

        if status == 429:
            self._throttle_counts[tenant_id][workload] += 1

    def get_stats(self, tenant_id: str, window_seconds: int = 300) -> dict:
        """Get metrics summary for a tenant (default: last 5 minutes)."""
        calls = self._calls.get(tenant_id, [])
        now = datetime.utcnow()
        cutoff = now.timestamp() - window_seconds

        recent = [c for c in calls if datetime.fromisoformat(c["ts"]).timestamp() > cutoff]

        if not recent:
            return {
                "tenant_id": tenant_id,
                "window_seconds": window_seconds,
                "total_calls": 0,
                "by_workload": {},
                "throttle_rate_pct": 0,
                "avg_latency_ms": 0,
            }

        # Per-workload breakdown
        by_workload: dict = defaultdict(lambda: {"calls": 0, "throttled": 0, "avg_ms": 0, "errors": 0})
        total_latency = 0
        throttled = 0
        errors = 0

        for c in recent:
            wl = c["workload"]
            by_workload[wl]["calls"] += 1
            by_workload[wl]["avg_ms"] += c["duration_ms"]
            total_latency += c["duration_ms"]
            if c["status"] == 429:
                throttled += 1
                by_workload[wl]["throttled"] += 1
            if c["status"] >= 400:
                errors += 1
                by_workload[wl]["errors"] += 1

        # Compute averages
        for wl in by_workload:
            count = by_workload[wl]["calls"]
            by_workload[wl]["avg_ms"] = round(by_workload[wl]["avg_ms"] / count) if count else 0

        calls_per_min = len(recent) / (window_seconds / 60)

        return {
            "tenant_id": tenant_id,
            "window_seconds": window_seconds,
            "total_calls": len(recent),
            "calls_per_minute": round(calls_per_min, 1),
            "throttled_calls": throttled,
            "throttle_rate_pct": round(throttled / len(recent) * 100, 1) if recent else 0,
            "error_calls": errors,
            "error_rate_pct": round(errors / len(recent) * 100, 1) if recent else 0,
            "avg_latency_ms": round(total_latency / len(recent)) if recent else 0,
            "by_workload": dict(by_workload),
            "lifetime_throttle_counts": dict(self._throttle_counts.get(tenant_id, {})),
        }

    def get_all_tenants(self) -> list[str]:
        """List all tenants with recorded metrics."""
        return list(self._calls.keys())


# Global singleton
graph_metrics = GraphAPIMetrics()


class GraphAPIError(Exception):
    """Custom exception for Graph API errors."""
    def __init__(self, status_code: int, message: str, error_code: str = None):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(f"Graph API Error {status_code}: {message}")


class ReadOnlyViolationError(GraphAPIError):
    """Raised when a write operation is attempted on a read-only (backup) client."""
    def __init__(self, method: str, url: str):
        super().__init__(
            403,
            f"Write operation ({method}) blocked: backup client is read-only. "
            f"Restore operations require a read-write client. URL: {url}",
            "READ_ONLY_VIOLATION",
        )


class GraphClient:
    """Throttle-aware Microsoft Graph API client with least-privilege access modes.

    Access modes:
    - "backup": Read-only — GET requests only. POST/PUT/DELETE are blocked.
    - "restore": Read-write — all HTTP methods allowed.
    - "default": Legacy mode using .default scope (all permissions).
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        access_mode: Literal["backup", "restore", "default"] = "default",
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_mode = access_mode
        self._token_cache: Optional[dict] = None
        self._token_expires_at: float = 0
        self._semaphore = asyncio.Semaphore(settings.GRAPH_MAX_CONCURRENT_REQUESTS)
        self._msal_app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"{settings.MS_AUTH_URL}/{tenant_id}",
            client_credential=client_secret,
        )

        # Circuit breaker integration
        from app.services.circuit_breaker import circuit_breaker
        self._circuit_breaker = circuit_breaker

        # Throttle tracking
        self._request_count = 0
        self._throttle_count = 0
        self._last_request_time = 0

        # Auto-adjust concurrency: reduce when throttled, recover when clear
        self._default_concurrency = settings.GRAPH_MAX_CONCURRENT_REQUESTS
        self._current_concurrency = self._default_concurrency
        self._consecutive_throttles = 0
        self._last_throttle_reduce = 0

        logger.info(
            f"GraphClient initialized in '{access_mode}' mode for tenant {tenant_id} "
            f"(concurrency: {self._current_concurrency})"
        )

    def _get_scopes(self) -> list[str]:
        """Get OAuth2 scopes for client credential flow.

        Client credential flows MUST use '.default' — individual scopes like
        Mail.Read are not supported. The actual permissions are configured as
        Application Permissions in the Azure AD App Registration.

        The access_mode ('backup' vs 'restore') controls the client-side
        read-only guard (_ensure_write_allowed), NOT the token scopes.

        See MS_GRAPH_BACKUP_SCOPES / MS_GRAPH_RESTORE_SCOPES in config.py
        for the list of Application Permissions each mode requires.
        """
        return [settings.MS_GRAPH_SCOPE]

    def _ensure_write_allowed(self, method: str, url: str):
        """Block write operations on read-only (backup) clients."""
        if self.access_mode == "backup" and method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            raise ReadOnlyViolationError(method, url)

    async def _get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if self._token_cache and time.time() < self._token_expires_at - 60:
            return self._token_cache["access_token"]

        scopes = self._get_scopes()
        result = self._msal_app.acquire_token_for_client(scopes=scopes)

        if "access_token" not in result:
            error_desc = result.get("error_description", "Unknown error")
            raise GraphAPIError(401, f"Failed to acquire token: {error_desc}")

        self._token_cache = result
        self._token_expires_at = time.time() + result.get("expires_in", 3600)
        logger.debug(f"Token acquired for mode '{self.access_mode}' with {len(scopes)} scope(s)")
        return result["access_token"]

    async def _request(
        self,
        method: str,
        url: str,
        headers: dict = None,
        params: dict = None,
        json_data: dict = None,
        data: bytes = None,
        retry_count: int = 0,
    ) -> httpx.Response:
        """Make an HTTP request with throttling, retry logic, and circuit breaker.

        Enforces read-only mode for backup clients — blocks POST/PUT/PATCH/DELETE.
        """
        # Enforce least-privilege: block writes on read-only clients
        self._ensure_write_allowed(method, url)

        # Circuit breaker: fail fast if the tenant's API is in bad state
        if self._circuit_breaker.is_open(self.tenant_id):
            cb_status = self._circuit_breaker.get_status(self.tenant_id)
            raise GraphAPIError(
                503,
                f"Circuit breaker OPEN for tenant {self.tenant_id}. "
                f"API failing at {cb_status['failure_rate']:.0%} rate. "
                f"Retry in {cb_status['cooldown_remaining']}s.",
                "CIRCUIT_BREAKER_OPEN",
            )

        async with self._semaphore:
            token = await self._get_token()
            req_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            if headers:
                req_headers.update(headers)

            start_time = time.time()
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    self._request_count += 1
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=req_headers,
                        params=params,
                        json=json_data,
                        content=data,
                    )
                    duration_ms = int((time.time() - start_time) * 1000)

                    # Record metrics for every call
                    graph_metrics.record(
                        tenant_id=self.tenant_id,
                        method=method,
                        path=url.replace(settings.MS_GRAPH_BASE_URL, ''),
                        status=response.status_code,
                        duration_ms=duration_ms,
                        response_headers=dict(response.headers),
                    )

                    # Handle throttling (429)
                    if response.status_code == 429:
                        self._throttle_count += 1
                        self._consecutive_throttles += 1

                        # Auto-reduce concurrency when getting throttled
                        self._auto_reduce_concurrency()

                        retry_after = int(response.headers.get("Retry-After", 5))

                        # Record throttle with retry_after
                        graph_metrics.record(
                            tenant_id=self.tenant_id,
                            method=method,
                            path=url.replace(settings.MS_GRAPH_BASE_URL, ''),
                            status=429,
                            duration_ms=duration_ms,
                            retry_after=retry_after,
                            response_headers=dict(response.headers),
                        )

                        if retry_count >= settings.GRAPH_MAX_RETRIES:
                            self._circuit_breaker.record_failure(self.tenant_id)
                            raise GraphAPIError(429, "Max retries exceeded due to throttling")

                        # Exponential backoff with jitter
                        delay = min(
                            retry_after * (2 ** retry_count) + random.uniform(0, 1),
                            120,
                        )
                        logger.warning(
                            f"Throttled (429). Retry {retry_count + 1}/{settings.GRAPH_MAX_RETRIES} "
                            f"after {delay:.1f}s (concurrency: {self._current_concurrency})"
                        )
                        await asyncio.sleep(delay)
                        return await self._request(
                            method, url, headers, params, json_data, data, retry_count + 1
                        )

                    # Success — record for circuit breaker, clear throttle counter
                    self._circuit_breaker.record_success(self.tenant_id)
                    self._consecutive_throttles = 0
                    self._auto_restore_concurrency()

                    # Handle server errors with retry
                    if response.status_code >= 500 and retry_count < settings.GRAPH_MAX_RETRIES:
                        delay = settings.GRAPH_RETRY_BASE_DELAY * (2 ** retry_count) + random.uniform(0, 1)
                        logger.warning(
                            f"Server error {response.status_code}. Retry {retry_count + 1} after {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        return await self._request(
                            method, url, headers, params, json_data, data, retry_count + 1
                        )

                    # Handle client errors
                    if response.status_code >= 400:
                        self._circuit_breaker.record_failure(self.tenant_id)
                        try:
                            error_body = response.json()
                            error_msg = error_body.get("error", {}).get("message", response.text)
                            error_code = error_body.get("error", {}).get("code", "")
                        except Exception:
                            error_msg = response.text
                            error_code = ""
                        raise GraphAPIError(response.status_code, error_msg, error_code)

                    return response

                except httpx.TimeoutException:
                    duration_ms = int((time.time() - start_time) * 1000)
                    graph_metrics.record(
                        tenant_id=self.tenant_id, method=method,
                        path=url.replace(settings.MS_GRAPH_BASE_URL, ''),
                        status=408, duration_ms=duration_ms,
                    )
                    if retry_count < settings.GRAPH_MAX_RETRIES:
                        delay = settings.GRAPH_RETRY_BASE_DELAY * (2 ** retry_count)
                        logger.warning(f"Timeout. Retry {retry_count + 1} after {delay:.1f}s")
                        await asyncio.sleep(delay)
                        return await self._request(
                            method, url, headers, params, json_data, data, retry_count + 1
                        )
                    self._circuit_breaker.record_failure(self.tenant_id)
                    raise GraphAPIError(408, "Request timed out after max retries")

    def _auto_reduce_concurrency(self):
        """Reduce concurrent requests when getting throttled."""
        now = time.time()
        if self._consecutive_throttles >= 3 and now - self._last_throttle_reduce > 30:
            old = self._current_concurrency
            self._current_concurrency = max(2, self._current_concurrency // 2)
            if old != self._current_concurrency:
                self._semaphore = asyncio.Semaphore(self._current_concurrency)
                self._last_throttle_reduce = now
                logger.warning(
                    f"Auto-reduced Graph concurrency: {old} → {self._current_concurrency} "
                    f"(tenant {self.tenant_id}, {self._consecutive_throttles} consecutive 429s)"
                )

    def _auto_restore_concurrency(self):
        """Gradually restore concurrency after throttling clears."""
        if self._current_concurrency < self._default_concurrency:
            # Restore after 60s of no throttling
            if time.time() - self._last_throttle_reduce > 60:
                old = self._current_concurrency
                self._current_concurrency = min(self._default_concurrency, self._current_concurrency + 2)
                self._semaphore = asyncio.Semaphore(self._current_concurrency)
                logger.info(
                    f"Auto-restored Graph concurrency: {old} → {self._current_concurrency} "
                    f"(tenant {self.tenant_id})"
                )

    async def get(self, path: str, params: dict = None) -> dict:
        """GET request to Graph API."""
        url = f"{settings.MS_GRAPH_BASE_URL}{path}"
        response = await self._request("GET", url, params=params)
        return response.json()

    async def post(self, path: str, json_data: dict = None) -> dict:
        """POST request to Graph API."""
        url = f"{settings.MS_GRAPH_BASE_URL}{path}"
        response = await self._request("POST", url, json_data=json_data)
        if response.status_code == 204:
            return {}
        return response.json()

    async def put(self, path: str, data: bytes = None, json_data: dict = None) -> dict:
        """PUT request to Graph API."""
        url = f"{settings.MS_GRAPH_BASE_URL}{path}"
        headers = {}
        if data:
            headers["Content-Type"] = "application/octet-stream"
        response = await self._request("PUT", url, headers=headers, json_data=json_data, data=data)
        if response.status_code == 204:
            return {}
        return response.json()

    async def delete(self, path: str) -> None:
        """DELETE request to Graph API."""
        url = f"{settings.MS_GRAPH_BASE_URL}{path}"
        await self._request("DELETE", url)

    async def get_binary(self, path: str) -> bytes:
        """GET request that returns binary data (file downloads)."""
        url = f"{settings.MS_GRAPH_BASE_URL}{path}"
        response = await self._request("GET", url)
        return response.content

    async def get_all_pages(self, path: str, params: dict = None, extra_headers: dict = None) -> list:
        """Get all pages of a paginated response."""
        all_items = []
        url = f"{settings.MS_GRAPH_BASE_URL}{path}"

        while url:
            response = await self._request("GET", url, params=params, headers=extra_headers)
            data = response.json()
            items = data.get("value", [])
            all_items.extend(items)

            # Follow @odata.nextLink for pagination
            url = data.get("@odata.nextLink")
            params = None  # nextLink already contains params

        return all_items

    async def get_delta(self, path: str, delta_token: str = None) -> tuple[list, str]:
        """Get delta (incremental) changes.

        Returns (changed_items, new_delta_token).
        """
        all_items = []
        params = None

        if delta_token:
            url = delta_token  # Delta token is a full URL
        else:
            url = f"{settings.MS_GRAPH_BASE_URL}{path}"

        while url:
            response = await self._request("GET", url, params=params)
            data = response.json()
            items = data.get("value", [])
            all_items.extend(items)

            # Check for next page or delta link
            if "@odata.nextLink" in data:
                url = data["@odata.nextLink"]
            elif "@odata.deltaLink" in data:
                new_delta_token = data["@odata.deltaLink"]
                return all_items, new_delta_token
            else:
                break
            params = None

        return all_items, None

    async def batch_request(self, requests: list[dict]) -> list[dict]:
        """Execute batch requests via $batch endpoint.

        Each request dict: {"id": "1", "method": "GET", "url": "/users/..."}
        Maximum 20 requests per batch (Graph API limit).
        """
        results = []
        # Split into chunks of GRAPH_BATCH_SIZE
        for i in range(0, len(requests), settings.GRAPH_BATCH_SIZE):
            chunk = requests[i:i + settings.GRAPH_BATCH_SIZE]
            batch_body = {"requests": chunk}
            response = await self._request(
                "POST", settings.MS_GRAPH_BATCH_URL, json_data=batch_body
            )
            batch_results = response.json().get("responses", [])
            results.extend(batch_results)

        return results

    def get_stats(self) -> dict:
        """Get API usage statistics."""
        return {
            "total_requests": self._request_count,
            "throttle_count": self._throttle_count,
            "throttle_rate": (
                round(self._throttle_count / self._request_count * 100, 2)
                if self._request_count > 0 else 0
            ),
        }
