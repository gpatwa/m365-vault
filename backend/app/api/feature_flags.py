"""Feature Flags API — tier-based feature gating tied to pricing engine.

Endpoints:
- GET /api/features — all features with enabled/disabled status (public, no auth needed for UI gating)
- GET /api/features/categories — features grouped by category
- GET /api/features/tiers — compare features across all pricing tiers
- PUT /api/features/override — admin override to force enable/disable a feature
- DELETE /api/features/override/{feature} — remove an admin override
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.user import User
from app.services.auth import get_current_user
from app.services.feature_flags import feature_flags

router = APIRouter(prefix="/api/features", tags=["Feature Flags"])


@router.get("")
async def get_features():
    """Get all features with enabled/disabled status.

    No auth required — frontend needs this to gate UI components before login.
    """
    return {
        "tier": feature_flags.tier,
        "features": feature_flags.get_all(),
        "limits": feature_flags.get_limits(),
        "overrides": feature_flags.get_overrides(),
    }


@router.get("/categories")
async def get_features_by_category():
    """Get features grouped by category with enabled status."""
    return {
        "tier": feature_flags.tier,
        "categories": feature_flags.get_by_category(),
        "limits": feature_flags.get_limits(),
    }


@router.get("/tiers")
async def get_tier_comparison():
    """Compare features across all pricing tiers.

    Useful for pricing page, upgrade prompts, and sales materials.
    """
    return {
        "current_tier": feature_flags.tier,
        "comparison": feature_flags.get_tier_comparison(),
    }


@router.get("/check/{feature}")
async def check_feature(feature: str):
    """Check if a specific feature is enabled.

    Returns: {"feature": "msp_dashboard", "enabled": true, "tier": "business"}
    """
    return {
        "feature": feature,
        "enabled": feature_flags.is_enabled(feature),
        "tier": feature_flags.tier,
    }


class OverrideRequest(BaseModel):
    feature: str
    enabled: bool


@router.put("/override")
async def set_override(
    req: OverrideRequest,
    current_user: User = Depends(get_current_user),
):
    """Admin override — force enable/disable a feature regardless of tier.

    Requires admin role. Overrides persist until removed or server restarts.
    """
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can set feature overrides")

    feature_flags.set_override(req.feature, req.enabled)

    return {
        "feature": req.feature,
        "enabled": req.enabled,
        "source": "override",
        "message": f"Feature '{req.feature}' {'enabled' if req.enabled else 'disabled'} via admin override",
    }


@router.delete("/override/{feature}")
async def remove_override(
    feature: str,
    current_user: User = Depends(get_current_user),
):
    """Remove an admin override — revert feature to tier-based gating."""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove feature overrides")

    feature_flags.remove_override(feature)
    return {
        "feature": feature,
        "enabled": feature_flags.is_enabled(feature),
        "source": f"tier:{feature_flags.tier}",
        "message": f"Override removed. Feature '{feature}' now follows tier-based gating.",
    }
