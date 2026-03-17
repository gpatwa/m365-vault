"""Deduplication index model — content-addressable blob registry.

Tracks unique blobs by SHA-256 hash per tenant. Reference counting
enables safe garbage collection when snapshots are deleted.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, UniqueConstraint, Boolean
from app.database import Base


class DedupEntry(Base):
    """Content-addressable dedup index entry.

    Maps (tenant_id, content_hash) → blob_path on disk.
    ref_count tracks how many SnapshotItems reference this blob.
    """
    __tablename__ = "dedup_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hex digest
    blob_path = Column(String(1000), nullable=False)
    size_bytes = Column(Integer, default=0)             # Compressed + encrypted size on disk
    original_size = Column(Integer, default=0)          # Original uncompressed size
    ref_count = Column(Integer, default=1)              # Number of SnapshotItems referencing this blob
    is_chunk = Column(Boolean, default=False)           # True if this is a CDC chunk (not a full blob)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "content_hash", name="uq_tenant_content_hash"),
    )
