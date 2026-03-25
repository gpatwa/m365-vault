"""Job message schemas for dispatching between Control and Data Plane.

These Pydantic models define the contract between the scheduler/API
(control plane) and the backup/restore workers (data plane).
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class JobType(str, Enum):
    BACKUP_OBJECT = "backup_object"   # Single object backup (on-demand)
    BACKUP_JOB = "backup_job"         # Full scheduled job (multiple objects)
    RESTORE = "restore"               # Restore operation


class BackupObjectMessage(BaseModel):
    """Dispatch a single-object backup (on-demand from API)."""
    job_type: str = JobType.BACKUP_OBJECT
    protected_object_id: int
    backup_job_id: Optional[int] = None
    queue_entry_id: Optional[int] = None  # Set by RedisDispatcher for durability tracking


class BackupJobMessage(BaseModel):
    """Dispatch a full backup job (from scheduler)."""
    job_type: str = JobType.BACKUP_JOB
    backup_job_id: int
    queue_entry_id: Optional[int] = None  # Set by RedisDispatcher for durability tracking


class RestoreJobMessage(BaseModel):
    """Dispatch a restore job."""
    job_type: str = JobType.RESTORE
    restore_job_id: int
    queue_entry_id: Optional[int] = None  # Set by RedisDispatcher for durability tracking


class JobResult(BaseModel):
    """Result returned after job execution."""
    success: bool
    job_id: Optional[int] = None
    snapshot_id: Optional[int] = None
    item_count: Optional[int] = None
    size_bytes: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None
