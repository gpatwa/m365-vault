"""Tests for Prometheus observability — metrics endpoint and instrumentation."""
import pytest
import pytest_asyncio
from prometheus_client import REGISTRY, CollectorRegistry


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    """Reset prometheus metrics between tests to avoid duplicate registration."""
    # Prometheus client uses a global registry. We can't easily reset it,
    # but we can verify metrics are present.
    yield


class TestPathNormalization:
    """Path normalization prevents label cardinality explosion."""

    def test_numeric_ids_replaced(self):
        from app.observability import normalize_path
        assert normalize_path("/api/jobs/backup/123") == "/api/jobs/backup/{id}"

    def test_nested_ids_replaced(self):
        from app.observability import normalize_path
        assert normalize_path("/api/tenants/5/workloads") == "/api/tenants/{id}/workloads"

    def test_health_unchanged(self):
        from app.observability import normalize_path
        assert normalize_path("/health") == "/health"

    def test_metrics_unchanged(self):
        from app.observability import normalize_path
        assert normalize_path("/metrics") == "/metrics"

    def test_unknown_deep_paths_truncated(self):
        from app.observability import normalize_path
        result = normalize_path("/some/unknown/very/deep/path/here")
        parts = result.split("/")
        assert len(parts) <= 5  # Truncated to prevent cardinality

    def test_no_cardinality_explosion(self):
        """100 requests with different IDs produce few unique path labels."""
        from app.observability import normalize_path
        paths = set()
        for i in range(100):
            paths.add(normalize_path(f"/api/jobs/backup/{i}"))
        assert len(paths) == 1  # All normalize to same template


class TestMetricsEndpoint:
    """Prometheus /metrics endpoint returns valid format."""

    @pytest.mark.asyncio
    async def test_metrics_returns_prometheus_format(self, client):
        """GET /metrics returns text with HELP/TYPE headers."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        text = response.text
        assert "# HELP" in text
        assert "# TYPE" in text

    @pytest.mark.asyncio
    async def test_metrics_includes_http_histogram(self, client):
        """After a request, HTTP request duration histogram has data."""
        # Make a request first to populate metrics
        await client.get("/health")
        response = await client.get("/metrics")
        text = response.text
        assert "kavachiq_http_request_duration_seconds" in text

    @pytest.mark.asyncio
    async def test_metrics_includes_request_counter(self, client):
        """After requests, the request counter is incremented."""
        await client.get("/health")
        await client.get("/health")
        response = await client.get("/metrics")
        text = response.text
        assert "kavachiq_http_requests_total" in text

    @pytest.mark.asyncio
    async def test_metrics_content_type(self, client):
        """Metrics endpoint returns correct content type for Prometheus scraping."""
        response = await client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")
