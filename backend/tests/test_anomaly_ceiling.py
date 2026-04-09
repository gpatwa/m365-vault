"""Tests for anomaly detection ceiling, dedup, auto-resolve, and TTL cleanup."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from app.database import async_session
from app.models.health_baseline import HealthBaseline, AnomalyEvent
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.services.smart_engine import SmartEngine
from app.services.scheduler import cleanup_old_anomalies


@pytest_asyncio.fixture
async def tenant_with_baselines(db):
    """Tenant with established baselines and enough snapshots for detection."""
    tenant = Tenant(
        name="AnomalyTest Corp",
        ms_tenant_id="anomaly-test-123",
        client_id="test-client-id",
        client_secret_encrypted="test-secret-enc",
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    # Create protected object + 3 snapshots (pass grace period)
    obj = ProtectedObject(
        tenant_id=tenant.id,
        ms_object_id="user@test.com",
        display_name="Test User",
        workload_type="exchange",
        status=ProtectionStatus.PROTECTED,
    )
    db.add(obj)
    await db.flush()

    from app.models.snapshot import SnapshotType
    for i in range(3):
        snap = Snapshot(
            protected_object_id=obj.id,
            snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            item_count=100,
            size_bytes=50000,
            completed_at=datetime.utcnow() - timedelta(hours=i),
        )
        db.add(snap)

    # Create baseline with known values
    baseline = HealthBaseline(
        tenant_id=tenant.id,
        workload_type="exchange",
        metric_name="item_count",
        avg_value=100.0,
        std_dev=10.0,
        min_value=90.0,
        max_value=110.0,
        sample_count=10,
    )
    db.add(baseline)

    size_baseline = HealthBaseline(
        tenant_id=tenant.id,
        workload_type="exchange",
        metric_name="size_bytes",
        avg_value=50000.0,
        std_dev=5000.0,
        min_value=45000.0,
        max_value=55000.0,
        sample_count=10,
    )
    db.add(size_baseline)

    await db.commit()
    return tenant, obj


# ── Dedup Tests ──


@pytest.mark.asyncio
async def test_dedup_prevents_duplicate_anomaly(db, tenant_with_baselines):
    """Identical anomaly event is not created if one already exists unresolved."""
    tenant, obj = tenant_with_baselines

    # Create an existing unresolved anomaly
    existing = AnomalyEvent(
        tenant_id=tenant.id,
        workload_type="exchange",
        metric_name="item_count",
        expected_value=100.0,
        actual_value=200.0,
        z_score=10.0,
        severity="critical",
        resolved=0,
    )
    db.add(existing)
    await db.commit()

    engine = SmartEngine(db)
    # z_score threshold is 2.0 by default. 200 is 10 std devs from 100.
    result = await engine._check_metric(
        tenant.id, "exchange", "item_count", 200.0, 2.0
    )

    # Should return the anomaly dict (for alerting) but NOT create a new event
    assert result is not None
    assert result["z_score"] > 2.0

    from sqlalchemy import select, func
    count = (await db.execute(
        select(func.count(AnomalyEvent.id)).where(
            AnomalyEvent.tenant_id == tenant.id,
            AnomalyEvent.workload_type == "exchange",
            AnomalyEvent.metric_name == "item_count",
        )
    )).scalar()
    assert count == 1  # Still just the original


@pytest.mark.asyncio
async def test_new_anomaly_created_when_none_exists(db, tenant_with_baselines):
    """New anomaly event is created when no unresolved one exists."""
    tenant, obj = tenant_with_baselines

    engine = SmartEngine(db)
    result = await engine._check_metric(
        tenant.id, "exchange", "item_count", 200.0, 2.0
    )

    assert result is not None

    from sqlalchemy import select, func
    count = (await db.execute(
        select(func.count(AnomalyEvent.id)).where(
            AnomalyEvent.tenant_id == tenant.id,
            AnomalyEvent.metric_name == "item_count",
            AnomalyEvent.resolved == 0,
        )
    )).scalar()
    assert count == 1


# ── Ceiling Tests ──


@pytest.mark.asyncio
async def test_ceiling_prevents_excess_anomalies(db, tenant_with_baselines):
    """No new anomaly created when tenant is at ANOMALY_MAX_PER_TENANT."""
    tenant, obj = tenant_with_baselines

    # Create 10 existing anomalies (at ceiling)
    for i in range(10):
        event = AnomalyEvent(
            tenant_id=tenant.id,
            workload_type=f"workload_{i}",
            metric_name="item_count",
            expected_value=100.0,
            actual_value=200.0,
            z_score=5.0,
            severity="warning",
            resolved=0,
        )
        db.add(event)
    await db.flush()

    engine = SmartEngine(db)
    result = await engine._check_metric(
        tenant.id, "exchange", "size_bytes", 200000.0, 2.0
    )

    # Should return anomaly dict but NOT create a new event
    assert result is not None

    from sqlalchemy import select, func
    count = (await db.execute(
        select(func.count(AnomalyEvent.id)).where(
            AnomalyEvent.tenant_id == tenant.id,
            AnomalyEvent.resolved == 0,
        )
    )).scalar()
    assert count == 10  # Still at ceiling


# ── Auto-Resolve Tests ──


@pytest.mark.asyncio
async def test_auto_resolve_normal_metrics(db, tenant_with_baselines):
    """Anomalies are auto-resolved when their metric returns to normal."""
    tenant, obj = tenant_with_baselines

    # Create an old anomaly for a metric that is now normal
    old_anomaly = AnomalyEvent(
        tenant_id=tenant.id,
        workload_type="exchange",
        metric_name="item_count",
        expected_value=100.0,
        actual_value=200.0,
        z_score=10.0,
        severity="critical",
        resolved=0,
        detected_at=datetime.utcnow() - timedelta(hours=1),
    )
    db.add(old_anomaly)
    await db.commit()

    # Run detection — current snapshot has item_count=100 (normal, within baseline)
    engine = SmartEngine(db)
    anomalies = await engine.detect_anomalies(tenant.id)
    await db.flush()  # Persist auto-resolve changes

    # No new anomalies (data is normal)
    assert len(anomalies) == 0

    # Old anomaly should be auto-resolved
    await db.refresh(old_anomaly)
    assert old_anomaly.resolved == 1


@pytest.mark.asyncio
async def test_auto_resolve_keeps_active_anomalies(db, tenant_with_baselines):
    """Anomalies that are still flagged this cycle are NOT auto-resolved."""
    tenant, obj = tenant_with_baselines

    # Create anomaly for size_bytes — will still be flagged
    existing = AnomalyEvent(
        tenant_id=tenant.id,
        workload_type="exchange",
        metric_name="size_bytes",
        expected_value=50000.0,
        actual_value=200000.0,
        z_score=30.0,
        severity="critical",
        resolved=0,
    )
    db.add(existing)

    # Modify the latest snapshot to have anomalous size
    from sqlalchemy import select
    result = await db.execute(
        select(Snapshot)
        .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
        .where(ProtectedObject.tenant_id == tenant.id)
        .order_by(Snapshot.completed_at.desc()).limit(1)
    )
    latest = result.scalar_one()
    latest.size_bytes = 200000  # 30 std devs above normal
    await db.commit()

    engine = SmartEngine(db)
    anomalies = await engine.detect_anomalies(tenant.id)

    # size_bytes anomaly should still be active
    await db.refresh(existing)
    assert existing.resolved == 0


# ── TTL Cleanup Tests ──


@pytest.mark.asyncio
async def test_ttl_deletes_old_resolved(db):
    """Resolved anomalies older than 90 days are deleted."""
    old_resolved = AnomalyEvent(
        tenant_id=1,
        workload_type="exchange",
        metric_name="item_count",
        expected_value=100, actual_value=200, z_score=5.0,
        resolved=1,
        detected_at=datetime.utcnow() - timedelta(days=100),
    )
    recent_resolved = AnomalyEvent(
        tenant_id=1,
        workload_type="exchange",
        metric_name="size_bytes",
        expected_value=100, actual_value=200, z_score=5.0,
        resolved=1,
        detected_at=datetime.utcnow() - timedelta(days=10),
    )
    db.add_all([old_resolved, recent_resolved])
    await db.commit()

    await cleanup_old_anomalies()

    from sqlalchemy import select
    async with async_session() as check_db:
        result = await check_db.execute(select(AnomalyEvent))
        remaining = result.scalars().all()

    assert len(remaining) == 1
    assert remaining[0].metric_name == "size_bytes"  # Recent one kept


@pytest.mark.asyncio
async def test_ttl_auto_resolves_stale_unresolved(db):
    """Unresolved anomalies older than 30 days are auto-resolved."""
    stale = AnomalyEvent(
        tenant_id=1,
        workload_type="exchange",
        metric_name="item_count",
        expected_value=100, actual_value=200, z_score=5.0,
        resolved=0,
        detected_at=datetime.utcnow() - timedelta(days=35),
    )
    fresh = AnomalyEvent(
        tenant_id=1,
        workload_type="exchange",
        metric_name="size_bytes",
        expected_value=100, actual_value=200, z_score=5.0,
        resolved=0,
        detected_at=datetime.utcnow() - timedelta(days=5),
    )
    db.add_all([stale, fresh])
    await db.commit()

    await cleanup_old_anomalies()

    from sqlalchemy import select
    async with async_session() as check_db:
        result = await check_db.execute(select(AnomalyEvent))
        events = result.scalars().all()

    by_metric = {e.metric_name: e for e in events}
    assert by_metric["item_count"].resolved == 1   # Stale → auto-resolved
    assert by_metric["size_bytes"].resolved == 0    # Fresh → unchanged
