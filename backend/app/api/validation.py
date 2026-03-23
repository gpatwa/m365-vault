"""Backup Validation API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.snapshot import Snapshot
from app.models.user import User
from app.services.auth import get_current_user
from app.services.backup_validator import backup_validator
from app.services.storage import storage_service

router = APIRouter(prefix="/api/validation", tags=["Validation"])


@router.post("/snapshot/{snapshot_id}")
async def validate_snapshot(
    snapshot_id: int,
    sample_percent: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger backup validation on a snapshot."""
    snapshot = await db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

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

    result = await backup_validator.validate_snapshot(
        snapshot, db, storage_service, wrapped_dek, sample_percent
    )

    # Update snapshot validation fields
    snapshot.validation_status = result.status
    snapshot.validated_at = __import__('datetime').datetime.utcnow()
    await db.commit()

    return {
        "snapshot_id": snapshot_id,
        "status": result.status,
        "items_total": result.items_total,
        "items_sampled": result.items_sampled,
        "items_passed": result.items_passed,
        "items_failed": result.items_failed,
        "duration_ms": result.duration_ms,
        "errors": result.errors[:10],  # Limit errors in response
    }


@router.get("/snapshot/{snapshot_id}")
async def get_validation_result(
    snapshot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get validation result for a snapshot."""
    snapshot = await db.get(Snapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return {
        "snapshot_id": snapshot_id,
        "validation_status": snapshot.validation_status or "not_validated",
        "validated_at": snapshot.validated_at.isoformat() if snapshot.validated_at else None,
        "item_count": snapshot.item_count,
        "size_bytes": snapshot.size_bytes,
    }
