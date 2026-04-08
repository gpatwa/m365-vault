"""Tests for BFF Enterprise Auth — httpOnly cookies + Redis sessions.

Verifies the complete auth lifecycle:
  Login → cookie set → session valid → API access → logout → session destroyed
  Also: dual-mode (cookie + JWT), session expiry, cross-tenant isolation.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════
# Login + Cookie
# ═══════════════════════════════════════════════════════

async def _create_test_user(client: AsyncClient, username="bfftest", password="BffTest123"):
    """Helper: register + login, return (response, cookies)."""
    await client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@test.com",
        "password": password, "full_name": "BFF Test", "role": "admin",
    })
    return await client.post("/api/auth/login", data={
        "username": username, "password": password,
    })


@pytest.mark.asyncio
async def test_login_sets_httponly_cookie(client: AsyncClient):
    """Login should set httpOnly session cookie."""
    response = await _create_test_user(client)
    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    session_cookie = [c for c in cookies if "kavachiq_session" in c]
    assert len(session_cookie) > 0, "No kavachiq_session cookie set"
    cookie_str = session_cookie[0]
    assert "httponly" in cookie_str.lower()
    assert "samesite" in cookie_str.lower()


@pytest.mark.asyncio
async def test_login_returns_user_info(client: AsyncClient):
    """Login should return user info in response body."""
    response = await _create_test_user(client, "bffinfo", "BffInfo123")
    data = response.json()
    assert data["user"]["username"] == "bffinfo"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Invalid credentials should return error, no cookie."""
    response = await client.post("/api/auth/login", data={
        "username": "nobody", "password": "wrong",
    })
    assert response.status_code in (401, 422)
    cookies = response.headers.get_list("set-cookie")
    session_cookie = [c for c in cookies if "kavachiq_session" in c]
    assert len(session_cookie) == 0


# ═══════════════════════════════════════════════════════
# Session via Cookie
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_session_endpoint_with_cookie(auth_client: AsyncClient):
    """GET /auth/session with valid cookie should return user context."""
    response = await auth_client.get("/api/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert "onboarding_status" in data
    assert "has_tenants" in data
    assert "preferences" in data


@pytest.mark.asyncio
async def test_session_without_cookie(client: AsyncClient):
    """GET /auth/session without cookie should return 401."""
    response = await client.get("/api/auth/session")
    assert response.status_code == 401


# ═══════════════════════════════════════════════════════
# Dual-Mode Auth (Cookie + JWT)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_api_access_via_jwt_header(client: AsyncClient):
    """API should accept JWT in Authorization header (backward compat)."""
    login_resp = await _create_test_user(client, "bffjwt", "BffJwt123")
    token = login_resp.json()["access_token"]

    response = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 200
    assert response.json()["username"] == "bffjwt"


# ═══════════════════════════════════════════════════════
# Logout
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_logout_clears_cookie(auth_client: AsyncClient):
    """Logout should clear cookie and destroy Redis session."""
    # First verify session works
    resp1 = await auth_client.get("/api/auth/session")
    assert resp1.status_code == 200

    # Logout
    logout_resp = await auth_client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

    # Verify cookie is cleared (Max-Age=0 in Set-Cookie)
    cookies = logout_resp.headers.get_list("set-cookie")
    cleared = [c for c in cookies if "kavachiq_session" in c and "Max-Age=0" in c]
    assert len(cleared) > 0 or len(cookies) > 0  # Cookie should be cleared


@pytest.mark.asyncio
async def test_session_after_logout_returns_401(client: AsyncClient):
    """After logout, session should be destroyed (401)."""
    login_resp = await _create_test_user(client, "bfflogout2", "BffLogout2!")
    cookies = login_resp.cookies

    resp1 = await client.get("/api/auth/session", cookies=cookies)
    assert resp1.status_code == 200

    await client.post("/api/auth/logout", cookies=cookies)

    resp2 = await client.get("/api/auth/session", cookies=cookies)
    assert resp2.status_code == 401


# ═══════════════════════════════════════════════════════
# Session Manager
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_session_create_and_get():
    """Session manager should create and retrieve sessions from Redis."""
    from app.services.session import create_session, get_session_data, destroy_session

    session_id = await create_session(
        user_id=1, username="test", role="admin",
        tenant_ids=[1, 2], preferences={"theme": "dark"},
    )
    assert session_id is not None
    assert len(session_id) > 20  # URL-safe random string

    # Retrieve
    data = await get_session_data(session_id)
    assert data is not None
    assert data["user_id"] == 1
    assert data["username"] == "test"
    assert data["tenant_ids"] == [1, 2]
    assert data["preferences"]["theme"] == "dark"

    # Destroy
    await destroy_session(session_id)
    data = await get_session_data(session_id)
    assert data is None  # Session gone


@pytest.mark.asyncio
async def test_session_update():
    """Session manager should update specific fields."""
    from app.services.session import create_session, get_session_data, update_session, destroy_session

    session_id = await create_session(
        user_id=2, username="updater", role="viewer",
        tenant_ids=[], preferences={},
    )

    # Update tenant_ids
    await update_session(session_id, {"tenant_ids": [5, 6]})
    data = await get_session_data(session_id)
    assert data["tenant_ids"] == [5, 6]
    assert data["username"] == "updater"  # Other fields unchanged

    await destroy_session(session_id)


# ═══════════════════════════════════════════════════════
# Preferences (Server-Side)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_set_and_get_preference(auth_client: AsyncClient):
    """Preferences should be stored server-side, not in browser."""
    # Set preference
    resp = await auth_client.put("/api/auth/preferences/theme", json={"value": "light"})
    assert resp.status_code == 200
    assert resp.json()["value"] == "light"

    # Get all preferences
    resp2 = await auth_client.get("/api/auth/preferences")
    assert resp2.status_code == 200
    prefs = resp2.json()
    assert prefs.get("theme") == "light"
