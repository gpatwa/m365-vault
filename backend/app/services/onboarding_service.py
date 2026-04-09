"""Onboarding service — server-side step completion tracking.

Steps are immutable: once completed, they never un-complete.
This replaces the frontend's localStorage-based tracking.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.onboarding_step import OnboardingStep, ONBOARDING_STEPS

logger = logging.getLogger(__name__)


async def mark_step(
    db: AsyncSession, user_id: int, step: str, metadata: dict | None = None
) -> bool:
    """Mark an onboarding step as completed. Idempotent — skips if already done.

    Returns True if newly marked, False if already completed.
    """
    if step not in ONBOARDING_STEPS:
        logger.warning(f"Unknown onboarding step: {step}")
        return False

    existing = await db.execute(
        select(OnboardingStep).where(
            OnboardingStep.user_id == user_id,
            OnboardingStep.step == step,
        )
    )
    if existing.scalar_one_or_none():
        return False

    record = OnboardingStep(
        user_id=user_id,
        step=step,
        completed_at=datetime.utcnow(),
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(record)
    await db.flush()
    logger.info(f"Onboarding step '{step}' completed for user {user_id}")
    return True


async def get_steps(db: AsyncSession, user_id: int) -> dict:
    """Get all completed onboarding steps for a user.

    Returns: {"create_account": "2026-04-08T...", ...} for completed steps.
    """
    result = await db.execute(
        select(OnboardingStep).where(OnboardingStep.user_id == user_id)
    )
    steps = {}
    for record in result.scalars().all():
        steps[record.step] = record.completed_at.isoformat()
    return steps


async def get_onboarding_summary(db: AsyncSession, user_id: int) -> dict:
    """Get full onboarding summary for session response."""
    steps = await get_steps(db, user_id)
    return {
        "steps": steps,
        "completed": len(steps),
        "total": len(ONBOARDING_STEPS),
    }
