"""Restore Approval API — approval workflow for critical restores.

Critical restore types (mass recovery, cross-user, cross-tenant, Entra ID config)
require a second admin/restore_operator to approve before execution.
Enforces: requester != approver (separation of duties).
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.restore_approval import RestoreApproval
from app.services.auth import get_current_user, require_role
from app.services.audit import audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/restore-approvals", tags=["Restore Approvals"])

# Restore types that require approval
APPROVAL_REQUIRED_TYPES = {
    RestoreType.MASS_RECOVERY,
    RestoreType.CROSS_USER,
    RestoreType.CROSS_TENANT,
}

APPROVAL_EXPIRY_HOURS = 24

require_approve_permission = require_role(UserRole.ADMIN, UserRole.RESTORE_OPERATOR)


def needs_approval(restore_type: RestoreType, is_entra_id: bool = False) -> bool:
    """Determine if a restore operation needs approval."""
    if restore_type in APPROVAL_REQUIRED_TYPES:
        return True
    if is_entra_id:  # All Entra ID config restores need approval
        return True
    return False


async def create_approval_request(
    db: AsyncSession,
    restore_job: RestoreJob,
    requested_by_user_id: int,
) -> RestoreApproval:
    """Create an approval request for a restore job.

    Sets the restore job to PENDING_APPROVAL status.
    """
    restore_job.approval_required = 1
    restore_job.approval_status = "pending"

    approval = RestoreApproval(
        restore_job_id=restore_job.id,
        requested_by_user_id=requested_by_user_id,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(hours=APPROVAL_EXPIRY_HOURS),
    )
    db.add(approval)
    await db.flush()

    await audit_log(
        db, action="restore.approval_requested", resource_type="restore_job",
        resource_id=restore_job.id, user_id=requested_by_user_id,
        details=f"Approval requested for {restore_job.restore_type.value} restore",
        severity="warning",
    )

    return approval


@router.get("/pending")
async def list_pending_approvals(
    tenant_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_approve_permission),
):
    """List pending restore approval requests.

    Only shows requests that the current user did NOT create (separation of duties).
    Expired approvals are auto-marked as expired.
    """
    now = datetime.utcnow()

    # Auto-expire old approvals
    expired_stmt = select(RestoreApproval).where(
        RestoreApproval.status == "pending",
        RestoreApproval.expires_at < now,
    )
    expired_result = await db.execute(expired_stmt)
    for approval in expired_result.scalars().all():
        approval.status = "expired"
        approval.resolved_at = now
        # Also update the restore job
        job = await db.get(RestoreJob, approval.restore_job_id)
        if job:
            job.approval_status = "expired"

    # Get pending approvals (exclude own requests)
    stmt = (
        select(RestoreApproval, RestoreJob)
        .join(RestoreJob, RestoreApproval.restore_job_id == RestoreJob.id)
        .where(
            RestoreApproval.status == "pending",
            RestoreApproval.requested_by_user_id != current_user.id,
        )
    )
    if tenant_id:
        stmt = stmt.where(RestoreJob.tenant_id == tenant_id)

    stmt = stmt.order_by(RestoreApproval.requested_at.desc())
    result = await db.execute(stmt)
    rows = result.all()

    await db.commit()

    approvals = []
    for approval, job in rows:
        approvals.append({
            "id": approval.id,
            "restore_job_id": job.id,
            "restore_type": job.restore_type.value,
            "tenant_id": job.tenant_id,
            "requested_by_user_id": approval.requested_by_user_id,
            "status": approval.status,
            "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
            "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        })

    return {"total": len(approvals), "approvals": approvals}


class ApprovalAction(BaseModel):
    reason: str = None


@router.post("/{job_id}/approve")
async def approve_restore(
    job_id: int,
    req: ApprovalAction = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_approve_permission),
):
    """Approve a pending restore job. Requester cannot approve their own request."""
    approval_result = await db.execute(
        select(RestoreApproval).where(
            RestoreApproval.restore_job_id == job_id,
            RestoreApproval.status == "pending",
        )
    )
    approval = approval_result.scalar_one_or_none()
    if not approval:
        raise HTTPException(404, detail="No pending approval found for this restore job")

    # Separation of duties: requester != approver
    if approval.requested_by_user_id == current_user.id:
        raise HTTPException(403, detail="Cannot approve your own restore request. Another admin must approve.")

    # Check not expired
    if approval.expires_at < datetime.utcnow():
        approval.status = "expired"
        approval.resolved_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(410, detail="Approval request has expired")

    # Approve
    now = datetime.utcnow()
    approval.status = "approved"
    approval.approved_by_user_id = current_user.id
    approval.reason = req.reason if req else None
    approval.resolved_at = now

    # Update restore job → queue for execution
    job = await db.get(RestoreJob, job_id)
    if not job:
        raise HTTPException(404, detail="Restore job not found")

    job.approval_status = "approved"
    job.status = RestoreStatus.QUEUED

    # Dispatch the restore
    from app.services.job_dispatcher import get_dispatcher, RestoreJobMessage
    await get_dispatcher().dispatch_restore(
        RestoreJobMessage(restore_job_id=job.id), db=db
    )

    await audit_log(
        db, action="restore.approved", resource_type="restore_job",
        resource_id=job_id, user_id=current_user.id,
        details=f"Approved {job.restore_type.value} restore (requested by user {approval.requested_by_user_id})",
        severity="warning",
    )

    await db.commit()

    return {
        "status": "approved",
        "restore_job_id": job_id,
        "approved_by": current_user.id,
        "restore_status": job.status.value,
    }


@router.post("/{job_id}/reject")
async def reject_restore(
    job_id: int,
    req: ApprovalAction = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_approve_permission),
):
    """Reject a pending restore job."""
    approval_result = await db.execute(
        select(RestoreApproval).where(
            RestoreApproval.restore_job_id == job_id,
            RestoreApproval.status == "pending",
        )
    )
    approval = approval_result.scalar_one_or_none()
    if not approval:
        raise HTTPException(404, detail="No pending approval found for this restore job")

    # Separation of duties
    if approval.requested_by_user_id == current_user.id:
        raise HTTPException(403, detail="Cannot reject your own restore request.")

    now = datetime.utcnow()
    approval.status = "rejected"
    approval.approved_by_user_id = current_user.id
    approval.reason = req.reason if req else None
    approval.resolved_at = now

    # Update restore job
    job = await db.get(RestoreJob, job_id)
    if job:
        job.approval_status = "rejected"
        job.status = RestoreStatus.FAILED
        job.error_message = f"Rejected by user {current_user.id}: {req.reason if req else 'No reason given'}"

    await audit_log(
        db, action="restore.rejected", resource_type="restore_job",
        resource_id=job_id, user_id=current_user.id,
        details=f"Rejected {job.restore_type.value if job else 'unknown'} restore: {req.reason if req else 'No reason'}",
        severity="warning",
    )

    await db.commit()

    return {
        "status": "rejected",
        "restore_job_id": job_id,
        "rejected_by": current_user.id,
        "reason": req.reason if req else None,
    }


@router.get("/count")
async def pending_approval_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of pending approvals (for bell icon badge).

    Only counts requests the current user can act on (not their own).
    """
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(RestoreApproval.id)).where(
            RestoreApproval.status == "pending",
            RestoreApproval.requested_by_user_id != current_user.id,
            RestoreApproval.expires_at > datetime.utcnow(),
        )
    )
    count = result.scalar() or 0
    return {"pending_count": count}
