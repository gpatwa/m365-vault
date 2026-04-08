"""Generic CSV export endpoint for any list data source."""
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.snapshot import FailedItem, ErrorCategory, ERROR_RESOLUTION_GUIDE
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.auth import get_current_user, require_tenant_access_dep, resolve_tenant_filter

router = APIRouter(prefix="/api/export", tags=["Export"], dependencies=[Depends(require_tenant_access_dep())])


# Source definitions: maps source name -> (query builder, columns, filename)
# Each query builder receives (db, params) and returns rows as list of dicts.

async def _export_exchange_mailboxes(db: AsyncSession, params: dict) -> tuple[list[dict], list[str], str]:
    tenant_id = params.get("tenant_id")
    if not tenant_id:
        raise HTTPException(400, "tenant_id required")
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == int(tenant_id),
        ProtectedObject.workload_type == WorkloadType.EXCHANGE,
    )
    search = params.get("search")
    if search:
        stmt = stmt.where(ProtectedObject.display_name.ilike(f"%{search}%"))
    status = params.get("status")
    if status:
        stmt = stmt.where(ProtectedObject.status == status)
    stmt = stmt.order_by(ProtectedObject.display_name)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    columns = ["id", "display_name", "email", "status", "last_backup_at", "total_items", "total_size_bytes"]
    data = [
        {
            "id": m.id,
            "display_name": m.display_name,
            "email": m.email,
            "status": m.status.value,
            "last_backup_at": m.last_backup_at.isoformat() if m.last_backup_at else "",
            "total_items": m.total_items_backed_up,
            "total_size_bytes": m.total_size_bytes,
        }
        for m in rows
    ]
    return data, columns, "exchange_mailboxes"


async def _export_onedrive_accounts(db: AsyncSession, params: dict) -> tuple[list[dict], list[str], str]:
    tenant_id = params.get("tenant_id")
    if not tenant_id:
        raise HTTPException(400, "tenant_id required")
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == int(tenant_id),
        ProtectedObject.workload_type == WorkloadType.ONEDRIVE,
    )
    search = params.get("search")
    if search:
        stmt = stmt.where(ProtectedObject.display_name.ilike(f"%{search}%"))
    status = params.get("status")
    if status:
        stmt = stmt.where(ProtectedObject.status == status)
    stmt = stmt.order_by(ProtectedObject.display_name)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    columns = ["id", "display_name", "email", "status", "last_backup_at", "total_items", "total_size_bytes"]
    data = [
        {
            "id": a.id,
            "display_name": a.display_name,
            "email": a.email,
            "status": a.status.value,
            "last_backup_at": a.last_backup_at.isoformat() if a.last_backup_at else "",
            "total_items": a.total_items_backed_up,
            "total_size_bytes": a.total_size_bytes,
        }
        for a in rows
    ]
    return data, columns, "onedrive_accounts"


async def _export_sharepoint_sites(db: AsyncSession, params: dict) -> tuple[list[dict], list[str], str]:
    tenant_id = params.get("tenant_id")
    if not tenant_id:
        raise HTTPException(400, "tenant_id required")
    stmt = select(ProtectedObject).where(
        ProtectedObject.tenant_id == int(tenant_id),
        ProtectedObject.workload_type == WorkloadType.SHAREPOINT,
    )
    search = params.get("search")
    if search:
        stmt = stmt.where(ProtectedObject.display_name.ilike(f"%{search}%"))
    status = params.get("status")
    if status:
        stmt = stmt.where(ProtectedObject.status == status)
    stmt = stmt.order_by(ProtectedObject.display_name)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    columns = ["id", "display_name", "site_url", "status", "last_backup_at", "total_items", "total_size_bytes"]
    data = [
        {
            "id": s.id,
            "display_name": s.display_name,
            "site_url": s.site_url,
            "status": s.status.value,
            "last_backup_at": s.last_backup_at.isoformat() if s.last_backup_at else "",
            "total_items": s.total_items_backed_up,
            "total_size_bytes": s.total_size_bytes,
        }
        for s in rows
    ]
    return data, columns, "sharepoint_sites"


async def _export_failed_items(db: AsyncSession, params: dict) -> tuple[list[dict], list[str], str]:
    stmt = select(FailedItem)
    error_category = params.get("error_category")
    if error_category:
        stmt = stmt.where(FailedItem.error_category == error_category)
    is_resolved = params.get("is_resolved")
    if is_resolved is not None and is_resolved != "":
        stmt = stmt.where(FailedItem.is_resolved == (is_resolved == "true"))
    search = params.get("search")
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(FailedItem.item_name.ilike(pattern) | FailedItem.error_message.ilike(pattern))
    stmt = stmt.order_by(desc(FailedItem.created_at))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    columns = [
        "id", "item_name", "item_type", "item_path", "error_category",
        "error_message", "error_code", "retries_attempted", "is_resolved",
        "can_retry", "created_at",
    ]
    data = [
        {
            "id": fi.id,
            "item_name": fi.item_name or "",
            "item_type": fi.item_type.value if fi.item_type else "",
            "item_path": fi.item_path or "",
            "error_category": fi.error_category.value if hasattr(fi.error_category, "value") else str(fi.error_category),
            "error_message": fi.error_message or "",
            "error_code": fi.error_code or "",
            "retries_attempted": fi.retries_attempted,
            "is_resolved": fi.is_resolved,
            "can_retry": fi.can_retry,
            "created_at": fi.created_at.isoformat() if fi.created_at else "",
        }
        for fi in rows
    ]
    return data, columns, "failed_items"


async def _export_audit_logs(db: AsyncSession, params: dict) -> tuple[list[dict], list[str], str]:
    stmt = select(AuditLog)
    severity = params.get("severity")
    if severity:
        stmt = stmt.where(AuditLog.severity == severity)
    search = params.get("search")
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(AuditLog.action.ilike(pattern) | AuditLog.details.ilike(pattern))
    stmt = stmt.order_by(desc(AuditLog.timestamp))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    columns = ["id", "timestamp", "severity", "action", "resource_type", "resource_id", "details", "user_id", "ip_address"]
    data = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            "severity": log.severity,
            "action": log.action,
            "resource_type": log.resource_type or "",
            "resource_id": log.resource_id or "",
            "details": log.details or "",
            "user_id": log.user_id or "",
            "ip_address": log.ip_address or "",
        }
        for log in rows
    ]
    return data, columns, "audit_logs"


_SOURCE_MAP = {
    "exchange_mailboxes": _export_exchange_mailboxes,
    "onedrive_accounts": _export_onedrive_accounts,
    "sharepoint_sites": _export_sharepoint_sites,
    "failed_items": _export_failed_items,
    "audit_logs": _export_audit_logs,
}


@router.get("/csv")
async def export_csv(
    source: str = Query(..., description="Data source: exchange_mailboxes, onedrive_accounts, sharepoint_sites, failed_items, audit_logs"),
    tenant_id: int = Query(None),
    search: str = Query(None),
    status: str = Query(None),
    severity: str = Query(None),
    error_category: str = Query(None),
    is_resolved: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export any list data source as a streaming CSV download."""
    if source not in _SOURCE_MAP:
        raise HTTPException(400, f"Unknown source: {source}. Available: {', '.join(_SOURCE_MAP.keys())}")

    # Validate tenant access (prevent cross-tenant data export)
    if tenant_id:
        from app.services.auth import require_tenant_access
        await require_tenant_access(db, tenant_id, current_user)

    export_fn = _SOURCE_MAP[source]
    params = {
        "tenant_id": tenant_id,
        "search": search,
        "status": status,
        "severity": severity,
        "error_category": error_category,
        "is_resolved": is_resolved,
    }

    data, columns, filename_base = await export_fn(db, params)

    # Stream CSV response
    def generate():
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in data:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_base}_{timestamp}.csv"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
