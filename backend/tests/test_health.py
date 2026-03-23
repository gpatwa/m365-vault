"""Tests for health check and core endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root returns app info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check returns status with DB check."""
    response = await client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]


@pytest.mark.asyncio
async def test_correlation_id_header(client: AsyncClient):
    """Test that responses include correlation ID."""
    response = await client.get("/")
    assert "X-Correlation-ID" in response.headers
    assert "X-Response-Time" in response.headers


@pytest.mark.asyncio
async def test_custom_correlation_id(client: AsyncClient):
    """Test that custom correlation ID is echoed back."""
    response = await client.get("/", headers={"X-Correlation-ID": "test-123"})
    assert response.headers["X-Correlation-ID"] == "test-123"


@pytest.mark.asyncio
async def test_openapi_schema(client: AsyncClient):
    """Test OpenAPI schema is accessible."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert len(data["paths"]) > 50  # We have 97+ routes
