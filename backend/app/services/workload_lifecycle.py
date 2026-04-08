"""Workload Lifecycle Service — manages opt-in per workload, gated by subscription.

Enterprise pattern: each workload follows a state machine:
  disabled → enabled → discovered → protected → paused

Only enabled+ workloads get discovered.
Only discovered+ workloads get protected.
Only protected workloads get backed up and monitored.

This is the SINGLE SOURCE OF TRUTH for what's active per tenant.
Discovery, protection, backup, monitoring, and dashboard all check here.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_workload_app import TenantWorkloadApp, WorkloadLifecycle

logger = logging.getLogger(__name__)

# Subscription tier → max workloads allowed
TIER_WORKLOAD_LIMITS = {
    "community": 2,
    "professional": 5,
    "business": 5,
    "enterprise": 6,  # 5 standard + Power Platform
}

# Valid lifecycle transitions
VALID_TRANSITIONS = {
    WorkloadLifecycle.DISABLED: {WorkloadLifecycle.ENABLED},
    WorkloadLifecycle.ENABLED: {WorkloadLifecycle.DISCOVERED, WorkloadLifecycle.DISABLED},
    WorkloadLifecycle.DISCOVERED: {WorkloadLifecycle.PROTECTED, WorkloadLifecycle.DISABLED},
    WorkloadLifecycle.PROTECTED: {WorkloadLifecycle.PAUSED, WorkloadLifecycle.DISABLED},
    WorkloadLifecycle.PAUSED: {WorkloadLifecycle.PROTECTED, WorkloadLifecycle.DISABLED},
}


async def get_enabled_workloads(db: AsyncSession, tenant_id: int) -> set[str]:
    """Get workloads that are enabled+ (enabled, discovered, or protected) for a tenant.

    Used by: discovery, scheduler, dashboard, anomaly detection.
    """
    result = await db.execute(
        select(TenantWorkloadApp.workload).where(
            TenantWorkloadApp.tenant_id == tenant_id,
            TenantWorkloadApp.lifecycle_status.in_([
                WorkloadLifecycle.ENABLED.value,
                WorkloadLifecycle.DISCOVERED.value,
                WorkloadLifecycle.PROTECTED.value,
            ]),
        )
    )
    return {r[0] for r in result.all()}


async def get_protected_workloads(db: AsyncSession, tenant_id: int) -> set[str]:
    """Get workloads that are in protected state — active backup + monitoring.

    Used by: scheduler (only backup protected), smart engine (only monitor protected).
    """
    result = await db.execute(
        select(TenantWorkloadApp.workload).where(
            TenantWorkloadApp.tenant_id == tenant_id,
            TenantWorkloadApp.lifecycle_status == WorkloadLifecycle.PROTECTED.value,
        )
    )
    return {r[0] for r in result.all()}


async def transition_workload(
    db: AsyncSession,
    tenant_id: int,
    workload: str,
    new_status: WorkloadLifecycle,
) -> bool:
    """Transition a workload to a new lifecycle state.

    Validates the transition is valid per the state machine.
    Returns True if successful, False if invalid transition.
    """
    result = await db.execute(
        select(TenantWorkloadApp).where(
            TenantWorkloadApp.tenant_id == tenant_id,
            TenantWorkloadApp.workload == workload,
        )
    )
    wl_app = result.scalar_one_or_none()

    if not wl_app:
        return False

    current = WorkloadLifecycle(wl_app.lifecycle_status)
    valid_next = VALID_TRANSITIONS.get(current, set())

    if new_status not in valid_next:
        logger.warning(
            f"Invalid workload transition: tenant={tenant_id} workload={workload} "
            f"{current.value} → {new_status.value} (valid: {[s.value for s in valid_next]})"
        )
        return False

    wl_app.lifecycle_status = new_status.value
    logger.info(f"Workload transition: tenant={tenant_id} {workload}: {current.value} → {new_status.value}")
    return True


async def check_subscription_limit(
    db: AsyncSession,
    tenant_id: int,
    tier: str,
) -> tuple[bool, str]:
    """Check if tenant can enable another workload based on subscription tier.

    Returns (allowed, reason).
    """
    max_allowed = TIER_WORKLOAD_LIMITS.get(tier, 2)
    current_enabled = await get_enabled_workloads(db, tenant_id)

    if len(current_enabled) >= max_allowed:
        return False, f"Your {tier} plan allows {max_allowed} workloads. Upgrade to enable more."

    return True, "OK"
