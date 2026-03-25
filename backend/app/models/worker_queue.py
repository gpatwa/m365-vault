"""Worker queue — durable backing store for the Redis job queue.

Every message pushed to Redis is first persisted here.  On worker startup
any QUEUED or PROCESSING (interrupted) entries are replayed into Redis,
making Redis a transport rather than the source of truth.

Dead-letter: once retry_count reaches max_retries the entry transitions
to DEAD_LETTER and is never re-enqueued automatically.
"""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text

from app.database import Base


class WorkerQueueStatus(str, enum.Enum):
    QUEUED = "queued"            # Persisted and pushed to Redis
    PROCESSING = "processing"    # Picked up by a worker coroutine
    COMPLETED = "completed"      # Finished successfully
    DEAD_LETTER = "dead_letter"  # Exceeded max_retries; no further attempts


class WorkerQueueEntry(Base):
    __tablename__ = "worker_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Redis queue name this entry belongs to
    queue = Column(String(100), nullable=False, index=True)
    # Original message payload (without queue_entry_id injection)
    message_json = Column(Text, nullable=False)
    status = Column(
        Enum(WorkerQueueStatus),
        default=WorkerQueueStatus.QUEUED,
        nullable=False,
        index=True,
    )
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_attempted_at = Column(DateTime, nullable=True)
