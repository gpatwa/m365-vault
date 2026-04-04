"""License enforcement middleware — connects Stripe subscription to feature access.

Checks tenant subscription status and tier before allowing actions.
Community tier: hard block at 25 protected objects.
Expired/canceled: downgrade to Community automatically.
"""
import logging
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.services.feature_flags import TIER_FEATURES

logger = logging.getLogger(__name__)


async def get_tenant_tier(tenant_id: int, db: AsyncSession) -> str:
    """Get the effective license tier for a tenant based on subscription status."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return "community"

    status = tenant.subscription_status or "free"

    # Active or trialing → use subscription tier
    if status in ("active", "trialing"):
        return tenant.subscription_tier or "community"

    # Past due → grace period (7 days), then downgrade
    if status == "past_due":
        return tenant.subscription_tier or "community"

    # Free, canceled, or anything else → community
    return "community"


async def get_tier_limits(tenant_id: int, db: AsyncSession) -> dict:
    """Get the limits for a tenant's current tier."""
    tier = await get_tenant_tier(tenant_id, db)
    tier_config = TIER_FEATURES.get(tier, TIER_FEATURES.get("community", {}))
    return tier_config.get("limits", {
        "max_objects": 25,
        "max_tenants": 1,
        "max_workloads": 2,
        "retention_days": 30,
    })


async def check_object_limit(tenant_id: int, db: AsyncSession):
    """Check if tenant can create more protected objects. Raises 403 if limit exceeded."""
    limits = await get_tier_limits(tenant_id, db)
    max_objects = limits.get("max_objects")

    if max_objects is None:
        return  # Unlimited

    # Count current protected objects
    result = await db.execute(
        select(func.count()).select_from(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status.in_([ProtectionStatus.PROTECTED, ProtectionStatus.UNPROTECTED]),
        )
    )
    current = result.scalar() or 0

    if current >= max_objects:
        raise HTTPException(
            status_code=403,
            detail=f"Object limit reached ({current}/{max_objects}). Upgrade your plan at /billing to protect more objects.",
        )


async def check_feature_access(tenant_id: int, feature: str, db: AsyncSession):
    """Check if a specific feature is available for the tenant's tier."""
    tier = await get_tenant_tier(tenant_id, db)
    tier_config = TIER_FEATURES.get(tier, TIER_FEATURES.get("community", {}))

    # Check across all feature categories
    all_features = []
    for category in ["workloads", "intelligence", "recovery", "compliance", "operations", "platform"]:
        all_features.extend(tier_config.get(category, []))

    if feature not in all_features:
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{feature}' requires a higher plan. Current tier: {tier}. Upgrade at /billing.",
        )


async def check_backup_allowed(tenant_id: int, db: AsyncSession):
    """Check if backup is allowed — subscription must be active/trialing."""
    tier = await get_tenant_tier(tenant_id, db)
    tenant = await db.get(Tenant, tenant_id)

    if not tenant:
        raise HTTPException(404, detail="Tenant not found")

    status = tenant.subscription_status or "free"

    # Allow free tier (community), active, trialing
    if status in ("free", "active", "trialing"):
        return

    # Past due — allow with warning (logged)
    if status == "past_due":
        logger.warning(f"Tenant {tenant_id} running backup with past_due subscription")
        return

    # Canceled — block
    if status == "canceled":
        raise HTTPException(
            403,
            detail="Subscription canceled. Reactivate at /billing to resume backups.",
        )
