"""Backup Job model — tracks backup operations."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, ForeignKey
from app.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Some objects succeeded, some failed


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    workload_type = Column(String(50), nullable=False)
    sla_policy_id = Column(Integer, ForeignKey("sla_policies.id"), nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    objects_total = Column(Integer, default=0)
    objects_processed = Column(Integer, default=0)
    objects_failed = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    progress_details = Column(Text, nullable=True)  # JSON: per-object status
    retry_count = Column(Integer, default=0)           # How many times this job has been retried
    max_retries = Column(Integer, default=3)            # Max auto-retries allowed
    retry_of_job_id = Column(Integer, ForeignKey("backup_jobs.id"), nullable=True)  # Links to original failed job
    failed_object_ids = Column(Text, nullable=True)     # JSON: list of object IDs that failed (for targeted retry)
    created_at = Column(DateTime, default=datetime.utcnow)
