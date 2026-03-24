#!/usr/bin/env python3
"""
Shieldio — Data Simulation Script

Exercises the full compression + dedup + encryption pipeline by simulating
three real-world backup scenarios:

  1. Initial tenant onboarding with full data ingestion
  2. Incremental backup after first ingestion (with dedup)
  3. Large file backup to trigger CDC chunking

Usage:
    rm -f backend/m365_protection.db
    cd backend && python3 ../scripts/simulate_backup_data.py
"""
import asyncio
import json
import os
import random
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import engine, async_session, init_db  # noqa: E402
from app.config import settings  # noqa: E402

# Models
from app.models.user import User, UserRole  # noqa: E402
from app.models.tenant import Tenant, TenantStatus  # noqa: E402
from app.models.sla_policy import SLAPolicy  # noqa: E402
from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus  # noqa: E402
from app.models.backup_job import BackupJob, JobStatus  # noqa: E402
from app.models.snapshot import (  # noqa: E402
    Snapshot, SnapshotType, SnapshotStatus,
    SnapshotItem, ItemType,
    FailedItem, ErrorCategory, ERROR_RESOLUTION_GUIDE,
)
from app.models.restore_job import RestoreJob, RestoreType, RestoreStatus  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.dedup import DedupEntry  # noqa: E402

# Services
from app.services.auth import hash_password  # noqa: E402
from app.services.encryption import encryption_service  # noqa: E402
from app.services.storage import StorageService, StoreResult  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  Realistic sample data generators
# ═══════════════════════════════════════════════════════════════════════════

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
)

EMAIL_SUBJECTS = [
    "Q1 Project Roadmap Review",
    "Weekly Status Update — Sprint 14",
    "Updated Security Policy Document",
    "Customer Feedback Analysis Report",
    "Team Building Event Next Friday",
    "Budget Approval for Cloud Migration",
    "API Documentation Update v2.3",
    "Production Incident — Resolved",
    "New Hiring Plan for Engineering",
    "All Hands Meeting Recap",
    "Infrastructure Cost Optimization",
    "Release Notes — v3.5.0",
    "Vendor Contract Renewal",
    "Data Compliance Audit Results",
    "Performance Review Schedule",
]

NAMES = [
    ("Alex Johnson", "alex.johnson@contoso.com"),
    ("Sarah Chen", "sarah.chen@contoso.com"),
    ("Mike Williams", "mike.williams@contoso.com"),
    ("Emily Davis", "emily.davis@contoso.com"),
    ("James Wilson", "james.wilson@contoso.com"),
]


def make_email(subject_idx: int, sender_idx: int = 0, folder: str = "Inbox") -> dict:
    """Generate a realistic email message JSON."""
    sender = NAMES[sender_idx % len(NAMES)]
    recipients = [NAMES[(sender_idx + 1) % len(NAMES)], NAMES[(sender_idx + 2) % len(NAMES)]]
    body_text = LOREM * random.randint(3, 8)
    return {
        "id": f"AAMkAG{''.join(random.choices(string.ascii_letters, k=20))}",
        "subject": EMAIL_SUBJECTS[subject_idx % len(EMAIL_SUBJECTS)],
        "from": {"emailAddress": {"name": sender[0], "address": sender[1]}},
        "sender": {"emailAddress": {"name": sender[0], "address": sender[1]}},
        "toRecipients": [{"emailAddress": {"name": r[0], "address": r[1]}} for r in recipients],
        "ccRecipients": [],
        "receivedDateTime": (datetime.utcnow() - timedelta(hours=random.randint(1, 168))).isoformat() + "Z",
        "bodyPreview": body_text[:200],
        "body": {"contentType": "text", "content": body_text},
        "hasAttachments": False,
        "importance": random.choice(["normal", "high", "low"]),
        "isRead": random.choice([True, False]),
        "parentFolderId": folder,
    }


def make_calendar_event(idx: int) -> dict:
    start = datetime.utcnow() + timedelta(days=random.randint(1, 30), hours=random.randint(9, 16))
    end = start + timedelta(hours=1)
    subjects = ["Weekly Standup", "Sprint Planning", "Architecture Review", "1:1 Meeting", "All Hands"]
    return {
        "id": f"AAMkAGCal{''.join(random.choices(string.ascii_letters, k=16))}",
        "subject": subjects[idx % len(subjects)],
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "organizer": {"emailAddress": {"name": NAMES[0][0], "address": NAMES[0][1]}},
        "attendees": [{"emailAddress": {"name": n[0], "address": n[1]}} for n in NAMES[1:3]],
        "location": {"displayName": random.choice(["Conference Room A", "Virtual", "Room 301"])},
        "isAllDay": False,
        "body": {"contentType": "text", "content": f"Agenda for {subjects[idx % len(subjects)]}:\n1. Updates\n2. Discussion\n3. Action items"},
    }


def make_contact(idx: int) -> dict:
    name, email = NAMES[idx % len(NAMES)]
    return {
        "id": f"AAMkAGCon{''.join(random.choices(string.ascii_letters, k=16))}",
        "displayName": name,
        "emailAddresses": [{"address": email, "name": name}],
        "businessPhones": [f"+1-555-{random.randint(1000, 9999)}"],
        "mobilePhone": f"+1-555-{random.randint(1000, 9999)}",
        "companyName": "Contoso Corporation",
        "jobTitle": random.choice(["Engineer", "Manager", "Director", "VP", "Analyst"]),
    }


def make_text_file(name: str, size_kb: int = 2) -> bytes:
    """Generate repeating text content."""
    line = f"This is content from {name}. {LOREM}"
    content = (line * ((size_kb * 1024) // len(line) + 1))[:size_kb * 1024]
    return content.encode("utf-8")


def make_json_file(name: str, items: int = 20) -> bytes:
    """Generate a JSON data file."""
    data = {
        "title": name,
        "generated": datetime.utcnow().isoformat(),
        "records": [
            {"id": i, "name": f"Item {i}", "value": random.random() * 1000, "description": LOREM[:100]}
            for i in range(items)
        ],
    }
    return json.dumps(data, indent=2).encode("utf-8")


def make_binary_file(size_bytes: int) -> bytes:
    """Generate random binary data (incompressible)."""
    return os.urandom(size_bytes)


# The shared email for dedup testing
SHARED_EMAIL = make_email(0, sender_idx=0, folder="Inbox")
SHARED_EMAIL["subject"] = "SHARED: Company-wide Policy Update"
SHARED_EMAIL["body"]["content"] = LOREM * 10  # Consistent body for dedup


# ═══════════════════════════════════════════════════════════════════════════
#  Storage helper
# ═══════════════════════════════════════════════════════════════════════════

class Stats:
    total_original = 0
    total_compressed = 0
    total_items = 0
    dedup_hits = 0
    chunked_items = 0


async def store_and_catalog(
    db, storage, tenant_id, workload, object_id, snapshot_id, snapshot,
    item_id, item_type, name, path, data, wrapped_dek,
    filename=None, mime_type=None, **extra_fields
) -> SnapshotItem:
    """Store an item through the pipeline and create a SnapshotItem."""
    result: StoreResult = await storage.store_item(
        tenant_id=tenant_id,
        workload=workload,
        object_id=object_id,
        snapshot_id=snapshot_id,
        item_id=item_id,
        data=data,
        wrapped_dek=wrapped_dek,
        filename=filename,
        mime_type=mime_type,
        db=db,
    )

    Stats.total_original += result.original_size
    Stats.total_compressed += result.compressed_size
    Stats.total_items += 1
    if result.is_duplicate:
        Stats.dedup_hits += 1
    if result.is_chunked:
        Stats.chunked_items += 1

    item = SnapshotItem(
        snapshot_id=snapshot_id,
        item_type=item_type,
        ms_item_id=item_id,
        name=name,
        path=path,
        size_bytes=len(data),
        compressed_size=result.compressed_size,
        content_hash=result.content_hash,
        storage_flags=result.storage_flags,
        blob_path=result.blob_path,
        **extra_fields,
    )
    db.add(item)
    return item


# ═══════════════════════════════════════════════════════════════════════════
#  Main simulation
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    print("=" * 70)
    print("  Shieldio — Data Simulation")
    print("=" * 70)
    print()

    # ── Initialize DB ─────────────────────────────────────────────────
    await init_db()
    print("[OK] Database initialized")

    from app.services.storage_factory import create_storage_backend
    backend = create_storage_backend()
    storage = StorageService(backend)

    async with async_session() as db:
        # ── Step 1: Foundation Data ───────────────────────────────────
        print("\n── Step 1: Seeding foundation data ──")

        # Admin user
        admin = User(
            username="admin",
            email="admin@contoso.com",
            password_hash=hash_password("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        await db.flush()
        print(f"  User: admin (id={admin.id})")

        # Tenant
        tenant = Tenant(
            name="Contoso Corp",
            ms_tenant_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            client_id="app-reg-client-id-contoso-00001",
            client_secret_encrypted=encryption_service.encrypt_dek(b"fake-client-secret-value"),
            status=TenantStatus.ACTIVE,
            total_mailboxes=3,
            total_onedrives=2,
            total_sites=1,
        )
        db.add(tenant)
        await db.flush()
        print(f"  Tenant: {tenant.name} (id={tenant.id})")

        # SLA Policy
        sla = SLAPolicy(
            name="Standard 24h",
            description="Daily backup with 30-day retention",
            backup_frequency_hours=24,
            retention_days=30,
            priority=5,
            is_active=True,
        )
        db.add(sla)
        await db.flush()
        print(f"  SLA: {sla.name} (id={sla.id})")

        # Protected Objects
        mailboxes = []
        for i, (name, email) in enumerate(NAMES[:3]):
            obj = ProtectedObject(
                tenant_id=tenant.id,
                workload_type=WorkloadType.EXCHANGE,
                ms_object_id=f"user-{email.split('@')[0]}-id",
                display_name=name,
                email=email,
                user_principal_name=email,
                status=ProtectionStatus.PROTECTED,
                sla_policy_id=sla.id,
            )
            db.add(obj)
            mailboxes.append(obj)

        onedrives = []
        for i, (name, email) in enumerate(NAMES[:2]):
            obj = ProtectedObject(
                tenant_id=tenant.id,
                workload_type=WorkloadType.ONEDRIVE,
                ms_object_id=f"drive-{email.split('@')[0]}-id",
                display_name=f"{name}'s OneDrive",
                email=email,
                user_principal_name=email,
                status=ProtectionStatus.PROTECTED,
                sla_policy_id=sla.id,
            )
            db.add(obj)
            onedrives.append(obj)

        sp_site = ProtectedObject(
            tenant_id=tenant.id,
            workload_type=WorkloadType.SHAREPOINT,
            ms_object_id="site-contoso-engineering-id",
            display_name="Engineering Hub",
            site_url="https://contoso.sharepoint.com/sites/engineering",
            status=ProtectionStatus.PROTECTED,
            sla_policy_id=sla.id,
        )
        db.add(sp_site)

        await db.flush()
        all_objects = mailboxes + onedrives + [sp_site]
        print(f"  Protected objects: {len(all_objects)} (3 Exchange, 2 OneDrive, 1 SharePoint)")

        # Audit: tenant creation
        db.add(AuditLog(user_id=admin.id, action="tenant.create", resource_type="tenant",
                        resource_id=tenant.id, details=json.dumps({"name": tenant.name}), severity="info"))
        db.add(AuditLog(user_id=admin.id, action="sla.assign", resource_type="sla_policy",
                        resource_id=sla.id, details=json.dumps({"objects": len(all_objects)}), severity="info"))

        # ── Step 2: Full Backup (Use Case 1) ─────────────────────────
        print("\n── Step 2: Full backup (initial ingestion) ──")
        full_start = datetime.utcnow() - timedelta(hours=6)

        async def run_full_backup(obj, workload_name, items_gen_fn):
            job = BackupJob(
                tenant_id=tenant.id, workload_type=obj.workload_type,
                sla_policy_id=sla.id, status=JobStatus.COMPLETED,
                started_at=full_start, completed_at=full_start + timedelta(minutes=random.randint(2, 8)),
                objects_total=1, objects_processed=1, objects_failed=0,
                created_at=full_start,
            )
            db.add(job)
            await db.flush()

            wrapped_dek, _ = await storage.init_snapshot_storage(
                tenant.id, workload_name, obj.ms_object_id, job.id
            )
            snap = Snapshot(
                protected_object_id=obj.id, snapshot_type=SnapshotType.FULL,
                status=SnapshotStatus.COMPLETED, started_at=full_start,
                completed_at=full_start + timedelta(minutes=random.randint(2, 8)),
            )
            db.add(snap)
            await db.flush()

            count, size = await items_gen_fn(
                db, storage, tenant.id, workload_name, obj.ms_object_id,
                snap.id, snap, wrapped_dek
            )

            snap.item_count = count
            snap.size_bytes = size
            job.total_items = count
            job.total_size_bytes = size
            obj.last_backup_at = snap.completed_at
            obj.last_backup_status = "completed"
            obj.total_items_backed_up = count
            obj.total_size_bytes = size
            return snap, wrapped_dek

        # ── Exchange full backups ──
        async def gen_exchange_items(db, storage, tid, wl, oid, sid, snap, dek, num_emails=10, num_cal=3, num_contacts=4, include_shared=False, include_attachments=True):
            count = 0
            size = 0
            # Emails
            for i in range(num_emails):
                msg = make_email(i, sender_idx=i % len(NAMES))
                data = json.dumps(msg, default=str).encode("utf-8")
                item = await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=msg["id"], item_type=ItemType.EMAIL,
                    name=msg["subject"], path="Inbox", data=data,
                    wrapped_dek=dek, mime_type="application/json",
                    subject=msg["subject"],
                    sender=msg["from"]["emailAddress"]["address"],
                    recipients=json.dumps([r["emailAddress"]["address"] for r in msg["toRecipients"]]),
                    received_at=datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00")),
                    metadata_json=json.dumps({"importance": msg["importance"], "isRead": msg["isRead"], "folderId": "Inbox"}),
                )
                count += 1
                size += len(data)

            # Shared email for dedup
            if include_shared:
                data = json.dumps(SHARED_EMAIL, default=str).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=f"shared-{oid[:8]}", item_type=ItemType.EMAIL,
                    name=SHARED_EMAIL["subject"], path="Inbox", data=data,
                    wrapped_dek=dek, mime_type="application/json",
                    subject=SHARED_EMAIL["subject"],
                    sender=SHARED_EMAIL["from"]["emailAddress"]["address"],
                )
                count += 1
                size += len(data)

            # Calendar
            for i in range(num_cal):
                evt = make_calendar_event(i)
                data = json.dumps(evt, default=str).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=evt["id"], item_type=ItemType.CALENDAR_EVENT,
                    name=evt["subject"], path="Calendar", data=data,
                    wrapped_dek=dek, mime_type="application/json",
                    metadata_json=json.dumps({"start": evt["start"], "end": evt["end"]}),
                )
                count += 1
                size += len(data)

            # Contacts
            for i in range(num_contacts):
                ct = make_contact(i)
                data = json.dumps(ct, default=str).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=ct["id"], item_type=ItemType.CONTACT,
                    name=ct["displayName"], path="Contacts", data=data,
                    wrapped_dek=dek, mime_type="application/json",
                    metadata_json=json.dumps({"company": ct["companyName"], "jobTitle": ct["jobTitle"]}),
                )
                count += 1
                size += len(data)

            # Attachments
            if include_attachments:
                pdf_data = make_binary_file(15000)  # ~15KB fake PDF
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id="att-quarterly-report-pdf", item_type=ItemType.FILE,
                    name="Quarterly-Report.pdf", path="attachments", data=pdf_data,
                    wrapped_dek=dek, filename="Quarterly-Report.pdf", mime_type="application/pdf",
                    file_name="Quarterly-Report.pdf",
                )
                count += 1
                size += len(pdf_data)

                docx_data = make_binary_file(20000)  # ~20KB fake docx
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id="att-meeting-notes-docx", item_type=ItemType.FILE,
                    name="Meeting-Notes.docx", path="attachments", data=docx_data,
                    wrapped_dek=dek, filename="Meeting-Notes.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    file_name="Meeting-Notes.docx",
                )
                count += 1
                size += len(docx_data)

            return count, size

        # Mailbox 1: Alex (10 emails, 3 cal, 4 contacts, 2 attachments)
        snap1, dek1 = await run_full_backup(
            mailboxes[0], "exchange",
            lambda *a, **k: gen_exchange_items(*a, num_emails=10, num_cal=3, num_contacts=4, include_attachments=True, **k)
        )
        print(f"  Exchange [{mailboxes[0].display_name}]: {snap1.item_count} items, {snap1.size_bytes:,} bytes")

        # Mailbox 2: Sarah (8 emails, 2 cal, 3 contacts)
        snap2, dek2 = await run_full_backup(
            mailboxes[1], "exchange",
            lambda *a, **k: gen_exchange_items(*a, num_emails=8, num_cal=2, num_contacts=3, include_attachments=False, **k)
        )
        print(f"  Exchange [{mailboxes[1].display_name}]: {snap2.item_count} items, {snap2.size_bytes:,} bytes")

        # Mailbox 3: Mike (6 emails, 1 cal, 2 contacts)
        snap3, dek3 = await run_full_backup(
            mailboxes[2], "exchange",
            lambda *a, **k: gen_exchange_items(*a, num_emails=6, num_cal=1, num_contacts=2, include_attachments=False, **k)
        )
        print(f"  Exchange [{mailboxes[2].display_name}]: {snap3.item_count} items, {snap3.size_bytes:,} bytes")

        # ── OneDrive full backups ──
        async def gen_onedrive_items_alex(db, storage, tid, wl, oid, sid, snap, dek):
            count = 0
            size = 0
            # Folders
            for fname in ["Projects", "Reports"]:
                data = json.dumps({"id": f"folder-{fname}", "name": fname, "folder": {"childCount": 3}}).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=f"folder-{fname}", item_type=ItemType.FOLDER,
                    name=fname, path="/", data=data,
                    wrapped_dek=dek, mime_type="application/json", file_name=fname,
                    metadata_json=json.dumps({"childCount": 3}),
                )
                count += 1

            # Text/JSON files
            files = [
                ("project-roadmap.md", "text/markdown", make_text_file("project-roadmap.md", 2)),
                ("budget.json", "application/json", make_json_file("budget", 30)),
                ("meeting-notes.txt", "text/plain", make_text_file("meeting-notes.txt", 3)),
            ]
            for fname, mime, data in files:
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=f"file-{fname}", item_type=ItemType.FILE,
                    name=fname, path="/Projects", data=data,
                    wrapped_dek=dek, filename=fname, mime_type=mime,
                    file_name=fname,
                )
                count += 1
                size += len(data)

            # Binary files
            arch_data = make_binary_file(50000)
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="file-architecture.png", item_type=ItemType.FILE,
                name="architecture.png", path="/Projects", data=arch_data,
                wrapped_dek=dek, filename="architecture.png", mime_type="image/png",
                file_name="architecture.png",
            )
            count += 1
            size += len(arch_data)

            report_data = make_binary_file(20000)
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="file-report.docx", item_type=ItemType.FILE,
                name="report.docx", path="/Reports", data=report_data,
                wrapped_dek=dek, filename="report.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_name="report.docx",
            )
            count += 1
            size += len(report_data)
            return count, size

        async def gen_onedrive_items_sarah(db, storage, tid, wl, oid, sid, snap, dek):
            count = 0
            size = 0
            # Folder
            data = json.dumps({"id": "folder-Marketing", "name": "Marketing", "folder": {"childCount": 3}}).encode("utf-8")
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="folder-Marketing", item_type=ItemType.FOLDER,
                name="Marketing", path="/", data=data,
                wrapped_dek=dek, mime_type="application/json", file_name="Marketing",
            )
            count += 1

            files = [
                ("marketing-plan.json", "application/json", make_json_file("marketing-plan", 25)),
                ("presentation-notes.txt", "text/plain", make_text_file("presentation-notes.txt", 2)),
            ]
            for fname, mime, fdata in files:
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=f"file-{fname}", item_type=ItemType.FILE,
                    name=fname, path="/Marketing", data=fdata,
                    wrapped_dek=dek, filename=fname, mime_type=mime,
                    file_name=fname,
                )
                count += 1
                size += len(fdata)

            zip_data = make_binary_file(30000)
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="file-campaign-assets.zip", item_type=ItemType.FILE,
                name="campaign-assets.zip", path="/Marketing", data=zip_data,
                wrapped_dek=dek, filename="campaign-assets.zip", mime_type="application/zip",
                file_name="campaign-assets.zip",
            )
            count += 1
            size += len(zip_data)
            return count, size

        snap_od1, dek_od1 = await run_full_backup(onedrives[0], "onedrive", gen_onedrive_items_alex)
        print(f"  OneDrive [{onedrives[0].display_name}]: {snap_od1.item_count} items, {snap_od1.size_bytes:,} bytes")

        snap_od2, dek_od2 = await run_full_backup(onedrives[1], "onedrive", gen_onedrive_items_sarah)
        print(f"  OneDrive [{onedrives[1].display_name}]: {snap_od2.item_count} items, {snap_od2.size_bytes:,} bytes")

        # ── SharePoint full backup ──
        async def gen_sharepoint_items(db, storage, tid, wl, oid, sid, snap, dek):
            count = 0
            size = 0
            # Doc library
            lib_data = json.dumps({"id": "doclib-001", "name": "Documents", "driveType": "documentLibrary"}).encode("utf-8")
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="doclib-001", item_type=ItemType.DOCUMENT_LIBRARY,
                name="Documents", path="/", data=lib_data,
                wrapped_dek=dek, mime_type="application/json",
                metadata_json=json.dumps({"driveType": "documentLibrary"}),
            )
            count += 1

            # Files
            sp_files = [
                ("compliance-checklist.json", "application/json", make_json_file("compliance-checklist", 15)),
                ("project-charter.txt", "text/plain", make_text_file("project-charter.txt", 4)),
                ("technical-spec.md", "text/markdown", make_text_file("technical-spec.md", 5)),
            ]
            for fname, mime, fdata in sp_files:
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=f"spfile-{fname}", item_type=ItemType.FILE,
                    name=fname, path="/Documents", data=fdata,
                    wrapped_dek=dek, filename=fname, mime_type=mime,
                    file_name=fname,
                    metadata_json=json.dumps({"driveId": "doclib-001"}),
                )
                count += 1
                size += len(fdata)

            # List
            list_data = json.dumps({"id": "list-tasks", "displayName": "Project Tasks", "list": {"template": "genericList"}}).encode("utf-8")
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="list-tasks", item_type=ItemType.LIST,
                name="Project Tasks", path="/Lists", data=list_data,
                wrapped_dek=dek, mime_type="application/json",
                metadata_json=json.dumps({"template": "genericList"}),
            )
            count += 1

            # List items
            tasks = ["Set up CI/CD pipeline", "Write API documentation", "Security audit", "Load testing"]
            for i, task in enumerate(tasks):
                li_data = json.dumps({"id": f"task-{i}", "fields": {"Title": task, "Status": random.choice(["Not Started", "In Progress", "Completed"])}}).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=f"listitem-tasks-{i}", item_type=ItemType.LIST_ITEM,
                    name=task, path="/Lists/Project Tasks", data=li_data,
                    wrapped_dek=dek, mime_type="application/json",
                    metadata_json=json.dumps({"Title": task}),
                )
                count += 1
                size += len(li_data)

            return count, size

        snap_sp, dek_sp = await run_full_backup(sp_site, "sharepoint", gen_sharepoint_items)
        print(f"  SharePoint [{sp_site.display_name}]: {snap_sp.item_count} items, {snap_sp.size_bytes:,} bytes")

        # Audit: backup complete
        db.add(AuditLog(user_id=admin.id, action="backup.complete", resource_type="backup_job",
                        details=json.dumps({"workloads": 3, "objects": 6}), severity="info",
                        timestamp=full_start + timedelta(minutes=10)))

        print(f"\n  Full backup totals: {Stats.total_items} items, "
              f"original={Stats.total_original:,}B, compressed={Stats.total_compressed:,}B "
              f"({(1 - Stats.total_compressed / max(Stats.total_original, 1)) * 100:.1f}% saved)")

        # ── Step 3: Incremental Backup (Use Case 2) ──────────────────
        print("\n── Step 3: Incremental backup (with dedup) ──")
        incr_start = datetime.utcnow() - timedelta(hours=2)
        pre_dedup = Stats.dedup_hits

        # Mailbox 1 incremental: 3 new emails + shared email
        async def gen_incr_exchange_1(db, storage, tid, wl, oid, sid, snap, dek):
            count = 0
            size = 0
            for i in range(3):
                msg = make_email(10 + i, sender_idx=i + 2)
                data = json.dumps(msg, default=str).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=msg["id"], item_type=ItemType.EMAIL,
                    name=msg["subject"], path="Inbox", data=data,
                    wrapped_dek=dek, mime_type="application/json",
                    subject=msg["subject"],
                    sender=msg["from"]["emailAddress"]["address"],
                )
                count += 1
                size += len(data)
            # Shared email (should register in dedup index)
            data = json.dumps(SHARED_EMAIL, default=str).encode("utf-8")
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="shared-incr-1", item_type=ItemType.EMAIL,
                name=SHARED_EMAIL["subject"], path="Inbox", data=data,
                wrapped_dek=dek, mime_type="application/json",
                subject=SHARED_EMAIL["subject"],
            )
            count += 1
            size += len(data)
            return count, size

        job_incr1 = BackupJob(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            sla_policy_id=sla.id, status=JobStatus.COMPLETED,
            started_at=incr_start, completed_at=incr_start + timedelta(minutes=1),
            objects_total=1, objects_processed=1, objects_failed=0,
            created_at=incr_start,
        )
        db.add(job_incr1)
        await db.flush()

        wrapped_dek_incr1, _ = await storage.init_snapshot_storage(
            tenant.id, "exchange", mailboxes[0].ms_object_id, job_incr1.id
        )
        snap_incr1 = Snapshot(
            protected_object_id=mailboxes[0].id, snapshot_type=SnapshotType.INCREMENTAL,
            status=SnapshotStatus.COMPLETED, started_at=incr_start,
            completed_at=incr_start + timedelta(minutes=1),
        )
        db.add(snap_incr1)
        await db.flush()

        c, s = await gen_incr_exchange_1(db, storage, tenant.id, "exchange",
                                         mailboxes[0].ms_object_id, snap_incr1.id,
                                         snap_incr1, wrapped_dek_incr1)
        snap_incr1.item_count = c
        snap_incr1.size_bytes = s
        mailboxes[0].last_backup_at = snap_incr1.completed_at
        print(f"  Incremental Exchange [{mailboxes[0].display_name}]: {c} items")

        # Mailbox 2 incremental: 2 new emails + same shared email (DEDUP HIT expected)
        async def gen_incr_exchange_2(db, storage, tid, wl, oid, sid, snap, dek):
            count = 0
            size = 0
            for i in range(2):
                msg = make_email(13 + i, sender_idx=i + 1)
                data = json.dumps(msg, default=str).encode("utf-8")
                await store_and_catalog(
                    db, storage, tid, wl, oid, sid, snap,
                    item_id=msg["id"], item_type=ItemType.EMAIL,
                    name=msg["subject"], path="Inbox", data=data,
                    wrapped_dek=dek, mime_type="application/json",
                    subject=msg["subject"],
                    sender=msg["from"]["emailAddress"]["address"],
                )
                count += 1
                size += len(data)
            # Same shared email (dedup hit!)
            data = json.dumps(SHARED_EMAIL, default=str).encode("utf-8")
            await store_and_catalog(
                db, storage, tid, wl, oid, sid, snap,
                item_id="shared-incr-2", item_type=ItemType.EMAIL,
                name=SHARED_EMAIL["subject"], path="Inbox", data=data,
                wrapped_dek=dek, mime_type="application/json",
                subject=SHARED_EMAIL["subject"],
            )
            count += 1
            size += len(data)
            return count, size

        job_incr2 = BackupJob(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            sla_policy_id=sla.id, status=JobStatus.COMPLETED,
            started_at=incr_start, completed_at=incr_start + timedelta(minutes=1),
            objects_total=1, objects_processed=1, objects_failed=0,
            created_at=incr_start,
        )
        db.add(job_incr2)
        await db.flush()

        wrapped_dek_incr2, _ = await storage.init_snapshot_storage(
            tenant.id, "exchange", mailboxes[1].ms_object_id, job_incr2.id
        )
        snap_incr2 = Snapshot(
            protected_object_id=mailboxes[1].id, snapshot_type=SnapshotType.INCREMENTAL,
            status=SnapshotStatus.COMPLETED, started_at=incr_start,
            completed_at=incr_start + timedelta(minutes=1),
        )
        db.add(snap_incr2)
        await db.flush()

        c2, s2 = await gen_incr_exchange_2(db, storage, tenant.id, "exchange",
                                            mailboxes[1].ms_object_id, snap_incr2.id,
                                            snap_incr2, wrapped_dek_incr2)
        snap_incr2.item_count = c2
        snap_incr2.size_bytes = s2
        mailboxes[1].last_backup_at = snap_incr2.completed_at
        print(f"  Incremental Exchange [{mailboxes[1].display_name}]: {c2} items")

        new_dedup = Stats.dedup_hits - pre_dedup
        print(f"  Dedup hits during incremental: {new_dedup}")

        # ── Step 4: Large Data (Use Case 3) ──────────────────────────
        print("\n── Step 4: Large file backup (CDC chunking) ──")
        pre_chunked = Stats.chunked_items

        large_job = BackupJob(
            tenant_id=tenant.id, workload_type=WorkloadType.ONEDRIVE,
            sla_policy_id=sla.id, status=JobStatus.COMPLETED,
            started_at=incr_start, completed_at=incr_start + timedelta(minutes=5),
            objects_total=1, objects_processed=1, objects_failed=0,
            created_at=incr_start,
        )
        db.add(large_job)
        await db.flush()

        wrapped_dek_large, _ = await storage.init_snapshot_storage(
            tenant.id, "onedrive", onedrives[0].ms_object_id, large_job.id
        )
        snap_large = Snapshot(
            protected_object_id=onedrives[0].id, snapshot_type=SnapshotType.INCREMENTAL,
            status=SnapshotStatus.COMPLETED, started_at=incr_start,
            completed_at=incr_start + timedelta(minutes=5),
        )
        db.add(snap_large)
        await db.flush()

        large_count = 0
        large_size = 0

        # 8MB random binary (won't compress, triggers CDC)
        print("  Storing raw-data.bin (8MB random binary)...")
        raw_data = make_binary_file(8 * 1024 * 1024)
        await store_and_catalog(
            db, storage, tenant.id, "onedrive", onedrives[0].ms_object_id,
            snap_large.id, snap_large,
            item_id="file-raw-data-bin", item_type=ItemType.FILE,
            name="raw-data.bin", path="/Reports", data=raw_data,
            wrapped_dek=wrapped_dek_large, filename="raw-data.bin",
            mime_type="application/octet-stream", file_name="raw-data.bin",
        )
        large_count += 1
        large_size += len(raw_data)

        # 5MB CSV (text, compresses but check if still triggers CDC)
        print("  Storing database-export.csv (5MB text)...")
        csv_lines = "id,name,email,department,salary,hire_date,performance_score\n"
        csv_line = "12345,John Smith,john@contoso.com,Engineering,125000,2022-03-15,4.5\n"
        csv_data = (csv_lines + csv_line * ((5 * 1024 * 1024) // len(csv_line))).encode("utf-8")
        await store_and_catalog(
            db, storage, tenant.id, "onedrive", onedrives[0].ms_object_id,
            snap_large.id, snap_large,
            item_id="file-database-export-csv", item_type=ItemType.FILE,
            name="database-export.csv", path="/Reports", data=csv_data,
            wrapped_dek=wrapped_dek_large, filename="database-export.csv",
            mime_type="text/csv", file_name="database-export.csv",
        )
        large_count += 1
        large_size += len(csv_data)

        snap_large.item_count = large_count
        snap_large.size_bytes = large_size

        new_chunked = Stats.chunked_items - pre_chunked
        print(f"  CDC chunked items: {new_chunked}")

        # ── Step 5: Activity History + Failed Jobs ────────────────────
        print("\n── Step 5: Activity history & failed items ──")

        # Historical backup jobs (spread across 7 days)
        for days_ago in range(1, 7):
            ts = datetime.utcnow() - timedelta(days=days_ago)
            status = JobStatus.COMPLETED if days_ago != 3 else JobStatus.FAILED
            hj = BackupJob(
                tenant_id=tenant.id,
                workload_type=random.choice([WorkloadType.EXCHANGE, WorkloadType.ONEDRIVE, WorkloadType.SHAREPOINT]),
                sla_policy_id=sla.id, status=status,
                started_at=ts, completed_at=ts + timedelta(minutes=random.randint(3, 15)),
                objects_total=random.randint(1, 3), objects_processed=random.randint(1, 3),
                objects_failed=1 if status == JobStatus.FAILED else 0,
                total_items=random.randint(10, 50), total_size_bytes=random.randint(50000, 500000),
                error_message="Graph API 429 — throttled after max retries" if status == JobStatus.FAILED else None,
                created_at=ts,
            )
            db.add(hj)

        # Partial job
        partial_ts = datetime.utcnow() - timedelta(days=2, hours=3)
        partial_job = BackupJob(
            tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
            sla_policy_id=sla.id, status=JobStatus.PARTIAL,
            started_at=partial_ts, completed_at=partial_ts + timedelta(minutes=8),
            objects_total=3, objects_processed=2, objects_failed=1,
            total_items=18, total_size_bytes=120000,
            error_message="1 of 3 mailboxes failed due to permission error",
            created_at=partial_ts,
        )
        db.add(partial_job)
        await db.flush()

        # Failed items
        failed_snap = Snapshot(
            protected_object_id=mailboxes[2].id, snapshot_type=SnapshotType.FULL,
            status=SnapshotStatus.COMPLETED, started_at=partial_ts,
            completed_at=partial_ts + timedelta(minutes=5),
            items_failed=3,
        )
        db.add(failed_snap)
        await db.flush()

        failed_items_data = [
            (ErrorCategory.PERMISSION_DENIED, "403 Forbidden: Insufficient privileges to access mailbox",
             "ErrorAccessDenied", 403),
            (ErrorCategory.THROTTLED, "429 Too Many Requests: Rate limit exceeded after 5 retries",
             "ErrorTooManyRequests", 429),
            (ErrorCategory.NOT_FOUND, "404 Not Found: Message was deleted between discovery and backup",
             "ErrorItemNotFound", 404),
        ]
        for cat, msg, code, http in failed_items_data:
            fi = FailedItem(
                snapshot_id=failed_snap.id,
                protected_object_id=mailboxes[2].id,
                ms_item_id=f"failed-item-{cat.value}",
                item_type=ItemType.EMAIL,
                item_name=f"Email that failed: {cat.value}",
                item_path="Inbox",
                error_category=cat,
                error_message=msg,
                error_code=code,
                http_status=http,
                retries_attempted=3,
                resolution_hint=ERROR_RESOLUTION_GUIDE.get(cat, ""),
                can_retry=cat != ErrorCategory.NOT_FOUND,
            )
            db.add(fi)
        print(f"  Created {len(failed_items_data)} failed items")

        # Restore job
        restore = RestoreJob(
            tenant_id=tenant.id, source_snapshot_id=snap1.id,
            source_object_id=mailboxes[0].id,
            restore_type=RestoreType.ITEM_LEVEL,
            status=RestoreStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(minutes=55),
            items_total=3, items_restored=3, items_failed=0,
            total_size_bytes=15000,
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(restore)

        # Audit logs
        audit_entries = [
            ("user.login", "user", admin.id, {"username": "admin"}, "info", datetime.utcnow() - timedelta(hours=7)),
            ("backup.start", "backup_job", None, {"workloads": ["exchange", "onedrive", "sharepoint"]}, "info", full_start),
            ("backup.complete", "backup_job", None, {"objects": 6, "items": Stats.total_items}, "info", full_start + timedelta(minutes=10)),
            ("backup.failed", "backup_job", None, {"error": "Graph API throttled"}, "warning", datetime.utcnow() - timedelta(days=3)),
            ("restore.complete", "restore_job", None, {"items_restored": 3}, "info", datetime.utcnow() - timedelta(minutes=55)),
        ]
        for action, rtype, rid, details, sev, ts in audit_entries:
            db.add(AuditLog(user_id=admin.id, action=action, resource_type=rtype,
                            resource_id=rid, details=json.dumps(details), severity=sev, timestamp=ts))

        print(f"  Created 6 historical backup jobs, 1 restore job, {len(audit_entries)} audit entries")

        # ── Commit everything ─────────────────────────────────────────
        await db.commit()

    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SIMULATION COMPLETE")
    print("=" * 70)
    print(f"""
  Tenant:       Contoso Corp
  Users:        1 admin
  Exchange:     3 mailboxes (protected)
  OneDrive:     2 accounts (protected)
  SharePoint:   1 site (protected)

  Snapshots:    Full + Incremental per workload
  Total items:  {Stats.total_items}

  Storage Pipeline:
    Original size:   {Stats.total_original:>12,} bytes ({Stats.total_original / 1024 / 1024:.2f} MB)
    Compressed size: {Stats.total_compressed:>12,} bytes ({Stats.total_compressed / 1024 / 1024:.2f} MB)
    Savings:         {(1 - Stats.total_compressed / max(Stats.total_original, 1)) * 100:.1f}%
    Dedup hits:      {Stats.dedup_hits}
    CDC chunked:     {Stats.chunked_items} items

  Login:  admin / admin123
  Start:  cd backend && python3 -m uvicorn app.main:app --port 8000
""")


if __name__ == "__main__":
    asyncio.run(main())
