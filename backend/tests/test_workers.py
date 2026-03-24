"""Tests for all workload workers — verify BaseWorker inheritance and interface compliance."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.workers.base_worker import BaseWorker, BackupItem
from app.workers.exchange_worker import ExchangeWorker
from app.workers.onedrive_worker import OneDriveWorker
from app.workers.sharepoint_worker import SharePointWorker
from app.workers.teams_worker import TeamsWorker
from app.workers.entra_id_worker import EntraIDWorker
from app.models.snapshot import ItemType


# ── Fixtures ──

@pytest.fixture
def mock_deps():
    """Create mock dependencies for all workers."""
    from dataclasses import dataclass

    @dataclass
    class MockStorageResult:
        compressed_size: int = 100
        content_hash: str = "abc123"
        storage_flags: int = 1
        blob_path: str = "mock/path.blob"

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    graph = AsyncMock()
    graph.get_all_pages = AsyncMock(return_value=[])
    graph.get_delta = AsyncMock(return_value=([], None))
    graph.get = AsyncMock(return_value={})
    graph.get_binary = AsyncMock(return_value=b"file content")
    graph.batch_request = AsyncMock(return_value=[])
    graph.BATCH_SIZE = 20

    storage = AsyncMock()
    storage.store_item = AsyncMock(return_value=MockStorageResult())
    storage.retrieve_item = AsyncMock(return_value=b'{"test": true}')

    encryption = AsyncMock()

    return db, graph, storage, encryption


# ═══════════════════════════════════════════════════════
# Test: All workers extend BaseWorker
# ═══════════════════════════════════════════════════════

class TestWorkerInheritance:
    """Verify all workers properly extend BaseWorker."""

    def test_exchange_extends_baseworker(self, mock_deps):
        worker = ExchangeWorker(*mock_deps)
        assert isinstance(worker, BaseWorker)

    def test_onedrive_extends_baseworker(self, mock_deps):
        worker = OneDriveWorker(*mock_deps)
        assert isinstance(worker, BaseWorker)

    def test_sharepoint_extends_baseworker(self, mock_deps):
        worker = SharePointWorker(*mock_deps)
        assert isinstance(worker, BaseWorker)

    def test_teams_extends_baseworker(self, mock_deps):
        worker = TeamsWorker(*mock_deps)
        assert isinstance(worker, BaseWorker)

    def test_entra_id_extends_baseworker(self, mock_deps):
        worker = EntraIDWorker(*mock_deps)
        assert isinstance(worker, BaseWorker)


# ═══════════════════════════════════════════════════════
# Test: workload_name() returns correct identifier
# ═══════════════════════════════════════════════════════

class TestWorkloadNames:
    """Verify workload_name() returns correct identifiers."""

    def test_exchange_name(self, mock_deps):
        assert ExchangeWorker(*mock_deps).workload_name() == "exchange"

    def test_onedrive_name(self, mock_deps):
        assert OneDriveWorker(*mock_deps).workload_name() == "onedrive"

    def test_sharepoint_name(self, mock_deps):
        assert SharePointWorker(*mock_deps).workload_name() == "sharepoint"

    def test_teams_name(self, mock_deps):
        assert TeamsWorker(*mock_deps).workload_name() == "teams"

    def test_entra_id_name(self, mock_deps):
        assert EntraIDWorker(*mock_deps).workload_name() == "entra_id"

    def test_all_names_unique(self, mock_deps):
        workers = [
            ExchangeWorker(*mock_deps),
            OneDriveWorker(*mock_deps),
            SharePointWorker(*mock_deps),
            TeamsWorker(*mock_deps),
            EntraIDWorker(*mock_deps),
        ]
        names = [w.workload_name() for w in workers]
        assert len(names) == len(set(names)), f"Duplicate workload names: {names}"


# ═══════════════════════════════════════════════════════
# Test: discover_items() interface compliance
# ═══════════════════════════════════════════════════════

class TestDiscoverItems:
    """Verify discover_items() returns correct types."""

    @pytest.mark.asyncio
    async def test_exchange_discover_returns_tuple(self, mock_deps):
        db, graph, storage, enc = mock_deps
        # Mock folder and message responses
        graph.get_all_pages = AsyncMock(return_value=[
            {"id": "inbox", "displayName": "Inbox"},
        ])
        graph.get_delta = AsyncMock(return_value=([
            {"id": "msg1", "subject": "Test", "from": {"emailAddress": {"address": "a@b.com"}},
             "toRecipients": [], "receivedDateTime": "2024-01-01T00:00:00Z",
             "importance": "normal", "isRead": True, "hasAttachments": False}
        ], "delta_token_1"))

        worker = ExchangeWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user123")
        items, delta = await worker.discover_items(obj)

        assert isinstance(items, list)
        assert len(items) >= 1
        assert all(isinstance(i, BackupItem) for i in items)
        assert items[0].item_type == ItemType.EMAIL
        assert items[0].name == "Test"

    @pytest.mark.asyncio
    async def test_onedrive_discover_returns_tuple(self, mock_deps):
        db, graph, storage, enc = mock_deps
        graph.get_delta = AsyncMock(return_value=([
            {"id": "file1", "name": "doc.pdf", "file": {"mimeType": "application/pdf"},
             "parentReference": {"path": "/drive/root:"}, "lastModifiedDateTime": "2024-01-01T00:00:00Z"},
            {"id": "folder1", "name": "Photos", "folder": {"childCount": 5},
             "parentReference": {"path": "/drive/root:"}},
        ], "delta_od"))

        worker = OneDriveWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user123")
        items, delta = await worker.discover_items(obj)

        assert isinstance(items, list)
        assert len(items) == 2
        file_items = [i for i in items if i.item_type == ItemType.FILE]
        folder_items = [i for i in items if i.item_type == ItemType.FOLDER]
        assert len(file_items) == 1
        assert len(folder_items) == 1
        assert file_items[0].name == "doc.pdf"
        assert delta == "delta_od"

    @pytest.mark.asyncio
    async def test_exchange_discover_empty_on_error(self, mock_deps):
        db, graph, storage, enc = mock_deps
        graph.get_all_pages = AsyncMock(side_effect=ConnectionError("API down"))

        worker = ExchangeWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user123")
        items, delta = await worker.discover_items(obj)

        # Should not crash — returns empty with fallback folders
        assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_onedrive_discover_empty_on_error(self, mock_deps):
        db, graph, storage, enc = mock_deps
        graph.get_delta = AsyncMock(side_effect=ConnectionError("API down"))

        worker = OneDriveWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user123")
        items, delta = await worker.discover_items(obj)

        assert items == []
        assert delta is None


# ═══════════════════════════════════════════════════════
# Test: Exchange-specific backup via BaseWorker pipeline
# ═══════════════════════════════════════════════════════

class TestExchangeBackup:
    """Test Exchange backup using BaseWorker pipeline."""

    @pytest.mark.asyncio
    async def test_full_backup_with_emails(self, mock_deps):
        db, graph, storage, enc = mock_deps

        # get_all_pages called for: folders, calendar, contacts, (no attachments since hasAttachments=False)
        graph.get_all_pages = AsyncMock(side_effect=[
            [{"id": "inbox", "displayName": "Inbox"}],  # folders
            [],  # calendar events
            [],  # contacts
        ])
        graph.get_delta = AsyncMock(return_value=([
            {"id": "msg1", "subject": "Email 1", "from": {"emailAddress": {"address": "sender@test.com"}},
             "toRecipients": [{"emailAddress": {"address": "to@test.com"}}],
             "receivedDateTime": "2024-01-01T12:00:00Z", "importance": "normal",
             "isRead": False, "hasAttachments": False, "body": {"content": "Hello"}},
            {"id": "msg2", "subject": "Email 2", "from": {"emailAddress": {"address": "other@test.com"}},
             "toRecipients": [], "receivedDateTime": "2024-01-02T08:00:00Z",
             "importance": "high", "isRead": True, "hasAttachments": False},
        ], "new_delta"))

        worker = ExchangeWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user1", tenant_id=1, id=10, display_name="Test User")
        snapshot = MagicMock(id=100)

        item_count, total_size, delta = await worker.backup(obj, snapshot, "wrapped_dek", concurrency=5)

        assert item_count == 2  # 2 emails, 0 cal, 0 contacts
        assert total_size > 0
        assert storage.store_item.call_count == 2
        assert db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_backup_with_attachments(self, mock_deps):
        db, graph, storage, enc = mock_deps

        graph.get_all_pages = AsyncMock(side_effect=[
            [{"id": "inbox", "displayName": "Inbox"}],  # folders
            [{"id": "att1", "name": "doc.pdf", "contentBytes": "dGVzdA==",  # base64 "test"
              "contentType": "application/pdf"}],  # attachments
        ])
        graph.get_delta = AsyncMock(return_value=([
            {"id": "msg1", "subject": "With Attachment",
             "from": {"emailAddress": {"address": "a@b.com"}},
             "toRecipients": [], "receivedDateTime": "2024-01-01T00:00:00Z",
             "importance": "normal", "isRead": False, "hasAttachments": True},
        ], None))

        worker = ExchangeWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user1", tenant_id=1, id=10, display_name="Test")
        snapshot = MagicMock(id=100)

        item_count, total_size, delta = await worker.backup(obj, snapshot, "dek", concurrency=5)

        # 1 email + 1 attachment = 2 items
        assert item_count == 2
        assert storage.store_item.call_count == 2


# ═══════════════════════════════════════════════════════
# Test: OneDrive backup via BaseWorker pipeline
# ═══════════════════════════════════════════════════════

class TestOneDriveBackup:
    """Test OneDrive backup using BaseWorker pipeline."""

    @pytest.mark.asyncio
    async def test_files_and_folders(self, mock_deps):
        db, graph, storage, enc = mock_deps

        graph.get_delta = AsyncMock(return_value=([
            {"id": "f1", "name": "report.xlsx", "file": {"mimeType": "application/xlsx"}, "size": 5000,
             "parentReference": {"path": "/drive/root:"}, "lastModifiedDateTime": "2024-06-01T00:00:00Z"},
            {"id": "d1", "name": "Projects", "folder": {"childCount": 3},
             "parentReference": {"path": "/drive/root:"}},
            {"id": "@removed_item", "@removed": {"reason": "deleted"}},  # Should be skipped
        ], "delta_123"))

        worker = OneDriveWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="user1", tenant_id=1, id=10, display_name="Test")
        snapshot = MagicMock(id=200)

        item_count, total_size, delta = await worker.backup(obj, snapshot, "dek", concurrency=3)

        assert item_count == 2  # file + folder, removed skipped
        assert delta == "delta_123"


# ═══════════════════════════════════════════════════════
# Test: BackupItem extra_fields for workload-specific data
# ═══════════════════════════════════════════════════════

class TestBackupItemFields:
    """Test that workload-specific fields are correctly populated."""

    @pytest.mark.asyncio
    async def test_email_has_subject_and_sender(self, mock_deps):
        db, graph, storage, enc = mock_deps

        graph.get_all_pages = AsyncMock(side_effect=[
            [{"id": "inbox", "displayName": "Inbox"}],  # folders
            [],  # calendar
            [],  # contacts
        ])
        graph.get_delta = AsyncMock(return_value=([
            {"id": "msg1", "subject": "Important Meeting",
             "from": {"emailAddress": {"address": "boss@corp.com"}},
             "toRecipients": [{"emailAddress": {"address": "me@corp.com"}}],
             "receivedDateTime": "2024-03-15T09:30:00Z",
             "importance": "high", "isRead": False, "hasAttachments": False},
        ], None))

        worker = ExchangeWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="u1")
        items, _ = await worker.discover_items(obj)

        email_items = [i for i in items if i.item_type == ItemType.EMAIL]
        assert len(email_items) == 1
        item = email_items[0]
        assert item.extra_fields["subject"] == "Important Meeting"
        assert item.extra_fields["sender"] == "boss@corp.com"
        assert item.extra_fields["received_at"] is not None

    @pytest.mark.asyncio
    async def test_onedrive_file_has_filename_and_modified(self, mock_deps):
        db, graph, storage, enc = mock_deps

        graph.get_delta = AsyncMock(return_value=([
            {"id": "f1", "name": "quarterly-report.pdf",
             "file": {"mimeType": "application/pdf"}, "size": 1024,
             "parentReference": {"path": "/drive/root:/Finance"},
             "lastModifiedDateTime": "2024-06-15T14:00:00Z"},
        ], None))

        worker = OneDriveWorker(db, graph, storage, enc)
        obj = MagicMock(ms_object_id="u1")
        items, _ = await worker.discover_items(obj)

        assert len(items) == 1
        item = items[0]
        assert item.extra_fields["file_name"] == "quarterly-report.pdf"
        assert item.extra_fields["last_modified_at"] is not None
        assert item.path == "/Finance"


# ═══════════════════════════════════════════════════════
# Test: Worker has required methods for BackupEngine
# ═══════════════════════════════════════════════════════

class TestWorkerInterface:
    """Verify all workers have the methods BackupEngine expects."""

    def test_all_workers_have_backup(self, mock_deps):
        for cls in [ExchangeWorker, OneDriveWorker, SharePointWorker, TeamsWorker, EntraIDWorker]:
            worker = cls(*mock_deps)
            assert hasattr(worker, 'backup'), f"{cls.__name__} missing backup()"
            assert callable(worker.backup)

    def test_all_workers_have_workload_name(self, mock_deps):
        for cls in [ExchangeWorker, OneDriveWorker, SharePointWorker, TeamsWorker, EntraIDWorker]:
            worker = cls(*mock_deps)
            assert hasattr(worker, 'workload_name'), f"{cls.__name__} missing workload_name()"
            assert isinstance(worker.workload_name(), str)

    def test_all_workers_have_discover_items(self, mock_deps):
        for cls in [ExchangeWorker, OneDriveWorker, SharePointWorker, TeamsWorker, EntraIDWorker]:
            worker = cls(*mock_deps)
            assert hasattr(worker, 'discover_items'), f"{cls.__name__} missing discover_items()"

    def test_exchange_has_restore(self, mock_deps):
        worker = ExchangeWorker(*mock_deps)
        assert hasattr(worker, 'restore_items')
        assert hasattr(worker, 'restore_full_mailbox')
        assert hasattr(worker, 'export_to_eml')

    def test_onedrive_has_restore(self, mock_deps):
        worker = OneDriveWorker(*mock_deps)
        assert hasattr(worker, 'restore_items')
        assert hasattr(worker, 'restore_full_account')

    def test_teams_has_restore(self, mock_deps):
        worker = TeamsWorker(*mock_deps)
        assert hasattr(worker, 'restore_items')

    def test_entra_id_has_restore(self, mock_deps):
        worker = EntraIDWorker(*mock_deps)
        assert hasattr(worker, 'restore_items')
