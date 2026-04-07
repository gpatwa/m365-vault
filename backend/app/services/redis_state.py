"""Redis State Store — shared state across multiple backend pods.

Replaces in-memory dicts (_onboard_states, _rate_limit_store, consent tokens)
that lose data on pod restart and don't work across replicas.

Falls back to in-memory dict when Redis is unavailable (dev without Redis).
"""
import json
import logging
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client = None
_fallback_store: dict[str, str] = {}  # In-memory fallback


async def _get_redis():
    """Get or create Redis connection. Returns None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not settings.REDIS_URL:
        return None

    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=5,
            decode_responses=True,
        )
        await _redis_client.ping()
        logger.info("Redis state store connected")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
        _redis_client = None
        return None


async def set_state(key: str, value: Any, ttl_seconds: int = 600):
    """Store state in Redis (or in-memory fallback). Default TTL: 10 minutes."""
    serialized = json.dumps(value, default=str)
    redis = await _get_redis()
    if redis:
        try:
            await redis.setex(f"kavachiq:state:{key}", ttl_seconds, serialized)
            return
        except Exception as e:
            logger.warning(f"Redis set failed, using fallback: {e}")

    # Fallback: in-memory with expiry tracking
    _fallback_store[key] = json.dumps({"data": serialized, "expires": time.time() + ttl_seconds})


async def get_state(key: str) -> Any | None:
    """Retrieve state from Redis (or in-memory fallback). Returns None if expired/missing."""
    redis = await _get_redis()
    if redis:
        try:
            raw = await redis.get(f"kavachiq:state:{key}")
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"Redis get failed, using fallback: {e}")

    # Fallback
    raw = _fallback_store.get(key)
    if raw:
        entry = json.loads(raw)
        if time.time() < entry.get("expires", 0):
            return json.loads(entry["data"])
        else:
            _fallback_store.pop(key, None)
    return None


async def delete_state(key: str):
    """Delete state from Redis (or in-memory fallback)."""
    redis = await _get_redis()
    if redis:
        try:
            await redis.delete(f"kavachiq:state:{key}")
            return
        except Exception:
            pass
    _fallback_store.pop(key, None)


async def increment_rate(key: str, window_seconds: int = 60) -> int:
    """Increment a rate counter. Returns current count within window.

    Uses Redis sorted sets for efficient sliding window rate limiting.
    Falls back to in-memory counting.
    """
    redis = await _get_redis()
    now = time.time()
    redis_key = f"kavachiq:rate:{key}"

    if redis:
        try:
            pipe = redis.pipeline()
            # Remove old entries outside window
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            # Count requests in window
            pipe.zcard(redis_key)
            # Set TTL to clean up abandoned keys
            pipe.expire(redis_key, window_seconds * 2)
            results = await pipe.execute()
            return results[2]  # zcard result
        except Exception as e:
            logger.warning(f"Redis rate limit failed: {e}")

    # Fallback: simple counter (not accurate across pods)
    count_key = f"rate:{key}"
    raw = _fallback_store.get(count_key)
    if raw:
        entry = json.loads(raw)
        if now - entry.get("start", 0) < window_seconds:
            entry["count"] = entry.get("count", 0) + 1
            _fallback_store[count_key] = json.dumps(entry)
            return entry["count"]
    _fallback_store[count_key] = json.dumps({"start": now, "count": 1})
    return 1
