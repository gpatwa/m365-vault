"""End-to-end tests for MSP multi-tenant dashboard.

Tests the /api/msp/overview endpoint with:
- Empty state (no tenants)
- Single tenant with objects
- Multiple tenants with varying health states
- Health scoring logic (unprotected, failed backups, stale)
- Sorting (worst health first)
- Authentication required
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.backup_job import BackupJob, JobStatus
from app.database import async_session


async def _create_tenant(db, name, status=TenantStatus.ACTIVE, ms_tenant_id=None):
    """Helper: create a tenant."""
    tenant = Tenant(
        name=name,
        ms_tenant_id=ms_tenant_id or f"tid-{name.lower().replace(' ', '-')}",
        client_id="test-client-id",
        client_secret_encrypted="encrypted-secret",
        status=status,
    )
    db.add(tenant)
    await db.flush()
    return tenant


async def _create_objects(db, tenant_id, count=5, workload=WorkloadType.EXCHANGE,
                          status=ProtectionStatus.PROTECTED):
    """Helper: create protected objects."""
    objects = []
    for i in range(count):
        obj = ProtectedObject(
            tenant_id=tenant_id,
            workload_type=workload,
            ms_object_id=f"obj-{tenant_id}-{i}",
            display_name=f"Object {i}",
            status=status,
            last_backup_at=datetime.utcnow() - timedelta(hours=2),
        )
        db.add(obj)
        objects.append(obj)
    await db.flush()
    return objects


async def _create_job(db, tenant_id, status=JobStatus.COMPLETED, hours_ago=1):
    """Helper: create a backup job."""
    now = datetime.utcnow()
    job = BackupJob(
        tenant_id=tenant_id,
        workload_type="exchange",
        status=status,
        started_at=now - timedelta(hours=hours_ago),
        completed_at=now - timedelta(hours=hours_ago - 0.1) if status == JobStatus.COMPLETED else None,
        objects_total=5,
        objects_processed=5 if status == JobStatus.COMPLETED else 0,
        objects_failed=0 if status == JobStatus.COMPLETED else 5,
        created_at=now - timedelta(hours=hours_ago),
    )
    db.add(job)
    await db.flush()
    return job


# ── Auth Tests ──

@pytest.mark.asyncio
async def test_msp_overview_requires_auth(client: AsyncClient):
    """MSP overview returns 401 without auth."""
    response = await client.get("/api/msp/overview")
    assert response.status_code == 401


# ── Empty State ──

@pytest.mark.asyncio
async def test_msp_overview_empty(auth_client: AsyncClient):
    """MSP overview returns empty state when no tenants exist."""
    response = await auth_client.get("/api/msp/overview")
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_tenants"] == 0
    assert data["summary"]["total_protected_users"] == 0
    assert data["summary"]["total_storage_bytes"] == 0
    assert data["summary"]["total_alerts"] == 0
    assert data["tenants"] == []


# ── Single Tenant ──

@pytest.mark.asyncio
async def test_msp_overview_single_tenant(auth_client: AsyncClient):
    """MSP overview returns correct data for a single healthy tenant."""
    async with async_session() as db:
        tenant = await _create_tenant(db, "Acme Corp")
        await _create_objects(db, tenant.id, count=5)
        await _create_job(db, tenant.id, JobStatus.COMPLETED, hours_ago=2)
        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_tenants"] == 1
    assert data["summary"]["total_protected_users"] == 5
    assert len(data["tenants"]) == 1

    tenant_data = data["tenants"][0]
    assert tenant_data["name"] == "Acme Corp"
    assert tenant_data["protected_objects"] == 5
    assert tenant_data["total_objects"] == 5
    assert tenant_data["protection_pct"] == 100
    assert tenant_data["backups_24h"] == 1
    assert tenant_data["failed_24h"] == 0
    assert tenant_data["health_score"] == 100
    assert tenant_data["health_status"] == "healthy"
    assert tenant_data["alert_count"] == 0


# ── Multiple Tenants with Different Health ──

@pytest.mark.asyncio
async def test_msp_overview_multiple_tenants_sorted_by_health(auth_client: AsyncClient):
    """MSP overview returns multiple tenants sorted worst-health-first."""
    async with async_session() as db:
        # Healthy tenant: all protected, recent backup
        t1 = await _create_tenant(db, "Healthy Inc")
        await _create_objects(db, t1.id, count=10)
        await _create_job(db, t1.id, JobStatus.COMPLETED, hours_ago=2)

        # At-risk tenant: some unprotected
        t2 = await _create_tenant(db, "Risky LLC")
        await _create_objects(db, t2.id, count=5, status=ProtectionStatus.PROTECTED)
        await _create_objects(db, t2.id, count=3, status=ProtectionStatus.UNPROTECTED)

        # Critical tenant: failed backups
        t3 = await _create_tenant(db, "Broken Corp")
        await _create_objects(db, t3.id, count=5)
        await _create_job(db, t3.id, JobStatus.FAILED, hours_ago=1)

        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_tenants"] == 3
    tenants = data["tenants"]
    assert len(tenants) == 3

    # Sorted worst first
    assert tenants[0]["health_score"] <= tenants[1]["health_score"]
    assert tenants[1]["health_score"] <= tenants[2]["health_score"]

    # Broken Corp should be worst (failed backups = -30)
    broken = next(t for t in tenants if t["name"] == "Broken Corp")
    assert broken["failed_24h"] == 1
    assert broken["health_score"] < 100
    assert broken["alert_count"] > 0
    assert any("failed" in a for a in broken["alerts"])

    # Healthy Inc should be best
    healthy = next(t for t in tenants if t["name"] == "Healthy Inc")
    assert healthy["health_score"] == 100
    assert healthy["health_status"] == "healthy"
    assert healthy["alert_count"] == 0


# ── Health Score Calculations ──

@pytest.mark.asyncio
async def test_health_score_unprotected_objects(auth_client: AsyncClient):
    """Health drops by 20 when objects are unprotected."""
    async with async_session() as db:
        tenant = await _create_tenant(db, "Partial Corp")
        await _create_objects(db, tenant.id, count=3, status=ProtectionStatus.PROTECTED)
        await _create_objects(db, tenant.id, count=2, status=ProtectionStatus.UNPROTECTED)
        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    data = response.json()

    tenant_data = data["tenants"][0]
    assert tenant_data["protection_pct"] == 60  # 3/5
    assert tenant_data["health_score"] == 80  # 100 - 20 for unprotected
    assert any("unprotected" in a for a in tenant_data["alerts"])


@pytest.mark.asyncio
async def test_health_score_failed_backups(auth_client: AsyncClient):
    """Health drops by 30 when backups fail in last 24h."""
    async with async_session() as db:
        tenant = await _create_tenant(db, "Failing Corp")
        await _create_objects(db, tenant.id, count=5)
        await _create_job(db, tenant.id, JobStatus.FAILED, hours_ago=1)
        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    data = response.json()

    tenant_data = data["tenants"][0]
    assert tenant_data["failed_24h"] == 1
    assert tenant_data["health_score"] == 70  # 100 - 30 for failed
    assert any("failed" in a for a in tenant_data["alerts"])


@pytest.mark.asyncio
async def test_health_score_no_objects(auth_client: AsyncClient):
    """Health is 0 when no objects discovered."""
    async with async_session() as db:
        await _create_tenant(db, "Empty Corp")
        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    data = response.json()

    tenant_data = data["tenants"][0]
    assert tenant_data["total_objects"] == 0
    assert tenant_data["health_score"] == 0
    assert tenant_data["health_status"] == "critical"
    assert any("No objects" in a for a in tenant_data["alerts"])


# ── Summary Aggregation ──

@pytest.mark.asyncio
async def test_msp_summary_aggregation(auth_client: AsyncClient):
    """Summary correctly aggregates across all tenants."""
    async with async_session() as db:
        t1 = await _create_tenant(db, "Tenant A")
        await _create_objects(db, t1.id, count=10)

        t2 = await _create_tenant(db, "Tenant B")
        await _create_objects(db, t2.id, count=15)

        # One inactive tenant
        await _create_tenant(db, "Inactive", status=TenantStatus.INACTIVE)

        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    data = response.json()

    assert data["summary"]["total_tenants"] == 3
    assert data["summary"]["active_tenants"] == 2
    assert data["summary"]["total_protected_users"] == 25  # 10 + 15
    assert data["summary"]["overall_health"] > 0


# ── Workload Count ──

@pytest.mark.asyncio
async def test_msp_overview_workload_count(auth_client: AsyncClient):
    """Tenant shows correct workload count across multiple workloads."""
    async with async_session() as db:
        tenant = await _create_tenant(db, "Multi-WL Corp")
        await _create_objects(db, tenant.id, count=3, workload=WorkloadType.EXCHANGE)
        await _create_objects(db, tenant.id, count=2, workload=WorkloadType.SHAREPOINT)
        await _create_objects(db, tenant.id, count=1, workload=WorkloadType.ENTRA_ID)
        await db.commit()

    response = await auth_client.get("/api/msp/overview")
    data = response.json()

    tenant_data = data["tenants"][0]
    assert tenant_data["total_objects"] == 6
    assert tenant_data["workload_count"] == 3  # exchange, sharepoint, entra_id
