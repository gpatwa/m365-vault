"""Tenant lifecycle management — deactivate, reactivate, purge.

Handles the full lifecycle of a tenant including safe cascade deletion
of all related data (jobs, snapshots, items, dedup entries, storage blobs).
"""
import logging
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus
from app.models.backup_job import BackupJob
from app.models.restore_job import RestoreJob
from app.models.snapshot import Snapshot, SnapshotItem, FailedItem
from app.models.dedup import DedupEntry
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class TenantLifecycleService:
    """Manages tenant lifecycle: deactivate, reactivate, purge."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def deactivate(self, tenant: Tenant) -> dict:
        """Deactivate a tenant — stops backups, preserves all data.

        Sets tenant status to INACTIVE and pauses all protected objects.
        Backups can be resumed via reactivate().
        """
        tenant.status = TenantStatus.INACTIVE
        tenant.updated_at = datetime.utcnow()

        # Pause all protected objects
        result = await self.db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == tenant.id,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )
        objects = result.scalars().all()
        paused_count = 0
        for obj in objects:
            obj.status = ProtectionStatus.PAUSED
            paused_count += 1

        await self.db.commit()
        logger.info(f"Tenant {tenant.name} deactivated: {paused_count} objects paused")

        return {
            "status": "deactivated",
            "objects_paused": paused_count,
        }

    async def reactivate(self, tenant: Tenant) -> dict:
        """Reactivate a tenant — resumes backups for objects with SLA policies.

        Sets tenant status to ACTIVE and restores PAUSED objects to PROTECTED
        (only those that have an SLA policy assigned).
        """
        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.utcnow()

        # Reactivate paused objects that have SLA policies
        result = await self.db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == tenant.id,
                ProtectedObject.status == ProtectionStatus.PAUSED,
            )
        )
        objects = result.scalars().all()
        reactivated_count = 0
        skipped_count = 0
        for obj in objects:
            if obj.sla_policy_id:
                obj.status = ProtectionStatus.PROTECTED
                reactivated_count += 1
            else:
                obj.status = ProtectionStatus.UNPROTECTED
                skipped_count += 1

        await self.db.commit()
        logger.info(
            f"Tenant {tenant.name} reactivated: {reactivated_count} objects resumed, "
            f"{skipped_count} unprotected (no SLA)"
        )

        return {
            "status": "reactivated",
            "objects_reactivated": reactivated_count,
            "objects_unprotected": skipped_count,
        }

    async def purge(self, tenant: Tenant) -> dict:
        """Permanently delete a tenant and ALL associated data.

        Cascade deletes in FK-safe order:
        1. RestoreJobs
        2. BackupJobs
        3. Snapshots (with storage + dedup cleanup)
        4. ProtectedObjects
        5. DedupEntries
        6. Storage blobs (prefix delete)
        7. Tenant record

        This is IRREVERSIBLE.
        """
        tenant_id = tenant.id
        tenant_name = tenant.name
        stats = {
            "restore_jobs_deleted": 0,
            "backup_jobs_deleted": 0,
            "snapshots_deleted": 0,
            "items_deleted": 0,
            "objects_deleted": 0,
            "dedup_entries_deleted": 0,
        }

        logger.info(f"Starting purge for tenant {tenant_name} (id={tenant_id})")

        # 1. Delete RestoreJobs
        result = await self.db.execute(
            delete(RestoreJob).where(RestoreJob.tenant_id == tenant_id)
        )
        stats["restore_jobs_deleted"] = result.rowcount
        logger.info(f"  Deleted {result.rowcount} restore jobs")

        # 2. Delete BackupJobs
        result = await self.db.execute(
            delete(BackupJob).where(BackupJob.tenant_id == tenant_id)
        )
        stats["backup_jobs_deleted"] = result.rowcount
        logger.info(f"  Deleted {result.rowcount} backup jobs")

        # 3. Delete Snapshots + SnapshotItems + FailedItems + storage
        obj_result = await self.db.execute(
            select(ProtectedObject).where(ProtectedObject.tenant_id == tenant_id)
        )
        protected_objects = obj_result.scalars().all()

        for obj in protected_objects:
            snap_result = await self.db.execute(
                select(Snapshot).where(Snapshot.protected_object_id == obj.id)
            )
            snapshots = snap_result.scalars().all()

            for snapshot in snapshots:
                # Delete SnapshotItems
                item_result = await self.db.execute(
                    delete(SnapshotItem).where(SnapshotItem.snapshot_id == snapshot.id)
                )
                stats["items_deleted"] += item_result.rowcount

                # Delete FailedItems
                await self.db.execute(
                    delete(FailedItem).where(FailedItem.snapshot_id == snapshot.id)
                )

                # Clean up storage blobs + dedup refs
                try:
                    await storage_service.delete_snapshot_storage(
                        tenant_id=tenant_id,
                        workload=obj.workload_type.value,
                        object_id=obj.ms_object_id,
                        snapshot_id=snapshot.id,
                    )
                except Exception as e:
                    logger.warning(f"  Storage cleanup failed for snapshot {snapshot.id}: {e}")

                # Delete snapshot record
                await self.db.delete(snapshot)
                stats["snapshots_deleted"] += 1

        logger.info(f"  Deleted {stats['snapshots_deleted']} snapshots, {stats['items_deleted']} items")

        # 4. Delete ProtectedObjects
        result = await self.db.execute(
            delete(ProtectedObject).where(ProtectedObject.tenant_id == tenant_id)
        )
        stats["objects_deleted"] = result.rowcount
        logger.info(f"  Deleted {result.rowcount} protected objects")

        # 5. Delete remaining DedupEntries (should be mostly cleaned by step 3)
        result = await self.db.execute(
            delete(DedupEntry).where(DedupEntry.tenant_id == tenant_id)
        )
        stats["dedup_entries_deleted"] = result.rowcount
        if result.rowcount > 0:
            logger.info(f"  Deleted {result.rowcount} orphaned dedup entries")

        # 6. Clean up any orphaned storage blobs under this tenant prefix
        try:
            deleted_blobs = await storage_service.backend.delete_prefix(f"{tenant_id}/")
            logger.info(f"  Cleaned up {deleted_blobs} storage blobs")
        except Exception as e:
            logger.warning(f"  Storage prefix cleanup failed: {e}")

        # 7. Delete Tenant record
        await self.db.delete(tenant)
        await self.db.commit()

        logger.info(f"Tenant {tenant_name} purged successfully: {stats}")

        return {
            "status": "purged",
            "tenant_name": tenant_name,
            **stats,
        }
