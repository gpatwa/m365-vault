"""Tests for Teams API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_teams_list_empty(auth_client: AsyncClient, test_tenant):
    """Teams list returns empty when no teams discovered."""
    response = await auth_client.get(f"/api/teams/teams?tenant_id={test_tenant}")
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_teams_backup_all_no_teams(auth_client: AsyncClient, test_tenant):
    """Backup all returns 404 when no teams exist."""
    response = await auth_client.post(f"/api/teams/backup-all?tenant_id={test_tenant}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_teams_backup_single_not_found(auth_client: AsyncClient):
    """Backup single team returns 404 for non-existent team."""
    response = await auth_client.post("/api/teams/teams/99999/backup")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_teams_snapshots_not_found(auth_client: AsyncClient):
    """Snapshots for non-existent team returns empty list, not 404."""
    response = await auth_client.get("/api/teams/teams/99999/snapshots")
    assert response.status_code == 200  # Empty list, not 404


@pytest.mark.asyncio
async def test_teams_chats_list(auth_client: AsyncClient, test_tenant):
    """Chats endpoint returns teams/chats breakdown."""
    response = await auth_client.get(f"/api/teams/chats?tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
    assert "chats" in data
    assert data["teams"]["total"] == 0
    assert data["chats"]["total"] == 0


@pytest.mark.asyncio
async def test_teams_chat_messages_not_found(auth_client: AsyncClient):
    """Chat messages returns 404 for non-existent user object."""
    response = await auth_client.get("/api/teams/chats/99999/messages")
    assert response.status_code == 404
