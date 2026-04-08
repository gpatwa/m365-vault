"""Comprehensive data accuracy tests for every sidebar page's API endpoint.

Seeds exact data into the database and verifies exact values returned from each
API endpoint — ensuring the frontend displays correct numbers for every page.
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.backup_job import BackupJob, JobStatus
from app.models.sla_policy import SLAPolicy
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.health_baseline import HealthBaseline, AnomalyEvent
from app.models.alert_config import TenantAlertConfig
from app.models.audit_log import AuditLog
from app.models.user_tenant import UserTenant
from app.models.tenant_workload_app import TenantWorkloadApp, WorkloadLifecycle
from app.models.user import User

# ── Helpers ─────────────────────────────────────────────────


async def seed_test_tenant(db, name="Data Test", ms_tenant_id="data-001"):
    """Create and return an ACTIVE test tenant."""
    t = Tenant(
        name=name,
        ms_tenant_id=ms_tenant_id,
        client_id="x",
        client_secret_encrypted="x",
        status=TenantStatus.ACTIVE,
    )
    db.add(t)
    await db.flush()
    return t


async def assign_auth_user_to_tenant(db, tenant_id):
    """Grant the 'testadmin' user (created by auth_client fixture) access to a tenant."""
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.username == "testadmin"))
    user = result.scalar_one_or_none()
    if user:
        ut = UserTenant(user_id=user.id, tenant_id=tenant_id, role="owner")
        db.add(ut)
        await db.flush()
        return user
    return None


async def seed_workload_app(db, tenant_id, workload, lifecycle="enabled"):
    """Create a TenantWorkloadApp record to mark a workload as enabled."""
    app = TenantWorkloadApp(
        tenant_id=tenant_id,
        workload=workload,
        client_id="test-client",
        client_secret_encrypted="test-secret",
        consent_status="consented",
        lifecycle_status=lifecycle,
        enabled=1,
    )
    db.add(app)
    await db.flush()
    return app


async def seed_protected_object(
    db, tenant_id, workload_type, display_name, status=ProtectionStatus.UNPROTECTED,
    email=None, sla_policy_id=None, last_backup_at=None, last_backup_status=None,
):
    """Create a ProtectedObject with specified attributes."""
    obj = ProtectedObject(
        tenant_id=tenant_id,
        workload_type=workload_type,
        ms_object_id=f"ms-{display_name.lower().replace(' ', '-')}",
        display_name=display_name,
        email=email,
        status=status,
        sla_policy_id=sla_policy_id,
        last_backup_at=last_backup_at,
        last_backup_status=last_backup_status,
    )
    db.add(obj)
    await db.flush()
    return obj


# ═══════════════════════════════════════════════════════════
# 1. Dashboard Summary — Exact Counts
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_summary_exact_counts(auth_client: AsyncClient):
    """Seed 5 Exchange (3 protected, 2 unprotected) + 2 Entra ID (both protected),
    2 backup jobs (1 completed, 1 failed), and verify exact response values."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db)
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        # Enable workloads so dashboard counts them
        await seed_workload_app(db, tid, "exchange", lifecycle="enabled")
        await seed_workload_app(db, tid, "entra_id", lifecycle="enabled")

        # 5 Exchange objects: 3 protected, 2 unprotected
        for i in range(3):
            await seed_protected_object(
                db, tid, WorkloadType.EXCHANGE, f"Mailbox P{i+1}",
                status=ProtectionStatus.PROTECTED, email=f"p{i+1}@test.com",
            )
        for i in range(2):
            await seed_protected_object(
                db, tid, WorkloadType.EXCHANGE, f"Mailbox U{i+1}",
                status=ProtectionStatus.UNPROTECTED, email=f"u{i+1}@test.com",
            )

        # 2 Entra ID objects: both protected
        for i in range(2):
            await seed_protected_object(
                db, tid, WorkloadType.ENTRA_ID, f"Entra Obj {i+1}",
                status=ProtectionStatus.PROTECTED,
            )

        # 2 backup jobs in last 24h: 1 COMPLETED, 1 FAILED
        now = datetime.utcnow()
        db.add(BackupJob(
            tenant_id=tid, workload_type="exchange", status=JobStatus.COMPLETED,
            created_at=now - timedelta(hours=2), completed_at=now - timedelta(hours=1),
            objects_total=3, objects_processed=3, objects_failed=0,
        ))
        db.add(BackupJob(
            tenant_id=tid, workload_type="exchange", status=JobStatus.FAILED,
            created_at=now - timedelta(hours=1),
            objects_total=2, objects_processed=0, objects_failed=2,
            error_message="Graph API timeout",
        ))

        await db.commit()

    resp = await auth_client.get(f"/api/dashboard/summary?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_objects"] == 7
    assert data["total_protected"] == 5
    assert data["protection_rate"] == 71.4

    # Exchange breakdown
    ex = data["workloads"]["exchange"]
    assert ex["total"] == 5
    assert ex["protected"] == 3
    assert ex["unprotected"] == 2

    # Entra ID breakdown
    eid = data["workloads"]["entra_id"]
    assert eid["total"] == 2
    assert eid["protected"] == 2

    # Job stats (last 24h)
    jobs = data["jobs_24h"]
    assert jobs["backup_total"] == 2
    assert jobs["backup_successful"] == 1
    assert jobs["backup_failed"] == 1


# ═══════════════════════════════════════════════════════════
# 2. Dashboard Compliance — SLA Adherence
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_compliance_accuracy(auth_client: AsyncClient):
    """Seed 3 protected objects with varying backup recency against 1h SLA.
    Verify compliant vs non-compliant classification."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Compliance Test", ms_tenant_id="comp-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        # Create 1h SLA
        sla = SLAPolicy(
            name="Hourly SLA Test",
            backup_frequency_hours=1,
            retention_days=90,
            priority=1,
        )
        db.add(sla)
        await db.flush()
        sla_id = sla.id

        now = datetime.utcnow()

        # Object 1: backed up now — compliant
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Recent Backup",
            status=ProtectionStatus.PROTECTED, sla_policy_id=sla_id,
            last_backup_at=now,
        )

        # Object 2: backed up 3 hours ago — overdue (SLA is 1h)
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Overdue Backup",
            status=ProtectionStatus.PROTECTED, sla_policy_id=sla_id,
            last_backup_at=now - timedelta(hours=3),
        )

        # Object 3: just created, no backup yet — within grace period (created_at is now)
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "New Object",
            status=ProtectionStatus.PROTECTED, sla_policy_id=sla_id,
        )

        await db.commit()

    resp = await auth_client.get(f"/api/dashboard/compliance?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    # compliant = object 1 (recent backup) + object 3 (grace period)
    assert data["compliant"] == 2
    # non_compliant = object 2 (3h overdue on 1h SLA)
    assert data["non_compliant"] == 1
    assert data["total"] == 3
    assert data["pending_first_backup"] == 1


# ═══════════════════════════════════════════════════════════
# 3. Dashboard Unprotected — At-Risk Items
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_unprotected_accuracy(auth_client: AsyncClient):
    """Seed 2 UNPROTECTED objects + 1 PROTECTED (with SLA) that has a failed backup.
    Verify total_unprotected=2 and total_at_risk=1."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Unprotected Test", ms_tenant_id="unprot-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        # Create an SLA so the protected object has a policy assigned
        sla = SLAPolicy(
            name="Unprot Test SLA", backup_frequency_hours=24,
            retention_days=30, priority=5,
        )
        db.add(sla)
        await db.flush()

        # 2 unprotected
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Unprotected Box 1",
            status=ProtectionStatus.UNPROTECTED,
        )
        await seed_protected_object(
            db, tid, WorkloadType.ONEDRIVE, "Unprotected Drive 1",
            status=ProtectionStatus.UNPROTECTED,
        )

        # 1 protected WITH SLA, but last backup failed (at-risk)
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Failed Backup Box",
            status=ProtectionStatus.PROTECTED, sla_policy_id=sla.id,
            last_backup_status="failed",
        )

        await db.commit()

    resp = await auth_client.get(f"/api/dashboard/unprotected?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_unprotected"] == 2
    assert data["total_at_risk"] == 1


# ═══════════════════════════════════════════════════════════
# 4. Exchange List — Exact Objects
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_exchange_list_exact_objects(auth_client: AsyncClient):
    """Seed 3 Exchange objects, verify the list endpoint returns them."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Exchange Test", ms_tenant_id="exch-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        names = ["Alice Inbox", "Bob Inbox", "Carol Inbox"]
        for name in names:
            await seed_protected_object(
                db, tid, WorkloadType.EXCHANGE, name,
                email=f"{name.split()[0].lower()}@test.com",
            )

        await db.commit()

    resp = await auth_client.get(f"/api/exchange/mailboxes?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 3
    returned_names = {item["display_name"] for item in data["items"]}
    assert returned_names == set(names)


# ═══════════════════════════════════════════════════════════
# 5. SLA Policies — List Accuracy
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sla_policies_list_accuracy(auth_client: AsyncClient):
    """Seed 2 SLA policies (hourly and daily), verify list returns exact values."""
    async with async_session() as db:
        sla1 = SLAPolicy(
            name="Accuracy Hourly",
            backup_frequency_hours=1,
            retention_days=90,
            priority=1,
        )
        sla2 = SLAPolicy(
            name="Accuracy Daily",
            backup_frequency_hours=24,
            retention_days=30,
            priority=5,
        )
        db.add(sla1)
        db.add(sla2)
        await db.commit()

    resp = await auth_client.get("/api/sla-policies/")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    policies = {p["name"]: p for p in data}

    assert policies["Accuracy Hourly"]["backup_frequency_hours"] == 1
    assert policies["Accuracy Hourly"]["retention_days"] == 90

    assert policies["Accuracy Daily"]["backup_frequency_hours"] == 24
    assert policies["Accuracy Daily"]["retention_days"] == 30


# ═══════════════════════════════════════════════════════════
# 6. Alerts — Tenant Defaults (No Config)
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_alerts_tenant_defaults(auth_client: AsyncClient):
    """No alert config seeded — verify defaults are returned."""
    resp = await auth_client.get("/api/alerts/tenant?tenant_id=99999")
    assert resp.status_code == 200
    data = resp.json()

    assert data["configured"] is False
    assert "backup_failed" in data["enabled_events"]
    assert "anomaly_detected" in data["enabled_events"]
    assert "protection_gap" in data["enabled_events"]
    assert data["frequency"] == "immediate"
    assert data["email_recipients"] == ""


# ═══════════════════════════════════════════════════════════
# 7. Alerts — Tenant Custom Config
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_alerts_tenant_custom_config(auth_client: AsyncClient):
    """Seed a TenantAlertConfig and verify the API returns its values."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Alert Config Test", ms_tenant_id="alert-cfg-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        config = TenantAlertConfig(
            tenant_id=tid,
            email_recipients="ops@test.com",
            webhook_url="https://hooks.test.com/alert",
            enabled_events=json.dumps(["backup_failed"]),
            frequency="hourly",
            quiet_start_hour=22,
            quiet_end_hour=6,
        )
        db.add(config)
        await db.commit()

    resp = await auth_client.get(f"/api/alerts/tenant?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["configured"] is True
    assert data["email_recipients"] == "ops@test.com"
    assert data["webhook_url"] == "https://hooks.test.com/alert"
    assert data["enabled_events"] == ["backup_failed"]
    assert data["frequency"] == "hourly"
    assert data["quiet_start_hour"] == 22
    assert data["quiet_end_hour"] == 6


# ═══════════════════════════════════════════════════════════
# 8. Jobs — Backup List Accuracy
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_jobs_list_accuracy(auth_client: AsyncClient):
    """Seed 3 backup jobs with different statuses, verify list returns them."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Jobs Test", ms_tenant_id="jobs-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        now = datetime.utcnow()
        statuses = [JobStatus.QUEUED, JobStatus.COMPLETED, JobStatus.FAILED]
        for i, status in enumerate(statuses):
            db.add(BackupJob(
                tenant_id=tid,
                workload_type="exchange",
                status=status,
                created_at=now - timedelta(hours=i),
                objects_total=10,
                objects_processed=10 if status == JobStatus.COMPLETED else 0,
                objects_failed=10 if status == JobStatus.FAILED else 0,
            ))

        await db.commit()

    resp = await auth_client.get(f"/api/jobs/backup?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 3
    returned_statuses = {item["status"] for item in data["items"]}
    assert returned_statuses == {"queued", "completed", "failed"}


# ═══════════════════════════════════════════════════════════
# 9. Billing Config — Structure Verification
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_billing_config_structure(auth_client: AsyncClient):
    """Verify billing config returns expected structure with tier keys."""
    resp = await auth_client.get("/api/billing/config")
    assert resp.status_code == 200
    data = resp.json()

    assert "prices" in data
    prices = data["prices"]
    assert "professional" in prices
    assert "business" in prices
    assert "enterprise" in prices
    assert "trial_days" in data


# ═══════════════════════════════════════════════════════════
# 10. Feature Flags — Accuracy
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_feature_flags_accuracy(auth_client: AsyncClient):
    """Verify feature flags endpoint returns tier, features dict, and limits."""
    resp = await auth_client.get("/api/features")
    assert resp.status_code == 200
    data = resp.json()

    assert "tier" in data
    assert "features" in data
    assert "limits" in data
    assert isinstance(data["features"], dict)
    # Default tier from config is 'community' (unless LICENSE_TIER env var is set)
    assert data["tier"] == "community"


# ═══════════════════════════════════════════════════════════
# 11. Audit Log — Action Tracking
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_log_accuracy(auth_client: AsyncClient):
    """Create an SLA policy (which writes an audit log), verify the log appears."""
    # Create an SLA policy — the create_tenant endpoint writes audit logs
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Audit Test", ms_tenant_id="audit-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)
        await db.commit()

    # Creating a tenant via API produces an audit log entry
    resp = await auth_client.post("/api/tenants/", json={
        "name": "Audit Tenant",
        "ms_tenant_id": "audit-tenant-001",
        "client_id": "audit-cid",
        "client_secret": "audit-secret",
    })
    assert resp.status_code == 200

    # Check audit logs
    resp = await auth_client.get("/api/audit/logs")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] >= 1
    actions = [item["action"] for item in data["items"]]
    assert "tenant.created" in actions

    # Verify the tenant.created log has correct resource_type
    tenant_logs = [item for item in data["items"] if item["action"] == "tenant.created"]
    assert len(tenant_logs) >= 1
    assert tenant_logs[0]["resource_type"] == "tenant"


# ═══════════════════════════════════════════════════════════
# 12. Cross-Tenant Data Isolation
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cross_tenant_data_isolation(auth_client: AsyncClient):
    """Create 2 tenants with different object counts.
    Verify dashboard summary scoped to tenant A only shows tenant A's objects."""
    async with async_session() as db:
        tenant_a = await seed_test_tenant(db, name="Tenant A", ms_tenant_id="iso-a-001")
        tenant_b = await seed_test_tenant(db, name="Tenant B", ms_tenant_id="iso-b-001")
        tid_a = tenant_a.id
        tid_b = tenant_b.id

        # Assign user to BOTH tenants
        await assign_auth_user_to_tenant(db, tid_a)
        user_result = await db.execute(
            __import__("sqlalchemy").select(User).where(User.username == "testadmin")
        )
        user = user_result.scalar_one()
        ut_b = UserTenant(user_id=user.id, tenant_id=tid_b, role="member")
        db.add(ut_b)

        # Enable exchange workload for both tenants
        await seed_workload_app(db, tid_a, "exchange", lifecycle="enabled")
        await seed_workload_app(db, tid_b, "exchange", lifecycle="enabled")

        # Tenant A: 5 Exchange objects (3 protected, 2 unprotected)
        for i in range(3):
            await seed_protected_object(
                db, tid_a, WorkloadType.EXCHANGE, f"A-Protected-{i}",
                status=ProtectionStatus.PROTECTED,
            )
        for i in range(2):
            await seed_protected_object(
                db, tid_a, WorkloadType.EXCHANGE, f"A-Unprotected-{i}",
                status=ProtectionStatus.UNPROTECTED,
            )

        # Tenant B: 3 Exchange objects (all protected)
        for i in range(3):
            await seed_protected_object(
                db, tid_b, WorkloadType.EXCHANGE, f"B-Protected-{i}",
                status=ProtectionStatus.PROTECTED,
            )

        await db.commit()

    # Query scoped to tenant A only
    resp = await auth_client.get(f"/api/dashboard/summary?tenant_id={tid_a}")
    assert resp.status_code == 200
    data = resp.json()

    # Must show only tenant A's objects
    assert data["total_objects"] == 5
    assert data["total_protected"] == 3

    # Query scoped to tenant B
    resp_b = await auth_client.get(f"/api/dashboard/summary?tenant_id={tid_b}")
    assert resp_b.status_code == 200
    data_b = resp_b.json()

    assert data_b["total_objects"] == 3
    assert data_b["total_protected"] == 3


# ═══════════════════════════════════════════════════════════
# 13. Organization Tenant Counts
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_organization_tenant_counts(auth_client: AsyncClient):
    """Seed a tenant with specific mailbox/onedrive/site counts,
    verify the /api/tenants/ response includes them."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Org Count Test", ms_tenant_id="org-cnt-001")
        tenant.total_mailboxes = 10
        tenant.total_onedrives = 5
        tenant.total_sites = 3
        tenant.total_teams = 2
        tenant.total_entra_objects = 1
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)
        await db.commit()

    resp = await auth_client.get("/api/tenants/")
    assert resp.status_code == 200
    data = resp.json()

    # Find our tenant in the list
    tenant_data = next((t for t in data if t["ms_tenant_id"] == "org-cnt-001"), None)
    assert tenant_data is not None
    assert tenant_data["total_mailboxes"] == 10
    assert tenant_data["total_onedrives"] == 5
    assert tenant_data["total_sites"] == 3
    assert tenant_data["total_teams"] == 2
    assert tenant_data["total_entra_objects"] == 1


# ═══════════════════════════════════════════════════════════
# 14. Smart Engine — Health Score for New Tenant
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smart_engine_health_score_new_tenant(auth_client: AsyncClient):
    """New tenant with no jobs and no snapshots should get a default health score.
    Formula: success_rate=100 (no failures), sla=100 (no protected objects),
    anomaly=100 (no active anomalies), storage=50 (no jobs).
    Weighted: 100*0.4 + 100*0.3 + 100*0.2 + 50*0.1 = 95."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Health Test", ms_tenant_id="health-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)
        await db.commit()

    resp = await auth_client.get(f"/api/health/score?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert "score" in data
    assert "components" in data
    # New tenant: no jobs → success_rate=100, sla=100, anomaly=100, storage=50
    assert data["score"] == 95
    assert data["components"]["success_rate"] == 100
    assert data["components"]["sla_adherence"] == 100
    assert data["components"]["anomaly_score"] == 100
    assert data["components"]["storage_score"] == 50

    assert data["details"]["total_jobs_7d"] == 0
    assert data["details"]["protected_objects"] == 0
    assert data["details"]["active_anomalies"] == 0


# ═══════════════════════════════════════════════════════════
# 15. Health Score — With Failed Jobs
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_score_with_failures(auth_client: AsyncClient):
    """Seed a tenant with 4 completed and 1 failed job (80% success rate).
    Verify the health score reflects the degraded success component."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Health Fail Test", ms_tenant_id="health-fail-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        now = datetime.utcnow()

        # 4 completed jobs
        for i in range(4):
            db.add(BackupJob(
                tenant_id=tid, workload_type="exchange", status=JobStatus.COMPLETED,
                created_at=now - timedelta(hours=i+1),
                completed_at=now - timedelta(hours=i),
                objects_total=5, objects_processed=5, objects_failed=0,
            ))

        # 1 failed job
        db.add(BackupJob(
            tenant_id=tid, workload_type="exchange", status=JobStatus.FAILED,
            created_at=now - timedelta(hours=5),
            completed_at=now - timedelta(hours=4),
            objects_total=5, objects_processed=0, objects_failed=5,
        ))

        await db.commit()

    resp = await auth_client.get(f"/api/health/score?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    # success_rate: 4/5 completed = 80%
    assert data["components"]["success_rate"] == 80.0
    assert data["details"]["total_jobs_7d"] == 5
    assert data["details"]["completed_jobs_7d"] == 4


# ═══════════════════════════════════════════════════════════
# 16. Dashboard Summary — Empty Tenant
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_summary_empty_tenant(auth_client: AsyncClient):
    """Brand new tenant with zero objects should return all zeroes."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Empty Test", ms_tenant_id="empty-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)
        await db.commit()

    resp = await auth_client.get(f"/api/dashboard/summary?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_objects"] == 0
    assert data["total_protected"] == 0
    assert data["protection_rate"] == 0
    assert data["jobs_24h"]["backup_total"] == 0
    assert data["jobs_24h"]["backup_failed"] == 0


# ═══════════════════════════════════════════════════════════
# 17. SLA Quick Protect — Verify Assignment
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sla_quick_protect_accuracy(auth_client: AsyncClient):
    """Use quick-protect to assign SLA to all Exchange objects, verify status changes."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Quick Protect", ms_tenant_id="qp-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        # 3 unprotected Exchange objects
        for i in range(3):
            await seed_protected_object(
                db, tid, WorkloadType.EXCHANGE, f"QP Mailbox {i+1}",
                status=ProtectionStatus.UNPROTECTED,
            )
        await db.commit()

    # Quick protect all exchange objects
    resp = await auth_client.post("/api/sla-policies/quick-protect", json={
        "tenant_id": tid,
        "workload_types": ["exchange"],
        "frequency_hours": 12,
        "retention_days": 60,
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "protected"
    assert data["total_protected"] == 3
    assert data["workloads"]["exchange"] == 3

    # Verify via dashboard that they are now protected
    resp2 = await auth_client.get(f"/api/dashboard/unprotected?tenant_id={tid}")
    assert resp2.status_code == 200
    assert resp2.json()["total_unprotected"] == 0


# ═══════════════════════════════════════════════════════════
# 18. Audit Log — Filtered by Action
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_log_filter_by_action(auth_client: AsyncClient):
    """Seed audit entries directly and verify filtering works."""
    async with async_session() as db:
        now = datetime.utcnow()
        db.add(AuditLog(
            action="backup.completed", resource_type="backup_job",
            resource_id=1, details="Exchange backup completed",
            severity="info", timestamp=now,
        ))
        db.add(AuditLog(
            action="backup.failed", resource_type="backup_job",
            resource_id=2, details="Exchange backup failed",
            severity="error", timestamp=now - timedelta(minutes=5),
        ))
        db.add(AuditLog(
            action="tenant.created", resource_type="tenant",
            resource_id=1, details="Test tenant created",
            severity="info", timestamp=now - timedelta(minutes=10),
        ))
        await db.commit()

    # Filter by action
    resp = await auth_client.get("/api/audit/logs?action=backup")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] >= 2
    for item in data["items"]:
        assert "backup" in item["action"]

    # Filter by severity
    resp2 = await auth_client.get("/api/audit/logs?severity=error")
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["total"] >= 1
    for item in data2["items"]:
        assert item["severity"] == "error"


# ═══════════════════════════════════════════════════════════
# 19. Jobs — Filter by Status
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_jobs_filter_by_status(auth_client: AsyncClient):
    """Verify jobs can be filtered by status parameter."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Job Filter Test", ms_tenant_id="jfilt-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        now = datetime.utcnow()
        # 2 completed + 1 failed
        for i in range(2):
            db.add(BackupJob(
                tenant_id=tid, workload_type="exchange", status=JobStatus.COMPLETED,
                created_at=now - timedelta(hours=i+1),
                completed_at=now - timedelta(hours=i),
                objects_total=5, objects_processed=5, objects_failed=0,
            ))
        db.add(BackupJob(
            tenant_id=tid, workload_type="exchange", status=JobStatus.FAILED,
            created_at=now - timedelta(hours=3),
            objects_total=5, objects_processed=0, objects_failed=5,
        ))
        await db.commit()

    # Filter completed only
    resp = await auth_client.get(f"/api/jobs/backup?tenant_id={tid}&status=completed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(item["status"] == "completed" for item in data["items"])

    # Filter failed only
    resp2 = await auth_client.get(f"/api/jobs/backup?tenant_id={tid}&status=failed")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["status"] == "failed"


# ═══════════════════════════════════════════════════════════
# 20. Viewer Role — Read Access
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_viewer_can_read_dashboard(auth_client: AsyncClient, viewer_client: AsyncClient):
    """Viewer should be able to read dashboard summary."""
    resp = await viewer_client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_objects" in data


@pytest.mark.asyncio
async def test_viewer_cannot_create_sla(viewer_client: AsyncClient):
    """Viewer should NOT be able to create SLA policies (admin-only)."""
    resp = await viewer_client.post("/api/sla-policies/", json={
        "name": "Viewer Attempt",
        "backup_frequency_hours": 24,
        "retention_days": 30,
    })
    assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════
# 21. Dashboard Protection Rate Rounding
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_protection_rate_rounding(auth_client: AsyncClient):
    """Verify protection rate is rounded to 1 decimal place."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Rate Round", ms_tenant_id="rate-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)
        await seed_workload_app(db, tid, "exchange", lifecycle="enabled")

        # 3 objects: 1 protected, 2 unprotected = 33.3%
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Protected One",
            status=ProtectionStatus.PROTECTED,
        )
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Unprotected One",
            status=ProtectionStatus.UNPROTECTED,
        )
        await seed_protected_object(
            db, tid, WorkloadType.EXCHANGE, "Unprotected Two",
            status=ProtectionStatus.UNPROTECTED,
        )
        await db.commit()

    resp = await auth_client.get(f"/api/dashboard/summary?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["protection_rate"] == 33.3
    assert data["workloads"]["exchange"]["protection_rate"] == 33.3


# ═══════════════════════════════════════════════════════════
# 22. Health Anomalies Endpoint
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_anomalies_accuracy(auth_client: AsyncClient):
    """Seed anomaly events and verify the anomalies endpoint returns them."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Anomaly Test", ms_tenant_id="anomaly-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)

        now = datetime.utcnow()
        db.add(AnomalyEvent(
            tenant_id=tid, workload_type="exchange", metric_name="item_count",
            expected_value=100.0, actual_value=500.0, z_score=4.5,
            severity="critical", message="Item count spike", resolved=0,
            detected_at=now,
        ))
        db.add(AnomalyEvent(
            tenant_id=tid, workload_type="exchange", metric_name="size_bytes",
            expected_value=1000.0, actual_value=200.0, z_score=3.2,
            severity="warning", message="Size drop", resolved=1,
            detected_at=now - timedelta(hours=1),
        ))
        await db.commit()

    # Active only (default)
    resp = await auth_client.get(f"/api/health/anomalies?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 1
    assert data["items"][0]["severity"] == "critical"
    assert data["items"][0]["z_score"] == 4.5

    # All anomalies (including resolved)
    resp2 = await auth_client.get(f"/api/health/anomalies?tenant_id={tid}&active_only=false")
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["total"] == 2


# ═══════════════════════════════════════════════════════════
# 23. Feature Flags — Check Individual Feature
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_feature_flag_check_individual(auth_client: AsyncClient):
    """Verify individual feature check endpoint returns expected structure."""
    resp = await auth_client.get("/api/features/check/msp_dashboard")
    assert resp.status_code == 200
    data = resp.json()

    assert data["feature"] == "msp_dashboard"
    assert "enabled" in data
    assert isinstance(data["enabled"], bool)
    assert data["tier"] == "community"


# ═══════════════════════════════════════════════════════════
# 24. Compliance Rate Calculation Edge Case
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_compliance_empty_returns_100(auth_client: AsyncClient):
    """Tenant with no protected objects should show 100% compliance."""
    async with async_session() as db:
        tenant = await seed_test_tenant(db, name="Empty Compliance", ms_tenant_id="emptycomp-001")
        tid = tenant.id
        await assign_auth_user_to_tenant(db, tid)
        await db.commit()

    resp = await auth_client.get(f"/api/dashboard/compliance?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 0
    assert data["compliance_rate"] == 100


# ═══════════════════════════════════════════════════════════
# 25. Dashboard Activity — 7-Day History
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_activity_history(auth_client: AsyncClient):
    """Verify dashboard activity endpoint returns the correct number of days."""
    resp = await auth_client.get("/api/dashboard/activity?days=3")
    assert resp.status_code == 200
    data = resp.json()

    assert "activity" in data
    assert len(data["activity"]) == 3
    # Each day entry should have expected fields
    for day in data["activity"]:
        assert "date" in day
        assert "backups" in day
        assert "restores" in day
        assert "data_backed_up_bytes" in day
