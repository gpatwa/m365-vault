"""Tests for batch scheduler — parent-child job decomposition."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.database import async_session
from app.models.backup_job import BackupJob, JobStatus
from app.models.tenant import Tenant, TenantStatus
from app.models.sla_policy import SLAPolicy
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.services.scheduler import check_and_schedule_backups, aggregate_parent_jobs


@pytest_asyncio.fixture
async def tenant_with_objects(db):
    """Create a tenant with SLA policy and protected objects."""
    tenant = Tenant(
        name="BatchTest Corp",
        ms_tenant_id="batch-test-123",
        client_id="test-client-id",
        client_secret_encrypted="test-secret-enc",
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    sla = SLAPolicy(
        name="Hourly",
        backup_frequency_hours=1,
        retention_days=30,
        is_active=1,
    )
    db.add(sla)
    await db.flush()

    return tenant, sla


async def _create_objects(db, tenant, sla, count, workload="exchange"):
    """Helper to create N protected objects."""
    for i in range(count):
        obj = ProtectedObject(
            tenant_id=tenant.id,
            ms_object_id=f"user-{i}@test.com",
            display_name=f"User {i}",
            workload_type=workload,
            status=ProtectionStatus.PROTECTED,
            sla_policy_id=sla.id,
        )
        db.add(obj)
    await db.flush()
    await db.commit()


# ── Model Tests ──


@pytest.mark.asyncio
async def test_backup_job_has_batch_columns(db):
    """BackupJob model includes parent_job_id, batch_offset, batch_size."""
    job = BackupJob(
        tenant_id=1,
        workload_type="exchange",
        status=JobStatus.QUEUED,
        objects_total=100,
        parent_job_id=None,
        batch_offset=0,
        batch_size=50,
    )
    db.add(job)
    await db.flush()
    assert job.id is not None
    assert job.batch_offset == 0
    assert job.batch_size == 50
    assert job.parent_job_id is None


@pytest.mark.asyncio
async def test_parent_child_relationship(db):
    """Child jobs reference parent via parent_job_id."""
    parent = BackupJob(
        tenant_id=1,
        workload_type="exchange",
        status=JobStatus.IN_PROGRESS,
        objects_total=1000,
    )
    db.add(parent)
    await db.flush()

    child = BackupJob(
        tenant_id=1,
        workload_type="exchange",
        status=JobStatus.QUEUED,
        objects_total=500,
        parent_job_id=parent.id,
        batch_offset=0,
        batch_size=500,
    )
    db.add(child)
    await db.flush()

    assert child.parent_job_id == parent.id


# ── Scheduler Batch Creation Tests ──


@pytest.mark.asyncio
async def test_small_workload_creates_single_job(db, tenant_with_objects):
    """Workload with <= BATCH_THRESHOLD objects creates a single job (no batching)."""
    tenant, sla = tenant_with_objects
    await _create_objects(db, tenant, sla, count=50)

    with patch("app.services.scheduler.settings") as mock_settings:
        mock_settings.BATCH_THRESHOLD = 500
        mock_settings.BATCH_SIZE = 500
        mock_settings.SCHEDULER_CHECK_INTERVAL_SECONDS = 60
        with patch("app.services.scheduler.execute_queued_jobs", new_callable=AsyncMock):
            await check_and_schedule_backups()

    async with async_session() as check_db:
        from sqlalchemy import select
        result = await check_db.execute(select(BackupJob))
        jobs = result.scalars().all()

    # Should create a single job with no parent/batch fields
    queued = [j for j in jobs if j.status == JobStatus.QUEUED]
    assert len(queued) == 1
    assert queued[0].parent_job_id is None
    assert queued[0].batch_offset is None
    assert queued[0].objects_total == 50


@pytest.mark.asyncio
async def test_large_workload_creates_parent_and_children(db, tenant_with_objects):
    """Workload with > BATCH_THRESHOLD objects creates parent + child batch jobs."""
    tenant, sla = tenant_with_objects
    await _create_objects(db, tenant, sla, count=1200)

    with patch("app.services.scheduler.settings") as mock_settings:
        mock_settings.BATCH_THRESHOLD = 500
        mock_settings.BATCH_SIZE = 500
        mock_settings.SCHEDULER_CHECK_INTERVAL_SECONDS = 60
        with patch("app.services.scheduler.execute_queued_jobs", new_callable=AsyncMock):
            await check_and_schedule_backups()

    async with async_session() as check_db:
        from sqlalchemy import select
        result = await check_db.execute(select(BackupJob))
        jobs = result.scalars().all()

    parents = [j for j in jobs if j.parent_job_id is None and j.status == JobStatus.IN_PROGRESS]
    children = [j for j in jobs if j.parent_job_id is not None]

    assert len(parents) == 1
    assert parents[0].objects_total == 1200

    # 1200 / 500 = 3 batches (0-500, 500-1000, 1000-1200)
    assert len(children) == 3
    assert all(c.status == JobStatus.QUEUED for c in children)

    offsets = sorted(c.batch_offset for c in children)
    assert offsets == [0, 500, 1000]

    sizes = sorted(c.batch_size for c in children)
    assert sizes == [200, 500, 500]


@pytest.mark.asyncio
async def test_dedup_skips_existing_queued_job(db, tenant_with_objects):
    """Scheduler skips creating jobs when QUEUED/IN_PROGRESS job already exists."""
    tenant, sla = tenant_with_objects
    await _create_objects(db, tenant, sla, count=50)

    # Pre-create a queued job
    existing = BackupJob(
        tenant_id=tenant.id,
        workload_type="exchange",
        status=JobStatus.QUEUED,
        objects_total=50,
    )
    db.add(existing)
    await db.commit()

    with patch("app.services.scheduler.settings") as mock_settings:
        mock_settings.BATCH_THRESHOLD = 500
        mock_settings.BATCH_SIZE = 500
        mock_settings.SCHEDULER_CHECK_INTERVAL_SECONDS = 60
        with patch("app.services.scheduler.execute_queued_jobs", new_callable=AsyncMock):
            await check_and_schedule_backups()

    async with async_session() as check_db:
        from sqlalchemy import select
        result = await check_db.execute(select(BackupJob))
        jobs = result.scalars().all()

    # Should still be just the original job
    assert len(jobs) == 1


# ── Parent Aggregation Tests ──


@pytest.mark.asyncio
async def test_aggregate_all_children_completed(db):
    """Parent status = COMPLETED when all children succeed."""
    parent = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.IN_PROGRESS, objects_total=1000,
    )
    db.add(parent)
    await db.flush()

    for i in range(2):
        child = BackupJob(
            tenant_id=1, workload_type="exchange",
            status=JobStatus.COMPLETED,
            parent_job_id=parent.id,
            batch_offset=i * 500, batch_size=500,
            objects_total=500, objects_processed=500,
            objects_failed=0, total_size_bytes=1000000,
            completed_at=datetime.utcnow(),
        )
        db.add(child)
    await db.commit()

    await aggregate_parent_jobs()

    async with async_session() as check_db:
        updated = await check_db.get(BackupJob, parent.id)
        assert updated.status == JobStatus.COMPLETED
        assert updated.objects_processed == 1000
        assert updated.total_size_bytes == 2000000
        assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_aggregate_mixed_children_partial(db):
    """Parent status = PARTIAL when some children fail."""
    parent = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.IN_PROGRESS, objects_total=1000,
    )
    db.add(parent)
    await db.flush()

    child1 = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.COMPLETED,
        parent_job_id=parent.id,
        batch_offset=0, batch_size=500,
        objects_total=500, objects_processed=500,
        completed_at=datetime.utcnow(),
    )
    child2 = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.FAILED,
        parent_job_id=parent.id,
        batch_offset=500, batch_size=500,
        objects_total=500, objects_processed=100, objects_failed=400,
        completed_at=datetime.utcnow(),
    )
    db.add_all([child1, child2])
    await db.commit()

    await aggregate_parent_jobs()

    async with async_session() as check_db:
        updated = await check_db.get(BackupJob, parent.id)
        assert updated.status == JobStatus.PARTIAL
        assert updated.objects_processed == 600
        assert updated.objects_failed == 400


@pytest.mark.asyncio
async def test_aggregate_all_children_failed(db):
    """Parent status = FAILED when all children fail."""
    parent = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.IN_PROGRESS, objects_total=500,
    )
    db.add(parent)
    await db.flush()

    child = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.FAILED,
        parent_job_id=parent.id,
        batch_offset=0, batch_size=500,
        objects_total=500, objects_failed=500,
        completed_at=datetime.utcnow(),
    )
    db.add(child)
    await db.commit()

    await aggregate_parent_jobs()

    async with async_session() as check_db:
        updated = await check_db.get(BackupJob, parent.id)
        assert updated.status == JobStatus.FAILED


@pytest.mark.asyncio
async def test_aggregate_skips_incomplete_children(db):
    """Parent stays IN_PROGRESS while children are still running."""
    parent = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.IN_PROGRESS, objects_total=1000,
    )
    db.add(parent)
    await db.flush()

    child1 = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.COMPLETED,
        parent_job_id=parent.id,
        batch_offset=0, batch_size=500,
        completed_at=datetime.utcnow(),
    )
    child2 = BackupJob(
        tenant_id=1, workload_type="exchange",
        status=JobStatus.IN_PROGRESS,  # Still running
        parent_job_id=parent.id,
        batch_offset=500, batch_size=500,
    )
    db.add_all([child1, child2])
    await db.commit()

    await aggregate_parent_jobs()

    async with async_session() as check_db:
        updated = await check_db.get(BackupJob, parent.id)
        assert updated.status == JobStatus.IN_PROGRESS  # Unchanged
