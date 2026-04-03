"""Feature flag service — tier-based feature gating tied to the pricing engine.

Features are enabled/disabled based on the LICENSE_TIER setting.
Admin overrides allow force-enabling or force-disabling individual features
regardless of tier (for demos, pilots, or beta testing).

Feature categories:
  - workloads: exchange, onedrive, sharepoint, teams, entra_id, power_platform
  - intelligence: org_context, mvb_plans, criticality_scoring, anomaly_detection
  - recovery: agentic_recovery, cleanroom, mass_recovery
  - compliance: worm, ediscovery, legal_hold
  - operations: msp_dashboard, msp_billing, msp_branding, msp_bulk_onboard, msp_demo
  - platform: sso, api_access, webhooks, custom_reports
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ── Feature definitions per tier ──────────────────────────────

TIER_FEATURES = {
    "community": {
        "workloads": ["exchange", "onedrive", "sharepoint"],
        "intelligence": ["anomaly_detection"],
        "recovery": ["mass_recovery"],
        "compliance": [],
        "operations": [],
        "platform": ["api_access"],
        "limits": {
            "max_objects": 25,
            "max_tenants": 1,
            "max_workloads": 3,
            "retention_days": 30,
        },
    },
    "professional": {
        "workloads": ["exchange", "onedrive", "sharepoint", "teams", "entra_id"],
        "intelligence": ["anomaly_detection", "health_scoring", "sensitive_data_scanner", "openclaw_attack_demo", "agent_audit"],
        "recovery": ["mass_recovery", "test_restore"],
        "compliance": [],
        "operations": [],
        "platform": ["api_access", "sso"],
        "limits": {
            "max_objects": None,  # unlimited
            "max_tenants": 10,
            "max_workloads": 5,
            "retention_days": 90,
        },
    },
    "business": {
        "workloads": ["exchange", "onedrive", "sharepoint", "teams", "entra_id"],
        "intelligence": ["anomaly_detection", "health_scoring", "sensitive_data_scanner",
                         "org_context", "mvb_plans", "criticality_scoring", "openclaw_attack_demo", "agent_audit"],
        "recovery": ["mass_recovery", "test_restore"],
        "compliance": ["worm", "legal_hold"],
        "operations": ["msp_dashboard", "msp_billing"],
        "platform": ["api_access", "sso", "webhooks"],
        "limits": {
            "max_objects": None,
            "max_tenants": None,
            "max_workloads": None,
            "retention_days": 365,
        },
    },
    "enterprise": {
        "workloads": ["exchange", "onedrive", "sharepoint", "teams", "entra_id", "power_platform"],
        "intelligence": ["anomaly_detection", "health_scoring", "sensitive_data_scanner",
                         "org_context", "mvb_plans", "criticality_scoring", "openclaw_attack_demo", "agent_audit", "agent_rewind", "agent_governance"],
        "recovery": ["mass_recovery", "test_restore", "agentic_recovery", "cleanroom"],
        "compliance": ["worm", "legal_hold", "ediscovery"],
        "operations": ["msp_dashboard", "msp_billing", "msp_branding", "msp_bulk_onboard", "msp_demo"],
        "platform": ["api_access", "sso", "webhooks", "custom_reports"],
        "limits": {
            "max_objects": None,
            "max_tenants": None,
            "max_workloads": None,
            "retention_days": 365,
        },
    },
}

# Admin overrides: force-enable or force-disable features regardless of tier
# Format: {"feature_name": True/False}
# Set via API or environment variable FEATURE_OVERRIDES="+msp_dashboard,-worm"
_overrides: dict[str, bool] = {}


def _parse_env_overrides():
    """Parse FEATURE_OVERRIDES env var: "+feature1,-feature2,+feature3" """
    raw = getattr(settings, 'FEATURE_OVERRIDES', '') or ''
    for token in raw.split(','):
        token = token.strip()
        if token.startswith('+'):
            _overrides[token[1:]] = True
        elif token.startswith('-'):
            _overrides[token[1:]] = False


# Parse on module load
_parse_env_overrides()


class FeatureFlagService:
    """Check feature availability based on license tier + overrides."""

    def __init__(self):
        self.tier = settings.LICENSE_TIER
        self.tier_config = TIER_FEATURES.get(self.tier, TIER_FEATURES["community"])

    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled for the current tier."""
        # Admin override takes precedence
        if feature in _overrides:
            return _overrides[feature]

        # Check across all categories
        for category in ["workloads", "intelligence", "recovery", "compliance", "operations", "platform"]:
            if feature in self.tier_config.get(category, []):
                return True
        return False

    def get_all(self) -> dict:
        """Get all features with their enabled/disabled status."""
        all_features = set()
        for tier_config in TIER_FEATURES.values():
            for category in ["workloads", "intelligence", "recovery", "compliance", "operations", "platform"]:
                all_features.update(tier_config.get(category, []))

        result = {}
        for feature in sorted(all_features):
            enabled = self.is_enabled(feature)
            source = "override" if feature in _overrides else f"tier:{self.tier}"
            result[feature] = {"enabled": enabled, "source": source}
        return result

    def get_by_category(self) -> dict:
        """Get features grouped by category with enabled status."""
        categories = {}
        all_possible = {}

        # Collect all possible features from enterprise tier
        enterprise = TIER_FEATURES["enterprise"]
        for category in ["workloads", "intelligence", "recovery", "compliance", "operations", "platform"]:
            all_possible[category] = enterprise.get(category, [])

        for category, features in all_possible.items():
            categories[category] = {
                f: self.is_enabled(f) for f in features
            }
        return categories

    def get_limits(self) -> dict:
        """Get tier limits (max objects, tenants, etc.)."""
        return self.tier_config.get("limits", {})

    def set_override(self, feature: str, enabled: bool):
        """Set an admin override for a feature."""
        _overrides[feature] = enabled
        logger.info(f"Feature override set: {feature}={enabled}")

    def remove_override(self, feature: str):
        """Remove an admin override (revert to tier-based)."""
        _overrides.pop(feature, None)
        logger.info(f"Feature override removed: {feature}")

    def get_overrides(self) -> dict[str, bool]:
        """Get all active admin overrides."""
        return dict(_overrides)

    def get_tier_comparison(self) -> dict:
        """Compare features across all tiers (for pricing page / upgrade prompts)."""
        comparison = {}
        all_features = set()
        for tier_config in TIER_FEATURES.values():
            for category in ["workloads", "intelligence", "recovery", "compliance", "operations", "platform"]:
                all_features.update(tier_config.get(category, []))

        for feature in sorted(all_features):
            comparison[feature] = {}
            for tier_name, tier_config in TIER_FEATURES.items():
                found = False
                for category in ["workloads", "intelligence", "recovery", "compliance", "operations", "platform"]:
                    if feature in tier_config.get(category, []):
                        found = True
                        break
                comparison[feature][tier_name] = found
        return comparison


# Global instance
feature_flags = FeatureFlagService()
