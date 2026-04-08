"""Test configuration and fixtures."""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Use SQLite by default, but allow PostgreSQL override for make test-pg.
# When DATABASE_URL_OVERRIDE is set, use it instead of SQLite.
# This catches migration bugs that SQLite's create_all never sees.
if "DATABASE_URL_OVERRIDE" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_OVERRIDE"]
else:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = "/tmp/kavachiq-test-storage"
os.environ["DISPATCH_MODE"] = "in_process"
os.environ["ENCRYPTION_MASTER_KEY"] = "dGVzdC1tYXN0ZXIta2V5LWZvci10ZXN0aW5nLW9ubHk="
os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "0"  # Disable rate limiting in tests

from app.database import Base, engine, async_session
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after.

    Disposes engine after teardown to close all asyncpg connections cleanly.
    Without this, PostgreSQL tests get 'Event loop is closed' errors because
    the connection pool holds stale connections between test functions.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Close all pool connections — prevents asyncpg event loop errors in PG mode
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    """Authenticated client with admin token."""
    await client.post("/api/auth/register", json={
        "username": "testadmin",
        "email": "admin@test.com",
        "password": "TestPass123",
        "full_name": "Test Admin",
        "role": "admin",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testadmin",
        "password": "TestPass123",
    })
    data = response.json()
    token = data.get("access_token", "")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    # Also set cookie if present (BFF mode)
    if "kavachiq_session" in response.cookies:
        client.cookies.set("kavachiq_session", response.cookies["kavachiq_session"])
    yield client


@pytest_asyncio.fixture
async def msp_admin_client(client: AsyncClient):
    """Authenticated client with msp_admin role."""
    await client.post("/api/auth/register", json={
        "username": "testmsp",
        "email": "msp@test.com",
        "password": "TestPass123",
        "full_name": "Test MSP Admin",
        "role": "msp_admin",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testmsp",
        "password": "TestPass123",
    })
    data = response.json()
    token = data.get("access_token", "")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    if "kavachiq_session" in response.cookies:
        client.cookies.set("kavachiq_session", response.cookies["kavachiq_session"])
    yield client


@pytest_asyncio.fixture
async def viewer_client(client: AsyncClient):
    """Authenticated client with viewer role (should be blocked from MSP)."""
    await client.post("/api/auth/register", json={
        "username": "testviewer",
        "email": "viewer@test.com",
        "password": "TestPass123",
        "full_name": "Test Viewer",
        "role": "viewer",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testviewer",
        "password": "TestPass123",
    })
    data = response.json()
    token = data.get("access_token", "")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    if "kavachiq_session" in response.cookies:
        client.cookies.set("kavachiq_session", response.cookies["kavachiq_session"])
    yield client


@pytest_asyncio.fixture
async def operator_client(client: AsyncClient):
    """Authenticated client with operator role (backup operations, not admin)."""
    await client.post("/api/auth/register", json={
        "username": "testoperator",
        "email": "operator@test.com",
        "password": "TestPass123",
        "full_name": "Test Operator",
        "role": "operator",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testoperator",
        "password": "TestPass123",
    })
    data = response.json()
    token = data.get("access_token", "")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    if "kavachiq_session" in response.cookies:
        client.cookies.set("kavachiq_session", response.cookies["kavachiq_session"])
    yield client


@pytest_asyncio.fixture
async def restore_operator_client(client: AsyncClient):
    """Authenticated client with restore_operator role (can restore, not admin)."""
    await client.post("/api/auth/register", json={
        "username": "testrestoreop",
        "email": "restoreop@test.com",
        "password": "TestPass123",
        "full_name": "Test Restore Operator",
        "role": "restore_operator",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testrestoreop",
        "password": "TestPass123",
    })
    data = response.json()
    token = data.get("access_token", "")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    if "kavachiq_session" in response.cookies:
        client.cookies.set("kavachiq_session", response.cookies["kavachiq_session"])
    yield client


@pytest_asyncio.fixture
async def db():
    """Database session for direct DB operations in tests."""
    async with async_session() as session:
        yield session
