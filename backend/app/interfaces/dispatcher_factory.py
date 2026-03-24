"""Dispatcher factory — returns the correct dispatcher based on config.

Usage:
    from app.interfaces.dispatcher_factory import get_dispatcher
    dispatcher = get_dispatcher()
    result = await dispatcher.dispatch_backup_object(msg, db=db)
"""
import logging
from app.config import settings
from app.interfaces.job_dispatcher import JobDispatcher, InProcessDispatcher

logger = logging.getLogger(__name__)

_dispatcher: JobDispatcher | None = None


def get_dispatcher() -> JobDispatcher:
    """Get or create the global dispatcher instance.

    Returns InProcessDispatcher (default) or RedisDispatcher based on
    DISPATCH_MODE config. Thread-safe for the async context.
    """
    global _dispatcher

    if _dispatcher is None:
        if settings.DISPATCH_MODE == "redis":
            try:
                from app.interfaces.redis_dispatcher import RedisDispatcher
                _dispatcher = RedisDispatcher(settings.REDIS_URL)
                logger.info(f"Dispatcher: Redis ({settings.REDIS_URL})")
            except ImportError:
                logger.warning("Redis dispatcher not available, falling back to in-process")
                _dispatcher = InProcessDispatcher()
        else:
            _dispatcher = InProcessDispatcher()
            logger.info("Dispatcher: InProcess (single-container mode)")

    return _dispatcher


def reset_dispatcher():
    """Reset the global dispatcher (for testing)."""
    global _dispatcher
    _dispatcher = None
