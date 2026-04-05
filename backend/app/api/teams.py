"""Teams API routes — browse backed-up Teams data."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import KavachIQError, BACKUP_NO_OBJECTS
from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.user import User
from app.services.auth import get_current_user
from app.services.resilience import idempotency_store
from app.api.dependencies import get_idempotency_key
from app.interfaces.dispatcher_factory import get_dispatcher
from app.interfaces.job_message import BackupObjectMessage, RestoreJobMessage
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.services.auth import require_restore_permission
from app.utils.query import ListParams, apply_sorting, apply_pagination
from pydantic import BaseModel

router = APIRouter(prefix="/api/teams", tags=["Teams"])

TEAMS_ITEM_TYPES = [
    ItemType.CHAT_MESSAGE, ItemType.CHANNEL_MESSAGE,
    ItemType.TEAM_CHANNEL, ItemType.MEETING, ItemType.FILE,
    ItemType.CHAT, ItemType.CHAT_ATTACHMENT,
]


@router.get("/teams")
async def list_teams(
    tenant_id: int = Query(...),
    params: ListParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all protected Teams for a tenant with sorting, search, and pagination."""
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == tenant_id,
        ProtectedObject.workload_type == WorkloadType.TEAMS,
    )

    if params.search:
        stmt = stmt.where(
            or_(
                ProtectedObject.display_name.ilike(f"%{params.search}%"),
                ProtectedObject.email.ilike(f"%{params.search}%"),
            )
        )

    # Count before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Sort — default to display_name asc
    stmt = apply_sorting(
        stmt, ProtectedObject,
        params.sort_by or "display_name",
        params.sort_order if params.sort_by else "asc",
    )
    stmt = apply_pagination(stmt, params.page, params.page_size)

    result = await db.execute(stmt)
    teams = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "items": [
            {
                "id": t.id,
                "display_name": t.display_name,
                "ms_object_id": t.ms_object_id,
                "status": t.status.value,
                "last_backup_at": t.last_backup_at.isoformat() if t.last_backup_at else None,
                "total_items_backed_up": t.total_items_backed_up,
                "total_size_bytes": t.total_size_bytes,
                "criticality_score": t.criticality_score,
                "criticality_tier": t.criticality_tier,
            }
            for t in teams
        ],
    }


@router.get("/snapshot/{snapshot_id}/items")
async def list_snapshot_items(
    snapshot_id: int,
    item_type: str = Query(None),
    search: str = Query(None),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse items in a Teams backup snapshot."""
    stmt = select(SnapshotItem).where(
        SnapshotItem.snapshot_id == snapshot_id,
        SnapshotItem.item_type.in_(TEAMS_ITEM_TYPES),
    )
    if item_type:
        try:
            stmt = stmt.where(SnapshotItem.item_type == ItemType(item_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid item_type: {item_type}")
    if search:
        stmt = stmt.where(SnapshotItem.name.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(stmt.order_by(SnapshotItem.item_type, SnapshotItem.name).limit(page_size))
    items = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": i.id, "item_type": i.item_type.value,
                "ms_item_id": i.ms_item_id, "name": i.name,
                "path": i.path, "size_bytes": i.size_bytes,
                "metadata": json.loads(i.metadata_json) if i.metadata_json else None,
            }
            for i in items
        ],
    }


@router.post("/backup-all")
async def backup_all_teams(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger on-demand backup of all Teams for a tenant."""
    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.TEAMS,
        )
    )
    teams = result.scalars().all()
    if not teams:
        raise HTTPException(status_code=404, detail="No Teams found for this tenant. Run discovery first.")

    dispatcher = get_dispatcher()
    results = []
    queued_count = 0

    for team in teams:
        r = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=team.id), db=db
        )
        if r.status == "queued":
            queued_count += 1
        else:
            results.append({
                "team": team.display_name,
                "snapshot_id": r.snapshot_id,
                "item_count": r.item_count,
                "status": r.status,
            })

    if queued_count:
        return {"backed_up": queued_count, "status": "queued"}

    await db.commit()
    return {"backed_up": len(results), "results": results}


@router.get("/teams/{team_id}/snapshots")
async def list_team_snapshots(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List snapshots for a specific Team/Chat object."""
    obj = await db.get(ProtectedObject, team_id)
    if not obj or obj.workload_type != WorkloadType.TEAMS:
        raise HTTPException(status_code=404, detail="Team not found")

    result = await db.execute(
        select(Snapshot).where(
            Snapshot.protected_object_id == team_id,
        ).order_by(desc(Snapshot.started_at))
    )
    snapshots = result.scalars().all()

    return [
        {
            "id": s.id,
            "snapshot_type": s.snapshot_type.value,
            "status": s.status.value,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "item_count": s.item_count,
            "size_bytes": s.size_bytes,
        }
        for s in snapshots
    ]


@router.post("/teams/{team_id}/backup")
async def backup_single_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger on-demand backup of a single Team."""
    obj = await db.get(ProtectedObject, team_id)
    if not obj or obj.workload_type != WorkloadType.TEAMS:
        raise HTTPException(status_code=404, detail="Team not found")

    result = await get_dispatcher().dispatch_backup_object(
        BackupObjectMessage(protected_object_id=obj.id), db=db
    )
    if not result.success and result.status != "queued":
        raise HTTPException(status_code=500, detail=result.error or "Backup failed")
    if result.status != "queued":
        await db.commit()

    return {
        "status": result.status,
        "snapshot_id": result.snapshot_id,
        "item_count": result.item_count,
        "size_bytes": result.size_bytes,
    }


@router.get("/chats")
async def list_chat_users(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users with Teams chat backup (user_chats type)."""
    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.TEAMS,
        ).order_by(ProtectedObject.display_name)
    )
    all_objects = result.scalars().all()

    # Separate teams vs chat users
    teams = []
    chat_users = []
    for obj in all_objects:
        metadata = {}
        if obj.metadata_json:
            try:
                metadata = json.loads(obj.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass
        entry = {
            "id": obj.id,
            "display_name": obj.display_name,
            "ms_object_id": obj.ms_object_id,
            "email": obj.email,
            "status": obj.status.value,
            "last_backup_at": obj.last_backup_at.isoformat() if obj.last_backup_at else None,
            "total_items_backed_up": obj.total_items_backed_up,
            "total_size_bytes": obj.total_size_bytes,
            "type": metadata.get("type", "team"),
        }
        if metadata.get("type") == "user_chats":
            chat_users.append(entry)
        else:
            teams.append(entry)

    return {
        "teams": {"total": len(teams), "items": teams},
        "chats": {"total": len(chat_users), "items": chat_users},
    }


@router.get("/chats/{user_object_id}/messages")
async def list_chat_messages(
    user_object_id: int,
    snapshot_id: int = Query(None),
    search: str = Query(None),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse backed-up chat messages for a user."""
    obj = await db.get(ProtectedObject, user_object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User chat object not found")

    # Get latest snapshot if not specified
    if not snapshot_id:
        snap_result = await db.execute(
            select(Snapshot).where(
                Snapshot.protected_object_id == obj.id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            ).order_by(desc(Snapshot.completed_at)).limit(1)
        )
        snap = snap_result.scalar_one_or_none()
        if not snap:
            return {"total": 0, "items": []}
        snapshot_id = snap.id

    stmt = select(SnapshotItem).where(
        SnapshotItem.snapshot_id == snapshot_id,
        SnapshotItem.item_type.in_([ItemType.CHAT_MESSAGE, ItemType.CHAT]),
    )
    if search:
        stmt = stmt.where(SnapshotItem.name.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(stmt.order_by(SnapshotItem.item_type, SnapshotItem.name).limit(page_size))
    items = result.scalars().all()

    return {
        "total": total,
        "snapshot_id": snapshot_id,
        "items": [
            {
                "id": i.id, "item_type": i.item_type.value,
                "ms_item_id": i.ms_item_id, "name": i.name,
                "path": i.path, "size_bytes": i.size_bytes,
                "metadata": json.loads(i.metadata_json) if i.metadata_json else None,
            }
            for i in items
        ],
    }


class TeamsRestoreRequest(BaseModel):
    snapshot_id: int
    restore_type: str = "full_inplace"
    item_ids: list[int] = None
    target_team_id: int = None


@router.post("/teams/{team_id}/restore")
async def restore_team(
    team_id: int,
    req: TeamsRestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Restore Teams data from a snapshot. Requires ADMIN role."""
    obj = await db.get(ProtectedObject, team_id)
    if not obj or obj.workload_type != WorkloadType.TEAMS:
        raise HTTPException(status_code=404, detail="Team not found")

    snapshot = await db.get(Snapshot, req.snapshot_id)
    if not snapshot or snapshot.status != SnapshotStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Valid snapshot not found")

    restore_job = RestoreJob(
        tenant_id=obj.tenant_id,
        source_snapshot_id=req.snapshot_id,
        source_object_id=team_id,
        restore_type=RestoreType(req.restore_type),
        target_object_id=req.target_team_id,
        item_ids_json=json.dumps(req.item_ids) if req.item_ids else None,
        status=RestoreStatus.QUEUED,
    )
    db.add(restore_job)
    await db.flush()

    result = await get_dispatcher().dispatch_restore(
        RestoreJobMessage(restore_job_id=restore_job.id), db=db
    )

    return {
        "restore_job_id": restore_job.id,
        "status": result.status or restore_job.status.value,
        "items_restored": restore_job.items_restored,
    }
