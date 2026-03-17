"""Local filesystem storage service with compression + dedup pipeline.

Pipeline (store):
  Raw data -> Compress -> M3VZ Header -> Hash -> Dedup check -> CDC (if large)
  -> Encrypt -> Write -> Register dedup

Pipeline (retrieve):
  Read -> Decrypt -> Check M3VZ header -> Dechunk (if chunked) -> Decompress -> Return

Directory structure:
  data/{tenant_id}/{workload}/{object_id}/{snapshot_id}/
    manifest.json     - Snapshot metadata
    wrapped_dek.key   - Encrypted DEK for this snapshot
    items/
      {item_id}.blob  - Encrypted item data

  data/{tenant_id}/.chunks/{hash[:2]}/{hash[2:4]}/{hash}.chunk  - CDC chunks

Backward compatibility:
  Legacy blobs (no M3VZ header after decryption) are returned as-is.
"""
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.compression import compression_service, FLAG_COMPRESSED, FLAG_CHUNKED
from app.services.dedup import dedup_service, chunk_store, sha256_hex, ChunkInfo
from app.services.encryption import encryption_service

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


class StorageService:
    """Manages encrypted backup blob storage with compression and dedup."""

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
          7. WRITE     - write to disk
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
                # Increment reference count
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
            blob_path = await self._store_chunked(
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
            items_dir = self._items_path(tenant_id, workload, object_id, snapshot_id)
            os.makedirs(items_dir, exist_ok=True)
            blob_filename = f"{item_id}.blob"
            blob_path = os.path.join(items_dir, blob_filename)
            async with aiofiles.open(blob_path, "wb") as f:
                await f.write(encrypted_data)

        # --- 8. REGISTER DEDUP ---
        if settings.DEDUP_ENABLED and db is not None and not is_duplicate:
            await self._register_dedup(
                db=db,
                tenant_id=tenant_id,
                content_hash=content_hash,
                blob_path=blob_path,
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
            blob_path=blob_path,
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
        """Store a large item as CDC chunks + manifest.

        Each chunk is individually encrypted and stored in the chunk store.
        The item's .blob file contains an encrypted manifest listing all chunks.
        """
        # CDC on the compressed data (not the header+compressed, since we need
        # to reconstruct header + reassembled chunks on retrieval)
        chunks = dedup_service.cdc_chunk(compressed_data)

        chunk_entries = []
        for chunk_info in chunks:
            chunk_data = compressed_data[chunk_info.offset:chunk_info.offset + chunk_info.length]

            # Check if this chunk already exists (chunk-level dedup)
            if chunk_store.chunk_exists(tenant_id, chunk_info.hash):
                # Increment ref count if tracking
                if db is not None:
                    await self._increment_ref_count(db, tenant_id, chunk_info.hash)
            else:
                # Encrypt and store the chunk
                encrypted_chunk = encryption_service.encrypt_data(chunk_data, dek)
                await chunk_store.store_chunk(tenant_id, chunk_info.hash, encrypted_chunk)

                # Register chunk in dedup index
                if db is not None:
                    chunk_path = chunk_store._chunk_path(tenant_id, chunk_info.hash)
                    await self._register_dedup(
                        db=db,
                        tenant_id=tenant_id,
                        content_hash=chunk_info.hash,
                        blob_path=chunk_path,
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

        # The blob file stores the M3VZ header + encrypted manifest
        header = compression_service.encode_header(
            was_compressed=True,  # The chunks contain compressed data
            is_chunked=True,
        )
        header_and_manifest = header + manifest_bytes
        encrypted_manifest = encryption_service.encrypt_data(header_and_manifest, dek)

        items_dir = self._items_path(tenant_id, workload, object_id, snapshot_id)
        os.makedirs(items_dir, exist_ok=True)
        blob_path = os.path.join(items_dir, f"{item_id}.blob")
        async with aiofiles.open(blob_path, "wb") as f:
            await f.write(encrypted_manifest)

        logger.debug(
            f"Chunked store: {item_id} → {len(chunks)} chunks, "
            f"manifest at {blob_path}"
        )
        return blob_path

    async def retrieve_item(
        self,
        blob_path: str,
        wrapped_dek: str,
        tenant_id: int = None,
    ) -> bytes:
        """Retrieve, decrypt, and decompress a backup item.

        Pipeline:
          1. READ + DECRYPT
          2. CHECK M3VZ HEADER
          3. DECHUNK (if chunked flag set)
          4. DECOMPRESS (if compressed flag set)
          5. RETURN original data

        Backward compatibility: legacy blobs (no M3VZ header) are returned as-is.
        """
        async with aiofiles.open(blob_path, "rb") as f:
            encrypted_data = await f.read()

        dek = encryption_service.decrypt_dek(wrapped_dek)
        decrypted = encryption_service.decrypt_data(encrypted_data, dek)

        # Check for M3VZ header
        has_header, offset, is_compressed, is_chunked = compression_service.decode_header(decrypted)

        if not has_header:
            # Legacy blob — return as-is
            return decrypted

        if is_chunked:
            # Decrypted payload after header is the chunk manifest
            manifest_bytes = decrypted[offset:]
            manifest = json.loads(manifest_bytes)

            # Reassemble from chunks
            reassembled = bytearray()
            for chunk_entry in manifest["chunks"]:
                chunk_hash = chunk_entry["hash"]
                if tenant_id is None:
                    raise ValueError(
                        "tenant_id required to retrieve chunked items"
                    )
                encrypted_chunk = await chunk_store.retrieve_chunk(tenant_id, chunk_hash)
                chunk_data = encryption_service.decrypt_data(encrypted_chunk, dek)
                reassembled.extend(chunk_data)

            compressed_data = bytes(reassembled)
        else:
            compressed_data = decrypted[offset:]

        # Decompress if needed
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
        self,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
        db: AsyncSession = None,
    ):
        """Delete all storage for a snapshot (for retention cleanup).

        If db is provided and dedup is enabled, decrements ref counts
        and only deletes blobs when ref_count reaches 0.
        """
        import shutil

        if settings.DEDUP_ENABLED and db is not None:
            await self._cleanup_dedup_refs(
                db=db,
                tenant_id=tenant_id,
                workload=workload,
                object_id=object_id,
                snapshot_id=snapshot_id,
            )

        snapshot_dir = self._snapshot_path(tenant_id, workload, object_id, snapshot_id)
        if os.path.exists(snapshot_dir):
            shutil.rmtree(snapshot_dir)

    # ------------------------------------------------------------------ #
    #  Dedup helpers                                                       #
    # ------------------------------------------------------------------ #

    async def _check_dedup(
        self, db: AsyncSession, tenant_id: int, content_hash: str
    ) -> Optional[str]:
        """Check if a blob with this content hash already exists for the tenant."""
        from app.models.dedup import DedupEntry

        result = await db.execute(
            select(DedupEntry.blob_path).where(
                DedupEntry.tenant_id == tenant_id,
                DedupEntry.content_hash == content_hash,
            )
        )
        row = result.scalar_one_or_none()
        return row  # blob_path or None

    async def _increment_ref_count(
        self, db: AsyncSession, tenant_id: int, content_hash: str
    ):
        """Increment the reference count for a dedup entry."""
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
        self,
        db: AsyncSession,
        tenant_id: int,
        content_hash: str,
        blob_path: str,
        size_bytes: int,
        original_size: int,
        is_chunk: bool = False,
    ):
        """Register a new blob in the dedup index."""
        from app.models.dedup import DedupEntry

        entry = DedupEntry(
            tenant_id=tenant_id,
            content_hash=content_hash,
            blob_path=blob_path,
            size_bytes=size_bytes,
            original_size=original_size,
            ref_count=1,
            is_chunk=is_chunk,
        )
        db.add(entry)

    async def _cleanup_dedup_refs(
        self,
        db: AsyncSession,
        tenant_id: int,
        workload: str,
        object_id: str,
        snapshot_id: int,
    ):
        """Decrement dedup ref counts for all items in a snapshot.

        Deletes blobs from disk when ref_count reaches 0.
        """
        from app.models.dedup import DedupEntry
        from app.models.snapshot import SnapshotItem

        # Get all content hashes for items in this snapshot
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
                # Delete the blob from disk
                if entry.is_chunk:
                    await chunk_store.delete_chunk(tenant_id, content_hash)
                elif os.path.exists(entry.blob_path):
                    try:
                        os.remove(entry.blob_path)
                    except OSError:
                        logger.warning(f"Could not delete blob: {entry.blob_path}")

                await db.delete(entry)

                logger.debug(f"Dedup GC: removed {content_hash[:12]}... (ref_count=0)")


storage_service = StorageService()
