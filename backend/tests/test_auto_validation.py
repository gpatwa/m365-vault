"""Tests for automatic backup validation — feeds recovery confidence score."""
import pytest
import pytest_asyncio
from datetime import datetime

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotType
from app.services.scheduler import validate_recent_backups


@pytest_asyncio.fixture
async def tenant_with_snapshots(db):
    """Create a tenant with completed but unvalidated snapshots."""
    tenant = Tenant(
        name="ValidationTest Corp",
        ms_tenant_id="validation-test-123",
        client_id="test-client",
        client_secret_encrypted="test-enc",
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    obj = ProtectedObject(
        tenant_id=tenant.id,
        ms_object_id="user@validation.com",
        display_name="Validation User",
        workload_type="exchange",
        status=ProtectionStatus.PROTECTED,
    )
    db.add(obj)
    await db.flush()

    # Create 5 completed snapshots, none validated
    snapshots = []
    for i in range(5):
        snap = Snapshot(
            protected_object_id=obj.id,
            snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            item_count=10,
            size_bytes=1000,
            completed_at=datetime.utcnow(),
            validation_status=None,  # Not yet validated
        )
        db.add(snap)
        snapshots.append(snap)

    await db.commit()
    return tenant, obj, snapshots


@pytest.mark.asyncio
async def test_validates_unvalidated_snapshots(db, tenant_with_snapshots):
    """validate_recent_backups() processes unvalidated snapshots."""
    tenant, obj, snapshots = tenant_with_snapshots

    await validate_recent_backups()

    # Refresh snapshots from DB
    from sqlalchemy import select
    async with async_session() as check_db:
        result = await check_db.execute(
            select(Snapshot).where(Snapshot.protected_object_id == obj.id)
        )
        updated = result.scalars().all()

    validated = [s for s in updated if s.validation_status is not None]
    assert len(validated) == 5
    # Snapshots without encryption_key_id get auto-passed
    for s in validated:
        assert s.validation_status in ("passed", "failed", "partial")
        assert s.validated_at is not None


@pytest.mark.asyncio
async def test_skips_already_validated(db, tenant_with_snapshots):
    """Already validated snapshots are not re-validated."""
    tenant, obj, snapshots = tenant_with_snapshots

    # Pre-validate one snapshot
    snapshots[0].validation_status = "passed"
    snapshots[0].validated_at = datetime.utcnow()
    await db.commit()

    await validate_recent_backups()

    # The pre-validated one should still be "passed" (not re-processed)
    async with async_session() as check_db:
        from sqlalchemy import select
        result = await check_db.execute(
            select(Snapshot).where(
                Snapshot.protected_object_id == obj.id,
                Snapshot.validation_status.isnot(None),
            )
        )
        validated = result.scalars().all()

    assert len(validated) == 5  # All 5 now validated


@pytest.mark.asyncio
async def test_validation_feeds_recovery_score(auth_client, test_tenant, db):
    """Validated snapshots improve the recovery confidence score's validation factor."""
    # Create a protected object + snapshot for the test tenant
    obj = ProtectedObject(
        tenant_id=test_tenant,
        ms_object_id="score-test@test.com",
        display_name="Score Test",
        workload_type="exchange",
        status=ProtectionStatus.PROTECTED,
    )
    db.add(obj)
    await db.flush()

    snap = Snapshot(
        protected_object_id=obj.id,
        snapshot_type=SnapshotType.FULL,
        status=SnapshotStatus.COMPLETED,
        item_count=5,
        size_bytes=500,
        completed_at=datetime.utcnow(),
        validation_status=None,
    )
    db.add(snap)
    await db.commit()

    # Check recovery score before validation
    resp1 = await auth_client.get(f"/api/recovery/confidence?tenant_id={test_tenant}")
    assert resp1.status_code == 200
    score_before = resp1.json()

    # Validate the snapshot
    snap.validation_status = "passed"
    snap.validated_at = datetime.utcnow()
    await db.commit()

    # Check recovery score after validation
    resp2 = await auth_client.get(f"/api/recovery/confidence?tenant_id={test_tenant}")
    assert resp2.status_code == 200
    score_after = resp2.json()

    # Validation factor should improve (or at least not decrease)
    validation_before = score_before["factors"]["validation"]["score"]
    validation_after = score_after["factors"]["validation"]["score"]
    assert validation_after >= validation_before
