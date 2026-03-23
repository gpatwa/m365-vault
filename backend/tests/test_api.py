"""Tests for core API endpoints (tenants, SLA, jobs, dashboard)."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tenants(auth_client: AsyncClient):
    """Test listing tenants."""
    response = await auth_client.get("/api/tenants/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_sla_policy(auth_client: AsyncClient):
    """Test creating SLA policy."""
    response = await auth_client.post("/api/sla-policies/", json={
        "name": "Test Daily",
        "backup_frequency_hours": 24,
        "retention_days": 30,
    })
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["name"] == "Test Daily"
    assert data["retention_days"] == 30


@pytest.mark.asyncio
async def test_list_backup_jobs(auth_client: AsyncClient):
    """Test listing backup jobs."""
    response = await auth_client.get("/api/jobs/backup")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_dashboard_summary(auth_client: AsyncClient):
    """Test dashboard summary."""
    response = await auth_client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_protected" in data
    assert "workloads" in data


@pytest.mark.asyncio
async def test_failed_items(auth_client: AsyncClient):
    """Test failed items listing."""
    response = await auth_client.get("/api/failed-items")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data


@pytest.mark.asyncio
async def test_audit_logs(auth_client: AsyncClient):
    """Test audit logs listing."""
    response = await auth_client.get("/api/audit/logs")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data


@pytest.mark.asyncio
async def test_alerts_config(auth_client: AsyncClient):
    """Test alerts config."""
    response = await auth_client.get("/api/alerts/config")
    assert response.status_code == 200
    data = response.json()
    assert "smtp_configured" in data


@pytest.mark.asyncio
async def test_sso_config(client: AsyncClient):
    """Test SSO config (public endpoint)."""
    response = await client.get("/api/auth/sso/config")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert data["enabled"] is False  # Disabled in test env
