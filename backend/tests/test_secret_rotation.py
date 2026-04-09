"""Tests for secret rotation — expiry monitoring and alerting."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.database import async_session


@pytest_asyncio.fixture
async def saas_apps_with_expiry(db):
    """Create SaaS workload apps with various expiry dates."""
    from app.models.saas_workload_app import SaaSWorkloadApp

    now = datetime.utcnow()
    apps = [
        SaaSWorkloadApp(
            workload="exchange",
            display_name="KavachIQ-Exchange",
            app_id="healthy-app-id-1234",
            client_secret_encrypted="enc-secret",
            secret_expires_at=now + timedelta(days=90),  # Healthy
        ),
        SaaSWorkloadApp(
            workload="sharepoint",
            display_name="KavachIQ-SharePoint",
            app_id="warning-app-id-5678",
            client_secret_encrypted="enc-secret",
            secret_expires_at=now + timedelta(days=25),  # Warning (< 30d)
        ),
        SaaSWorkloadApp(
            workload="onedrive",
            display_name="KavachIQ-OneDrive",
            app_id="critical-app-id-9012",
            client_secret_encrypted="enc-secret",
            secret_expires_at=now + timedelta(days=5),  # Critical (< 7d)
        ),
        SaaSWorkloadApp(
            workload="teams",
            display_name="KavachIQ-Teams",
            app_id="expired-app-id-3456",
            client_secret_encrypted="enc-secret",
            secret_expires_at=now - timedelta(days=2),  # Expired
        ),
    ]
    for app in apps:
        db.add(app)
    await db.commit()
    return apps


class TestCheckExpiringSecrets:
    """check_expiring_secrets() detects and alerts on expiring secrets."""

    @pytest.mark.asyncio
    async def test_warns_at_30d(self, db, saas_apps_with_expiry):
        """Secret expiring in 25 days triggers warning."""
        from app.services.secret_rotation import check_expiring_secrets
        expiring = await check_expiring_secrets()
        workloads = {e["workload"]: e for e in expiring}
        assert "sharepoint" in workloads
        assert workloads["sharepoint"]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_critical_at_7d(self, db, saas_apps_with_expiry):
        """Secret expiring in 5 days triggers critical alert."""
        from app.services.secret_rotation import check_expiring_secrets
        expiring = await check_expiring_secrets()
        workloads = {e["workload"]: e for e in expiring}
        assert "onedrive" in workloads
        assert workloads["onedrive"]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_expired_is_critical(self, db, saas_apps_with_expiry):
        """Already expired secret is flagged as critical."""
        from app.services.secret_rotation import check_expiring_secrets
        expiring = await check_expiring_secrets()
        workloads = {e["workload"]: e for e in expiring}
        assert "teams" in workloads
        assert workloads["teams"]["status"] == "expired"

    @pytest.mark.asyncio
    async def test_ignores_healthy(self, db, saas_apps_with_expiry):
        """Secret expiring in 90 days is not flagged."""
        from app.services.secret_rotation import check_expiring_secrets
        expiring = await check_expiring_secrets()
        workloads = {e["workload"] for e in expiring}
        assert "exchange" not in workloads


class TestSecretStatus:
    """get_secret_status() returns status without exposing secrets."""

    @pytest.mark.asyncio
    async def test_status_no_secret_values(self, db, saas_apps_with_expiry):
        """Status response never contains actual secret values."""
        from app.services.secret_rotation import get_secret_status
        statuses = await get_secret_status()
        for s in statuses:
            assert "client_secret" not in s
            # app_id is truncated to first 8 chars + "..."
            if s.get("client_id"):
                assert s["client_id"].endswith("...")

    @pytest.mark.asyncio
    async def test_status_structure(self, db, saas_apps_with_expiry):
        """Status has expected fields."""
        from app.services.secret_rotation import get_secret_status
        statuses = await get_secret_status()
        assert len(statuses) == 4
        for s in statuses:
            assert "workload" in s
            assert "status" in s
            assert s["status"] in ("healthy", "warning", "critical", "expired", "no_expiry_set")


class TestDiagnosticsEndpoint:
    """GET /api/diagnostics/secrets endpoint."""

    @pytest.mark.asyncio
    async def test_endpoint_returns_200(self, auth_client, saas_apps_with_expiry):
        """Diagnostics secrets endpoint is accessible to admin."""
        response = await auth_client.get("/api/diagnostics/secrets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
