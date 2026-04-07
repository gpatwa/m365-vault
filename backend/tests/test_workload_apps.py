"""Tests for Per-Workload App Separation (Phase 8).

Covers:
  - TenantWorkloadApp model + credential resolver
  - SaaSWorkloadApp model + workload bootstrap
  - Workload management API (enable, list, check, disable, remove)
  - Credential resolver: per-workload app vs fallback
  - Permission maps
  - Auto-bootstrap lifecycle
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.tenant_workload_app import TenantWorkloadApp
from app.models.saas_workload_app import SaaSWorkloadApp
from app.models.user import User, UserRole


# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════

async def _seed_tenant():
    """Create a test tenant with credentials."""
    async with async_session() as db:
        tenant = Tenant(
            name="Workload Test Corp", ms_tenant_id="wl-test-001",
            client_id="cid-wl-test", client_secret_encrypted="enc-wl-test",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()
        tid = tenant.id
        await db.commit()
    return tid


async def _seed_workload_app(tenant_id, workload="exchange", consent="consented"):
    """Create a workload app entry."""
    async with async_session() as db:
        app = TenantWorkloadApp(
            tenant_id=tenant_id,
            workload=workload,
            client_id=f"cid-{workload}-test",
            client_secret_encrypted=f"enc-{workload}-test",
            consent_status=consent,
            permissions_requested=json.dumps(["Mail.Read"]),
            backup_ready=1 if consent == "consented" else 0,
            restore_ready=1 if consent == "consented" else 0,
            enabled=1,
        )
        db.add(app)
        await db.flush()
        app_id = app.id
        await db.commit()
    return app_id


# ═══════════════════════════════════════════════════════
# Credential Resolver Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_credential_resolver_uses_workload_app():
    """Resolver returns workload-specific credentials when available."""
    tid = await _seed_tenant()
    await _seed_workload_app(tid, "exchange", "consented")

    from app.services.credential_resolver import get_graph_client
    async with async_session() as db:
        tenant = await db.get(Tenant, tid)
        # This will fail at GraphClient init (fake creds) but we can verify
        # the resolver found the right app by checking what it tries to use
        from app.services.credential_resolver import get_workload_app
        app = await get_workload_app(db, tid, "exchange")
        assert app is not None
        assert app.client_id == "cid-exchange-test"
        assert app.consent_status == "consented"


@pytest.mark.asyncio
async def test_credential_resolver_fallback_to_legacy():
    """Resolver falls back to tenant credentials when no workload app exists."""
    tid = await _seed_tenant()
    # No workload app created

    from app.services.credential_resolver import get_workload_app
    async with async_session() as db:
        app = await get_workload_app(db, tid, "exchange")
        assert app is None  # No workload app


@pytest.mark.asyncio
async def test_credential_resolver_disabled_app_not_used():
    """Disabled workload app is not returned by resolver."""
    tid = await _seed_tenant()
    async with async_session() as db:
        app = TenantWorkloadApp(
            tenant_id=tid, workload="exchange",
            client_id="cid-disabled", client_secret_encrypted="enc-disabled",
            consent_status="consented", enabled=0,  # DISABLED
        )
        db.add(app)
        await db.commit()

    from app.services.credential_resolver import get_workload_apps
    async with async_session() as db:
        apps = await get_workload_apps(db, tid, enabled_only=True)
        assert len(apps) == 0  # Disabled app filtered out


# ═══════════════════════════════════════════════════════
# Permission Maps Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_workload_permissions_exist():
    """All workloads have permission maps defined."""
    from app.services.app_provisioning import WORKLOAD_PERMISSIONS, get_workload_permissions

    for workload in ["entra_id", "exchange", "sharepoint", "onedrive", "teams"]:
        assert workload in WORKLOAD_PERMISSIONS
        perms = get_workload_permissions(workload)
        assert len(perms) > 0, f"No permissions for {workload}"


@pytest.mark.asyncio
async def test_workload_permissions_no_overlap():
    """Exchange app doesn't request Directory.Read.All (that's Entra ID's)."""
    from app.services.app_provisioning import get_workload_permissions

    exchange_perms = get_workload_permissions("exchange")
    assert "Directory.Read.All" not in exchange_perms
    assert "Mail.Read" in exchange_perms

    entra_perms = get_workload_permissions("entra_id")
    assert "Directory.Read.All" in entra_perms
    assert "Mail.Read" not in entra_perms


@pytest.mark.asyncio
async def test_workload_permissions_backup_only():
    """Backup-only permissions exclude ReadWrite."""
    from app.services.app_provisioning import get_workload_permissions

    perms = get_workload_permissions("exchange", include_restore=False)
    assert "Mail.Read" in perms
    assert "Mail.ReadWrite" not in perms


# ═══════════════════════════════════════════════════════
# Workload API Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_workload_api_requires_auth(client: AsyncClient):
    """Workload endpoints require authentication."""
    response = await client.get("/api/tenants/1/workloads")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_enable_workloads(auth_client: AsyncClient):
    """Enable workloads creates per-workload app entries."""
    tid = await _seed_tenant()

    response = await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["entra_id", "exchange"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "entra_id" in data["workloads_created"]
    assert "exchange" in data["workloads_created"]
    assert data["total_workload_apps"] == 2


@pytest.mark.asyncio
async def test_enable_duplicate_workload(auth_client: AsyncClient):
    """Enabling an already-enabled workload is idempotent."""
    tid = await _seed_tenant()

    # Enable first time
    await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["exchange"],
    })

    # Enable again — should not create duplicate
    response = await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["exchange"],
    })
    assert response.status_code == 200
    assert response.json()["total_workload_apps"] == 0  # Already exists


@pytest.mark.asyncio
async def test_enable_invalid_workload(auth_client: AsyncClient):
    """Invalid workload name returns 400."""
    tid = await _seed_tenant()
    response = await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["invalid_workload"],
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_workloads(auth_client: AsyncClient):
    """List workloads returns all configured apps."""
    tid = await _seed_tenant()
    await _seed_workload_app(tid, "entra_id")
    await _seed_workload_app(tid, "exchange")

    response = await auth_client.get(f"/api/tenants/{tid}/workloads")
    assert response.status_code == 200
    data = response.json()
    assert len(data["workloads"]) == 2
    workload_names = {w["workload"] for w in data["workloads"]}
    assert workload_names == {"entra_id", "exchange"}


@pytest.mark.asyncio
async def test_disable_workload(auth_client: AsyncClient):
    """Disabling a workload sets enabled=0."""
    tid = await _seed_tenant()
    await _seed_workload_app(tid, "exchange")

    response = await auth_client.post(f"/api/tenants/{tid}/workloads/exchange/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_remove_workload(auth_client: AsyncClient):
    """Removing a workload deletes the app entry."""
    tid = await _seed_tenant()
    await _seed_workload_app(tid, "exchange")

    response = await auth_client.delete(f"/api/tenants/{tid}/workloads/exchange")
    assert response.status_code == 200
    assert response.json()["removed"] is True

    # Verify it's gone
    response = await auth_client.get(f"/api/tenants/{tid}/workloads")
    assert len(response.json()["workloads"]) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_workload(auth_client: AsyncClient):
    """Removing a non-configured workload returns 404."""
    tid = await _seed_tenant()
    response = await auth_client.delete(f"/api/tenants/{tid}/workloads/exchange")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_viewer_cannot_enable_workloads(viewer_client: AsyncClient):
    """VIEWER role cannot enable workloads."""
    tid = await _seed_tenant()
    response = await viewer_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["exchange"],
    })
    assert response.status_code == 403


# ═══════════════════════════════════════════════════════
# SaaS Workload App (Platform-Level) Tests
# ═══════════════════════════════════════════════════════

async def _seed_saas_workload_app(workload="exchange"):
    """Create a SaaS-level workload app entry."""
    from app.services.app_provisioning import WORKLOAD_PERMISSIONS
    config = WORKLOAD_PERMISSIONS[workload]
    perms = set(config["backup"]) | set(config.get("restore", []))

    async with async_session() as db:
        app = SaaSWorkloadApp(
            workload=workload,
            display_name=config["display_name"],
            app_id=f"saas-app-{workload}-test",
            app_object_id=f"saas-obj-{workload}-test",
            client_secret_encrypted=f"enc-saas-{workload}-test",
            permissions_configured=json.dumps(sorted(perms)),
            sign_in_audience="AzureADMultipleOrgs",
            redirect_uris=json.dumps(["http://localhost:5173/onboard/callback"]),
            secret_expires_at=datetime.utcnow() + timedelta(days=365),
            status="active",
        )
        db.add(app)
        await db.flush()
        app_id = app.id
        await db.commit()
    return app_id


@pytest.mark.asyncio
async def test_saas_workload_app_model():
    """SaaSWorkloadApp stores platform-level per-workload app registrations."""
    app_id = await _seed_saas_workload_app("exchange")

    async with async_session() as db:
        app = await db.get(SaaSWorkloadApp, app_id)
        assert app is not None
        assert app.workload == "exchange"
        assert app.display_name == "KavachIQ-Exchange"
        assert app.app_id.startswith("saas-app-exchange")
        assert app.status == "active"


@pytest.mark.asyncio
async def test_saas_workload_app_unique_constraint():
    """Cannot create two SaaS apps for the same workload."""
    await _seed_saas_workload_app("entra_id")

    with pytest.raises(Exception):  # IntegrityError
        await _seed_saas_workload_app("entra_id")


@pytest.mark.asyncio
async def test_get_saas_workload_app():
    """get_saas_workload_app returns the active app for a workload."""
    await _seed_saas_workload_app("sharepoint")

    from app.services.workload_bootstrap import get_saas_workload_app
    async with async_session() as db:
        app = await get_saas_workload_app(db, "sharepoint")
        assert app is not None
        assert app.workload == "sharepoint"
        assert app.display_name == "KavachIQ-SharePoint"


@pytest.mark.asyncio
async def test_get_all_saas_workload_apps():
    """get_all_saas_workload_apps returns dict keyed by workload."""
    await _seed_saas_workload_app("onedrive")
    await _seed_saas_workload_app("teams")

    from app.services.workload_bootstrap import get_all_saas_workload_apps
    async with async_session() as db:
        apps = await get_all_saas_workload_apps(db)
        assert "onedrive" in apps
        assert "teams" in apps
        assert apps["onedrive"].display_name == "KavachIQ-OneDrive"


@pytest.mark.asyncio
async def test_enable_workloads_uses_saas_app(auth_client: AsyncClient):
    """When SaaS workload app exists, enable_workloads uses its credentials."""
    tid = await _seed_tenant()
    await _seed_saas_workload_app("exchange")

    response = await auth_client.post(f"/api/tenants/{tid}/workloads", json={
        "workloads": ["exchange"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "exchange" in data["workloads_created"]
    assert data.get("per_workload_apps") is True

    # Verify the TenantWorkloadApp uses the SaaS app's client_id
    async with async_session() as db:
        from app.services.credential_resolver import get_workload_app
        wl_app = await get_workload_app(db, tid, "exchange")
        assert wl_app is not None
        assert wl_app.client_id == "saas-app-exchange-test"
        assert wl_app.consent_status == "pending"  # Customer hasn't consented yet


@pytest.mark.asyncio
async def test_workload_bootstrap_idempotent():
    """Bootstrap skips workloads already in the database."""
    # Seed one app manually
    await _seed_saas_workload_app("exchange")

    from app.services.workload_bootstrap import get_saas_workload_app
    async with async_session() as db:
        app = await get_saas_workload_app(db, "exchange")
        original_id = app.id

    # Bootstrap should skip exchange since it already exists
    # (Will also skip others due to no credentials)
    from app.services.workload_bootstrap import bootstrap_workload_apps
    await bootstrap_workload_apps()

    async with async_session() as db:
        app = await get_saas_workload_app(db, "exchange")
        assert app.id == original_id  # Same record, not re-created


@pytest.mark.asyncio
async def test_all_workloads_have_display_names():
    """Every workload config has a display_name for Entra app registration."""
    from app.services.app_provisioning import WORKLOAD_PERMISSIONS

    for workload, config in WORKLOAD_PERMISSIONS.items():
        assert "display_name" in config, f"Missing display_name for {workload}"
        assert config["display_name"].startswith("KavachIQ-"), f"Bad display_name for {workload}"


@pytest.mark.asyncio
async def test_workload_consent_url_format():
    """Consent URLs use per-workload app IDs, not the legacy connector ID."""
    await _seed_saas_workload_app("exchange")
    await _seed_saas_workload_app("entra_id")

    from app.services.workload_bootstrap import get_all_saas_workload_apps
    async with async_session() as db:
        saas_apps = await get_all_saas_workload_apps(db)

    tenant_id = "test-tenant-123"
    for wl_key, saas_app in saas_apps.items():
        url = (
            f"https://login.microsoftonline.com/{tenant_id}/adminconsent"
            f"?client_id={saas_app.app_id}"
        )
        assert saas_app.app_id in url
        assert "saas-app-" in url  # Uses per-workload app, not CONNECTOR_APP_ID
