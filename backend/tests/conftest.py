"""Test configuration and fixtures."""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Use SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = "/tmp/shieldio-test-storage"
os.environ["DISPATCH_MODE"] = "in_process"
os.environ["ENCRYPTION_MASTER_KEY"] = "dGVzdC1tYXN0ZXIta2V5LWZvci10ZXN0aW5nLW9ubHk="

from app.database import Base, engine, async_session
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after. Clear rate limiter."""
    # Clear rate limiter between tests to prevent 429 errors
    from app.main import _rate_limit_store
    _rate_limit_store.clear()

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
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest_asyncio.fixture
async def db():
    """Database session for direct DB operations in tests."""
    async with async_session() as session:
        yield session
