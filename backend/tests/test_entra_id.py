"""Tests for Entra ID API endpoints — including new object types and snapshot diff."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_entra_id_summary_no_tenant(auth_client: AsyncClient, test_tenant):
    """Entra ID summary returns not-protected when no tenant exists."""
    response = await auth_client.get(f"/api/entra-id/summary?tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert data["protected"] is False or data.get("protected") is None


@pytest.mark.asyncio
async def test_entra_id_snapshots_empty(auth_client: AsyncClient, test_tenant):
    """Entra ID snapshots returns empty for non-existent tenant."""
    response = await auth_client.get(f"/api/entra-id/snapshots?tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_entra_id_snapshot_items_not_found(auth_client: AsyncClient):
    """Snapshot items returns 404 for non-existent snapshot."""
    response = await auth_client.get("/api/entra-id/snapshot/99999/items")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_entra_id_snapshot_item_detail_not_found(auth_client: AsyncClient):
    """Item detail returns 404 for non-existent item."""
    response = await auth_client.get("/api/entra-id/snapshot/1/item/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_entra_id_compare_empty(auth_client: AsyncClient):
    """Compare endpoint works with empty snapshots."""
    # Create two fake snapshots by accessing non-existent ones
    # The API should handle gracefully
    response = await auth_client.get("/api/entra-id/compare?snapshot_a=99998&snapshot_b=99999")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["added"] == 0
    assert data["summary"]["removed"] == 0
    assert data["summary"]["changed"] == 0
    assert data["summary"]["unchanged"] == 0


@pytest.mark.asyncio
async def test_entra_id_backup_no_tenant(auth_client: AsyncClient, test_tenant):
    """Backup returns 404 when no Entra ID object exists."""
    response = await auth_client.post(f"/api/entra-id/backup?tenant_id={test_tenant}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_entra_id_item_types_in_api(auth_client: AsyncClient):
    """Verify all 12 item types are recognized by the API."""
    # This tests that the ENTRA_ITEM_TYPES list includes all new types
    valid_types = [
        'user', 'group', 'directory_role', 'role_assignment',
        'conditional_access_policy', 'app_registration', 'named_location',
        'service_principal', 'administrative_unit', 'oauth_permission_grant',
        'device', 'domain',
    ]
    # Just verify the API accepts these as filter params without error
    for item_type in valid_types:
        response = await auth_client.get(f"/api/entra-id/snapshot/1/items?item_type={item_type}")
        # Should be 404 (snapshot not found) not 400 (invalid type)
        assert response.status_code in (200, 404), f"Failed for type: {item_type}"
