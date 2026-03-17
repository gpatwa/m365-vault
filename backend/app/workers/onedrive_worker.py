"""OneDrive backup and restore worker.

Handles backup and restore of OneDrive data:
- Files and folders with full directory structure
- Uses delta queries for incremental backups
- Downloads actual file content for backup
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient, GraphAPIError
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.utils.retry import retry_async, record_failed_item

logger = logging.getLogger(__name__)

ITEM_MAX_RETRIES = 3
ITEM_BASE_DELAY = 2.0


class OneDriveWorker:
    """Worker for OneDrive backup and restore operations."""

    def __init__(
        self,
        db: AsyncSession,
        graph: GraphClient,
        storage: StorageService,
        encryption: EncryptionService,
    ):
        self.db = db
        self.graph = graph
        self.storage = storage
        self.encryption = encryption

    async def backup(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
    ) -> tuple[int, int, str]:
        """Backup a OneDrive account using delta queries.

        Returns (item_count, total_size_bytes, new_delta_token).
        """
        user_id = protected_object.ms_object_id
        delta_path = f"/users/{user_id}/drive/root/delta"

        if delta_token:
            items, new_delta_token = await self.graph.get_delta(
                delta_path, delta_token=delta_token
            )
        else:
            items, new_delta_token = await self.graph.get_delta(delta_path)

        for drive_item in items:
            try:
                if drive_item.get("@removed") or drive_item.get("deleted"):
                    continue
                await self._backup_single_item(
                    user_id=user_id,
                    drive_item=drive_item,
                    protected_object=protected_object,
                    snapshot=snapshot,
                    wrapped_dek=wrapped_dek,
                )
            except Exception as e:
                logger.error(f"Failed to backup OneDrive item {drive_item.get('id')} after retries: {e}")
                is_folder = "folder" in drive_item
                await record_failed_item(
                    db=self.db, snapshot_id=snapshot.id,
                    protected_object_id=protected_object.id, error=e,
                    ms_item_id=drive_item.get("id"),
                    item_type_str="folder" if is_folder else "file",
                    item_name=drive_item.get("name", "unknown"),
                    item_path=drive_item.get("parentReference", {}).get("path", ""),
                    retries_attempted=ITEM_MAX_RETRIES,
                )

        await self.db.flush()

        # Get counts
        result = await self.db.execute(
            select(func.count(SnapshotItem.id), func.sum(SnapshotItem.size_bytes))
            .where(SnapshotItem.snapshot_id == snapshot.id)
        )
        row = result.one()
        return row[0] or 0, row[1] or 0, new_delta_token

    @retry_async(max_retries=ITEM_MAX_RETRIES, base_delay=ITEM_BASE_DELAY)
    async def _backup_single_item(
        self,
        user_id: str,
        drive_item: dict,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
    ):
        """Backup a single OneDrive file/folder with retry support."""
        item_id = drive_item.get("id")
        name = drive_item.get("name", "unknown")
        is_folder = "folder" in drive_item
        parent_path = drive_item.get("parentReference", {}).get("path", "/drive/root:")
        path = parent_path.replace("/drive/root:", "")
        if not path:
            path = "/"

        if is_folder:
            folder_data = json.dumps(drive_item, default=str).encode("utf-8")
            blob_path = await self.storage.store_item(
                tenant_id=protected_object.tenant_id,
                workload="onedrive",
                object_id=protected_object.ms_object_id,
                snapshot_id=snapshot.id,
                item_id=item_id,
                data=folder_data,
                wrapped_dek=wrapped_dek,
            )
            catalog_item = SnapshotItem(
                snapshot_id=snapshot.id,
                item_type=ItemType.FOLDER,
                ms_item_id=item_id,
                name=name,
                path=path,
                size_bytes=0,
                blob_path=blob_path,
                file_name=name,
                metadata_json=json.dumps({
                    "childCount": drive_item.get("folder", {}).get("childCount", 0),
                }),
            )
            self.db.add(catalog_item)
        else:
            file_size = drive_item.get("size", 0)
            try:
                file_content = await self.graph.get_binary(
                    f"/users/{user_id}/drive/items/{item_id}/content"
                )
            except Exception as e:
                logger.warning(f"Could not download file {name}: {e}")
                file_content = json.dumps(drive_item, default=str).encode("utf-8")

            blob_path = await self.storage.store_item(
                tenant_id=protected_object.tenant_id,
                workload="onedrive",
                object_id=protected_object.ms_object_id,
                snapshot_id=snapshot.id,
                item_id=item_id,
                data=file_content,
                wrapped_dek=wrapped_dek,
            )

            last_modified = drive_item.get("lastModifiedDateTime")
            mime_type = drive_item.get("file", {}).get("mimeType")
            content_hash = drive_item.get("file", {}).get("hashes", {}).get("sha256Hash")

            catalog_item = SnapshotItem(
                snapshot_id=snapshot.id,
                item_type=ItemType.FILE,
                ms_item_id=item_id,
                name=name,
                path=path,
                size_bytes=file_size,
                content_hash=content_hash,
                blob_path=blob_path,
                file_name=name,
                mime_type=mime_type,
                last_modified_at=datetime.fromisoformat(
                    last_modified.replace("Z", "+00:00")
                ) if last_modified else None,
                metadata_json=json.dumps({
                    "webUrl": drive_item.get("webUrl"),
                    "createdBy": drive_item.get("createdBy", {}).get("user", {}).get("displayName"),
                }),
            )
            self.db.add(catalog_item)

    async def restore_full_account(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        target_user_id: str = None,
    ) -> int:
        """Restore entire OneDrive account from snapshot."""
        target = target_user_id or protected_object.ms_object_id
        items_restored = 0

        # Get all files and folders, sorted by path to ensure correct order
        result = await self.db.execute(
            select(SnapshotItem)
            .where(SnapshotItem.snapshot_id == snapshot.id)
            .order_by(SnapshotItem.path, SnapshotItem.item_type.desc())  # Folders first
        )
        items = result.scalars().all()

        # Track created folders
        created_folders = {}

        for item in items:
            try:
                if item.item_type == ItemType.FOLDER:
                    # Create folder
                    folder_path = f"{item.path}/{item.name}".replace("//", "/")
                    try:
                        result = await self.graph.post(
                            f"/users/{target}/drive/root:{item.path}:/children",
                            json_data={
                                "name": item.name,
                                "folder": {},
                                "@microsoft.graph.conflictBehavior": "rename",
                            },
                        )
                        created_folders[folder_path] = result.get("id")
                        items_restored += 1
                    except Exception as e:
                        logger.warning(f"Folder may already exist: {item.name}: {e}")

                elif item.item_type == ItemType.FILE:
                    # Download from backup and upload to OneDrive
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    upload_path = f"{item.path}/{item.name}".replace("//", "/")

                    await self.graph.put(
                        f"/users/{target}/drive/root:{upload_path}:/content",
                        data=data,
                    )
                    items_restored += 1

            except Exception as e:
                logger.error(f"Failed to restore OneDrive item {item.name}: {e}")

        return items_restored

    async def restore_items(
        self,
        item_ids: list[int],
        snapshot: Snapshot,
        wrapped_dek: str,
        target_user_id: str = None,
        protected_object: ProtectedObject = None,
    ) -> int:
        """Restore specific OneDrive files/folders."""
        target = target_user_id or protected_object.ms_object_id
        items_restored = 0

        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()

        for item in items:
            try:
                if item.item_type == ItemType.FILE:
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    upload_path = f"{item.path}/{item.name}".replace("//", "/")
                    await self.graph.put(
                        f"/users/{target}/drive/root:{upload_path}:/content",
                        data=data,
                    )
                    items_restored += 1

            except Exception as e:
                logger.error(f"Failed to restore item {item.id}: {e}")

        return items_restored

    async def download_file(
        self,
        item_id: int,
        wrapped_dek: str,
    ) -> tuple[str, bytes]:
        """Download a backed-up file. Returns (filename, file_data)."""
        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"Item {item_id} not found")

        data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
        return item.file_name or item.name, data
