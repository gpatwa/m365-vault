"""Tests for P0-P2 production readiness features.

Covers:
  P0: WORM enforcement, tenant filter coverage
  P1: Audit export, user invites, backup alerts
  P2: Password change, Prometheus metrics
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════
# P0: WORM Enforcement
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_worm_blocks_deletion():
    """WORM-locked snapshot cannot be deleted."""
    from app.services.storage import StorageService

    class MockSnapshot:
        locked_until = datetime.utcnow() + timedelta(days=30)

    class MockSLA:
        legal_hold = 0

    can_delete, reason = StorageService.can_delete_snapshot(MockSnapshot(), MockSLA())
    assert can_delete is False
    assert "WORM lock active" in reason


@pytest.mark.asyncio
async def test_legal_hold_blocks_deletion():
    """Legal hold prevents snapshot deletion."""
    from app.services.storage import StorageService

    class MockSnapshot:
        locked_until = None

    class MockSLA:
        legal_hold = 1

    can_delete, reason = StorageService.can_delete_snapshot(MockSnapshot(), MockSLA())
    assert can_delete is False
    assert "legal hold" in reason


@pytest.mark.asyncio
async def test_unlocked_snapshot_can_be_deleted():
    """Snapshot without WORM or legal hold can be deleted."""
    from app.services.storage import StorageService

    class MockSnapshot:
        locked_until = None

    can_delete, reason = StorageService.can_delete_snapshot(MockSnapshot(), None)
    assert can_delete is True


@pytest.mark.asyncio
async def test_expired_worm_allows_deletion():
    """Expired WORM lock allows deletion."""
    from app.services.storage import StorageService

    class MockSnapshot:
        locked_until = datetime.utcnow() - timedelta(days=1)

    can_delete, reason = StorageService.can_delete_snapshot(MockSnapshot(), None)
    assert can_delete is True


# ═══════════════════════════════════════════════════════
# P1: Audit Log Export
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_export_csv(auth_client: AsyncClient):
    """Audit log CSV export returns downloadable file."""
    resp = await auth_client.get("/api/audit/export?format=csv&days=7")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_audit_export_json(auth_client: AsyncClient):
    """Audit log JSON export returns downloadable file."""
    resp = await auth_client.get("/api/audit/export?format=json&days=7")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_audit_export_requires_auth(client: AsyncClient):
    """Audit export requires authentication."""
    resp = await client.get("/api/audit/export?format=csv")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════
# P1: User Invites
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_invite_user(auth_client: AsyncClient):
    """Admin can invite a new user."""
    resp = await auth_client.post("/api/auth/invite", json={
        "email": "newuser@test.com",
        "role": "viewer",
        "full_name": "New User",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "viewer"
    assert data["status"] == "invited"


@pytest.mark.asyncio
async def test_invite_duplicate_email(auth_client: AsyncClient):
    """Inviting existing email returns 409."""
    # First invite
    await auth_client.post("/api/auth/invite", json={
        "email": "dup@test.com", "role": "viewer",
    })
    # Duplicate
    resp = await auth_client.post("/api/auth/invite", json={
        "email": "dup@test.com", "role": "viewer",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_invite_invalid_role(auth_client: AsyncClient):
    """Invalid role returns 400."""
    resp = await auth_client.post("/api/auth/invite", json={
        "email": "bad@test.com", "role": "superadmin",
    })
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════
# P2: Password Change
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_change_password(auth_client: AsyncClient):
    """Authenticated user can change their password."""
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "TestPass123",
        "new_password": "NewSecure456!",
    })
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_client: AsyncClient):
    """Wrong current password returns 400."""
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "WrongPassword",
        "new_password": "NewSecure456!",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_weak_new(auth_client: AsyncClient):
    """Weak new password returns 400."""
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "TestPass123",
        "new_password": "weak",
    })
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════
# P2: Prometheus Metrics
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """Prometheus /metrics endpoint returns prometheus-client format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    # prometheus-client library outputs HELP/TYPE headers
    assert "# HELP" in text
    assert "# TYPE" in text
    # Custom KavachIQ metrics present
    assert "kavachiq_http_requests_total" in text or "kavachiq_tenants_active" in text


@pytest.mark.asyncio
async def test_metrics_no_auth_required(client: AsyncClient):
    """/metrics should be publicly accessible (Prometheus scraper has no auth)."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════
# P0: Tenant Filter Coverage
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_resolve_tenant_filter_returns_user_tenants():
    """resolve_tenant_filter returns assigned tenant IDs."""
    from app.services.auth import resolve_tenant_filter
    from app.database import async_session
    from app.models.tenant import Tenant, TenantStatus
    from app.models.user import User
    from app.models.user_tenant import UserTenant

    async with async_session() as db:
        # Create test tenant
        t = Tenant(name="Filter Test", ms_tenant_id="filter-test-001", client_id="test", client_secret_encrypted="test", status=TenantStatus.ACTIVE)
        db.add(t)
        await db.flush()

        # Create test user
        u = User(username="filtertest", email="filter@test.com", password_hash="x", role="admin")
        db.add(u)
        await db.flush()

        # Assign
        db.add(UserTenant(user_id=u.id, tenant_id=t.id, role="owner"))
        await db.flush()

        # Test with tenant_id provided
        result = await resolve_tenant_filter(db, u, t.id)
        assert result == [t.id]

        # Test without tenant_id (returns all assigned)
        result = await resolve_tenant_filter(db, u, None)
        assert t.id in result

        await db.rollback()


@pytest.mark.asyncio
async def test_resolve_tenant_filter_blocks_unassigned():
    """resolve_tenant_filter raises 403 for unassigned tenant."""
    from app.services.auth import resolve_tenant_filter
    from app.database import async_session
    from app.models.user import User
    from fastapi import HTTPException

    async with async_session() as db:
        u = User(username="blocked", email="blocked@test.com", password_hash="x", role="viewer")
        db.add(u)
        await db.flush()

        with pytest.raises(HTTPException) as exc_info:
            await resolve_tenant_filter(db, u, 99999)
        assert exc_info.value.status_code == 403

        await db.rollback()
