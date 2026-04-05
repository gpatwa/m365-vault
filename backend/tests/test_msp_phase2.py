"""MSP Phase 2 tests — role permissions, branding, billing, bulk onboard, compliance.

Tests all MSP features added in Weeks 1-5 of the MSP Phase 2 build.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from app.database import async_session
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.backup_job import BackupJob, JobStatus


async def _seed_tenant(db, name="Test Corp", status=TenantStatus.ACTIVE):
    tenant = Tenant(
        name=name, ms_tenant_id=f"tid-{name.lower().replace(' ', '-')}",
        client_id="test-cid", client_secret_encrypted="encrypted",
        status=status,
    )
    db.add(tenant)
    await db.flush()
    return tenant


async def _seed_objects(db, tenant_id, count=5):
    for i in range(count):
        db.add(ProtectedObject(
            tenant_id=tenant_id, workload_type=WorkloadType.EXCHANGE,
            ms_object_id=f"obj-{tenant_id}-{i}", display_name=f"User {i}",
            status=ProtectionStatus.PROTECTED,
            last_backup_at=datetime.utcnow() - timedelta(hours=2),
        ))
    await db.flush()


async def _seed_jobs(db, tenant_id, count=3, status=JobStatus.COMPLETED):
    for i in range(count):
        db.add(BackupJob(
            tenant_id=tenant_id, workload_type="exchange", status=status,
            started_at=datetime.utcnow() - timedelta(hours=i+1),
            completed_at=datetime.utcnow() - timedelta(hours=i) if status == JobStatus.COMPLETED else None,
            objects_total=5, objects_processed=5 if status == JobStatus.COMPLETED else 0,
            created_at=datetime.utcnow() - timedelta(hours=i+1),
        ))
    await db.flush()


# ═══════════════════════════════════════════════════════
# 1. MSP Role Permissions
# ═══════════════════════════════════════════════════════

class TestMSPRolePermissions:

    @pytest.mark.asyncio
    async def test_admin_can_access_msp_overview(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/msp/overview")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_msp_admin_can_access_overview(self, msp_admin_client: AsyncClient):
        response = await msp_admin_client.get("/api/msp/overview")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_blocked_from_msp(self, viewer_client: AsyncClient):
        response = await viewer_client.get("/api/msp/overview")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_blocked_from_billing(self, viewer_client: AsyncClient):
        response = await viewer_client.get("/api/msp/billing")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_blocked_from_branding_update(self, viewer_client: AsyncClient):
        response = await viewer_client.put("/api/msp/branding", json={"company_name": "Hacked"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_msp_admin_can_update_branding(self, msp_admin_client: AsyncClient):
        response = await msp_admin_client.put("/api/msp/branding", json={"company_name": "MSP Corp"})
        assert response.status_code == 200
        assert response.json()["company_name"] == "MSP Corp"

    @pytest.mark.asyncio
    async def test_unauthenticated_blocked_from_msp(self, client: AsyncClient):
        response = await client.get("/api/msp/overview")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════
# 2. White-Label Branding
# ═══════════════════════════════════════════════════════

class TestBranding:

    @pytest.mark.asyncio
    async def test_branding_returns_defaults(self, client: AsyncClient):
        """GET branding works without auth and returns defaults."""
        response = await client.get("/api/msp/branding")
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "KavachIQ"
        assert data["primary_color"] == "#3b82f6"

    @pytest.mark.asyncio
    async def test_branding_no_auth_required(self, client: AsyncClient):
        """Branding GET is public (login page needs it)."""
        response = await client.get("/api/msp/branding")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_branding_update_and_read(self, auth_client: AsyncClient):
        """PUT branding then GET to verify persistence."""
        await auth_client.put("/api/msp/branding", json={
            "company_name": "Acme Security",
            "tagline": "Protecting Your Data",
            "primary_color": "#ff0000",
        })
        response = await auth_client.get("/api/msp/branding")
        data = response.json()
        assert data["company_name"] == "Acme Security"
        assert data["tagline"] == "Protecting Your Data"
        assert data["primary_color"] == "#ff0000"
        # Unchanged fields keep defaults
        assert data["secondary_color"] == "#1e293b"

    @pytest.mark.asyncio
    async def test_branding_partial_update(self, auth_client: AsyncClient):
        """Only updated fields change, others preserved."""
        await auth_client.put("/api/msp/branding", json={"company_name": "First"})
        await auth_client.put("/api/msp/branding", json={"tagline": "New Tagline"})
        response = await auth_client.get("/api/msp/branding")
        data = response.json()
        assert data["company_name"] == "First"
        assert data["tagline"] == "New Tagline"


# ═══════════════════════════════════════════════════════
# 3. Billing Portal
# ═══════════════════════════════════════════════════════

class TestBilling:

    @pytest.mark.asyncio
    async def test_billing_empty(self, auth_client: AsyncClient):
        """Billing with no tenants returns empty."""
        response = await auth_client.get("/api/msp/billing")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tenants"] == 0
        assert data["total_cost"] == 0
        assert data["line_items"] == []

    @pytest.mark.asyncio
    async def test_billing_calculates_cost(self, auth_client: AsyncClient):
        """Billing calculates per-tenant cost from usage."""
        async with async_session() as db:
            t = await _seed_tenant(db, "Billing Corp")
            await _seed_objects(db, t.id, count=10)
            await db.commit()

        response = await auth_client.get("/api/msp/billing")
        data = response.json()
        assert data["total_tenants"] == 1
        assert data["total_users"] == 10
        assert data["unit_price"] == 1.50  # <500 users tier
        assert data["total_cost"] == 15.00  # 10 × $1.50
        assert len(data["line_items"]) == 1
        assert data["line_items"][0]["tenant_name"] == "Billing Corp"
        assert data["line_items"][0]["monthly_cost"] == 15.00

    @pytest.mark.asyncio
    async def test_billing_has_tiers(self, auth_client: AsyncClient):
        """Billing response includes wholesale tier info."""
        response = await auth_client.get("/api/msp/billing")
        data = response.json()
        assert "tiers" in data
        assert len(data["tiers"]) == 4
        assert data["tiers"][0]["price"] == 1.50

    @pytest.mark.asyncio
    async def test_billing_csv_export(self, auth_client: AsyncClient):
        """CSV export returns CSV content type."""
        response = await auth_client.get("/api/msp/billing/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_billing_generate_snapshot(self, auth_client: AsyncClient):
        """Generate billing records for a month."""
        async with async_session() as db:
            t = await _seed_tenant(db, "Snapshot Corp")
            await _seed_objects(db, t.id, count=5)
            await db.commit()

        response = await auth_client.post("/api/msp/billing/generate?month=2026-03")
        assert response.status_code == 200
        data = response.json()
        assert data["month"] == "2026-03"
        assert data["created"] == 1
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_billing_month_filter(self, auth_client: AsyncClient):
        """Billing accepts month parameter."""
        response = await auth_client.get("/api/msp/billing?month=2026-01")
        assert response.status_code == 200
        assert response.json()["month"] == "2026-01"


# ═══════════════════════════════════════════════════════
# 4. Bulk Tenant Onboarding
# ═══════════════════════════════════════════════════════

class TestBulkOnboard:

    @pytest.mark.asyncio
    async def test_bulk_onboard_creates_tenants(self, auth_client: AsyncClient):
        """Bulk onboard creates multiple tenants."""
        response = await auth_client.post("/api/msp/onboard-bulk", json={
            "tenants": [
                {"name": "Tenant A", "ms_tenant_id": "tid-a", "client_id": "cid-a", "client_secret": "secret-a"},
                {"name": "Tenant B", "ms_tenant_id": "tid-b", "client_id": "cid-b", "client_secret": "secret-b"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["created"] == 2
        assert data["skipped"] == 0
        assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_bulk_onboard_skips_duplicates(self, auth_client: AsyncClient):
        """Duplicate ms_tenant_id is skipped, not failed."""
        async with async_session() as db:
            await _seed_tenant(db, "Existing")
            await db.commit()

        response = await auth_client.post("/api/msp/onboard-bulk", json={
            "tenants": [
                {"name": "Existing", "ms_tenant_id": "tid-existing", "client_id": "x", "client_secret": "x"},
                {"name": "New One", "ms_tenant_id": "tid-new", "client_id": "y", "client_secret": "y"},
            ]
        })
        data = response.json()
        assert data["created"] == 1
        assert data["skipped"] == 1

    @pytest.mark.asyncio
    async def test_bulk_onboard_empty_list(self, auth_client: AsyncClient):
        """Empty tenant list returns zero counts."""
        response = await auth_client.post("/api/msp/onboard-bulk", json={"tenants": []})
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_bulk_onboard_viewer_blocked(self, viewer_client: AsyncClient):
        """Viewer cannot bulk onboard."""
        response = await viewer_client.post("/api/msp/onboard-bulk", json={
            "tenants": [{"name": "X", "ms_tenant_id": "x", "client_id": "x", "client_secret": "x"}]
        })
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════
# 5. Compliance Reports
# ═══════════════════════════════════════════════════════

class TestComplianceReports:

    @pytest.mark.asyncio
    async def test_compliance_report_hipaa(self, auth_client: AsyncClient):
        """HIPAA report returns correct structure."""
        async with async_session() as db:
            t = await _seed_tenant(db, "Health Clinic")
            await _seed_objects(db, t.id, count=5)
            await _seed_jobs(db, t.id, count=3)
            await db.commit()

        response = await auth_client.get(f"/api/msp/compliance-report/{t.id}?report_type=hipaa")
        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "hipaa"
        assert data["title"] == "HIPAA Compliance Evidence Report"
        assert data["tenant"]["name"] == "Health Clinic"
        assert data["backup_coverage"]["coverage_pct"] == 100.0
        assert data["encryption"]["algorithm"] == "AES-256-GCM"
        assert len(data["controls"]) == 6
        assert data["controls"][0]["id"] == "164.312(a)(1)"

    @pytest.mark.asyncio
    async def test_compliance_report_soc2(self, auth_client: AsyncClient):
        """SOC 2 report has correct controls."""
        async with async_session() as db:
            t = await _seed_tenant(db, "SOC2 Corp")
            await _seed_objects(db, t.id)
            await db.commit()

        response = await auth_client.get(f"/api/msp/compliance-report/{t.id}?report_type=soc2")
        data = response.json()
        assert data["report_type"] == "soc2"
        assert data["controls"][0]["id"] == "CC6.1"

    @pytest.mark.asyncio
    async def test_compliance_report_gdpr(self, auth_client: AsyncClient):
        async with async_session() as db:
            t = await _seed_tenant(db, "EU Corp")
            await _seed_objects(db, t.id)
            await db.commit()

        response = await auth_client.get(f"/api/msp/compliance-report/{t.id}?report_type=gdpr")
        assert response.json()["controls"][0]["id"] == "Art. 5(1)(f)"

    @pytest.mark.asyncio
    async def test_compliance_report_dora(self, auth_client: AsyncClient):
        async with async_session() as db:
            t = await _seed_tenant(db, "Bank Corp")
            await _seed_objects(db, t.id)
            await db.commit()

        response = await auth_client.get(f"/api/msp/compliance-report/{t.id}?report_type=dora")
        assert response.json()["controls"][0]["id"] == "Art. 6"

    @pytest.mark.asyncio
    async def test_compliance_report_nonexistent_tenant(self, auth_client: AsyncClient):
        """404 for missing tenant."""
        response = await auth_client.get("/api/msp/compliance-report/99999?report_type=hipaa")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_compliance_report_backup_reliability(self, auth_client: AsyncClient):
        """Report includes backup reliability stats."""
        async with async_session() as db:
            t = await _seed_tenant(db, "Reliable Corp")
            await _seed_objects(db, t.id)
            await _seed_jobs(db, t.id, count=10)
            await db.commit()

        response = await auth_client.get(f"/api/msp/compliance-report/{t.id}")
        data = response.json()
        assert data["backup_reliability"]["total_jobs"] == 10
        assert data["backup_reliability"]["successful_jobs"] == 10
        assert data["backup_reliability"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_compliance_report_viewer_blocked(self, viewer_client: AsyncClient):
        """Viewer cannot access compliance reports."""
        response = await viewer_client.get("/api/msp/compliance-report/1")
        assert response.status_code == 403
