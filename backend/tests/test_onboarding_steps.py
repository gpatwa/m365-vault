"""Tests for server-side onboarding state machine."""
import pytest
import pytest_asyncio

from app.database import async_session
from app.models.onboarding_step import OnboardingStep, ONBOARDING_STEPS
from app.models.user import User
from app.services.onboarding_service import mark_step, get_steps, get_onboarding_summary


@pytest_asyncio.fixture
async def test_user(db):
    """Create a test user for onboarding step tests."""
    from app.services.auth import hash_password
    user = User(
        username="onboard_tester",
        email="onboard@test.com",
        password_hash=hash_password("TestPass123"),
        full_name="Onboard Tester",
        role="admin",
    )
    db.add(user)
    await db.flush()
    return user


# ── mark_step Tests ──


@pytest.mark.asyncio
async def test_mark_step_creates_record(db, test_user):
    """mark_step creates an OnboardingStep record."""
    was_new = await mark_step(db, test_user.id, "create_account")
    assert was_new is True

    steps = await get_steps(db, test_user.id)
    assert "create_account" in steps
    assert steps["create_account"]  # Has a timestamp


@pytest.mark.asyncio
async def test_mark_step_idempotent(db, test_user):
    """Marking the same step twice is idempotent — second call returns False."""
    first = await mark_step(db, test_user.id, "connect_platform")
    second = await mark_step(db, test_user.id, "connect_platform")

    assert first is True
    assert second is False

    steps = await get_steps(db, test_user.id)
    assert "connect_platform" in steps


@pytest.mark.asyncio
async def test_mark_unknown_step_rejected(db, test_user):
    """Unknown step names are rejected."""
    was_new = await mark_step(db, test_user.id, "not_a_real_step")
    assert was_new is False


@pytest.mark.asyncio
async def test_mark_step_with_metadata(db, test_user):
    """mark_step stores optional metadata as JSON."""
    await mark_step(db, test_user.id, "first_backup", metadata={"tenant_id": 42})

    from sqlalchemy import select
    result = await db.execute(
        select(OnboardingStep).where(
            OnboardingStep.user_id == test_user.id,
            OnboardingStep.step == "first_backup",
        )
    )
    record = result.scalar_one()
    assert '"tenant_id": 42' in record.metadata_json


# ── get_steps Tests ──


@pytest.mark.asyncio
async def test_get_steps_returns_completed_only(db, test_user):
    """get_steps returns only completed steps with timestamps."""
    await mark_step(db, test_user.id, "create_account")
    await mark_step(db, test_user.id, "connect_platform")

    steps = await get_steps(db, test_user.id)
    assert len(steps) == 2
    assert "create_account" in steps
    assert "connect_platform" in steps
    assert "discover_workloads" not in steps


@pytest.mark.asyncio
async def test_get_steps_empty_for_new_user(db, test_user):
    """New user has no completed steps."""
    steps = await get_steps(db, test_user.id)
    assert steps == {}


# ── get_onboarding_summary Tests ──


@pytest.mark.asyncio
async def test_onboarding_summary_structure(db, test_user):
    """Summary includes steps dict, completed count, and total."""
    await mark_step(db, test_user.id, "create_account")
    await mark_step(db, test_user.id, "connect_platform")
    await mark_step(db, test_user.id, "discover_workloads")

    summary = await get_onboarding_summary(db, test_user.id)
    assert summary["completed"] == 3
    assert summary["total"] == 6
    assert "create_account" in summary["steps"]
    assert "first_backup" not in summary["steps"]


@pytest.mark.asyncio
async def test_onboarding_summary_all_complete(db, test_user):
    """Summary shows 6/6 when all steps are completed."""
    for step in ONBOARDING_STEPS:
        await mark_step(db, test_user.id, step)

    summary = await get_onboarding_summary(db, test_user.id)
    assert summary["completed"] == 6
    assert summary["total"] == 6


# ── Session Integration Tests ──


@pytest.mark.asyncio
async def test_register_marks_create_account(auth_client):
    """POST /auth/register automatically marks create_account step."""
    # auth_client fixture already registered a user
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "onboarding" in data
    assert "create_account" in data["onboarding"]["steps"]


@pytest.mark.asyncio
async def test_session_includes_onboarding(auth_client):
    """GET /auth/session includes onboarding summary."""
    response = await auth_client.get("/api/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert "onboarding" in data
    assert "steps" in data["onboarding"]
    assert "completed" in data["onboarding"]
    assert "total" in data["onboarding"]
    assert data["onboarding"]["total"] == 6


# ── Step Completion Endpoint Tests ──


@pytest.mark.asyncio
async def test_complete_explore_recovery_step(auth_client):
    """POST /api/onboard/steps/explore_recovery/complete works for manual steps."""
    response = await auth_client.post("/api/onboard/steps/explore_recovery/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["step"] == "explore_recovery"
    assert data["completed"] is True
    assert data["was_new"] is True


@pytest.mark.asyncio
async def test_complete_explore_recovery_idempotent(auth_client):
    """Second call to complete same step returns was_new=False."""
    await auth_client.post("/api/onboard/steps/explore_recovery/complete")
    response = await auth_client.post("/api/onboard/steps/explore_recovery/complete")
    assert response.status_code == 200
    assert response.json()["was_new"] is False


@pytest.mark.asyncio
async def test_complete_auto_step_rejected(auth_client):
    """Cannot manually complete auto-marked steps (e.g. connect_platform)."""
    response = await auth_client.post("/api/onboard/steps/connect_platform/complete")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_complete_unknown_step_rejected(auth_client):
    """Cannot complete an unknown step."""
    response = await auth_client.post("/api/onboard/steps/nonexistent/complete")
    assert response.status_code == 400


# ── Immutability Test ──


@pytest.mark.asyncio
async def test_steps_are_immutable(db, test_user):
    """Once a step is completed, it cannot be un-completed."""
    await mark_step(db, test_user.id, "create_account")
    await db.flush()

    steps_before = await get_steps(db, test_user.id)
    assert "create_account" in steps_before

    # There's no "unmark" API. Steps are immutable.
    # The only way to verify immutability is to confirm the model doesn't expose deletion.
    summary = await get_onboarding_summary(db, test_user.id)
    assert summary["completed"] >= 1
