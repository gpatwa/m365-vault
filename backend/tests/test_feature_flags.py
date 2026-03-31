"""Feature flags tests — tier-based gating, admin overrides, API endpoints."""
import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════
# 1. Public API (No Auth)
# ═══════════════════════════════════════════════════════

class TestFeatureFlagsPublic:

    @pytest.mark.asyncio
    async def test_get_features_no_auth(self, client: AsyncClient):
        """Features endpoint works without authentication (for UI gating)."""
        response = await client.get("/api/features")
        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "features" in data
        assert "limits" in data

    @pytest.mark.asyncio
    async def test_features_has_expected_structure(self, client: AsyncClient):
        """Each feature has enabled and source fields."""
        response = await client.get("/api/features")
        data = response.json()
        features = data["features"]
        assert len(features) > 0
        for name, info in features.items():
            assert "enabled" in info
            assert "source" in info

    @pytest.mark.asyncio
    async def test_check_single_feature(self, client: AsyncClient):
        """Check a specific feature returns correct structure."""
        response = await client.get("/api/features/check/exchange")
        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "exchange"
        assert isinstance(data["enabled"], bool)
        assert "tier" in data

    @pytest.mark.asyncio
    async def test_check_nonexistent_feature(self, client: AsyncClient):
        """Nonexistent feature returns enabled=false."""
        response = await client.get("/api/features/check/nonexistent_feature")
        assert response.status_code == 200
        assert response.json()["enabled"] is False


# ═══════════════════════════════════════════════════════
# 2. Categories API
# ═══════════════════════════════════════════════════════

class TestFeatureCategories:

    @pytest.mark.asyncio
    async def test_categories_endpoint(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/features/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        cats = data["categories"]
        assert "workloads" in cats
        assert "intelligence" in cats
        assert "recovery" in cats
        assert "compliance" in cats
        assert "operations" in cats
        assert "platform" in cats

    @pytest.mark.asyncio
    async def test_categories_have_features(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/features/categories")
        cats = response.json()["categories"]
        # Workloads should always have exchange
        assert "exchange" in cats["workloads"]
        # Intelligence should have anomaly_detection
        assert "anomaly_detection" in cats["intelligence"]


# ═══════════════════════════════════════════════════════
# 3. Tier Comparison API
# ═══════════════════════════════════════════════════════

class TestTierComparison:

    @pytest.mark.asyncio
    async def test_tier_comparison(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/features/tiers")
        assert response.status_code == 200
        data = response.json()
        assert "current_tier" in data
        assert "comparison" in data
        comparison = data["comparison"]
        # Exchange should be in all tiers
        assert comparison["exchange"]["community"] is True
        assert comparison["exchange"]["enterprise"] is True
        # MSP dashboard should only be in business+
        assert comparison["msp_dashboard"]["community"] is False
        assert comparison["msp_dashboard"]["professional"] is False
        assert comparison["msp_dashboard"]["business"] is True
        assert comparison["msp_dashboard"]["enterprise"] is True

    @pytest.mark.asyncio
    async def test_enterprise_has_all_features(self, auth_client: AsyncClient):
        """Enterprise tier should have every feature enabled."""
        response = await auth_client.get("/api/features/tiers")
        comparison = response.json()["comparison"]
        for feature, tiers in comparison.items():
            assert tiers["enterprise"] is True, f"Enterprise missing: {feature}"


# ═══════════════════════════════════════════════════════
# 4. Admin Overrides
# ═══════════════════════════════════════════════════════

class TestAdminOverrides:

    @pytest.mark.asyncio
    async def test_set_override_enables_feature(self, auth_client: AsyncClient):
        """Admin can force-enable a feature."""
        # Community tier: msp_dashboard is disabled
        check = await auth_client.get("/api/features/check/msp_dashboard")
        assert check.json()["enabled"] is False

        # Force enable
        resp = await auth_client.put("/api/features/override", json={
            "feature": "msp_dashboard", "enabled": True,
        })
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

        # Verify it's now enabled
        check2 = await auth_client.get("/api/features/check/msp_dashboard")
        assert check2.json()["enabled"] is True

        # Clean up
        await auth_client.delete("/api/features/override/msp_dashboard")

    @pytest.mark.asyncio
    async def test_set_override_disables_feature(self, auth_client: AsyncClient):
        """Admin can force-disable a feature."""
        # Exchange is enabled in all tiers
        check = await auth_client.get("/api/features/check/exchange")
        assert check.json()["enabled"] is True

        # Force disable
        await auth_client.put("/api/features/override", json={
            "feature": "exchange", "enabled": False,
        })
        check2 = await auth_client.get("/api/features/check/exchange")
        assert check2.json()["enabled"] is False

        # Clean up
        await auth_client.delete("/api/features/override/exchange")

    @pytest.mark.asyncio
    async def test_remove_override_reverts(self, auth_client: AsyncClient):
        """Removing override reverts to tier-based."""
        await auth_client.put("/api/features/override", json={
            "feature": "msp_dashboard", "enabled": True,
        })
        # Remove
        resp = await auth_client.delete("/api/features/override/msp_dashboard")
        assert resp.status_code == 200
        assert "tier:" in resp.json()["source"]

        # Should be back to tier-based (disabled for community)
        check = await auth_client.get("/api/features/check/msp_dashboard")
        assert check.json()["enabled"] is False

    @pytest.mark.asyncio
    async def test_viewer_cannot_set_override(self, viewer_client: AsyncClient):
        """Viewer role cannot set feature overrides."""
        resp = await viewer_client.put("/api/features/override", json={
            "feature": "msp_dashboard", "enabled": True,
        })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_remove_override(self, viewer_client: AsyncClient):
        """Viewer role cannot remove overrides."""
        resp = await viewer_client.delete("/api/features/override/exchange")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_overrides_show_in_features_list(self, auth_client: AsyncClient):
        """Overrides appear in the features list with source=override."""
        await auth_client.put("/api/features/override", json={
            "feature": "cleanroom", "enabled": True,
        })
        resp = await auth_client.get("/api/features")
        features = resp.json()["features"]
        assert features["cleanroom"]["enabled"] is True
        assert features["cleanroom"]["source"] == "override"

        # Clean up
        await auth_client.delete("/api/features/override/cleanroom")


# ═══════════════════════════════════════════════════════
# 5. Tier-Based Gating Logic
# ═══════════════════════════════════════════════════════

class TestTierGating:

    @pytest.mark.asyncio
    async def test_community_basic_features(self, client: AsyncClient):
        """Community tier has basic workloads and anomaly detection."""
        resp = await client.get("/api/features")
        features = resp.json()["features"]
        assert features["exchange"]["enabled"] is True
        assert features["onedrive"]["enabled"] is True
        assert features["sharepoint"]["enabled"] is True
        assert features["anomaly_detection"]["enabled"] is True
        assert features["api_access"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_community_lacks_premium(self, client: AsyncClient):
        """Community tier lacks premium features."""
        resp = await client.get("/api/features")
        features = resp.json()["features"]
        assert features["teams"]["enabled"] is False
        assert features["entra_id"]["enabled"] is False
        assert features["org_context"]["enabled"] is False
        assert features["msp_dashboard"]["enabled"] is False
        assert features["worm"]["enabled"] is False
        assert features["sso"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_limits_returned(self, client: AsyncClient):
        """Tier limits are included in response."""
        resp = await client.get("/api/features")
        limits = resp.json()["limits"]
        assert "max_objects" in limits
        assert "max_tenants" in limits
        assert "retention_days" in limits
