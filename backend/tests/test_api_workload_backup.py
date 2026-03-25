"""Tests for workload API backup routes.

Verifies that all 5 workload backup endpoints (Exchange, OneDrive, SharePoint,
Teams, Entra ID) route through BackupEngine and return correct responses.
Also tests backup-all routes and restore route error handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.snapshot import SnapshotStatus


def make_mock_snapshot(snapshot_id=1, item_count=5, size_bytes=1024):
    snap = MagicMock()
    snap.id = snapshot_id
    snap.item_count = item_count
    snap.size_bytes = size_bytes
    snap.status = SnapshotStatus.COMPLETED
    return snap


def make_mock_object(obj_id=1, tenant_id=1, workload="exchange"):
    from app.models.protected_object import WorkloadType
    obj = MagicMock()
    obj.id = obj_id
    obj.tenant_id = tenant_id
    obj.display_name = f"Test {workload.title()}"
    obj.email = f"test@example.com"
    obj.workload_type = WorkloadType(workload)
    return obj


# ── Exchange backup routes ──

class TestExchangeBackupRoutes:
    """Tests for POST /api/exchange/mailboxes/{id}/backup."""

    @pytest.mark.asyncio
    async def test_single_mailbox_backup_calls_backup_engine(self):
        """Single mailbox backup invokes BackupEngine.run_backup_for_object."""
        from app.api.exchange import trigger_backup, BackupEngine
        from app.models.protected_object import WorkloadType

        mock_obj = make_mock_object(1, 1, "exchange")
        mock_snapshot = make_mock_snapshot(10, 20, 4096)

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)

        mock_user = MagicMock()

        with patch("app.api.exchange.BackupEngine", return_value=mock_engine):
            result = await trigger_backup(mailbox_id=1, db=mock_db, current_user=mock_user)

        mock_engine.run_backup_for_object.assert_called_once_with(mock_obj)
        assert result["snapshot_id"] == 10
        assert result["item_count"] == 20
        assert result["size_bytes"] == 4096

    @pytest.mark.asyncio
    async def test_single_mailbox_backup_404_when_not_found(self):
        """Returns 404 when mailbox doesn't exist."""
        from app.api.exchange import trigger_backup
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await trigger_backup(mailbox_id=9999, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_backup_all_creates_backup_job(self):
        """backup-all creates a BackupJob record for tracking."""
        from app.api.exchange import trigger_backup_all
        from app.models.backup_job import BackupJob, JobStatus

        mock_obj = make_mock_object(1, 1, "exchange")
        mock_snapshot = make_mock_snapshot(5, 3, 512)

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        added_objects = []

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        def capture_add(obj):
            added_objects.append(obj)
            if isinstance(obj, BackupJob):
                obj.id = 1

        mock_db.add = MagicMock(side_effect=capture_add)

        execute_count = 0
        async def mock_execute(stmt):
            nonlocal execute_count
            execute_count += 1
            mock_result = MagicMock()
            if execute_count == 1:
                mock_result.scalars.return_value.all.return_value = [mock_obj]
            else:
                mock_result.scalar_one_or_none.return_value = None
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        with patch("app.api.exchange.BackupEngine", return_value=mock_engine):
            result = await trigger_backup_all(tenant_id=1, db=mock_db, current_user=MagicMock())

        backup_jobs = [o for o in added_objects if isinstance(o, BackupJob)]
        assert len(backup_jobs) >= 1
        assert result["total"] == 1
        assert result["succeeded"] == 1

    @pytest.mark.asyncio
    async def test_backup_all_404_when_no_mailboxes(self):
        """Returns 404 when tenant has no Exchange mailboxes."""
        from app.api.exchange import trigger_backup_all
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await trigger_backup_all(tenant_id=99, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404


# ── OneDrive backup routes ──

class TestOneDriveBackupRoutes:
    """Tests for POST /api/onedrive/accounts/{id}/backup."""

    @pytest.mark.asyncio
    async def test_single_account_backup_calls_backup_engine(self):
        """Single account backup invokes BackupEngine.run_backup_for_object."""
        from app.api.onedrive import trigger_backup

        mock_obj = make_mock_object(2, 1, "onedrive")
        mock_snapshot = make_mock_snapshot(20, 15, 2048)

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)

        with patch("app.api.onedrive.BackupEngine", return_value=mock_engine):
            result = await trigger_backup(account_id=2, db=mock_db, current_user=MagicMock())

        mock_engine.run_backup_for_object.assert_called_once_with(mock_obj)
        assert result["snapshot_id"] == 20

    @pytest.mark.asyncio
    async def test_single_account_backup_404_when_not_found(self):
        """Returns 404 when OneDrive account doesn't exist."""
        from app.api.onedrive import trigger_backup
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await trigger_backup(account_id=9999, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404


# ── SharePoint backup routes ──

class TestSharePointBackupRoutes:
    """Tests for POST /api/sharepoint/sites/{id}/backup."""

    @pytest.mark.asyncio
    async def test_single_site_backup_calls_backup_engine(self):
        """Single site backup invokes BackupEngine.run_backup_for_object."""
        from app.api.sharepoint import trigger_backup

        mock_obj = make_mock_object(3, 1, "sharepoint")
        mock_snapshot = make_mock_snapshot(30, 100, 8192)

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)

        with patch("app.api.sharepoint.BackupEngine", return_value=mock_engine):
            result = await trigger_backup(site_id=3, db=mock_db, current_user=MagicMock())

        mock_engine.run_backup_for_object.assert_called_once_with(mock_obj)
        assert result["snapshot_id"] == 30

    @pytest.mark.asyncio
    async def test_single_site_backup_404_when_not_found(self):
        """Returns 404 when SharePoint site doesn't exist."""
        from app.api.sharepoint import trigger_backup
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await trigger_backup(site_id=9999, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404


# ── Teams backup routes ──

class TestTeamsBackupRoutes:
    """Tests for POST /api/teams/teams/{id}/backup."""

    @pytest.mark.asyncio
    async def test_single_team_backup_calls_backup_engine(self):
        """Single team backup invokes BackupEngine.run_backup_for_object."""
        from app.api.teams import backup_single_team
        from app.models.protected_object import WorkloadType

        mock_obj = make_mock_object(4, 1, "teams")
        mock_snapshot = make_mock_snapshot(40, 200, 16384)
        mock_snapshot.status = SnapshotStatus.COMPLETED

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_obj)
        mock_db.commit = AsyncMock()

        with patch("app.api.teams.BackupEngine", return_value=mock_engine):
            result = await backup_single_team(team_id=4, db=mock_db, current_user=MagicMock())

        mock_engine.run_backup_for_object.assert_called_once_with(mock_obj)
        assert result["snapshot_id"] == 40
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_single_team_backup_404_when_not_found(self):
        """Returns 404 when team doesn't exist."""
        from app.api.teams import backup_single_team
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await backup_single_team(team_id=9999, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_backup_all_teams_returns_results_list(self):
        """backup-all for Teams returns per-team results."""
        from app.api.teams import backup_all_teams
        from app.models.protected_object import WorkloadType

        team1 = make_mock_object(1, 1, "teams")
        team1.display_name = "Engineering Team"
        team2 = make_mock_object(2, 1, "teams")
        team2.display_name = "Marketing Team"

        snap1 = make_mock_snapshot(1, 50, 2048)
        snap2 = make_mock_snapshot(2, 30, 1024)

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(side_effect=[snap1, snap2])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [team1, team2]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch("app.api.teams.BackupEngine", return_value=mock_engine):
            result = await backup_all_teams(tenant_id=1, db=mock_db, current_user=MagicMock())

        assert result["backed_up"] == 2
        assert len(result["results"]) == 2


# ── Entra ID backup routes ──

class TestEntraIDBackupRoutes:
    """Tests for POST /api/entra-id/backup."""

    @pytest.mark.asyncio
    async def test_entra_id_backup_calls_backup_engine(self):
        """Entra ID backup invokes BackupEngine.run_backup_for_object."""
        from app.api.entra_id import backup_entra_id

        mock_obj = make_mock_object(5, 1, "entra_id")
        mock_snapshot = make_mock_snapshot(50, 500, 32768)

        mock_engine = AsyncMock()
        mock_engine.run_backup_for_object = AsyncMock(return_value=mock_snapshot)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_obj

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch("app.api.entra_id.BackupEngine", return_value=mock_engine):
            result = await backup_entra_id(tenant_id=1, db=mock_db, current_user=MagicMock())

        mock_engine.run_backup_for_object.assert_called_once_with(mock_obj)
        assert result["snapshot_id"] == 50
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_entra_id_backup_404_when_not_discovered(self):
        """Returns 404 when no Entra ID object exists for tenant."""
        from app.api.entra_id import backup_entra_id
        from fastapi import HTTPException

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await backup_entra_id(tenant_id=99, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404


# ── Restore route dispatcher integration ──

class TestRestoreRouteDispatcher:
    """Restore routes create a RestoreJob and invoke RestoreEngine."""

    @pytest.mark.asyncio
    async def test_exchange_restore_creates_restore_job(self):
        """Exchange restore endpoint creates a RestoreJob and calls execute_restore."""
        from app.api.exchange import restore_mailbox, RestoreRequest
        from app.models.restore_job import RestoreJob, RestoreStatus

        mock_obj = make_mock_object(1, 1, "exchange")
        mock_snapshot = MagicMock()
        mock_snapshot.status = SnapshotStatus.COMPLETED

        mock_restore_engine = AsyncMock()
        mock_restore_engine.execute_restore = AsyncMock()

        created_jobs = []
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(side_effect=lambda model, pk: mock_obj if "ProtectedObject" in str(model) else mock_snapshot)
        mock_db.add = MagicMock(side_effect=created_jobs.append)
        mock_db.flush = AsyncMock()

        req = RestoreRequest(snapshot_id=1)

        # RestoreEngine is imported locally inside the route function
        with patch("app.services.restore_engine.RestoreEngine", return_value=mock_restore_engine):
            result = await restore_mailbox(mailbox_id=1, req=req, db=mock_db, current_user=MagicMock())

        mock_restore_engine.execute_restore.assert_called_once()
        assert any(isinstance(j, RestoreJob) for j in created_jobs)

    @pytest.mark.asyncio
    async def test_restore_404_when_snapshot_not_found(self):
        """Restore returns 404 when snapshot doesn't exist or isn't COMPLETED."""
        from app.api.exchange import restore_mailbox, RestoreRequest
        from fastapi import HTTPException

        mock_obj = make_mock_object(1, 1, "exchange")
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(side_effect=[mock_obj, None])  # obj found, snapshot not found

        req = RestoreRequest(snapshot_id=9999)

        with pytest.raises(HTTPException) as exc_info:
            await restore_mailbox(mailbox_id=1, req=req, db=mock_db, current_user=MagicMock())

        assert exc_info.value.status_code == 404
