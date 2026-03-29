"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "username": "newuser", "email": "new@test.com",
        "password": "SecurePass1", "full_name": "New User",
    })
    assert response.status_code == 200
    assert response.json()["username"] == "newuser"


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    response = await client.post("/api/auth/register", json={
        "username": "weakuser", "email": "weak@test.com", "password": "short",
    })
    assert response.status_code == 422
    body = response.json()
    # Structured error format: {"error": {"code": ..., "detail": ...}}
    detail = body.get("error", {}).get("detail", body.get("detail", ""))
    assert "Password" in detail


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "loginuser", "email": "login@test.com", "password": "LoginPass1",
    })
    response = await client.post("/api/auth/login", data={
        "username": "loginuser", "password": "LoginPass1",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "wrongpw", "email": "wrongpw@test.com", "password": "CorrectPass1",
    })
    response = await client.post("/api/auth/login", data={
        "username": "wrongpw", "password": "WrongPassword1",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "refreshuser", "email": "refresh@test.com", "password": "RefreshPass1",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "refreshuser", "password": "RefreshPass1",
    })
    response = await client.post("/api/auth/refresh", json={
        "refresh_token": login_resp.json()["refresh_token"],
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_me_endpoint(auth_client: AsyncClient):
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "testadmin"


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sso_config(client: AsyncClient):
    response = await client.get("/api/auth/sso/config")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
