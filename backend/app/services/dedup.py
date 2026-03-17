"""Deduplication service — SHA-256 content-addressable dedup with CDC chunking.

Features:
- Whole-blob dedup for items < CDC threshold (default 4 MB)
- Content-Defined Chunking (CDC) for large files using gear-hash rolling hash
- Per-tenant dedup index backed by SQLAlchemy/SQLite
- Reference counting for safe garbage collection
"""
import hashlib
import json
import logging
import os
import struct
from dataclasses import dataclass, field
from typing import Optional

import aiofiles

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChunkInfo:
    """Metadata for a single CDC chunk."""
    hash: str       # SHA-256 hex digest
    offset: int     # Byte offset in original data
    length: int     # Chunk size in bytes


@dataclass
class DedupResult:
    """Result of a dedup check."""
    content_hash: str           # SHA-256 of the (compressed) data
    is_duplicate: bool          # True if blob already exists in index
    existing_blob_path: Optional[str] = None  # Path to existing blob (if duplicate)
    is_chunked: bool = False    # True if CDC chunking was applied
    chunks: list[ChunkInfo] = field(default_factory=list)


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hex digest."""
    return hashlib.sha256(data).hexdigest()


class DedupService:
    """Content-addressable deduplication with CDC for large files."""

    # Gear hash table — random 256 values for rolling hash
    # Pre-computed for deterministic chunking across runs
    _GEAR_TABLE = None

    @classmethod
    def _init_gear_table(cls):
        """Initialize the gear hash lookup table (deterministic via seed)."""
        if cls._GEAR_TABLE is not None:
            return
        import random
        rng = random.Random(0xDED00)  # Fixed seed for determinism
        cls._GEAR_TABLE = [rng.getrandbits(64) for _ in range(256)]

    def __init__(self):
        self._init_gear_table()

    def compute_hash(self, data: bytes) -> str:
        """Compute SHA-256 content hash."""
        return sha256_hex(data)

    def needs_chunking(self, data: bytes) -> bool:
        """Check if data is large enough to benefit from CDC."""
        return (
            settings.DEDUP_ENABLED
            and len(data) >= settings.CDC_THRESHOLD_BYTES
        )

    def cdc_chunk(self, data: bytes) -> list[ChunkInfo]:
        """Split data into variable-size chunks using gear-hash CDC.

        Uses a rolling hash to find natural content boundaries.
        Target chunk size: 64 KB (configurable).
        Min chunk: 16 KB, Max chunk: 256 KB.
        """
        chunks = []
        offset = 0
        data_len = len(data)
        target = settings.CDC_TARGET_CHUNK_BYTES
        min_size = settings.CDC_MIN_CHUNK_BYTES
        max_size = settings.CDC_MAX_CHUNK_BYTES

        # Mask for boundary detection — tuned for target chunk size
        # For 64KB target: mask = (1 << 16) - 1 = 0xFFFF
        mask_bits = max(1, (target - 1).bit_length())
        mask = (1 << mask_bits) - 1

        while offset < data_len:
            remaining = data_len - offset

            # If remaining is smaller than min chunk, take it all
            if remaining <= min_size:
                chunk_data = data[offset:offset + remaining]
                chunks.append(ChunkInfo(
                    hash=sha256_hex(chunk_data),
                    offset=offset,
                    length=remaining,
                ))
                break

            # Scan for boundary starting after min_size
            fingerprint = 0
            boundary = min(offset + max_size, data_len)
            scan_start = offset + min_size

            for i in range(scan_start, boundary):
                fingerprint = ((fingerprint << 1) + self._GEAR_TABLE[data[i]]) & 0xFFFFFFFFFFFFFFFF
                if (fingerprint & mask) == 0:
                    boundary = i + 1
                    break

            chunk_len = boundary - offset
            chunk_data = data[offset:boundary]
            chunks.append(ChunkInfo(
                hash=sha256_hex(chunk_data),
                offset=offset,
                length=chunk_len,
            ))
            offset = boundary

        logger.debug(
            f"CDC: {data_len} bytes → {len(chunks)} chunks "
            f"(avg {data_len // max(len(chunks), 1)} bytes/chunk)"
        )
        return chunks


class ChunkStore:
    """Manages encrypted chunk storage on disk.

    Chunk directory layout:
      data/{tenant_id}/.chunks/{hash[:2]}/{hash[2:4]}/{hash}.chunk
    Two-level fan-out prevents too many files per directory.
    """

    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.BACKUP_STORAGE_PATH

    def _chunk_dir(self, tenant_id: int, chunk_hash: str) -> str:
        """Get the directory for a chunk based on its hash."""
        return os.path.join(
            self.base_path,
            str(tenant_id),
            ".chunks",
            chunk_hash[:2],
            chunk_hash[2:4],
        )

    def _chunk_path(self, tenant_id: int, chunk_hash: str) -> str:
        """Get the full path to a chunk file."""
        return os.path.join(
            self._chunk_dir(tenant_id, chunk_hash),
            f"{chunk_hash}.chunk",
        )

    def chunk_exists(self, tenant_id: int, chunk_hash: str) -> bool:
        """Check if a chunk already exists on disk."""
        return os.path.exists(self._chunk_path(tenant_id, chunk_hash))

    async def store_chunk(
        self, tenant_id: int, chunk_hash: str, encrypted_data: bytes
    ) -> str:
        """Write an encrypted chunk to disk. Returns the chunk path.

        Idempotent: if the chunk already exists, returns the existing path.
        """
        path = self._chunk_path(tenant_id, chunk_hash)
        if os.path.exists(path):
            return path

        chunk_dir = self._chunk_dir(tenant_id, chunk_hash)
        os.makedirs(chunk_dir, exist_ok=True)

        async with aiofiles.open(path, "wb") as f:
            await f.write(encrypted_data)

        return path

    async def retrieve_chunk(self, tenant_id: int, chunk_hash: str) -> bytes:
        """Read an encrypted chunk from disk."""
        path = self._chunk_path(tenant_id, chunk_hash)
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_chunk(self, tenant_id: int, chunk_hash: str) -> bool:
        """Delete a chunk from disk. Returns True if deleted."""
        path = self._chunk_path(tenant_id, chunk_hash)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


# Singletons
dedup_service = DedupService()
chunk_store = ChunkStore()
