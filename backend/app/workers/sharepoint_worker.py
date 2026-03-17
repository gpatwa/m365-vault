"""SharePoint backup and restore worker.

Handles backup and restore of SharePoint site data:
- Document libraries (files and folders)
- Lists and list items
- Uses delta queries for incremental backups on document libraries
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


class SharePointWorker:
    """Worker for SharePoint backup and restore operations."""

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
        """Backup a SharePoint site.

        Returns (item_count, total_size_bytes, new_delta_token).
        """
        site_id = protected_object.ms_object_id
        new_delta_token = None

        # Backup document libraries
        try:
            drives = await self.graph.get_all_pages(
                f"/sites/{site_id}/drives",
                params={"$select": "id,name,driveType,webUrl"}
            )

            for drive in drives:
                drive_id = drive.get("id")
                drive_name = drive.get("name", "Documents")

                # Store drive metadata
                drive_data = json.dumps(drive, default=str).encode("utf-8")
                drv_result = await self.storage.store_item(
                    tenant_id=protected_object.tenant_id,
                    workload="sharepoint",
                    object_id=protected_object.ms_object_id,
                    snapshot_id=snapshot.id,
                    item_id=f"drive_{drive_id}",
                    data=drive_data,
                    wrapped_dek=wrapped_dek,
                    mime_type="application/json",
                    db=self.db,
                )

                doc_lib_item = SnapshotItem(
                    snapshot_id=snapshot.id,
                    item_type=ItemType.DOCUMENT_LIBRARY,
                    ms_item_id=drive_id,
                    name=drive_name,
                    path="/",
                    size_bytes=len(drive_data),
                    compressed_size=drv_result.compressed_size,
                    content_hash=drv_result.content_hash,
                    storage_flags=drv_result.storage_flags,
                    blob_path=drv_result.blob_path,
                    metadata_json=json.dumps({
                        "driveType": drive.get("driveType"),
                        "webUrl": drive.get("webUrl"),
                    }),
                )
                self.db.add(doc_lib_item)

                # Backup files in the drive using delta
                delta_path = f"/sites/{site_id}/drives/{drive_id}/root/delta"
                drive_delta_token = delta_token  # Could be per-drive in production

                if drive_delta_token:
                    items, drive_new_token = await self.graph.get_delta(
                        delta_path, delta_token=drive_delta_token
                    )
                else:
                    items, drive_new_token = await self.graph.get_delta(delta_path)

                if drive_new_token:
                    new_delta_token = drive_new_token  # Store the last one

                for drive_item in items:
                    await self._backup_drive_item(
                        site_id=site_id,
                        drive_id=drive_id,
                        drive_name=drive_name,
                        drive_item=drive_item,
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                    )

        except Exception as e:
            logger.error(f"Failed to backup document libraries for site {site_id}: {e}")

        # Backup lists
        await self._backup_lists(site_id, protected_object, snapshot, wrapped_dek)

        await self.db.flush()

        # Get counts
        result = await self.db.execute(
            select(func.count(SnapshotItem.id), func.sum(SnapshotItem.size_bytes))
            .where(SnapshotItem.snapshot_id == snapshot.id)
        )
        row = result.one()
        return row[0] or 0, row[1] or 0, new_delta_token

    @retry_async(max_retries=ITEM_MAX_RETRIES, base_delay=ITEM_BASE_DELAY)
    async def _backup_drive_item(
        self,
        site_id: str,
        drive_id: str,
        drive_name: str,
        drive_item: dict,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
    ):
        """Backup a single drive item (file or folder) with retry support."""
        try:
            if drive_item.get("@removed") or drive_item.get("deleted"):
                return

            item_id = drive_item.get("id")
            name = drive_item.get("name", "unknown")
            is_folder = "folder" in drive_item
            parent_path = drive_item.get("parentReference", {}).get("path", "")
            path = parent_path.replace(f"/drives/{drive_id}/root:", f"/{drive_name}")
            if not path:
                path = f"/{drive_name}"

            if is_folder:
                folder_data = json.dumps(drive_item, default=str).encode("utf-8")
                folder_result = await self.storage.store_item(
                    tenant_id=protected_object.tenant_id,
                    workload="sharepoint",
                    object_id=protected_object.ms_object_id,
                    snapshot_id=snapshot.id,
                    item_id=item_id,
                    data=folder_data,
                    wrapped_dek=wrapped_dek,
                    mime_type="application/json",
                    db=self.db,
                )

                catalog_item = SnapshotItem(
                    snapshot_id=snapshot.id,
                    item_type=ItemType.FOLDER,
                    ms_item_id=item_id,
                    name=name,
                    path=path,
                    size_bytes=0,
                    compressed_size=folder_result.compressed_size,
                    content_hash=folder_result.content_hash,
                    storage_flags=folder_result.storage_flags,
                    blob_path=folder_result.blob_path,
                    file_name=name,
                )
                self.db.add(catalog_item)
            else:
                # Download file content
                file_size = drive_item.get("size", 0)
                try:
                    file_content = await self.graph.get_binary(
                        f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
                    )
                except Exception:
                    file_content = json.dumps(drive_item, default=str).encode("utf-8")

                last_modified = drive_item.get("lastModifiedDateTime")
                mime_type = drive_item.get("file", {}).get("mimeType")

                file_result = await self.storage.store_item(
                    tenant_id=protected_object.tenant_id,
                    workload="sharepoint",
                    object_id=protected_object.ms_object_id,
                    snapshot_id=snapshot.id,
                    item_id=item_id,
                    data=file_content,
                    wrapped_dek=wrapped_dek,
                    filename=name,
                    mime_type=mime_type,
                    db=self.db,
                )

                catalog_item = SnapshotItem(
                    snapshot_id=snapshot.id,
                    item_type=ItemType.FILE,
                    ms_item_id=item_id,
                    name=name,
                    path=path,
                    size_bytes=file_size,
                    compressed_size=file_result.compressed_size,
                    content_hash=file_result.content_hash,
                    storage_flags=file_result.storage_flags,
                    blob_path=file_result.blob_path,
                    file_name=name,
                    mime_type=mime_type,
                    last_modified_at=datetime.fromisoformat(
                        last_modified.replace("Z", "+00:00")
                    ) if last_modified else None,
                    metadata_json=json.dumps({
                        "webUrl": drive_item.get("webUrl"),
                        "driveId": drive_id,
                    }),
                )
                self.db.add(catalog_item)

        except Exception as e:
            logger.error(f"Failed to backup drive item {drive_item.get('id')}: {e}")
            await record_failed_item(
                db=self.db, snapshot_id=snapshot.id,
                protected_object_id=protected_object.id, error=e,
                ms_item_id=drive_item.get("id"),
                item_type_str="folder" if "folder" in drive_item else "file",
                item_name=drive_item.get("name", "unknown"),
                item_path=f"/{drive_name}",
                retries_attempted=ITEM_MAX_RETRIES,
            )

    async def _backup_lists(
        self, site_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup SharePoint lists and their items."""
        try:
            lists = await self.graph.get_all_pages(
                f"/sites/{site_id}/lists",
                params={
                    "$select": "id,displayName,description,list",
                    "$filter": "list/hidden eq false",
                }
            )

            for sp_list in lists:
                list_id = sp_list.get("id")
                list_name = sp_list.get("displayName", "Unknown List")

                # Store list metadata
                list_data = json.dumps(sp_list, default=str).encode("utf-8")
                list_result = await self.storage.store_item(
                    tenant_id=protected_object.tenant_id,
                    workload="sharepoint",
                    object_id=protected_object.ms_object_id,
                    snapshot_id=snapshot.id,
                    item_id=f"list_{list_id}",
                    data=list_data,
                    wrapped_dek=wrapped_dek,
                    mime_type="application/json",
                    db=self.db,
                )

                list_item = SnapshotItem(
                    snapshot_id=snapshot.id,
                    item_type=ItemType.LIST,
                    ms_item_id=list_id,
                    name=list_name,
                    path="/Lists",
                    size_bytes=len(list_data),
                    compressed_size=list_result.compressed_size,
                    content_hash=list_result.content_hash,
                    storage_flags=list_result.storage_flags,
                    blob_path=list_result.blob_path,
                    metadata_json=json.dumps({
                        "template": sp_list.get("list", {}).get("template"),
                        "description": sp_list.get("description"),
                    }),
                )
                self.db.add(list_item)

                # Backup list items
                try:
                    list_items = await self.graph.get_all_pages(
                        f"/sites/{site_id}/lists/{list_id}/items",
                        params={"$expand": "fields", "$top": "100"}
                    )

                    for li in list_items:
                        li_id = li.get("id")
                        li_data = json.dumps(li, default=str).encode("utf-8")

                        li_result = await self.storage.store_item(
                            tenant_id=protected_object.tenant_id,
                            workload="sharepoint",
                            object_id=protected_object.ms_object_id,
                            snapshot_id=snapshot.id,
                            item_id=f"listitem_{list_id}_{li_id}",
                            data=li_data,
                            wrapped_dek=wrapped_dek,
                            mime_type="application/json",
                            db=self.db,
                        )

                        fields = li.get("fields", {})
                        li_name = fields.get("Title") or fields.get("FileLeafRef") or f"Item {li_id}"

                        li_item = SnapshotItem(
                            snapshot_id=snapshot.id,
                            item_type=ItemType.LIST_ITEM,
                            ms_item_id=li_id,
                            name=li_name,
                            path=f"/Lists/{list_name}",
                            size_bytes=len(li_data),
                            compressed_size=li_result.compressed_size,
                            content_hash=li_result.content_hash,
                            storage_flags=li_result.storage_flags,
                            blob_path=li_result.blob_path,
                            metadata_json=json.dumps(fields),
                        )
                        self.db.add(li_item)

                except Exception as e:
                    logger.error(f"Failed to backup items for list {list_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to backup lists for site {site_id}: {e}")

    async def restore_full_site(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
    ) -> int:
        """Restore entire SharePoint site from snapshot."""
        site_id = protected_object.ms_object_id
        items_restored = 0

        # Get all items sorted by path
        result = await self.db.execute(
            select(SnapshotItem)
            .where(SnapshotItem.snapshot_id == snapshot.id)
            .order_by(SnapshotItem.path, SnapshotItem.item_type.desc())
        )
        items = result.scalars().all()

        for item in items:
            try:
                if item.item_type == ItemType.FILE:
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    # Extract driveId from metadata
                    metadata = json.loads(item.metadata_json) if item.metadata_json else {}
                    drive_id = metadata.get("driveId")
                    if drive_id:
                        upload_path = f"{item.path}/{item.name}".replace("//", "/")
                        # Remove drive name prefix from path
                        parts = upload_path.split("/", 2)
                        if len(parts) > 2:
                            upload_path = "/" + parts[2]
                        else:
                            upload_path = f"/{item.name}"

                        await self.graph.put(
                            f"/sites/{site_id}/drives/{drive_id}/root:{upload_path}:/content",
                            data=data,
                        )
                        items_restored += 1

            except Exception as e:
                logger.error(f"Failed to restore SharePoint item {item.name}: {e}")

        return items_restored

    async def restore_items(
        self,
        item_ids: list[int],
        snapshot: Snapshot,
        wrapped_dek: str,
        protected_object: ProtectedObject = None,
    ) -> int:
        """Restore specific SharePoint items."""
        site_id = protected_object.ms_object_id
        items_restored = 0

        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()

        for item in items:
            try:
                if item.item_type == ItemType.FILE:
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    metadata = json.loads(item.metadata_json) if item.metadata_json else {}
                    drive_id = metadata.get("driveId")
                    if drive_id:
                        upload_path = f"/{item.name}"
                        await self.graph.put(
                            f"/sites/{site_id}/drives/{drive_id}/root:{upload_path}:/content",
                            data=data,
                        )
                        items_restored += 1

            except Exception as e:
                logger.error(f"Failed to restore item {item.id}: {e}")

        return items_restored
