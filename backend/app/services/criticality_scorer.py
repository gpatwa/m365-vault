"""Criticality Scorer — computes 0-100 scores for protected objects based on org context."""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.org_context import UserContext, SiteContext, VIPGroupMember

logger = logging.getLogger(__name__)

# Departments considered business-critical
CRITICAL_DEPARTMENTS = {"Executive", "C-Suite", "Legal", "Finance", "HR", "IT", "Compliance", "Security"}

# Job title keywords that indicate seniority
EXECUTIVE_TITLES = {"ceo", "cto", "cfo", "coo", "ciso", "cpo", "vp", "vice president",
                     "director", "head of", "chief", "president", "general counsel"}


class CriticalityScorer:
    """Computes criticality scores (0-100) for users and sites based on org context signals."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def score_all(self, tenant_id: int) -> dict:
        """Score all users and sites for a tenant. Returns summary."""
        now = datetime.utcnow()
        users_scored = await self.score_all_users(tenant_id, now)
        sites_scored = await self.score_all_sites(tenant_id, now)
        await self._propagate_to_protected_objects(tenant_id)
        await self.db.commit()

        # Count tiers
        result = await self.db.execute(
            select(UserContext.criticality_tier).where(UserContext.tenant_id == tenant_id)
        )
        tiers = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for (tier,) in result.all():
            tiers[tier] = tiers.get(tier, 0) + 1

        return {
            "users_scored": users_scored,
            "sites_scored": sites_scored,
            "tiers": tiers,
        }

    async def score_all_users(self, tenant_id: int, now: datetime = None) -> int:
        """Score all UserContext records for a tenant."""
        now = now or datetime.utcnow()
        result = await self.db.execute(
            select(UserContext).where(UserContext.tenant_id == tenant_id)
        )
        users = result.scalars().all()

        # Get VIP group memberships
        vip_boosts = await self._get_vip_boosts(tenant_id)

        count = 0
        for ctx in users:
            score, tier, signals = self._score_user(ctx, vip_boosts, now)
            ctx.criticality_score = score
            ctx.criticality_tier = tier
            ctx.signals = json.dumps(signals)
            ctx.computed_at = now
            count += 1

        await self.db.flush()
        return count

    async def score_all_sites(self, tenant_id: int, now: datetime = None) -> int:
        """Score all SiteContext records for a tenant."""
        now = now or datetime.utcnow()
        result = await self.db.execute(
            select(SiteContext).where(SiteContext.tenant_id == tenant_id)
        )
        sites = result.scalars().all()

        count = 0
        for ctx in sites:
            score, tier, signals = self._score_site(ctx)
            ctx.criticality_score = score
            ctx.criticality_tier = tier
            ctx.signals = json.dumps(signals)
            ctx.computed_at = now
            count += 1

        await self.db.flush()
        return count

    def _score_user(self, ctx: UserContext, vip_boosts: dict, now: datetime) -> tuple:
        """Compute criticality score for a single user.

        Weights:
        - User Importance (40%): VIP, admin roles, department, title, reports
        - Data Sensitivity (30%): legal hold, sensitivity labels, external sharing
        - Activity Level (20%): recent sign-in activity
        - Business Dependency (10%): VIP group boost, manager chain depth
        """
        signals = {}

        # ── User Importance (0-100, weight 40%) ──
        user_score = 0

        if ctx.is_global_admin:
            user_score = 100
            signals["global_admin"] = True
        elif ctx.has_privileged_role:
            user_score = 80
            signals["privileged_role"] = True
        elif ctx.is_vip:
            user_score = 90
            signals["admin_vip"] = True
        else:
            # Check job title for executive keywords
            title = (ctx.job_title or "").lower()
            if any(kw in title for kw in EXECUTIVE_TITLES):
                user_score = max(user_score, 70)
                signals["executive_title"] = ctx.job_title

            # Check department
            dept = ctx.department or ""
            if dept in CRITICAL_DEPARTMENTS:
                user_score = max(user_score, 60)
                signals["critical_department"] = dept

            # Direct reports
            if ctx.direct_reports_count > 10:
                user_score = max(user_score, 55)
                signals["many_reports"] = ctx.direct_reports_count
            elif ctx.direct_reports_count > 5:
                user_score = max(user_score, 45)
            elif ctx.direct_reports_count > 0:
                user_score = max(user_score, 35)

            # Default floor
            user_score = max(user_score, 30)

        # ── Data Sensitivity (0-100, weight 30%) ──
        sensitivity_score = 20  # default baseline

        if ctx.has_legal_hold:
            sensitivity_score = 100
            signals["legal_hold"] = True
        elif ctx.highest_sensitivity_label:
            label = ctx.highest_sensitivity_label.lower()
            if "highly confidential" in label:
                sensitivity_score = 100
                signals["sensitivity_label"] = ctx.highest_sensitivity_label
            elif "confidential" in label:
                sensitivity_score = 70
                signals["sensitivity_label"] = ctx.highest_sensitivity_label
            elif "internal" in label:
                sensitivity_score = 40

        if ctx.external_sharing_active:
            sensitivity_score = min(100, sensitivity_score + 20)
            signals["external_sharing"] = True

        # ── Activity Level (0-100, weight 20%) ──
        activity_score = 10  # default for unknown

        if ctx.last_sign_in_at:
            days_since = (now - ctx.last_sign_in_at).days
            if days_since <= 1:
                activity_score = 100
                signals["active_today"] = True
            elif days_since <= 7:
                activity_score = 80
            elif days_since <= 30:
                activity_score = 50
            elif days_since <= 90:
                activity_score = 20
            else:
                activity_score = 5
                signals["inactive_90d"] = True

        # ── Business Dependency (0-100, weight 10%) ──
        dep_score = 20  # default

        # VIP group boost
        po_id = ctx.protected_object_id
        if po_id and po_id in vip_boosts:
            dep_score = min(100, dep_score + vip_boosts[po_id])
            signals["vip_group_boost"] = vip_boosts[po_id]

        # Manager of managers (has direct reports who have direct reports)
        if ctx.direct_reports_count > 5:
            dep_score = min(100, dep_score + 30)

        # ── Weighted total ──
        total = round(
            user_score * 0.40 +
            sensitivity_score * 0.30 +
            activity_score * 0.20 +
            dep_score * 0.10
        )

        # Floor for critical roles — these should NEVER score below threshold
        # regardless of missing activity/sensitivity data
        if ctx.is_global_admin:
            total = max(total, 90)  # Global Admin is always critical
            signals["floor_applied"] = "global_admin>=90"
        elif ctx.has_privileged_role:
            total = max(total, 75)  # Privileged roles are always high+
            signals["floor_applied"] = "privileged_role>=75"
        elif ctx.is_vip:
            total = max(total, 80)  # Admin-flagged VIP is critical
            signals["floor_applied"] = "vip>=80"

        total = max(0, min(100, total))

        # Add threat exposure (OCSF future integration)
        if ctx.threat_exposure_score > 0:
            total = min(100, total + ctx.threat_exposure_score // 5)
            signals["threat_exposure"] = ctx.threat_exposure_score

        tier = self._score_to_tier(total)

        signals["user_importance"] = round(user_score * 0.40)
        signals["data_sensitivity"] = round(sensitivity_score * 0.30)
        signals["activity_level"] = round(activity_score * 0.20)
        signals["business_dependency"] = round(dep_score * 0.10)

        return total, tier, signals

    def _score_site(self, ctx: SiteContext) -> tuple:
        """Compute criticality score for a site."""
        signals = {}
        score = 0

        # Traffic (0-40)
        if ctx.unique_visitors > 100:
            score += 40
            signals["high_traffic"] = ctx.unique_visitors
        elif ctx.unique_visitors > 20:
            score += 25
        elif ctx.unique_visitors > 5:
            score += 15
        else:
            score += 5

        # Content volume (0-20)
        if ctx.file_count > 1000:
            score += 20
            signals["large_library"] = ctx.file_count
        elif ctx.file_count > 100:
            score += 12
        elif ctx.file_count > 10:
            score += 6

        # Sensitivity (0-25)
        if ctx.sensitivity_label:
            label = ctx.sensitivity_label.lower()
            if "highly confidential" in label:
                score += 25
                signals["sensitivity_label"] = ctx.sensitivity_label
            elif "confidential" in label:
                score += 18
            elif "internal" in label:
                score += 8

        # External sharing (0-15)
        if ctx.external_sharing_enabled:
            score += 15
            signals["external_sharing"] = True

        # Activity recency
        if ctx.last_activity_at:
            days_since = (datetime.utcnow() - ctx.last_activity_at).days
            if days_since > 90:
                score = max(10, score - 15)
                signals["abandoned_90d"] = True

        score = max(0, min(100, score))
        tier = self._score_to_tier(score)

        return score, tier, signals

    @staticmethod
    def _score_to_tier(score: int) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        return "low"

    async def _get_vip_boosts(self, tenant_id: int) -> dict:
        """Get VIP group membership boosts keyed by protected_object_id."""
        from app.models.org_context import VIPGroup
        result = await self.db.execute(
            select(VIPGroupMember.protected_object_id, VIPGroup.criticality_boost)
            .join(VIPGroup, VIPGroupMember.vip_group_id == VIPGroup.id)
            .where(VIPGroup.tenant_id == tenant_id)
        )
        boosts: dict = {}
        for po_id, boost in result.all():
            # Take highest boost if user is in multiple groups
            boosts[po_id] = max(boosts.get(po_id, 0), boost)
        return boosts

    async def _propagate_to_protected_objects(self, tenant_id: int):
        """Write criticality scores from context tables back to ProtectedObject."""
        # Users → ProtectedObjects
        result = await self.db.execute(
            select(UserContext).where(
                UserContext.tenant_id == tenant_id,
                UserContext.protected_object_id.isnot(None),
            )
        )
        for ctx in result.scalars().all():
            po_result = await self.db.execute(
                select(ProtectedObject).where(ProtectedObject.id == ctx.protected_object_id)
            )
            po = po_result.scalar_one_or_none()
            if po:
                po.criticality_score = ctx.criticality_score
                po.criticality_tier = ctx.criticality_tier

        # Sites → ProtectedObjects
        result = await self.db.execute(
            select(SiteContext).where(
                SiteContext.tenant_id == tenant_id,
                SiteContext.protected_object_id.isnot(None),
            )
        )
        for ctx in result.scalars().all():
            po_result = await self.db.execute(
                select(ProtectedObject).where(ProtectedObject.id == ctx.protected_object_id)
            )
            po = po_result.scalar_one_or_none()
            if po:
                po.criticality_score = ctx.criticality_score
                po.criticality_tier = ctx.criticality_tier

        await self.db.flush()
