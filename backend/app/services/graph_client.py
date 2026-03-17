"""Microsoft Graph API client with OAuth2, throttling, retries, and batching.

Features:
- Client credentials OAuth2 flow via MSAL
- Automatic token caching and refresh
- Exponential backoff with jitter for throttling (429)
- Request batching via $batch endpoint
- Concurrent request limiting
"""
import asyncio
import json
import logging
import time
import random
from typing import Any, Optional

import httpx
import msal

from app.config import settings

logger = logging.getLogger(__name__)


class GraphAPIError(Exception):
    """Custom exception for Graph API errors."""
    def __init__(self, status_code: int, message: str, error_code: str = None):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(f"Graph API Error {status_code}: {message}")


class GraphClient:
    """Throttle-aware Microsoft Graph API client."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._token_cache: Optional[dict] = None
        self._token_expires_at: float = 0
        self._semaphore = asyncio.Semaphore(settings.GRAPH_MAX_CONCURRENT_REQUESTS)
        self._msal_app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"{settings.MS_AUTH_URL}/{tenant_id}",
            client_credential=client_secret,
        )

        # Throttle tracking
        self._request_count = 0
        self._throttle_count = 0
        self._last_request_time = 0

    async def _get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if self._token_cache and time.time() < self._token_expires_at - 60:
            return self._token_cache["access_token"]

        result = self._msal_app.acquire_token_for_client(
            scopes=[settings.MS_GRAPH_SCOPE]
        )

        if "access_token" not in result:
            error_desc = result.get("error_description", "Unknown error")
            raise GraphAPIError(401, f"Failed to acquire token: {error_desc}")

        self._token_cache = result
        self._token_expires_at = time.time() + result.get("expires_in", 3600)
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
        """Make an HTTP request with throttling and retry logic."""
        async with self._semaphore:
            token = await self._get_token()
            req_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            if headers:
                req_headers.update(headers)

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

                    # Handle throttling (429)
                    if response.status_code == 429:
                        self._throttle_count += 1
                        if retry_count >= settings.GRAPH_MAX_RETRIES:
                            raise GraphAPIError(429, "Max retries exceeded due to throttling")

                        retry_after = int(response.headers.get("Retry-After", 5))
                        # Exponential backoff with jitter
                        delay = min(
                            retry_after * (2 ** retry_count) + random.uniform(0, 1),
                            120,
                        )
                        logger.warning(
                            f"Throttled (429). Retry {retry_count + 1}/{settings.GRAPH_MAX_RETRIES} "
                            f"after {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        return await self._request(
                            method, url, headers, params, json_data, data, retry_count + 1
                        )

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
                    if retry_count < settings.GRAPH_MAX_RETRIES:
                        delay = settings.GRAPH_RETRY_BASE_DELAY * (2 ** retry_count)
                        logger.warning(f"Timeout. Retry {retry_count + 1} after {delay:.1f}s")
                        await asyncio.sleep(delay)
                        return await self._request(
                            method, url, headers, params, json_data, data, retry_count + 1
                        )
                    raise GraphAPIError(408, "Request timed out after max retries")

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
