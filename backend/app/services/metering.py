"""Per-tenant usage metering — Redis-backed atomic counters.

Metrics are accumulated in Redis (cross-pod safe) and flushed
to the tenant_usage_metrics table every 5 minutes by the scheduler.

Redis key pattern: kavachiq:meter:{tenant_id}:{YYYY-MM-DD}:{metric}
"""
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


async def record_api_call(tenant_id: int, calls: int = 1, throttled: int = 0):
    """Record Graph API calls for a tenant. Atomic via Redis INCRBY."""
    try:
        r = await _get_redis()
        today = date.today().isoformat()
        prefix = f"kavachiq:meter:{tenant_id}:{today}"
        await r.incrby(f"{prefix}:graph_api_calls", calls)
        if throttled:
            await r.incrby(f"{prefix}:graph_api_throttled", throttled)
    except Exception as e:
        logger.debug(f"Metering record_api_call failed: {e}")


async def record_backup_duration(tenant_id: int, duration_seconds: int, items: int = 0):
    """Record backup execution time for a tenant."""
    try:
        r = await _get_redis()
        today = date.today().isoformat()
        prefix = f"kavachiq:meter:{tenant_id}:{today}"
        await r.incrby(f"{prefix}:backup_duration_seconds", duration_seconds)
        if items:
            await r.incrby(f"{prefix}:items_backed_up", items)
    except Exception as e:
        logger.debug(f"Metering record_backup_duration failed: {e}")


async def record_restore_duration(tenant_id: int, duration_seconds: int, items: int = 0):
    """Record restore execution time for a tenant."""
    try:
        r = await _get_redis()
        today = date.today().isoformat()
        prefix = f"kavachiq:meter:{tenant_id}:{today}"
        await r.incrby(f"{prefix}:restore_duration_seconds", duration_seconds)
        if items:
            await r.incrby(f"{prefix}:items_restored", items)
    except Exception as e:
        logger.debug(f"Metering record_restore_duration failed: {e}")


async def flush_to_db():
    """Flush Redis metering counters to tenant_usage_metrics table.

    Called by scheduler every 5 minutes. Reads all kavachiq:meter:* keys,
    upserts into DB, then deletes the Redis keys.
    """
    from app.database import async_session
    from app.models.usage_metric import TenantUsageMetric
    from sqlalchemy import select

    try:
        r = await _get_redis()
        keys = []
        async for key in r.scan_iter("kavachiq:meter:*"):
            keys.append(key)

        if not keys:
            return

        # Group by (tenant_id, date)
        buckets = {}
        for key in keys:
            parts = key.split(":")
            if len(parts) != 5:
                continue
            _, _, tenant_id_str, metric_date, metric_name = parts
            bucket_key = (int(tenant_id_str), metric_date)
            if bucket_key not in buckets:
                buckets[bucket_key] = {}
            value = await r.get(key)
            buckets[bucket_key][metric_name] = int(value or 0)

        async with async_session() as db:
            for (tenant_id, metric_date_str), metrics in buckets.items():
                metric_date = date.fromisoformat(metric_date_str)

                # Upsert: check if row exists
                existing = await db.execute(
                    select(TenantUsageMetric).where(
                        TenantUsageMetric.tenant_id == tenant_id,
                        TenantUsageMetric.metric_date == metric_date,
                    )
                )
                row = existing.scalar_one_or_none()

                if row:
                    row.graph_api_calls = (row.graph_api_calls or 0) + metrics.get("graph_api_calls", 0)
                    row.graph_api_throttled = (row.graph_api_throttled or 0) + metrics.get("graph_api_throttled", 0)
                    row.backup_duration_seconds = (row.backup_duration_seconds or 0) + metrics.get("backup_duration_seconds", 0)
                    row.restore_duration_seconds = (row.restore_duration_seconds or 0) + metrics.get("restore_duration_seconds", 0)
                    row.items_backed_up = (row.items_backed_up or 0) + metrics.get("items_backed_up", 0)
                    row.items_restored = (row.items_restored or 0) + metrics.get("items_restored", 0)
                else:
                    row = TenantUsageMetric(
                        tenant_id=tenant_id,
                        metric_date=metric_date,
                        graph_api_calls=metrics.get("graph_api_calls", 0),
                        graph_api_throttled=metrics.get("graph_api_throttled", 0),
                        backup_duration_seconds=metrics.get("backup_duration_seconds", 0),
                        restore_duration_seconds=metrics.get("restore_duration_seconds", 0),
                        items_backed_up=metrics.get("items_backed_up", 0),
                        items_restored=metrics.get("items_restored", 0),
                    )
                    db.add(row)

            await db.commit()

        # Delete flushed keys
        if keys:
            await r.delete(*keys)

        logger.info(f"Metering: flushed {len(buckets)} tenant-day buckets from Redis to DB")

    except Exception as e:
        logger.warning(f"Metering flush failed: {e}")


async def get_cost_breakdown(tenant_id: int, days: int = 30) -> dict:
    """Compute cost breakdown for a tenant over the last N days.

    Returns: { users, storage, api_calls, compute, total }
    """
    from app.database import async_session
    from app.models.usage_metric import TenantUsageMetric
    from app.models.protected_object import ProtectedObject, ProtectionStatus
    from app.models.snapshot import Snapshot, SnapshotStatus
    from sqlalchemy import select, func

    since = date.today().replace(day=1) if days >= 28 else date.fromordinal(date.today().toordinal() - days)

    async with async_session() as db:
        # User count
        user_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )).scalar() or 0

        # Storage bytes
        storage_bytes = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
        )).scalar() or 0

        # Usage metrics from DB
        metrics_result = await db.execute(
            select(
                func.sum(TenantUsageMetric.graph_api_calls),
                func.sum(TenantUsageMetric.backup_duration_seconds),
                func.sum(TenantUsageMetric.restore_duration_seconds),
            ).where(
                TenantUsageMetric.tenant_id == tenant_id,
                TenantUsageMetric.metric_date >= since,
            )
        )
        row = metrics_result.one_or_none()
        api_calls = int(row[0] or 0) if row else 0
        backup_seconds = int(row[1] or 0) if row else 0
        restore_seconds = int(row[2] or 0) if row else 0

    # Cost estimation (Azure pricing)
    storage_gb = storage_bytes / (1024 ** 3)
    compute_minutes = (backup_seconds + restore_seconds) / 60.0

    # Pricing: $1.50/user, $0.018/GB/month storage, $0.000012/vCPU-second compute
    user_cost = user_count * 1.50
    storage_cost = storage_gb * 0.018
    compute_cost = (backup_seconds + restore_seconds) * 0.5 * 0.000012  # 0.5 vCPU
    api_cost = 0.0  # Graph API is free but tracked for capacity

    return {
        "users": {"count": user_count, "cost": round(user_cost, 2)},
        "storage": {"gb": round(storage_gb, 3), "cost": round(storage_cost, 2)},
        "api_calls": {"count": api_calls, "cost": round(api_cost, 2)},
        "compute": {"minutes": round(compute_minutes, 1), "cost": round(compute_cost, 4)},
        "total": round(user_cost + storage_cost + compute_cost + api_cost, 2),
    }


# ── Redis connection helper ──

_redis_client = None

async def _get_redis():
    """Get or create Redis client for metering."""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        from app.config import settings
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client
