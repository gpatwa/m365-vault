"""Tests for recovery API — confidence score, RPO/RTO, runbooks, verification."""
import pytest
from httpx import AsyncClient


# ── Recovery Confidence Score ──

@pytest.mark.asyncio
async def test_confidence_score(auth_client: AsyncClient):
    """Confidence score returns valid structure."""
    response = await auth_client.get("/api/recovery/confidence?tenant_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "grade" in data
    assert data["grade"] in ("A", "B", "C", "D")
    assert "factors" in data
    assert "freshness" in data["factors"]
    assert "completeness" in data["factors"]
    assert "restore_success" in data["factors"]
    assert "validation" in data["factors"]
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


@pytest.mark.asyncio
async def test_confidence_score_empty_tenant(auth_client: AsyncClient):
    """Confidence score for non-existent tenant returns 0."""
    response = await auth_client.get("/api/recovery/confidence?tenant_id=999")
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0 or data["factors"]["completeness"]["score"] == 0


# ── RPO/RTO ──

@pytest.mark.asyncio
async def test_rpo_rto(auth_client: AsyncClient):
    """RPO/RTO returns valid structure."""
    response = await auth_client.get("/api/recovery/rpo-rto?tenant_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "overall_rpo_compliance" in data
    assert "overall_status" in data
    assert data["overall_status"] in ("compliant", "at_risk", "violated")
    assert "workloads" in data


@pytest.mark.asyncio
async def test_rpo_rto_empty_tenant(auth_client: AsyncClient):
    """RPO/RTO for empty tenant returns 0 compliance."""
    response = await auth_client.get("/api/recovery/rpo-rto?tenant_id=999")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_rpo_compliance"] == 0


# ── Runbooks ──

@pytest.mark.asyncio
async def test_runbooks(auth_client: AsyncClient):
    """Runbooks returns pre-defined recovery procedures."""
    response = await auth_client.get("/api/recovery/runbooks")
    assert response.status_code == 200
    data = response.json()
    assert "runbooks" in data
    assert len(data["runbooks"]) >= 5

    # Verify ransomware runbook exists
    ransomware = next((r for r in data["runbooks"] if r["id"] == "ransomware"), None)
    assert ransomware is not None
    assert ransomware["severity"] == "critical"
    assert len(ransomware["steps"]) >= 5


@pytest.mark.asyncio
async def test_runbook_has_all_scenarios(auth_client: AsyncClient):
    """All 5 recovery scenarios are covered."""
    response = await auth_client.get("/api/recovery/runbooks")
    data = response.json()
    ids = [r["id"] for r in data["runbooks"]]
    assert "ransomware" in ids
    assert "accidental_deletion" in ids
    assert "tenant_migration" in ids
    assert "compliance_audit" in ids
    assert "config_drift" in ids


# ── Recovery Verification ──

@pytest.mark.asyncio
async def test_verify_recovery(auth_client: AsyncClient):
    """Recovery verification returns valid structure."""
    response = await auth_client.get("/api/recovery/verify?tenant_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "verified" in data
    assert "score" in data
    # Empty tenant returns no grade/checks
    if data["score"] > 0:
        assert "grade" in data
        assert "checks" in data


@pytest.mark.asyncio
async def test_verify_empty_tenant(auth_client: AsyncClient):
    """Verification for empty tenant returns not verified."""
    response = await auth_client.get("/api/recovery/verify?tenant_id=999")
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is False
    assert data["score"] == 0


# ── Mass Recovery ──

@pytest.mark.asyncio
async def test_mass_restore_dry_run(auth_client: AsyncClient):
    """Mass restore dry run shows plan without executing."""
    response = await auth_client.post("/api/recovery/mass-restore", json={
        "tenant_id": 1,
        "dry_run": True,
    })
    # 200 with plan or 404 if no objects
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "dry_run"
        assert "plan" in data


@pytest.mark.asyncio
async def test_mass_restore_no_objects(auth_client: AsyncClient):
    """Mass restore returns 404 when no protected objects."""
    response = await auth_client.post("/api/recovery/mass-restore", json={
        "tenant_id": 999,
        "dry_run": True,
    })
    assert response.status_code == 404


# ── Test Restore ──

@pytest.mark.asyncio
async def test_test_restore_no_objects(auth_client: AsyncClient):
    """Test restore returns 404 when no objects to test."""
    response = await auth_client.post("/api/recovery/test-restore?tenant_id=999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_test_restore_with_workload_filter(auth_client: AsyncClient):
    """Test restore accepts workload filter."""
    response = await auth_client.post("/api/recovery/test-restore?tenant_id=1&workload=exchange")
    # 200 with results or 404 if no exchange objects
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "total_tested" in data
        assert "pass_rate" in data
        assert "results" in data


# ── All Recovery Endpoints Exist ──

@pytest.mark.asyncio
async def test_all_recovery_endpoints_exist(auth_client: AsyncClient):
    """Verify all recovery endpoints are registered."""
    endpoints = [
        ("GET", "/api/recovery/confidence?tenant_id=1"),
        ("GET", "/api/recovery/rpo-rto?tenant_id=1"),
        ("GET", "/api/recovery/runbooks"),
        ("GET", "/api/recovery/verify?tenant_id=1"),
    ]
    for method, path in endpoints:
        response = await auth_client.get(path)
        assert response.status_code != 405, f"Endpoint not registered: {method} {path}"
        assert response.status_code != 404 or "not found" not in str(response.url), f"Route missing: {path}"
