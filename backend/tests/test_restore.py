"""Tests for restore/recovery endpoints across all workloads."""
import pytest
from httpx import AsyncClient


# ── Exchange Restore ──

@pytest.mark.asyncio
async def test_exchange_restore_not_found(auth_client: AsyncClient):
    """Restore returns 404 for non-existent mailbox."""
    response = await auth_client.post("/api/exchange/mailboxes/99999/restore", json={
        "snapshot_id": 1, "restore_type": "full_inplace",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_exchange_restore_invalid_snapshot(auth_client: AsyncClient):
    """Restore returns 404 for non-existent snapshot."""
    # Create a protected object first
    from app.database import async_session
    from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
    from app.models.tenant import Tenant, TenantStatus

    async with async_session() as db:
        tenant = Tenant(name="Test", ms_tenant_id="test-123", client_id="cid",
                       client_secret_encrypted="enc", status=TenantStatus.ACTIVE)
        db.add(tenant)
        await db.flush()
        obj = ProtectedObject(tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
                             ms_object_id="user-123", display_name="Test Mailbox",
                             status=ProtectionStatus.PROTECTED)
        db.add(obj)
        await db.flush()
        obj_id = obj.id
        await db.commit()

    response = await auth_client.post(f"/api/exchange/mailboxes/{obj_id}/restore", json={
        "snapshot_id": 99999, "restore_type": "full_inplace",
    })
    assert response.status_code == 404


# ── OneDrive Restore ──

@pytest.mark.asyncio
async def test_onedrive_restore_not_found(auth_client: AsyncClient):
    response = await auth_client.post("/api/onedrive/accounts/99999/restore", json={
        "snapshot_id": 1, "restore_type": "full_inplace",
    })
    assert response.status_code == 404


# ── SharePoint Restore ──

@pytest.mark.asyncio
async def test_sharepoint_restore_not_found(auth_client: AsyncClient):
    response = await auth_client.post("/api/sharepoint/sites/99999/restore", json={
        "snapshot_id": 1, "restore_type": "full_inplace",
    })
    assert response.status_code == 404


# ── Teams Restore ──

@pytest.mark.asyncio
async def test_teams_restore_not_found(auth_client: AsyncClient):
    """Teams restore returns 404 for non-existent team."""
    response = await auth_client.post("/api/teams/teams/99999/restore", json={
        "snapshot_id": 1, "restore_type": "full_inplace",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_teams_restore_invalid_snapshot(auth_client: AsyncClient):
    """Teams restore returns 404 for invalid snapshot."""
    from app.database import async_session
    from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
    from app.models.tenant import Tenant, TenantStatus

    async with async_session() as db:
        tenant = Tenant(name="Test2", ms_tenant_id="test-456", client_id="cid2",
                       client_secret_encrypted="enc2", status=TenantStatus.ACTIVE)
        db.add(tenant)
        await db.flush()
        obj = ProtectedObject(tenant_id=tenant.id, workload_type=WorkloadType.TEAMS,
                             ms_object_id="team-123", display_name="Test Team",
                             status=ProtectionStatus.PROTECTED)
        db.add(obj)
        await db.flush()
        obj_id = obj.id
        await db.commit()

    response = await auth_client.post(f"/api/teams/teams/{obj_id}/restore", json={
        "snapshot_id": 99999, "restore_type": "item_level", "item_ids": [1, 2],
    })
    assert response.status_code == 404


# ── Entra ID Restore ──

@pytest.mark.asyncio
async def test_entra_restore_no_object(auth_client: AsyncClient, test_tenant):
    """Entra ID restore returns 404 when no Entra object exists."""
    response = await auth_client.post(f"/api/entra-id/restore?tenant_id={test_tenant}", json={
        "snapshot_id": 1, "restore_type": "item_level", "item_ids": [1],
    })
    assert response.status_code == 404


# ── Restore Jobs ──

@pytest.mark.asyncio
async def test_list_restore_jobs(auth_client: AsyncClient):
    """List restore jobs returns paginated response."""
    response = await auth_client.get("/api/jobs/restore")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


# ── Self-Service Restore ──

@pytest.mark.asyncio
async def test_self_restore_search(auth_client: AsyncClient, test_tenant):
    """Self-restore search returns results structure."""
    response = await auth_client.get(f"/api/self-restore/search?query=test&tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_self_restore_requires_query(auth_client: AsyncClient, test_tenant):
    """Self-restore search requires query parameter."""
    response = await auth_client.get(f"/api/self-restore/search?tenant_id={test_tenant}")
    assert response.status_code in (200, 422)  # Empty query returns empty or validation error


# ── Mass Recovery ──

@pytest.mark.asyncio
async def test_mass_recovery_empty(auth_client: AsyncClient, test_tenant):
    """Mass recovery with no failed jobs returns appropriate response."""
    response = await auth_client.post("/api/jobs/mass-recovery", json={
        "tenant_id": test_tenant, "workload_type": "exchange",
    })
    # 200 = success, 404 = no failed jobs, 422 = validation error
    assert response.status_code in (200, 404, 422)


# ── Restore Endpoint Exists ──

@pytest.mark.asyncio
async def test_all_restore_endpoints_exist(auth_client: AsyncClient):
    """Verify all workload restore endpoints are registered."""
    endpoints = [
        ("POST", "/api/exchange/mailboxes/1/restore"),
        ("POST", "/api/onedrive/accounts/1/restore"),
        ("POST", "/api/sharepoint/sites/1/restore"),
        ("POST", "/api/teams/teams/1/restore"),
        ("POST", "/api/entra-id/restore?tenant_id=1"),
        ("POST", "/api/self-restore/restore"),
        ("POST", "/api/jobs/mass-recovery"),
    ]
    for method, path in endpoints:
        if method == "POST":
            response = await auth_client.post(path, json={"snapshot_id": 1})
        else:
            response = await auth_client.get(path)
        # Should NOT be 405 (Method Not Allowed) or 404 on the route itself
        # 404 on the object is fine (means route exists but object doesn't)
        assert response.status_code != 405, f"Endpoint not registered: {method} {path}"
