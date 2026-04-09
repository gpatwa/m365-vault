"""Tests for workload API backup routes.

Verifies that all 5 workload backup endpoints route through the
dispatcher (get_dispatcher) and return correct responses.

Tests use HTTP client calls (auth_client) to exercise the routes the
same way production does, with the dispatcher mocked at the factory level.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.interfaces.job_message import JobResult
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.tenant import Tenant, TenantStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotType


def make_job_result(success=True, snapshot_id=1, item_count=5, size_bytes=1024, error=None, status="completed"):
    return JobResult(
        success=success,
        snapshot_id=snapshot_id,
        item_count=item_count,
        size_bytes=size_bytes,
        error=error,
        status=status,
    )


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
    async def test_single_mailbox_backup_dispatches(self, auth_client: AsyncClient, db, test_tenant):
        """Single mailbox backup routes through dispatcher."""
        # Create a protected object for Exchange
        obj = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-001", display_name="Test Mailbox",
            email="test@example.com", status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()
        await db.commit()
        obj_id = obj.id

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=10, item_count=20))

        with patch("app.api.workload_base.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/exchange/mailboxes/{obj_id}/backup")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == 10
        assert data["item_count"] == 20
        mock_disp.dispatch_backup_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_backup_all_dispatches_for_each_object(self, auth_client: AsyncClient, db, test_tenant):
        """Backup-all creates backup job via dispatcher for all mailboxes."""
        obj1 = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-all-001", display_name="Mailbox 1",
            email="mbx1@example.com", status=ProtectionStatus.PROTECTED,
        )
        obj2 = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-all-002", display_name="Mailbox 2",
            email="mbx2@example.com", status=ProtectionStatus.PROTECTED,
        )
        db.add_all([obj1, obj2])
        await db.flush()
        await db.commit()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=5, item_count=10))

        with patch("app.api.workload_base.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/exchange/backup-all?tenant_id={test_tenant}")

        assert response.status_code == 200
        assert mock_disp.dispatch_backup_object.call_count == 2


# ── OneDrive backup routes ──

class TestOneDriveBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_account_backup_dispatches(self, auth_client: AsyncClient, db, test_tenant):
        """Single OneDrive backup routes through dispatcher."""
        obj = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.ONEDRIVE,
            ms_object_id="od-001", display_name="Test OneDrive",
            email="test@example.com", status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()
        await db.commit()
        obj_id = obj.id

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=15, item_count=8))

        with patch("app.api.workload_base.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/onedrive/accounts/{obj_id}/backup")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == 15
        mock_disp.dispatch_backup_object.assert_called_once()


# ── SharePoint backup routes ──

class TestSharePointBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_site_backup_dispatches(self, auth_client: AsyncClient, db, test_tenant):
        """Single SharePoint site backup routes through dispatcher."""
        obj = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.SHAREPOINT,
            ms_object_id="sp-001", display_name="Test SharePoint Site",
            site_url="https://test.sharepoint.com/sites/test",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()
        await db.commit()
        obj_id = obj.id

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=20, item_count=19))

        with patch("app.api.workload_base.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/sharepoint/sites/{obj_id}/backup")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == 20
        mock_disp.dispatch_backup_object.assert_called_once()


# ── Teams backup routes ──

class TestTeamsBackupRoutes:

    @pytest.mark.asyncio
    async def test_single_team_backup_dispatches(self, auth_client: AsyncClient, db, test_tenant):
        """Single Team backup routes through dispatcher."""
        obj = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.TEAMS,
            ms_object_id="team-001", display_name="Test Team",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()
        await db.commit()
        obj_id = obj.id

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=25, item_count=12))

        with patch("app.api.workload_base.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/teams/teams/{obj_id}/backup")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == 25
        mock_disp.dispatch_backup_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_backup_all_teams_dispatches(self, auth_client: AsyncClient, db, test_tenant):
        """Backup-all dispatches for each team."""
        obj = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.TEAMS,
            ms_object_id="team-all-001", display_name="Test Team All",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()
        await db.commit()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=30, item_count=4))

        with patch("app.api.workload_base.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/teams/backup-all?tenant_id={test_tenant}")

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1


# ── Entra ID backup routes ──

class TestEntraIDBackupRoutes:

    @pytest.mark.asyncio
    async def test_entra_id_backup_dispatches(self, auth_client: AsyncClient, db, test_tenant):
        """Entra ID backup routes through dispatcher."""
        obj = ProtectedObject(
            tenant_id=test_tenant, workload_type=WorkloadType.ENTRA_ID,
            ms_object_id="entra-001", display_name="Entra ID Config",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()
        await db.commit()

        mock_disp = make_mock_dispatcher(make_job_result(snapshot_id=35, item_count=16, size_bytes=48000))

        with patch("app.api.entra_id.get_dispatcher", return_value=mock_disp):
            response = await auth_client.post(f"/api/entra-id/backup?tenant_id={test_tenant}")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == 35
        mock_disp.dispatch_backup_object.assert_called_once()
