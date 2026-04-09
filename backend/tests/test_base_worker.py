"""Tests for BaseWorker framework — parallel processing, error handling, storage pipeline."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from app.workers.base_worker import BaseWorker, BackupItem
from app.models.snapshot import ItemType


# ── Test Worker Implementation ──

class MockWorker(BaseWorker):
    """Minimal worker implementation for testing the framework."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pre_backup_called = False
        self.post_backup_called = False
        self.post_backup_args = None

    def workload_name(self) -> str:
        return "mock"

    async def discover_items(self, protected_object, delta_token=None):
        items = [
            BackupItem(
                id=f"item_{i}",
                item_type=ItemType.FILE,
                name=f"Test Item {i}",
                path="test/path",
                raw_data={"content": f"data_{i}", "index": i},
                metadata={"source": "test"},
            )
            for i in range(5)
        ]
        return items, "new_delta_token_123"

    async def pre_backup(self, protected_object, snapshot):
        self.pre_backup_called = True

    async def post_backup(self, protected_object, snapshot, item_count, total_size):
        self.post_backup_called = True
        self.post_backup_args = (item_count, total_size)


class FailingWorker(BaseWorker):
    """Worker that has some items fail during backup."""

    def workload_name(self) -> str:
        return "failing"

    async def discover_items(self, protected_object, delta_token=None):
        items = [
            BackupItem(id="good_1", item_type=ItemType.FILE, name="Good Item", path="test",
                       raw_data={"ok": True}),
            BackupItem(id="bad_1", item_type=ItemType.FILE, name="Bad Item", path="test",
                       raw_data=None, binary_data=None),  # No data — will fail
            BackupItem(id="good_2", item_type=ItemType.FILE, name="Good Item 2", path="test",
                       raw_data={"ok": True}),
        ]
        return items, None


class EmptyWorker(BaseWorker):
    """Worker that discovers no items."""

    def workload_name(self) -> str:
        return "empty"

    async def discover_items(self, protected_object, delta_token=None):
        return [], "empty_delta"


class DiscoveryFailWorker(BaseWorker):
    """Worker where discover_items raises an exception."""

    def workload_name(self) -> str:
        return "disc_fail"

    async def discover_items(self, protected_object, delta_token=None):
        raise ConnectionError("Graph API unreachable")


# ── Fixtures ──

@dataclass
class MockStorageResult:
    compressed_size: int = 100
    content_hash: str = "abc123"
    storage_flags: int = 1
    blob_path: str = "mock/path/item.blob"


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    # begin_nested() must return an async context manager for savepoint-per-item
    nested_ctx = AsyncMock()
    nested_ctx.__aenter__ = AsyncMock(return_value=None)
    nested_ctx.__aexit__ = AsyncMock(return_value=False)
    db.begin_nested = MagicMock(return_value=nested_ctx)
    return db


@pytest.fixture
def mock_graph():
    return AsyncMock()


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.store_item = AsyncMock(return_value=MockStorageResult())
    return storage


@pytest.fixture
def mock_encryption():
    return AsyncMock()


@pytest.fixture
def mock_protected_object():
    obj = MagicMock()
    obj.id = 1
    obj.tenant_id = 1
    obj.ms_object_id = "test-object-id"
    obj.display_name = "Test Object"
    obj.workload_type = MagicMock(value="mock")
    return obj


@pytest.fixture
def mock_snapshot():
    snap = MagicMock()
    snap.id = 100
    return snap


# ── Tests ──

class TestBackupItem:
    """Tests for the BackupItem data class."""

    def test_create_with_raw_data(self):
        item = BackupItem(
            id="test-1", item_type=ItemType.EMAIL,
            name="Test Email", raw_data={"subject": "Hello"}
        )
        assert item.id == "test-1"
        assert item.item_type == ItemType.EMAIL
        assert item.raw_data == {"subject": "Hello"}
        assert item.binary_data is None
        assert item.mime_type == "application/json"

    def test_create_with_binary_data(self):
        item = BackupItem(
            id="file-1", item_type=ItemType.FILE,
            name="doc.pdf", binary_data=b"PDF content",
            mime_type="application/pdf"
        )
        assert item.binary_data == b"PDF content"
        assert item.mime_type == "application/pdf"

    def test_create_with_extra_fields(self):
        item = BackupItem(
            id="email-1", item_type=ItemType.EMAIL,
            name="Subject", extra_fields={"subject": "Hi", "sender": "a@b.com"}
        )
        assert item.extra_fields["subject"] == "Hi"
        assert item.extra_fields["sender"] == "a@b.com"

    def test_defaults(self):
        item = BackupItem(id="x", item_type=ItemType.FILE, name="test")
        assert item.path == ""
        assert item.metadata == {}
        assert item.extra_fields == {}


class TestBaseWorkerBackup:
    """Tests for BaseWorker.backup() parallel processing."""

    @pytest.mark.asyncio
    async def test_successful_backup(self, mock_db, mock_graph, mock_storage,
                                      mock_encryption, mock_protected_object, mock_snapshot):
        worker = MockWorker(mock_db, mock_graph, mock_storage, mock_encryption)

        item_count, total_size, delta_token = await worker.backup(
            mock_protected_object, mock_snapshot, "wrapped_dek_123", concurrency=5
        )

        assert item_count == 5
        assert total_size > 0
        assert delta_token == "new_delta_token_123"
        assert mock_storage.store_item.call_count == 5
        assert mock_db.add.call_count == 5
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_pre_post_hooks_called(self, mock_db, mock_graph, mock_storage,
                                          mock_encryption, mock_protected_object, mock_snapshot):
        worker = MockWorker(mock_db, mock_graph, mock_storage, mock_encryption)

        await worker.backup(mock_protected_object, mock_snapshot, "dek")

        assert worker.pre_backup_called
        assert worker.post_backup_called
        assert worker.post_backup_args[0] == 5  # item_count
        assert worker.post_backup_args[1] > 0   # total_size

    @pytest.mark.asyncio
    async def test_empty_discovery(self, mock_db, mock_graph, mock_storage,
                                    mock_encryption, mock_protected_object, mock_snapshot):
        worker = EmptyWorker(mock_db, mock_graph, mock_storage, mock_encryption)

        item_count, total_size, delta_token = await worker.backup(
            mock_protected_object, mock_snapshot, "dek"
        )

        assert item_count == 0
        assert total_size == 0
        assert delta_token == "empty_delta"
        assert mock_storage.store_item.call_count == 0

    @pytest.mark.asyncio
    async def test_discovery_failure(self, mock_db, mock_graph, mock_storage,
                                      mock_encryption, mock_protected_object, mock_snapshot):
        worker = DiscoveryFailWorker(mock_db, mock_graph, mock_storage, mock_encryption)

        item_count, total_size, delta_token = await worker.backup(
            mock_protected_object, mock_snapshot, "dek"
        )

        assert item_count == 0
        assert total_size == 0
        assert delta_token is None

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self, mock_db, mock_graph, mock_storage,
                                              mock_encryption, mock_protected_object, mock_snapshot):
        """Items that fail don't stop the whole backup."""
        worker = FailingWorker(mock_db, mock_graph, mock_storage, mock_encryption)

        item_count, total_size, delta_token = await worker.backup(
            mock_protected_object, mock_snapshot, "dek"
        )

        # 2 good items succeed, 1 bad item fails (no data)
        assert item_count == 2
        assert mock_storage.store_item.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrency_respected(self, mock_db, mock_graph, mock_storage,
                                          mock_encryption, mock_protected_object, mock_snapshot):
        """Verify that concurrency semaphore limits parallel execution."""
        max_concurrent = 0
        current_concurrent = 0

        original_store = mock_storage.store_item

        async def tracking_store(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)  # Simulate work
            current_concurrent -= 1
            return MockStorageResult()

        mock_storage.store_item = tracking_store

        worker = MockWorker(mock_db, mock_graph, mock_storage, mock_encryption)
        await worker.backup(mock_protected_object, mock_snapshot, "dek", concurrency=2)

        assert max_concurrent <= 2  # Never exceeded concurrency limit

    @pytest.mark.asyncio
    async def test_workload_name(self, mock_db, mock_graph, mock_storage, mock_encryption):
        worker = MockWorker(mock_db, mock_graph, mock_storage, mock_encryption)
        assert worker.workload_name() == "mock"

    @pytest.mark.asyncio
    async def test_storage_called_with_correct_params(self, mock_db, mock_graph, mock_storage,
                                                       mock_encryption, mock_protected_object, mock_snapshot):
        worker = MockWorker(mock_db, mock_graph, mock_storage, mock_encryption)
        await worker.backup(mock_protected_object, mock_snapshot, "wrapped_dek_xyz", concurrency=1)

        call_args = mock_storage.store_item.call_args_list[0]
        kwargs = call_args.kwargs
        assert kwargs["tenant_id"] == 1
        assert kwargs["workload"] == "mock"
        assert kwargs["object_id"] == "test-object-id"
        assert kwargs["snapshot_id"] == 100
        assert kwargs["wrapped_dek"] == "wrapped_dek_xyz"


class TestBaseWorkerDeltaTokens:
    """Tests for delta token parsing/serialization."""

    def test_parse_valid_tokens(self):
        tokens = BaseWorker.parse_delta_tokens('{"users": "token1", "groups": "token2"}')
        assert tokens == {"users": "token1", "groups": "token2"}

    def test_parse_none(self):
        assert BaseWorker.parse_delta_tokens(None) == {}

    def test_parse_empty_string(self):
        assert BaseWorker.parse_delta_tokens("") == {}

    def test_parse_invalid_json(self):
        assert BaseWorker.parse_delta_tokens("not json") == {}

    def test_serialize_tokens(self):
        result = BaseWorker.serialize_delta_tokens({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_serialize_empty(self):
        assert BaseWorker.serialize_delta_tokens({}) is None

    def test_serialize_none(self):
        assert BaseWorker.serialize_delta_tokens(None) is None
