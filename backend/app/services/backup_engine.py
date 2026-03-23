"""Backup orchestration engine.

Coordinates backup jobs across all workload workers (Exchange, OneDrive, SharePoint).
Handles job lifecycle, progress tracking, and error handling.
"""
import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.backup_job import BackupJob, JobStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotType, SnapshotStatus
from app.models.tenant import Tenant
from app.services.graph_client import GraphClient
from app.services.encryption import encryption_service
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class BackupEngine:
    """Orchestrates backup operations across all workloads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_graph_client(self, tenant: Tenant) -> GraphClient:
        """Create a read-only Graph client for backup operations.

        Backup operations only need read access to M365 data (GET requests).
        Write operations (POST/PUT/DELETE) are blocked at the client level.
        """
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret,
            access_mode="backup",
        )

    async def process_queued_jobs(self):
        """Process all queued backup jobs."""
        result = await self.db.execute(
            select(BackupJob)
            .where(BackupJob.status == JobStatus.QUEUED)
            .order_by(BackupJob.created_at)
        )
        jobs = result.scalars().all()

        for job in jobs:
            try:
                await self._execute_backup_job(job)
            except Exception as e:
                logger.error(f"Backup job {job.id} failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                await self.db.commit()

    async def run_backup_for_object(
        self,
        protected_object: ProtectedObject,
        job: BackupJob = None,
    ) -> Snapshot:
        """Run a backup for a single protected object. Returns the created snapshot.
        If a BackupJob is provided, updates its progress_details in real-time.
        """
        tenant = await self.db.get(Tenant, protected_object.tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {protected_object.tenant_id} not found")

        graph = self._get_graph_client(tenant)

        # Determine snapshot type (full if first backup, incremental otherwise)
        last_snapshot = await self._get_last_snapshot(protected_object.id)
        snapshot_type = SnapshotType.INCREMENTAL if last_snapshot else SnapshotType.FULL
        delta_token = last_snapshot.delta_token if last_snapshot else None

        # Update job progress: starting this object
        if job:
            self._update_job_progress(job, protected_object, "in_progress",
                                      detail=f"Starting {snapshot_type.value} backup")
            await self.db.commit()

        # Create snapshot record
        snapshot = Snapshot(
            protected_object_id=protected_object.id,
            snapshot_type=snapshot_type,
            status=SnapshotStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        self.db.add(snapshot)
        await self.db.flush()

        # Initialize storage
        wrapped_dek, blob_path = await storage_service.init_snapshot_storage(
            tenant_id=tenant.id,
            workload=protected_object.workload_type.value,
            object_id=protected_object.ms_object_id,
            snapshot_id=snapshot.id,
        )
        snapshot.blob_path = blob_path
        snapshot.encryption_key_id = wrapped_dek[:50]  # Store reference

        try:
            # Dispatch to appropriate worker
            from app.workers.exchange_worker import ExchangeWorker
            from app.workers.onedrive_worker import OneDriveWorker
            from app.workers.sharepoint_worker import SharePointWorker
            from app.workers.entra_id_worker import EntraIDWorker
            from app.workers.teams_worker import TeamsWorker

            worker_map = {
                WorkloadType.EXCHANGE: ExchangeWorker,
                WorkloadType.ONEDRIVE: OneDriveWorker,
                WorkloadType.SHAREPOINT: SharePointWorker,
                WorkloadType.ENTRA_ID: EntraIDWorker,
                WorkloadType.TEAMS: TeamsWorker,
            }

            worker_class = worker_map.get(protected_object.workload_type)
            if not worker_class:
                raise ValueError(f"Unknown workload type: {protected_object.workload_type}")

            worker = worker_class(
                db=self.db,
                graph=graph,
                storage=storage_service,
                encryption=encryption_service,
            )

            if job:
                self._update_job_progress(job, protected_object, "in_progress",
                                          detail="Fetching data from Microsoft Graph API")
                await self.db.commit()

            item_count, total_size, new_delta_token = await worker.backup(
                protected_object=protected_object,
                snapshot=snapshot,
                wrapped_dek=wrapped_dek,
                delta_token=delta_token,
            )

            # Update snapshot
            snapshot.status = SnapshotStatus.COMPLETED
            snapshot.completed_at = datetime.utcnow()
            snapshot.item_count = item_count
            snapshot.size_bytes = total_size
            snapshot.delta_token = new_delta_token

            # Apply WORM lock if SLA policy has worm_enabled
            if protected_object.sla_policy_id:
                from app.models.sla_policy import SLAPolicy
                sla = await self.db.get(SLAPolicy, protected_object.sla_policy_id)
                if sla and getattr(sla, 'worm_enabled', 0):
                    storage_service.apply_worm_lock(snapshot, sla.retention_days)
                    logger.info(f"WORM lock applied: snapshot {snapshot.id} locked until {snapshot.locked_until}")

            # Update protected object
            protected_object.last_backup_at = datetime.utcnow()
            protected_object.last_backup_status = "success"
            protected_object.total_items_backed_up += item_count
            protected_object.total_size_bytes += total_size

            # Save manifest
            await storage_service.save_manifest(
                tenant_id=tenant.id,
                workload=protected_object.workload_type.value,
                object_id=protected_object.ms_object_id,
                snapshot_id=snapshot.id,
                manifest={
                    "snapshot_id": snapshot.id,
                    "snapshot_type": snapshot_type.value,
                    "object_id": protected_object.ms_object_id,
                    "object_name": protected_object.display_name,
                    "workload": protected_object.workload_type.value,
                    "item_count": item_count,
                    "size_bytes": total_size,
                    "started_at": snapshot.started_at,
                    "completed_at": snapshot.completed_at,
                },
            )

            # Update job progress: completed this object
            if job:
                self._update_job_progress(job, protected_object, "completed",
                                          item_count=item_count, size_bytes=total_size,
                                          snapshot_id=snapshot.id)
                job.total_items += item_count
                job.total_size_bytes += total_size

            await self.db.commit()
            logger.info(
                f"Backup completed: {protected_object.display_name} — "
                f"{item_count} items, {total_size} bytes"
            )
            return snapshot

        except Exception as e:
            snapshot.status = SnapshotStatus.FAILED
            snapshot.error_message = str(e)
            snapshot.completed_at = datetime.utcnow()
            protected_object.last_backup_status = "failed"

            if job:
                self._update_job_progress(job, protected_object, "failed",
                                          error=str(e))

            await self.db.commit()
            raise

    def _update_job_progress(
        self,
        job: BackupJob,
        obj: ProtectedObject,
        status: str,
        detail: str = None,
        item_count: int = None,
        size_bytes: int = None,
        snapshot_id: int = None,
        error: str = None,
    ):
        """Update the progress_details JSON on a BackupJob."""
        progress = json.loads(job.progress_details) if job.progress_details else {"objects": {}}

        obj_key = str(obj.id)
        progress["objects"][obj_key] = {
            "name": obj.display_name,
            "email": obj.email,
            "workload": obj.workload_type.value,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if detail:
            progress["objects"][obj_key]["detail"] = detail
        if item_count is not None:
            progress["objects"][obj_key]["item_count"] = item_count
        if size_bytes is not None:
            progress["objects"][obj_key]["size_bytes"] = size_bytes
        if snapshot_id is not None:
            progress["objects"][obj_key]["snapshot_id"] = snapshot_id
        if error:
            progress["objects"][obj_key]["error"] = error

        # Summary counts
        statuses = [o["status"] for o in progress["objects"].values()]
        progress["summary"] = {
            "total": len(statuses),
            "completed": statuses.count("completed"),
            "failed": statuses.count("failed"),
            "in_progress": statuses.count("in_progress"),
            "pending": statuses.count("pending"),
            "total_items": sum(o.get("item_count", 0) for o in progress["objects"].values()),
            "total_size_bytes": sum(o.get("size_bytes", 0) for o in progress["objects"].values()),
        }

        job.progress_details = json.dumps(progress)

    async def _execute_backup_job(self, job: BackupJob):
        """Execute a backup job, backing up all relevant objects with progress tracking."""
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        await self.db.commit()

        # Get all protected objects for this job's workload + tenant
        result = await self.db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == job.tenant_id,
                ProtectedObject.workload_type == job.workload_type,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
                ProtectedObject.sla_policy_id == job.sla_policy_id,
            )
        )
        objects = result.scalars().all()
        job.objects_total = len(objects)

        # Initialize progress with all objects as pending
        progress = {"objects": {}, "summary": {"total": len(objects), "completed": 0, "failed": 0, "in_progress": 0, "pending": len(objects), "total_items": 0, "total_size_bytes": 0}}
        for obj in objects:
            progress["objects"][str(obj.id)] = {
                "name": obj.display_name,
                "email": obj.email,
                "workload": obj.workload_type.value,
                "status": "pending",
            }
        job.progress_details = json.dumps(progress)
        await self.db.commit()

        for obj in objects:
            try:
                await self.run_backup_for_object(obj, job=job)
                job.objects_processed += 1
            except Exception as e:
                job.objects_failed += 1
                logger.error(f"Failed to backup {obj.display_name}: {e}")
            await self.db.commit()

        # Final job status
        if job.objects_failed == 0:
            job.status = JobStatus.COMPLETED
        elif job.objects_processed > 0:
            job.status = JobStatus.PARTIAL
        else:
            job.status = JobStatus.FAILED

        job.completed_at = datetime.utcnow()
        await self.db.commit()

    async def _get_last_snapshot(self, protected_object_id: int) -> Snapshot:
        """Get the most recent completed snapshot for an object."""
        result = await self.db.execute(
            select(Snapshot)
            .where(
                Snapshot.protected_object_id == protected_object_id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
            .order_by(Snapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
