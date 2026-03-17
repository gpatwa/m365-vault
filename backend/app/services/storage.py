"""Local filesystem storage service for backup blobs.

Directory structure:
  data/{tenant_id}/{workload}/{object_id}/{snapshot_id}/
    manifest.json     — Snapshot metadata
    wrapped_dek.key   — Encrypted DEK for this snapshot
    items/
      {item_id}.blob  — Encrypted item data
"""
import os
import json
import aiofiles
from typing import Optional
from datetime import datetime

from app.config import settings
from app.services.encryption import encryption_service


class StorageService:
    """Manages encrypted backup blob storage on local filesystem."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.BACKUP_STORAGE_PATH

    def _snapshot_path(self, tenant_id: int, workload: str, object_id: str, snapshot_id: int) -> str:
        return os.path.join(
            self.base_path,
            str(tenant_id),
            workload,
            str(object_id),
            str(snapshot_id),
        )

    def _items_path(self, tenant_id: int, workload: str, object_id: str, snapshot_id: int) -> str:
        return os.path.join(
            self._snapshot_path(tenant_id, workload, object_id, snapshot_id),
            "items",
        )

    async def init_snapshot_storage(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ) -> tuple[str, str]:
        """Initialize storage for a new snapshot.

        Returns (wrapped_dek, blob_base_path).
        """
        snapshot_dir = self._snapshot_path(tenant_id, workload, object_id, snapshot_id)
        items_dir = self._items_path(tenant_id, workload, object_id, snapshot_id)
        os.makedirs(items_dir, exist_ok=True)

        # Generate a unique DEK for this snapshot
        dek = encryption_service.generate_dek()
        wrapped_dek = encryption_service.encrypt_dek(dek)

        # Store wrapped DEK
        key_path = os.path.join(snapshot_dir, "wrapped_dek.key")
        async with aiofiles.open(key_path, "w") as f:
            await f.write(wrapped_dek)

        return wrapped_dek, snapshot_dir

    async def store_item(
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        item_id: str,
        data: bytes,
        wrapped_dek: str,
    ) -> str:
        """Encrypt and store a backup item. Returns the blob path."""
        items_dir = self._items_path(tenant_id, workload, object_id, snapshot_id)
        os.makedirs(items_dir, exist_ok=True)

        # Decrypt DEK, encrypt data
        dek = encryption_service.decrypt_dek(wrapped_dek)
        encrypted_data = encryption_service.encrypt_data(data, dek)

        # Write encrypted blob
        blob_filename = f"{item_id}.blob"
        blob_path = os.path.join(items_dir, blob_filename)
        async with aiofiles.open(blob_path, "wb") as f:
            await f.write(encrypted_data)

        return blob_path

    async def retrieve_item(
        self,
        blob_path: str,
        wrapped_dek: str,
    ) -> bytes:
        """Retrieve and decrypt a backup item."""
        async with aiofiles.open(blob_path, "rb") as f:
            encrypted_data = await f.read()

        dek = encryption_service.decrypt_dek(wrapped_dek)
        return encryption_service.decrypt_data(encrypted_data, dek)

    async def save_manifest(
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        manifest: dict,
    ):
        """Save snapshot manifest (metadata)."""
        snapshot_dir = self._snapshot_path(tenant_id, workload, object_id, snapshot_id)
        os.makedirs(snapshot_dir, exist_ok=True)
        manifest_path = os.path.join(snapshot_dir, "manifest.json")
        async with aiofiles.open(manifest_path, "w") as f:
            await f.write(json.dumps(manifest, indent=2, default=str))

    async def load_manifest(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ) -> Optional[dict]:
        """Load snapshot manifest."""
        manifest_path = os.path.join(
            self._snapshot_path(tenant_id, workload, object_id, snapshot_id),
            "manifest.json",
        )
        if not os.path.exists(manifest_path):
            return None
        async with aiofiles.open(manifest_path, "r") as f:
            return json.loads(await f.read())

    async def get_wrapped_dek(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ) -> Optional[str]:
        """Retrieve the wrapped DEK for a snapshot."""
        key_path = os.path.join(
            self._snapshot_path(tenant_id, workload, object_id, snapshot_id),
            "wrapped_dek.key",
        )
        if not os.path.exists(key_path):
            return None
        async with aiofiles.open(key_path, "r") as f:
            return await f.read()

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        total_size = 0
        total_files = 0
        for dirpath, dirnames, filenames in os.walk(self.base_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
                total_files += 1
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": total_files,
            "storage_path": self.base_path,
        }

    async def delete_snapshot_storage(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ):
        """Delete all storage for a snapshot (for retention cleanup)."""
        import shutil
        snapshot_dir = self._snapshot_path(tenant_id, workload, object_id, snapshot_id)
        if os.path.exists(snapshot_dir):
            shutil.rmtree(snapshot_dir)


storage_service = StorageService()
