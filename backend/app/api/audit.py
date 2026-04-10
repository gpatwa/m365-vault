"""Audit log API routes — list, filter, and export audit trail."""
import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.services.auth import get_current_user
from app.utils.query import ListParams, apply_sorting, apply_pagination

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/logs")
async def list_audit_logs(
    params: ListParams = Depends(),
    action: str = Query(None),
    resource_type: str = Query(None),
    severity: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List audit log entries with filtering, sorting, and pagination."""
    stmt = select(AuditLog)

    # Non-admin users can only see their own audit logs
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(AuditLog.user_id == current_user.id)

    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if severity:
        stmt = stmt.where(AuditLog.severity == severity)
    if params.search:
        pattern = f"%{params.search}%"
        stmt = stmt.where(
            AuditLog.action.ilike(pattern)
            | AuditLog.details.ilike(pattern)
            | AuditLog.resource_type.ilike(pattern)
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    stmt = apply_sorting(stmt, AuditLog, params.sort_by, params.sort_order)
    if not params.sort_by:
        stmt = stmt.order_by(desc(AuditLog.timestamp))
    stmt = apply_pagination(stmt, params.page, params.page_size)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "severity": log.severity,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", description="Export format: csv or json"),
    action: str = Query(None),
    resource_type: str = Query(None),
    severity: str = Query(None),
    days: int = Query(30, description="Export last N days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export audit logs as CSV or JSON download. Required for SOC 2 compliance."""
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(AuditLog).where(AuditLog.timestamp >= since)

    # Non-admin users can only export their own audit logs
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(AuditLog.user_id == current_user.id)

    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if severity:
        stmt = stmt.where(AuditLog.severity == severity)

    stmt = stmt.order_by(desc(AuditLog.timestamp))
    result = await db.execute(stmt)
    logs = result.scalars().all()

    rows = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "severity": log.severity,
            "ip_address": log.ip_address,
        }
        for log in logs
    ]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(rows, indent=2, default=str).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit-log-{days}d.json"},
        )

    # CSV export
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit-log-{days}d.csv"},
    )
