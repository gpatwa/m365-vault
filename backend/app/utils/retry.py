"""Retry utilities for backup operations.

Provides:
- retry_async: Decorator for retrying async functions with exponential backoff
- RetryableError: Exception class for errors that should trigger retry
- classify_error: Determines if a Graph API error is retryable
"""
import asyncio
import functools
import logging
import random
from typing import Callable, Optional, Type

from app.services.graph_client import GraphAPIError

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Marks an error as retryable."""
    pass


class PermanentError(Exception):
    """Marks an error as non-retryable (e.g., 404 not found, 403 forbidden)."""
    pass


# Graph API error codes that are safe to retry
RETRYABLE_ERROR_CODES = {
    "activityLimitReached",
    "serviceNotAvailable",
    "quotaLimitReached",
    "generalException",      # Transient server errors
    "timeout",
    "resourceBusy",
    "tooManyRequests",
    "serviceUnavailable",
}

# HTTP status codes that are safe to retry
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# HTTP status codes that should NOT be retried
PERMANENT_STATUS_CODES = {400, 401, 403, 404, 405, 409, 410, 422}


def classify_error(error: Exception) -> str:
    """Classify an error as 'retryable', 'permanent', or 'unknown'.

    Follows Microsoft's guidance:
    https://learn.microsoft.com/en-us/graph/errors#handling-errors
    """
    if isinstance(error, GraphAPIError):
        if error.status_code in RETRYABLE_STATUS_CODES:
            return "retryable"
        if error.status_code in PERMANENT_STATUS_CODES:
            return "permanent"
        if error.error_code in RETRYABLE_ERROR_CODES:
            return "retryable"
        return "permanent"

    # Network/connection errors are retryable
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return "retryable"

    return "unknown"


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """Decorator for retrying async operations with exponential backoff + jitter.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback(attempt, error, delay) called before each retry
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except PermanentError:
                    raise  # Never retry permanent errors
                except retryable_exceptions as e:
                    last_error = e

                    # Check if this specific error is retryable
                    error_class = classify_error(e)
                    if error_class == "permanent":
                        raise

                    if attempt >= max_retries:
                        break

                    # Exponential backoff with jitter
                    delay = min(
                        base_delay * (2 ** attempt) + random.uniform(0, 1),
                        max_delay,
                    )

                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    else:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                            f"after {delay:.1f}s — {type(e).__name__}: {e}"
                        )

                    await asyncio.sleep(delay)

            raise last_error

        return wrapper
    return decorator


def categorize_error(error: Exception) -> str:
    """Map an exception to an ErrorCategory string value.

    Used by workers to record structured failed-item records.
    Returns the enum value string (e.g., "permission_denied").
    """
    if isinstance(error, GraphAPIError):
        status = error.status_code
        code = (error.error_code or "").lower()
        if status == 401:
            return "auth_expired"
        if status == 403:
            return "permission_denied"
        if status == 404 or "notfound" in code or "itemnotfound" in code:
            return "not_found"
        if status == 429 or "throttl" in code or "activitylimitreached" in code:
            return "throttled"
        if status == 408:
            return "timeout"
        if status == 413 or "maxrequestbody" in code or "toolarge" in code:
            return "file_too_large"
        if status == 507 or "quota" in code:
            return "quota_exceeded"
        if 500 <= status < 600:
            return "server_error"
        if "invalid" in code or "malformed" in code:
            return "invalid_data"
        return "unknown"

    if isinstance(error, (ConnectionError, OSError)):
        return "network_error"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, (ValueError, KeyError, TypeError)):
        return "invalid_data"

    error_str = str(error).lower()
    if "encrypt" in error_str or "dek" in error_str or "key" in error_str:
        return "encryption_error"
    if "storage" in error_str or "disk" in error_str:
        return "storage_error"

    return "unknown"


async def record_failed_item(
    db,
    snapshot_id: int,
    protected_object_id: int,
    error: Exception,
    ms_item_id: str = None,
    item_type_str: str = None,
    item_name: str = None,
    item_path: str = None,
    retries_attempted: int = 0,
):
    """Record a failed item in the failed_items table.

    Call this from workers when an item fails backup after retries.
    """
    from app.models.snapshot import FailedItem, ErrorCategory, ERROR_RESOLUTION_GUIDE, ItemType

    category_str = categorize_error(error)
    category = ErrorCategory(category_str)

    http_status = None
    error_code = None
    if isinstance(error, GraphAPIError):
        http_status = error.status_code
        error_code = error.error_code

    # Determine if retryable
    can_retry = category_str not in ("not_found", "permission_denied", "file_too_large", "invalid_data")

    # Parse item type
    item_type = None
    if item_type_str:
        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            pass

    failed = FailedItem(
        snapshot_id=snapshot_id,
        protected_object_id=protected_object_id,
        ms_item_id=ms_item_id,
        item_type=item_type,
        item_name=item_name,
        item_path=item_path,
        error_category=category,
        error_message=str(error)[:2000],
        error_code=error_code,
        http_status=http_status,
        retries_attempted=retries_attempted,
        resolution_hint=ERROR_RESOLUTION_GUIDE.get(category, ""),
        can_retry=can_retry,
    )
    db.add(failed)

    # Increment snapshot.items_failed counter
    from app.models.snapshot import Snapshot
    snapshot = await db.get(Snapshot, snapshot_id)
    if snapshot:
        snapshot.items_failed = (snapshot.items_failed or 0) + 1

    return failed


class RetryTracker:
    """Tracks retry statistics for a backup operation."""

    def __init__(self):
        self.total_items = 0
        self.succeeded = 0
        self.failed_items: list[dict] = []
        self.total_retries = 0

    def record_success(self, item_id: str):
        self.total_items += 1
        self.succeeded += 1

    def record_failure(self, item_id: str, error: str, retries_attempted: int = 0):
        self.total_items += 1
        self.failed_items.append({
            "item_id": item_id,
            "error": error,
            "retries_attempted": retries_attempted,
        })
        self.total_retries += retries_attempted

    def summary(self) -> dict:
        return {
            "total_items": self.total_items,
            "succeeded": self.succeeded,
            "failed": len(self.failed_items),
            "total_retries": self.total_retries,
            "failed_items": self.failed_items[:50],
        }
