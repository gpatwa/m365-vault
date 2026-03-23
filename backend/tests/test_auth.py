"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration with valid data."""
    response = await client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "new@test.com",
        "password": "SecurePass1",
        "full_name": "New User",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@test.com"


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test password policy enforcement."""
    response = await client.post("/api/auth/register", json={
        "username": "weakuser",
        "email": "weak@test.com",
        "password": "short",
    })
    assert response.status_code == 400
    assert "Password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_no_uppercase(client: AsyncClient):
    """Test password requires uppercase."""
    response = await client.post("/api/auth/register", json={
        "username": "nouppuser",
        "email": "noupp@test.com",
        "password": "alllowercase1",
    })
    assert response.status_code == 400
    assert "uppercase" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_no_digit(client: AsyncClient):
    """Test password requires digit."""
    response = await client.post("/api/auth/register", json={
        "username": "nodigituser",
        "email": "nodigit@test.com",
        "password": "NoDigitHere",
    })
    assert response.status_code == 400
    assert "digit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login returns access + refresh tokens."""
    await client.post("/api/auth/register", json={
        "username": "loginuser",
        "email": "login@test.com",
        "password": "LoginPass1",
    })
    response = await client.post("/api/auth/login", data={
        "username": "loginuser",
        "password": "LoginPass1",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "loginuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password returns 401."""
    await client.post("/api/auth/register", json={
        "username": "wrongpw",
        "email": "wrongpw@test.com",
        "password": "CorrectPass1",
    })
    response = await client.post("/api/auth/login", data={
        "username": "wrongpw",
        "password": "WrongPassword1",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Test refresh token exchange."""
    await client.post("/api/auth/register", json={
        "username": "refreshuser",
        "email": "refresh@test.com",
        "password": "RefreshPass1",
    })
    login_resp = await client.post("/api/auth/login", data={
        "username": "refreshuser",
        "password": "RefreshPass1",
    })
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_me_endpoint(auth_client: AsyncClient):
    """Test /me returns current user info."""
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient):
    """Test that protected endpoints return 401 without token."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
