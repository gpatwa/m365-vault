"""SLA Policy management API routes."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sla_policy import SLAPolicy
from app.models.protected_object import ProtectedObject, ProtectionStatus, WorkloadType
from app.models.user import User, UserRole
from app.services.auth import get_current_user, require_role
from app.services.audit import audit_log

router = APIRouter(prefix="/api/sla-policies", tags=["SLA Policies"])


class SLAPolicyCreate(BaseModel):
    name: str
    description: str = None
    backup_frequency_hours: int = 24
    retention_days: int = 30
    priority: int = 5
    is_locked: bool = False
    worm_enabled: bool = False
    legal_hold: bool = False


class SLAPolicyResponse(BaseModel):
    id: int
    name: str
    description: str | None
    backup_frequency_hours: int
    retention_days: int
    priority: int
    is_locked: int
    worm_enabled: int
    legal_hold: int
    is_active: int
    created_at: str
    protected_objects_count: int = 0

    class Config:
        from_attributes = True


class SLAAssignRequest(BaseModel):
    sla_policy_id: int
    object_ids: list[int] = None  # Specific object IDs
    workload_type: str = None  # Apply to all objects of this workload
    tenant_id: int = None
    assignment_type: str = "individual"  # application, group, individual


@router.get("/", response_model=list[SLAPolicyResponse])
async def list_sla_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all SLA policies."""
    result = await db.execute(select(SLAPolicy).order_by(SLAPolicy.priority))
    policies = result.scalars().all()

    responses = []
    for p in policies:
        # Count assigned objects
        count_result = await db.execute(
            select(ProtectedObject).where(ProtectedObject.sla_policy_id == p.id)
        )
        count = len(count_result.scalars().all())

        responses.append(SLAPolicyResponse(
            id=p.id, name=p.name, description=p.description,
            backup_frequency_hours=p.backup_frequency_hours,
            retention_days=p.retention_days, priority=p.priority,
            is_locked=p.is_locked, is_active=p.is_active,
            created_at=p.created_at.isoformat(),
            protected_objects_count=count,
        ))
    return responses


@router.post("/", response_model=SLAPolicyResponse)
async def create_sla_policy(
    req: SLAPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new SLA policy."""
    existing = await db.execute(select(SLAPolicy).where(SLAPolicy.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="SLA policy name already exists")

    policy = SLAPolicy(
        name=req.name,
        description=req.description,
        backup_frequency_hours=req.backup_frequency_hours,
        retention_days=req.retention_days,
        priority=req.priority,
        worm_enabled=int(req.worm_enabled),
        legal_hold=int(req.legal_hold),
        is_locked=1 if req.is_locked else 0,
    )
    db.add(policy)
    await db.flush()

    return SLAPolicyResponse(
        id=policy.id, name=policy.name, description=policy.description,
        backup_frequency_hours=policy.backup_frequency_hours,
        retention_days=policy.retention_days, priority=policy.priority,
        is_locked=policy.is_locked, is_active=policy.is_active,
        created_at=policy.created_at.isoformat(),
    )


@router.put("/{policy_id}", response_model=SLAPolicyResponse)
async def update_sla_policy(
    policy_id: int,
    req: SLAPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update an SLA policy."""
    policy = await db.get(SLAPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")

    if policy.is_locked:
        raise HTTPException(status_code=403, detail="Cannot modify a retention-locked SLA policy")

    policy.name = req.name
    policy.description = req.description
    policy.backup_frequency_hours = req.backup_frequency_hours
    policy.retention_days = req.retention_days
    policy.priority = req.priority
    policy.updated_at = datetime.utcnow()
    await db.flush()

    return SLAPolicyResponse(
        id=policy.id, name=policy.name, description=policy.description,
        backup_frequency_hours=policy.backup_frequency_hours,
        retention_days=policy.retention_days, priority=policy.priority,
        is_locked=policy.is_locked, is_active=policy.is_active,
        created_at=policy.created_at.isoformat(),
    )


@router.delete("/{policy_id}")
async def delete_sla_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete an SLA policy."""
    policy = await db.get(SLAPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    if policy.is_locked:
        raise HTTPException(status_code=403, detail="Cannot delete a retention-locked SLA policy")

    # Unassign all objects
    await db.execute(
        update(ProtectedObject)
        .where(ProtectedObject.sla_policy_id == policy_id)
        .values(sla_policy_id=None, status=ProtectionStatus.UNPROTECTED)
    )
    await db.delete(policy)
    return {"status": "deleted"}


@router.post("/assign")
async def assign_sla(
    req: SLAAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Assign SLA policy to objects (supports hierarchical assignment)."""
    policy = await db.get(SLAPolicy, req.sla_policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")

    updated_count = 0

    if req.workload_type and req.tenant_id:
        # Application-level assignment — assign to all objects of this workload type
        result = await db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == req.tenant_id,
                ProtectedObject.workload_type == req.workload_type,
            )
        )
        objects = result.scalars().all()
        for obj in objects:
            # Only override if current assignment is application-level or unprotected
            if obj.sla_assignment_type in ("application", None) or obj.status == ProtectionStatus.UNPROTECTED:
                obj.sla_policy_id = req.sla_policy_id
                obj.sla_assignment_type = "application"
                obj.status = ProtectionStatus.PROTECTED
                updated_count += 1

    elif req.object_ids:
        # Individual assignment — overrides any inherited SLA
        for obj_id in req.object_ids:
            obj = await db.get(ProtectedObject, obj_id)
            if obj:
                obj.sla_policy_id = req.sla_policy_id
                obj.sla_assignment_type = req.assignment_type
                obj.status = ProtectionStatus.PROTECTED
                updated_count += 1

    await audit_log(db, action="sla.assigned", resource_type="sla_policy",
                    resource_id=req.sla_policy_id,
                    details=f"Assigned to {updated_count} objects (workload={req.workload_type or 'individual'})",
                    user_id=current_user.id)
    await db.flush()
    return {"status": "assigned", "objects_updated": updated_count}


@router.post("/unassign")
async def unassign_sla(
    object_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Remove SLA assignment from specific objects."""
    updated = 0
    for obj_id in object_ids:
        obj = await db.get(ProtectedObject, obj_id)
        if obj:
            if obj.sla_policy_id:
                # Check if SLA is locked
                policy = await db.get(SLAPolicy, obj.sla_policy_id)
                if policy and policy.is_locked:
                    continue  # Can't unassign from locked SLA
            obj.sla_policy_id = None
            obj.sla_assignment_type = None
            obj.status = ProtectionStatus.UNPROTECTED
            updated += 1

    return {"status": "unassigned", "objects_updated": updated}


class QuickProtectRequest(BaseModel):
    tenant_id: int
    workload_types: list[str]  # ["exchange", "onedrive", "sharepoint", "entra_id"]
    frequency_hours: int = 24
    retention_days: int = 30


@router.post("/quick-protect")
async def quick_protect(
    req: QuickProtectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """One-call protection setup for onboarding wizard.

    Creates or reuses an SLA policy and assigns it to all objects
    of the specified workload types for the given tenant.
    """
    # Find or create policy
    policy_name = f"Auto-{req.frequency_hours}h-{req.retention_days}d"
    result = await db.execute(
        select(SLAPolicy).where(
            SLAPolicy.name == policy_name,
            SLAPolicy.backup_frequency_hours == req.frequency_hours,
            SLAPolicy.retention_days == req.retention_days,
        )
    )
    policy = result.scalar_one_or_none()

    if not policy:
        policy = SLAPolicy(
            name=policy_name,
            description=f"Auto-created: backup every {req.frequency_hours}h, retain {req.retention_days} days",
            backup_frequency_hours=req.frequency_hours,
            retention_days=req.retention_days,
            priority=5,
        )
        db.add(policy)
        await db.flush()

    # Assign to all selected workloads
    total_protected = 0
    workload_details = {}

    for wt_str in req.workload_types:
        try:
            wt = WorkloadType(wt_str)
        except ValueError:
            continue

        objects_result = await db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == req.tenant_id,
                ProtectedObject.workload_type == wt,
            )
        )
        objects = objects_result.scalars().all()
        count = 0
        for obj in objects:
            obj.sla_policy_id = policy.id
            obj.sla_assignment_type = "application"
            obj.status = ProtectionStatus.PROTECTED
            count += 1

        total_protected += count
        workload_details[wt_str] = count

    await db.flush()

    return {
        "status": "protected",
        "policy_id": policy.id,
        "policy_name": policy.name,
        "total_protected": total_protected,
        "workloads": workload_details,
    }
