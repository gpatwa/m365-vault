"""Job dispatcher interface and in-process implementation.

The dispatcher decouples the control plane (scheduler, API) from the
data plane (backup engine, workers). Two implementations:

- InProcessDispatcher: Execute jobs in the same process (current behavior)
- RedisDispatcher: Enqueue jobs for separate worker processes (Phase 2)
"""
import logging
from abc import ABC, abstractmethod

from app.interfaces.job_message import (
    BackupObjectMessage, BackupJobMessage, RestoreJobMessage, JobResult
)

logger = logging.getLogger(__name__)


class JobDispatcher(ABC):
    """Abstract interface for dispatching backup/restore jobs."""

    @abstractmethod
    async def dispatch_backup_object(self, msg: BackupObjectMessage, **kwargs) -> JobResult:
        """Dispatch a single-object backup."""
        ...

    @abstractmethod
    async def dispatch_backup_job(self, msg: BackupJobMessage, **kwargs) -> JobResult:
        """Dispatch a full backup job (multiple objects)."""
        ...

    @abstractmethod
    async def dispatch_restore(self, msg: RestoreJobMessage, **kwargs) -> JobResult:
        """Dispatch a restore job."""
        ...


class InProcessDispatcher(JobDispatcher):
    """Execute jobs synchronously in the same process.

    This is the default dispatcher — identical to current behavior.
    When DISPATCH_MODE=in_process, all callers use this.

    Accepts optional `db` kwarg to share the caller's DB session
    (needed for API routes that return results synchronously).
    """

    async def dispatch_backup_object(self, msg: BackupObjectMessage, **kwargs) -> JobResult:
        """Execute a single-object backup inline."""
        db = kwargs.get("db")

        try:
            if db:
                # Use caller's session (API route context)
                return await self._execute_backup_object(msg, db)
            else:
                # Create own session (scheduler/worker context)
                from app.database import async_session
                async with async_session() as session:
                    result = await self._execute_backup_object(msg, session)
                    await session.commit()
                    return result
        except Exception as e:
            logger.error(f"InProcess backup object failed: {e}")
            return JobResult(success=False, error=str(e))

    async def dispatch_backup_job(self, msg: BackupJobMessage, **kwargs) -> JobResult:
        """Execute a full backup job inline."""
        db = kwargs.get("db")

        try:
            if db:
                return await self._execute_backup_job(msg, db)
            else:
                from app.database import async_session
                async with async_session() as session:
                    result = await self._execute_backup_job(msg, session)
                    await session.commit()
                    return result
        except Exception as e:
            logger.error(f"InProcess backup job failed: {e}")
            return JobResult(success=False, error=str(e))

    async def dispatch_restore(self, msg: RestoreJobMessage, **kwargs) -> JobResult:
        """Execute a restore job inline."""
        db = kwargs.get("db")

        try:
            if db:
                return await self._execute_restore(msg, db)
            else:
                from app.database import async_session
                async with async_session() as session:
                    result = await self._execute_restore(msg, session)
                    await session.commit()
                    return result
        except Exception as e:
            logger.error(f"InProcess restore failed: {e}")
            return JobResult(success=False, error=str(e))

    # ── Internal execution methods ──

    async def _execute_backup_object(self, msg: BackupObjectMessage, db) -> JobResult:
        from app.services.backup_engine import BackupEngine
        from app.models.protected_object import ProtectedObject
        from app.models.backup_job import BackupJob

        obj = await db.get(ProtectedObject, msg.protected_object_id)
        if not obj:
            return JobResult(success=False, error=f"Protected object {msg.protected_object_id} not found")

        job = await db.get(BackupJob, msg.backup_job_id) if msg.backup_job_id else None

        engine = BackupEngine(db)
        snapshot = await engine.run_backup_for_object(obj, job=job)

        return JobResult(
            success=True,
            snapshot_id=snapshot.id,
            item_count=snapshot.item_count,
            size_bytes=snapshot.size_bytes,
            status=snapshot.status.value,
        )

    async def _execute_backup_job(self, msg: BackupJobMessage, db) -> JobResult:
        from app.services.backup_engine import BackupEngine
        from app.models.backup_job import BackupJob

        job = await db.get(BackupJob, msg.backup_job_id)
        if not job:
            return JobResult(success=False, error=f"Backup job {msg.backup_job_id} not found")

        engine = BackupEngine(db)
        await engine._execute_backup_job(job)

        return JobResult(
            success=True,
            job_id=job.id,
            status=job.status.value,
        )

    async def _execute_restore(self, msg: RestoreJobMessage, db) -> JobResult:
        from app.services.restore_engine import RestoreEngine
        from app.models.restore_job import RestoreJob

        restore_job = await db.get(RestoreJob, msg.restore_job_id)
        if not restore_job:
            return JobResult(success=False, error=f"Restore job {msg.restore_job_id} not found")

        engine = RestoreEngine(db)
        await engine.execute_restore(restore_job)

        return JobResult(
            success=True,
            job_id=restore_job.id,
            status=restore_job.status.value if hasattr(restore_job.status, 'value') else str(restore_job.status),
        )
