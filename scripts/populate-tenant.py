#!/usr/bin/env python3
"""Populate a tenant with realistic test data for demo/onboarding.

Creates test users in the M365 tenant via Graph API, then runs
org-context sync + criticality scoring to produce a compelling
Intelligence Map with all 4 tiers populated.

Usage:
  docker compose exec backend python3 scripts/populate-tenant.py --tenant-id 3
  docker compose exec backend python3 scripts/populate-tenant.py --tenant-id 3 --skip-graph  # DB only, no Graph API
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Realistic org structure — 15 users across 4 criticality tiers
DEMO_ORG = [
    # Critical tier (score 80+) — C-suite, Global Admin
    {"name": "Gopal Patwa", "title": "Chief Executive Officer", "dept": "Executive", "admin": True, "reports": 4, "tier": "critical"},
    # High tier (score 60-79) — VPs, Directors with privileged roles
    {"name": "Priya Sharma", "title": "VP Engineering", "dept": "Engineering", "admin": False, "reports": 3, "tier": "high"},
    {"name": "David Chen", "title": "VP Sales", "dept": "Sales", "admin": False, "reports": 2, "tier": "high"},
    {"name": "Rachel Kim", "title": "CFO", "dept": "Finance", "admin": False, "reports": 2, "tier": "high"},
    # Medium tier (score 40-59) — Directors, Senior Managers
    {"name": "Emily Davis", "title": "Director of HR", "dept": "HR", "admin": False, "reports": 2, "tier": "medium"},
    {"name": "James Wilson", "title": "Director of Finance", "dept": "Finance", "admin": False, "reports": 1, "tier": "medium"},
    {"name": "Lisa Thompson", "title": "Director of IT", "dept": "IT", "admin": False, "reports": 2, "tier": "medium"},
    {"name": "Alex Johnson", "title": "Senior Architect", "dept": "Engineering", "admin": False, "reports": 1, "tier": "medium"},
    {"name": "Sarah Chen", "title": "Head of Marketing", "dept": "Marketing", "admin": False, "reports": 1, "tier": "medium"},
    # Low tier (score <40) — Individual contributors
    {"name": "Mike Williams", "title": "Sales Representative", "dept": "Sales", "admin": False, "reports": 0, "tier": "low"},
    {"name": "Tom Nakamura", "title": "Software Engineer", "dept": "Engineering", "admin": False, "reports": 0, "tier": "low"},
    {"name": "Fatima Al-Zahra", "title": "Account Executive", "dept": "Sales", "admin": False, "reports": 0, "tier": "low"},
    {"name": "Ben Cooper", "title": "DevOps Engineer", "dept": "Engineering", "admin": False, "reports": 0, "tier": "low"},
    {"name": "Mia Santos", "title": "Marketing Analyst", "dept": "Marketing", "admin": False, "reports": 0, "tier": "low"},
    {"name": "Jake Morrison", "title": "Financial Analyst", "dept": "Finance", "admin": False, "reports": 0, "tier": "low"},
]

# Tier score ranges
TIER_SCORES = {
    "critical": (85, 95),
    "high": (65, 79),
    "medium": (45, 59),
    "low": (20, 38),
}


async def populate_db_only(tenant_id: int):
    """Populate user_contexts directly in DB (no Graph API calls)."""
    from app.database import engine
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Clear existing user_contexts for this tenant
        await conn.execute(text("DELETE FROM user_contexts WHERE tenant_id = :tid").bindparams(tid=tenant_id))

        for i, user in enumerate(DEMO_ORG):
            lo, hi = TIER_SCORES[user["tier"]]
            score = lo + (hi - lo) * (len(DEMO_ORG) - i) // len(DEMO_ORG)
            email_prefix = user["name"].lower().replace(" ", ".").replace("-", "")
            ms_id = f"user-{email_prefix}"

            # Determine manager
            manager_id = None
            if user["tier"] == "high":
                manager_id = "user-gopal.patwa"
            elif user["tier"] == "medium":
                # Assign to a VP
                vps = [u for u in DEMO_ORG if u["tier"] == "high"]
                if vps:
                    vp = vps[i % len(vps)]
                    manager_id = f"user-{vp['name'].lower().replace(' ', '.').replace('-', '')}"
            elif user["tier"] == "low":
                # Assign to a director
                dirs = [u for u in DEMO_ORG if u["tier"] == "medium"]
                if dirs:
                    d = dirs[i % len(dirs)]
                    manager_id = f"user-{d['name'].lower().replace(' ', '.').replace('-', '')}"

            await conn.execute(text("""
                INSERT INTO user_contexts (tenant_id, ms_user_id, display_name, email, job_title, department,
                    criticality_score, criticality_tier, is_global_admin, has_privileged_role,
                    direct_reports_count, manager_ms_id, synced_at, computed_at, created_at, updated_at)
                VALUES (:tid, :ms_id, :name, :email, :title, :dept, :score, :tier, :admin, :priv,
                    :reports, :mgr, NOW(), NOW(), NOW(), NOW())
            """).bindparams(
                tid=tenant_id, ms_id=ms_id, name=user["name"],
                email=f"{email_prefix}@patwainc.onmicrosoft.com",
                title=user["title"], dept=user["dept"],
                score=score, tier=user["tier"],
                admin=1 if user["admin"] else 0,
                priv=1 if user["admin"] or user["tier"] in ("critical", "high") else 0,
                reports=user["reports"],
                mgr=manager_id,
            ))

        logger.info(f"Populated {len(DEMO_ORG)} users for tenant {tenant_id}")

        # Verify
        r = await conn.execute(text("""
            SELECT criticality_tier, count(*), round(avg(criticality_score))
            FROM user_contexts WHERE tenant_id = :tid
            GROUP BY criticality_tier ORDER BY
            CASE criticality_tier WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END
        """).bindparams(tid=tenant_id))
        for row in r.all():
            logger.info(f"  {row[0]}: {row[1]} users (avg score {row[2]})")


async def populate_with_graph(tenant_id: int):
    """Sync from Graph API then supplement with additional users if needed."""
    from app.database import async_session
    from app.services.context_collector import ContextCollectorService
    from app.services.criticality_scorer import CriticalityScorer
    from sqlalchemy import text

    async with async_session() as db:
        # Get tenant
        from app.models.tenant import Tenant
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return

        # Run real Graph sync
        logger.info(f"Syncing org context for '{tenant.name}' from Graph API...")
        collector = ContextCollectorService(db)
        await collector.collect_all(tenant)

        # Score
        scorer = CriticalityScorer(db)
        await scorer.score_all(tenant_id)
        await db.commit()

        # Check results
        r = await db.execute(text("""
            SELECT criticality_tier, count(*) FROM user_contexts WHERE tenant_id = :tid
            GROUP BY criticality_tier
        """).bindparams(tid=tenant_id))
        tiers = {row[0]: row[1] for row in r.all()}
        total = sum(tiers.values())

        logger.info(f"Graph sync: {total} users — {tiers}")

        # If fewer than 10 users, supplement with DB-only users
        if total < 10:
            logger.info(f"Only {total} users from Graph. Supplementing with demo users...")
            await populate_db_only(tenant_id)
        else:
            logger.info(f"Sufficient users from Graph ({total}). No supplementation needed.")


async def main():
    parser = argparse.ArgumentParser(description="Populate tenant with demo data")
    parser.add_argument("--tenant-id", type=int, required=True, help="Tenant ID to populate")
    parser.add_argument("--skip-graph", action="store_true", help="Skip Graph API, populate DB directly")
    args = parser.parse_args()

    if args.skip_graph:
        await populate_db_only(args.tenant_id)
    else:
        await populate_with_graph(args.tenant_id)


if __name__ == "__main__":
    asyncio.run(main())
