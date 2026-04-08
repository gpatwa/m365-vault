"""PostgreSQL test configuration — mirrors production database behavior.

Unlike conftest.py (SQLite + create_all), this uses the Docker Compose PostgreSQL
and relies on the SAME auto-migration that runs in production (main.py lifespan).
This catches migration bugs like missing columns that SQLite create_all never sees.

Usage:
    make test-pg       # Requires: make dev (docker-compose up)
    # Or manually:
    DATABASE_URL=postgresql+asyncpg://m365vault:m365vault_dev@localhost:5432/m365vault_test \
        python -m pytest tests/ -c tests/conftest_pg.py

Design:
    - Uses a SEPARATE database (m365vault_test) so dev data isn't destroyed
    - Creates the test DB if it doesn't exist
    - Runs the same auto-migration as production (via app startup)
    - Drops all tables after tests complete (clean slate each run)
    - Same fixtures as conftest.py (auth_client, viewer_client, etc.)
"""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# PostgreSQL — same driver as production, against Docker Compose DB
PG_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://m365vault:m365vault_dev@localhost:5432/m365vault_test"
)
os.environ["DATABASE_URL"] = PG_URL
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = "/tmp/kavachiq-test-storage"
os.environ["DISPATCH_MODE"] = "in_process"
os.environ["ENCRYPTION_MASTER_KEY"] = "dGVzdC1tYXN0ZXIta2V5LWZvci10ZXN0aW5nLW9ubHk="
os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "0"

from app.database import Base, engine, async_session
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_pg_database():
    """Create the test database if it doesn't exist (one-time per session)."""
    import asyncpg
    # Parse connection params from URL
    # postgresql+asyncpg://user:pass@host:port/dbname
    parts = PG_URL.replace("postgresql+asyncpg://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")
    db_name = host_db[1]

    try:
        conn = await asyncpg.connect(
            user=user_pass[0], password=user_pass[1],
            host=host_port[0], port=int(host_port[1]),
            database="postgres"  # Connect to default DB to create test DB
        )
        # Check if test DB exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
        await conn.close()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}. Run 'make dev' first.")


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after.

    Uses create_all (same as SQLite tests) BUT against PostgreSQL.
    The auto-migration in main.py lifespan ALSO runs (when app starts via
    the ASGI transport), adding any ALTER TABLE columns.
    This is the key difference: if a migration is missing, the column won't
    exist and the test will fail with ProgrammingError — just like production.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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
    if "kavachiq_session" in response.cookies:
        client.cookies.set("kavachiq_session", response.cookies["kavachiq_session"])
    yield client


@pytest_asyncio.fixture
async def viewer_client(client: AsyncClient):
    """Authenticated client with viewer role."""
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
    """Authenticated client with operator role."""
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
async def db():
    """Database session for direct DB operations in tests."""
    async with async_session() as session:
        yield session
