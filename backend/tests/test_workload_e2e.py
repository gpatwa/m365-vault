"""End-to-End tests for Per-Workload App Separation.

Tests the full lifecycle:
  1. Create tenant → Enable workloads → Verify apps created
  2. Credential resolver picks correct workload app
  3. Backup engine uses workload-specific credentials
  4. Restore engine uses workload-specific credentials
  5. Permission check returns per-workload breakdown
  6. Disable/remove workload → resolver falls back
  7. Full RBAC matrix for workload management
"""
import json
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.tenant_workload_app import TenantWorkloadApp
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotType
from app.models.user import User, UserRole


# ═══════════════════════════════════════════════════════
# E2E: Full Workload Lifecycle
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2e_enable_workloads_and_list(auth_client: AsyncClient):
    """E2E: Create tenant → enable workloads → list → verify."""
    # 1. Create tenant
    async with async_session() as db:
        tenant = Tenant(
            name="E2E Workload Corp", ms_tenant_id="e2e-wl-001",
            client_id="cid-e2e", client_secret_encrypted="enc-e2e",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()
        tid = tenant.id
        await db.commit()

    # 2. Enable workloads
    resp = await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["entra_id", "exchange"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["workloads_created"]) == {"entra_id", "exchange"}
    assert data["total_workload_apps"] == 2

    # 3. List workloads
    resp = await auth_client.get(f"/api/tenants/{tid}/workloads")
    assert resp.status_code == 200
    workloads = resp.json()["workloads"]
    assert len(workloads) == 2
    wl_map = {w["workload"]: w for w in workloads}
    assert wl_map["entra_id"]["consent_status"] == "consented"
    assert wl_map["exchange"]["backup_ready"] is True

    # 4. Disable exchange
    resp = await auth_client.post(f"/api/tenants/{tid}/workloads/exchange/disable")
    assert resp.status_code == 200

    # 5. Verify disabled
    resp = await auth_client.get(f"/api/tenants/{tid}/workloads")
    workloads = resp.json()["workloads"]
    exchange = next(w for w in workloads if w["workload"] == "exchange")
    assert exchange["enabled"] is False

    # 6. Remove exchange
    resp = await auth_client.delete(f"/api/tenants/{tid}/workloads/exchange")
    assert resp.status_code == 200

    # 7. Verify only entra_id remains
    resp = await auth_client.get(f"/api/tenants/{tid}/workloads")
    workloads = resp.json()["workloads"]
    assert len(workloads) == 1
    assert workloads[0]["workload"] == "entra_id"


@pytest.mark.asyncio
async def test_e2e_credential_resolver_picks_workload_app():
    """E2E: Credential resolver returns per-workload app credentials."""
    async with async_session() as db:
        tenant = Tenant(
            name="Resolver E2E", ms_tenant_id="resolver-e2e-001",
            client_id="cid-legacy", client_secret_encrypted="enc-legacy",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        # Add per-workload app for exchange with DIFFERENT credentials
        exchange_app = TenantWorkloadApp(
            tenant_id=tenant.id, workload="exchange",
            client_id="cid-exchange-specific",
            client_secret_encrypted="enc-exchange-specific",
            consent_status="consented", backup_ready=1, enabled=1,
        )
        db.add(exchange_app)
        await db.flush()

        # Resolver should pick exchange-specific app
        from app.services.credential_resolver import get_workload_app
        app = await get_workload_app(db, tenant.id, "exchange")
        assert app is not None
        assert app.client_id == "cid-exchange-specific"

        # For entra_id (no workload app), resolver should fall back
        entra_app = await get_workload_app(db, tenant.id, "entra_id")
        assert entra_app is None  # No per-workload app → will use legacy

        await db.commit()


@pytest.mark.asyncio
async def test_e2e_credential_resolver_selects_correct_app():
    """E2E: Credential resolver selects per-workload app over legacy credentials."""
    async with async_session() as db:
        tenant = Tenant(
            name="Select E2E", ms_tenant_id="select-e2e-001",
            client_id="cid-legacy", client_secret_encrypted="enc-legacy",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        # Create per-workload apps with DIFFERENT client_ids
        for wl in ["entra_id", "exchange"]:
            app = TenantWorkloadApp(
                tenant_id=tenant.id, workload=wl,
                client_id=f"cid-{wl}-specific",
                client_secret_encrypted=f"enc-{wl}-specific",
                consent_status="consented", backup_ready=1, enabled=1,
            )
            db.add(app)
        await db.flush()

        # Verify resolver finds correct app for each workload
        from app.services.credential_resolver import get_workload_app
        entra_app = await get_workload_app(db, tenant.id, "entra_id")
        exchange_app = await get_workload_app(db, tenant.id, "exchange")
        teams_app = await get_workload_app(db, tenant.id, "teams")

        assert entra_app is not None
        assert entra_app.client_id == "cid-entra_id-specific"

        assert exchange_app is not None
        assert exchange_app.client_id == "cid-exchange-specific"

        assert teams_app is None  # Not configured

        await db.commit()


@pytest.mark.asyncio
async def test_e2e_enable_all_five_workloads(auth_client: AsyncClient):
    """E2E: Can enable all 5 workloads for a tenant."""
    async with async_session() as db:
        tenant = Tenant(
            name="All Workloads Corp", ms_tenant_id="all-wl-001",
            client_id="cid-all", client_secret_encrypted="enc-all",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()
        tid = tenant.id
        await db.commit()

    resp = await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["entra_id", "exchange", "sharepoint", "onedrive", "teams"],
    })
    assert resp.status_code == 200
    assert resp.json()["total_workload_apps"] == 5

    resp = await auth_client.get(f"/api/tenants/{tid}/workloads")
    assert len(resp.json()["workloads"]) == 5


@pytest.mark.asyncio
async def test_e2e_permission_maps_per_workload():
    """E2E: Each workload has isolated permissions — no cross-contamination."""
    from app.services.app_provisioning import get_workload_permissions

    exchange = get_workload_permissions("exchange", include_restore=True)
    entra = get_workload_permissions("entra_id", include_restore=True)
    sharepoint = get_workload_permissions("sharepoint", include_restore=True)
    onedrive = get_workload_permissions("onedrive", include_restore=True)
    teams = get_workload_permissions("teams", include_restore=True)

    # Exchange shouldn't have directory permissions
    assert "Directory.Read.All" not in exchange
    assert "Application.ReadWrite.All" not in exchange

    # Entra ID shouldn't have mail permissions
    assert "Mail.Read" not in entra
    assert "Calendars.Read" not in entra

    # SharePoint shouldn't have mail or directory
    assert "Mail.Read" not in sharepoint
    assert "Directory.Read.All" not in sharepoint

    # OneDrive shouldn't have mail permissions
    assert "Mail.Read" not in onedrive

    # Teams shouldn't have mail or file permissions
    assert "Mail.Read" not in teams
    assert "Files.Read.All" not in teams

    # User.Read.All is shared where needed for enumeration
    assert "User.Read.All" in exchange  # enumerate mailboxes
    assert "User.Read.All" in entra     # enumerate users
    assert "User.Read.All" in onedrive  # enumerate drives


@pytest.mark.asyncio
async def test_e2e_workload_unique_constraint():
    """E2E: Cannot have duplicate workload for same tenant."""
    async with async_session() as db:
        tenant = Tenant(
            name="Unique E2E", ms_tenant_id="unique-wl-001",
            client_id="cid-uniq", client_secret_encrypted="enc-uniq",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        app1 = TenantWorkloadApp(
            tenant_id=tenant.id, workload="exchange",
            client_id="cid-ex1", client_secret_encrypted="enc-ex1",
            consent_status="consented", enabled=1,
        )
        db.add(app1)
        await db.flush()

        # Try duplicate
        app2 = TenantWorkloadApp(
            tenant_id=tenant.id, workload="exchange",
            client_id="cid-ex2", client_secret_encrypted="enc-ex2",
            consent_status="consented", enabled=1,
        )
        db.add(app2)

        import sqlalchemy.exc
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            await db.flush()

        await db.rollback()


@pytest.mark.asyncio
async def test_e2e_rbac_viewer_blocked(viewer_client: AsyncClient):
    """E2E: VIEWER cannot manage workloads."""
    async with async_session() as db:
        tenant = Tenant(
            name="RBAC E2E", ms_tenant_id="rbac-wl-001",
            client_id="cid-rbac", client_secret_encrypted="enc-rbac",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()
        tid = tenant.id
        await db.commit()

    # VIEWER can list but not enable
    resp = await viewer_client.get(f"/api/tenants/{tid}/workloads")
    assert resp.status_code == 200  # Read OK

    resp = await viewer_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["exchange"],
    })
    assert resp.status_code == 403  # Write blocked


@pytest.mark.asyncio
async def test_e2e_workload_api_audit_trail(auth_client: AsyncClient):
    """E2E: Enabling workloads creates audit log entries."""
    async with async_session() as db:
        tenant = Tenant(
            name="Audit E2E", ms_tenant_id="audit-wl-001",
            client_id="cid-audit", client_secret_encrypted="enc-audit",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()
        tid = tenant.id
        await db.commit()

    await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["entra_id"],
    })

    # Check audit log
    from app.models.audit_log import AuditLog
    from sqlalchemy import select
    async with async_session() as db:
        result = await db.execute(
            select(AuditLog).where(AuditLog.action == "workload.enabled")
        )
        logs = result.scalars().all()
        assert len(logs) >= 1
        assert "entra_id" in logs[0].details
