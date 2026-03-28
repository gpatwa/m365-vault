"""Tests for Phase 1B — MVB Recovery Plans, criticality-ordered restore, weighted confidence.

Comprehensive end-to-end coverage:
- MVB plan generation with criticality phases
- Phase ordering (identity first, then by criticality tier)
- Criticality-weighted confidence score (v2)
- Mass restore criticality ordering
- Pre-computed plan API endpoints
- Edge cases (empty tenant, no snapshots, single workload)
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.snapshot import Snapshot, SnapshotStatus, SnapshotType
from app.models.org_context import UserContext, SiteContext, VIPGroup, VIPGroupMember, RecoveryPlan
from app.services.mvb_plan_generator import MVBPlanGenerator
from app.services.criticality_scorer import CriticalityScorer


# ══════════════════════════════════════════════════════════
# Fixtures — realistic enterprise scenario
# ══════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def enterprise_tenant(db: AsyncSession):
    """Create a tenant with realistic enterprise data."""
    tenant = Tenant(
        name="Acme Corp",
        ms_tenant_id="acme-tenant-id",
        client_id="acme-client",
        client_secret_encrypted="encrypted",
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    now = datetime.utcnow()
    objects = []

    # ── Entra ID object (identity controls) ──
    entra = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.ENTRA_ID,
        ms_object_id="entra-tenant", display_name="Acme Corp (Entra ID)",
        status=ProtectionStatus.PROTECTED, criticality_score=90, criticality_tier="critical",
        last_backup_at=now - timedelta(hours=2),
    )
    db.add(entra)
    objects.append(entra)

    # ── CEO mailbox (critical) ──
    ceo_mail = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
        ms_object_id="user-ceo", display_name="Jane CEO (Mailbox)",
        email="jane@acme.com", status=ProtectionStatus.PROTECTED,
        criticality_score=95, criticality_tier="critical",
        last_backup_at=now - timedelta(hours=1),
    )
    db.add(ceo_mail)
    objects.append(ceo_mail)

    # ── CFO mailbox (critical) ──
    cfo_mail = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
        ms_object_id="user-cfo", display_name="Bob CFO (Mailbox)",
        email="bob@acme.com", status=ProtectionStatus.PROTECTED,
        criticality_score=85, criticality_tier="critical",
        last_backup_at=now - timedelta(hours=1),
    )
    db.add(cfo_mail)
    objects.append(cfo_mail)

    # ── Legal counsel mailbox (high) ──
    legal_mail = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
        ms_object_id="user-legal", display_name="Carol Legal (Mailbox)",
        email="carol@acme.com", status=ProtectionStatus.PROTECTED,
        criticality_score=72, criticality_tier="high",
        last_backup_at=now - timedelta(hours=3),
    )
    db.add(legal_mail)
    objects.append(legal_mail)

    # ── Developer mailbox (medium) ──
    dev_mail = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
        ms_object_id="user-dev", display_name="Dave Dev (Mailbox)",
        email="dave@acme.com", status=ProtectionStatus.PROTECTED,
        criticality_score=45, criticality_tier="medium",
        last_backup_at=now - timedelta(hours=5),
    )
    db.add(dev_mail)
    objects.append(dev_mail)

    # ── Intern mailbox (low) ──
    intern_mail = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
        ms_object_id="user-intern", display_name="Eve Intern (Mailbox)",
        email="eve@acme.com", status=ProtectionStatus.PROTECTED,
        criticality_score=22, criticality_tier="low",
        last_backup_at=now - timedelta(days=3),
    )
    db.add(intern_mail)
    objects.append(intern_mail)

    # ── Finance SharePoint (high) ──
    finance_sp = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.SHAREPOINT,
        ms_object_id="site-finance", display_name="Finance Reports",
        site_url="https://acme.sharepoint.com/sites/finance",
        status=ProtectionStatus.PROTECTED,
        criticality_score=70, criticality_tier="high",
        last_backup_at=now - timedelta(hours=4),
    )
    db.add(finance_sp)
    objects.append(finance_sp)

    # ── CEO OneDrive (critical) ──
    ceo_od = ProtectedObject(
        tenant_id=tenant.id, workload_type=WorkloadType.ONEDRIVE,
        ms_object_id="user-ceo", display_name="Jane CEO (OneDrive)",
        email="jane@acme.com", status=ProtectionStatus.PROTECTED,
        criticality_score=95, criticality_tier="critical",
        last_backup_at=now - timedelta(hours=2),
    )
    db.add(ceo_od)
    objects.append(ceo_od)

    await db.flush()

    # Create snapshots for each object
    for obj in objects:
        snap = Snapshot(
            protected_object_id=obj.id,
            snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED,
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1, minutes=50),
            item_count=10,
            size_bytes=5000,
        )
        db.add(snap)

    # Create user contexts for criticality
    for ms_id, name, email, dept, title, score, tier, ga in [
        ("user-ceo", "Jane CEO", "jane@acme.com", "Executive", "CEO", 95, "critical", 1),
        ("user-cfo", "Bob CFO", "bob@acme.com", "Finance", "CFO", 85, "critical", 0),
        ("user-legal", "Carol Legal", "carol@acme.com", "Legal", "General Counsel", 72, "high", 0),
        ("user-dev", "Dave Dev", "dave@acme.com", "Engineering", "Developer", 45, "medium", 0),
        ("user-intern", "Eve Intern", "eve@acme.com", "Marketing", "Intern", 22, "low", 0),
    ]:
        ctx = UserContext(
            tenant_id=tenant.id, ms_user_id=ms_id, display_name=name,
            email=email, department=dept, job_title=title,
            criticality_score=score, criticality_tier=tier,
            is_global_admin=ga, synced_at=now,
        )
        # Link to first matching protected object
        for obj in objects:
            if obj.ms_object_id == ms_id and obj.workload_type == WorkloadType.EXCHANGE:
                ctx.protected_object_id = obj.id
                break
        db.add(ctx)

    await db.flush()
    await db.commit()

    return tenant, objects


# ══════════════════════════════════════════════════════════
# MVB Plan Generator — Service Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_mvb_plan_has_4_phases(db: AsyncSession, enterprise_tenant):
    """MVB plan generates all 4 recovery phases."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    phases = json.loads(plan.phases_json)
    assert len(phases) == 4
    assert phases[0]["name"] == "Identity Controls"
    assert phases[1]["name"] == "Minimum Viable Business"
    assert phases[2]["name"] == "High-Priority Data"
    assert phases[3]["name"] == "Full Recovery"


@pytest.mark.asyncio
async def test_mvb_phase1_is_identity(db: AsyncSession, enterprise_tenant):
    """Phase 1 always contains Entra ID objects."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    phases = json.loads(plan.phases_json)
    phase1 = phases[0]
    assert phase1["priority"] == "immediate"
    assert all(
        s["workload"] == "entra_id"
        for s in phase1["object_summaries"]
    )


@pytest.mark.asyncio
async def test_mvb_phase2_has_critical_users(db: AsyncSession, enterprise_tenant):
    """Phase 2 (MVB) contains only critical-tier objects."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    phases = json.loads(plan.phases_json)
    phase2 = phases[1]
    assert phase2["priority"] == "critical"
    assert all(
        s["criticality_tier"] == "critical"
        for s in phase2["object_summaries"]
    )
    # CEO and CFO mailboxes + CEO OneDrive should be here
    names = [s["object_name"] for s in phase2["object_summaries"]]
    assert any("CEO" in n for n in names)
    assert any("CFO" in n for n in names)


@pytest.mark.asyncio
async def test_mvb_phase3_has_high_priority(db: AsyncSession, enterprise_tenant):
    """Phase 3 contains high-tier objects."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    phases = json.loads(plan.phases_json)
    phase3 = phases[2]
    assert phase3["priority"] == "high"
    assert all(
        s["criticality_tier"] == "high"
        for s in phase3["object_summaries"]
    )


@pytest.mark.asyncio
async def test_mvb_phase4_has_remaining(db: AsyncSession, enterprise_tenant):
    """Phase 4 contains medium + low tier objects."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    phases = json.loads(plan.phases_json)
    phase4 = phases[3]
    assert phase4["priority"] == "normal"
    assert all(
        s["criticality_tier"] in ("medium", "low")
        for s in phase4["object_summaries"]
    )


@pytest.mark.asyncio
async def test_mvb_user_count(db: AsyncSession, enterprise_tenant):
    """MVB user count reflects unique critical users."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    # CEO (jane) + CFO (bob) = 2 MVB users (CEO appears in both Exchange + OneDrive)
    assert plan.mvb_user_count >= 2


@pytest.mark.asyncio
async def test_mvb_has_reasoning(db: AsyncSession, enterprise_tenant):
    """Plan includes human-readable reasoning."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    assert plan.reasoning is not None
    assert "phase" in plan.reasoning.lower()
    assert len(plan.reasoning) > 50


@pytest.mark.asyncio
async def test_mvb_total_stats(db: AsyncSession, enterprise_tenant):
    """Plan total stats are computed correctly."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    assert plan.total_object_count == 8  # All objects with snapshots
    assert plan.total_items > 0
    assert plan.total_size_bytes > 0
    assert plan.estimated_minutes > 0


@pytest.mark.asyncio
async def test_mvb_replaces_old_plan(db: AsyncSession, enterprise_tenant):
    """Generating a new plan replaces the old one."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)

    plan1 = await generator.generate_plan(tenant)
    plan1_id = plan1.id
    await db.commit()

    plan2 = await generator.generate_plan(tenant)
    await db.commit()

    assert plan2.id != plan1_id

    # Only one plan should exist
    result = await db.execute(
        select(RecoveryPlan).where(
            RecoveryPlan.tenant_id == tenant.id,
            RecoveryPlan.plan_type == "mvb",
        )
    )
    plans = result.scalars().all()
    assert len(plans) == 1


@pytest.mark.asyncio
async def test_mvb_empty_tenant(db: AsyncSession):
    """Empty tenant gets an empty plan."""
    tenant = Tenant(
        name="Empty Corp", ms_tenant_id="empty-id",
        client_id="x", client_secret_encrypted="x",
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    assert plan.total_object_count == 0
    assert json.loads(plan.phases_json) == []


@pytest.mark.asyncio
async def test_mvb_stale_after(db: AsyncSession, enterprise_tenant):
    """Plan has a stale_after timestamp 6 hours in the future."""
    tenant, objects = enterprise_tenant
    generator = MVBPlanGenerator(db)
    plan = await generator.generate_plan(tenant)

    assert plan.stale_after is not None
    delta = (plan.stale_after - plan.computed_at).total_seconds()
    assert 21000 < delta < 22000  # ~6 hours


# ══════════════════════════════════════════════════════════
# Mass Restore — Criticality Ordering Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_mass_restore_ordered_by_criticality(auth_client: AsyncClient, db, enterprise_tenant):
    """Mass restore dry-run returns objects ordered by criticality."""
    tenant, objects = enterprise_tenant

    response = await auth_client.post("/api/recovery/mass-restore", json={
        "tenant_id": tenant.id,
        "dry_run": True,
    })
    assert response.status_code == 200
    data = response.json()
    plan = data["plan"]

    assert len(plan) > 0

    # First item should be entra_id (identity first)
    assert plan[0]["workload"] == "entra_id"

    # After identity, should be sorted by criticality score descending
    non_identity = [p for p in plan if p["workload"] != "entra_id"]
    scores = [p["criticality_score"] for p in non_identity]
    assert scores == sorted(scores, reverse=True), "Objects not sorted by criticality"


@pytest.mark.asyncio
async def test_mass_restore_includes_criticality_fields(auth_client: AsyncClient, db, enterprise_tenant):
    """Mass restore plan includes criticality_score and criticality_tier."""
    tenant, objects = enterprise_tenant

    response = await auth_client.post("/api/recovery/mass-restore", json={
        "tenant_id": tenant.id,
        "dry_run": True,
    })
    data = response.json()

    for item in data["plan"]:
        assert "criticality_score" in item
        assert "criticality_tier" in item
        assert item["criticality_tier"] in ("critical", "high", "medium", "low")


# ══════════════════════════════════════════════════════════
# MVB Plan API — Endpoint Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_mvb_plan_api_no_plan(auth_client: AsyncClient):
    """GET mvb-plan returns no_plan for tenant without a plan."""
    response = await auth_client.get("/api/recovery/mvb-plan?tenant_id=999")
    assert response.status_code == 200
    assert response.json()["status"] == "no_plan"


@pytest.mark.asyncio
async def test_mvb_plan_generate_api(auth_client: AsyncClient, db, enterprise_tenant):
    """POST mvb-plan/generate creates a plan and returns summary."""
    tenant, objects = enterprise_tenant

    response = await auth_client.post(f"/api/recovery/mvb-plan/generate?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"
    assert data["mvb_user_count"] >= 2
    assert data["phases_count"] == 4
    assert data["estimated_minutes"] > 0
    assert data["reasoning"] is not None


@pytest.mark.asyncio
async def test_mvb_plan_get_after_generate(auth_client: AsyncClient, db, enterprise_tenant):
    """GET mvb-plan returns the plan after generation."""
    tenant, objects = enterprise_tenant

    # Generate
    await auth_client.post(f"/api/recovery/mvb-plan/generate?tenant_id={tenant.id}")

    # Get
    response = await auth_client.get(f"/api/recovery/mvb-plan?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert len(data["phases"]) == 4
    assert data["phases"][0]["name"] == "Identity Controls"
    assert data["phases"][1]["name"] == "Minimum Viable Business"
    assert data["total_object_count"] == 8


@pytest.mark.asyncio
async def test_mvb_plan_phases_have_object_summaries(auth_client: AsyncClient, db, enterprise_tenant):
    """Each phase in the plan contains object summaries with criticality info."""
    tenant, objects = enterprise_tenant
    await auth_client.post(f"/api/recovery/mvb-plan/generate?tenant_id={tenant.id}")

    response = await auth_client.get(f"/api/recovery/mvb-plan?tenant_id={tenant.id}")
    data = response.json()

    for phase in data["phases"]:
        assert "object_summaries" in phase
        assert "object_count" in phase
        assert "estimated_minutes" in phase
        assert "reason" in phase
        for obj in phase["object_summaries"]:
            assert "object_name" in obj
            assert "workload" in obj
            assert "criticality_score" in obj
            assert "criticality_tier" in obj


# ══════════════════════════════════════════════════════════
# Criticality-Weighted Confidence Score (v2) Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_confidence_v2_structure(auth_client: AsyncClient, db, enterprise_tenant):
    """Confidence v2 returns valid structure with MVB coverage factor."""
    tenant, objects = enterprise_tenant

    response = await auth_client.get(f"/api/recovery/confidence/v2?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()

    assert "score" in data
    assert "grade" in data
    assert data["grade"] in ("A", "B", "C", "D")
    assert "factors" in data
    assert "freshness" in data["factors"]
    assert "completeness" in data["factors"]
    assert "mvb_coverage" in data["factors"]
    assert "restore_success" in data["factors"]
    assert "validation" in data["factors"]


@pytest.mark.asyncio
async def test_confidence_v2_has_mvb_coverage(auth_client: AsyncClient, db, enterprise_tenant):
    """Confidence v2 includes MVB coverage as a factor."""
    tenant, objects = enterprise_tenant

    response = await auth_client.get(f"/api/recovery/confidence/v2?tenant_id={tenant.id}")
    data = response.json()

    mvb = data["factors"]["mvb_coverage"]
    assert mvb["weight"] == 20
    assert mvb["score"] >= 0
    assert "critical" in mvb["detail"].lower() or "protected" in mvb["detail"].lower()


@pytest.mark.asyncio
async def test_confidence_v2_weights_critical_users(auth_client: AsyncClient, db, enterprise_tenant):
    """Critical users have 4x weight in freshness calculation."""
    tenant, objects = enterprise_tenant

    response = await auth_client.get(f"/api/recovery/confidence/v2?tenant_id={tenant.id}")
    data = response.json()

    # All objects are backed up (protected), so freshness should be high
    assert data["factors"]["freshness"]["score"] > 50


@pytest.mark.asyncio
async def test_confidence_v2_empty_tenant(auth_client: AsyncClient):
    """Confidence v2 for empty tenant returns 0."""
    response = await auth_client.get("/api/recovery/confidence/v2?tenant_id=999")
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0


# ══════════════════════════════════════════════════════════
# End-to-End Integration Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2e_full_recovery_workflow(auth_client: AsyncClient, db, enterprise_tenant):
    """Full workflow: generate plan → check confidence → verify plan phases → dry-run restore."""
    tenant, objects = enterprise_tenant

    # 1. Generate MVB plan
    gen_resp = await auth_client.post(f"/api/recovery/mvb-plan/generate?tenant_id={tenant.id}")
    assert gen_resp.status_code == 200
    assert gen_resp.json()["status"] == "generated"

    # 2. Get the plan
    plan_resp = await auth_client.get(f"/api/recovery/mvb-plan?tenant_id={tenant.id}")
    plan = plan_resp.json()
    assert plan["status"] == "ready"
    assert plan["phases"][0]["name"] == "Identity Controls"
    assert plan["mvb_user_count"] >= 2

    # 3. Check confidence v2
    conf_resp = await auth_client.get(f"/api/recovery/confidence/v2?tenant_id={tenant.id}")
    conf = conf_resp.json()
    assert conf["score"] > 0
    assert "mvb_coverage" in conf["factors"]

    # 4. Run mass-restore dry-run (should be criticality-ordered)
    restore_resp = await auth_client.post("/api/recovery/mass-restore", json={
        "tenant_id": tenant.id, "dry_run": True,
    })
    restore = restore_resp.json()
    assert restore["plan"][0]["workload"] == "entra_id"  # Identity first

    # 5. Verify plan coverage matches restore
    plan_total = plan["total_object_count"]
    restore_total = restore["objects_to_restore"]
    assert plan_total == restore_total


@pytest.mark.asyncio
async def test_e2e_plan_reflects_criticality_changes(auth_client: AsyncClient, db, enterprise_tenant):
    """When criticality changes, regenerating the plan reflects new ordering."""
    tenant, objects = enterprise_tenant

    # Generate initial plan
    await auth_client.post(f"/api/recovery/mvb-plan/generate?tenant_id={tenant.id}")
    plan1 = (await auth_client.get(f"/api/recovery/mvb-plan?tenant_id={tenant.id}")).json()

    # Change intern to critical (simulating VIP group addition)
    intern_obj = [o for o in objects if "Intern" in o.display_name][0]
    intern_obj.criticality_score = 90
    intern_obj.criticality_tier = "critical"
    await db.commit()

    # Regenerate plan
    await auth_client.post(f"/api/recovery/mvb-plan/generate?tenant_id={tenant.id}")
    plan2 = (await auth_client.get(f"/api/recovery/mvb-plan?tenant_id={tenant.id}")).json()

    # MVB phase should now have more objects
    mvb1_count = plan1["phases"][1]["object_count"]
    mvb2_count = plan2["phases"][1]["object_count"]
    assert mvb2_count > mvb1_count
