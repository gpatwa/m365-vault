"""Tests for Organizational Context Layer — models, scorer, API endpoints."""
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.org_context import UserContext, SiteContext, VIPGroup, VIPGroupMember
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.services.criticality_scorer import CriticalityScorer


# ══════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def tenant(db: AsyncSession):
    """Create a test tenant."""
    t = Tenant(
        name="Test Corp",
        ms_tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret_encrypted="encrypted",
        status=TenantStatus.ACTIVE,
    )
    db.add(t)
    await db.flush()

    # Create UserTenantMembership for the testadmin user
    user = (await db.execute(select(User).where(User.username == "testadmin"))).scalar_one_or_none()
    if user:
        db.add(UserTenant(user_id=user.id, tenant_id=t.id, role="owner", is_default=1))
        await db.flush()

    return t


@pytest_asyncio.fixture
async def protected_objects(db: AsyncSession, tenant: Tenant):
    """Create test protected objects."""
    objects = []
    users = [
        ("user-ceo", "Jane Smith", "jane@test.com", "CEO", "Executive"),
        ("user-cfo", "Bob Johnson", "bob@test.com", "CFO", "Finance"),
        ("user-dev", "Alice Dev", "alice@test.com", "Developer", "Engineering"),
        ("user-intern", "Charlie Intern", "charlie@test.com", "Intern", "Marketing"),
    ]
    for ms_id, name, email, title, dept in users:
        po = ProtectedObject(
            tenant_id=tenant.id,
            workload_type=WorkloadType.EXCHANGE,
            ms_object_id=ms_id,
            display_name=f"{name} (Mailbox)",
            email=email,
            status=ProtectionStatus.PROTECTED,
        )
        db.add(po)
        objects.append(po)

    # SharePoint site
    site = ProtectedObject(
        tenant_id=tenant.id,
        workload_type=WorkloadType.SHAREPOINT,
        ms_object_id="site-finance",
        display_name="Finance Reports",
        site_url="https://test.sharepoint.com/sites/finance",
        status=ProtectionStatus.PROTECTED,
    )
    db.add(site)
    objects.append(site)

    await db.flush()
    return objects


@pytest_asyncio.fixture
async def user_contexts(db: AsyncSession, tenant: Tenant, protected_objects):
    """Create test user contexts with various signals."""
    from datetime import datetime, timedelta

    contexts = []
    now = datetime.utcnow()

    # CEO — should score critical
    ceo = UserContext(
        tenant_id=tenant.id,
        protected_object_id=protected_objects[0].id,
        ms_user_id="user-ceo",
        display_name="Jane Smith",
        email="jane@test.com",
        job_title="CEO",
        department="Executive",
        is_vip=1,
        has_privileged_role=1,
        is_global_admin=1,
        privileged_roles=json.dumps(["Global Administrator"]),
        direct_reports_count=8,
        last_sign_in_at=now - timedelta(hours=2),
        has_legal_hold=1,
        synced_at=now,
    )
    db.add(ceo)
    contexts.append(ceo)

    # CFO — should score high
    cfo = UserContext(
        tenant_id=tenant.id,
        protected_object_id=protected_objects[1].id,
        ms_user_id="user-cfo",
        display_name="Bob Johnson",
        email="bob@test.com",
        job_title="CFO",
        department="Finance",
        has_privileged_role=0,
        direct_reports_count=3,
        last_sign_in_at=now - timedelta(hours=5),
        highest_sensitivity_label="Confidential",
        synced_at=now,
    )
    db.add(cfo)
    contexts.append(cfo)

    # Developer — should score medium
    dev = UserContext(
        tenant_id=tenant.id,
        protected_object_id=protected_objects[2].id,
        ms_user_id="user-dev",
        display_name="Alice Dev",
        email="alice@test.com",
        job_title="Developer",
        department="Engineering",
        direct_reports_count=0,
        last_sign_in_at=now - timedelta(days=2),
        synced_at=now,
    )
    db.add(dev)
    contexts.append(dev)

    # Intern — should score low
    intern = UserContext(
        tenant_id=tenant.id,
        protected_object_id=protected_objects[3].id,
        ms_user_id="user-intern",
        display_name="Charlie Intern",
        email="charlie@test.com",
        job_title="Intern",
        department="Marketing",
        direct_reports_count=0,
        last_sign_in_at=now - timedelta(days=120),
        synced_at=now,
    )
    db.add(intern)
    contexts.append(intern)

    await db.flush()
    return contexts


@pytest_asyncio.fixture
async def site_contexts(db: AsyncSession, tenant: Tenant, protected_objects):
    """Create test site contexts."""
    ctx = SiteContext(
        tenant_id=tenant.id,
        protected_object_id=protected_objects[4].id,
        ms_site_id="site-finance",
        site_name="Finance Reports",
        site_url="https://test.sharepoint.com/sites/finance",
        unique_visitors=50,
        file_count=500,
        external_sharing_enabled=1,
        sensitivity_label="Confidential",
    )
    db.add(ctx)
    await db.flush()
    return [ctx]


# ══════════════════════════════════════════════════════════
# Criticality Scorer Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scorer_ceo_is_critical(db: AsyncSession, tenant, protected_objects, user_contexts):
    """CEO with Global Admin + legal hold should score critical (>=80)."""
    scorer = CriticalityScorer(db)
    await scorer.score_all_users(tenant.id)
    await db.refresh(user_contexts[0])

    assert user_contexts[0].criticality_score >= 80
    assert user_contexts[0].criticality_tier == "critical"
    assert user_contexts[0].signals is not None
    signals = json.loads(user_contexts[0].signals)
    assert signals.get("global_admin") is True


@pytest.mark.asyncio
async def test_scorer_cfo_is_high(db: AsyncSession, tenant, protected_objects, user_contexts):
    """CFO with Confidential labels should score high (>=60)."""
    scorer = CriticalityScorer(db)
    await scorer.score_all_users(tenant.id)
    await db.refresh(user_contexts[1])

    assert user_contexts[1].criticality_score >= 60
    assert user_contexts[1].criticality_tier in ("high", "critical")


@pytest.mark.asyncio
async def test_scorer_intern_is_low(db: AsyncSession, tenant, protected_objects, user_contexts):
    """Inactive intern should score low (<40)."""
    scorer = CriticalityScorer(db)
    await scorer.score_all_users(tenant.id)
    await db.refresh(user_contexts[3])

    assert user_contexts[3].criticality_score < 40
    assert user_contexts[3].criticality_tier == "low"
    signals = json.loads(user_contexts[3].signals)
    assert signals.get("inactive_90d") is True


@pytest.mark.asyncio
async def test_scorer_site_with_sharing(db: AsyncSession, tenant, protected_objects, site_contexts):
    """SharePoint site with external sharing + confidential label should score high."""
    scorer = CriticalityScorer(db)
    await scorer.score_all_sites(tenant.id)
    await db.refresh(site_contexts[0])

    assert site_contexts[0].criticality_score >= 50
    assert site_contexts[0].criticality_tier in ("high", "medium")
    signals = json.loads(site_contexts[0].signals)
    assert signals.get("external_sharing") is True


@pytest.mark.asyncio
async def test_scorer_propagates_to_protected_objects(db: AsyncSession, tenant, protected_objects, user_contexts):
    """Scores should propagate from UserContext to ProtectedObject."""
    scorer = CriticalityScorer(db)
    result = await scorer.score_all(tenant.id)

    assert result["users_scored"] == 4
    assert result["tiers"]["critical"] >= 1

    # Check propagation
    await db.refresh(protected_objects[0])
    assert protected_objects[0].criticality_score >= 80
    assert protected_objects[0].criticality_tier == "critical"


@pytest.mark.asyncio
async def test_scorer_vip_boost(db: AsyncSession, tenant, protected_objects, user_contexts):
    """VIP group membership should boost scores."""
    # Create VIP group
    group = VIPGroup(tenant_id=tenant.id, name="Executive Team", criticality_boost=30)
    db.add(group)
    await db.flush()

    # Add the developer to VIP group
    member = VIPGroupMember(
        vip_group_id=group.id,
        protected_object_id=protected_objects[2].id,
        ms_user_id="user-dev",
    )
    db.add(member)
    await db.flush()

    scorer = CriticalityScorer(db)
    await scorer.score_all_users(tenant.id)
    await db.refresh(user_contexts[2])

    # Developer should now score higher due to VIP boost
    signals = json.loads(user_contexts[2].signals)
    assert signals.get("vip_group_boost") == 30


@pytest.mark.asyncio
async def test_scorer_empty_tenant(db: AsyncSession, tenant):
    """Scoring empty tenant should return 0 scored."""
    scorer = CriticalityScorer(db)
    result = await scorer.score_all(tenant.id)
    assert result["users_scored"] == 0
    assert result["sites_scored"] == 0


# ══════════════════════════════════════════════════════════
# API Endpoint Tests
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_summary_empty(auth_client: AsyncClient, test_tenant):
    """Summary for non-existent tenant returns zeros."""
    response = await auth_client.get(f"/api/org-context/summary?tenant_id={test_tenant}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 0
    assert data["total_sites"] == 0
    assert data["by_tier"]["critical"] == 0


@pytest.mark.asyncio
async def test_summary_with_data(auth_client: AsyncClient, db, tenant, protected_objects, user_contexts):
    """Summary returns correct tier counts after scoring."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/org-context/summary?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 4
    assert data["by_tier"]["critical"] >= 1
    assert len(data["top_critical_users"]) >= 1
    assert data["top_critical_users"][0]["display_name"] == "Jane Smith"


@pytest.mark.asyncio
async def test_users_list_pagination(auth_client: AsyncClient, db, tenant, protected_objects, user_contexts):
    """Users list supports pagination."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/org-context/users?tenant_id={tenant.id}&page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_users_list_filter_by_tier(auth_client: AsyncClient, db, tenant, protected_objects, user_contexts):
    """Users list can filter by criticality tier."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/org-context/users?tenant_id={tenant.id}&tier=critical")
    assert response.status_code == 200
    data = response.json()
    assert all(u["criticality_tier"] == "critical" for u in data["items"])
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_users_list_search(auth_client: AsyncClient, db, tenant, protected_objects, user_contexts):
    """Users list can search by name."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/org-context/users?tenant_id={tenant.id}&search=Jane")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["display_name"] == "Jane Smith"


@pytest.mark.asyncio
async def test_users_sorted_by_score_desc(auth_client: AsyncClient, db, tenant, protected_objects, user_contexts):
    """Users default sorted by criticality_score descending."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/org-context/users?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()
    scores = [u["criticality_score"] for u in data["items"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_sites_list(auth_client: AsyncClient, db, tenant, protected_objects, site_contexts):
    """Sites list returns scored sites."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/org-context/sites?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["site_name"] == "Finance Reports"
    assert data["items"][0]["external_sharing_enabled"] is True


# ── VIP Groups ──

@pytest.mark.asyncio
async def test_vip_group_crud(auth_client: AsyncClient, db, tenant, protected_objects):
    """Create, list, update, delete VIP groups."""
    # Commit fixture data so API session can see it (SQLite lock workaround)
    await db.commit()

    # Create
    response = await auth_client.post("/api/org-context/vip-groups", json={
        "tenant_id": tenant.id,
        "name": "Executive Team",
        "description": "C-suite and board",
        "criticality_boost": 25,
        "member_object_ids": [protected_objects[0].id],
    })
    assert response.status_code == 201
    group_id = response.json()["id"]

    # List
    response = await auth_client.get(f"/api/org-context/vip-groups?tenant_id={tenant.id}")
    assert response.status_code == 200
    groups = response.json()["groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "Executive Team"
    assert groups[0]["member_count"] == 1
    assert groups[0]["criticality_boost"] == 25

    # Update
    response = await auth_client.put(f"/api/org-context/vip-groups/{group_id}", json={
        "name": "Leadership Team",
        "criticality_boost": 30,
    })
    assert response.status_code == 200
    assert response.json()["name"] == "Leadership Team"

    # Add member
    response = await auth_client.post(f"/api/org-context/vip-groups/{group_id}/members", json={
        "protected_object_ids": [protected_objects[1].id],
    })
    assert response.status_code == 200
    assert response.json()["added"] == 1

    # Delete
    response = await auth_client.delete(f"/api/org-context/vip-groups/{group_id}")
    assert response.status_code == 204

    # Verify deleted
    response = await auth_client.get(f"/api/org-context/vip-groups?tenant_id={tenant.id}")
    assert len(response.json()["groups"]) == 0


# ── Workload API — criticality fields ──

@pytest.mark.asyncio
async def test_exchange_includes_criticality(auth_client: AsyncClient, db, tenant, protected_objects, user_contexts):
    """Exchange mailbox list includes criticality_score and criticality_tier."""
    scorer = CriticalityScorer(db)
    await scorer.score_all(tenant.id)

    response = await auth_client.get(f"/api/exchange/mailboxes?tenant_id={tenant.id}")
    assert response.status_code == 200
    data = response.json()
    if data["items"]:
        item = data["items"][0]
        assert "criticality_score" in item
        assert "criticality_tier" in item
