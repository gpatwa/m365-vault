"""End-to-end tests for Restore Permission Model.

Covers:
  P0: Audit logging on restore endpoints + initiated_by_user_id tracking
  P1: RESTORE_OPERATOR role, self-restore hardening, PST export restriction
  P2: Approval workflow (pending, approve, reject, separation of duties, expiry)
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotType
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus
from app.models.restore_approval import RestoreApproval
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


# ═══════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def restore_operator_client(client: AsyncClient):
    """Authenticated client with restore_operator role."""
    await client.post("/api/auth/register", json={
        "username": "testoperator",
        "email": "restoreop@test.com",
        "password": "TestPass123",
        "full_name": "Test Restore Operator",
        "role": "restore_operator",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testoperator",
        "password": "TestPass123",
    })
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest_asyncio.fixture
async def operator_client(client: AsyncClient):
    """Authenticated client with operator role (backup only, no restore)."""
    await client.post("/api/auth/register", json={
        "username": "testbackupop",
        "email": "backupop@test.com",
        "password": "TestPass123",
        "full_name": "Test Backup Operator",
        "role": "operator",
    })
    response = await client.post("/api/auth/login", data={
        "username": "testbackupop",
        "password": "TestPass123",
    })
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


async def _seed_tenant_with_snapshot():
    """Helper: create tenant + protected object + snapshot for restore tests."""
    async with async_session() as db:
        tenant = Tenant(
            name="Restore Test Corp", ms_tenant_id="restore-test-001",
            client_id="cid-restore", client_secret_encrypted="enc-restore",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        obj = ProtectedObject(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-restore-001", display_name="Alice Mailbox",
            email="alice@test.com", status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()

        snapshot = Snapshot(
            protected_object_id=obj.id,
            snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow(),
            item_count=10, size_bytes=1024,
        )
        db.add(snapshot)
        await db.flush()

        tid, oid, sid = tenant.id, obj.id, snapshot.id
        await db.commit()

    return tid, oid, sid


async def _seed_entra_tenant_with_snapshot():
    """Helper: create Entra ID tenant + object + snapshot."""
    async with async_session() as db:
        tenant = Tenant(
            name="Entra Test Corp", ms_tenant_id="entra-test-001",
            client_id="cid-entra", client_secret_encrypted="enc-entra",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        obj = ProtectedObject(
            tenant_id=tenant.id, workload_type=WorkloadType.ENTRA_ID,
            ms_object_id="entra-obj-001", display_name="Entra Config",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()

        snapshot = Snapshot(
            protected_object_id=obj.id,
            snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow(),
            item_count=5, size_bytes=512,
        )
        db.add(snapshot)
        await db.flush()

        tid, oid, sid = tenant.id, obj.id, snapshot.id
        await db.commit()

    return tid, oid, sid


async def _get_audit_logs(action_prefix: str):
    """Helper: query audit logs by action prefix."""
    from sqlalchemy import select
    async with async_session() as db:
        result = await db.execute(
            select(AuditLog).where(AuditLog.action.like(f"{action_prefix}%"))
        )
        return result.scalars().all()


async def _get_restore_job(job_id: int):
    """Helper: get a restore job by ID."""
    async with async_session() as db:
        return await db.get(RestoreJob, job_id)


# ═══════════════════════════════════════════════════════
# P0: Audit Logging Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_exchange_restore_creates_audit_log(auth_client: AsyncClient):
    """Exchange restore creates an audit log entry with user_id."""
    tid, oid, sid = await _seed_tenant_with_snapshot()

    response = await auth_client.post(f"/api/exchange/mailboxes/{oid}/restore", json={
        "snapshot_id": sid, "restore_type": "full_inplace",
    })
    # Restore may succeed or fail depending on dispatcher, but audit should be logged
    assert response.status_code in (200, 500)

    logs = await _get_audit_logs("restore.exchange")
    assert len(logs) >= 1
    log = logs[0]
    assert log.action == "restore.exchange"
    assert log.resource_type == "protected_object"
    assert log.resource_id == oid
    assert log.user_id is not None
    assert log.severity == "warning"


@pytest.mark.asyncio
async def test_exchange_restore_sets_initiated_by(auth_client: AsyncClient):
    """Exchange restore sets initiated_by_user_id on RestoreJob."""
    tid, oid, sid = await _seed_tenant_with_snapshot()

    response = await auth_client.post(f"/api/exchange/mailboxes/{oid}/restore", json={
        "snapshot_id": sid, "restore_type": "full_inplace",
    })
    assert response.status_code in (200, 500)

    if response.status_code == 200:
        job_id = response.json()["restore_job_id"]
        job = await _get_restore_job(job_id)
        assert job is not None
        assert job.initiated_by_user_id is not None


@pytest.mark.asyncio
async def test_entra_restore_creates_audit_log(auth_client: AsyncClient):
    """Entra ID restore creates an audit log entry."""
    tid, oid, sid = await _seed_entra_tenant_with_snapshot()

    response = await auth_client.post(f"/api/entra-id/restore?tenant_id={tid}", json={
        "snapshot_id": sid, "restore_type": "item_level", "item_ids": [1],
    })
    assert response.status_code in (200, 500)

    logs = await _get_audit_logs("restore.entra_id")
    assert len(logs) >= 1
    assert logs[0].severity == "warning"


@pytest.mark.asyncio
async def test_test_restore_creates_audit_log(auth_client: AsyncClient):
    """Test restore creates an audit log entry."""
    tid, oid, sid = await _seed_tenant_with_snapshot()

    response = await auth_client.post(f"/api/recovery/test-restore?tenant_id={tid}")
    assert response.status_code in (200, 404)

    logs = await _get_audit_logs("restore.test")
    # Only logged if objects were found
    if response.status_code == 200:
        assert len(logs) >= 1
        assert logs[0].severity == "info"


# ═══════════════════════════════════════════════════════
# P1: RESTORE_OPERATOR Role Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_restore_operator_can_restore_exchange(restore_operator_client: AsyncClient):
    """RESTORE_OPERATOR can trigger Exchange restore."""
    tid, oid, sid = await _seed_tenant_with_snapshot()

    response = await restore_operator_client.post(
        f"/api/exchange/mailboxes/{oid}/restore",
        json={"snapshot_id": sid, "restore_type": "full_inplace"},
    )
    # Should NOT be 403 — restore operator has permission
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_restore_operator_can_restore_entra(restore_operator_client: AsyncClient):
    """RESTORE_OPERATOR can trigger Entra ID restore."""
    tid, oid, sid = await _seed_entra_tenant_with_snapshot()

    response = await restore_operator_client.post(
        f"/api/entra-id/restore?tenant_id={tid}",
        json={"snapshot_id": sid, "restore_type": "item_level", "item_ids": [1]},
    )
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_backup_operator_cannot_restore(operator_client: AsyncClient):
    """Regular OPERATOR (backup-only) cannot trigger restore."""
    tid, oid, sid = await _seed_tenant_with_snapshot()

    response = await operator_client.post(
        f"/api/exchange/mailboxes/{oid}/restore",
        json={"snapshot_id": sid, "restore_type": "full_inplace"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_restore(viewer_client: AsyncClient):
    """VIEWER cannot trigger restore."""
    tid, oid, sid = await _seed_tenant_with_snapshot()

    response = await viewer_client.post(
        f"/api/exchange/mailboxes/{oid}/restore",
        json={"snapshot_id": sid, "restore_type": "full_inplace"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_restore(client: AsyncClient):
    """Unauthenticated user cannot trigger restore."""
    response = await client.post("/api/exchange/mailboxes/1/restore", json={
        "snapshot_id": 1, "restore_type": "full_inplace",
    })
    assert response.status_code == 401


# ═══════════════════════════════════════════════════════
# P1: Self-Restore Hardening Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_self_restore_search_works(auth_client: AsyncClient):
    """Self-restore search endpoint is accessible."""
    response = await auth_client.get("/api/self-restore/search?query=test")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_self_restore_requires_valid_items(auth_client: AsyncClient):
    """Self-restore requires valid item IDs."""
    response = await auth_client.post(
        "/api/self-restore/restore?snapshot_id=999&item_ids=invalid",
    )
    assert response.status_code in (400, 404)


# ═══════════════════════════════════════════════════════
# P1: PST Export Restriction Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pst_export_blocked_for_viewer(viewer_client: AsyncClient):
    """VIEWER cannot export PST (data exfiltration prevention)."""
    response = await viewer_client.post(
        "/api/exchange/mailboxes/1/export-pst?snapshot_id=1",
    )
    assert response.status_code == 403
    assert "Restore Operator or Admin" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_pst_export_blocked_for_operator(operator_client: AsyncClient):
    """Regular OPERATOR cannot export PST."""
    response = await operator_client.post(
        "/api/exchange/mailboxes/1/export-pst?snapshot_id=1",
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pst_export_allowed_for_admin(auth_client: AsyncClient):
    """ADMIN can access PST export (may fail on feature flag, not on permission)."""
    response = await auth_client.post(
        "/api/exchange/mailboxes/1/export-pst?snapshot_id=1",
    )
    # 403 from feature flag is OK (means role check passed), 404 is also fine
    # Should NOT be 403 with "Restore Operator or Admin" message
    if response.status_code == 403:
        assert "Restore Operator or Admin" not in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_pst_export_allowed_for_restore_operator(restore_operator_client: AsyncClient):
    """RESTORE_OPERATOR can access PST export."""
    response = await restore_operator_client.post(
        "/api/exchange/mailboxes/1/export-pst?snapshot_id=1",
    )
    if response.status_code == 403:
        assert "Restore Operator or Admin" not in response.json().get("detail", "")


# ═══════════════════════════════════════════════════════
# P2: Approval Workflow Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_approval_endpoints_exist(auth_client: AsyncClient):
    """Approval API endpoints are registered."""
    response = await auth_client.get("/api/restore-approvals/pending")
    assert response.status_code == 200

    response = await auth_client.get("/api/restore-approvals/count")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pending_approvals_empty(auth_client: AsyncClient):
    """Pending approvals returns empty list when none exist."""
    response = await auth_client.get("/api/restore-approvals/pending")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["approvals"] == []


@pytest.mark.asyncio
async def test_pending_count_zero(auth_client: AsyncClient):
    """Approval count returns 0 when no pending approvals."""
    response = await auth_client.get("/api/restore-approvals/count")
    assert response.status_code == 200
    assert response.json()["pending_count"] == 0


@pytest.mark.asyncio
async def test_approve_nonexistent_job(auth_client: AsyncClient):
    """Approving non-existent job returns 404."""
    response = await auth_client.post("/api/restore-approvals/99999/approve", json={
        "reason": "test",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_nonexistent_job(auth_client: AsyncClient):
    """Rejecting non-existent job returns 404."""
    response = await auth_client.post("/api/restore-approvals/99999/reject", json={
        "reason": "test",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approval_workflow_approve():
    """Full approval workflow: create request -> approve by different user -> job queued."""
    from app.services.audit import audit_log as _audit_log

    async with async_session() as db:
        # Create two users
        from app.services.auth import hash_password
        user1 = User(
            username="requester", email="req@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        user2 = User(
            username="approver", email="appr@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        db.add_all([user1, user2])
        await db.flush()

        # Create tenant + restore job
        tenant = Tenant(
            name="Approval Test", ms_tenant_id="approval-001",
            client_id="cid-appr", client_secret_encrypted="enc-appr",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        obj = ProtectedObject(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-appr-001", display_name="Approval Mailbox",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()

        snapshot = Snapshot(
            protected_object_id=obj.id, snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
            item_count=5, size_bytes=256,
        )
        db.add(snapshot)
        await db.flush()

        # Create restore job that needs approval
        job = RestoreJob(
            tenant_id=tenant.id, source_snapshot_id=snapshot.id,
            source_object_id=obj.id, restore_type=RestoreType.CROSS_USER,
            status=RestoreStatus.QUEUED,
            initiated_by_user_id=user1.id,
            approval_required=1, approval_status="pending",
        )
        db.add(job)
        await db.flush()

        # Create approval request
        from app.api.restore_approval import create_approval_request
        approval = await create_approval_request(db, job, user1.id)

        assert approval.status == "pending"
        assert approval.requested_by_user_id == user1.id
        assert approval.expires_at > datetime.utcnow()
        assert job.approval_required == 1
        assert job.approval_status == "pending"

        job_id = job.id
        approval_id = approval.id
        user1_id, user2_id = user1.id, user2.id
        await db.commit()

    # Now test the API: login as approver and approve
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Login as approver (user2)
        resp = await c.post("/api/auth/login", data={
            "username": "approver", "password": "TestPass123",
        })
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        # Check pending count (should see 1 — not own request)
        resp = await c.get("/api/restore-approvals/count")
        assert resp.status_code == 200
        assert resp.json()["pending_count"] == 1

        # List pending
        resp = await c.get("/api/restore-approvals/pending")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["approvals"][0]["restore_job_id"] == job_id

        # Approve
        resp = await c.post(f"/api/restore-approvals/{job_id}/approve", json={
            "reason": "Looks good, approved for recovery",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["restore_job_id"] == job_id

    # Verify job status updated
    job = await _get_restore_job(job_id)
    assert job.approval_status == "approved"

    # Verify audit logs
    logs = await _get_audit_logs("restore.approved")
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_approval_workflow_reject():
    """Rejection workflow: create request -> reject by different user."""
    async with async_session() as db:
        from app.services.auth import hash_password
        user1 = User(
            username="rejecter_req", email="rejreq@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        user2 = User(
            username="rejecter_appr", email="rejappr@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        db.add_all([user1, user2])
        await db.flush()

        tenant = Tenant(
            name="Reject Test", ms_tenant_id="reject-001",
            client_id="cid-rej", client_secret_encrypted="enc-rej",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        obj = ProtectedObject(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-rej-001", display_name="Reject Mailbox",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()

        snapshot = Snapshot(
            protected_object_id=obj.id, snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
            item_count=5, size_bytes=256,
        )
        db.add(snapshot)
        await db.flush()

        job = RestoreJob(
            tenant_id=tenant.id, source_snapshot_id=snapshot.id,
            source_object_id=obj.id, restore_type=RestoreType.MASS_RECOVERY,
            status=RestoreStatus.QUEUED,
            initiated_by_user_id=user1.id,
            approval_required=1, approval_status="pending",
        )
        db.add(job)
        await db.flush()

        approval = RestoreApproval(
            restore_job_id=job.id, requested_by_user_id=user1.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(approval)
        await db.flush()

        job_id = job.id
        await db.commit()

    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/auth/login", data={
            "username": "rejecter_appr", "password": "TestPass123",
        })
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        resp = await c.post(f"/api/restore-approvals/{job_id}/reject", json={
            "reason": "Too risky, not approved",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["reason"] == "Too risky, not approved"

    # Verify job status
    job = await _get_restore_job(job_id)
    assert job.approval_status == "rejected"
    assert job.status == RestoreStatus.FAILED
    assert "Rejected" in job.error_message

    # Verify audit
    logs = await _get_audit_logs("restore.rejected")
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_cannot_approve_own_request():
    """Separation of duties: requester cannot approve their own request."""
    async with async_session() as db:
        from app.services.auth import hash_password
        user1 = User(
            username="selfapprover", email="selfappr@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        db.add(user1)
        await db.flush()

        tenant = Tenant(
            name="Self Approve Test", ms_tenant_id="selfappr-001",
            client_id="cid-sa", client_secret_encrypted="enc-sa",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        obj = ProtectedObject(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-sa-001", display_name="Self Approve Mailbox",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()

        snapshot = Snapshot(
            protected_object_id=obj.id, snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
            item_count=5, size_bytes=256,
        )
        db.add(snapshot)
        await db.flush()

        job = RestoreJob(
            tenant_id=tenant.id, source_snapshot_id=snapshot.id,
            source_object_id=obj.id, restore_type=RestoreType.CROSS_USER,
            status=RestoreStatus.QUEUED,
            initiated_by_user_id=user1.id,
            approval_required=1, approval_status="pending",
        )
        db.add(job)
        await db.flush()

        approval = RestoreApproval(
            restore_job_id=job.id, requested_by_user_id=user1.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(approval)
        await db.flush()

        job_id = job.id
        await db.commit()

    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Login as the SAME user who requested
        resp = await c.post("/api/auth/login", data={
            "username": "selfapprover", "password": "TestPass123",
        })
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        # Try to approve own request
        resp = await c.post(f"/api/restore-approvals/{job_id}/approve", json={
            "reason": "I approve my own request",
        })
        assert resp.status_code == 403
        assert "Cannot approve your own" in resp.json()["detail"]

        # Also verify own requests don't show in pending list
        resp = await c.get("/api/restore-approvals/pending")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0  # Filtered out own requests

        # And count should be 0
        resp = await c.get("/api/restore-approvals/count")
        assert resp.json()["pending_count"] == 0


@pytest.mark.asyncio
async def test_approval_expiry():
    """Expired approvals are auto-marked as expired."""
    async with async_session() as db:
        from app.services.auth import hash_password
        user1 = User(
            username="expiry_req", email="expiry_req@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        user2 = User(
            username="expiry_appr", email="expiry_appr@test.com",
            password_hash=hash_password("TestPass123"),
            role=UserRole.ADMIN, is_active=1,
        )
        db.add_all([user1, user2])
        await db.flush()

        tenant = Tenant(
            name="Expiry Test", ms_tenant_id="expiry-001",
            client_id="cid-exp", client_secret_encrypted="enc-exp",
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        obj = ProtectedObject(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            ms_object_id="mbx-exp-001", display_name="Expiry Mailbox",
            status=ProtectionStatus.PROTECTED,
        )
        db.add(obj)
        await db.flush()

        snapshot = Snapshot(
            protected_object_id=obj.id, snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
            item_count=5, size_bytes=256,
        )
        db.add(snapshot)
        await db.flush()

        job = RestoreJob(
            tenant_id=tenant.id, source_snapshot_id=snapshot.id,
            source_object_id=obj.id, restore_type=RestoreType.CROSS_TENANT,
            status=RestoreStatus.QUEUED,
            initiated_by_user_id=user1.id,
            approval_required=1, approval_status="pending",
        )
        db.add(job)
        await db.flush()

        # Create ALREADY EXPIRED approval
        approval = RestoreApproval(
            restore_job_id=job.id, requested_by_user_id=user1.id,
            status="pending",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Already expired
        )
        db.add(approval)
        await db.flush()

        job_id = job.id
        await db.commit()

    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/auth/login", data={
            "username": "expiry_appr", "password": "TestPass123",
        })
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        # Listing pending should auto-expire and return empty
        resp = await c.get("/api/restore-approvals/pending")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

        # Trying to approve expired should fail
        resp = await c.post(f"/api/restore-approvals/{job_id}/approve")
        assert resp.status_code in (404, 410)  # Not found or Gone


# ═══════════════════════════════════════════════════════
# P2: Approval Logic Tests
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_needs_approval_logic():
    """Verify which restore types need approval."""
    from app.api.restore_approval import needs_approval

    # Mass recovery always needs approval
    assert needs_approval(RestoreType.MASS_RECOVERY) is True
    # Cross-user always needs approval
    assert needs_approval(RestoreType.CROSS_USER) is True
    # Cross-tenant always needs approval
    assert needs_approval(RestoreType.CROSS_TENANT) is True
    # Regular full_inplace does NOT need approval
    assert needs_approval(RestoreType.FULL_INPLACE) is False
    # Item-level does NOT need approval
    assert needs_approval(RestoreType.ITEM_LEVEL) is False
    # But Entra ID always needs approval
    assert needs_approval(RestoreType.ITEM_LEVEL, is_entra_id=True) is True
    assert needs_approval(RestoreType.FULL_INPLACE, is_entra_id=True) is True


# ═══════════════════════════════════════════════════════
# P1: RBAC Access Control Matrix
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_viewer_blocked_from_approvals(viewer_client: AsyncClient):
    """VIEWER cannot access approval endpoints."""
    response = await viewer_client.get("/api/restore-approvals/pending")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_operator_blocked_from_approvals(operator_client: AsyncClient):
    """Regular OPERATOR cannot access approval endpoints."""
    response = await operator_client.get("/api/restore-approvals/pending")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_restore_operator_can_access_approvals(restore_operator_client: AsyncClient):
    """RESTORE_OPERATOR can access approval endpoints."""
    response = await restore_operator_client.get("/api/restore-approvals/pending")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mass_restore_blocked_for_viewer(viewer_client: AsyncClient):
    """VIEWER cannot trigger mass restore."""
    response = await viewer_client.post("/api/recovery/mass-restore", json={
        "tenant_id": 1, "dry_run": True,
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mass_restore_blocked_for_operator(operator_client: AsyncClient):
    """Regular OPERATOR cannot trigger mass restore."""
    response = await operator_client.post("/api/recovery/mass-restore", json={
        "tenant_id": 1, "dry_run": True,
    })
    assert response.status_code == 403
