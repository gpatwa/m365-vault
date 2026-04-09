"""Tests for core API endpoints (tenants, SLA, jobs, dashboard, alerts, reports)."""
import pytest
from httpx import AsyncClient


# ── Tenants ──

@pytest.mark.asyncio
async def test_list_tenants(auth_client: AsyncClient):
    response = await auth_client.get("/api/tenants/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── SLA Policies ──

@pytest.mark.asyncio
async def test_create_sla_policy(auth_client: AsyncClient):
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
async def test_create_sla_with_worm(auth_client: AsyncClient):
    response = await auth_client.post("/api/sla-policies/", json={
        "name": "WORM Policy",
        "backup_frequency_hours": 12,
        "retention_days": 365,
        "worm_enabled": 1,
        "legal_hold": 0,
    })
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["worm_enabled"] == 1


# ── Jobs ──

@pytest.mark.asyncio
async def test_list_backup_jobs(auth_client: AsyncClient):
    response = await auth_client.get("/api/jobs/backup")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_failed_items(auth_client: AsyncClient):
    response = await auth_client.get("/api/failed-items")
    assert response.status_code == 200
    assert "total" in response.json()


# ── Dashboard ──

@pytest.mark.asyncio
async def test_dashboard_summary(auth_client: AsyncClient):
    response = await auth_client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_protected" in data
    assert "workloads" in data


# ── Alerts ──

@pytest.mark.asyncio
async def test_alerts_config(auth_client: AsyncClient):
    response = await auth_client.get("/api/alerts/config")
    assert response.status_code == 200
    assert "smtp_configured" in response.json()


# ── Health Score ──

@pytest.mark.asyncio
async def test_health_score(auth_client: AsyncClient, test_tenant):
    response = await auth_client.get(f"/api/health/score?tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "components" in data


# ── Reports ──

@pytest.mark.asyncio
async def test_reports_backup_performance(auth_client: AsyncClient, test_tenant):
    response = await auth_client.get(f"/api/reports/backup-performance?period=7d&tenant_id={test_tenant}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reports_storage(auth_client: AsyncClient, test_tenant):
    response = await auth_client.get(f"/api/reports/storage-analytics?tenant_id={test_tenant}")
    assert response.status_code == 200


# ── Usage & License ──

@pytest.mark.asyncio
async def test_usage_license(auth_client: AsyncClient):
    response = await auth_client.get("/api/usage/license")
    assert response.status_code == 200
    data = response.json()
    assert "tier" in data


@pytest.mark.asyncio
async def test_usage_platform(auth_client: AsyncClient):
    response = await auth_client.get("/api/usage/platform")
    assert response.status_code == 200
    assert "total_tenants" in response.json()


# ── Search ──

@pytest.mark.asyncio
async def test_intent_search(auth_client: AsyncClient, test_tenant):
    response = await auth_client.get(f"/api/search/intent?q=exchange%20backup%20status&tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert "categories" in data or "results" in data


# ── Audit Log ──

@pytest.mark.asyncio
async def test_audit_logs(auth_client: AsyncClient):
    response = await auth_client.get("/api/audit/logs")
    assert response.status_code == 200
    assert "total" in response.json()
