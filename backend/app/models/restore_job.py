"""Restore Job model — tracks restore operations."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, ForeignKey, Index
from app.database import Base


class RestoreType(str, enum.Enum):
    FULL_INPLACE = "full_inplace"
    ITEM_LEVEL = "item_level"
    CROSS_USER = "cross_user"
    EXPORT = "export"
    MASS_RECOVERY = "mass_recovery"
    CROSS_TENANT = "cross_tenant"


class RestoreStatus(str, enum.Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    DEAD_LETTER = "dead_letter"  # Exceeded max_retries; no further attempts


class RestoreJob(Base):
    __tablename__ = "restore_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    source_snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    source_object_id = Column(Integer, ForeignKey("protected_objects.id"), nullable=False)
    restore_type = Column(Enum(RestoreType), nullable=False)
    target_object_id = Column(Integer, nullable=True)  # For cross-user restore
    target_tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)  # For cross-tenant restore
    target_path = Column(String(1000), nullable=True)  # For export
    scan_status = Column(String(50), nullable=True)  # Malware scan: clean/blocked/skipped
    scan_details = Column(Text, nullable=True)  # JSON with scan results
    status = Column(Enum(RestoreStatus), default=RestoreStatus.QUEUED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    items_total = Column(Integer, default=0)
    items_restored = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    item_ids_json = Column(Text, nullable=True)  # JSON array of specific item IDs for item-level
    retry_count = Column(Integer, default=0)     # Number of times this job has been retried
    max_retries = Column(Integer, default=3)     # Maximum auto-retries before dead-lettering
    # Audit + approval
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_required = Column(Integer, default=0)    # 0=no, 1=yes
    approval_status = Column(String(20), nullable=True)  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
