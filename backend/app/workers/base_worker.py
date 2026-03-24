"""Base worker framework for all workload backup/restore operations.

Provides common platform features that all workload workers inherit:
- Parallel item processing with configurable concurrency
- Graph API batch fetching
- Unified error handling and failed item recording
- Storage pipeline (serialize → compress → encrypt → store)
- Delta token management
- Progress tracking and checkpointing

Workload-specific workers only need to implement 4 abstract methods:
- workload_name() → str
- discover_items() → list of items to backup
- fetch_item_data() → raw bytes for each item
- get_item_metadata() → searchable metadata per item
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.utils.retry import record_failed_item

logger = logging.getLogger(__name__)


class BackupItem:
    """Standardized item representation for the backup pipeline.

    All workload workers discover items and convert them to BackupItem
    instances. The BaseWorker framework handles the rest.
    """
    __slots__ = ('id', 'item_type', 'name', 'path', 'raw_data', 'binary_data',
                 'mime_type', 'metadata', 'extra_fields')

    def __init__(
        self,
        id: str,
        item_type: ItemType,
        name: str,
        path: str = "",
        raw_data: dict = None,
        binary_data: bytes = None,
        mime_type: str = "application/json",
        metadata: dict = None,
        extra_fields: dict = None,
    ):
        self.id = id
        self.item_type = item_type
        self.name = name
        self.path = path
        self.raw_data = raw_data        # JSON-serializable dict (for metadata items)
        self.binary_data = binary_data  # Raw bytes (for files, attachments)
        self.mime_type = mime_type
        self.metadata = metadata or {}
        self.extra_fields = extra_fields or {}  # Workload-specific SnapshotItem fields


class BaseWorker(ABC):
    """Abstract base class for all workload backup workers.

    Subclasses implement workload-specific logic (Graph API calls,
    item discovery). The base class handles everything else:
    parallelism, error handling, storage, encryption, progress.
    """

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

    # ═══════════════════════════════════════════════════════
    # Abstract methods — workload-specific
    # ═══════════════════════════════════════════════════════

    @abstractmethod
    def workload_name(self) -> str:
        """Return workload identifier: 'exchange', 'onedrive', etc."""
        ...

    @abstractmethod
    async def discover_items(
        self,
        protected_object: ProtectedObject,
        delta_token: str = None,
    ) -> tuple[list[BackupItem], Optional[str]]:
        """Discover items to backup from the source API.

        Returns:
            tuple: (list of BackupItem, new_delta_token or None)

        The delta_token enables incremental backups:
        - First run: delta_token is None, return all items + new token
        - Subsequent runs: use delta_token to get only changed items
        """
        ...

    # ═══════════════════════════════════════════════════════
    # Optional overrides
    # ═══════════════════════════════════════════════════════

    async def pre_backup(self, protected_object: ProtectedObject, snapshot: Snapshot):
        """Hook called before backup starts. Override for setup logic."""
        pass

    async def post_backup(self, protected_object: ProtectedObject, snapshot: Snapshot,
                          item_count: int, total_size: int):
        """Hook called after backup completes. Override for cleanup logic."""
        pass

    # ═══════════════════════════════════════════════════════
    # Common backup framework
    # ═══════════════════════════════════════════════════════

    async def backup(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
        concurrency: int = None,
    ) -> tuple[int, int, str]:
        """Run backup with parallel item processing.

        This is the main entry point called by BackupEngine.
        Returns: (item_count, total_size_bytes, new_delta_token)
        """
        concurrency = concurrency or settings.ITEM_CONCURRENCY

        await self.pre_backup(protected_object, snapshot)

        # Step 1: Discover items (workload-specific)
        try:
            items, new_delta_token = await self.discover_items(protected_object, delta_token)
        except Exception as e:
            logger.error(f"[{self.workload_name()}] Discovery failed for {protected_object.display_name}: {e}")
            return 0, 0, None

        if not items:
            logger.info(f"[{self.workload_name()}] No items found for {protected_object.display_name}")
            return 0, 0, new_delta_token

        logger.info(
            f"[{self.workload_name()}] Discovered {len(items)} items for "
            f"{protected_object.display_name}, processing with concurrency={concurrency}"
        )

        # Step 2: Process items in parallel (common framework)
        semaphore = asyncio.Semaphore(concurrency)
        counters = {"count": 0, "size": 0, "failed": 0}

        async def process_item(item: BackupItem):
            async with semaphore:
                await self._process_single_item(
                    item, protected_object, snapshot, wrapped_dek, counters
                )

        await asyncio.gather(*[process_item(item) for item in items])
        await self.db.flush()

        item_count = counters["count"]
        total_size = counters["size"]

        await self.post_backup(protected_object, snapshot, item_count, total_size)

        logger.info(
            f"[{self.workload_name()}] Backup complete: {item_count} items, "
            f"{total_size} bytes, {counters['failed']} failed"
        )

        return item_count, total_size, new_delta_token

    async def _process_single_item(
        self,
        item: BackupItem,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        counters: dict,
    ):
        """Process a single item through the storage pipeline."""
        try:
            # Serialize to bytes
            if item.binary_data is not None:
                data = item.binary_data
            elif item.raw_data is not None:
                data = json.dumps(item.raw_data, default=str).encode("utf-8")
            else:
                logger.warning(f"[{self.workload_name()}] Item {item.id} has no data, skipping")
                return

            # Store through compression/dedup/encryption pipeline
            result = await self.storage.store_item(
                tenant_id=protected_object.tenant_id,
                workload=self.workload_name(),
                object_id=protected_object.ms_object_id,
                snapshot_id=snapshot.id,
                item_id=item.id,
                data=data,
                wrapped_dek=wrapped_dek,
                mime_type=item.mime_type,
                filename=item.extra_fields.get("file_name"),
                db=self.db,
            )

            # Create catalog entry
            snapshot_item = SnapshotItem(
                snapshot_id=snapshot.id,
                item_type=item.item_type,
                ms_item_id=item.id,
                name=item.name[:1000] if item.name else "Unknown",
                path=item.path[:2000] if item.path else "",
                size_bytes=len(data),
                compressed_size=result.compressed_size,
                content_hash=result.content_hash,
                storage_flags=result.storage_flags,
                blob_path=result.blob_path,
                metadata_json=json.dumps(item.metadata) if item.metadata else None,
                # Workload-specific fields
                subject=item.extra_fields.get("subject"),
                sender=item.extra_fields.get("sender"),
                recipients=item.extra_fields.get("recipients"),
                received_at=item.extra_fields.get("received_at"),
                file_name=item.extra_fields.get("file_name"),
                mime_type=item.extra_fields.get("content_mime_type") or item.mime_type,
                last_modified_at=item.extra_fields.get("last_modified_at"),
            )
            self.db.add(snapshot_item)

            counters["count"] += 1
            counters["size"] += len(data)

        except Exception as e:
            counters["failed"] += 1
            logger.error(f"[{self.workload_name()}] Failed to backup item {item.id}: {e}")
            try:
                await record_failed_item(
                    db=self.db,
                    snapshot_id=snapshot.id,
                    protected_object_id=protected_object.id,
                    error=e,
                    ms_item_id=item.id,
                    item_type_str=item.item_type.value if hasattr(item.item_type, 'value') else str(item.item_type),
                    item_name=item.name[:500] if item.name else "Unknown",
                    item_path=item.path[:500] if item.path else "",
                )
            except Exception as record_err:
                logger.error(f"[{self.workload_name()}] Failed to record error for {item.id}: {record_err}")

    # ═══════════════════════════════════════════════════════
    # Helper: Graph API batch fetching
    # ═══════════════════════════════════════════════════════

    async def batch_fetch(self, urls: list[str]) -> list[dict]:
        """Fetch multiple Graph API URLs in batches.

        Uses the Graph $batch endpoint (up to 20 requests per batch)
        for efficient bulk data retrieval.
        """
        batch_size = settings.GRAPH_BATCH_SIZE
        results = []

        for i in range(0, len(urls), batch_size):
            batch = [{"method": "GET", "url": url} for url in urls[i:i + batch_size]]
            try:
                batch_results = await self.graph.batch_request(batch)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"[{self.workload_name()}] Batch fetch failed: {e}")
                # Fallback: fetch individually
                for url in urls[i:i + batch_size]:
                    try:
                        result = await self.graph.get(url)
                        results.append(result)
                    except Exception:
                        results.append(None)

        return results

    # ═══════════════════════════════════════════════════════
    # Helper: Delta token management
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def parse_delta_tokens(delta_token: str) -> dict:
        """Parse a JSON delta token string into a dict."""
        if not delta_token:
            return {}
        try:
            return json.loads(delta_token)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def serialize_delta_tokens(tokens: dict) -> Optional[str]:
        """Serialize delta tokens dict to JSON string."""
        return json.dumps(tokens) if tokens else None
