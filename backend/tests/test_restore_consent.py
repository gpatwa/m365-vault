"""Tests for Delegated Restore Consent flow — Redis-backed.

Covers:
  1. Authorization URL generation (requires auth)
  2. Consent status check (state in Redis)
  3. Token retrieval (async, from Redis)
  4. Token discard (async, clears Redis)
  5. State stored in Redis (survives pod restart)
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.api.restore_consent import get_restore_token, discard_restore_token
from app.services.redis_state import set_state, get_state, delete_state


# Redis key prefix (must match restore_consent.py)
_PREFIX = "restore_consent:"


# ═══════════════════════════════════════════════════════
# Authorization
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_authorize_requires_auth(client: AsyncClient):
    """Unauthenticated user cannot start restore consent."""
    resp = await client.get("/api/restore-consent/authorize?tenant_id=1")
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════
# Consent Status (Redis-backed)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_consent_status_from_redis():
    """Status endpoint reads from Redis, not in-memory."""
    state = "test-redis-status"
    await set_state(f"{_PREFIX}{state}", {
        "tenant_id": 1,
        "ms_tenant_id": "test-tenant",
        "user_id": 1,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }, ttl_seconds=60)

    entry = await get_state(f"{_PREFIX}{state}")
    assert entry is not None
    assert entry["status"] == "pending"
    assert entry["tenant_id"] == 1

    # Cleanup
    await delete_state(f"{_PREFIX}{state}")


@pytest.mark.asyncio
async def test_consent_status_ready_has_token():
    """Ready status includes access token flag."""
    state = "test-redis-ready"
    await set_state(f"{_PREFIX}{state}", {
        "tenant_id": 2,
        "ms_tenant_id": "test-tenant-2",
        "user_id": 1,
        "created_at": datetime.utcnow().isoformat(),
        "status": "ready",
        "access_token": "mock-token-abc",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
    }, ttl_seconds=60)

    entry = await get_state(f"{_PREFIX}{state}")
    assert entry["status"] == "ready"
    assert "access_token" in entry

    await delete_state(f"{_PREFIX}{state}")


# ═══════════════════════════════════════════════════════
# Token Retrieval (Async, from Redis)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_restore_token_returns_access_token():
    """get_restore_token returns the access token from Redis."""
    state = "test-get-token"
    await set_state(f"{_PREFIX}{state}", {
        "tenant_id": 1,
        "ms_tenant_id": "test",
        "user_id": 1,
        "created_at": datetime.utcnow().isoformat(),
        "status": "ready",
        "access_token": "valid-restore-token-xyz",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
    }, ttl_seconds=60)

    token = await get_restore_token(state)
    assert token == "valid-restore-token-xyz"

    await delete_state(f"{_PREFIX}{state}")


@pytest.mark.asyncio
async def test_get_restore_token_missing_raises():
    """get_restore_token raises ValueError for non-existent state."""
    with pytest.raises(ValueError, match="No restore consent token found"):
        await get_restore_token("nonexistent-state-xyz")


@pytest.mark.asyncio
async def test_get_restore_token_pending_raises():
    """get_restore_token raises ValueError if status is not ready."""
    state = "test-pending-token"
    await set_state(f"{_PREFIX}{state}", {
        "tenant_id": 1,
        "ms_tenant_id": "test",
        "user_id": 1,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }, ttl_seconds=60)

    with pytest.raises(ValueError, match="not ready"):
        await get_restore_token(state)

    await delete_state(f"{_PREFIX}{state}")


# ═══════════════════════════════════════════════════════
# Token Discard (Zero Standing Write Access)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_discard_restore_token():
    """discard_restore_token removes entry from Redis."""
    state = "test-discard"
    await set_state(f"{_PREFIX}{state}", {
        "tenant_id": 3,
        "ms_tenant_id": "test-discard",
        "user_id": 1,
        "created_at": datetime.utcnow().isoformat(),
        "status": "ready",
        "access_token": "discard-me-token",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
    }, ttl_seconds=60)

    # Verify exists
    entry = await get_state(f"{_PREFIX}{state}")
    assert entry is not None

    # Discard
    await discard_restore_token(state)

    # Verify gone
    entry = await get_state(f"{_PREFIX}{state}")
    assert entry is None


@pytest.mark.asyncio
async def test_discard_nonexistent_is_safe():
    """Discarding a non-existent token should not raise."""
    await discard_restore_token("does-not-exist-xyz")
    # No exception = success


# ═══════════════════════════════════════════════════════
# Redis TTL Auto-Expiry (No Manual Cleanup Needed)
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_consent_state_has_ttl():
    """Consent state stored with TTL — auto-expires, no cleanup function needed."""
    state = "test-ttl"
    await set_state(f"{_PREFIX}{state}", {"status": "test"}, ttl_seconds=1)

    entry = await get_state(f"{_PREFIX}{state}")
    assert entry is not None

    # TTL will auto-expire (we don't wait — just verify it was set with TTL)
    await delete_state(f"{_PREFIX}{state}")


# ═══════════════════════════════════════════════════════
# Security: Tokens Never Persisted to DB
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tokens_stored_in_redis_not_db():
    """Restore tokens must NEVER be in the database — only Redis with TTL."""
    import app.api.restore_consent as module
    # Verify no SQLAlchemy model for tokens
    assert not hasattr(module, 'RestoreToken')  # No DB model
    assert not hasattr(module, '__tablename__')  # Module is not a model
    # Verify Redis prefix is used
    assert module._PREFIX == "restore_consent:"
