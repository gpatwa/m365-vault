#!/usr/bin/env python3
"""Seed demo data for Shieldio — creates realistic sample data for prospect demos.

Usage:
  make seed-demo
  # or: docker compose exec backend python3 scripts/seed-demo.py

Creates:
- 1 demo tenant ("Acme Corporation")
- 25 protected objects across 5 workloads
- 60+ backup jobs (mix of completed/failed/partial over 14 days)
- 200+ snapshot items
- 30+ failed items with error categories
- Anomaly events + health baselines
- Audit log entries
- SLA policies (Daily + Hourly)
"""
import asyncio
import json
import random
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import async_session, init_db
from app.models.tenant import Tenant, TenantStatus
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.sla_policy import SLAPolicy
from app.models.backup_job import BackupJob, JobStatus
from app.models.snapshot import (
    Snapshot, SnapshotType, SnapshotStatus, SnapshotItem, ItemType,
    FailedItem, ErrorCategory,
)
from app.models.health_baseline import HealthBaseline, AnomalyEvent
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.services.auth import hash_password
from sqlalchemy import select

# Demo data constants
DEMO_USERS = [
    ("Sarah Chen", "sarahc@acmecorp.com"),
    ("Marcus Johnson", "marcusj@acmecorp.com"),
    ("Emily Rodriguez", "emilyr@acmecorp.com"),
    ("David Kim", "davidk@acmecorp.com"),
    ("Lisa Thompson", "lisat@acmecorp.com"),
    ("James Wilson", "jamesw@acmecorp.com"),
    ("Priya Patel", "priyap@acmecorp.com"),
    ("Alex Turner", "alext@acmecorp.com"),
]

SHAREPOINT_SITES = [
    "Marketing Hub", "Engineering Wiki", "Sales Pipeline",
    "HR Portal", "Finance Reports", "Executive Dashboard",
]

TEAMS = [
    "Engineering Team", "Marketing Team", "Sales Operations",
]

EMAIL_SUBJECTS = [
    "Q4 Budget Review — Final Numbers",
    "RE: Project Deadline Update",
    "FW: Client Feedback Summary",
    "Meeting Notes — Board Review",
    "Action Items from Strategy Session",
    "Updated Contract — v3 Final",
    "Quarterly Performance Report",
    "New Hire Onboarding Checklist",
    "Security Incident — Follow Up",
    "Annual Review Templates",
]

FILE_NAMES = [
    "Q4_Budget_Final.xlsx", "Project_Timeline.pptx", "Client_Contracts/",
    "Brand_Guidelines_v2.pdf", "Architecture_Diagram.vsdx",
    "Marketing_Campaign_Q1.docx", "API_Documentation.md",
    "Employee_Handbook_2026.pdf", "Sales_Pipeline_Report.xlsx",
    "Disaster_Recovery_Plan.docx",
]


async def seed():
    await init_db()

    async with async_session() as db:
        # Check if demo data already exists
        existing = await db.execute(
            select(Tenant).where(Tenant.name == "Acme Corporation")
        )
        if existing.scalar_one_or_none():
            print("⚠️  Demo data already exists. Run 'make seed-clean' first to reset.")
            return

        print("🌱 Seeding demo data for Shieldio...")
        now = datetime.utcnow()

        # ── 1. Demo Accounts ──
        DEMO_ACCOUNTS = [
            {"username": "admin", "email": "admin@shieldio.local", "password": "Admin123",
             "full_name": "Platform Admin", "role": UserRole.ADMIN,
             "purpose": "Full product with data — dashboard, all features"},
            {"username": "demo", "email": "demo@shieldio.local", "password": "ShieldiDemo2026!",
             "full_name": "Demo User", "role": UserRole.ADMIN,
             "purpose": "Clean onboarding Storyline — fresh tenant setup"},
            {"username": "prospect", "email": "prospect@shieldio.local", "password": "Prospect2026!",
             "full_name": "Prospect Demo", "role": UserRole.ADMIN,
             "purpose": "Post-auth onboarding — tenant connected, start at discovery"},
            {"username": "msp", "email": "msp@shieldio.local", "password": "MSPDemo2026!",
             "full_name": "MSP Partner", "role": UserRole.MSP_ADMIN,
             "purpose": "MSP evaluation — multi-tenant dashboard, billing, branding"},
            {"username": "viewer", "email": "viewer@shieldio.local", "password": "Viewer2026!",
             "full_name": "Compliance Auditor", "role": UserRole.VIEWER,
             "purpose": "Read-only — browse dashboard, reports, audit log"},
        ]

        for acct in DEMO_ACCOUNTS:
            existing = await db.execute(select(User).where(User.username == acct["username"]))
            if not existing.scalar_one_or_none():
                user = User(
                    username=acct["username"], email=acct["email"],
                    password_hash=hash_password(acct["password"]),
                    full_name=acct["full_name"], role=acct["role"], is_active=1,
                )
                db.add(user)
                print(f"  ✅ {acct['role'].value:10} {acct['username']:8} / {acct['password']:20} — {acct['purpose']}")

        # ── 1b. Prospect Tenant (connected but not discovered) ──
        prospect_tenant_exists = await db.execute(
            select(Tenant).where(Tenant.ms_tenant_id == "prospect-contoso-demo")
        )
        if not prospect_tenant_exists.scalar_one_or_none():
            prospect_tenant = Tenant(
                name="Contoso Corp",
                ms_tenant_id="prospect-contoso-demo",
                client_id="demo-prospect-client-id",
                client_secret_encrypted="demo-encrypted-secret",
                status=TenantStatus.ONBOARDING,
            )
            db.add(prospect_tenant)
            await db.flush()
            print(f"  ✅ Prospect tenant: Contoso Corp (id={prospect_tenant.id}) — connected, awaiting discovery")

        # ── 2. SLA Policies ──
        daily_sla = SLAPolicy(
            name="Daily Backup", description="Standard daily backup with 30-day retention",
            backup_frequency_hours=24, retention_days=30, priority=5, is_active=1,
        )
        hourly_sla = SLAPolicy(
            name="Hourly Critical", description="Hourly backup for critical data with 90-day retention",
            backup_frequency_hours=1, retention_days=90, priority=1, is_active=1,
            worm_enabled=1,
        )
        db.add(daily_sla)
        db.add(hourly_sla)
        await db.flush()
        print(f"  ✅ SLA Policies: Daily (id={daily_sla.id}), Hourly Critical (id={hourly_sla.id})")

        # ── 3. Demo Tenant ──
        tenant = Tenant(
            name="Acme Corporation",
            ms_tenant_id="demo-acme-00000000-0000-0000-0000-000000000000",
            client_id="demo-client-id",
            client_secret_encrypted="demo-encrypted-secret",
            status=TenantStatus.ACTIVE,
            last_discovery_at=now - timedelta(hours=2),
            total_mailboxes=len(DEMO_USERS),
            total_onedrives=len(DEMO_USERS),
            total_sites=len(SHAREPOINT_SITES),
            total_teams=len(TEAMS),
            total_entra_objects=1,
        )
        db.add(tenant)
        await db.flush()
        tenant_id = tenant.id
        print(f"  ✅ Tenant: Acme Corporation (id={tenant_id})")

        # ── 4. Protected Objects ──
        objects = []

        # Exchange mailboxes
        for name, email in DEMO_USERS:
            obj = ProtectedObject(
                tenant_id=tenant_id, workload_type=WorkloadType.EXCHANGE,
                ms_object_id=f"demo-user-{email.split('@')[0]}",
                display_name=f"{name} (Mailbox)", email=email,
                sla_policy_id=daily_sla.id, status=ProtectionStatus.PROTECTED,
                last_backup_at=now - timedelta(hours=random.randint(1, 12)),
                last_backup_status="success",
                total_items_backed_up=random.randint(50, 500),
                total_size_bytes=random.randint(1000000, 50000000),
            )
            db.add(obj)
            objects.append(obj)

        # OneDrive accounts
        for name, email in DEMO_USERS:
            obj = ProtectedObject(
                tenant_id=tenant_id, workload_type=WorkloadType.ONEDRIVE,
                ms_object_id=f"demo-drive-{email.split('@')[0]}",
                display_name=f"{name} (OneDrive)", email=email,
                sla_policy_id=daily_sla.id, status=ProtectionStatus.PROTECTED,
                last_backup_at=now - timedelta(hours=random.randint(1, 12)),
                last_backup_status="success",
                total_items_backed_up=random.randint(20, 200),
                total_size_bytes=random.randint(5000000, 100000000),
            )
            db.add(obj)
            objects.append(obj)

        # SharePoint sites
        for site_name in SHAREPOINT_SITES:
            obj = ProtectedObject(
                tenant_id=tenant_id, workload_type=WorkloadType.SHAREPOINT,
                ms_object_id=f"demo-site-{site_name.lower().replace(' ', '-')}",
                display_name=f"{site_name} (SharePoint)",
                site_url=f"https://acmecorp.sharepoint.com/sites/{site_name.replace(' ', '')}",
                sla_policy_id=daily_sla.id, status=ProtectionStatus.PROTECTED,
                last_backup_at=now - timedelta(hours=random.randint(1, 24)),
                last_backup_status="success",
                total_items_backed_up=random.randint(10, 100),
                total_size_bytes=random.randint(2000000, 30000000),
            )
            db.add(obj)
            objects.append(obj)

        # Teams
        for team_name in TEAMS:
            obj = ProtectedObject(
                tenant_id=tenant_id, workload_type=WorkloadType.TEAMS,
                ms_object_id=f"demo-team-{team_name.lower().replace(' ', '-')}",
                display_name=f"{team_name} (Team)",
                sla_policy_id=daily_sla.id, status=ProtectionStatus.PROTECTED,
                last_backup_at=now - timedelta(hours=random.randint(1, 12)),
                last_backup_status="success",
                total_items_backed_up=random.randint(30, 200),
                total_size_bytes=random.randint(500000, 10000000),
            )
            db.add(obj)
            objects.append(obj)

        # Entra ID
        entra_obj = ProtectedObject(
            tenant_id=tenant_id, workload_type=WorkloadType.ENTRA_ID,
            ms_object_id="demo-entra-acme",
            display_name="Acme Corporation (Entra ID)",
            sla_policy_id=hourly_sla.id, status=ProtectionStatus.PROTECTED,
            last_backup_at=now - timedelta(minutes=45),
            last_backup_status="success",
            total_items_backed_up=188,
            total_size_bytes=95000,
        )
        db.add(entra_obj)
        objects.append(entra_obj)

        await db.flush()
        print(f"  ✅ Protected Objects: {len(objects)} across 5 workloads")

        # ── 5. Backup Jobs + Snapshots ──
        job_count = 0
        snapshot_count = 0
        item_count = 0

        for days_ago in range(14, 0, -1):
            for obj in objects:
                # Not every object gets a job every day
                if random.random() > 0.7:
                    continue

                job_time = now - timedelta(days=days_ago, hours=random.randint(0, 12))
                duration = timedelta(minutes=random.randint(1, 15))

                # 85% success, 10% partial, 5% failed
                r = random.random()
                if r < 0.85:
                    status = JobStatus.COMPLETED
                    error = None
                elif r < 0.95:
                    status = JobStatus.PARTIAL
                    error = "Some items failed"
                else:
                    status = JobStatus.FAILED
                    error = random.choice([
                        "Graph API throttled: 429 Too Many Requests",
                        "Token expired: 401 Unauthorized",
                        "Network timeout after 30s",
                    ])

                items = random.randint(5, 80)
                size = items * random.randint(500, 5000)

                job = BackupJob(
                    tenant_id=tenant_id, workload_type=obj.workload_type.value,
                    sla_policy_id=obj.sla_policy_id, status=status,
                    started_at=job_time, completed_at=job_time + duration,
                    objects_total=1, objects_processed=1 if status != JobStatus.FAILED else 0,
                    objects_failed=1 if status == JobStatus.FAILED else 0,
                    total_items=items, total_size_bytes=size,
                    error_message=error,
                    retry_count=random.randint(0, 2) if status == JobStatus.FAILED else 0,
                    max_retries=3,
                )
                db.add(job)
                job_count += 1

                # Create snapshot for completed/partial jobs
                if status in (JobStatus.COMPLETED, JobStatus.PARTIAL):
                    snap = Snapshot(
                        protected_object_id=obj.id,
                        snapshot_type=SnapshotType.INCREMENTAL if days_ago < 13 else SnapshotType.FULL,
                        status=SnapshotStatus.COMPLETED,
                        started_at=job_time, completed_at=job_time + duration,
                        item_count=items, size_bytes=size,
                    )
                    db.add(snap)
                    await db.flush()
                    snapshot_count += 1

                    # Add some snapshot items
                    for i in range(min(items, 5)):
                        item_type = random.choice([
                            ItemType.EMAIL, ItemType.FILE, ItemType.CALENDAR_EVENT,
                            ItemType.CONTACT, ItemType.LIST_ITEM,
                        ])
                        name = random.choice(EMAIL_SUBJECTS if item_type == ItemType.EMAIL else FILE_NAMES)
                        si = SnapshotItem(
                            snapshot_id=snap.id, item_type=item_type,
                            ms_item_id=f"demo-item-{snap.id}-{i}",
                            name=name, path=random.choice(["Inbox", "Documents", "Calendar", "Contacts"]),
                            size_bytes=random.randint(500, 50000),
                        )
                        db.add(si)
                        item_count += 1

        print(f"  ✅ Backup Jobs: {job_count}, Snapshots: {snapshot_count}, Items: {item_count}")

        # Collect snapshot IDs for failed items
        snap_ids_result = await db.execute(
            select(Snapshot.id).where(Snapshot.status == SnapshotStatus.COMPLETED).limit(50)
        )
        valid_snap_ids = [r[0] for r in snap_ids_result.all()]
        if not valid_snap_ids:
            valid_snap_ids = [1]  # fallback

        # ── 6. Failed Items ──
        error_categories = list(ErrorCategory)
        failed_count = 0
        for _ in range(35):
            cat = random.choice(error_categories)
            fi = FailedItem(
                snapshot_id=random.choice(valid_snap_ids),
                protected_object_id=random.choice(objects).id,
                ms_item_id=f"demo-failed-{_}",
                item_type=random.choice(["email", "file", "calendar_event"]),
                item_name=random.choice(EMAIL_SUBJECTS + FILE_NAMES),
                item_path=random.choice(["Inbox", "Documents", "Sent Items"]),
                error_category=cat,
                error_message=f"Demo error: {cat.value}",
                error_code=str(random.choice([403, 404, 429, 500, 503])),
                can_retry=cat in (ErrorCategory.THROTTLED, ErrorCategory.TIMEOUT, ErrorCategory.SERVER_ERROR),
                retries_attempted=random.randint(0, 3),
                is_resolved=random.choice([0, 0, 0, 1]),
                created_at=now - timedelta(hours=random.randint(1, 168)),
            )
            db.add(fi)
            failed_count += 1
        print(f"  ✅ Failed Items: {failed_count}")

        # ── 7. Anomalies ──
        anomalies = [
            AnomalyEvent(
                tenant_id=tenant_id, workload_type="exchange", metric_name="error_rate",
                expected_value=2.5, actual_value=18.0, z_score=3.1,
                severity="critical", message="Exchange error rate spiked to 18% (baseline: 2.5%)",
                detected_at=now - timedelta(hours=6),
            ),
            AnomalyEvent(
                tenant_id=tenant_id, workload_type="onedrive", metric_name="item_count",
                expected_value=45.0, actual_value=12.0, z_score=2.8,
                severity="warning", message="OneDrive item count dropped 73% — possible bulk deletion",
                detected_at=now - timedelta(hours=3),
            ),
            AnomalyEvent(
                tenant_id=tenant_id, workload_type="sharepoint", metric_name="size_bytes",
                expected_value=50000.0, actual_value=150000.0, z_score=2.5,
                severity="warning", message="SharePoint backup size tripled — possible bulk upload",
                resolved=1, detected_at=now - timedelta(days=2),
            ),
        ]
        for a in anomalies:
            db.add(a)
        print(f"  ✅ Anomalies: {len(anomalies)} ({sum(1 for a in anomalies if not a.resolved)} active)")

        # ── 8. Health Baselines ──
        for wl in ["exchange", "onedrive", "sharepoint", "teams", "entra_id"]:
            for metric in ["item_count", "size_bytes", "error_rate"]:
                bl = HealthBaseline(
                    tenant_id=tenant_id, workload_type=wl, metric_name=metric,
                    avg_value=random.uniform(10, 100), std_dev=random.uniform(2, 15),
                    min_value=random.uniform(1, 10), max_value=random.uniform(100, 500),
                    sample_count=random.randint(10, 50),
                    last_updated=now - timedelta(hours=1),
                )
                db.add(bl)
        print("  ✅ Health Baselines: 15 (5 workloads × 3 metrics)")

        # ── 9. Audit Logs ──
        audit_actions = [
            ("tenant.created", "Tenant 'Acme Corporation' onboarded"),
            ("discovery.completed", "Discovery found 26 objects across 5 workloads"),
            ("sla.assigned", "Daily Backup policy assigned to all objects"),
            ("backup.completed", "Full backup completed: 26 objects, 1,847 items"),
            ("anomaly.detected", "Exchange error rate spike detected"),
            ("user.login", "Admin logged in from 192.168.1.100"),
            ("backup.failed", "OneDrive backup failed: token expired"),
            ("backup.retried", "OneDrive backup retry succeeded"),
        ]
        for action, detail in audit_actions:
            al = AuditLog(
                action=action, details=detail,
                user_id=1, severity="info" if "completed" in action or "login" in action else "warning",
                resource_type=action.split(".")[0],
                ip_address="192.168.1.100",
                timestamp=now - timedelta(hours=random.randint(1, 48)),
            )
            db.add(al)
        print(f"  ✅ Audit Logs: {len(audit_actions)}")

        await db.commit()

        # ── Phase 2.5: Org Context + MVB Plans ──
        print("\n  ── Org Context + Smart Recovery ──")
        from app.models.org_context import UserContext, SiteContext, RecoveryPlan

        # Create user context with realistic criticality
        USER_PROFILES = [
            {"name": "Sarah Chen", "email": "sarahc@acmecorp.com", "dept": "Executive", "title": "CEO", "ga": 1, "priv": 1, "score": 95, "tier": "critical"},
            {"name": "Marcus Johnson", "email": "marcusj@acmecorp.com", "dept": "Finance", "title": "CFO", "ga": 0, "priv": 1, "score": 88, "tier": "critical"},
            {"name": "Emily Rodriguez", "email": "emilyr@acmecorp.com", "dept": "Legal", "title": "General Counsel", "ga": 0, "priv": 0, "score": 82, "tier": "critical"},
            {"name": "David Kim", "email": "davidk@acmecorp.com", "dept": "Engineering", "title": "VP Engineering", "ga": 0, "priv": 1, "score": 75, "tier": "high"},
            {"name": "Lisa Thompson", "email": "lisat@acmecorp.com", "dept": "HR", "title": "HR Director", "ga": 0, "priv": 0, "score": 68, "tier": "high"},
            {"name": "James Wilson", "email": "jamesw@acmecorp.com", "dept": "Sales", "title": "Sales Manager", "ga": 0, "priv": 0, "score": 45, "tier": "medium"},
            {"name": "Priya Patel", "email": "priyap@acmecorp.com", "dept": "Marketing", "title": "Marketing Specialist", "ga": 0, "priv": 0, "score": 35, "tier": "low"},
            {"name": "Alex Turner", "email": "alext@acmecorp.com", "dept": "Engineering", "title": "Junior Developer", "ga": 0, "priv": 0, "score": 22, "tier": "low"},
        ]

        for i, prof in enumerate(USER_PROFILES):
            # Find matching protected object
            po = None
            for obj in objects:
                if obj.display_name and prof["name"].split()[0] in obj.display_name and obj.workload_type == WorkloadType.EXCHANGE:
                    po = obj
                    break

            ctx = UserContext(
                tenant_id=tenant.id,
                protected_object_id=po.id if po else None,
                ms_user_id=f"user-{prof['name'].lower().replace(' ', '-')}",
                display_name=prof["name"],
                email=prof["email"],
                job_title=prof["title"],
                department=prof["dept"],
                is_global_admin=prof["ga"],
                has_privileged_role=prof["priv"],
                privileged_roles=json.dumps(["Global Administrator"] if prof["ga"] else (["User Administrator"] if prof["priv"] else [])),
                direct_reports_count=random.randint(0, 12) if prof["score"] > 60 else random.randint(0, 3),
                last_sign_in_at=now - timedelta(hours=random.randint(1, 48)),
                criticality_score=prof["score"],
                criticality_tier=prof["tier"],
                signals=json.dumps({"user_importance": int(prof["score"] * 0.4), "data_sensitivity": int(prof["score"] * 0.3), "activity_level": int(prof["score"] * 0.2), "floor_applied": "global_admin>=90" if prof["ga"] else None}),
                synced_at=now,
                computed_at=now,
            )
            db.add(ctx)

            # Also set criticality on the protected object
            if po:
                po.criticality_score = prof["score"]
                po.criticality_tier = prof["tier"]

        # Site context
        SITE_PROFILES = [
            {"name": "Finance Reports", "score": 78, "tier": "high", "visitors": 45, "files": 230, "external": 1},
            {"name": "Executive Dashboard", "score": 85, "tier": "critical", "visitors": 12, "files": 50, "external": 0},
            {"name": "Marketing Hub", "score": 42, "tier": "medium", "visitors": 80, "files": 500, "external": 1},
            {"name": "Engineering Wiki", "score": 55, "tier": "medium", "visitors": 60, "files": 1200, "external": 0},
            {"name": "HR Portal", "score": 65, "tier": "high", "visitors": 30, "files": 100, "external": 0},
            {"name": "Sales Pipeline", "score": 48, "tier": "medium", "visitors": 25, "files": 80, "external": 1},
        ]

        for sprof in SITE_PROFILES:
            sp_obj = None
            for obj in objects:
                if obj.display_name and sprof["name"] in obj.display_name and obj.workload_type == WorkloadType.SHAREPOINT:
                    sp_obj = obj
                    break

            sc = SiteContext(
                tenant_id=tenant.id,
                protected_object_id=sp_obj.id if sp_obj else None,
                ms_site_id=f"site-{sprof['name'].lower().replace(' ', '-')}",
                site_name=sprof["name"],
                site_url=f"https://acmecorp.sharepoint.com/sites/{sprof['name'].lower().replace(' ', '-')}",
                unique_visitors=sprof["visitors"],
                file_count=sprof["files"],
                external_sharing_enabled=sprof["external"],
                criticality_score=sprof["score"],
                criticality_tier=sprof["tier"],
                signals=json.dumps({"traffic": sprof["visitors"], "files": sprof["files"]}),
                synced_at=now,
                computed_at=now,
            )
            db.add(sc)

            if sp_obj:
                sp_obj.criticality_score = sprof["score"]
                sp_obj.criticality_tier = sprof["tier"]

        print(f"  ✅ User Context: {len(USER_PROFILES)} users with criticality scores")
        print(f"  ✅ Site Context: {len(SITE_PROFILES)} sites with criticality scores")

        # Pre-computed MVB Recovery Plan
        mvb_phases = [
            {"phase": 1, "name": "Identity Controls", "priority": "immediate", "object_count": 1, "item_count": 192, "size_bytes": 118784, "estimated_minutes": 5, "reason": "Restore identity controls first to prevent re-compromise.", "object_summaries": [{"object_name": "Acme Corp (Entra ID)", "workload": "entra_id", "criticality_score": 90, "criticality_tier": "critical", "item_count": 192}]},
            {"phase": 2, "name": "Minimum Viable Business", "priority": "critical", "object_count": 5, "item_count": 85, "size_bytes": 52000, "estimated_minutes": 15, "reason": "Restore CEO, CFO, and Legal Counsel — the minimum set needed for business continuity.", "object_summaries": [
                {"object_name": "Sarah Chen (Mailbox)", "workload": "exchange", "criticality_score": 95, "criticality_tier": "critical", "item_count": 23},
                {"object_name": "Marcus Johnson (Mailbox)", "workload": "exchange", "criticality_score": 88, "criticality_tier": "critical", "item_count": 18},
                {"object_name": "Emily Rodriguez (Mailbox)", "workload": "exchange", "criticality_score": 82, "criticality_tier": "critical", "item_count": 15},
                {"object_name": "Sarah Chen (OneDrive)", "workload": "onedrive", "criticality_score": 95, "criticality_tier": "critical", "item_count": 15},
                {"object_name": "Executive Dashboard", "workload": "sharepoint", "criticality_score": 85, "criticality_tier": "critical", "item_count": 14},
            ]},
            {"phase": 3, "name": "High-Priority Data", "priority": "high", "object_count": 6, "item_count": 120, "size_bytes": 75000, "estimated_minutes": 30, "reason": "Restore VP Engineering, HR Director, and high-traffic sites.", "object_summaries": [
                {"object_name": "David Kim (Mailbox)", "workload": "exchange", "criticality_score": 75, "criticality_tier": "high", "item_count": 20},
                {"object_name": "Lisa Thompson (Mailbox)", "workload": "exchange", "criticality_score": 68, "criticality_tier": "high", "item_count": 18},
                {"object_name": "Finance Reports", "workload": "sharepoint", "criticality_score": 78, "criticality_tier": "high", "item_count": 30},
                {"object_name": "HR Portal", "workload": "sharepoint", "criticality_score": 65, "criticality_tier": "high", "item_count": 25},
            ]},
            {"phase": 4, "name": "Full Recovery", "priority": "normal", "object_count": 14, "item_count": 350, "size_bytes": 200000, "estimated_minutes": 120, "reason": "Complete recovery of remaining 14 objects.", "object_summaries": []},
        ]

        plan = RecoveryPlan(
            tenant_id=tenant.id,
            name="MVB Recovery Plan",
            plan_type="mvb",
            status="ready",
            mvb_user_count=3,
            mvb_object_count=6,
            total_object_count=26,
            phases_json=json.dumps(mvb_phases),
            total_items=747,
            total_size_bytes=445784,
            estimated_minutes=170,
            reasoning="Generated 4-phase recovery plan for 26 objects. MVB set: 3 critical users (CEO, CFO, General Counsel) + Executive Dashboard will be restored first for business continuity. Identity controls restored immediately. Full recovery of remaining 14 objects in Phase 4.",
            computed_at=now,
            stale_after=now + timedelta(hours=6),
        )
        db.add(plan)
        print(f"  ✅ MVB Recovery Plan: 4 phases, 3 MVB users, est. 170 min")

        await db.commit()

        print()
        print("═══ DEMO DATA READY ═══")
        print(f"  Tenant: Acme Corporation")
        print(f"  Objects: {len(objects)} across 5 workloads")
        print(f"  Jobs: {job_count} (14 days of history)")
        print(f"  Snapshots: {snapshot_count}")
        print(f"  Items: {item_count}")
        print(f"  Org Context: {len(USER_PROFILES)} users + {len(SITE_PROFILES)} sites scored")
        print(f"  MVB Plan: 4 phases (Identity → MVB → High → Full)")
        print(f"  Login: admin / admin123 or demo / ShieldiDemo2026!")
        print()


if __name__ == "__main__":
    asyncio.run(seed())
