"""Exchange API routes — browse, search, and restore mailbox data."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import ShieldioError, BACKUP_NO_OBJECTS, BACKUP_ALREADY_RUNNING
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.user import User
from app.services.auth import get_current_user, require_backup_permission, require_restore_permission
from app.services.catalog import CatalogService
from app.services.resilience import idempotency_store
from app.api.dependencies import run_backup_preflight, get_idempotency_key
from app.interfaces.dispatcher_factory import get_dispatcher
from app.interfaces.job_message import BackupObjectMessage, RestoreJobMessage
from app.utils.query import ListParams, apply_sorting, apply_pagination

router = APIRouter(prefix="/api/exchange", tags=["Exchange"])


@router.get("/mailboxes")
async def list_mailboxes(
    tenant_id: int = Query(...),
    params: ListParams = Depends(),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Exchange mailboxes for a tenant with sorting and pagination."""
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == tenant_id,
        ProtectedObject.workload_type == WorkloadType.EXCHANGE,
    )
    if params.search:
        pattern = f"%{params.search}%"
        stmt = stmt.where(
            ProtectedObject.display_name.ilike(pattern)
            | ProtectedObject.email.ilike(pattern)
        )
    if status:
        stmt = stmt.where(ProtectedObject.status == status)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    # Sort + paginate
    stmt = apply_sorting(stmt, ProtectedObject, params.sort_by, params.sort_order)
    if not params.sort_by:
        stmt = stmt.order_by(ProtectedObject.display_name)
    stmt = apply_pagination(stmt, params.page, params.page_size)
    result = await db.execute(stmt)
    mailboxes = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "items": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "email": m.email,
                "status": m.status.value,
                "sla_policy_id": m.sla_policy_id,
                "last_backup_at": m.last_backup_at.isoformat() if m.last_backup_at else None,
                "last_backup_status": m.last_backup_status,
                "total_items": m.total_items_backed_up,
                "total_size_bytes": m.total_size_bytes,
                "criticality_score": m.criticality_score,
                "criticality_tier": m.criticality_tier,
                "object_subtype": m.object_subtype,
            }
            for m in mailboxes
        ],
    }


@router.get("/mailboxes/{mailbox_id}/snapshots")
async def list_snapshots(
    mailbox_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all snapshots for a mailbox."""
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.protected_object_id == mailbox_id)
        .order_by(desc(Snapshot.created_at))
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


@router.get("/mailboxes/{mailbox_id}/snapshots/{snapshot_id}/browse")
async def browse_snapshot(
    mailbox_id: int,
    snapshot_id: int,
    path: str = Query(None),
    item_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse items within a snapshot."""
    catalog = CatalogService(db)
    it = ItemType(item_type) if item_type else None
    items = await catalog.browse_snapshot(
        snapshot_id=snapshot_id,
        path=path,
        item_type=it,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {"items": items}


@router.get("/search")
async def search_emails(
    tenant_id: int = Query(...),
    query: str = Query(..., min_length=1),
    mailbox_id: int = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search emails across all snapshots."""
    catalog = CatalogService(db)
    results = await catalog.search_emails(
        tenant_id=tenant_id,
        query=query,
        object_id=mailbox_id,
        limit=limit,
    )
    return {"results": results, "total": len(results)}


class RestoreRequest(BaseModel):
    snapshot_id: int
    restore_type: str = "full_inplace"  # full_inplace, item_level, cross_user, export
    item_ids: list[int] = None
    target_object_id: int = None


@router.post("/mailboxes/{mailbox_id}/restore")
async def restore_mailbox(
    mailbox_id: int,
    req: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_restore_permission),
):
    """Restore Exchange mailbox data. Requires ADMIN role (write access)."""
    obj = await db.get(ProtectedObject, mailbox_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    snapshot = await db.get(Snapshot, req.snapshot_id)
    if not snapshot or snapshot.status != SnapshotStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Valid snapshot not found")

    restore_job = RestoreJob(
        tenant_id=obj.tenant_id,
        source_snapshot_id=req.snapshot_id,
        source_object_id=mailbox_id,
        restore_type=RestoreType(req.restore_type),
        target_object_id=req.target_object_id,
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


@router.post("/mailboxes/{mailbox_id}/export-pst")
async def export_pst(
    mailbox_id: int,
    snapshot_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export mailbox snapshot as downloadable EML bundle (PST-compatible).

    Requires Business+ tier (pst_export feature flag).
    Returns a ZIP file containing all emails as .eml files organized by folder.
    """
    from app.services.feature_flags import feature_flags
    if not feature_flags.is_enabled("pst_export"):
        raise HTTPException(403, detail="PST export requires Business plan or higher. Upgrade at /billing.")

    from app.models.snapshot import Snapshot, SnapshotItem
    from sqlalchemy import select

    # Get snapshot items
    result = await db.execute(
        select(SnapshotItem)
        .where(SnapshotItem.snapshot_id == snapshot_id)
        .where(SnapshotItem.item_type.in_(["email", "calendar_event", "contact"]))
        .order_by(SnapshotItem.path, SnapshotItem.name)
    )
    items = result.scalars().all()

    if not items:
        raise HTTPException(404, detail="No items found in snapshot")

    import io
    import zipfile
    import json as _json

    # Create ZIP with EML files organized by folder
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            folder = item.path or "Inbox"
            safe_name = (item.name or "item")[:80].replace("/", "_").replace("\\", "_")
            ext = ".eml" if item.item_type in ("email",) else ".json"
            filename = f"{folder}/{safe_name}_{item.id}{ext}"

            if item.metadata_json:
                try:
                    data = _json.loads(item.metadata_json) if isinstance(item.metadata_json, str) else item.metadata_json
                    zf.writestr(filename, _json.dumps(data, indent=2, default=str))
                except Exception:
                    zf.writestr(filename, item.metadata_json or "")
            else:
                zf.writestr(filename, f"Item: {item.name}\nType: {item.item_type}\nPath: {item.path}")

    buffer.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=mailbox_{mailbox_id}_snapshot_{snapshot_id}.zip"},
    )


@router.post("/mailboxes/{mailbox_id}/backup")
async def trigger_backup(
    mailbox_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Manually trigger a backup for a mailbox. Requires ADMIN or OPERATOR role."""
    obj = await db.get(ProtectedObject, mailbox_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    result = await get_dispatcher().dispatch_backup_object(
        BackupObjectMessage(protected_object_id=obj.id), db=db
    )
    if not result.success and result.status != "queued":
        raise HTTPException(status_code=500, detail=result.error or "Backup failed")
    return {
        "snapshot_id": result.snapshot_id,
        "status": result.status,
        "item_count": result.item_count,
        "size_bytes": result.size_bytes,
    }


@router.post("/backup-all")
async def trigger_backup_all(
    tenant_id: int = Query(..., description="Tenant ID to backup"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
    idempotency_key: str | None = Depends(get_idempotency_key),
):
    """Trigger backup for ALL Exchange mailboxes in a tenant. Requires ADMIN or OPERATOR role.

    Supports X-Idempotency-Key header — retries with the same key return cached result.
    Runs pre-flight checks on Graph API, storage, and database before starting.
    """
    # Idempotency: return cached result on retry
    if idempotency_key:
        cached = idempotency_store.get(current_user.id, idempotency_key)
        if cached is not None:
            return cached

    from app.models.backup_job import BackupJob, JobStatus

    result = await db.execute(
        select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == WorkloadType.EXCHANGE,
            ProtectedObject.status != ProtectionStatus.ERROR,
        )
    )
    mailboxes = result.scalars().all()

    if not mailboxes:
        raise ShieldioError(BACKUP_NO_OBJECTS, detail="No Exchange mailboxes found for this tenant")

    # Create a BackupJob for tracking
    job = BackupJob(
        tenant_id=tenant_id,
        workload_type="exchange",
        status=JobStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        objects_total=len(mailboxes),
        objects_processed=0,
        objects_failed=0,
    )
    db.add(job)
    await db.flush()

    # Initialize progress with all objects as pending
    import json as _json
    progress = {"objects": {}, "summary": {"total": len(mailboxes), "completed": 0, "failed": 0, "in_progress": 0, "pending": len(mailboxes), "total_items": 0, "total_size_bytes": 0}}
    for obj in mailboxes:
        progress["objects"][str(obj.id)] = {
            "name": obj.display_name,
            "email": obj.email,
            "workload": "exchange",
            "status": "pending",
        }
    job.progress_details = _json.dumps(progress)
    await db.commit()

    dispatcher = get_dispatcher()
    results = []
    succeeded = 0
    failed = 0
    queued_count = 0

    for obj in mailboxes:
        r = await dispatcher.dispatch_backup_object(
            BackupObjectMessage(protected_object_id=obj.id, backup_job_id=job.id), db=db
        )
        if r.status == "queued":
            queued_count += 1
        elif r.success:
            results.append({
                "mailbox": obj.display_name,
                "email": obj.email,
                "status": "success",
                "snapshot_id": r.snapshot_id,
                "item_count": r.item_count,
                "size_bytes": r.size_bytes,
            })
            succeeded += 1
            job.objects_processed += 1
            await db.commit()
        else:
            results.append({
                "mailbox": obj.display_name,
                "email": obj.email,
                "status": "failed",
                "error": r.error,
            })
            failed += 1
            job.objects_failed += 1
            await db.commit()

    if queued_count:
        # Redis mode: workers handle execution and update job progress
        job.status = JobStatus.QUEUED
        await db.commit()
        response = {"job_id": job.id, "status": "queued", "total": len(mailboxes)}
        if idempotency_key:
            idempotency_store.set(current_user.id, idempotency_key, response)
        return response

    # In-process mode: finalize job now
    if failed == 0:
        job.status = JobStatus.COMPLETED
    elif succeeded > 0:
        job.status = JobStatus.PARTIAL
    else:
        job.status = JobStatus.FAILED
    job.completed_at = datetime.utcnow()
    await db.commit()

    response = {
        "total": len(mailboxes),
        "succeeded": succeeded,
        "failed": failed,
        "job_id": job.id,
        "results": results,
    }
    if idempotency_key:
        idempotency_store.set(current_user.id, idempotency_key, response)
    return response
