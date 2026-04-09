"""Tests for cost attribution metering service."""
import pytest
import pytest_asyncio
from datetime import date

from app.database import async_session
from app.models.usage_metric import TenantUsageMetric
from app.models.tenant import Tenant, TenantStatus


@pytest_asyncio.fixture
async def metering_tenant(db):
    """Create a tenant for metering tests."""
    tenant = Tenant(
        name="MeterTest Corp",
        ms_tenant_id="meter-test-123",
        client_id="test-client-id",
        client_secret_encrypted="test-enc",
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()
    return tenant


class TestCostBreakdownStructure:
    """Cost breakdown returns expected structure."""

    @pytest.mark.asyncio
    async def test_cost_breakdown_has_all_fields(self, db, metering_tenant):
        """get_cost_breakdown returns users, storage, api_calls, compute, total."""
        from app.services.metering import get_cost_breakdown
        breakdown = await get_cost_breakdown(metering_tenant.id)
        assert "users" in breakdown
        assert "storage" in breakdown
        assert "api_calls" in breakdown
        assert "compute" in breakdown
        assert "total" in breakdown

    @pytest.mark.asyncio
    async def test_cost_breakdown_nested_structure(self, db, metering_tenant):
        """Each cost category has count/gb and cost."""
        from app.services.metering import get_cost_breakdown
        breakdown = await get_cost_breakdown(metering_tenant.id)
        assert "count" in breakdown["users"]
        assert "cost" in breakdown["users"]
        assert "gb" in breakdown["storage"]
        assert "cost" in breakdown["storage"]
        assert "count" in breakdown["api_calls"]
        assert "minutes" in breakdown["compute"]

    @pytest.mark.asyncio
    async def test_empty_tenant_zero_cost(self, db, metering_tenant):
        """Tenant with no data has zero cost."""
        from app.services.metering import get_cost_breakdown
        breakdown = await get_cost_breakdown(metering_tenant.id)
        assert breakdown["total"] == 0.0
        assert breakdown["users"]["count"] == 0


class TestUsageMetricModel:
    """TenantUsageMetric model persists correctly."""

    @pytest.mark.asyncio
    async def test_create_usage_metric(self, db, metering_tenant):
        """Usage metric row can be created and read back."""
        metric = TenantUsageMetric(
            tenant_id=metering_tenant.id,
            metric_date=date.today(),
            graph_api_calls=150,
            backup_duration_seconds=3600,
            items_backed_up=500,
        )
        db.add(metric)
        await db.flush()

        from sqlalchemy import select
        result = await db.execute(
            select(TenantUsageMetric).where(
                TenantUsageMetric.tenant_id == metering_tenant.id
            )
        )
        row = result.scalar_one()
        assert row.graph_api_calls == 150
        assert row.backup_duration_seconds == 3600
        assert row.items_backed_up == 500
