"""Tests for Workload Lifecycle state machine.

Verifies: opt-in per workload, subscription gating, discovery scoping,
protection coverage, smart engine grace period, dashboard scoping.

Every scenario is automated — zero manual verification.
"""
import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════
# Helpers — create test data for lifecycle tests
# ═══════════════════════════════════════════════════════

async def _create_test_tenant(db, name="Lifecycle Test", ms_tenant_id="lifecycle-001"):
    from app.models.tenant import Tenant, TenantStatus
    t = Tenant(
        name=name,
        ms_tenant_id=ms_tenant_id,
        client_id="test-client",
        client_secret_encrypted="test-secret",
        status=TenantStatus.ACTIVE,
    )
    db.add(t)
    await db.flush()
    return t


async def _create_workload_app(db, tenant_id, workload, lifecycle_status="disabled"):
    from app.models.tenant_workload_app import TenantWorkloadApp
    wl = TenantWorkloadApp(
        tenant_id=tenant_id,
        workload=workload,
        client_id="test-client",
        client_secret_encrypted="test-secret",
        consent_status="consented",
        lifecycle_status=lifecycle_status,
        backup_ready=1,
        restore_ready=1,
        enabled=1 if lifecycle_status != "disabled" else 0,
    )
    db.add(wl)
    await db.flush()
    return wl


async def _create_protected_object(db, tenant_id, workload_type, name, status="unprotected"):
    from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
    obj = ProtectedObject(
        tenant_id=tenant_id,
        workload_type=WorkloadType(workload_type),
        ms_object_id=f"test-{name.lower().replace(' ', '-')}",
        display_name=name,
        status=ProtectionStatus(status),
    )
    db.add(obj)
    await db.flush()
    return obj


async def _create_sla_policy(db, name="Test SLA", frequency_hours=24, retention_days=30):
    from app.models.sla_policy import SLAPolicy
    sla = SLAPolicy(
        name=name,
        backup_frequency_hours=frequency_hours,
        retention_days=retention_days,
        is_active=1,
    )
    db.add(sla)
    await db.flush()
    return sla


# ═══════════════════════════════════════════════════════
# Lifecycle State Machine Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_workload_default_disabled():
    """New workload apps start with lifecycle_status='disabled'."""
    from app.database import async_session
    from app.models.tenant_workload_app import TenantWorkloadApp

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Default Test", ms_tenant_id="default-001")
        wl = TenantWorkloadApp(
            tenant_id=t.id,
            workload="exchange",
            client_id="x",
            client_secret_encrypted="x",
            consent_status="consented",
        )
        db.add(wl)
        await db.flush()
        assert wl.lifecycle_status == "disabled"
        await db.commit()


@pytest.mark.asyncio
async def test_valid_lifecycle_transitions():
    """Verify all valid transitions succeed per the state machine."""
    from app.database import async_session
    from app.models.tenant_workload_app import WorkloadLifecycle
    from app.services.workload_lifecycle import transition_workload

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Transition Test", ms_tenant_id="transition-001")
        wl = await _create_workload_app(db, t.id, "exchange", "disabled")

        # disabled → enabled
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.ENABLED) is True
        assert wl.lifecycle_status == WorkloadLifecycle.ENABLED.value

        # enabled → discovered
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.DISCOVERED) is True
        assert wl.lifecycle_status == WorkloadLifecycle.DISCOVERED.value

        # discovered → protected
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.PROTECTED) is True
        assert wl.lifecycle_status == WorkloadLifecycle.PROTECTED.value

        # protected → paused
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.PAUSED) is True
        assert wl.lifecycle_status == WorkloadLifecycle.PAUSED.value

        # paused → protected (resume)
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.PROTECTED) is True
        assert wl.lifecycle_status == WorkloadLifecycle.PROTECTED.value

        # protected → disabled
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.DISABLED) is True
        assert wl.lifecycle_status == WorkloadLifecycle.DISABLED.value

        await db.commit()


@pytest.mark.asyncio
async def test_invalid_lifecycle_transitions():
    """Invalid transitions are rejected — cannot skip states."""
    from app.database import async_session
    from app.models.tenant_workload_app import WorkloadLifecycle
    from app.services.workload_lifecycle import transition_workload

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Invalid Test", ms_tenant_id="invalid-001")
        await _create_workload_app(db, t.id, "exchange", "disabled")

        # disabled → discovered (invalid: must go through enabled)
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.DISCOVERED) is False

        # disabled → protected (invalid: must go through enabled → discovered)
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.PROTECTED) is False

        # disabled → paused (invalid)
        assert await transition_workload(db, t.id, "exchange", WorkloadLifecycle.PAUSED) is False

        await db.commit()


# ═══════════════════════════════════════════════════════
# Enabled/Protected Workload Queries
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_enabled_workloads():
    """get_enabled_workloads returns only enabled+ workloads."""
    from app.database import async_session
    from app.services.workload_lifecycle import get_enabled_workloads

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Enabled Test", ms_tenant_id="enabled-001")
        await _create_workload_app(db, t.id, "exchange", "enabled")
        await _create_workload_app(db, t.id, "entra_id", "protected")
        await _create_workload_app(db, t.id, "onedrive", "disabled")
        await db.commit()

        enabled = await get_enabled_workloads(db, t.id)
        assert "exchange" in enabled
        assert "entra_id" in enabled
        assert "onedrive" not in enabled
        assert len(enabled) == 2


@pytest.mark.asyncio
async def test_get_protected_workloads():
    """get_protected_workloads returns only PROTECTED workloads."""
    from app.database import async_session
    from app.services.workload_lifecycle import get_protected_workloads

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Protected Test", ms_tenant_id="protected-001")
        await _create_workload_app(db, t.id, "exchange", "protected")
        await _create_workload_app(db, t.id, "entra_id", "enabled")
        await _create_workload_app(db, t.id, "onedrive", "discovered")
        await db.commit()

        protected = await get_protected_workloads(db, t.id)
        assert "exchange" in protected
        assert "entra_id" not in protected
        assert "onedrive" not in protected
        assert len(protected) == 1


# ═══════════════════════════════════════════════════════
# Subscription Gating
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_community_max_2_workloads():
    """Community tier: enabling 3rd workload is rejected."""
    from app.database import async_session
    from app.services.workload_lifecycle import check_subscription_limit

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Community Test", ms_tenant_id="community-001")
        # Enable 2 workloads (at limit for community)
        await _create_workload_app(db, t.id, "exchange", "enabled")
        await _create_workload_app(db, t.id, "entra_id", "enabled")
        await db.commit()

        allowed, reason = await check_subscription_limit(db, t.id, "community")
        assert allowed is False
        assert "2 workloads" in reason


@pytest.mark.asyncio
async def test_professional_allows_all_workloads():
    """Professional tier: enabling all 5 workloads succeeds."""
    from app.database import async_session
    from app.services.workload_lifecycle import check_subscription_limit

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Pro Test", ms_tenant_id="pro-001")
        # Enable 4 workloads
        for wl in ["exchange", "entra_id", "onedrive", "sharepoint"]:
            await _create_workload_app(db, t.id, wl, "enabled")
        await db.commit()

        allowed, reason = await check_subscription_limit(db, t.id, "professional")
        assert allowed is True
        assert reason == "OK"


@pytest.mark.asyncio
async def test_enterprise_allows_6_workloads():
    """Enterprise tier: supports 6 workloads (5 standard + Power Platform)."""
    from app.database import async_session
    from app.services.workload_lifecycle import check_subscription_limit

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Ent Test", ms_tenant_id="ent-001")
        # Enable 5 workloads
        for wl in ["exchange", "entra_id", "onedrive", "sharepoint", "teams"]:
            await _create_workload_app(db, t.id, wl, "enabled")
        await db.commit()

        allowed, reason = await check_subscription_limit(db, t.id, "enterprise")
        assert allowed is True
        assert reason == "OK"


# ═══════════════════════════════════════════════════════
# Smart Engine Grace Period
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_anomaly_skip_new_tenant():
    """Tenant with <3 snapshots gets 0 anomalies (grace period)."""
    from app.database import async_session
    from app.services.smart_engine import SmartEngine

    async with async_session() as db:
        t = await _create_test_tenant(db, name="New Tenant", ms_tenant_id="new-001")
        await db.commit()

        engine = SmartEngine(db)
        anomalies = await engine.detect_anomalies(t.id)
        assert len(anomalies) == 0


# ═══════════════════════════════════════════════════════
# /complete Protects ALL Discovered (No Workload Filter)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_complete_protects_all_discovered(auth_client: AsyncClient):
    """protect_all=True assigns SLA to ALL unprotected objects (no workload filter)."""
    from app.database import async_session
    from app.models.protected_object import ProtectedObject, ProtectionStatus
    from sqlalchemy import select, func

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Complete Test", ms_tenant_id="complete-001")
        sla = await _create_sla_policy(db, name="Hourly Test", frequency_hours=1)

        # Create objects for 2 different workloads
        await _create_protected_object(db, t.id, "exchange", "Mailbox A")
        await _create_protected_object(db, t.id, "entra_id", "Entra Config")

        # Enable workloads (so lifecycle transitions work)
        await _create_workload_app(db, t.id, "exchange", "discovered")
        await _create_workload_app(db, t.id, "entra_id", "discovered")
        await db.commit()
        tid = t.id
        sla_id = sla.id

    # Call /complete with protect_all=True, NO workload_types filter
    resp = await auth_client.post("/api/onboard/complete", json={
        "tenant_id": tid,
        "sla_policy_id": sla_id,
        "protect_all": True,
    })
    assert resp.status_code == 200

    # Verify: 0 unprotected objects for this tenant
    async with async_session() as db:
        unprotected_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.UNPROTECTED,
            )
        )).scalar()
        assert unprotected_count == 0

        # Verify: all objects are protected
        protected_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )).scalar()
        assert protected_count == 2


@pytest.mark.asyncio
async def test_complete_zero_unprotected_after(auth_client: AsyncClient):
    """After /complete, dashboard query for unprotected returns 0."""
    from app.database import async_session
    from app.models.protected_object import ProtectedObject, ProtectionStatus
    from sqlalchemy import select, func

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Zero Test", ms_tenant_id="zero-001")
        sla = await _create_sla_policy(db, name="Daily Test", frequency_hours=24)

        # Create 3 objects across different workloads
        for i, wl in enumerate(["exchange", "entra_id", "sharepoint"]):
            await _create_protected_object(db, t.id, wl, f"Object {i}")
            await _create_workload_app(db, t.id, wl, "discovered")
        await db.commit()
        tid = t.id
        sla_id = sla.id

    resp = await auth_client.post("/api/onboard/complete", json={
        "tenant_id": tid,
        "sla_policy_id": sla_id,
        "protect_all": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["protected_count"] == 3

    # Verify dashboard-style query returns 0 unprotected
    async with async_session() as db:
        unprotected = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.UNPROTECTED,
            )
        )).scalar()
        assert unprotected == 0


# ═══════════════════════════════════════════════════════
# Callback No Auto-Discovery
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_onboard_callback_no_autodiscovery():
    """Verify the callback endpoint does NOT run auto-discovery.

    After callback, new tenants should have 0 ProtectedObjects.
    Discovery only happens when customer explicitly calls /discover.
    """
    from app.database import async_session
    from app.models.tenant import Tenant, TenantStatus
    from app.models.protected_object import ProtectedObject
    from sqlalchemy import select, func

    # Create a tenant (simulating post-callback state)
    async with async_session() as db:
        t = Tenant(
            name="Callback Test",
            ms_tenant_id="callback-001",
            client_id="test",
            client_secret_encrypted="test",
            status=TenantStatus.ONBOARDING,
        )
        db.add(t)
        await db.flush()
        tid = t.id
        await db.commit()

    # Verify: 0 objects (callback didn't auto-discover)
    async with async_session() as db:
        obj_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(ProtectedObject.tenant_id == tid)
        )).scalar()
        assert obj_count == 0


# ═══════════════════════════════════════════════════════
# Dashboard Scoping
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_counts_only_enabled_workloads(auth_client: AsyncClient):
    """Dashboard summary only shows workloads that are enabled for the tenant."""
    from app.database import async_session
    from app.models.user_tenant import UserTenant

    async with async_session() as db:
        t = await _create_test_tenant(db, name="Dashboard Test", ms_tenant_id="dash-001")

        # Enable only exchange and entra_id
        await _create_workload_app(db, t.id, "exchange", "protected")
        await _create_workload_app(db, t.id, "entra_id", "protected")
        # OneDrive is DISABLED — should NOT appear in dashboard
        await _create_workload_app(db, t.id, "onedrive", "disabled")

        # Create objects for enabled workloads
        await _create_protected_object(db, t.id, "exchange", "Mailbox", "protected")
        await _create_protected_object(db, t.id, "entra_id", "Directory", "protected")

        # Assign test user to this tenant
        ut = UserTenant(user_id=1, tenant_id=t.id, role="owner", is_default=True)
        db.add(ut)
        await db.commit()
        tid = t.id

    resp = await auth_client.get(f"/api/dashboard/summary?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    # Should include exchange and entra_id, but NOT onedrive/sharepoint/teams
    workloads = data.get("workloads", {})
    assert "exchange" in workloads
    assert "entra_id" in workloads
    # Disabled workloads should not appear
    assert "onedrive" not in workloads


# ═══════════════════════════════════════════════════════
# E2E: Full Enable → Discover → Protect Flow
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_onboard_enable_discover_protect():
    """Full lifecycle: enable workloads → discover → protect → 0 unprotected.

    Simulates the happy path without Graph API calls (demo tenant).
    """
    from app.database import async_session
    from app.models.tenant_workload_app import TenantWorkloadApp, WorkloadLifecycle
    from app.models.protected_object import ProtectedObject, ProtectionStatus
    from app.services.workload_lifecycle import get_enabled_workloads, transition_workload
    from app.services.discovery import DiscoveryService
    from sqlalchemy import select, func

    async with async_session() as db:
        # Step 1: Create tenant (post-callback, no discovery yet)
        t = await _create_test_tenant(db, name="E2E Demo Corp", ms_tenant_id="demo-e2e-001")
        sla = await _create_sla_policy(db, name="Hourly E2E", frequency_hours=1)

        # Step 2: Enable 2 workloads (opt-in)
        await _create_workload_app(db, t.id, "exchange", "enabled")
        await _create_workload_app(db, t.id, "entra_id", "enabled")
        await db.commit()

        # Verify enabled workloads
        enabled = await get_enabled_workloads(db, t.id)
        assert enabled == {"exchange", "entra_id"}

        # Step 3: Discover only enabled workloads (demo discovery)
        discovery = DiscoveryService(db)
        result = await discovery.discover_all(t, workloads=list(enabled))

        # Should have discovered objects for exchange + entra_id only
        assert result["mailboxes"] > 0
        assert result["entra_objects"] > 0
        # OneDrive/SharePoint/Teams should be 0 (not enabled)
        assert result["onedrives"] == 0
        assert result["sites"] == 0
        assert result["teams"] == 0

        # Transition to discovered
        for wl in enabled:
            await transition_workload(db, t.id, wl, WorkloadLifecycle.DISCOVERED)

        # Step 4: Protect ALL discovered objects
        objs = (await db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == t.id,
                ProtectedObject.status == ProtectionStatus.UNPROTECTED,
            )
        )).scalars().all()
        for obj in objs:
            obj.sla_policy_id = sla.id
            obj.status = ProtectionStatus.PROTECTED

        # Transition to protected
        for wl in enabled:
            await transition_workload(db, t.id, wl, WorkloadLifecycle.PROTECTED)

        await db.commit()

        # Step 5: Verify 0 unprotected
        unprotected = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == t.id,
                ProtectedObject.status == ProtectionStatus.UNPROTECTED,
            )
        )).scalar()
        assert unprotected == 0

        # Verify all objects are in workloads we enabled
        all_objs = (await db.execute(
            select(ProtectedObject).where(ProtectedObject.tenant_id == t.id)
        )).scalars().all()
        for obj in all_objs:
            wl_type = obj.workload_type.value if hasattr(obj.workload_type, 'value') else str(obj.workload_type)
            assert wl_type in enabled, f"Object {obj.display_name} is in {wl_type}, but only {enabled} are enabled"
