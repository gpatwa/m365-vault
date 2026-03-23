"""Sensitive Data Discovery API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.snapshot import Snapshot
from app.models.user import User
from app.services.auth import get_current_user
from app.services.sensitive_data_scanner import sensitive_data_scanner
from app.services.storage import storage_service

router = APIRouter(prefix="/api/sensitive-data", tags=["Sensitive Data"])


@router.post("/scan/{snapshot_id}")
async def scan_snapshot(
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger sensitive data scan on a snapshot."""
    snapshot = await db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # Get wrapped DEK from storage
    from app.models.protected_object import ProtectedObject
    obj = await db.get(ProtectedObject, snapshot.protected_object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protected object not found")

    wrapped_dek = await storage_service.get_wrapped_dek(
        tenant_id=obj.tenant_id,
        workload=obj.workload_type.value,
        object_id=obj.ms_object_id,
        snapshot_id=snapshot.id,
    )

    result = await sensitive_data_scanner.scan_snapshot(snapshot, db, storage_service, wrapped_dek)
    await db.commit()

    return {
        "snapshot_id": snapshot_id,
        "items_scanned": result.total_items_scanned,
        "items_flagged": result.items_with_findings,
        "total_findings": result.total_findings,
        "by_category": result.findings_by_category,
        "by_pattern": result.findings_by_pattern,
    }


@router.get("/results")
async def get_scan_results(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated sensitive data scan results for a tenant."""
    return await sensitive_data_scanner.get_scan_results(tenant_id, db)
