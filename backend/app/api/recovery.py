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

    # RTO: calculate from actual restore job durations
    for wl in workload_data:
        restore_result = await db.execute(
            select(
                func.avg(
                    func.julianday(RestoreJob.completed_at) - func.julianday(RestoreJob.started_at)
                ).label("avg_days")
            ).where(
                RestoreJob.tenant_id == tenant_id,
                RestoreJob.status == RestoreStatus.COMPLETED,
            )
        )
        row = restore_result.one()
        avg_days = row.avg_days or 0
        workload_data[wl]["avg_rto_seconds"] = round(avg_days * 86400, 1)

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
            })

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
