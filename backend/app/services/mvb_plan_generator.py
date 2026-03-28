"""MVB Plan Generator — computes Minimum Viable Business recovery plans.

Generates pre-computed, criticality-ordered recovery plans that are ready to
execute instantly when an incident occurs. Plans are refreshed every 6 hours
by the scheduler.

MVB (Minimum Viable Business) = the smallest set of users and data needed
for the organization to function. Inspired by Rubrik's concept, but auto-detected
from Microsoft Graph signals rather than manually defined.
"""
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.org_context import UserContext, SiteContext, RecoveryPlan

logger = logging.getLogger(__name__)

# Phase definitions for recovery ordering (NIST-aligned)
PHASE_IDENTITY = {"phase": 1, "name": "Identity Controls", "priority": "immediate"}
PHASE_MVB = {"phase": 2, "name": "Minimum Viable Business", "priority": "critical"}
PHASE_HIGH = {"phase": 3, "name": "High-Priority Data", "priority": "high"}
PHASE_FULL = {"phase": 4, "name": "Full Recovery", "priority": "normal"}


class MVBPlanGenerator:
    """Generates and maintains pre-computed recovery plans for a tenant."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_plan(self, tenant: Tenant, restore_point: datetime = None) -> RecoveryPlan:
        """Generate a full criticality-ordered recovery plan for a tenant.

        The plan is organized into 4 phases:
        1. Identity Controls (Entra ID) — always first
        2. MVB (critical tier users) — executives, admins, legal, finance
        3. High Priority — high tier users and sites
        4. Full Recovery — everything else
        """
        now = datetime.utcnow()
        restore_point = restore_point or now

        # Get all protected objects with their latest snapshots
        objects_with_snapshots = await self._get_recoverable_objects(tenant.id, restore_point)

        if not objects_with_snapshots:
            # Create empty plan
            plan = RecoveryPlan(
                tenant_id=tenant.id,
                name="MVB Recovery Plan",
                plan_type="mvb",
                status="ready",
                phases_json=json.dumps([]),
                computed_at=now,
                stale_after=now + timedelta(hours=6),
            )
            self.db.add(plan)
            await self.db.flush()
            return plan

        # Build phases
        phases = []
        total_items = 0
        total_size = 0
        mvb_users = set()
        mvb_objects = 0

        # Phase 1: Identity Controls (Entra ID objects)
        identity_objects = [
            o for o in objects_with_snapshots
            if o["workload"] == "entra_id"
        ]
        if identity_objects:
            phase_items = sum(o["item_count"] for o in identity_objects)
            phase_size = sum(o["size_bytes"] for o in identity_objects)
            phases.append({
                **PHASE_IDENTITY,
                "objects": identity_objects,
                "object_count": len(identity_objects),
                "item_count": phase_items,
                "size_bytes": phase_size,
                "estimated_minutes": max(5, len(identity_objects) * 2),
                "reason": "Restore identity controls first to prevent re-compromise. Includes Conditional Access policies, admin roles, and OAuth permissions.",
            })
            total_items += phase_items
            total_size += phase_size
            mvb_objects += len(identity_objects)

        # Phase 2: MVB — critical tier users (across all workloads)
        critical_objects = [
            o for o in objects_with_snapshots
            if o["criticality_tier"] == "critical" and o["workload"] != "entra_id"
        ]
        if critical_objects:
            phase_items = sum(o["item_count"] for o in critical_objects)
            phase_size = sum(o["size_bytes"] for o in critical_objects)

            # Collect unique users for MVB count
            for o in critical_objects:
                if o.get("email"):
                    mvb_users.add(o["email"])

            # Build reason from departments
            depts = set()
            for o in critical_objects:
                ctx = o.get("user_context")
                if ctx and ctx.get("department"):
                    depts.add(ctx["department"])
            dept_str = ", ".join(sorted(depts)[:3]) if depts else "critical users"

            phases.append({
                **PHASE_MVB,
                "objects": critical_objects,
                "object_count": len(critical_objects),
                "item_count": phase_items,
                "size_bytes": phase_size,
                "estimated_minutes": max(10, len(critical_objects) * 3),
                "reason": f"Restore {len(mvb_users)} critical users ({dept_str}) — the minimum set needed for business continuity.",
            })
            total_items += phase_items
            total_size += phase_size
            mvb_objects += len(critical_objects)

        # Phase 3: High priority — high tier users and sites
        high_objects = [
            o for o in objects_with_snapshots
            if o["criticality_tier"] == "high" and o["workload"] != "entra_id"
        ]
        if high_objects:
            phase_items = sum(o["item_count"] for o in high_objects)
            phase_size = sum(o["size_bytes"] for o in high_objects)
            phases.append({
                **PHASE_HIGH,
                "objects": high_objects,
                "object_count": len(high_objects),
                "item_count": phase_items,
                "size_bytes": phase_size,
                "estimated_minutes": max(15, len(high_objects) * 3),
                "reason": f"Restore {len(high_objects)} high-priority objects — important users and sites with elevated criticality.",
            })
            total_items += phase_items
            total_size += phase_size

        # Phase 4: Full recovery — medium + low tier
        remaining_objects = [
            o for o in objects_with_snapshots
            if o["criticality_tier"] in ("medium", "low") and o["workload"] != "entra_id"
        ]
        if remaining_objects:
            phase_items = sum(o["item_count"] for o in remaining_objects)
            phase_size = sum(o["size_bytes"] for o in remaining_objects)
            phases.append({
                **PHASE_FULL,
                "objects": remaining_objects,
                "object_count": len(remaining_objects),
                "item_count": phase_items,
                "size_bytes": phase_size,
                "estimated_minutes": max(30, len(remaining_objects) * 5),
                "reason": f"Complete recovery of remaining {len(remaining_objects)} objects.",
            })
            total_items += phase_items
            total_size += phase_size

        total_estimated = sum(p["estimated_minutes"] for p in phases)

        # Serialize phases (strip full object lists for storage, keep summaries)
        phases_for_storage = []
        for phase in phases:
            phase_copy = {k: v for k, v in phase.items() if k != "objects"}
            # Store object references (IDs only) instead of full data
            phase_copy["object_ids"] = [o["object_id"] for o in phase["objects"]]
            # Store object summaries for UI display
            phase_copy["object_summaries"] = [
                {
                    "object_id": o["object_id"],
                    "object_name": o["object_name"],
                    "workload": o["workload"],
                    "snapshot_id": o["snapshot_id"],
                    "snapshot_date": o["snapshot_date"],
                    "item_count": o["item_count"],
                    "size_bytes": o["size_bytes"],
                    "criticality_score": o["criticality_score"],
                    "criticality_tier": o["criticality_tier"],
                }
                for o in phase["objects"]
            ]
            phases_for_storage.append(phase_copy)

        # Delete old plans for this tenant
        old_plans = await self.db.execute(
            select(RecoveryPlan).where(
                RecoveryPlan.tenant_id == tenant.id,
                RecoveryPlan.plan_type == "mvb",
            )
        )
        for old in old_plans.scalars().all():
            await self.db.delete(old)

        # Create new plan
        plan = RecoveryPlan(
            tenant_id=tenant.id,
            name="MVB Recovery Plan",
            plan_type="mvb",
            status="ready",
            mvb_user_count=len(mvb_users),
            mvb_object_count=mvb_objects,
            total_object_count=len(objects_with_snapshots),
            phases_json=json.dumps(phases_for_storage, default=str),
            total_items=total_items,
            total_size_bytes=total_size,
            estimated_minutes=total_estimated,
            reasoning=self._generate_reasoning(phases, len(mvb_users), mvb_objects, len(objects_with_snapshots)),
            computed_at=now,
            stale_after=now + timedelta(hours=6),
        )
        self.db.add(plan)
        await self.db.flush()

        logger.info(
            f"MVB plan generated for tenant {tenant.name}: "
            f"{len(phases)} phases, {len(objects_with_snapshots)} objects, "
            f"MVB={len(mvb_users)} users, est. {total_estimated} min"
        )

        return plan

    async def _get_recoverable_objects(self, tenant_id: int, restore_point: datetime) -> list:
        """Get all protected objects with their latest snapshot and criticality context."""
        result = await self.db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )
        objects = result.scalars().all()

        recoverable = []
        for obj in objects:
            # Find latest snapshot before restore point
            snap_result = await self.db.execute(
                select(Snapshot).where(
                    Snapshot.protected_object_id == obj.id,
                    Snapshot.status == SnapshotStatus.COMPLETED,
                    Snapshot.completed_at <= restore_point,
                ).order_by(desc(Snapshot.completed_at)).limit(1)
            )
            snapshot = snap_result.scalar_one_or_none()
            if not snapshot:
                continue

            # Get user context if available
            user_ctx = None
            if obj.workload_type in (WorkloadType.EXCHANGE, WorkloadType.ONEDRIVE, WorkloadType.TEAMS):
                ctx_result = await self.db.execute(
                    select(UserContext).where(
                        UserContext.tenant_id == tenant_id,
                        UserContext.ms_user_id == obj.ms_object_id,
                    )
                )
                uc = ctx_result.scalar_one_or_none()
                if uc:
                    user_ctx = {
                        "department": uc.department,
                        "job_title": uc.job_title,
                        "is_global_admin": bool(uc.is_global_admin),
                        "has_privileged_role": bool(uc.has_privileged_role),
                        "is_vip": bool(uc.is_vip),
                    }

            recoverable.append({
                "object_id": obj.id,
                "object_name": obj.display_name,
                "workload": obj.workload_type.value,
                "email": obj.email,
                "criticality_score": obj.criticality_score or 50,
                "criticality_tier": obj.criticality_tier or "medium",
                "snapshot_id": snapshot.id,
                "snapshot_date": snapshot.completed_at.isoformat() if snapshot.completed_at else None,
                "item_count": snapshot.item_count or 0,
                "size_bytes": snapshot.size_bytes or 0,
                "user_context": user_ctx,
            })

        # Sort by criticality score descending within each phase
        recoverable.sort(key=lambda x: x["criticality_score"], reverse=True)
        return recoverable

    def _generate_reasoning(self, phases: list, mvb_users: int, mvb_objects: int, total_objects: int) -> str:
        """Generate human-readable reasoning for the plan."""
        parts = [f"Generated {len(phases)}-phase recovery plan for {total_objects} objects."]

        if mvb_users > 0:
            parts.append(
                f"MVB set: {mvb_users} critical users ({mvb_objects} objects) "
                f"will be restored first for business continuity."
            )

        for phase in phases:
            parts.append(
                f"Phase {phase['phase']} ({phase['name']}): "
                f"{phase.get('object_count', 0)} objects, ~{phase.get('estimated_minutes', 0)} min. "
                f"{phase.get('reason', '')}"
            )

        return " ".join(parts)
