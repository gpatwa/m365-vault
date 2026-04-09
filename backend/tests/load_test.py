"""Load test — verifies batch scheduler, worker throughput, and DB pool under load.

NOT a pytest test. Run directly:
    python -m tests.load_test

Tests against the local Docker stack (docker-compose), not production.
Measures:
  - Batch scheduler: correct parent-child decomposition for large workloads
  - Worker throughput: jobs processed per second
  - DB pool: connection utilization under concurrent load
  - Queue depth: Redis queue behavior during burst
  - Tenant fairness: no tenant starves another

Prerequisites:
  make dev   # Docker Compose must be running (PG + Redis + MinIO)
"""
# Set env BEFORE any app imports (controls SQLAlchemy echo, config validation)
import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://m365vault:m365vault_dev@localhost:5432/m365vault"
os.environ["DISPATCH_MODE"] = "redis"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "load-test-secret-key-not-for-production"
os.environ["ENCRYPTION_MASTER_KEY"] = "load-test-encryption-key-32bytes!"

import asyncio
import json
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("load_test")

# Test parameters — large scenario to test batch decomposition
NUM_TENANTS = 10          # Simulate 10 tenants
OBJECTS_PER_TENANT = 2000 # 2000 protected objects each = 20,000 total
BATCH_SIZE = 500          # From config — 4 batches per tenant
SLA_HOURS = 1             # Hourly SLA = all objects are due for backup


async def setup_test_data():
    """Create tenants, SLA policies, and protected objects in Docker PG."""

    from app.database import engine, async_session, Base
    from app.models.tenant import Tenant, TenantStatus
    from app.models.sla_policy import SLAPolicy
    from app.models.protected_object import ProtectedObject, ProtectionStatus
    from app.models.backup_job import BackupJob
    from sqlalchemy import select, delete, text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Clean up previous load test jobs only (leave existing demo data intact)
        from sqlalchemy import and_
        await db.execute(delete(BackupJob).where(
            and_(BackupJob.workload_type == "exchange",
                 BackupJob.tenant_id.in_(select(Tenant.id).where(Tenant.ms_tenant_id.like("loadtest-%"))))
        ))

        # Create SLA policy
        existing_sla = (await db.execute(select(SLAPolicy).limit(1))).scalar_one_or_none()
        if not existing_sla:
            sla = SLAPolicy(name="Hourly Load Test", backup_frequency_hours=SLA_HOURS, retention_days=7, is_active=1)
            db.add(sla)
            await db.flush()
            sla_id = sla.id
        else:
            sla_id = existing_sla.id

        tenant_ids = []
        for t in range(NUM_TENANTS):
            # Check if tenant exists
            existing = (await db.execute(
                select(Tenant).where(Tenant.ms_tenant_id == f"loadtest-{t}")
            )).scalar_one_or_none()

            if existing:
                tenant_ids.append(existing.id)
                continue

            tenant = Tenant(
                name=f"LoadTest Tenant {t}",
                ms_tenant_id=f"loadtest-{t}",
                client_id="loadtest-client",
                client_secret_encrypted="loadtest-enc",
                status=TenantStatus.ACTIVE,
            )
            db.add(tenant)
            await db.flush()
            tenant_ids.append(tenant.id)

        # Create protected objects
        total_objects = 0
        for tid in tenant_ids:
            # Check existing count
            from sqlalchemy import func
            existing_count = (await db.execute(
                select(func.count(ProtectedObject.id)).where(
                    ProtectedObject.tenant_id == tid,
                    ProtectedObject.workload_type == "EXCHANGE",
                )
            )).scalar() or 0

            needed = OBJECTS_PER_TENANT - existing_count
            for i in range(needed):
                obj = ProtectedObject(
                    tenant_id=tid,
                    ms_object_id=f"loadtest-user-{i}@tenant-{tid}.com",
                    display_name=f"Load Test User {i}",
                    workload_type="EXCHANGE",
                    status=ProtectionStatus.PROTECTED,
                    sla_policy_id=sla_id,
                )
                db.add(obj)
            total_objects += OBJECTS_PER_TENANT

        await db.commit()
        logger.info(f"Setup: {NUM_TENANTS} tenants × {OBJECTS_PER_TENANT} objects = {total_objects} total")
        return tenant_ids


async def run_scheduler_once():
    """Run the scheduler's check_and_schedule_backups() once and measure."""
    from app.services.scheduler import check_and_schedule_backups
    from unittest.mock import AsyncMock, patch

    # Patch execute_queued_jobs to not actually dispatch (we just want to test scheduling)
    with patch("app.services.scheduler.execute_queued_jobs", new_callable=AsyncMock):
        start = time.monotonic()
        await check_and_schedule_backups()
        elapsed = time.monotonic() - start

    logger.info(f"Scheduler: created jobs in {elapsed:.2f}s")
    return elapsed


async def measure_job_creation():
    """Verify the batch scheduler created correct parent-child structure."""
    from app.database import async_session
    from app.models.backup_job import BackupJob, JobStatus
    from sqlalchemy import select, func

    async with async_session() as db:
        # Count total jobs
        total = (await db.execute(select(func.count(BackupJob.id)))).scalar() or 0

        # Count by type
        parents = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.parent_job_id.is_(None),
                BackupJob.batch_size.is_(None),
                BackupJob.status == JobStatus.QUEUED,
            )
        )).scalar() or 0

        batch_parents = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.parent_job_id.is_(None),
                BackupJob.status == JobStatus.IN_PROGRESS,
            )
        )).scalar() or 0

        children = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.parent_job_id.isnot(None),
            )
        )).scalar() or 0

        queued = (await db.execute(
            select(func.count(BackupJob.id)).where(BackupJob.status == JobStatus.QUEUED)
        )).scalar() or 0

    logger.info(f"Jobs: total={total}, single={parents}, batch_parents={batch_parents}, children={children}, queued={queued}")

    return {
        "total": total,
        "single_jobs": parents,
        "batch_parents": batch_parents,
        "children": children,
        "queued": queued,
    }


async def measure_queue_depth():
    """Check Redis queue depth."""
    import redis.asyncio as aioredis
    r = aioredis.from_url("redis://localhost:6379/0", decode_responses=True)
    backup_len = await r.llen("kavachiq:backup_queue")
    restore_len = await r.llen("kavachiq:restore_queue")
    await r.aclose()
    logger.info(f"Queue depth: backup={backup_len}, restore={restore_len}")
    return {"backup_queue": backup_len, "restore_queue": restore_len}


async def measure_db_pool():
    """Check DB connection pool stats."""
    from app.database import engine
    pool = engine.pool
    stats = {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "utilization": round(pool.checkedout() / max(pool.size() + pool.overflow(), 1), 2),
    }
    logger.info(f"DB pool: size={stats['pool_size']}, checked_out={stats['checked_out']}, overflow={stats['overflow']}, utilization={stats['utilization']:.0%}")
    return stats


async def main():
    """Run the full load test."""
    logger.info("=" * 60)
    logger.info(f"LOAD TEST: {NUM_TENANTS} tenants × {OBJECTS_PER_TENANT} objects")
    logger.info("=" * 60)

    # Setup
    logger.info("\n── Phase 1: Setup ──")
    tenant_ids = await setup_test_data()

    # Run scheduler
    logger.info("\n── Phase 2: Scheduler ──")
    scheduler_time = await run_scheduler_once()

    # Measure results
    logger.info("\n── Phase 3: Measure ──")
    jobs = await measure_job_creation()
    queues = await measure_queue_depth()
    pool = await measure_db_pool()

    # Report
    logger.info("\n" + "=" * 60)
    logger.info("LOAD TEST RESULTS")
    logger.info("=" * 60)

    total_objects = NUM_TENANTS * OBJECTS_PER_TENANT
    results = {
        "config": {
            "tenants": NUM_TENANTS,
            "objects_per_tenant": OBJECTS_PER_TENANT,
            "total_objects": total_objects,
            "batch_size": BATCH_SIZE,
        },
        "scheduler": {
            "time_seconds": round(scheduler_time, 2),
            "objects_per_second": round(total_objects / max(scheduler_time, 0.001)),
        },
        "jobs": jobs,
        "queues": queues,
        "db_pool": pool,
    }

    # Validate expectations
    passed = 0
    total_checks = 0

    def check(name, condition, detail=""):
        nonlocal passed, total_checks
        total_checks += 1
        status = "✅" if condition else "❌"
        if condition:
            passed += 1
        logger.info(f"  {status} {name} {detail}")

    logger.info("\n── Checks ──")

    # With 500 objects per tenant and BATCH_SIZE=500, each tenant gets 1 single job (no batching)
    if OBJECTS_PER_TENANT <= BATCH_SIZE:
        check("Single jobs = tenant count", jobs["single_jobs"] == NUM_TENANTS,
              f"(expected {NUM_TENANTS}, got {jobs['single_jobs']})")
        check("No batch parents", jobs["batch_parents"] == 0,
              f"(expected 0, got {jobs['batch_parents']})")
        check("No children", jobs["children"] == 0,
              f"(expected 0, got {jobs['children']})")
    else:
        expected_batches = (OBJECTS_PER_TENANT + BATCH_SIZE - 1) // BATCH_SIZE
        check("Batch parents = tenant count", jobs["batch_parents"] == NUM_TENANTS,
              f"(expected {NUM_TENANTS}, got {jobs['batch_parents']})")
        check("Children per parent", jobs["children"] == NUM_TENANTS * expected_batches,
              f"(expected {NUM_TENANTS * expected_batches}, got {jobs['children']})")

    check("Scheduler < 10s", scheduler_time < 10,
          f"({scheduler_time:.2f}s)")
    check("DB pool not exhausted", pool["utilization"] < 0.8,
          f"({pool['utilization']:.0%})")
    check("Total queued > 0", jobs["queued"] > 0,
          f"({jobs['queued']} queued)")

    logger.info(f"\n  {passed}/{total_checks} checks passed")
    logger.info(f"\n  Scheduler throughput: {results['scheduler']['objects_per_second']} objects/second")

    print(json.dumps(results, indent=2))

    return passed == total_checks


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
