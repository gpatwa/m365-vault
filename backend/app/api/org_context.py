"""Organizational Context API — criticality scoring, VIP groups, context sync."""
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.protected_object import ProtectedObject
from app.models.org_context import UserContext, SiteContext, VIPGroup, VIPGroupMember
from app.services.auth import get_current_user, require_backup_permission
from app.services.context_collector import ContextCollectorService
from app.services.criticality_scorer import CriticalityScorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/org-context", tags=["Org Context"])


# ── Pydantic schemas ──

class VIPGroupCreate(BaseModel):
    tenant_id: int
    name: str
    description: str = None
    criticality_boost: int = 20
    member_object_ids: list[int] = []


class VIPGroupUpdate(BaseModel):
    name: str = None
    description: str = None
    criticality_boost: int = None


class VIPMemberAdd(BaseModel):
    protected_object_ids: list[int]


# ── Summary ──

@router.get("/summary")
async def get_summary(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Org context dashboard summary: tier counts, top critical users, last sync."""
    # Count users by tier
    tier_result = await db.execute(
        select(UserContext.criticality_tier, func.count())
        .where(UserContext.tenant_id == tenant_id)
        .group_by(UserContext.criticality_tier)
    )
    tiers = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_users = 0
    for tier, count in tier_result.all():
        tiers[tier] = count
        total_users += count

    # Count sites
    total_sites = (await db.execute(
        select(func.count()).where(SiteContext.tenant_id == tenant_id)
    )).scalar() or 0

    # Top 5 critical users
    top_result = await db.execute(
        select(UserContext)
        .where(UserContext.tenant_id == tenant_id)
        .order_by(desc(UserContext.criticality_score))
        .limit(5)
    )
    top_users = []
    for ctx in top_result.scalars().all():
        import json
        signals = json.loads(ctx.signals) if ctx.signals else {}
        # Determine top signal
        top_signal_parts = []
        if ctx.is_global_admin:
            top_signal_parts.append("Global Admin")
        elif ctx.has_privileged_role:
            top_signal_parts.append("Privileged Role")
        if ctx.has_legal_hold:
            top_signal_parts.append("Legal Hold")
        if ctx.is_vip:
            top_signal_parts.append("VIP")
        if ctx.department:
            top_signal_parts.append(ctx.department)
        top_signal = " + ".join(top_signal_parts[:2]) if top_signal_parts else ctx.job_title or "Active user"

        top_users.append({
            "display_name": ctx.display_name,
            "email": ctx.email,
            "criticality_score": ctx.criticality_score,
            "criticality_tier": ctx.criticality_tier,
            "top_signal": top_signal,
        })

    # Last sync
    last_sync = (await db.execute(
        select(func.max(UserContext.synced_at)).where(UserContext.tenant_id == tenant_id)
    )).scalar()

    # VIP groups count
    vip_count = (await db.execute(
        select(func.count()).where(VIPGroup.tenant_id == tenant_id)
    )).scalar() or 0

    return {
        "total_users": total_users,
        "total_sites": total_sites,
        "by_tier": tiers,
        "top_critical_users": top_users,
        "last_sync_at": last_sync.isoformat() if last_sync else None,
        "vip_groups_count": vip_count,
    }


# ── Users list ──

@router.get("/users")
async def list_users(
    tenant_id: int = Query(...),
    tier: str = Query(None, description="Filter by tier: critical, high, medium, low"),
    search: str = Query(None),
    sort_by: str = Query("criticality_score", description="Sort field"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users with criticality scores, paginated and filterable."""
    stmt = select(UserContext).where(UserContext.tenant_id == tenant_id)

    if tier:
        stmt = stmt.where(UserContext.criticality_tier == tier)
    if search:
        stmt = stmt.where(or_(
            UserContext.display_name.ilike(f"%{search}%"),
            UserContext.email.ilike(f"%{search}%"),
            UserContext.department.ilike(f"%{search}%"),
        ))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Sort
    sort_col = getattr(UserContext, sort_by, UserContext.criticality_score)
    stmt = stmt.order_by(desc(sort_col) if sort_order == "desc" else sort_col)

    # Paginate
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)

    import json
    items = []
    for ctx in result.scalars().all():
        items.append({
            "id": ctx.id,
            "ms_user_id": ctx.ms_user_id,
            "display_name": ctx.display_name,
            "email": ctx.email,
            "job_title": ctx.job_title,
            "department": ctx.department,
            "criticality_score": ctx.criticality_score,
            "criticality_tier": ctx.criticality_tier,
            "is_vip": bool(ctx.is_vip),
            "has_privileged_role": bool(ctx.has_privileged_role),
            "is_global_admin": bool(ctx.is_global_admin),
            "direct_reports_count": ctx.direct_reports_count,
            "last_sign_in_at": ctx.last_sign_in_at.isoformat() if ctx.last_sign_in_at else None,
            "signals": json.loads(ctx.signals) if ctx.signals else {},
            "synced_at": ctx.synced_at.isoformat() if ctx.synced_at else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── Sites list ──

@router.get("/sites")
async def list_sites(
    tenant_id: int = Query(...),
    tier: str = Query(None),
    search: str = Query(None),
    sort_by: str = Query("criticality_score"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sites with criticality scores."""
    stmt = select(SiteContext).where(SiteContext.tenant_id == tenant_id)
    if tier:
        stmt = stmt.where(SiteContext.criticality_tier == tier)
    if search:
        stmt = stmt.where(or_(
            SiteContext.site_name.ilike(f"%{search}%"),
            SiteContext.site_url.ilike(f"%{search}%"),
        ))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    sort_col = getattr(SiteContext, sort_by, SiteContext.criticality_score)
    stmt = stmt.order_by(desc(sort_col) if sort_order == "desc" else sort_col)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)

    import json
    items = []
    for ctx in result.scalars().all():
        items.append({
            "id": ctx.id,
            "ms_site_id": ctx.ms_site_id,
            "site_name": ctx.site_name,
            "site_url": ctx.site_url,
            "site_type": ctx.site_type,
            "criticality_score": ctx.criticality_score,
            "criticality_tier": ctx.criticality_tier,
            "file_count": ctx.file_count,
            "unique_visitors": ctx.unique_visitors,
            "external_sharing_enabled": bool(ctx.external_sharing_enabled),
            "sensitivity_label": ctx.sensitivity_label,
            "signals": json.loads(ctx.signals) if ctx.signals else {},
            "synced_at": ctx.synced_at.isoformat() if ctx.synced_at else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ── Sync ──

@router.post("/sync")
async def trigger_sync(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Trigger manual org context sync + scoring for a tenant."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    start = time.time()

    collector = ContextCollectorService(db)
    collect_results = await collector.collect_all(tenant)

    scorer = CriticalityScorer(db)
    score_results = await scorer.score_all(tenant_id)

    duration = round(time.time() - start, 1)

    return {
        "status": "completed",
        "users_synced": collect_results["users_synced"],
        "sites_synced": collect_results["sites_synced"],
        "users_scored": score_results["users_scored"],
        "sites_scored": score_results["sites_scored"],
        "tiers": score_results["tiers"],
        "duration_seconds": duration,
        "errors": collect_results.get("errors", []),
    }


# ── VIP Groups CRUD ──

@router.get("/vip-groups")
async def list_vip_groups(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List VIP groups for a tenant."""
    result = await db.execute(
        select(VIPGroup).where(VIPGroup.tenant_id == tenant_id).order_by(VIPGroup.name)
    )
    groups = []
    for g in result.scalars().all():
        member_count = (await db.execute(
            select(func.count()).where(VIPGroupMember.vip_group_id == g.id)
        )).scalar() or 0
        groups.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "criticality_boost": g.criticality_boost,
            "member_count": member_count,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    return {"groups": groups}


@router.post("/vip-groups", status_code=201)
async def create_vip_group(
    body: VIPGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Create a VIP group."""
    group = VIPGroup(
        tenant_id=body.tenant_id,
        name=body.name,
        description=body.description,
        criticality_boost=body.criticality_boost,
    )
    db.add(group)
    await db.flush()

    # Add members
    for po_id in body.member_object_ids:
        po = await db.get(ProtectedObject, po_id)
        if po and po.tenant_id == body.tenant_id:
            member = VIPGroupMember(
                vip_group_id=group.id,
                protected_object_id=po_id,
                ms_user_id=po.ms_object_id,
            )
            db.add(member)

    await db.commit()
    return {"id": group.id, "name": group.name, "status": "created"}


@router.put("/vip-groups/{group_id}")
async def update_vip_group(
    group_id: int,
    body: VIPGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Update a VIP group."""
    group = await db.get(VIPGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="VIP group not found")

    if body.name is not None:
        group.name = body.name
    if body.description is not None:
        group.description = body.description
    if body.criticality_boost is not None:
        group.criticality_boost = body.criticality_boost

    await db.commit()
    return {"id": group.id, "name": group.name, "status": "updated"}


@router.delete("/vip-groups/{group_id}", status_code=204)
async def delete_vip_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Delete a VIP group and its memberships."""
    group = await db.get(VIPGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="VIP group not found")
    await db.delete(group)
    await db.commit()


@router.post("/vip-groups/{group_id}/members")
async def add_vip_members(
    group_id: int,
    body: VIPMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Add members to a VIP group."""
    group = await db.get(VIPGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="VIP group not found")

    added = 0
    for po_id in body.protected_object_ids:
        po = await db.get(ProtectedObject, po_id)
        if not po or po.tenant_id != group.tenant_id:
            continue
        # Check if already a member
        existing = await db.execute(
            select(VIPGroupMember).where(
                VIPGroupMember.vip_group_id == group_id,
                VIPGroupMember.protected_object_id == po_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        member = VIPGroupMember(
            vip_group_id=group_id,
            protected_object_id=po_id,
            ms_user_id=po.ms_object_id,
        )
        db.add(member)
        added += 1

    await db.commit()
    return {"added": added}


@router.delete("/vip-groups/{group_id}/members/{member_id}", status_code=204)
async def remove_vip_member(
    group_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Remove a member from a VIP group."""
    result = await db.execute(
        select(VIPGroupMember).where(
            VIPGroupMember.id == member_id,
            VIPGroupMember.vip_group_id == group_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()
