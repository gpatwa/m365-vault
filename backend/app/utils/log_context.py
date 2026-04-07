"""Structured logging context — propagates tenant_id, workload, job_id across async calls.

Every log line automatically includes tenant context without manual extra= params.
Uses Python contextvars (async-safe, zero-copy, works with asyncio.gather).

Usage:
    from app.utils.log_context import get_logger, tenant_ctx, workload_ctx

    logger = get_logger(__name__)

    # Set context (propagates to all async calls within scope)
    tenant_ctx.set(tenant_id)
    workload_ctx.set("exchange")

    # All subsequent logs include tenant_id + workload automatically
    logger.info("Backup started")
    # → {"tenant_id": 1, "workload": "exchange", "message": "Backup started"}
"""
import contextvars
import functools
import logging
from typing import Any

# ── Context Variables (async-safe) ──────────────────────────
tenant_ctx: contextvars.ContextVar[int | None] = contextvars.ContextVar('tenant_id', default=None)
workload_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar('workload', default=None)
job_ctx: contextvars.ContextVar[int | None] = contextvars.ContextVar('job_id', default=None)
user_ctx: contextvars.ContextVar[int | None] = contextvars.ContextVar('user_id', default=None)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that auto-injects context vars into every log line.

    Works with both text and JSON formatters. Context fields are added
    to the `extra` dict which the JSONFormatter in main.py already reads.
    """
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.setdefault('extra', {})
        # Only inject non-None values (reduces noise)
        ctx_values = {
            'tenant_id': tenant_ctx.get(),
            'workload': workload_ctx.get(),
            'job_id': job_ctx.get(),
            'user_id': user_ctx.get(),
        }
        for k, v in ctx_values.items():
            if v is not None:
                extra[k] = v
        return msg, kwargs


def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger. Drop-in replacement for logging.getLogger()."""
    return ContextLogger(logging.getLogger(name), {})


def set_context(
    tenant_id: int = None,
    workload: str = None,
    job_id: int = None,
    user_id: int = None,
) -> list:
    """Set multiple context vars at once. Returns tokens for reset."""
    tokens = []
    if tenant_id is not None:
        tokens.append(tenant_ctx.set(tenant_id))
    if workload is not None:
        tokens.append(workload_ctx.set(workload))
    if job_id is not None:
        tokens.append(job_ctx.set(job_id))
    if user_id is not None:
        tokens.append(user_ctx.set(user_id))
    return tokens


def clear_context(tokens: list):
    """Reset context vars using saved tokens."""
    for token in tokens:
        token.var.reset(token)


def with_context(**ctx_kwargs):
    """Decorator that sets logging context for the duration of an async function.

    Usage:
        @with_context(workload="exchange")
        async def backup_exchange(self, tenant_id, ...):
            ...  # All logs inside include workload="exchange"
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tokens = set_context(**ctx_kwargs)
            try:
                return await func(*args, **kwargs)
            finally:
                clear_context(tokens)
        return wrapper
    return decorator
