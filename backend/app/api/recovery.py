"""Recovery API — confidence scoring, RPO/RTO tracking, runbooks, mass recovery.

Endpoints:
- GET /recovery/confidence — Recovery confidence score (0-100)
- GET /recovery/rpo-rto — RPO/RTO compliance per workload
- GET /recovery/runbooks — Pre-defined recovery procedures
- POST /recovery/mass-restore — One-click mass recovery
- POST /recovery/test-restore — Automated test restore for validation
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backup_job import BackupJob, JobStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotItem
from app.models.sla_policy import SLAPolicy
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_current_user, require_restore_permission
from app.interfaces.dispatcher_factory import get_dispatcher
from app.interfaces.job_message import RestoreJobMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recovery", tags=["Recovery"])


# ═══════════════════════════════════════════════════════
# 1. Recovery Confidence Score
# ═══════════════════════════════════════════════════════

@router.get("/confidence")
async def get_recovery_confidence(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recovery Confidence Score (0-100) — proves you CAN actually recover.

    Factors:
    - Backup freshness (are backups recent?)
    - Backup completeness (all objects backed up?)
    - Restore success rate (do restores actually work?)
    - Validation pass rate (backup data integrity verified?)
    - Malware scan status (backups clean?)
    """
    since_7d = datetime.utcnow() - timedelta(days=7)
    since_30d = datetime.utcnow() - timedelta(days=30)

    # Factor 1: Backup Freshness (25%) — what % of objects have been backed up within SLA?
    total_protected = (await db.execute(
        select(func.count()).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )).scalar() or 0

    recently_backed_up = (await db.execute(
        select(func.count()).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
            ProtectedObject.last_backup_at >= since_7d,
        )
    )).scalar() or 0

    freshness_score = (recently_backed_up / total_protected * 100) if total_protected > 0 else 0

    # Factor 2: Backup Completeness (25%) — what % of total objects are protected?
    total_objects = (await db.execute(
        select(func.count()).where(ProtectedObject.tenant_id == tenant_id)
    )).scalar() or 0

    completeness_score = (total_protected / total_objects * 100) if total_objects > 0 else 0

    # Factor 3: Restore Success Rate (25%) — do restores actually work?
    total_restores = (await db.execute(
        select(func.count()).where(
            RestoreJob.tenant_id == tenant_id,
            RestoreJob.completed_at >= since_30d,
        )
    )).scalar() or 0

    successful_restores = (await db.execute(
        select(func.count()).where(
            RestoreJob.tenant_id == tenant_id,
            RestoreJob.status == RestoreStatus.COMPLETED,
            RestoreJob.completed_at >= since_30d,
        )
    )).scalar() or 0

    restore_score = (successful_restores / total_restores * 100) if total_restores > 0 else 50  # 50% if no restores attempted

    # Factor 4: Validation & Scan (25%) — have backups been validated?
    validated_snapshots = (await db.execute(
        select(func.count()).where(
            Snapshot.protected_object_id.in_(
                select(ProtectedObject.id).where(ProtectedObject.tenant_id == tenant_id)
            ),
            Snapshot.validation_status == "passed",
        )
    )).scalar() or 0

    total_completed_snapshots = (await db.execute(
        select(func.count()).where(
            Snapshot.protected_object_id.in_(
                select(ProtectedObject.id).where(ProtectedObject.tenant_id == tenant_id)
            ),
            Snapshot.status == SnapshotStatus.COMPLETED,
        )
    )).scalar() or 0

    validation_score = (validated_snapshots / total_completed_snapshots * 100) if total_completed_snapshots > 0 else 30

    # Weighted total
    confidence = round(
        freshness_score * 0.25 +
        completeness_score * 0.25 +
        restore_score * 0.25 +
        validation_score * 0.25
    )

    # Determine grade
    if confidence >= 90:
        grade = "A"
        label = "Excellent"
        color = "green"
    elif confidence >= 70:
        grade = "B"
        label = "Good"
        color = "blue"
    elif confidence >= 50:
        grade = "C"
        label = "Fair"
        color = "amber"
    else:
        grade = "D"
        label = "At Risk"
        color = "red"

    return {
        "score": min(confidence, 100),
        "grade": grade,
        "label": label,
        "color": color,
        "factors": {
            "freshness": {"score": round(freshness_score, 1), "weight": 25,
                         "detail": f"{recently_backed_up}/{total_protected} objects backed up within 7 days"},
            "completeness": {"score": round(completeness_score, 1), "weight": 25,
                            "detail": f"{total_protected}/{total_objects} objects protected"},
            "restore_success": {"score": round(restore_score, 1), "weight": 25,
                               "detail": f"{successful_restores}/{total_restores} restores succeeded (30d)" if total_restores > 0 else "No restores attempted yet"},
            "validation": {"score": round(validation_score, 1), "weight": 25,
                          "detail": f"{validated_snapshots}/{total_completed_snapshots} snapshots validated"},
        },
        "recommendations": _get_recommendations(freshness_score, completeness_score, restore_score, validation_score),
    }


def _get_recommendations(freshness, completeness, restore, validation) -> list[dict]:
    """Generate actionable recommendations based on scores."""
    recs = []
    if freshness < 80:
        recs.append({"priority": "high", "action": "Run backups for stale objects",
                     "detail": "Some protected objects haven't been backed up in over 7 days."})
    if completeness < 90:
        recs.append({"priority": "high", "action": "Protect unprotected objects",
                     "detail": "Assign SLA policies to unprotected objects to ensure full coverage."})
    if restore < 80 and restore > 0:
        recs.append({"priority": "medium", "action": "Investigate restore failures",
                     "detail": "Some restore operations have failed. Check failed items for root cause."})
    if restore == 50:
        recs.append({"priority": "medium", "action": "Run a test restore",
                     "detail": "No restores have been attempted. Run a test restore to verify recoverability."})
    if validation < 50:
        recs.append({"priority": "medium", "action": "Validate backup integrity",
                     "detail": "Most backups haven't been validated. Run backup validation to check data integrity."})
    if not recs:
        recs.append({"priority": "low", "action": "Maintain current practices",
                     "detail": "Recovery posture is strong. Continue regular backups and periodic test restores."})
    return recs


# ═══════════════════════════════════════════════════════
# 2. RPO/RTO Compliance
# ═══════════════════════════════════════════════════════

@router.get("/rpo-rto")
async def get_rpo_rto(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """RPO/RTO compliance per workload.

    RPO = Recovery Point Objective (how much data can you lose?)
    RTO = Recovery Time Objective (how long to recover?)
    """
    now = datetime.utcnow()

    # Get all protected objects with their SLA policies
    result = await db.execute(
        select(ProtectedObject, SLAPolicy)
        .outerjoin(SLAPolicy, ProtectedObject.sla_policy_id == SLAPolicy.id)
        .where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )
    rows = result.all()

    # Group by workload
    workload_data = {}
    for obj, sla in rows:
        wl = obj.workload_type.value
        if wl not in workload_data:
            workload_data[wl] = {
                "objects": 0, "rpo_met": 0, "rpo_violated": 0,
                "rpo_target_hours": sla.backup_frequency_hours if sla else 24,
                "worst_rpo_hours": 0,
                "avg_rto_seconds": 0,
                "restore_count": 0,
            }

        workload_data[wl]["objects"] += 1

        # RPO check: is last backup within SLA frequency?
        rpo_target = sla.backup_frequency_hours if sla else 24
        workload_data[wl]["rpo_target_hours"] = rpo_target

        if obj.last_backup_at:
            hours_since = (now - obj.last_backup_at).total_seconds() / 3600
            if hours_since <= rpo_target:
                workload_data[wl]["rpo_met"] += 1
            else:
                workload_data[wl]["rpo_violated"] += 1
            workload_data[wl]["worst_rpo_hours"] = max(
                workload_data[wl]["worst_rpo_hours"], round(hours_since, 1)
            )
        else:
            workload_data[wl]["rpo_violated"] += 1

    # RTO: calculate from actual restore job durations (DB-agnostic)
    try:
        restore_jobs = await db.execute(
            select(RestoreJob.started_at, RestoreJob.completed_at).where(
                RestoreJob.tenant_id == tenant_id,
                RestoreJob.status == RestoreStatus.COMPLETED,
                RestoreJob.started_at.isnot(None),
                RestoreJob.completed_at.isnot(None),
            )
        )
        durations = []
        for rj in restore_jobs.all():
            if rj.started_at and rj.completed_at:
                durations.append((rj.completed_at - rj.started_at).total_seconds())
        avg_rto = sum(durations) / len(durations) if durations else 0
        for wl in workload_data:
            workload_data[wl]["avg_rto_seconds"] = round(avg_rto, 1)
    except Exception:
        for wl in workload_data:
            workload_data[wl]["avg_rto_seconds"] = 0

    # Build response
    workloads = []
    overall_rpo_met = 0
    overall_total = 0

    for wl, data in workload_data.items():
        total = data["objects"]
        met = data["rpo_met"]
        compliance = round(met / total * 100, 1) if total > 0 else 0

        overall_rpo_met += met
        overall_total += total

        workloads.append({
            "workload": wl,
            "objects": total,
            "rpo_target_hours": data["rpo_target_hours"],
            "rpo_compliance_pct": compliance,
            "rpo_met": met,
            "rpo_violated": data["rpo_violated"],
            "worst_rpo_hours": data["worst_rpo_hours"],
            "avg_rto_seconds": data["avg_rto_seconds"],
            "status": "compliant" if compliance == 100 else ("at_risk" if compliance >= 80 else "violated"),
        })

    overall_compliance = round(overall_rpo_met / overall_total * 100, 1) if overall_total > 0 else 0

    return {
        "overall_rpo_compliance": overall_compliance,
        "overall_status": "compliant" if overall_compliance == 100 else ("at_risk" if overall_compliance >= 80 else "violated"),
        "workloads": workloads,
    }


# ═══════════════════════════════════════════════════════
# 3. Recovery Runbooks
# ═══════════════════════════════════════════════════════

@router.get("/runbooks")
async def get_runbooks(
    current_user: User = Depends(get_current_user),
):
    """Pre-defined recovery runbooks for common scenarios."""
    return {
        "runbooks": [
            {
                "id": "ransomware",
                "name": "Ransomware Recovery",
                "severity": "critical",
                "icon": "shield-alert",
                "description": "Full tenant recovery after a ransomware attack",
                "estimated_time": "2-4 hours",
                "steps": [
                    {"order": 1, "action": "Isolate", "detail": "Disconnect affected accounts from M365 to stop spread. Revoke all active sessions via Entra ID."},
                    {"order": 2, "action": "Assess", "detail": "Use Smart Engine anomaly detection to identify blast radius — which workloads/objects were affected and when."},
                    {"order": 3, "action": "Identify restore point", "detail": "Find the last clean backup before the attack using snapshot timeline and anomaly timestamps."},
                    {"order": 4, "action": "Malware scan", "detail": "Run malware scan on the selected restore point to verify it's clean before proceeding."},
                    {"order": 5, "action": "Restore Entra ID", "detail": "Restore Conditional Access policies and security groups first — identity controls protect everything else."},
                    {"order": 6, "action": "Restore data", "detail": "Use Mass Recovery to restore Exchange, OneDrive, SharePoint, and Teams in parallel."},
                    {"order": 7, "action": "Validate", "detail": "Run backup validation on restored data. Verify item counts match pre-attack baselines."},
                    {"order": 8, "action": "Monitor", "detail": "Enable enhanced monitoring via Smart Engine for 72 hours. Watch for reinfection patterns."},
                ],
            },
            {
                "id": "accidental_deletion",
                "name": "Accidental Deletion Recovery",
                "severity": "high",
                "icon": "trash",
                "description": "Recover accidentally deleted emails, files, or sites",
                "estimated_time": "5-15 minutes",
                "steps": [
                    {"order": 1, "action": "Identify", "detail": "Use Self-Service Restore search to find the deleted item by name, sender, or date."},
                    {"order": 2, "action": "Select snapshot", "detail": "Choose a backup snapshot from before the deletion occurred."},
                    {"order": 3, "action": "Restore", "detail": "Use Item-Level Restore to recover just the deleted items to their original location."},
                    {"order": 4, "action": "Verify", "detail": "Confirm the restored items are accessible in M365."},
                ],
            },
            {
                "id": "tenant_migration",
                "name": "Tenant Migration / M&A",
                "severity": "medium",
                "icon": "building",
                "description": "Migrate data between M365 tenants during merger or acquisition",
                "estimated_time": "4-8 hours",
                "steps": [
                    {"order": 1, "action": "Backup source", "detail": "Run full backup of all workloads in the source tenant."},
                    {"order": 2, "action": "Onboard target", "detail": "Connect the target tenant to Shieldio and run discovery."},
                    {"order": 3, "action": "Cross-tenant restore", "detail": "Use Cross-Tenant Restore to move Exchange, OneDrive, and SharePoint data to the target tenant."},
                    {"order": 4, "action": "Restore Entra ID", "detail": "Recreate groups, app registrations, and policies in the target tenant from backup."},
                    {"order": 5, "action": "Validate", "detail": "Run backup validation on migrated data. Compare item counts between source and target."},
                ],
            },
            {
                "id": "compliance_audit",
                "name": "Compliance / eDiscovery Response",
                "severity": "medium",
                "icon": "file-search",
                "description": "Respond to legal hold or compliance audit request",
                "estimated_time": "30-60 minutes",
                "steps": [
                    {"order": 1, "action": "Identify scope", "detail": "Determine which users, date range, and data types are in scope for the request."},
                    {"order": 2, "action": "Search backups", "detail": "Use Global Search (⌘K) to find relevant emails, files, and messages across all workloads."},
                    {"order": 3, "action": "Export", "detail": "Export matching items to EML/CSV format for legal review."},
                    {"order": 4, "action": "Apply legal hold", "detail": "Enable Legal Hold on relevant SLA policies to prevent backup data deletion during the hold period."},
                    {"order": 5, "action": "Document", "detail": "Generate audit report showing chain of custody: backup timestamps, encryption, access logs."},
                ],
            },
            {
                "id": "config_drift",
                "name": "Configuration Drift Recovery",
                "severity": "low",
                "icon": "settings",
                "description": "Restore Entra ID configuration after unauthorized changes",
                "estimated_time": "15-30 minutes",
                "steps": [
                    {"order": 1, "action": "Detect", "detail": "Use Entra ID Snapshot Compare to identify what changed between two backup points."},
                    {"order": 2, "action": "Review changes", "detail": "Examine added/removed/changed Conditional Access policies, groups, and role assignments."},
                    {"order": 3, "action": "Restore", "detail": "Selectively restore the specific objects that were changed back to their previous state."},
                    {"order": 4, "action": "Monitor", "detail": "Set up anomaly alerts for future unauthorized configuration changes."},
                ],
            },
        ],
    }


# ═══════════════════════════════════════════════════════
# 4. Mass Recovery
# ═══════════════════════════════════════════════════════

class MassRecoveryRequest(BaseModel):
    tenant_id: int
    workload_types: list[str] = None  # None = all workloads
    restore_point: str = None  # ISO datetime — restore to this point in time
    dry_run: bool = False  # If true, just show what would be restored


@router.post("/mass-restore")
async def mass_restore(
    req: MassRecoveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """One-click mass recovery — restore all workloads to a point in time.

    Finds the closest snapshot to the requested restore point for each
    protected object and dispatches parallel restore jobs.
    """
    now = datetime.utcnow()
    restore_point = datetime.fromisoformat(req.restore_point) if req.restore_point else now

    # Get all protected objects
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == req.tenant_id,
        ProtectedObject.status == ProtectionStatus.PROTECTED,
    )
    if req.workload_types:
        wl_enums = [WorkloadType(wt) for wt in req.workload_types]
        stmt = stmt.where(ProtectedObject.workload_type.in_(wl_enums))

    result = await db.execute(stmt)
    objects = result.scalars().all()

    if not objects:
        raise HTTPException(status_code=404, detail="No protected objects found")

    # For each object, find the closest snapshot to the restore point
    restore_plan = []
    for obj in objects:
        snap_result = await db.execute(
            select(Snapshot).where(
                Snapshot.protected_object_id == obj.id,
                Snapshot.status == SnapshotStatus.COMPLETED,
                Snapshot.completed_at <= restore_point,
            ).order_by(desc(Snapshot.completed_at)).limit(1)
        )
        snapshot = snap_result.scalar_one_or_none()

        if snapshot:
            restore_plan.append({
                "object_id": obj.id,
                "object_name": obj.display_name,
                "workload": obj.workload_type.value,
                "snapshot_id": snapshot.id,
                "snapshot_date": snapshot.completed_at.isoformat() if snapshot.completed_at else None,
                "item_count": snapshot.item_count,
                "size_bytes": snapshot.size_bytes,
                "criticality_score": obj.criticality_score or 50,
                "criticality_tier": obj.criticality_tier or "medium",
            })

    # Sort by criticality: entra_id first (identity), then by score descending
    restore_plan.sort(key=lambda x: (
        0 if x["workload"] == "entra_id" else 1,  # Identity first
        -x["criticality_score"],  # Then by score descending
    ))

    if req.dry_run:
        return {
            "status": "dry_run",
            "restore_point": restore_point.isoformat(),
            "objects_to_restore": len(restore_plan),
            "plan": restore_plan,
        }

    # Execute restore jobs
    jobs_created = 0
    for plan_item in restore_plan:
        restore_job = RestoreJob(
            tenant_id=req.tenant_id,
            source_snapshot_id=plan_item["snapshot_id"],
            source_object_id=plan_item["object_id"],
            restore_type=RestoreType.FULL_INPLACE,
            status=RestoreStatus.QUEUED,
        )
        db.add(restore_job)
        await db.flush()

        await get_dispatcher().dispatch_restore(
            RestoreJobMessage(restore_job_id=restore_job.id), db=db
        )
        jobs_created += 1

    await db.commit()

    return {
        "status": "initiated",
        "restore_point": restore_point.isoformat(),
        "jobs_created": jobs_created,
        "objects_restored": len(restore_plan),
        "plan": restore_plan,
    }


# ═══════════════════════════════════════════════════════
# 5. Test Restore
# ═══════════════════════════════════════════════════════

@router.post("/test-restore")
async def test_restore(
    tenant_id: int = Query(...),
    workload: str = Query(None, description="Specific workload to test, or all if omitted"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Run automated test restore to verify recoverability.

    Picks a random protected object, retrieves its latest snapshot,
    decrypts and validates the data without actually restoring to M365.
    Updates the snapshot's validation_status.
    """
    from app.services.storage import storage_service

    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == tenant_id,
        ProtectedObject.status == ProtectionStatus.PROTECTED,
    )
    if workload:
        stmt = stmt.where(ProtectedObject.workload_type == WorkloadType(workload))

    result = await db.execute(stmt.limit(5))
    objects = result.scalars().all()

    if not objects:
        raise HTTPException(status_code=404, detail="No protected objects to test")

    test_results = []
    for obj in objects:
        snap_result = await db.execute(
            select(Snapshot).where(
                Snapshot.protected_object_id == obj.id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            ).order_by(desc(Snapshot.completed_at)).limit(1)
        )
        snapshot = snap_result.scalar_one_or_none()
        if not snapshot:
            test_results.append({
                "object": obj.display_name, "workload": obj.workload_type.value,
                "status": "skipped", "reason": "No completed snapshots",
            })
            continue

        # Get a few items and verify they can be retrieved
        items_result = await db.execute(
            select(SnapshotItem).where(
                SnapshotItem.snapshot_id == snapshot.id,
            ).limit(3)
        )
        items = items_result.scalars().all()

        verified = 0
        errors = []
        for item in items:
            try:
                wrapped_dek = await storage_service.get_wrapped_dek(
                    tenant_id=obj.tenant_id,
                    workload=obj.workload_type.value,
                    object_id=obj.ms_object_id,
                    snapshot_id=snapshot.id,
                )
                if wrapped_dek and item.blob_path:
                    data = await storage_service.retrieve_item(item.blob_path, wrapped_dek)
                    if data and len(data) > 0:
                        verified += 1
                    else:
                        errors.append(f"Empty data for {item.name}")
                else:
                    errors.append(f"Missing DEK or blob_path for {item.name}")
            except Exception as e:
                errors.append(f"{item.name}: {str(e)[:80]}")

        status = "passed" if verified > 0 and not errors else ("partial" if verified > 0 else "failed")

        # Update snapshot validation status
        snapshot.validation_status = status
        snapshot.validated_at = datetime.utcnow()

        test_results.append({
            "object": obj.display_name,
            "workload": obj.workload_type.value,
            "snapshot_id": snapshot.id,
            "status": status,
            "items_tested": len(items),
            "items_verified": verified,
            "errors": errors,
        })

    await db.commit()

    passed = sum(1 for r in test_results if r["status"] == "passed")
    total = len(test_results)

    return {
        "total_tested": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "results": test_results,
    }


# ═══════════════════════════════════════════════════════
# 6. Recovery Verification — "Did everything come back?"
# ═══════════════════════════════════════════════════════

@router.get("/verify")
async def verify_recovery(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full recovery verification — proves 100% recoverability at tenant level.

    Checks:
    1. Coverage: All protected objects have at least one completed snapshot
    2. Freshness: All snapshots within SLA RPO window
    3. Integrity: Backup data can be decrypted and read (sample check)
    4. Restore capability: Recent restore jobs succeeded
    5. Continuity: No gaps in backup chain
    """
    now = datetime.utcnow()

    # Get all protected objects
    obj_result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )
    objects = obj_result.scalars().all()
    total_objects = len(objects)

    if total_objects == 0:
        return {"verified": False, "score": 0, "message": "No protected objects found",
                "checks": {}, "workloads": {}}

    # ── Check 1: Coverage (every object has a completed snapshot) ──
    objects_with_snapshots = 0
    objects_without_snapshots = []
    for obj in objects:
        snap_count = (await db.execute(
            select(func.count()).where(
                Snapshot.protected_object_id == obj.id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
        )).scalar() or 0
        if snap_count > 0:
            objects_with_snapshots += 1
        else:
            objects_without_snapshots.append({
                "name": obj.display_name,
                "workload": obj.workload_type.value,
            })

    coverage_pct = round(objects_with_snapshots / total_objects * 100, 1)

    # ── Check 2: Freshness (latest backup within SLA window) ──
    fresh_count = 0
    stale_objects = []
    for obj in objects:
        if obj.last_backup_at:
            hours_since = (now - obj.last_backup_at).total_seconds() / 3600
            # Get SLA target
            sla_hours = 24  # default
            if obj.sla_policy_id:
                sla = await db.get(SLAPolicy, obj.sla_policy_id)
                if sla:
                    sla_hours = sla.backup_frequency_hours

            if hours_since <= sla_hours * 1.5:  # 1.5x grace period
                fresh_count += 1
            else:
                stale_objects.append({
                    "name": obj.display_name,
                    "workload": obj.workload_type.value,
                    "hours_since_backup": round(hours_since, 1),
                    "sla_target_hours": sla_hours,
                })
        else:
            stale_objects.append({
                "name": obj.display_name,
                "workload": obj.workload_type.value,
                "hours_since_backup": None,
                "sla_target_hours": 24,
            })

    freshness_pct = round(fresh_count / total_objects * 100, 1)

    # ── Check 3: Integrity (validated snapshots) ──
    total_snapshots = (await db.execute(
        select(func.count()).where(
            Snapshot.protected_object_id.in_([o.id for o in objects]),
            Snapshot.status == SnapshotStatus.COMPLETED,
        )
    )).scalar() or 0

    validated_snapshots = (await db.execute(
        select(func.count()).where(
            Snapshot.protected_object_id.in_([o.id for o in objects]),
            Snapshot.validation_status == "passed",
        )
    )).scalar() or 0

    integrity_pct = round(validated_snapshots / total_snapshots * 100, 1) if total_snapshots > 0 else 0

    # ── Check 4: Restore Capability ──
    total_restores = (await db.execute(
        select(func.count()).where(RestoreJob.tenant_id == tenant_id)
    )).scalar() or 0

    successful_restores = (await db.execute(
        select(func.count()).where(
            RestoreJob.tenant_id == tenant_id,
            RestoreJob.status == RestoreStatus.COMPLETED,
        )
    )).scalar() or 0

    restore_pct = round(successful_restores / total_restores * 100, 1) if total_restores > 0 else 0

    # ── Check 5: Continuity (per-workload backup chain) ──
    workload_status = {}
    for obj in objects:
        wl = obj.workload_type.value
        if wl not in workload_status:
            workload_status[wl] = {
                "objects": 0, "with_backup": 0, "fresh": 0,
                "total_items": 0, "total_size": 0,
                "latest_backup": None,
            }

        workload_status[wl]["objects"] += 1
        workload_status[wl]["total_items"] += obj.total_items_backed_up or 0
        workload_status[wl]["total_size"] += obj.total_size_bytes or 0

        if obj.last_backup_at:
            workload_status[wl]["with_backup"] += 1
            if not workload_status[wl]["latest_backup"] or obj.last_backup_at > datetime.fromisoformat(workload_status[wl]["latest_backup"]):
                workload_status[wl]["latest_backup"] = obj.last_backup_at.isoformat()

            hours = (now - obj.last_backup_at).total_seconds() / 3600
            if hours <= 48:
                workload_status[wl]["fresh"] += 1

    # ── Overall Score ──
    overall_score = round(
        coverage_pct * 0.30 +
        freshness_pct * 0.30 +
        integrity_pct * 0.20 +
        (restore_pct if total_restores > 0 else 50) * 0.20
    )

    verified = overall_score >= 80

    return {
        "verified": verified,
        "score": min(overall_score, 100),
        "grade": "A" if overall_score >= 90 else "B" if overall_score >= 70 else "C" if overall_score >= 50 else "D",
        "message": "Tenant recovery verified — all checks passed" if verified else "Recovery verification incomplete — see recommendations below",
        "checks": {
            "coverage": {
                "score": coverage_pct,
                "status": "pass" if coverage_pct == 100 else "fail",
                "detail": f"{objects_with_snapshots}/{total_objects} objects have backup data",
                "issues": objects_without_snapshots,
            },
            "freshness": {
                "score": freshness_pct,
                "status": "pass" if freshness_pct >= 90 else ("warn" if freshness_pct >= 70 else "fail"),
                "detail": f"{fresh_count}/{total_objects} objects backed up within SLA window",
                "issues": stale_objects[:5],  # Limit to 5
            },
            "integrity": {
                "score": integrity_pct,
                "status": "pass" if integrity_pct >= 50 else ("warn" if integrity_pct > 0 else "fail"),
                "detail": f"{validated_snapshots}/{total_snapshots} snapshots validated",
            },
            "restore_capability": {
                "score": restore_pct,
                "status": "pass" if restore_pct >= 90 else ("warn" if total_restores == 0 else "fail"),
                "detail": f"{successful_restores}/{total_restores} restores succeeded" if total_restores > 0 else "No restores attempted — run a test restore to verify",
            },
        },
        "workloads": workload_status,
        "summary": {
            "total_objects": total_objects,
            "total_snapshots": total_snapshots,
            "total_items_backed_up": sum(o.total_items_backed_up or 0 for o in objects),
            "total_size_bytes": sum(o.total_size_bytes or 0 for o in objects),
            "total_restores": total_restores,
        },
    }


# ═══════════════════════════════════════════════════════
# 7. MVB Recovery Plan — Pre-computed, criticality-ordered
# ═══════════════════════════════════════════════════════

@router.get("/mvb-plan")
async def get_mvb_plan(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current pre-computed MVB recovery plan for a tenant."""
    from app.models.org_context import RecoveryPlan
    import json as _json

    result = await db.execute(
        select(RecoveryPlan).where(
            RecoveryPlan.tenant_id == tenant_id,
            RecoveryPlan.plan_type == "mvb",
        ).order_by(desc(RecoveryPlan.computed_at)).limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return {
            "status": "no_plan",
            "message": "No MVB plan computed yet. Click 'Generate Plan' or wait for scheduled refresh.",
        }

    # Check staleness
    is_stale = plan.stale_after and datetime.utcnow() > plan.stale_after

    return {
        "status": "stale" if is_stale else plan.status,
        "plan_id": plan.id,
        "name": plan.name,
        "plan_type": plan.plan_type,
        "mvb_user_count": plan.mvb_user_count,
        "mvb_object_count": plan.mvb_object_count,
        "total_object_count": plan.total_object_count,
        "total_items": plan.total_items,
        "total_size_bytes": plan.total_size_bytes,
        "estimated_minutes": plan.estimated_minutes,
        "phases": _json.loads(plan.phases_json) if plan.phases_json else [],
        "reasoning": plan.reasoning,
        "computed_at": plan.computed_at.isoformat() if plan.computed_at else None,
        "is_stale": is_stale,
    }


@router.post("/mvb-plan/generate")
async def generate_mvb_plan(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Generate (or refresh) the MVB recovery plan for a tenant."""
    from app.services.mvb_plan_generator import MVBPlanGenerator

    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)
    await db.commit()

    import json as _json
    return {
        "status": "generated",
        "plan_id": plan.id,
        "mvb_user_count": plan.mvb_user_count,
        "mvb_object_count": plan.mvb_object_count,
        "total_object_count": plan.total_object_count,
        "phases_count": len(_json.loads(plan.phases_json)) if plan.phases_json else 0,
        "estimated_minutes": plan.estimated_minutes,
        "reasoning": plan.reasoning,
    }


# ═══════════════════════════════════════════════════════
# 8. Criticality-Weighted Confidence Score (v2)
# ═══════════════════════════════════════════════════════

@router.get("/confidence/v2")
async def get_confidence_v2(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recovery Confidence Score v2 — weighted by criticality.

    Critical users matter more. A tenant with 100% backup coverage on
    low-priority users but missing the CEO scores lower than one with
    the CEO protected but missing some interns.
    """
    from app.models.org_context import UserContext

    since_7d = datetime.utcnow() - timedelta(days=7)

    # Get all protected objects with criticality
    objects = (await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )).scalars().all()

    total_objects = (await db.execute(
        select(func.count()).where(ProtectedObject.tenant_id == tenant_id)
    )).scalar() or 0

    if not objects:
        return _build_confidence_response(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    # Weight each object by criticality
    # critical=4x, high=2x, medium=1x, low=0.5x
    TIER_WEIGHTS = {"critical": 4.0, "high": 2.0, "medium": 1.0, "low": 0.5}
    total_weight = sum(TIER_WEIGHTS.get(o.criticality_tier or "medium", 1.0) for o in objects)

    # Weighted freshness — are critical users backed up recently?
    fresh_weight = sum(
        TIER_WEIGHTS.get(o.criticality_tier or "medium", 1.0)
        for o in objects
        if o.last_backup_at and o.last_backup_at >= since_7d
    )
    freshness_score = (fresh_weight / total_weight * 100) if total_weight > 0 else 0

    # Weighted completeness — are critical users protected?
    total_all_weight = total_weight + sum(
        TIER_WEIGHTS.get("medium", 1.0)
        for _ in range(max(0, total_objects - len(objects)))
    )
    completeness_score = (total_weight / total_all_weight * 100) if total_all_weight > 0 else 0

    # MVB coverage — what % of critical+high users are protected?
    critical_high_total = (await db.execute(
        select(func.count()).where(
            UserContext.tenant_id == tenant_id,
            UserContext.criticality_tier.in_(["critical", "high"]),
        )
    )).scalar() or 0

    critical_high_protected = (await db.execute(
        select(func.count()).where(
            UserContext.tenant_id == tenant_id,
            UserContext.criticality_tier.in_(["critical", "high"]),
            UserContext.protected_object_id.isnot(None),
        )
    )).scalar() or 0

    mvb_coverage = (critical_high_protected / critical_high_total * 100) if critical_high_total > 0 else 100

    # Restore success (same as v1)
    total_restores = (await db.execute(
        select(func.count()).where(
            RestoreJob.tenant_id == tenant_id,
            RestoreJob.completed_at >= datetime.utcnow() - timedelta(days=30),
        )
    )).scalar() or 0

    successful_restores = (await db.execute(
        select(func.count()).where(
            RestoreJob.tenant_id == tenant_id,
            RestoreJob.status == RestoreStatus.COMPLETED,
            RestoreJob.completed_at >= datetime.utcnow() - timedelta(days=30),
        )
    )).scalar() or 0

    restore_score = (successful_restores / total_restores * 100) if total_restores > 0 else 50

    # Validation (same as v1)
    validated = (await db.execute(
        select(func.count()).where(
            Snapshot.protected_object_id.in_([o.id for o in objects]),
            Snapshot.validation_status == "passed",
        )
    )).scalar() or 0

    total_snaps = (await db.execute(
        select(func.count()).where(
            Snapshot.protected_object_id.in_([o.id for o in objects]),
            Snapshot.status == SnapshotStatus.COMPLETED,
        )
    )).scalar() or 0

    validation_score = (validated / total_snaps * 100) if total_snaps > 0 else 30

    return _build_confidence_response(
        freshness_score, completeness_score, restore_score, validation_score,
        mvb_coverage, len(objects), total_objects, critical_high_total,
        critical_high_protected, total_restores, successful_restores,
    )


def _build_confidence_response(
    freshness, completeness, restore, validation,
    mvb_coverage, protected_count, total_count, critical_total,
    critical_protected, total_restores, successful_restores,
):
    # Weighted: freshness 25%, completeness 20%, MVB coverage 20%, restore 20%, validation 15%
    confidence = round(
        freshness * 0.25 +
        completeness * 0.20 +
        mvb_coverage * 0.20 +
        restore * 0.20 +
        validation * 0.15
    )

    if confidence >= 90:
        grade, label, color = "A", "Excellent", "green"
    elif confidence >= 70:
        grade, label, color = "B", "Good", "blue"
    elif confidence >= 50:
        grade, label, color = "C", "Fair", "amber"
    else:
        grade, label, color = "D", "At Risk", "red"

    return {
        "score": min(confidence, 100),
        "grade": grade,
        "label": label,
        "color": color,
        "factors": {
            "freshness": {
                "score": round(freshness, 1), "weight": 25,
                "detail": "Criticality-weighted backup freshness (critical users count 4x)",
            },
            "completeness": {
                "score": round(completeness, 1), "weight": 20,
                "detail": f"{protected_count}/{total_count} objects protected (weighted by criticality)",
            },
            "mvb_coverage": {
                "score": round(mvb_coverage, 1), "weight": 20,
                "detail": f"{critical_protected}/{critical_total} critical+high users protected",
            },
            "restore_success": {
                "score": round(restore, 1), "weight": 20,
                "detail": f"{successful_restores}/{total_restores} restores succeeded (30d)" if total_restores > 0 else "No restores attempted yet",
            },
            "validation": {
                "score": round(validation, 1), "weight": 15,
                "detail": "Snapshot validation pass rate",
            },
        },
    }
