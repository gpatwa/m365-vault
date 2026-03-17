"""Content-aware zstd compression service.

Implements adaptive compression with:
- Extension-based content detection to skip incompressible files
- MIME type detection for text/JSON optimization
- Magic byte detection for already-compressed data
- Safety valve: skips compression if output ≥ input size
"""
import logging
import os
import struct
from typing import Optional

import zstandard as zstd

from app.config import settings

logger = logging.getLogger(__name__)

# 4-byte magic header placed inside the encrypted envelope
# to signal that data has been processed by the compression/dedup pipeline.
MAGIC = b"M3VZ"  # M365 Vault Zstd
HEADER_SIZE = 5   # 4 bytes magic + 1 byte flags

# Flag bits
FLAG_COMPRESSED = 0x01
FLAG_CHUNKED = 0x02
FLAG_DEDUPED = 0x04

# File extensions known to be already compressed — do not compress these
INCOMPRESSIBLE_EXTENSIONS = frozenset({
    # Archives
    ".zip", ".gz", ".bz2", ".xz", ".zst", ".lz4", ".7z", ".rar", ".tar.gz", ".tgz",
    # Office Open XML (internally ZIP)
    ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".ico", ".svg",
    # Video
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv",
    # Audio
    ".mp3", ".aac", ".ogg", ".flac", ".wav", ".wma", ".m4a",
    # Other pre-compressed
    ".pdf", ".epub", ".woff", ".woff2",
})

# Magic bytes for common compressed formats (first 2-4 bytes)
COMPRESSED_MAGIC_BYTES = [
    b"PK",      # ZIP (and docx, xlsx, pptx, jar, etc.)
    b"\x1f\x8b",  # gzip
    b"BZ",      # bzip2
    b"\xfd7zXZ",  # xz
    b"\x28\xb5\x2f\xfd",  # zstd
    b"\x04\x22\x4d\x18",  # lz4
    b"\x89PNG",  # PNG
    b"\xff\xd8\xff",  # JPEG
]

# MIME types that are highly compressible
TEXT_MIME_PREFIXES = (
    "text/", "application/json", "application/xml", "application/javascript",
    "application/typescript", "application/x-yaml", "application/csv",
    "application/ld+json", "application/xhtml+xml",
)


class CompressionService:
    """Content-aware zstd compression with adaptive levels."""

    LEVEL_SKIP = 0  # Sentinel: do not compress

    def __init__(self):
        self._compressor_cache = {}
        self._decompressor = zstd.ZstdDecompressor()

    def _get_compressor(self, level: int) -> zstd.ZstdCompressor:
        """Get or create a cached compressor for a given level."""
        if level not in self._compressor_cache:
            self._compressor_cache[level] = zstd.ZstdCompressor(level=level)
        return self._compressor_cache[level]

    def choose_level(
        self,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        data: bytes = None,
    ) -> int:
        """Select optimal compression level based on content analysis.

        Returns:
            Compression level (1-22 for zstd) or LEVEL_SKIP (0) to skip.
        """
        if not settings.COMPRESSION_ENABLED:
            return self.LEVEL_SKIP

        # Skip tiny data (overhead not worth it)
        if data and len(data) < settings.COMPRESSION_MIN_SIZE:
            return self.LEVEL_SKIP

        # 1. Check file extension
        if filename:
            ext = os.path.splitext(filename.lower())[1]
            if ext in INCOMPRESSIBLE_EXTENSIONS:
                return self.LEVEL_SKIP

        # 2. Check MIME type
        if mime_type:
            mime_lower = mime_type.lower()
            if any(mime_lower.startswith(prefix) for prefix in TEXT_MIME_PREFIXES):
                return settings.COMPRESSION_ZSTD_LEVEL_TEXT

            # Image/video/audio MIME types are incompressible
            if mime_lower.startswith(("image/", "video/", "audio/")):
                return self.LEVEL_SKIP

        # 3. Check magic bytes for already-compressed data
        if data and len(data) >= 4:
            for magic in COMPRESSED_MAGIC_BYTES:
                if data[:len(magic)] == magic:
                    return self.LEVEL_SKIP

        # 4. Heuristic: if no filename/mime and data looks like JSON/text
        if data and not filename and not mime_type:
            # Quick check: does it start with common JSON/text bytes?
            if data[:1] in (b"{", b"[", b"<", b'"'):
                return settings.COMPRESSION_ZSTD_LEVEL_TEXT

        # Default: use binary compression level
        return settings.COMPRESSION_ZSTD_LEVEL_BINARY

    def compress(self, data: bytes, level: int) -> tuple[bytes, bool]:
        """Compress data with zstd at the given level.

        Args:
            data: Raw bytes to compress.
            level: Compression level (0 = skip).

        Returns:
            (output_bytes, was_compressed).
            If level == SKIP or compressed >= original, returns (data, False).
        """
        if level == self.LEVEL_SKIP:
            return data, False

        compressor = self._get_compressor(level)
        compressed = compressor.compress(data)

        # Safety valve: don't inflate data
        if len(compressed) >= len(data):
            logger.debug(
                f"Compression skipped: {len(data)}B → {len(compressed)}B "
                f"(no savings at level {level})"
            )
            return data, False

        ratio = (1 - len(compressed) / len(data)) * 100
        logger.debug(
            f"Compressed: {len(data)}B → {len(compressed)}B "
            f"({ratio:.1f}% reduction at level {level})"
        )
        return compressed, True

    def decompress(self, data: bytes) -> bytes:
        """Decompress zstd-compressed data."""
        return self._decompressor.decompress(data)

    def encode_header(self, was_compressed: bool, is_chunked: bool = False) -> bytes:
        """Create the M3VZ header to prepend inside the encrypted envelope.

        Returns 5 bytes: MAGIC (4) + flags (1).
        """
        flags = 0
        if was_compressed:
            flags |= FLAG_COMPRESSED
        if is_chunked:
            flags |= FLAG_CHUNKED
        return MAGIC + struct.pack("B", flags)

    def decode_header(self, data: bytes) -> tuple[bool, int, bool, bool]:
        """Check if data has the M3VZ header.

        Returns (has_header, payload_offset, is_compressed, is_chunked).
        """
        if len(data) >= HEADER_SIZE and data[:4] == MAGIC:
            flags = data[4]
            return (
                True,
                HEADER_SIZE,
                bool(flags & FLAG_COMPRESSED),
                bool(flags & FLAG_CHUNKED),
            )
        # Legacy blob — no header
        return False, 0, False, False


compression_service = CompressionService()
