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

    async def _get_graph_client(self, tenant: Tenant, workload: str) -> GraphClient:
        """Get a read-write Graph client for restore using per-workload credentials.

        Each workload has its own Entra app. Restore operations need write
        access (POST/PUT) to recreate messages, files, and config objects.
        """
        from app.services.credential_resolver import get_graph_client
        return await get_graph_client(self.db, tenant, workload, access_mode="restore")

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

            graph = await self._get_graph_client(tenant, source_obj.workload_type.value)

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

            # Dispatch to appropriate worker via registry (no hard-coded imports)
            from app.workers import get_worker_class
            worker_class = get_worker_class(source_obj.workload_type)

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

            # Determine expected item count for success calculation
            expected_items = snapshot.item_count or 0
            if restore_job.item_ids_json:
                expected_items = len(json.loads(restore_job.item_ids_json))

            # Update job status with success threshold
            restore_job.items_restored = items_restored
            restore_job.completed_at = datetime.utcnow()

            if expected_items == 0:
                restore_job.status = RestoreStatus.COMPLETED
            else:
                success_rate = (items_restored / expected_items * 100) if expected_items > 0 else 0
                # Thresholds: 95%+ = COMPLETED, 50-94% = PARTIAL, <50% = FAILED
                if success_rate >= 95:
                    restore_job.status = RestoreStatus.COMPLETED
                elif success_rate >= 50:
                    restore_job.status = RestoreStatus.PARTIAL
                    restore_job.error_message = f"Partial restore: {items_restored}/{expected_items} items ({success_rate:.0f}%)"
                else:
                    restore_job.status = RestoreStatus.FAILED
                    restore_job.error_message = f"Restore mostly failed: only {items_restored}/{expected_items} items ({success_rate:.0f}%)"

            await self.db.commit()

            logger.info(f"Restore job {restore_job.id} {restore_job.status.value}: {items_restored}/{expected_items} items restored")
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
