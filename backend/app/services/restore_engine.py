"""Restore orchestration engine.

Coordinates restore jobs across all workloads with support for:
- Full in-place restore
- Item-level restore
- Cross-user restore
- Export/download
- Mass recovery (parallel multi-object restore)
"""
import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.tenant import Tenant
from app.services.graph_client import GraphClient
from app.services.encryption import encryption_service
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class RestoreEngine:
    """Orchestrates restore operations across all workloads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_graph_client(self, tenant: Tenant) -> GraphClient:
        """Create a read-write Graph client for restore operations.

        Restore operations need write access to M365 data (POST/PUT) to
        recreate messages, upload files, and restore SharePoint items.
        """
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret,
            access_mode="restore",
        )

    async def execute_restore(self, restore_job: RestoreJob) -> RestoreJob:
        """Execute a restore job."""
        restore_job.status = RestoreStatus.IN_PROGRESS
        restore_job.started_at = datetime.utcnow()
        await self.db.commit()

        try:
            # Load related objects
            snapshot = await self.db.get(Snapshot, restore_job.source_snapshot_id)
            source_obj = await self.db.get(ProtectedObject, restore_job.source_object_id)
            tenant = await self.db.get(Tenant, restore_job.tenant_id)

            if not all([snapshot, source_obj, tenant]):
                raise ValueError("Required objects not found")

            if snapshot.status != SnapshotStatus.COMPLETED:
                raise ValueError(f"Snapshot {snapshot.id} is not in completed state")

            graph = self._get_graph_client(tenant)

            # Get wrapped DEK for decryption
            wrapped_dek = await storage_service.get_wrapped_dek(
                tenant_id=tenant.id,
                workload=source_obj.workload_type.value,
                object_id=source_obj.ms_object_id,
                snapshot_id=snapshot.id,
            )
            if not wrapped_dek:
                raise ValueError("Encryption key not found for snapshot")

            # Determine target user for cross-user restore
            target_user_id = None
            if restore_job.restore_type == RestoreType.CROSS_USER and restore_job.target_object_id:
                target_obj = await self.db.get(ProtectedObject, restore_job.target_object_id)
                if target_obj:
                    target_user_id = target_obj.ms_object_id

            # Dispatch to appropriate worker
            from app.workers.exchange_worker import ExchangeWorker
            from app.workers.onedrive_worker import OneDriveWorker
            from app.workers.sharepoint_worker import SharePointWorker
            from app.workers.teams_worker import TeamsWorker
            from app.workers.entra_id_worker import EntraIDWorker

            worker_map = {
                WorkloadType.EXCHANGE: ExchangeWorker,
                WorkloadType.ONEDRIVE: OneDriveWorker,
                WorkloadType.SHAREPOINT: SharePointWorker,
                WorkloadType.TEAMS: TeamsWorker,
                WorkloadType.ENTRA_ID: EntraIDWorker,
            }

            worker_class = worker_map.get(source_obj.workload_type)
            if not worker_class:
                raise ValueError(f"Unknown workload type: {source_obj.workload_type}")

            worker = worker_class(
                db=self.db, graph=graph,
                storage=storage_service, encryption=encryption_service,
            )

            # ── Malware scan before restore ──
            try:
                from app.services.malware_scanner import malware_scanner
                item_ids_to_scan = json.loads(restore_job.item_ids_json) if restore_job.item_ids_json else []
                if item_ids_to_scan:
                    scan_result = await malware_scanner.scan_items(
                        self.db, item_ids_to_scan, snapshot.id, wrapped_dek
                    )
                    restore_job.scan_status = scan_result.get("status", "skipped")
                    restore_job.scan_details = json.dumps(scan_result)
                    if scan_result.get("threats_found", 0) > 0:
                        restore_job.status = RestoreStatus.FAILED
                        restore_job.error_message = f"Malware scan blocked restore: {scan_result['threats_found']} threat(s) detected"
                        restore_job.completed_at = datetime.utcnow()
                        await self.db.commit()
                        logger.warning(f"Restore job {restore_job.id} blocked by malware scan")
                        return restore_job
                else:
                    restore_job.scan_status = "clean"
            except Exception as scan_err:
                logger.warning(f"Malware scan skipped: {scan_err}")
                restore_job.scan_status = "skipped"

            items_restored = 0

            if restore_job.restore_type in (RestoreType.FULL_INPLACE, RestoreType.CROSS_USER):
                # Full restore
                if source_obj.workload_type == WorkloadType.EXCHANGE:
                    items_restored = await worker.restore_full_mailbox(
                        source_obj, snapshot, wrapped_dek, target_user_id
                    )
                elif source_obj.workload_type == WorkloadType.ONEDRIVE:
                    items_restored = await worker.restore_full_account(
                        source_obj, snapshot, wrapped_dek, target_user_id
                    )
                elif source_obj.workload_type == WorkloadType.SHAREPOINT:
                    items_restored = await worker.restore_full_site(
                        source_obj, snapshot, wrapped_dek
                    )

            elif restore_job.restore_type == RestoreType.ITEM_LEVEL:
                # Item-level restore
                item_ids = json.loads(restore_job.item_ids_json) if restore_job.item_ids_json else []
                if item_ids:
                    items_restored = await worker.restore_items(
                        item_ids=item_ids,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        target_user_id=target_user_id,
                        protected_object=source_obj,
                    )

            elif restore_job.restore_type == RestoreType.EXPORT:
                # Export (Exchange only — export .eml files)
                if source_obj.workload_type == WorkloadType.EXCHANGE:
                    item_ids = json.loads(restore_job.item_ids_json) if restore_job.item_ids_json else []
                    exports = await worker.export_to_eml(item_ids, snapshot, wrapped_dek)
                    items_restored = len(exports)
                    # Store export path info
                    restore_job.target_path = json.dumps([e["filename"] for e in exports])

            # Update job status
            restore_job.items_restored = items_restored
            restore_job.status = RestoreStatus.COMPLETED
            restore_job.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Restore job {restore_job.id} completed: {items_restored} items restored")
            return restore_job

        except Exception as e:
            restore_job.status = RestoreStatus.FAILED
            restore_job.error_message = str(e)
            restore_job.completed_at = datetime.utcnow()
            await self.db.commit()
            logger.error(f"Restore job {restore_job.id} failed: {e}")
            raise

    async def mass_recovery(
        self,
        tenant_id: int,
        object_ids: list[int],
        snapshot_ids: dict[int, int] = None,  # {object_id: snapshot_id}
        restore_type: RestoreType = RestoreType.FULL_INPLACE,
        max_concurrent: int = 5,
    ) -> list[RestoreJob]:
        """Perform mass recovery of multiple objects in parallel.

        If snapshot_ids is not provided, uses the latest snapshot for each object.
        """
        restore_jobs = []

        for obj_id in object_ids:
            obj = await self.db.get(ProtectedObject, obj_id)
            if not obj:
                continue

            # Get snapshot
            if snapshot_ids and obj_id in snapshot_ids:
                snapshot_id = snapshot_ids[obj_id]
            else:
                # Use latest completed snapshot
                result = await self.db.execute(
                    select(Snapshot)
                    .where(
                        Snapshot.protected_object_id == obj_id,
                        Snapshot.status == SnapshotStatus.COMPLETED,
                    )
                    .order_by(Snapshot.created_at.desc())
                    .limit(1)
                )
                snapshot = result.scalar_one_or_none()
                if not snapshot:
                    logger.warning(f"No completed snapshot for object {obj_id}")
                    continue
                snapshot_id = snapshot.id

            # Create restore job
            job = RestoreJob(
                tenant_id=tenant_id,
                source_snapshot_id=snapshot_id,
                source_object_id=obj_id,
                restore_type=restore_type,
                status=RestoreStatus.QUEUED,
            )
            self.db.add(job)
            restore_jobs.append(job)

        await self.db.commit()

        # Execute in parallel with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_limit(job: RestoreJob):
            async with semaphore:
                try:
                    await self.execute_restore(job)
                except Exception as e:
                    logger.error(f"Mass recovery job {job.id} failed: {e}")

        await asyncio.gather(*[execute_with_limit(job) for job in restore_jobs])

        return restore_jobs
