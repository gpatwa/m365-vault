"""Tests for Multi-Tenant Isolation (user_tenants membership).

Covers:
  - UserTenant model and assignment
  - get_user_tenant_ids() scoping
  - require_tenant_access() enforcement
  - /api/tenants/ filtered by user membership
  - Dashboard scoped to user's tenants
  - Cross-tenant access denied (403)
"""
import pytest
from httpx import AsyncClient

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, UserRole
from app.models.user_tenant import UserTenant
from app.services.auth import hash_password


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

async def _create_user(username: str, role: str = "admin") -> int:
    async with async_session() as db:
        user = User(
            username=username,
            email=f"{username}@test.com",
            password_hash=hash_password("Test123!"),
            full_name=f"{username.title()} User",
            role=UserRole(role),
            is_active=1,
            email_verified=1,
        )
        db.add(user)
        await db.flush()
        uid = user.id
        await db.commit()
    return uid


async def _create_tenant(name: str, ms_tenant_id: str = None) -> int:
    async with async_session() as db:
        tenant = Tenant(
            name=name,
            ms_tenant_id=ms_tenant_id or f"test-{name.lower().replace(' ', '-')}",
            client_id=f"cid-{name.lower().replace(' ', '-')}",
            client_secret_encrypted="enc-test",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()
        tid = tenant.id
        await db.commit()
    return tid


async def _assign_user_tenant(user_id: int, tenant_id: int, role: str = "member") -> None:
    async with async_session() as db:
        db.add(UserTenant(user_id=user_id, tenant_id=tenant_id, role=role, is_default=1))
        await db.commit()


async def _login(client: AsyncClient, username: str, password: str = "Test123!") -> str:
    resp = await client.post("/api/auth/login", data={"username": username, "password": password})
    return resp.json().get("access_token", "")


# ═══════════════════════════════════════════════════════
# Model Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_user_tenant_assignment():
    """UserTenant model stores user-tenant membership."""
    uid = await _create_user("iso_user1")
    tid = await _create_tenant("Iso Corp 1")
    await _assign_user_tenant(uid, tid, "owner")

    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(UserTenant).where(UserTenant.user_id == uid, UserTenant.tenant_id == tid)
        )
        ut = result.scalar_one_or_none()
        assert ut is not None
        assert ut.role == "owner"


@pytest.mark.asyncio
async def test_user_tenant_unique_constraint():
    """Cannot assign same user to same tenant twice."""
    uid = await _create_user("iso_user2")
    tid = await _create_tenant("Iso Corp 2")
    await _assign_user_tenant(uid, tid)

    with pytest.raises(Exception):  # IntegrityError
        await _assign_user_tenant(uid, tid)


# ═══════════════════════════════════════════════════════
# Auth Service Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_user_tenant_ids_returns_assigned():
    """get_user_tenant_ids returns only assigned tenant IDs."""
    uid = await _create_user("iso_user3")
    tid1 = await _create_tenant("Iso Corp 3A")
    tid2 = await _create_tenant("Iso Corp 3B")
    _tid3 = await _create_tenant("Iso Corp 3C")  # NOT assigned

    await _assign_user_tenant(uid, tid1)
    await _assign_user_tenant(uid, tid2)

    from app.services.auth import get_user_tenant_ids
    async with async_session() as db:
        user = await db.get(User, uid)
        ids = await get_user_tenant_ids(db, user)
        assert tid1 in ids
        assert tid2 in ids
        assert _tid3 not in ids


@pytest.mark.asyncio
async def test_require_tenant_access_allows_assigned():
    """require_tenant_access passes for assigned tenant."""
    uid = await _create_user("iso_user4")
    tid = await _create_tenant("Iso Corp 4")
    await _assign_user_tenant(uid, tid)

    from app.services.auth import require_tenant_access
    async with async_session() as db:
        user = await db.get(User, uid)
        # Should not raise
        await require_tenant_access(db, tid, user)


@pytest.mark.asyncio
async def test_require_tenant_access_blocks_unassigned():
    """require_tenant_access raises 403 for unassigned tenant."""
    uid = await _create_user("iso_user5", role="viewer")  # non-admin, no fallback
    tid = await _create_tenant("Iso Corp 5")
    # NOT assigned

    from app.services.auth import require_tenant_access
    from fastapi import HTTPException
    async with async_session() as db:
        user = await db.get(User, uid)
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_access(db, tid, user)
        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_assign_user_to_tenant_idempotent():
    """assign_user_to_tenant skips if already assigned."""
    uid = await _create_user("iso_user6")
    tid = await _create_tenant("Iso Corp 6")

    from app.services.auth import assign_user_to_tenant
    async with async_session() as db:
        await assign_user_to_tenant(db, uid, tid, role="owner")
        await db.commit()

    # Call again — should not raise
    async with async_session() as db:
        await assign_user_to_tenant(db, uid, tid, role="owner")
        await db.commit()


# ═══════════════════════════════════════════════════════
# API Tests — Tenant List Scoped
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tenant_list_scoped_to_user(client: AsyncClient):
    """GET /api/tenants/ returns only user's assigned tenants."""
    uid = await _create_user("iso_api1")
    tid1 = await _create_tenant("API Tenant A")
    _tid2 = await _create_tenant("API Tenant B")  # NOT assigned
    await _assign_user_tenant(uid, tid1)

    token = await _login(client, "iso_api1")
    resp = await client.get("/api/tenants/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    tenants = resp.json()
    tenant_ids = [t["id"] for t in tenants]
    assert tid1 in tenant_ids
    assert _tid2 not in tenant_ids


@pytest.mark.asyncio
async def test_tenant_list_empty_for_unassigned_user(client: AsyncClient):
    """User with no tenant assignments sees empty list."""
    await _create_user("iso_api2", role="viewer")

    token = await _login(client, "iso_api2")
    resp = await client.get("/api/tenants/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


# ═══════════════════════════════════════════════════════
# API Tests — Dashboard Scoped
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_scoped_to_user_tenants(client: AsyncClient):
    """Dashboard summary only counts user's tenant data."""
    uid = await _create_user("iso_dash1")
    tid = await _create_tenant("Dash Tenant")
    await _assign_user_tenant(uid, tid)

    token = await _login(client, "iso_dash1")
    resp = await client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_rejects_wrong_tenant(client: AsyncClient):
    """Dashboard returns 403 when accessing unassigned tenant."""
    uid = await _create_user("iso_dash2")
    tid_mine = await _create_tenant("My Dash Tenant")
    tid_other = await _create_tenant("Other Dash Tenant")
    await _assign_user_tenant(uid, tid_mine)

    token = await _login(client, "iso_dash2")
    # Access my tenant — OK
    resp = await client.get(f"/api/dashboard/summary?tenant_id={tid_mine}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # Access other tenant — 403
    resp = await client.get(f"/api/dashboard/summary?tenant_id={tid_other}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ═══════════════════════════════════════════════════════
# Admin Fallback Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_admin_fallback_sees_all_tenants():
    """Platform superadmin (username=admin) with no memberships sees all (migration compat)."""
    # The special "admin" username gets the fallback
    uid = await _create_user("admin", role="admin")
    tid1 = await _create_tenant("FB Tenant 1")
    tid2 = await _create_tenant("FB Tenant 2")
    # No explicit assignment

    from app.services.auth import get_user_tenant_ids
    async with async_session() as db:
        user = await db.get(User, uid)
        ids = await get_user_tenant_ids(db, user)
        assert tid1 in ids
        assert tid2 in ids


@pytest.mark.asyncio
async def test_non_superadmin_no_fallback():
    """Non-superadmin ADMIN users don't get fallback — must be explicitly assigned."""
    uid = await _create_user("iso_admin_nofb", role="admin")
    _tid = await _create_tenant("No FB Tenant")
    # No explicit assignment

    from app.services.auth import get_user_tenant_ids
    async with async_session() as db:
        user = await db.get(User, uid)
        ids = await get_user_tenant_ids(db, user)
        assert ids == []  # No fallback for non-"admin" username
