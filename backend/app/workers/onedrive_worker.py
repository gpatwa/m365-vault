"""OneDrive backup and restore worker.

Handles backup and restore of OneDrive data:
- Files and folders with full directory structure
- Uses delta queries for incremental backups
- Downloads actual file content for backup

Extends BaseWorker for parallel processing and common pipeline.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.workers.base_worker import BaseWorker, BackupItem

logger = logging.getLogger(__name__)


class OneDriveWorker(BaseWorker):
    """Worker for OneDrive backup and restore operations."""

    def workload_name(self) -> str:
        return "onedrive"

    async def discover_items(
        self,
        protected_object: ProtectedObject,
        delta_token: str = None,
    ) -> tuple[list[BackupItem], Optional[str]]:
        """Discover OneDrive files and folders via delta query."""
        user_id = protected_object.ms_object_id
        items = []
        delta_path = f"/users/{user_id}/drive/root/delta"

        try:
            if delta_token:
                drive_items, new_delta = await self.graph.get_delta(
                    delta_path, delta_token=delta_token
                )
            else:
                drive_items, new_delta = await self.graph.get_delta(delta_path)
        except Exception as e:
            logger.error(f"OneDrive delta query failed: {e}")
            return [], None

        for di in drive_items:
            if di.get("@removed") or di.get("deleted"):
                continue

            item_id = di.get("id")
            name = di.get("name", "unknown")
            is_folder = "folder" in di
            parent_path = di.get("parentReference", {}).get("path", "/drive/root:")
            path = parent_path.replace("/drive/root:", "") or "/"

            if is_folder:
                items.append(BackupItem(
                    id=item_id,
                    item_type=ItemType.FOLDER,
                    name=name,
                    path=path,
                    raw_data=di,
                    metadata={"childCount": di.get("folder", {}).get("childCount", 0)},
                    extra_fields={"file_name": name},
                ))
            else:
                # For files, we need to download content — store user_id for fetch
                items.append(BackupItem(
                    id=item_id,
                    item_type=ItemType.FILE,
                    name=name,
                    path=path,
                    raw_data=di,  # Fallback if download fails
                    mime_type=di.get("file", {}).get("mimeType", "application/octet-stream"),
                    metadata={
                        "webUrl": di.get("webUrl"),
                        "createdBy": di.get("createdBy", {}).get("user", {}).get("displayName"),
                        "_user_id": user_id,  # For fetch_item_data
                        "_needs_download": True,
                    },
                    extra_fields={
                        "file_name": name,
                        "content_mime_type": di.get("file", {}).get("mimeType"),
                        "last_modified_at": datetime.fromisoformat(
                            di["lastModifiedDateTime"].replace("Z", "+00:00")
                        ).replace(tzinfo=None) if di.get("lastModifiedDateTime") else None,
                    },
                ))

        logger.info(f"OneDrive discovery: {len(items)} items ({len([i for i in items if i.item_type == ItemType.FILE])} files, {len([i for i in items if i.item_type == ItemType.FOLDER])} folders)")
        return items, new_delta

    async def pre_backup(self, protected_object, snapshot):
        """Download file content for all file items before parallel processing."""
        # File content download happens in _process_single_item via raw_data fallback
        # or we could batch download here. For now, handled inline.
        pass

    async def _process_single_item(self, item, protected_object, snapshot, wrapped_dek, counters):
        """Override to download file content before storing."""
        if item.metadata.get("_needs_download") and item.binary_data is None:
            user_id = item.metadata.get("_user_id", protected_object.ms_object_id)
            try:
                file_content = await self.graph.get_binary(
                    f"/users/{user_id}/drive/items/{item.id}/content"
                )
                item.binary_data = file_content
            except Exception as e:
                logger.warning(f"Could not download file {item.name}: {e}, storing metadata only")
                # Fallback: store metadata as JSON
                item.binary_data = None  # Will use raw_data

        await super()._process_single_item(item, protected_object, snapshot, wrapped_dek, counters)

    # ═══════════════════════════════════════════════════════
    # Restore Operations
    # ═══════════════════════════════════════════════════════

    async def restore_full_account(
        self, protected_object: ProtectedObject, snapshot: Snapshot,
        wrapped_dek: str, target_user_id: str = None,
    ) -> int:
        """Restore entire OneDrive account from snapshot."""
        target = target_user_id or protected_object.ms_object_id
        items_restored = 0

        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.snapshot_id == snapshot.id)
            .order_by(SnapshotItem.path, SnapshotItem.item_type.desc())
        )
        items = result.scalars().all()

        for item in items:
            try:
                if item.item_type == ItemType.FOLDER:
                    await self.graph.post(
                        f"/users/{target}/drive/root:{item.path}:/children",
                        json_data={"name": item.name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"},
                    )
                    items_restored += 1
                elif item.item_type == ItemType.FILE:
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    upload_path = f"{item.path}/{item.name}".replace("//", "/")
                    await self.graph.put(f"/users/{target}/drive/root:{upload_path}:/content", data=data)
                    items_restored += 1
            except Exception as e:
                logger.error(f"Failed to restore {item.name}: {e}")

        return items_restored

    async def restore_items(
        self, item_ids: list[int], snapshot: Snapshot, wrapped_dek: str,
        target_user_id: str = None, protected_object: ProtectedObject = None,
    ) -> int:
        target = target_user_id or protected_object.ms_object_id
        items_restored = 0

        result = await self.db.execute(select(SnapshotItem).where(SnapshotItem.id.in_(item_ids)))
        for item in result.scalars().all():
            try:
                if item.item_type == ItemType.FILE:
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    path = f"{item.path}/{item.name}".replace("//", "/")
                    await self.graph.put(f"/users/{target}/drive/root:{path}:/content", data=data)
                    items_restored += 1
            except Exception as e:
                logger.error(f"Failed to restore {item.id}: {e}")

        return items_restored
