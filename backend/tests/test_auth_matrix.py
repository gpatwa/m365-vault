"""Comprehensive parametrized auth enforcement tests for every sidebar-reachable API endpoint.

Tests every endpoint across all 5 user roles + unauthenticated access.
Groups:
  1. ANY_AUTH — 200 for all authenticated, 401 for unauthenticated
  2. ADMIN_ONLY — 200 for admin, 403 for others, 401 for unauth
  3. MSP_PERM — 200 for admin + msp_admin, 403 for others
  4. Feature flag override — inline admin check
  5. Unauthenticated — every protected endpoint returns 401
  6. Special setup — workload enable (needs tenant seed)
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import async_session
from app.models.tenant import Tenant, TenantStatus


# ---------------------------------------------------------------------------
# Helper: create a fresh AsyncClient with a specific role token
# ---------------------------------------------------------------------------

async def _register_and_login(
    base_client: AsyncClient,
    username: str,
    role: str,
) -> str:
    """Register a user with the given role and return the JWT access token."""
    await base_client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@authmatrix.test",
        "password": "TestPass123",
        "full_name": f"Matrix {role}",
        "role": role,
    })
    resp = await base_client.post("/api/auth/login", data={
        "username": username,
        "password": "TestPass123",
    })
    return resp.json().get("access_token", "")


async def _make_client(role: str, suffix: str = "") -> AsyncClient:
    """Create an independent AsyncClient authenticated with the given role.

    Each call creates a fresh transport + client so multiple role clients can
    coexist in a single test without header collision.
    """
    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    username = f"matrix_{role}{suffix}"
    token = await _register_and_login(c, username, role)
    if token:
        c.headers["Authorization"] = f"Bearer {token}"
    return c


async def _make_unauth_client() -> AsyncClient:
    """Create an unauthenticated AsyncClient."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _seed_tenant() -> int:
    """Seed a tenant row directly via the ORM and return its ID."""
    async with async_session() as db:
        t = Tenant(
            name="AuthMatrixTenant",
            ms_tenant_id="auth-matrix-tid-001",
            client_id="test-client",
            client_secret_encrypted="enc-secret",
            status=TenantStatus.ACTIVE,
        )
        db.add(t)
        await db.flush()
        tid = t.id
        await db.commit()
    return tid


# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------

# ANY_AUTH endpoints: (method, path, json_body_or_None)
ANY_AUTH_ENDPOINTS = [
    ("GET", "/api/dashboard/summary", None),
    ("GET", "/api/dashboard/activity", None),
    ("GET", "/api/dashboard/compliance", None),
    ("GET", "/api/dashboard/unprotected", None),
    ("GET", "/api/sla-policies/", None),
    ("GET", "/api/audit/logs", None),
    ("GET", "/api/alerts/tenant?tenant_id=1", None),
    ("GET", "/api/ediscovery/status", None),
]

# ADMIN_ONLY endpoints: (method, path, json_body_or_None)
ADMIN_ONLY_ENDPOINTS = [
    ("GET", "/api/alerts/config", None),
    ("POST", "/api/alerts/test", None),
    (
        "POST",
        "/api/tenants/",
        {
            "name": "MatrixTenant",
            "ms_tenant_id": "matrix-tenant-001",
            "client_id": "cid",
            "client_secret": "csecret",
        },
    ),
    (
        "POST",
        "/api/ediscovery/search",
        {"query": "test", "tenant_id": 1},
    ),
    (
        "POST",
        "/api/ediscovery/hold",
        {
            "tenant_id": 1,
            "name": "Test Hold",
            "custodians": ["a@b.com"],
        },
    ),
    (
        "POST",
        "/api/sla-policies/",
        {
            "name": "MatrixSLA",
            "backup_frequency_hours": 24,
            "retention_days": 30,
        },
    ),
]

# MSP_PERM endpoints
MSP_PERM_ENDPOINTS = [
    ("GET", "/api/msp/overview", None),
]

# Public (no auth) endpoints — should return 200 even without a token
PUBLIC_ENDPOINTS = [
    ("GET", "/api/billing/config", None),
    ("GET", "/api/features", None),
]

# Endpoints that use get_current_user but are NOT admin-restricted (write)
ANY_AUTH_WRITE_ENDPOINTS = [
    (
        "PUT",
        "/api/alerts/tenant?tenant_id=1",
        {
            "email_recipients": "ops@test.com",
            "enabled_events": ["backup_failed"],
            "frequency": "immediate",
        },
    ),
]

# Feature-flag override (inline admin check)
FEATURE_OVERRIDE_ENDPOINT = (
    "PUT",
    "/api/features/override",
    {"feature": "test_flag", "enabled": True},
)


# ---------------------------------------------------------------------------
# Helpers for issuing requests
# ---------------------------------------------------------------------------

async def _request(client: AsyncClient, method: str, path: str, json_body=None):
    """Issue a request and return the response."""
    if method == "GET":
        return await client.get(path)
    elif method == "POST":
        return await client.post(path, json=json_body)
    elif method == "PUT":
        return await client.put(path, json=json_body)
    elif method == "DELETE":
        return await client.delete(path)
    raise ValueError(f"Unsupported method: {method}")


# ---------------------------------------------------------------------------
# 1. ANY_AUTH endpoints — all authenticated roles get 200, unauth gets 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_ENDPOINTS],
)
async def test_any_auth_admin_gets_200(auth_client: AsyncClient, method, path, body):
    """Admin should be able to access any-auth endpoints."""
    resp = await _request(auth_client, method, path, body)
    assert resp.status_code == 200, f"Admin got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_ENDPOINTS],
)
async def test_any_auth_viewer_gets_200(viewer_client: AsyncClient, method, path, body):
    """Viewer should be able to access any-auth endpoints."""
    resp = await _request(viewer_client, method, path, body)
    assert resp.status_code == 200, f"Viewer got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_ENDPOINTS],
)
async def test_any_auth_operator_gets_200(operator_client: AsyncClient, method, path, body):
    """Operator should be able to access any-auth endpoints."""
    resp = await _request(operator_client, method, path, body)
    assert resp.status_code == 200, f"Operator got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_ENDPOINTS],
)
async def test_any_auth_msp_admin_gets_200(msp_admin_client: AsyncClient, method, path, body):
    """MSP admin should be able to access any-auth endpoints."""
    resp = await _request(msp_admin_client, method, path, body)
    assert resp.status_code == 200, f"MSP admin got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_ENDPOINTS],
)
async def test_any_auth_restore_operator_gets_200(restore_operator_client: AsyncClient, method, path, body):
    """Restore operator should be able to access any-auth endpoints."""
    resp = await _request(restore_operator_client, method, path, body)
    assert resp.status_code == 200, f"Restore operator got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_ENDPOINTS],
)
async def test_any_auth_unauth_gets_401(client: AsyncClient, method, path, body):
    """Unauthenticated requests to any-auth endpoints should get 401."""
    resp = await _request(client, method, path, body)
    assert resp.status_code == 401, f"Unauth got {resp.status_code} on {method} {path} (expected 401): {resp.text}"


# ---------------------------------------------------------------------------
# 2. ADMIN_ONLY endpoints — 200 for admin, 403 for others, 401 for unauth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ADMIN_ONLY_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ONLY_ENDPOINTS],
)
async def test_admin_only_admin_allowed(auth_client: AsyncClient, method, path, body):
    """Admin should be allowed on admin-only endpoints."""
    resp = await _request(auth_client, method, path, body)
    # Accept 200 or other success-ish codes (some POST may return 201 or 4xx for
    # domain reasons like "feature not enabled" or "duplicate"); the key is NOT 401/403.
    # Exception: eDiscovery endpoints may return 403 with "Enterprise plan" — that is
    # a feature-flag gate, not an auth rejection.
    assert resp.status_code != 401, (
        f"Admin got 401 on {method} {path}: {resp.text}"
    )
    if resp.status_code == 403:
        # Only acceptable if it is a domain/feature-flag rejection, not auth
        detail = resp.json().get("detail", "")
        assert "requires" in detail.lower() or "enterprise" in detail.lower(), (
            f"Admin got auth-level 403 on {method} {path}: {resp.text}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ADMIN_ONLY_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ONLY_ENDPOINTS],
)
async def test_admin_only_viewer_blocked(viewer_client: AsyncClient, method, path, body):
    """Viewer should be blocked (403) on admin-only endpoints."""
    resp = await _request(viewer_client, method, path, body)
    assert resp.status_code == 403, (
        f"Viewer got {resp.status_code} on {method} {path} (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ADMIN_ONLY_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ONLY_ENDPOINTS],
)
async def test_admin_only_operator_blocked(operator_client: AsyncClient, method, path, body):
    """Operator should be blocked (403) on admin-only endpoints."""
    resp = await _request(operator_client, method, path, body)
    assert resp.status_code == 403, (
        f"Operator got {resp.status_code} on {method} {path} (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ADMIN_ONLY_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ONLY_ENDPOINTS],
)
async def test_admin_only_msp_admin_blocked(msp_admin_client: AsyncClient, method, path, body):
    """MSP admin should be blocked (403) on admin-only endpoints."""
    resp = await _request(msp_admin_client, method, path, body)
    assert resp.status_code == 403, (
        f"MSP admin got {resp.status_code} on {method} {path} (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ADMIN_ONLY_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ONLY_ENDPOINTS],
)
async def test_admin_only_restore_operator_blocked(restore_operator_client: AsyncClient, method, path, body):
    """Restore operator should be blocked (403) on admin-only endpoints."""
    resp = await _request(restore_operator_client, method, path, body)
    assert resp.status_code == 403, (
        f"Restore operator got {resp.status_code} on {method} {path} (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ADMIN_ONLY_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ADMIN_ONLY_ENDPOINTS],
)
async def test_admin_only_unauth_gets_401(client: AsyncClient, method, path, body):
    """Unauthenticated requests to admin-only endpoints should get 401."""
    resp = await _request(client, method, path, body)
    assert resp.status_code == 401, (
        f"Unauth got {resp.status_code} on {method} {path} (expected 401): {resp.text}"
    )


# ---------------------------------------------------------------------------
# 3. MSP_PERM endpoints — 200 for admin + msp_admin, 403 for others
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    MSP_PERM_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in MSP_PERM_ENDPOINTS],
)
async def test_msp_perm_admin_allowed(auth_client: AsyncClient, method, path, body):
    """Admin should be allowed on MSP endpoints."""
    resp = await _request(auth_client, method, path, body)
    assert resp.status_code == 200, f"Admin got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    MSP_PERM_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in MSP_PERM_ENDPOINTS],
)
async def test_msp_perm_msp_admin_allowed(msp_admin_client: AsyncClient, method, path, body):
    """MSP admin should be allowed on MSP endpoints."""
    resp = await _request(msp_admin_client, method, path, body)
    assert resp.status_code == 200, f"MSP admin got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    MSP_PERM_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in MSP_PERM_ENDPOINTS],
)
async def test_msp_perm_viewer_blocked(viewer_client: AsyncClient, method, path, body):
    """Viewer should be blocked (403) on MSP endpoints."""
    resp = await _request(viewer_client, method, path, body)
    assert resp.status_code == 403, f"Viewer got {resp.status_code} on {method} {path} (expected 403): {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    MSP_PERM_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in MSP_PERM_ENDPOINTS],
)
async def test_msp_perm_operator_blocked(operator_client: AsyncClient, method, path, body):
    """Operator should be blocked (403) on MSP endpoints."""
    resp = await _request(operator_client, method, path, body)
    assert resp.status_code == 403, f"Operator got {resp.status_code} on {method} {path} (expected 403): {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    MSP_PERM_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in MSP_PERM_ENDPOINTS],
)
async def test_msp_perm_restore_operator_blocked(restore_operator_client: AsyncClient, method, path, body):
    """Restore operator should be blocked (403) on MSP endpoints."""
    resp = await _request(restore_operator_client, method, path, body)
    assert resp.status_code == 403, (
        f"Restore operator got {resp.status_code} on {method} {path} (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    MSP_PERM_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in MSP_PERM_ENDPOINTS],
)
async def test_msp_perm_unauth_gets_401(client: AsyncClient, method, path, body):
    """Unauthenticated requests to MSP endpoints should get 401."""
    resp = await _request(client, method, path, body)
    assert resp.status_code == 401, f"Unauth got {resp.status_code} on {method} {path} (expected 401): {resp.text}"


# ---------------------------------------------------------------------------
# 4. Public endpoints — 200 for both authenticated AND unauthenticated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    PUBLIC_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in PUBLIC_ENDPOINTS],
)
async def test_public_endpoints_unauth(client: AsyncClient, method, path, body):
    """Public endpoints should be accessible without authentication."""
    resp = await _request(client, method, path, body)
    assert resp.status_code == 200, (
        f"Unauth got {resp.status_code} on public {method} {path} (expected 200): {resp.text}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    PUBLIC_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in PUBLIC_ENDPOINTS],
)
async def test_public_endpoints_auth(auth_client: AsyncClient, method, path, body):
    """Public endpoints should also work when authenticated."""
    resp = await _request(auth_client, method, path, body)
    assert resp.status_code == 200, (
        f"Admin got {resp.status_code} on public {method} {path} (expected 200): {resp.text}"
    )


# ---------------------------------------------------------------------------
# 5. ANY_AUTH write endpoints — all authenticated roles allowed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_WRITE_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_WRITE_ENDPOINTS],
)
async def test_any_auth_write_admin_allowed(auth_client: AsyncClient, method, path, body):
    """Admin can access any-auth write endpoints."""
    resp = await _request(auth_client, method, path, body)
    assert resp.status_code == 200, f"Admin got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_WRITE_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_WRITE_ENDPOINTS],
)
async def test_any_auth_write_viewer_allowed(viewer_client: AsyncClient, method, path, body):
    """Viewer can access any-auth write endpoints (PUT alerts/tenant uses get_current_user)."""
    resp = await _request(viewer_client, method, path, body)
    assert resp.status_code == 200, f"Viewer got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_WRITE_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_WRITE_ENDPOINTS],
)
async def test_any_auth_write_operator_allowed(operator_client: AsyncClient, method, path, body):
    """Operator can access any-auth write endpoints."""
    resp = await _request(operator_client, method, path, body)
    assert resp.status_code == 200, f"Operator got {resp.status_code} on {method} {path}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ANY_AUTH_WRITE_ENDPOINTS,
    ids=[f"{m} {p.split('?')[0]}" for m, p, _ in ANY_AUTH_WRITE_ENDPOINTS],
)
async def test_any_auth_write_unauth_gets_401(client: AsyncClient, method, path, body):
    """Unauthenticated requests to any-auth write endpoints get 401."""
    resp = await _request(client, method, path, body)
    assert resp.status_code == 401, (
        f"Unauth got {resp.status_code} on {method} {path} (expected 401): {resp.text}"
    )


# ---------------------------------------------------------------------------
# 6. Feature flag override — inline admin check (not require_role)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feature_override_admin_allowed(auth_client: AsyncClient):
    """Admin can set feature flag overrides."""
    method, path, body = FEATURE_OVERRIDE_ENDPOINT
    resp = await _request(auth_client, method, path, body)
    assert resp.status_code == 200, f"Admin got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_feature_override_viewer_blocked(viewer_client: AsyncClient):
    """Viewer is blocked (403) from setting feature flag overrides."""
    method, path, body = FEATURE_OVERRIDE_ENDPOINT
    resp = await _request(viewer_client, method, path, body)
    assert resp.status_code == 403, f"Viewer got {resp.status_code} (expected 403): {resp.text}"


@pytest.mark.asyncio
async def test_feature_override_operator_blocked(operator_client: AsyncClient):
    """Operator is blocked (403) from setting feature flag overrides."""
    method, path, body = FEATURE_OVERRIDE_ENDPOINT
    resp = await _request(operator_client, method, path, body)
    assert resp.status_code == 403, f"Operator got {resp.status_code} (expected 403): {resp.text}"


@pytest.mark.asyncio
async def test_feature_override_msp_admin_blocked(msp_admin_client: AsyncClient):
    """MSP admin is blocked (403) from setting feature flag overrides."""
    method, path, body = FEATURE_OVERRIDE_ENDPOINT
    resp = await _request(msp_admin_client, method, path, body)
    assert resp.status_code == 403, f"MSP admin got {resp.status_code} (expected 403): {resp.text}"


@pytest.mark.asyncio
async def test_feature_override_restore_operator_blocked(restore_operator_client: AsyncClient):
    """Restore operator is blocked (403) from setting feature flag overrides."""
    method, path, body = FEATURE_OVERRIDE_ENDPOINT
    resp = await _request(restore_operator_client, method, path, body)
    assert resp.status_code == 403, f"Restore operator got {resp.status_code} (expected 403): {resp.text}"


@pytest.mark.asyncio
async def test_feature_override_unauth_gets_401(client: AsyncClient):
    """Unauthenticated requests to feature override get 401."""
    method, path, body = FEATURE_OVERRIDE_ENDPOINT
    resp = await _request(client, method, path, body)
    assert resp.status_code == 401, f"Unauth got {resp.status_code} (expected 401): {resp.text}"


# ---------------------------------------------------------------------------
# 7. Unauthenticated blanket test — every protected endpoint returns 401
# ---------------------------------------------------------------------------

ALL_PROTECTED_ENDPOINTS = (
    ANY_AUTH_ENDPOINTS
    + ADMIN_ONLY_ENDPOINTS
    + MSP_PERM_ENDPOINTS
    + ANY_AUTH_WRITE_ENDPOINTS
    + [FEATURE_OVERRIDE_ENDPOINT]
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    ALL_PROTECTED_ENDPOINTS,
    ids=[f"unauth {m} {p.split('?')[0]}" for m, p, _ in ALL_PROTECTED_ENDPOINTS],
)
async def test_unauthenticated_blocked(client: AsyncClient, method, path, body):
    """Every protected endpoint must return 401 for unauthenticated requests."""
    resp = await _request(client, method, path, body)
    assert resp.status_code == 401, (
        f"Unauth got {resp.status_code} on {method} {path} (expected 401): {resp.text}"
    )


# ---------------------------------------------------------------------------
# 8. Workload enable — admin-only with tenant seed (special setup)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workload_enable_admin_allowed(auth_client: AsyncClient):
    """Admin can enable workloads on a tenant."""
    tid = await _seed_tenant()
    resp = await auth_client.post(
        f"/api/tenants/{tid}/workloads",
        json={"workloads": ["exchange"]},
    )
    # Accept success or domain-level rejection (e.g., 403 from subscription gate
    # is acceptable — we just verify it is NOT a 401 auth rejection)
    assert resp.status_code != 401, (
        f"Admin got 401 on workload enable (auth should pass): {resp.text}"
    )
    # Should not be a role-based 403 either; if 403 it should be subscription-related
    if resp.status_code == 403:
        assert "subscription" in resp.text.lower() or "tier" in resp.text.lower(), (
            f"Admin got 403 that appears role-based (not subscription): {resp.text}"
        )


@pytest.mark.asyncio
async def test_workload_enable_viewer_blocked(viewer_client: AsyncClient):
    """Viewer is blocked (403) from enabling workloads."""
    tid = await _seed_tenant()
    resp = await viewer_client.post(
        f"/api/tenants/{tid}/workloads",
        json={"workloads": ["exchange"]},
    )
    assert resp.status_code == 403, (
        f"Viewer got {resp.status_code} on workload enable (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
async def test_workload_enable_operator_blocked(operator_client: AsyncClient):
    """Operator is blocked (403) from enabling workloads."""
    tid = await _seed_tenant()
    resp = await operator_client.post(
        f"/api/tenants/{tid}/workloads",
        json={"workloads": ["exchange"]},
    )
    assert resp.status_code == 403, (
        f"Operator got {resp.status_code} on workload enable (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
async def test_workload_enable_msp_admin_blocked(msp_admin_client: AsyncClient):
    """MSP admin is blocked (403) from enabling workloads (admin-only)."""
    tid = await _seed_tenant()
    resp = await msp_admin_client.post(
        f"/api/tenants/{tid}/workloads",
        json={"workloads": ["exchange"]},
    )
    assert resp.status_code == 403, (
        f"MSP admin got {resp.status_code} on workload enable (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
async def test_workload_enable_restore_operator_blocked(restore_operator_client: AsyncClient):
    """Restore operator is blocked (403) from enabling workloads."""
    tid = await _seed_tenant()
    resp = await restore_operator_client.post(
        f"/api/tenants/{tid}/workloads",
        json={"workloads": ["exchange"]},
    )
    assert resp.status_code == 403, (
        f"Restore operator got {resp.status_code} on workload enable (expected 403): {resp.text}"
    )


@pytest.mark.asyncio
async def test_workload_enable_unauth_gets_401(client: AsyncClient):
    """Unauthenticated request to workload enable returns 401."""
    tid = await _seed_tenant()
    resp = await client.post(
        f"/api/tenants/{tid}/workloads",
        json={"workloads": ["exchange"]},
    )
    assert resp.status_code == 401, (
        f"Unauth got {resp.status_code} on workload enable (expected 401): {resp.text}"
    )


# ---------------------------------------------------------------------------
# 9. Cross-role matrix — compact parametrized test covering all combinations
# ---------------------------------------------------------------------------

# Each tuple: (description, method, path, body, allowed_roles, auth_required)
# allowed_roles = set of role strings that should NOT get 403
CROSS_ROLE_MATRIX = [
    # ANY_AUTH read endpoints
    ("dashboard summary", "GET", "/api/dashboard/summary", None,
     {"admin", "msp_admin", "operator", "restore_operator", "viewer"}, True),
    ("audit logs", "GET", "/api/audit/logs", None,
     {"admin", "msp_admin", "operator", "restore_operator", "viewer"}, True),
    ("sla policies list", "GET", "/api/sla-policies/", None,
     {"admin", "msp_admin", "operator", "restore_operator", "viewer"}, True),
    ("ediscovery status", "GET", "/api/ediscovery/status", None,
     {"admin", "msp_admin", "operator", "restore_operator", "viewer"}, True),
    # ADMIN_ONLY
    ("global alert config", "GET", "/api/alerts/config", None,
     {"admin"}, True),
    ("test alert", "POST", "/api/alerts/test", None,
     {"admin"}, True),
    # MSP_PERM
    ("msp overview", "GET", "/api/msp/overview", None,
     {"admin", "msp_admin"}, True),
    # Feature override (inline admin check)
    ("feature override", "PUT", "/api/features/override",
     {"feature": "cross_flag", "enabled": True},
     {"admin"}, True),
    # Public
    ("billing config", "GET", "/api/billing/config", None,
     {"admin", "msp_admin", "operator", "restore_operator", "viewer"}, False),
    ("feature flags", "GET", "/api/features", None,
     {"admin", "msp_admin", "operator", "restore_operator", "viewer"}, False),
]

ALL_ROLES = ["admin", "viewer", "operator", "msp_admin", "restore_operator"]


def _matrix_ids():
    """Generate test IDs for the cross-role matrix."""
    ids = []
    for desc, method, path, body, allowed, auth_required in CROSS_ROLE_MATRIX:
        for role in ALL_ROLES:
            expected = "allowed" if role in allowed else "blocked"
            ids.append(f"{desc} [{role}={expected}]")
    return ids


def _matrix_params():
    """Expand the matrix into individual (desc, method, path, body, role, expected) tuples."""
    params = []
    for desc, method, path, body, allowed, auth_required in CROSS_ROLE_MATRIX:
        for role in ALL_ROLES:
            expected_blocked = role not in allowed and auth_required
            params.append((desc, method, path, body, role, expected_blocked))
    return params


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "desc,method,path,body,role,expected_blocked",
    _matrix_params(),
    ids=_matrix_ids(),
)
async def test_cross_role_matrix(desc, method, path, body, role, expected_blocked):
    """Cross-role matrix: verify each role gets the right status on each endpoint."""
    c = await _make_client(role, suffix=f"_{desc.replace(' ', '_')[:20]}")
    try:
        resp = await _request(c, method, path, body)
        if expected_blocked:
            assert resp.status_code == 403, (
                f"[{desc}] {role} got {resp.status_code} (expected 403): {resp.text}"
            )
        else:
            assert resp.status_code != 403, (
                f"[{desc}] {role} got 403 but should be allowed: {resp.text}"
            )
            assert resp.status_code != 401, (
                f"[{desc}] {role} got 401 but should be authenticated: {resp.text}"
            )
    finally:
        await c.aclose()


# ---------------------------------------------------------------------------
# 10. Unauthenticated cross-check for auth-required endpoints
# ---------------------------------------------------------------------------

AUTH_REQUIRED_MATRIX = [
    (desc, method, path, body)
    for desc, method, path, body, _, auth_required in CROSS_ROLE_MATRIX
    if auth_required
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "desc,method,path,body",
    AUTH_REQUIRED_MATRIX,
    ids=[f"unauth-{desc}" for desc, *_ in AUTH_REQUIRED_MATRIX],
)
async def test_cross_role_unauth_blocked(desc, method, path, body):
    """Unauthenticated access to auth-required endpoints returns 401."""
    c = await _make_unauth_client()
    try:
        resp = await _request(c, method, path, body)
        assert resp.status_code == 401, (
            f"[{desc}] Unauth got {resp.status_code} (expected 401): {resp.text}"
        )
    finally:
        await c.aclose()
