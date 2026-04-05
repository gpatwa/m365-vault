"""MSP Multi-Tenant Dashboard API — overview, branding, billing, onboarding.

Provides a single-pane-of-glass view across all tenants with per-tenant
health scores, protection status, backup activity, and alerts.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, ProtectionStatus, WorkloadType
from app.models.backup_job import BackupJob, JobStatus
from app.models.snapshot import Snapshot, SnapshotStatus
from app.models.msp_branding import MSPBranding
from app.models.billing import BillingRecord
from app.models.sla_policy import SLAPolicy
from app.models.user import User
from app.services.auth import require_msp_permission, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/msp", tags=["MSP Dashboard"])


@router.get("/overview")
async def msp_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """MSP overview — all tenants with per-tenant health summary.

    Returns a list of tenants with protection stats, backup activity,
    storage usage, and health indicators for the MSP dashboard.
    """
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)

    # Get all tenants
    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()

    tenant_summaries = []
    total_users = 0
    total_storage = 0
    total_alerts = 0

    for tenant in tenants:
        tid = tenant.id

        # Protected objects
        protected_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )).scalar() or 0

        total_objects = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tid,
            )
        )).scalar() or 0

        protection_pct = round(protected_count / total_objects * 100) if total_objects > 0 else 0

        # Active workloads
        wl_result = await db.execute(
            select(func.count(func.distinct(ProtectedObject.workload_type))).where(
                ProtectedObject.tenant_id == tid,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )
        workload_count = wl_result.scalar() or 0

        # Backup jobs (24h)
        jobs_24h = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.tenant_id == tid,
                BackupJob.created_at >= since_24h,
            )
        )).scalar() or 0

        jobs_failed_24h = (await db.execute(
            select(func.count(BackupJob.id)).where(
                BackupJob.tenant_id == tid,
                BackupJob.created_at >= since_24h,
                BackupJob.status == JobStatus.FAILED,
            )
        )).scalar() or 0

        # Storage
        storage_bytes = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tid,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
        )).scalar() or 0

        # Last backup time
        last_backup = (await db.execute(
            select(func.max(BackupJob.completed_at)).where(
                BackupJob.tenant_id == tid,
                BackupJob.status == JobStatus.COMPLETED,
            )
        )).scalar()

        # Simple health score (0-100)
        health = 100
        alerts = []

        if protection_pct < 100:
            health -= 20
            alerts.append(f"{total_objects - protected_count} unprotected objects")
        if jobs_failed_24h > 0:
            health -= 30
            alerts.append(f"{jobs_failed_24h} failed backups in 24h")
        if last_backup and (now - last_backup).total_seconds() > 86400:
            health -= 15
            alerts.append("No backup in 24+ hours")
        if total_objects == 0:
            health = 0
            alerts.append("No objects discovered")

        health = max(0, health)
        total_users += protected_count
        total_storage += storage_bytes
        total_alerts += len(alerts)

        tenant_summaries.append({
            "id": tenant.id,
            "name": tenant.name,
            "status": tenant.status.value,
            "ms_tenant_id": tenant.ms_tenant_id,
            "protected_objects": protected_count,
            "total_objects": total_objects,
            "protection_pct": protection_pct,
            "workload_count": workload_count,
            "backups_24h": jobs_24h,
            "failed_24h": jobs_failed_24h,
            "storage_bytes": storage_bytes,
            "storage_gb": round(storage_bytes / (1024 ** 3), 3),
            "last_backup": last_backup.isoformat() if last_backup else None,
            "health_score": health,
            "health_status": "healthy" if health >= 80 else ("at_risk" if health >= 50 else "critical"),
            "alerts": alerts,
            "alert_count": len(alerts),
        })

    # Sort by health (worst first for attention)
    tenant_summaries.sort(key=lambda t: t["health_score"])

    return {
        "summary": {
            "total_tenants": len(tenants),
            "active_tenants": sum(1 for t in tenants if t.status == TenantStatus.ACTIVE),
            "total_protected_users": total_users,
            "total_storage_bytes": total_storage,
            "total_storage_gb": round(total_storage / (1024 ** 3), 3),
            "total_alerts": total_alerts,
            "overall_health": round(sum(t["health_score"] for t in tenant_summaries) / len(tenant_summaries)) if tenant_summaries else 0,
        },
        "tenants": tenant_summaries,
    }


# ── Branding ──────────────────────────────────────────────────


BRANDING_DEFAULTS = {
    "company_name": "KavachIQ",
    "tagline": "SaaS Data Protection",
    "logo_url": None,
    "favicon_url": None,
    "primary_color": "#3b82f6",
    "secondary_color": "#1e293b",
}


@router.get("/branding")
async def get_branding(db: AsyncSession = Depends(get_db)):
    """Get MSP branding config. No auth required (login page needs branding too)."""
    result = await db.execute(select(MSPBranding).limit(1))
    branding = result.scalar_one_or_none()

    if not branding:
        return BRANDING_DEFAULTS

    return {
        "company_name": branding.company_name,
        "tagline": branding.tagline,
        "logo_url": branding.logo_url,
        "favicon_url": branding.favicon_url,
        "primary_color": branding.primary_color,
        "secondary_color": branding.secondary_color,
    }


class BrandingUpdate(BaseModel):
    company_name: Optional[str] = None
    tagline: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


@router.put("/branding")
async def update_branding(
    req: BrandingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Update MSP branding config. Upserts (creates if not exists)."""
    result = await db.execute(select(MSPBranding).limit(1))
    branding = result.scalar_one_or_none()

    if not branding:
        branding = MSPBranding()
        db.add(branding)

    if req.company_name is not None:
        branding.company_name = req.company_name
    if req.tagline is not None:
        branding.tagline = req.tagline
    if req.logo_url is not None:
        branding.logo_url = req.logo_url
    if req.favicon_url is not None:
        branding.favicon_url = req.favicon_url
    if req.primary_color is not None:
        branding.primary_color = req.primary_color
    if req.secondary_color is not None:
        branding.secondary_color = req.secondary_color

    branding.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "company_name": branding.company_name,
        "tagline": branding.tagline,
        "logo_url": branding.logo_url,
        "favicon_url": branding.favicon_url,
        "primary_color": branding.primary_color,
        "secondary_color": branding.secondary_color,
    }


# ── Billing ───────────────────────────────────────────────────

WHOLESALE_TIERS = [
    {"min_users": 0, "max_users": 500, "price": 1.50},
    {"min_users": 501, "max_users": 2000, "price": 1.25},
    {"min_users": 2001, "max_users": 5000, "price": 1.00},
    {"min_users": 5001, "max_users": None, "price": 0.85},
]


def _get_wholesale_price(total_users: int) -> float:
    for tier in WHOLESALE_TIERS:
        if tier["max_users"] is None or total_users <= tier["max_users"]:
            return tier["price"]
    return 0.85


@router.get("/billing")
async def get_billing(
    month: str = Query(None, description="Month in YYYY-MM format (default: current)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Per-tenant billing summary with wholesale tiered pricing."""
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    result = await db.execute(select(Tenant).where(Tenant.status == TenantStatus.ACTIVE))
    tenants = result.scalars().all()

    total_users_all = 0
    tenant_usage = []

    for tenant in tenants:
        user_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant.id,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )).scalar() or 0

        storage_bytes = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant.id,
                Snapshot.status == SnapshotStatus.COMPLETED,
            )
        )).scalar() or 0

        total_users_all += user_count
        tenant_usage.append({
            "tenant_id": tenant.id, "tenant_name": tenant.name,
            "user_count": user_count, "storage_gb": round(storage_bytes / (1024 ** 3), 3),
        })

    unit_price = _get_wholesale_price(total_users_all)
    line_items = []
    total_cost = 0.0

    for usage in tenant_usage:
        cost = round(usage["user_count"] * unit_price, 2)
        total_cost += cost

        existing = (await db.execute(
            select(BillingRecord).where(
                BillingRecord.tenant_id == usage["tenant_id"],
                BillingRecord.month == month,
            )
        )).scalar_one_or_none()

        line_items.append({
            **usage, "unit_price": unit_price, "monthly_cost": cost,
            "status": existing.status if existing else "draft",
        })

    return {
        "month": month, "total_tenants": len(tenants), "total_users": total_users_all,
        "unit_price": unit_price, "total_cost": round(total_cost, 2),
        "wholesale_tier": f"${unit_price}/user ({total_users_all} total users)",
        "line_items": line_items, "tiers": WHOLESALE_TIERS,
    }


@router.get("/billing/export")
async def export_billing_csv(
    month: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Export billing data as CSV for invoicing."""
    import csv, io
    from fastapi.responses import StreamingResponse

    billing = await get_billing(month=month, db=db, current_user=current_user)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tenant", "Users", "Storage (GB)", "Unit Price", "Monthly Cost", "Status"])
    for item in billing["line_items"]:
        writer.writerow([item["tenant_name"], item["user_count"], item["storage_gb"],
                         f"${item['unit_price']:.2f}", f"${item['monthly_cost']:.2f}", item["status"]])
    writer.writerow([])
    writer.writerow(["Total", billing["total_users"], "", "", f"${billing['total_cost']:.2f}", ""])
    writer.writerow(["Month", billing["month"]])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=kavachiq-billing-{billing['month']}.csv"},
    )


@router.post("/billing/generate")
async def generate_billing_records(
    month: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Snapshot billing records for a month."""
    if not month:
        month = datetime.utcnow().strftime("%Y-%m")

    billing = await get_billing(month=month, db=db, current_user=current_user)
    created = updated = 0

    for item in billing["line_items"]:
        existing = (await db.execute(
            select(BillingRecord).where(
                BillingRecord.tenant_id == item["tenant_id"], BillingRecord.month == month,
            )
        )).scalar_one_or_none()

        if existing:
            existing.user_count = item["user_count"]
            existing.storage_gb = item["storage_gb"]
            existing.unit_price = item["unit_price"]
            existing.total_cost = item["monthly_cost"]
            existing.tenant_name = item["tenant_name"]
            updated += 1
        else:
            db.add(BillingRecord(
                tenant_id=item["tenant_id"], month=month, tenant_name=item["tenant_name"],
                user_count=item["user_count"], storage_gb=item["storage_gb"],
                unit_price=item["unit_price"], total_cost=item["monthly_cost"], status="draft",
            ))
            created += 1

    await db.commit()
    return {"month": month, "created": created, "updated": updated, "total": created + updated}


# ── Bulk Onboarding ───────────────────────────────────────────


class BulkTenantEntry(BaseModel):
    name: str
    ms_tenant_id: str
    client_id: str
    client_secret: str
    sla_policy_id: Optional[int] = None


class BulkOnboardRequest(BaseModel):
    tenants: list[BulkTenantEntry]


@router.post("/onboard-bulk")
async def bulk_onboard_tenants(
    req: BulkOnboardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Bulk onboard multiple tenants at once.

    Accepts a list of tenant configs with pre-configured credentials.
    Encrypts secrets, creates tenants, skips duplicates.
    """
    from app.services.encryption import encryption_service
    from app.models.sla_policy import SLAPolicy
    from app.models.protected_object import ProtectedObject, ProtectionStatus

    results = []

    for entry in req.tenants:
        # Check for duplicate
        existing = (await db.execute(
            select(Tenant).where(Tenant.ms_tenant_id == entry.ms_tenant_id)
        )).scalar_one_or_none()

        if existing:
            results.append({
                "name": entry.name, "ms_tenant_id": entry.ms_tenant_id,
                "status": "skipped", "reason": "Tenant already exists",
                "tenant_id": existing.id,
            })
            continue

        try:
            tenant = Tenant(
                name=entry.name,
                ms_tenant_id=entry.ms_tenant_id,
                client_id=entry.client_id,
                client_secret_encrypted=encryption_service.encrypt_string(entry.client_secret),
                status=TenantStatus.ONBOARDING,
            )
            db.add(tenant)
            await db.flush()

            results.append({
                "name": entry.name, "ms_tenant_id": entry.ms_tenant_id,
                "status": "created", "tenant_id": tenant.id,
            })
        except Exception as e:
            results.append({
                "name": entry.name, "ms_tenant_id": entry.ms_tenant_id,
                "status": "failed", "reason": str(e)[:200],
            })

    await db.commit()

    created = sum(1 for r in results if r["status"] == "created")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")

    return {
        "total": len(req.tenants),
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


@router.post("/onboard-bulk/csv-parse")
async def parse_bulk_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_msp_permission),
):
    """Parse a CSV file for bulk onboarding preview.

    Expected CSV format: name, ms_tenant_id, client_id, client_secret
    Returns parsed entries for review before submission.
    """
    import csv
    import io

    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))

    entries = []
    errors = []

    for i, row in enumerate(reader):
        name = (row.get("name") or row.get("tenant_name") or "").strip()
        ms_tenant_id = (row.get("ms_tenant_id") or row.get("tenant_id") or "").strip()
        client_id = (row.get("client_id") or row.get("app_id") or "").strip()
        client_secret = (row.get("client_secret") or row.get("app_secret") or "").strip()

        if not name or not ms_tenant_id or not client_id or not client_secret:
            errors.append({"row": i + 2, "error": "Missing required fields", "data": row})
            continue

        entries.append({
            "name": name,
            "ms_tenant_id": ms_tenant_id,
            "client_id": client_id,
            "client_secret_masked": f"{client_secret[:4]}...{client_secret[-4:]}" if len(client_secret) > 8 else "***",
            "client_secret": client_secret,
        })

    return {
        "total_rows": len(entries) + len(errors),
        "valid": len(entries),
        "invalid": len(errors),
        "entries": entries,
        "errors": errors,
    }


# ── Compliance Reports ────────────────────────────────────────

REPORT_TYPES = {
    "hipaa": {
        "title": "HIPAA Compliance Evidence Report",
        "framework": "Health Insurance Portability and Accountability Act",
        "safeguards": [
            {"id": "164.312(a)(1)", "name": "Access Control", "control": "RBAC with Admin/Operator/Viewer roles, JWT authentication"},
            {"id": "164.312(a)(2)(iv)", "name": "Encryption", "control": "AES-256-GCM envelope encryption, per-snapshot DEK"},
            {"id": "164.312(b)", "name": "Audit Controls", "control": "Append-only audit log with user, action, timestamp, IP"},
            {"id": "164.312(c)(1)", "name": "Integrity", "control": "SHA-256 content hashing, backup validation"},
            {"id": "164.312(d)", "name": "Authentication", "control": "bcrypt password hashing, SSO/OIDC support"},
            {"id": "164.312(e)(1)", "name": "Transmission Security", "control": "TLS 1.2+ for all API and Graph communication"},
        ],
    },
    "soc2": {
        "title": "SOC 2 Type II Compliance Evidence Report",
        "framework": "AICPA Trust Services Criteria",
        "safeguards": [
            {"id": "CC6.1", "name": "Logical Access", "control": "JWT + SSO/OIDC, RBAC, inactive user blocking"},
            {"id": "CC6.3", "name": "Authorization", "control": "require_role() on every endpoint, 3 role levels"},
            {"id": "CC6.6", "name": "Encryption", "control": "AES-256-GCM at rest, TLS 1.2+ in transit"},
            {"id": "CC7.2", "name": "Monitoring", "control": "Anomaly detection, health scoring, circuit breaker"},
            {"id": "CC8.1", "name": "Change Management", "control": "Git version control, CI/CD pipeline, Terraform IaC"},
            {"id": "A1.2", "name": "Backup Recovery", "control": "SLA-driven scheduling, retry engine, restore verification"},
        ],
    },
    "gdpr": {
        "title": "GDPR Compliance Evidence Report",
        "framework": "General Data Protection Regulation (EU)",
        "safeguards": [
            {"id": "Art. 5(1)(f)", "name": "Integrity & Confidentiality", "control": "AES-256-GCM, per-tenant key isolation"},
            {"id": "Art. 17", "name": "Right to Erasure", "control": "Tenant purge, cascade data deletion"},
            {"id": "Art. 25", "name": "Data Protection by Design", "control": "Per-snapshot DEK, RBAC, audit logging from day 1"},
            {"id": "Art. 30", "name": "Processing Records", "control": "Audit log with user, action, timestamp, IP"},
            {"id": "Art. 32", "name": "Security of Processing", "control": "Encryption, access control, backup validation, resilience"},
            {"id": "Art. 33", "name": "Breach Notification", "control": "Anomaly detection alerts, structured incident logging"},
        ],
    },
    "dora": {
        "title": "DORA Compliance Evidence Report",
        "framework": "Digital Operational Resilience Act (EU Financial Services)",
        "safeguards": [
            {"id": "Art. 6", "name": "ICT Risk Management", "control": "Smart Engine risk assessment, anomaly detection"},
            {"id": "Art. 9", "name": "Protection & Prevention", "control": "WORM storage, encryption, pre-flight validation"},
            {"id": "Art. 10", "name": "Detection", "control": "Anomaly detection, circuit breaker, health monitoring"},
            {"id": "Art. 11", "name": "Response & Recovery", "control": "Self-healing retry, mass recovery, MVB plans"},
            {"id": "Art. 12", "name": "Backup Policies", "control": "Configurable SLA policies, retention, WORM"},
            {"id": "Art. 13", "name": "Learning & Evolving", "control": "Health baselines, trend analysis, audit trail"},
        ],
    },
}


@router.get("/compliance-report/{tenant_id}")
async def get_compliance_report(
    tenant_id: int,
    report_type: str = Query("hipaa", description="Report type: hipaa, soc2, gdpr, dora"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Generate compliance evidence report for a tenant.

    Returns structured JSON with backup coverage, encryption status,
    audit summary, SLA compliance, and framework-specific control mapping.
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Tenant not found")

    report_def = REPORT_TYPES.get(report_type, REPORT_TYPES["hipaa"])

    # Backup coverage
    total_objects = (await db.execute(
        select(func.count(ProtectedObject.id)).where(ProtectedObject.tenant_id == tenant_id)
    )).scalar() or 0

    protected_objects = (await db.execute(
        select(func.count(ProtectedObject.id)).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.status == ProtectionStatus.PROTECTED,
        )
    )).scalar() or 0

    coverage_pct = round(protected_objects / total_objects * 100, 1) if total_objects > 0 else 0

    # Last backup per workload
    workload_status = []
    for wt in WorkloadType:
        count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wt,
                ProtectedObject.status == ProtectionStatus.PROTECTED,
            )
        )).scalar() or 0

        last_backup = (await db.execute(
            select(func.max(ProtectedObject.last_backup_at)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wt,
            )
        )).scalar()

        if count > 0:
            workload_status.append({
                "workload": wt.value,
                "protected_objects": count,
                "last_backup": last_backup.isoformat() if last_backup else None,
            })

    # SLA compliance
    sla_result = await db.execute(
        select(SLAPolicy).limit(5)
    )
    policies = sla_result.scalars().all()
    sla_info = [
        {"name": p.name, "frequency_hours": p.backup_frequency_hours,
         "retention_days": p.retention_days, "worm_enabled": getattr(p, 'worm_enabled', False)}
        for p in policies
    ]

    # Backup job stats (last 90 days)
    since_90d = datetime.utcnow() - timedelta(days=90)
    total_jobs = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.tenant_id == tenant_id, BackupJob.created_at >= since_90d,
        )
    )).scalar() or 0

    successful_jobs = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.tenant_id == tenant_id, BackupJob.created_at >= since_90d,
            BackupJob.status == JobStatus.COMPLETED,
        )
    )).scalar() or 0

    success_rate = round(successful_jobs / total_jobs * 100, 1) if total_jobs > 0 else 0

    return {
        "report_type": report_type,
        "title": report_def["title"],
        "framework": report_def["framework"],
        "generated_at": datetime.utcnow().isoformat(),
        "tenant": {
            "name": tenant.name,
            "ms_tenant_id": tenant.ms_tenant_id,
            "status": tenant.status.value,
        },
        "backup_coverage": {
            "total_objects": total_objects,
            "protected_objects": protected_objects,
            "coverage_pct": coverage_pct,
            "workloads": workload_status,
        },
        "encryption": {
            "algorithm": "AES-256-GCM",
            "key_management": "Per-snapshot DEK wrapped by master KEK",
            "at_rest": "All backup data encrypted before storage",
            "in_transit": "TLS 1.2+ for all API and Graph API communication",
        },
        "backup_reliability": {
            "period": "Last 90 days",
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "success_rate": success_rate,
        },
        "sla_policies": sla_info,
        "controls": report_def["safeguards"],
    }


# ── Demo Seed ─────────────────────────────────────────────────

DEMO_TENANTS = [
    {"name": "Acme Healthcare", "ms_tenant_id": "demo-acme-healthcare", "users": 50, "segment": "HIPAA"},
    {"name": "Summit Legal Group", "ms_tenant_id": "demo-summit-legal", "users": 30, "segment": "Legal"},
    {"name": "Pacific Finance", "ms_tenant_id": "demo-pacific-finance", "users": 45, "segment": "SOC 2"},
]


@router.post("/demo-seed")
async def seed_demo_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Seed demo tenants for the MSP interactive demo. Idempotent."""
    from app.services.encryption import encryption_service

    created = []
    skipped = []

    for demo in DEMO_TENANTS:
        existing = (await db.execute(
            select(Tenant).where(Tenant.ms_tenant_id == demo["ms_tenant_id"])
        )).scalar_one_or_none()

        if existing:
            skipped.append(demo["name"])
            continue

        # Create tenant
        tenant = Tenant(
            name=demo["name"],
            ms_tenant_id=demo["ms_tenant_id"],
            client_id=f"demo-client-{demo['ms_tenant_id']}",
            client_secret_encrypted=encryption_service.encrypt_string("demo-secret"),
            status=TenantStatus.ACTIVE,
        )
        db.add(tenant)
        await db.flush()

        # Create protected objects
        workloads = [WorkloadType.EXCHANGE, WorkloadType.ONEDRIVE, WorkloadType.SHAREPOINT,
                     WorkloadType.TEAMS, WorkloadType.ENTRA_ID]
        obj_count = 0
        for wl in workloads:
            count = demo["users"] if wl in (WorkloadType.EXCHANGE, WorkloadType.ONEDRIVE) else (
                8 if wl == WorkloadType.SHAREPOINT else (
                    demo["users"] // 5 if wl == WorkloadType.TEAMS else 1
                )
            )
            for i in range(min(count, 15)):  # Cap at 15 per workload for demo
                db.add(ProtectedObject(
                    tenant_id=tenant.id,
                    workload_type=wl,
                    ms_object_id=f"demo-{tenant.id}-{wl.value}-{i}",
                    display_name=f"{demo['name']} {wl.value.title()} {i+1}",
                    status=ProtectionStatus.PROTECTED,
                    last_backup_at=datetime.utcnow() - timedelta(hours=2),
                ))
                obj_count += 1

        # Create backup jobs
        for j in range(3):
            db.add(BackupJob(
                tenant_id=tenant.id,
                workload_type="exchange",
                status=JobStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(hours=j * 12 + 1),
                completed_at=datetime.utcnow() - timedelta(hours=j * 12),
                objects_total=obj_count,
                objects_processed=obj_count,
                objects_failed=0,
                created_at=datetime.utcnow() - timedelta(hours=j * 12 + 1),
            ))

        created.append({"name": demo["name"], "tenant_id": tenant.id, "objects": obj_count})

    await db.commit()

    return {
        "created": len(created),
        "skipped": len(skipped),
        "tenants": created,
        "skipped_names": skipped,
    }


# ── Offboard Workflow ─────────────────────────────────────────


@router.get("/offboard/{tenant_id}/pre-check")
async def offboard_pre_check(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Pre-offboard checklist — data inventory, active jobs, retention timeline.

    Returns everything the MSP needs to review before deactivating a client.
    """
    from fastapi import HTTPException

    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    now = datetime.utcnow()

    # Data inventory per workload
    workload_inventory = []
    total_objects = 0
    total_snapshots = 0
    total_storage = 0

    for wl in WorkloadType:
        obj_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wl,
            )
        )).scalar() or 0

        if obj_count == 0:
            continue

        snap_count = (await db.execute(
            select(func.count(Snapshot.id))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wl,
            )
        )).scalar() or 0

        storage = (await db.execute(
            select(func.sum(Snapshot.size_bytes))
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wl,
            )
        )).scalar() or 0

        last_backup = (await db.execute(
            select(func.max(ProtectedObject.last_backup_at)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == wl,
            )
        )).scalar()

        total_objects += obj_count
        total_snapshots += snap_count
        total_storage += storage

        workload_inventory.append({
            "workload": wl.value,
            "objects": obj_count,
            "snapshots": snap_count,
            "storage_bytes": storage,
            "storage_gb": round(storage / (1024 ** 3), 3),
            "last_backup": last_backup.isoformat() if last_backup else None,
        })

    # Active/running jobs
    active_jobs = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.tenant_id == tenant_id,
            BackupJob.status.in_([JobStatus.IN_PROGRESS, JobStatus.QUEUED]),
        )
    )).scalar() or 0

    # SLA policies and retention timeline
    sla_result = await db.execute(
        select(SLAPolicy).join(
            ProtectedObject, ProtectedObject.sla_policy_id == SLAPolicy.id
        ).where(
            ProtectedObject.tenant_id == tenant_id,
        ).distinct()
    )
    policies = sla_result.scalars().all()

    retention_timeline = []
    for p in policies:
        obj_count = (await db.execute(
            select(func.count(ProtectedObject.id)).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.sla_policy_id == p.id,
            )
        )).scalar() or 0

        purge_date = now + timedelta(days=p.retention_days)
        retention_timeline.append({
            "policy_name": p.name,
            "retention_days": p.retention_days,
            "worm_enabled": bool(getattr(p, 'worm_enabled', 0)),
            "objects_covered": obj_count,
            "data_purge_date": purge_date.strftime("%Y-%m-%d"),
            "days_until_purge": p.retention_days,
        })

    # Blockers
    blockers = []
    if active_jobs > 0:
        blockers.append({
            "type": "active_jobs",
            "message": f"{active_jobs} backup job(s) currently running",
            "action": "Wait for jobs to complete or cancel them before offboarding",
        })

    worm_policies = [p for p in policies if getattr(p, 'worm_enabled', 0)]
    if worm_policies:
        blockers.append({
            "type": "worm_lock",
            "message": f"{len(worm_policies)} WORM-locked SLA policy(ies) — data cannot be deleted until retention expires",
            "action": "WORM data will be retained even after offboarding. This is by design for compliance.",
        })

    return {
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "status": tenant.status.value,
            "ms_tenant_id": tenant.ms_tenant_id,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        },
        "data_inventory": {
            "total_objects": total_objects,
            "total_snapshots": total_snapshots,
            "total_storage_bytes": total_storage,
            "total_storage_gb": round(total_storage / (1024 ** 3), 3),
            "workloads": workload_inventory,
        },
        "active_jobs": active_jobs,
        "retention_timeline": sorted(retention_timeline, key=lambda r: r["days_until_purge"]),
        "blockers": blockers,
        "can_offboard": active_jobs == 0,
        "post_offboard": {
            "backups_accessible": True,
            "new_backups_stopped": True,
            "data_export_available": True,
            "auto_purge_after_retention": True,
            "reactivation_possible": True,
        },
    }


@router.post("/offboard/{tenant_id}")
async def offboard_tenant(
    tenant_id: int,
    confirm: bool = Query(False, description="Must be true to execute offboard"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_msp_permission),
):
    """Execute offboard — deactivate tenant, stop new backups, preserve existing data.

    Requires confirm=true to prevent accidental offboarding.
    """
    from fastapi import HTTPException

    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to execute offboard. Use GET /offboard/{id}/pre-check first.")

    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.status == TenantStatus.INACTIVE:
        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "status": "already_inactive",
            "message": "Tenant is already offboarded",
        }

    # Check for active jobs
    active_jobs = (await db.execute(
        select(func.count(BackupJob.id)).where(
            BackupJob.tenant_id == tenant_id,
            BackupJob.status.in_([JobStatus.IN_PROGRESS, JobStatus.QUEUED]),
        )
    )).scalar() or 0

    if active_jobs > 0:
        raise HTTPException(status_code=409, detail=f"Cannot offboard: {active_jobs} job(s) still running. Wait or cancel first.")

    now = datetime.utcnow()
    tenant.status = TenantStatus.INACTIVE
    tenant.updated_at = now
    await db.commit()

    # Calculate retention info
    sla_result = await db.execute(
        select(SLAPolicy).join(
            ProtectedObject, ProtectedObject.sla_policy_id == SLAPolicy.id
        ).where(ProtectedObject.tenant_id == tenant_id).distinct()
    )
    policies = sla_result.scalars().all()
    max_retention = max((p.retention_days for p in policies), default=30)
    purge_date = now + timedelta(days=max_retention)

    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
        "status": "offboarded",
        "deactivated_at": now.isoformat(),
        "what_happened": [
            "Tenant status set to INACTIVE",
            "Scheduled backups stopped — no new backups will run",
            "Existing backup data preserved per SLA retention policies",
            "Connector credentials retained (encrypted) for potential reactivation",
        ],
        "retention": {
            "max_retention_days": max_retention,
            "data_purge_date": purge_date.strftime("%Y-%m-%d"),
            "data_accessible_until": purge_date.isoformat(),
            "worm_data": "WORM-locked data retained until lock expires regardless of offboard",
        },
        "next_steps": [
            "Export any data you need before the retention period ends",
            "To reactivate this tenant, use the tenant management API",
            f"All backup data will be eligible for purge after {purge_date.strftime('%B %d, %Y')}",
        ],
    }
