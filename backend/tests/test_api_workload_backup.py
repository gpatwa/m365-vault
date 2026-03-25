"""Tests for workload API backup routes.

Verifies that all 5 workload backup endpoints route through the
dispatcher (get_dispatcher) and return correct responses.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.interfaces.job_message import JobResult


def make_job_result(success=True, snapshot_id=1, item_count=5, size_bytes=1024, error=None):
    return JobResult(
        success=success,
        snapshot_id=snapshot_id,
        item_count=item_count,
        size_bytes=size_bytes,
        error=error,
    )


def make_mock_object(obj_id=1, tenant_id=1, workload="exchange"):
    from app.models.protected_object import WorkloadType
    obj = MagicMock()
    obj.id = obj_id
    obj.tenant_id = tenant_id
    obj.display_name = f"Test {workload.title()}"
    obj.email = "test@example.com"
    obj.workload_type = WorkloadType(workload)
    obj.status = MagicMock(value="protected")
    obj.last_backup_at = None
    obj.total_items_backed_up = 0
    obj.total_size_bytes = 0
    return obj


def make_mock_dispatcher(result=None):
    """Create a mock dispatcher that returns the given result."""
    if result is None:
        result = make_job_result()
    dispatcher = AsyncMock()
    dispatcher.dispatch_backup_object = AsyncMock(return_value=result)
    dispatcher.dispatch_backup_job = AsyncMock(return_value=result)
    dispatcher.dispatch_restore = AsyncMock(return_value=result)
    return dispatcher


# ── Exchange backup routes ──

class TestExchangeBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_mailbox_backup_dispatches(self):
        """Single mailbox backup routes through dispatcher."""
        from app.api.exchange import trigger_backup

        mock_obj = make_mock_object(1, 1, "exchange")
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=10, item_count=20))

        with patch("app.api.exchange.get_dispatcher", return_value=mock_disp):
            result = await trigger_backup(mailbox_id=1, db=mock_db, current_user=mock_user)

        mock_disp.dispatch_backup_object.assert_called_once()
        assert result["snapshot_id"] == 10
        assert result["item_count"] == 20

    @pytest.mark.asyncio
    async def test_backup_all_dispatches_for_each_object(self):
        """Backup-all creates backup job via dispatcher for all mailboxes."""
        from app.api.exchange import trigger_backup_all as backup_all_exchange

        mock_obj1 = make_mock_object(1, 1, "exchange")
        mock_obj2 = make_mock_object(2, 1, "exchange")

        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_obj1, mock_obj2])))
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=5, item_count=10))

        with patch("app.api.exchange.get_dispatcher", return_value=mock_disp):
            result = await backup_all_exchange(tenant_id=1, db=mock_db, current_user=mock_user)

        assert mock_disp.dispatch_backup_object.call_count == 2


# ── OneDrive backup routes ──

class TestOneDriveBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_account_backup_dispatches(self):
        """Single OneDrive backup routes through dispatcher."""
        from app.api.onedrive import trigger_backup

        mock_obj = make_mock_object(1, 1, "onedrive")
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=15, item_count=8))

        with patch("app.api.onedrive.get_dispatcher", return_value=mock_disp):
            result = await trigger_backup(account_id=1, db=mock_db, current_user=mock_user)

        mock_disp.dispatch_backup_object.assert_called_once()
        assert result["snapshot_id"] == 15


# ── SharePoint backup routes ──

class TestSharePointBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_site_backup_dispatches(self):
        """Single SharePoint site backup routes through dispatcher."""
        from app.api.sharepoint import trigger_backup

        mock_obj = make_mock_object(1, 1, "sharepoint")
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=20, item_count=19))

        with patch("app.api.sharepoint.get_dispatcher", return_value=mock_disp):
            result = await trigger_backup(site_id=1, db=mock_db, current_user=mock_user)

        mock_disp.dispatch_backup_object.assert_called_once()
        assert result["snapshot_id"] == 20


# ── Teams backup routes ──

class TestTeamsBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_team_backup_dispatches(self):
        """Single Team backup routes through dispatcher."""
        from app.api.teams import backup_single_team

        mock_obj = make_mock_object(1, 1, "teams")
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=25, item_count=12))

        with patch("app.api.teams.get_dispatcher", return_value=mock_disp):
            result = await backup_single_team(team_id=1, db=mock_db, current_user=mock_user)

        mock_disp.dispatch_backup_object.assert_called_once()
        assert result["snapshot_id"] == 25

    @pytest.mark.asyncio
    async def test_backup_all_teams_dispatches(self):
        """Backup-all dispatches for each team."""
        from app.api.teams import backup_all_teams

        mock_obj = make_mock_object(1, 1, "teams")
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_obj])))
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=30, item_count=4))

        with patch("app.api.teams.get_dispatcher", return_value=mock_disp):
            result = await backup_all_teams(tenant_id=1, db=mock_db, current_user=mock_user)

        assert result["backed_up"] == 1


# ── Entra ID backup routes ──

class TestEntraIDBackupRoutes:

    @pytest.mark.asyncio
    async def test_entra_id_backup_dispatches(self):
        """Entra ID backup routes through dispatcher."""
        from app.api.entra_id import backup_entra_id

        mock_obj = make_mock_object(1, 1, "entra_id")
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_obj)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_user = MagicMock()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=35, item_count=16, size_bytes=48000))

        with patch("app.api.entra_id.get_dispatcher", return_value=mock_disp):
            result = await backup_entra_id(tenant_id=1, db=mock_db, current_user=mock_user)

        mock_disp.dispatch_backup_object.assert_called_once()
        assert result["snapshot_id"] == 35


# ── Restore route dispatch ──

class TestRestoreRouteDispatcher:

    @pytest.mark.asyncio
    async def test_exchange_restore_dispatches(self):
        """Exchange restore routes through dispatcher."""
        from app.api.exchange import restore_mailbox, RestoreRequest
        from app.models.snapshot import Snapshot, SnapshotStatus as SS

        mock_obj = make_mock_object(1, 1, "exchange")
        mock_snapshot = MagicMock()
        mock_snapshot.id = 10
        mock_snapshot.status = SS.COMPLETED

        from app.models.protected_object import ProtectedObject

        mock_db = AsyncMock()
        # Return different mocks based on model type
        async def smart_get(model, pk):
            if model is Snapshot:
                return mock_snapshot
            if model is ProtectedObject:
                return mock_obj
            return mock_obj
        mock_db.get = smart_get
        def mock_add(obj):
            obj.id = 99  # Simulate DB assigning an ID
        mock_db.add = mock_add
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_user = MagicMock()

        req = RestoreRequest(snapshot_id=10, restore_type="full_inplace")
        mock_disp = make_mock_dispatcher(make_job_result(success=True))

        with patch("app.api.exchange.get_dispatcher", return_value=mock_disp):
            result = await restore_mailbox(
                mailbox_id=1, req=req, db=mock_db, current_user=mock_user
            )

        mock_disp.dispatch_restore.assert_called_once()
