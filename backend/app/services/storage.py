"""Backup storage service with compression + dedup pipeline.

Pipeline (store):
  Raw data -> Compress -> M3VZ Header -> Hash -> Dedup check -> CDC (if large)
  -> Encrypt -> Write -> Register dedup

Pipeline (retrieve):
  Read -> Decrypt -> Check M3VZ header -> Dechunk (if chunked) -> Decompress -> Return

Storage key layout:
  {tenant_id}/{workload}/{object_id}/{snapshot_id}/
    manifest.json     - Snapshot metadata
    wrapped_dek.key   - Encrypted DEK for this snapshot
    items/
      {item_id}.blob  - Encrypted item data

  {tenant_id}/.chunks/{hash[:2]}/{hash[2:4]}/{hash}.chunk  - CDC chunks

Backward compatibility:
  Legacy blobs (no M3VZ header after decryption) are returned as-is.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.compression import compression_service, FLAG_COMPRESSED, FLAG_CHUNKED
from app.services.dedup import dedup_service, sha256_hex, ChunkInfo
from app.services.encryption import encryption_service
from app.services.storage_backend import StorageBackend

logger = logging.getLogger(__name__)


@dataclass
class StoreResult:
    """Result of storing an item through the compression/dedup pipeline."""
    blob_path: str
    content_hash: str           # SHA-256 of compressed data
    original_size: int          # Size of raw input data
    compressed_size: int        # Size after compression (before encryption)
    was_compressed: bool
    is_chunked: bool
    is_duplicate: bool
    storage_flags: int          # Bitmask: bit 0=compressed, 1=chunked, 2=deduped


class ChunkStore:
    """Manages encrypted chunk storage via the pluggable backend.

    Chunk key layout:
      {tenant_id}/.chunks/{hash[:2]}/{hash[2:4]}/{hash}.chunk
    Two-level fan-out prevents too many objects per prefix.
    """

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    def _chunk_key(self, tenant_id: int, chunk_hash: str) -> str:
        return f"{tenant_id}/.chunks/{chunk_hash[:2]}/{chunk_hash[2:4]}/{chunk_hash}.chunk"

    async def chunk_exists(self, tenant_id: int, chunk_hash: str) -> bool:
        return await self.backend.exists(self._chunk_key(tenant_id, chunk_hash))

    async def store_chunk(self, tenant_id: int, chunk_hash: str, encrypted_data: bytes) -> str:
        key = self._chunk_key(tenant_id, chunk_hash)
        if await self.backend.exists(key):
            return key
        await self.backend.write(key, encrypted_data)
        return key

    async def retrieve_chunk(self, tenant_id: int, chunk_hash: str) -> bytes:
        return await self.backend.read(self._chunk_key(tenant_id, chunk_hash))

    async def delete_chunk(self, tenant_id: int, chunk_hash: str) -> bool:
        return await self.backend.delete(self._chunk_key(tenant_id, chunk_hash))


class StorageService:
    """Manages encrypted backup blob storage with compression and dedup.

    Uses a pluggable StorageBackend for all I/O — supports local filesystem,
    Azure Blob Storage, and MinIO/S3.
    """

    def __init__(self, backend: StorageBackend):
        self.backend = backend
        self.chunk_store = ChunkStore(backend)

    def _snapshot_key(self, tenant_id: int, workload: str, object_id: str, snapshot_id: int) -> str:
        return f"{tenant_id}/{workload}/{object_id}/{snapshot_id}"

    def _items_key(self, tenant_id: int, workload: str, object_id: str, snapshot_id: int) -> str:
        return f"{self._snapshot_key(tenant_id, workload, object_id, snapshot_id)}/items"

    async def init_snapshot_storage(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ) -> tuple[str, str]:
        """Initialize storage for a new snapshot.

        Returns (wrapped_dek, snapshot_key).
        """
        snapshot_key = self._snapshot_key(tenant_id, workload, object_id, snapshot_id)

        # Generate a unique DEK for this snapshot
        dek = encryption_service.generate_dek()
        wrapped_dek = encryption_service.encrypt_dek(dek)

        # Store wrapped DEK
        dek_key = f"{snapshot_key}/wrapped_dek.key"
        await self.backend.write(dek_key, wrapped_dek.encode("utf-8"))

        return wrapped_dek, snapshot_key

    async def store_item(
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        item_id: str,
        data: bytes,
        wrapped_dek: str,
        filename: str = None,
        mime_type: str = None,
        db: AsyncSession = None,
    ) -> StoreResult:
        """Compress, dedup, encrypt, and store a backup item.

        Pipeline:
          1. COMPRESS  - zstd with content-aware level selection
          2. HEADER    - prepend M3VZ + flags byte
          3. HASH      - SHA-256 of compressed data (for dedup)
          4. DEDUP     - check if identical content already stored for this tenant
          5. CDC       - if >= 4MB, split into variable chunks
          6. ENCRYPT   - AES-256-GCM with snapshot DEK
          7. WRITE     - write to storage backend
          8. REGISTER  - add to dedup index (if db session provided)

        Returns StoreResult with blob_path and storage metadata.
        """
        original_size = len(data)

        # --- 1. COMPRESS ---
        level = compression_service.choose_level(
            filename=filename, mime_type=mime_type, data=data
        )
        compressed_data, was_compressed = compression_service.compress(data, level)
        compressed_size = len(compressed_data)

        # --- 2. HEADER --- prepend inside the encrypted envelope
        is_chunked = dedup_service.needs_chunking(compressed_data)
        header = compression_service.encode_header(
            was_compressed=was_compressed,
            is_chunked=is_chunked,
        )
        payload = header + compressed_data

        # --- 3. HASH --- content hash of compressed data (excluding header)
        content_hash = dedup_service.compute_hash(compressed_data)

        # --- 4. DEDUP CHECK ---
        is_duplicate = False
        existing_blob_path = None
        if settings.DEDUP_ENABLED and db is not None:
            existing_blob_path = await self._check_dedup(db, tenant_id, content_hash)
            if existing_blob_path:
                is_duplicate = True
                await self._increment_ref_count(db, tenant_id, content_hash)
                logger.debug(
                    f"Dedup hit: {item_id} ({content_hash[:12]}...) → existing blob"
                )

        # Build storage flags bitmask
        storage_flags = 0
        if was_compressed:
            storage_flags |= 0x01  # FLAG_COMPRESSED
        if is_chunked:
            storage_flags |= 0x02  # FLAG_CHUNKED
        if is_duplicate:
            storage_flags |= 0x04  # FLAG_DEDUPED

        if is_duplicate and existing_blob_path:
            return StoreResult(
                blob_path=existing_blob_path,
                content_hash=content_hash,
                original_size=original_size,
                compressed_size=compressed_size,
                was_compressed=was_compressed,
                is_chunked=is_chunked,
                is_duplicate=True,
                storage_flags=storage_flags,
            )

        # --- 5. CDC CHUNKING (for large files) ---
        dek = encryption_service.decrypt_dek(wrapped_dek)

        if is_chunked:
            blob_key = await self._store_chunked(
                tenant_id=tenant_id,
                workload=workload,
                object_id=object_id,
                snapshot_id=snapshot_id,
                item_id=item_id,
                payload=payload,
                compressed_data=compressed_data,
                dek=dek,
                db=db,
                content_hash=content_hash,
            )
        else:
            # --- 6. ENCRYPT whole blob ---
            encrypted_data = encryption_service.encrypt_data(payload, dek)

            # --- 7. WRITE ---
            blob_key = f"{self._items_key(tenant_id, workload, object_id, snapshot_id)}/{item_id}.blob"
            await self.backend.write(blob_key, encrypted_data)

        # --- 8. REGISTER DEDUP ---
        if settings.DEDUP_ENABLED and db is not None and not is_duplicate:
            await self._register_dedup(
                db=db,
                tenant_id=tenant_id,
                content_hash=content_hash,
                blob_path=blob_key,
                size_bytes=compressed_size,
                original_size=original_size,
                is_chunk=False,
            )

        if was_compressed:
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            logger.debug(
                f"Stored {item_id}: {original_size}B → {compressed_size}B "
                f"({ratio:.1f}% saved) chunked={is_chunked}"
            )

        return StoreResult(
            blob_path=blob_key,
            content_hash=content_hash,
            original_size=original_size,
            compressed_size=compressed_size,
            was_compressed=was_compressed,
            is_chunked=is_chunked,
            is_duplicate=False,
            storage_flags=storage_flags,
        )

    async def _store_chunked(
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        item_id: str,
        payload: bytes,
        compressed_data: bytes,
        dek: bytes,
        db: AsyncSession = None,
        content_hash: str = None,
    ) -> str:
        """Store a large item as CDC chunks + manifest."""
        chunks = dedup_service.cdc_chunk(compressed_data)

        chunk_entries = []
        for chunk_info in chunks:
            chunk_data = compressed_data[chunk_info.offset:chunk_info.offset + chunk_info.length]

            if await self.chunk_store.chunk_exists(tenant_id, chunk_info.hash):
                if db is not None:
                    await self._increment_ref_count(db, tenant_id, chunk_info.hash)
            else:
                encrypted_chunk = encryption_service.encrypt_data(chunk_data, dek)
                chunk_key = await self.chunk_store.store_chunk(tenant_id, chunk_info.hash, encrypted_chunk)

                if db is not None:
                    await self._register_dedup(
                        db=db,
                        tenant_id=tenant_id,
                        content_hash=chunk_info.hash,
                        blob_path=chunk_key,
                        size_bytes=chunk_info.length,
                        original_size=chunk_info.length,
                        is_chunk=True,
                    )

            chunk_entries.append({
                "hash": chunk_info.hash,
                "offset": chunk_info.offset,
                "length": chunk_info.length,
            })

        # Build manifest
        manifest = {
            "version": 1,
            "content_hash": content_hash,
            "total_size": len(compressed_data),
            "chunk_count": len(chunk_entries),
            "chunks": chunk_entries,
        }
        manifest_bytes = json.dumps(manifest).encode("utf-8")

        header = compression_service.encode_header(was_compressed=True, is_chunked=True)
        header_and_manifest = header + manifest_bytes
        encrypted_manifest = encryption_service.encrypt_data(header_and_manifest, dek)

        blob_key = f"{self._items_key(tenant_id, workload, object_id, snapshot_id)}/{item_id}.blob"
        await self.backend.write(blob_key, encrypted_manifest)

        logger.debug(f"Chunked store: {item_id} → {len(chunks)} chunks")
        return blob_key

    async def retrieve_item(
        self,
        blob_path: str,
        wrapped_dek: str,
        tenant_id: int = None,
    ) -> bytes:
        """Retrieve, decrypt, and decompress a backup item.

        Backward compatibility: legacy blobs (no M3VZ header) are returned as-is.
        """
        encrypted_data = await self.backend.read(blob_path)

        dek = encryption_service.decrypt_dek(wrapped_dek)
        decrypted = encryption_service.decrypt_data(encrypted_data, dek)

        # Check for M3VZ header
        has_header, offset, is_compressed, is_chunked = compression_service.decode_header(decrypted)

        if not has_header:
            return decrypted

        if is_chunked:
            manifest_bytes = decrypted[offset:]
            manifest = json.loads(manifest_bytes)

            reassembled = bytearray()
            for chunk_entry in manifest["chunks"]:
                chunk_hash = chunk_entry["hash"]
                if tenant_id is None:
                    raise ValueError("tenant_id required to retrieve chunked items")
                encrypted_chunk = await self.chunk_store.retrieve_chunk(tenant_id, chunk_hash)
                chunk_data = encryption_service.decrypt_data(encrypted_chunk, dek)
                reassembled.extend(chunk_data)

            compressed_data = bytes(reassembled)
        else:
            compressed_data = decrypted[offset:]

        if is_compressed:
            return compression_service.decompress(compressed_data)
        else:
            return compressed_data

    async def save_manifest(
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        manifest: dict,
    ):
        """Save snapshot manifest (metadata)."""
        key = f"{self._snapshot_key(tenant_id, workload, object_id, snapshot_id)}/manifest.json"
        await self.backend.write(key, json.dumps(manifest, indent=2, default=str).encode("utf-8"))

    async def load_manifest(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ) -> Optional[dict]:
        """Load snapshot manifest."""
        key = f"{self._snapshot_key(tenant_id, workload, object_id, snapshot_id)}/manifest.json"
        try:
            data = await self.backend.read(key)
            return json.loads(data)
        except FileNotFoundError:
            return None

    async def get_wrapped_dek(
        self, tenant_id: int, workload: str, object_id: str, snapshot_id: int
    ) -> Optional[str]:
        """Retrieve the wrapped DEK for a snapshot."""
        key = f"{self._snapshot_key(tenant_id, workload, object_id, snapshot_id)}/wrapped_dek.key"
        try:
            data = await self.backend.read(key)
            return data.decode("utf-8")
        except FileNotFoundError:
            return None

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        return self.backend.get_storage_stats()

    @staticmethod
    def can_delete_snapshot(snapshot, sla_policy=None) -> tuple[bool, str]:
        """Check if a snapshot can be deleted (WORM / legal hold enforcement).

        Returns (can_delete, reason).
        """
        from datetime import datetime

        # Check legal hold — never deletable
        if sla_policy and getattr(sla_policy, 'legal_hold', 0):
            return False, "Snapshot is under legal hold — deletion blocked"

        # Check WORM lock
        if hasattr(snapshot, 'locked_until') and snapshot.locked_until:
            if datetime.utcnow() < snapshot.locked_until:
                return False, f"WORM lock active until {snapshot.locked_until.isoformat()} — deletion blocked"

        return True, "OK"

    @staticmethod
    def apply_worm_lock(snapshot, retention_days: int):
        """Apply WORM lock to a snapshot based on retention period."""
        from datetime import datetime, timedelta
        snapshot.locked_until = snapshot.created_at + timedelta(days=retention_days)

    async def delete_snapshot_storage(
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        db: AsyncSession = None,
    ):
        """Delete all storage for a snapshot (for retention cleanup).

        IMPORTANT: Callers must check can_delete_snapshot() before calling this.
        This method does NOT enforce WORM — it trusts the caller.
        """
        if settings.DEDUP_ENABLED and db is not None:
            await self._cleanup_dedup_refs(
                db=db, tenant_id=tenant_id, snapshot_id=snapshot_id,
            )

        snapshot_key = self._snapshot_key(tenant_id, workload, object_id, snapshot_id)
        await self.backend.delete_prefix(snapshot_key)

    # ------------------------------------------------------------------ #
    #  Dedup helpers                                                       #
    # ------------------------------------------------------------------ #

    async def _check_dedup(
        self, db: AsyncSession, tenant_id: int, content_hash: str
    ) -> Optional[str]:
        from app.models.dedup import DedupEntry
        result = await db.execute(
            select(DedupEntry.blob_path).where(
                DedupEntry.tenant_id == tenant_id,
                DedupEntry.content_hash == content_hash,
            )
        )
        return result.scalar_one_or_none()

    async def _increment_ref_count(
        self, db: AsyncSession, tenant_id: int, content_hash: str
    ):
        from app.models.dedup import DedupEntry
        result = await db.execute(
            select(DedupEntry).where(
                DedupEntry.tenant_id == tenant_id,
                DedupEntry.content_hash == content_hash,
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.ref_count += 1

    async def _register_dedup(
        self, db: AsyncSession, tenant_id: int, content_hash: str,
        blob_path: str, size_bytes: int, original_size: int, is_chunk: bool = False,
    ):
        from app.models.dedup import DedupEntry
        entry = DedupEntry(
            tenant_id=tenant_id, content_hash=content_hash, blob_path=blob_path,
            size_bytes=size_bytes, original_size=original_size, ref_count=1, is_chunk=is_chunk,
        )
        db.add(entry)

    async def _cleanup_dedup_refs(
        self, db: AsyncSession, tenant_id: int, snapshot_id: int,
    ):
        from app.models.dedup import DedupEntry
        from app.models.snapshot import SnapshotItem

        result = await db.execute(
            select(SnapshotItem.content_hash).where(
                SnapshotItem.snapshot_id == snapshot_id,
                SnapshotItem.content_hash.isnot(None),
            )
        )
        hashes = [row[0] for row in result.all()]

        for content_hash in hashes:
            entry_result = await db.execute(
                select(DedupEntry).where(
                    DedupEntry.tenant_id == tenant_id,
                    DedupEntry.content_hash == content_hash,
                )
            )
            entry = entry_result.scalar_one_or_none()
            if not entry:
                continue

            entry.ref_count -= 1
            if entry.ref_count <= 0:
                if entry.is_chunk:
                    await self.chunk_store.delete_chunk(tenant_id, content_hash)
                else:
                    await self.backend.delete(entry.blob_path)
                await db.delete(entry)
                logger.debug(f"Dedup GC: removed {content_hash[:12]}... (ref_count=0)")


# Default singleton — uses local backend. Overwritten by main.py lifespan
# with the configured backend (azure, minio, etc.) before any requests.
from app.services.storage_backend import LocalStorageBackend

storage_service = StorageService(LocalStorageBackend(settings.BACKUP_STORAGE_PATH))
