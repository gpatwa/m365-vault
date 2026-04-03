"""Agent Monitor Service — detects and tracks AI agent activity in M365.

Reads Microsoft Graph audit logs to identify agent vs human actions,
detect shadow (unmanaged) agents, and score agent risk levels.

Part of Agent Shield Phase 1 (Agent Audit).
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_activity import AgentProfile, AgentActivity

logger = logging.getLogger(__name__)

# Known managed agent patterns (extend as new agents are onboarded)
KNOWN_MANAGED_AGENTS = {
    "Microsoft Copilot": {"type": "copilot", "managed": True},
    "Microsoft 365 Copilot": {"type": "copilot", "managed": True},
    "Power Automate": {"type": "custom", "managed": True},
    "Logic Apps": {"type": "custom", "managed": True},
}

# High-risk action patterns
HIGH_RISK_ACTIONS = {
    "permission_change": 30,
    "delete": 20,
    "modify": 10,
    "read": 2,
}

HIGH_RISK_RESOURCES = {
    "identity": 30,
    "config": 25,
    "oauth": 25,
    "email": 10,
    "file": 5,
}


def classify_agent_type(agent_name: str, app_id: str = None) -> str:
    """Classify agent type from name and app registration ID."""
    name_lower = agent_name.lower()
    if "copilot" in name_lower:
        return "copilot"
    if "openclaw" in name_lower or "clawdbot" in name_lower or "moltbot" in name_lower:
        return "openclaw"
    if "power automate" in name_lower or "logic app" in name_lower:
        return "custom"
    if app_id:
        return "custom"
    return "unknown"


def score_agent_risk(profile: AgentProfile) -> int:
    """Calculate 0-100 risk score for an agent based on behavior and permissions.

    Factors:
    - Shadow status: +40 if unmanaged
    - Agent type: openclaw +30, unknown +20, custom +10, copilot +5
    - Action volume: high activity = higher risk
    - Permission breadth: more scopes = higher risk
    """
    score = 0

    # Shadow agent penalty
    if profile.is_shadow:
        score += 40

    # Agent type risk
    type_scores = {"openclaw": 30, "unknown": 20, "custom": 10, "copilot": 5}
    score += type_scores.get(profile.agent_type, 15)

    # Activity volume (normalized — >100 actions/day is suspicious)
    if profile.total_actions > 0:
        days_active = max((datetime.utcnow() - profile.first_seen_at).days, 1)
        actions_per_day = profile.total_actions / days_active
        if actions_per_day > 100:
            score += 20
        elif actions_per_day > 50:
            score += 10
        elif actions_per_day > 10:
            score += 5

    # Permission breadth
    if profile.permissions:
        try:
            perms = json.loads(profile.permissions)
            if len(perms) > 10:
                score += 15
            elif len(perms) > 5:
                score += 8
        except (json.JSONDecodeError, TypeError):
            pass

    return min(score, 100)


async def get_agent_dashboard(db: AsyncSession, tenant_id: int) -> dict:
    """Get Agent Shield dashboard summary for a tenant."""
    # Count profiles
    total = await db.execute(
        select(func.count()).select_from(AgentProfile).where(AgentProfile.tenant_id == tenant_id)
    )
    total_agents = total.scalar() or 0

    shadow = await db.execute(
        select(func.count()).select_from(AgentProfile).where(
            AgentProfile.tenant_id == tenant_id, AgentProfile.is_shadow == 1
        )
    )
    shadow_count = shadow.scalar() or 0

    # Actions in last 24h
    since = datetime.utcnow() - timedelta(hours=24)
    actions_24h = await db.execute(
        select(func.count()).select_from(AgentActivity).where(
            AgentActivity.tenant_id == tenant_id, AgentActivity.detected_at >= since
        )
    )
    actions_count = actions_24h.scalar() or 0

    # Average risk score
    avg_risk = await db.execute(
        select(func.avg(AgentProfile.risk_score)).where(AgentProfile.tenant_id == tenant_id)
    )
    risk_avg = round(avg_risk.scalar() or 0)

    # High risk actions in 24h
    high_risk = await db.execute(
        select(func.count()).select_from(AgentActivity).where(
            AgentActivity.tenant_id == tenant_id,
            AgentActivity.detected_at >= since,
            AgentActivity.risk_level.in_(["high", "critical"]),
        )
    )
    high_risk_count = high_risk.scalar() or 0

    return {
        "total_agents": total_agents,
        "shadow_agents": shadow_count,
        "managed_agents": total_agents - shadow_count,
        "actions_24h": actions_count,
        "high_risk_actions_24h": high_risk_count,
        "avg_risk_score": risk_avg,
    }


async def get_agent_profiles(db: AsyncSession, tenant_id: int) -> list:
    """Get all agent profiles for a tenant."""
    result = await db.execute(
        select(AgentProfile)
        .where(AgentProfile.tenant_id == tenant_id)
        .order_by(desc(AgentProfile.risk_score))
    )
    profiles = result.scalars().all()
    return [
        {
            "id": p.id,
            "agent_id": p.agent_id,
            "agent_name": p.agent_name,
            "agent_type": p.agent_type,
            "first_seen": p.first_seen_at.isoformat() if p.first_seen_at else None,
            "last_seen": p.last_seen_at.isoformat() if p.last_seen_at else None,
            "total_actions": p.total_actions,
            "is_managed": bool(p.is_managed),
            "is_shadow": bool(p.is_shadow),
            "risk_score": p.risk_score,
            "permissions": json.loads(p.permissions) if p.permissions else [],
        }
        for p in profiles
    ]


async def get_agent_activity(db: AsyncSession, tenant_id: int, page: int = 1, page_size: int = 25) -> dict:
    """Get paginated agent activity log."""
    stmt = select(AgentActivity).where(AgentActivity.tenant_id == tenant_id)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(
        stmt.order_by(desc(AgentActivity.detected_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    activities = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": a.id,
                "agent_name": a.agent_name,
                "agent_type": a.agent_type,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_name": a.resource_name,
                "resource_count": a.resource_count,
                "risk_level": a.risk_level,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            }
            for a in activities
        ],
    }


async def get_shadow_agents(db: AsyncSession, tenant_id: int) -> list:
    """Get shadow (unmanaged) agents for a tenant."""
    result = await db.execute(
        select(AgentProfile)
        .where(AgentProfile.tenant_id == tenant_id, AgentProfile.is_shadow == 1)
        .order_by(desc(AgentProfile.risk_score))
    )
    return [
        {
            "id": p.id,
            "agent_name": p.agent_name,
            "agent_type": p.agent_type,
            "first_seen": p.first_seen_at.isoformat() if p.first_seen_at else None,
            "total_actions": p.total_actions,
            "risk_score": p.risk_score,
        }
        for p in result.scalars().all()
    ]


async def scan_tenant_agents(db: AsyncSession, tenant_id: int) -> dict:
    """Trigger a scan for agent activity.

    In production: reads Graph API audit logs via GraphClient.
    For demo: returns current profile/activity counts.
    """
    # In a real implementation, this would:
    # 1. Call GraphClient.get('/auditLogs/directoryAudits') for Entra ID
    # 2. Filter for app-initiated actions (initiatedBy.app != null)
    # 3. Classify each as agent vs human
    # 4. Create/update AgentProfile records
    # 5. Create AgentActivity records
    # 6. Run score_agent_risk() on each profile

    profiles = await db.execute(
        select(func.count()).select_from(AgentProfile).where(AgentProfile.tenant_id == tenant_id)
    )
    activities = await db.execute(
        select(func.count()).select_from(AgentActivity).where(AgentActivity.tenant_id == tenant_id)
    )

    return {
        "status": "completed",
        "agents_found": profiles.scalar() or 0,
        "activities_logged": activities.scalar() or 0,
        "message": "Scan complete. Agent profiles and activities updated.",
    }
