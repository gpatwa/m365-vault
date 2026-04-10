"""Workload API Base — factory that generates standard CRUD endpoints for any workload.

Eliminates 70% of duplicated code across exchange.py, onedrive.py, sharepoint.py,
teams.py, and entra_id.py. Each workload API calls create_workload_router() to get
a pre-built router with list, search, snapshot, browse, backup, and restore endpoints.

Workload-specific endpoints (PST export, snapshot diff, etc.) are added to the
returned router by each workload module.

Usage:
    # exchange.py
    router = create_workload_router(WorkloadType.EXCHANGE, "/api/exchange", "mailbox", "Exchange")

    @router.post("/mailboxes/{id}/export-pst")
    async def export_pst(...):  # Exchange-specific only
        ...
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import KavachIQError, BACKUP_NO_OBJECTS
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.user import User
from app.services.auth import get_current_user, require_backup_permission, require_restore_permission, require_tenant_access_dep, resolve_tenant_filter
from app.services.catalog import CatalogService
from app.services.resilience import idempotency_store
from app.api.dependencies import run_backup_preflight, get_idempotency_key
from app.interfaces.dispatcher_factory import get_dispatcher
from app.interfaces.job_message import BackupObjectMessage, RestoreJobMessage
from app.utils.query import ListParams, apply_sorting, apply_pagination

logger = logging.getLogger(__name__)


class RestoreRequest(BaseModel):
    """Standard restore request — shared across all workloads."""
    snapshot_id: int
    restore_type: str = "full_inplace"
    item_ids: list[int] = None
    target_object_id: int = None


def create_workload_router(
    workload_type: WorkloadType,
    prefix: str,
    object_name: str,
    tag: str,
    search_fields: list[str] = None,
) -> APIRouter:
    """Factory that creates a full set of standard endpoints for a workload.

    Args:
        workload_type: The WorkloadType enum value (EXCHANGE, ONEDRIVE, etc.)
        prefix: API path prefix ("/api/exchange")
        object_name: Singular object name ("mailbox", "account", "site", "team")
        tag: OpenAPI tag for grouping
        search_fields: Extra ProtectedObject fields to search (default: display_name + email)

    Returns:
        APIRouter with 7 standard endpoints. Add workload-specific endpoints to this router.
    """
    router = APIRouter(prefix=prefix, tags=[tag], dependencies=[Depends(require_tenant_access_dep())])
    # Smart pluralization
    if object_name.endswith("x") or object_name.endswith("s") or object_name.endswith("ch"):
        plural = f"{object_name}es"
    else:
        plural = f"{object_name}s"

    # ── List Objects ──────────────────────────────────────────
    @router.get(f"/{plural}")
    async def list_objects(
        tenant_id: int = Query(...),
        params: ListParams = Depends(),
        status: str = Query(None),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        f"""List all {tag} {plural} for a tenant with sorting and pagination."""
        allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)
        if tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail="Tenant not found")
        stmt = select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.workload_type == workload_type,
        )
        if params.search:
            pattern = f"%{params.search}%"
            conditions = [ProtectedObject.display_name.ilike(pattern)]
            if hasattr(ProtectedObject, 'email'):
                conditions.append(ProtectedObject.email.ilike(pattern))
            if hasattr(ProtectedObject, 'site_url') and workload_type == WorkloadType.SHAREPOINT:
                conditions.append(ProtectedObject.site_url.ilike(pattern))
            from sqlalchemy import or_
            stmt = stmt.where(or_(*conditions))
        if status:
            stmt = stmt.where(ProtectedObject.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar()

        stmt = apply_sorting(stmt, ProtectedObject, params.sort_by, params.sort_order)
        if not params.sort_by:
            stmt = stmt.order_by(ProtectedObject.display_name)
        stmt = apply_pagination(stmt, params.page, params.page_size)
        result = await db.execute(stmt)
        objects = result.scalars().all()

        return {
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
            "items": [
                {
                    "id": o.id,
                    "display_name": o.display_name,
                    "email": o.email,
                    "site_url": getattr(o, 'site_url', None),
                    "status": o.status.value,
                    "sla_policy_id": o.sla_policy_id,
                    "last_backup_at": o.last_backup_at.isoformat() if o.last_backup_at else None,
                    "last_backup_status": o.last_backup_status,
                    "total_items": o.total_items_backed_up,
                    "total_size_bytes": o.total_size_bytes,
                    "criticality_score": o.criticality_score,
                    "criticality_tier": o.criticality_tier,
                    "object_subtype": o.object_subtype,
                }
                for o in objects
            ],
        }

    # ── List Snapshots ────────────────────────────────────────
    @router.get(f"/{plural}/{{object_id}}/snapshots")
    async def list_snapshots(
        object_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        f"""List all snapshots for a {object_name}."""
        # Verify tenant access on the protected object
        allowed_ids = await resolve_tenant_filter(db, current_user)
        obj = await db.get(ProtectedObject, object_id)
        if not obj:
            return []
        if obj.tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail=f"{object_name.title()} not found")
        result = await db.execute(
            select(Snapshot)
            .where(Snapshot.protected_object_id == object_id)
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

    # ── Browse Snapshot Items ─────────────────────────────────
    @router.get(f"/{plural}/{{object_id}}/snapshots/{{snapshot_id}}/browse")
    async def browse_snapshot(
        object_id: int,
        snapshot_id: int,
        path: str = Query(None),
        item_type: str = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        f"""Browse items within a {object_name} snapshot."""
        # Verify tenant access on the protected object
        allowed_ids = await resolve_tenant_filter(db, current_user)
        obj = await db.get(ProtectedObject, object_id)
        if not obj or obj.tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail=f"{object_name.title()} not found")
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

    # ── Search ────────────────────────────────────────────────
    @router.get("/search")
    async def search_items(
        tenant_id: int = Query(...),
        query: str = Query(..., min_length=1),
        object_id: int = Query(None),
        limit: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        f"""Search {tag} items across all snapshots."""
        allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)
        if tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail="Tenant not found")
        catalog = CatalogService(db)
        # Use workload-specific search for Exchange (emails), files for OD/SP, generic for others
        if workload_type == WorkloadType.EXCHANGE:
            results = await catalog.search_emails(
                tenant_id=tenant_id, query=query, object_id=object_id, limit=limit,
            )
        elif workload_type in (WorkloadType.ONEDRIVE, WorkloadType.SHAREPOINT):
            results = await catalog.search_files(
                tenant_id=tenant_id, query=query, workload_type=workload_type,
                object_id=object_id, limit=limit,
            )
        else:
            result = await catalog.search_all(
                tenant_id=tenant_id, query=query,
                workload_filter=workload_type.value, limit=limit,
            )
            return result  # search_all returns its own format
        return {"results": results, "total": len(results)}

    # ── Restore ───────────────────────────────────────────────
    @router.post(f"/{plural}/{{object_id}}/restore")
    async def restore_object(
        object_id: int,
        req: RestoreRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_restore_permission),
    ):
        f"""Restore {object_name} data from a snapshot."""
        allowed_ids = await resolve_tenant_filter(db, current_user)
        obj = await db.get(ProtectedObject, object_id)
        if not obj or obj.tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail=f"{object_name.title()} not found")

        snapshot = await db.get(Snapshot, req.snapshot_id)
        if not snapshot or snapshot.status != SnapshotStatus.COMPLETED:
            raise HTTPException(status_code=404, detail="Valid snapshot not found")

        restore_job = RestoreJob(
            tenant_id=obj.tenant_id,
            source_snapshot_id=req.snapshot_id,
            source_object_id=object_id,
            restore_type=RestoreType(req.restore_type),
            target_object_id=req.target_object_id,
            item_ids_json=json.dumps(req.item_ids) if req.item_ids else None,
            status=RestoreStatus.QUEUED,
            initiated_by_user_id=current_user.id,
        )
        db.add(restore_job)
        await db.flush()

        from app.services.audit import audit_log
        await audit_log(
            db, action=f"restore.{workload_type.value}", resource_type="protected_object",
            resource_id=object_id, user_id=current_user.id,
            details=f"{tag} restore: {req.restore_type} on {obj.display_name}",
            severity="warning",
        )

        result = await get_dispatcher().dispatch_restore(
            RestoreJobMessage(restore_job_id=restore_job.id), db=db
        )

        return {
            "restore_job_id": restore_job.id,
            "status": result.status or restore_job.status.value,
            "items_restored": restore_job.items_restored,
        }

    # ── Trigger Single Backup ─────────────────────────────────
    @router.post(f"/{plural}/{{object_id}}/backup")
    async def trigger_backup(
        object_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_backup_permission),
    ):
        f"""Manually trigger a backup for a {object_name}."""
        allowed_ids = await resolve_tenant_filter(db, current_user)
        obj = await db.get(ProtectedObject, object_id)
        if not obj or obj.tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail=f"{object_name.title()} not found")

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

    # ── Trigger Backup All ────────────────────────────────────
    @router.post("/backup-all")
    async def trigger_backup_all(
        tenant_id: int = Query(..., description="Tenant ID to backup"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(require_backup_permission),
        idempotency_key: str | None = Depends(get_idempotency_key),
    ):
        f"""Trigger backup for ALL {tag} {plural} in a tenant."""
        allowed_ids = await resolve_tenant_filter(db, current_user, tenant_id)
        if tenant_id not in allowed_ids:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if idempotency_key:
            cached = idempotency_store.get(current_user.id, idempotency_key)
            if cached is not None:
                return cached

        from app.models.backup_job import BackupJob, JobStatus

        result = await db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == workload_type,
                ProtectedObject.status != ProtectionStatus.ERROR,
            )
        )
        objects = result.scalars().all()

        if not objects:
            raise KavachIQError(BACKUP_NO_OBJECTS, detail=f"No {tag} {plural} found for this tenant")

        job = BackupJob(
            tenant_id=tenant_id,
            workload_type=workload_type.value,
            status=JobStatus.IN_PROGRESS,
            objects_total=len(objects),
        )
        db.add(job)
        await db.flush()

        results = []
        for obj in objects:
            try:
                r = await get_dispatcher().dispatch_backup_object(
                    BackupObjectMessage(protected_object_id=obj.id), db=db
                )
                results.append({
                    "object_id": obj.id,
                    "display_name": obj.display_name,
                    "status": r.status,
                    "snapshot_id": r.snapshot_id,
                })
            except Exception as e:
                results.append({
                    "object_id": obj.id,
                    "display_name": obj.display_name,
                    "status": "failed",
                    "error": str(e)[:200],
                })

        successful = sum(1 for r in results if r["status"] not in ("failed", "error"))
        job.objects_processed = successful
        job.objects_failed = len(results) - successful
        job.status = JobStatus.COMPLETED if successful == len(results) else (
            JobStatus.FAILED if successful == 0 else JobStatus.COMPLETED
        )
        await db.commit()

        response = {
            "job_id": job.id,
            "total_objects": len(objects),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results,
        }

        if idempotency_key:
            idempotency_store.set(current_user.id, idempotency_key, response)

        return response

    return router
