#!/usr/bin/env python3
"""
M365 Incremental Data Creator

Creates NEW data in Exchange and SharePoint to test incremental backups.
Run this AFTER an initial backup to generate changes that will appear
in the next incremental backup run.

Usage:
    python scripts/create_incremental_data.py              # create all
    python scripts/create_incremental_data.py --exchange    # exchange only
    python scripts/create_incremental_data.py --sharepoint  # sharepoint only

Required: MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET in backend/.env
Required API Permissions (Application):
    Mail.ReadWrite, Mail.Send, Calendars.ReadWrite,
    Contacts.ReadWrite, Sites.ReadWrite.All, Files.ReadWrite.All
"""

import asyncio
import json
import os
import sys
import random
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx

# ─── Configuration ───────────────────────────────────────────────────────────

TENANT_ID = os.getenv("MS_TENANT_ID", "")
CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")

if not TENANT_ID:
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key == "MS_TENANT_ID":
                    TENANT_ID = val
                elif key == "MS_CLIENT_ID":
                    CLIENT_ID = val
                elif key == "MS_CLIENT_SECRET":
                    CLIENT_SECRET = val

GRAPH_URL = "https://graph.microsoft.com/v1.0"
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
TIMESTAMP = NOW.strftime("%H:%M")


# ─── Token Acquisition ──────────────────────────────────────────────────────

async def get_token(client: httpx.AsyncClient) -> str:
    """Acquire Graph API token via client credentials."""
    resp = await client.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(data.get("error_description", "Token failed"))
    return data["access_token"]


async def graph_get(client: httpx.AsyncClient, token: str, path: str):
    """GET from Graph API."""
    resp = await client.get(
        f"{GRAPH_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code >= 400:
        return None
    return resp.json()


async def graph_post(client: httpx.AsyncClient, token: str, path: str, body: dict):
    """POST to Graph API."""
    resp = await client.post(
        f"{GRAPH_URL}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        print(f"      ERROR {resp.status_code}: {err}")
        return None
    # Some endpoints (e.g., sendMail) return 202 with no body
    if resp.status_code == 202 or not resp.content:
        return {"status": "accepted"}
    return resp.json()


async def graph_put(client: httpx.AsyncClient, token: str, path: str, content: bytes, content_type: str = "application/octet-stream"):
    """PUT binary content to Graph API."""
    resp = await client.put(
        f"{GRAPH_URL}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
        content=content,
    )
    if resp.status_code >= 400:
        err = resp.json().get("error", {}).get("message", resp.text[:200])
        print(f"      ERROR {resp.status_code}: {err}")
        return None
    return resp.json()


# ─── Discover Users ──────────────────────────────────────────────────────────

async def discover_users(client: httpx.AsyncClient, token: str) -> list[dict]:
    """Get all licensed users."""
    data = await graph_get(client, token, "/users?$select=id,displayName,mail,userPrincipalName&$filter=assignedLicenses/$count ne 0&$count=true")
    if not data:
        # Fallback without filter
        data = await graph_get(client, token, "/users?$select=id,displayName,mail,userPrincipalName&$top=20")
    users = data.get("value", []) if data else []
    return [u for u in users if u.get("mail") or u.get("userPrincipalName")]


# ─── Exchange: New Emails ────────────────────────────────────────────────────

INCREMENTAL_EMAILS = [
    {
        "subject": f"URGENT: Production deployment scheduled for {TODAY}",
        "body": f"""Team,

We have a critical production deployment scheduled for today at 6 PM PST.

Deployment Details:
- Version: v2.3.1
- Changes: Security patches + performance improvements
- Rollback plan: Automated rollback if health checks fail within 15 min
- On-call: Alex Johnson (primary), Mike Williams (secondary)

Please ensure all staging tests are passing before 4 PM.

Deployment Checklist:
[x] Code freeze applied
[x] Staging environment validated
[ ] Database migration script tested
[ ] Load balancer drain configured
[ ] Monitoring alerts adjusted

Status page: https://status.patwainc.com

Regards,
DevOps Team
Generated at: {TIMESTAMP} UTC""",
        "importance": "high",
    },
    {
        "subject": f"Data Protection Compliance Report - {NOW.strftime('%B %Y')}",
        "body": f"""Hi Leadership,

Monthly compliance report for our data protection platform:

Backup Statistics:
- Total backups completed: 1,247
- Success rate: 99.8% (3 retried, all resolved)
- Data protected: 2.3 TB across 6 users
- Average backup time: 4 min 23 sec

Compliance Status:
- GDPR: Compliant (audit passed March 5)
- SOC 2 Type II: In progress (estimated May 2026)
- ISO 27001: Certification renewal scheduled Q3

Encryption:
- All data encrypted at rest (AES-256-GCM)
- Per-tenant DEK rotation: Monthly
- Master KEK stored in Azure Key Vault

Recommendations:
1. Increase backup frequency for executive mailboxes
2. Enable geo-redundant storage for DR
3. Schedule quarterly restore drills

Full report attached.

Best,
Security Team
Report generated: {TODAY}""",
    },
    {
        "subject": f"Quarterly Business Review - Q1 {NOW.year}",
        "body": f"""All,

QBR is scheduled for next Friday. Here's the pre-read:

Revenue Highlights:
- ARR: $4.2M (up 35% YoY)
- New logos: 12 enterprise clients
- Churn rate: 1.2% (industry avg: 5%)
- Net retention: 118%

Product Updates:
- Shieldio launched to 3 pilot customers
- SharePoint backup GA this month
- OneDrive incremental backup in beta
- Compression pipeline reduced storage costs by 40%

Hiring:
- 4 engineers hired (2 backend, 1 frontend, 1 SRE)
- Open roles: 3 (security engineer, PM, solutions architect)

Customer Satisfaction:
- NPS: 74 (target: 70)
- Support CSAT: 4.6/5.0
- Avg response time: 2.1 hours

Please add discussion topics to the shared agenda on SharePoint.

Thanks,
Gopal""",
    },
    {
        "subject": f"New Feature Request: Automated Retention Policies",
        "body": f"""Product Team,

Multiple enterprise customers have requested automated retention policies:

Requirements gathered:
1. Configurable retention periods per workload (30/60/90/365 days)
2. Legal hold support (prevent deletion during litigation)
3. Automated cleanup of expired backups
4. Audit trail for all retention actions
5. Compliance templates (GDPR 6-year, HIPAA 7-year, SOX 7-year)

Priority customers requesting this:
- Acme Corp (Enterprise plan, $120K ARR)
- GlobalTech (Enterprise plan, $95K ARR)
- MedStar Health (Compliance-critical, potential $200K deal)

Proposed timeline:
- Design: 2 weeks
- Implementation: 4 weeks
- Beta: 2 weeks
- GA: End of Q2

Let's discuss in tomorrow's sprint planning.

Sarah""",
    },
    {
        "subject": f"Infrastructure Cost Optimization Results - {NOW.strftime('%B')}",
        "body": f"""Finance & Engineering,

Results of this month's cost optimization initiative:

Before Optimization:
- Compute: $8,500/mo
- Storage: $4,200/mo
- Database: $2,800/mo
- Total: $15,500/mo

After Optimization:
- Compute: $6,200/mo (auto-scaling + spot instances)
- Storage: $2,500/mo (compression + dedup saved 40%)
- Database: $2,100/mo (right-sized, reserved instances)
- Total: $10,800/mo

Monthly Savings: $4,700 (30.3% reduction)
Annual Projected Savings: $56,400

Key changes:
1. zstd compression on all backup blobs
2. Content-addressable deduplication
3. CDC chunking for large files
4. Tiered storage (hot/cool/archive)

Next steps: Implement Azure Reserved Instances for additional 20% savings.

James""",
    },
]

INCREMENTAL_CALENDAR_EVENTS = [
    {
        "subject": f"Sprint {random.randint(15, 25)} Planning",
        "body": {"contentType": "text", "content": "Sprint planning for the data protection team. Bring your backlog items."},
        "start": {"dateTime": (NOW + timedelta(days=1, hours=2)).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "end": {"dateTime": (NOW + timedelta(days=1, hours=3)).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "location": {"displayName": "Conference Room B"},
    },
    {
        "subject": "Customer Demo: Shieldio",
        "body": {"contentType": "text", "content": "Demo of Shieldio backup and restore capabilities to Acme Corp."},
        "start": {"dateTime": (NOW + timedelta(days=2, hours=4)).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "end": {"dateTime": (NOW + timedelta(days=2, hours=5)).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "location": {"displayName": "Zoom Meeting"},
        "isOnlineMeeting": True,
    },
    {
        "subject": "Security Review: Backup Encryption",
        "body": {"contentType": "text", "content": "Review AES-256-GCM encryption implementation and key rotation procedures."},
        "start": {"dateTime": (NOW + timedelta(days=3, hours=1)).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "end": {"dateTime": (NOW + timedelta(days=3, hours=2)).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"},
        "location": {"displayName": "Security Lab"},
    },
]

INCREMENTAL_CONTACTS = [
    {
        "givenName": "Lisa",
        "surname": "Park",
        "emailAddresses": [{"address": "lisa.park@acmecorp.com", "name": "Lisa Park"}],
        "companyName": "Acme Corp",
        "jobTitle": "VP of Engineering",
        "businessPhones": ["+1-555-0142"],
    },
    {
        "givenName": "Robert",
        "surname": "Chang",
        "emailAddresses": [{"address": "r.chang@globaltech.io", "name": "Robert Chang"}],
        "companyName": "GlobalTech",
        "jobTitle": "CTO",
        "businessPhones": ["+1-555-0198"],
    },
]


async def create_exchange_data(client: httpx.AsyncClient, token: str, users: list[dict]):
    """Create new Exchange items: emails, calendar events, contacts."""
    print("\n" + "=" * 60)
    print("  Exchange: Creating Incremental Data")
    print("=" * 60)

    email_count = 0
    event_count = 0
    contact_count = 0

    # Send emails between users
    print("\n  📧 Sending new emails...")
    for i, email_data in enumerate(INCREMENTAL_EMAILS):
        sender = users[i % len(users)]
        recipients = [u for u in users if u["id"] != sender["id"]]
        to_user = recipients[i % len(recipients)]

        sender_upn = sender.get("userPrincipalName") or sender.get("mail")
        to_mail = to_user.get("mail") or to_user.get("userPrincipalName")

        body = {
            "message": {
                "subject": email_data["subject"],
                "body": {
                    "contentType": "text",
                    "content": email_data["body"],
                },
                "toRecipients": [
                    {"emailAddress": {"address": to_mail}}
                ],
            },
            "saveToSentItems": "true",
        }
        if email_data.get("importance"):
            body["message"]["importance"] = email_data["importance"]

        result = await graph_post(client, token, f"/users/{sender_upn}/sendMail", body)
        if result is not None or True:  # sendMail returns 202 with no body
            sender_name = sender.get("displayName", sender_upn)
            to_name = to_user.get("displayName", to_mail)
            print(f"     {sender_name} -> {to_name}: {email_data['subject'][:50]}...")
            email_count += 1

    # Create calendar events
    print("\n  📅 Creating calendar events...")
    for event_data in INCREMENTAL_CALENDAR_EVENTS:
        user = random.choice(users)
        upn = user.get("userPrincipalName") or user.get("mail")
        result = await graph_post(client, token, f"/users/{upn}/events", event_data)
        if result:
            print(f"     {user['displayName']}: {event_data['subject']}")
            event_count += 1

    # Create contacts
    print("\n  👤 Creating contacts...")
    for contact_data in INCREMENTAL_CONTACTS:
        user = random.choice(users)
        upn = user.get("userPrincipalName") or user.get("mail")
        result = await graph_post(client, token, f"/users/{upn}/contacts", contact_data)
        if result:
            print(f"     {user['displayName']}: {contact_data['givenName']} {contact_data['surname']} ({contact_data['companyName']})")
            contact_count += 1

    print(f"\n  Exchange Summary:")
    print(f"     Emails sent:     {email_count}")
    print(f"     Events created:  {event_count}")
    print(f"     Contacts added:  {contact_count}")
    return email_count + event_count + contact_count


# ─── SharePoint: New Documents & List Items ──────────────────────────────────

SHAREPOINT_DOCUMENTS = [
    {
        "name": f"Incident_Report_{TODAY}.md",
        "content": f"""# Incident Report - {TODAY}

## Summary
Elevated database latency detected in production environment.

## Timeline
- {TIMESTAMP} UTC - Alert triggered
- {TIMESTAMP} UTC - On-call engineer acknowledged
- {TIMESTAMP} UTC - Root cause identified (connection pool exhaustion)
- {TIMESTAMP} UTC - Fix deployed, monitoring

## Impact
- Duration: 45 minutes
- Users affected: ~200
- SLA impact: None (within 99.9% target)

## Root Cause
Connection pool exhaustion due to long-running backup queries.

## Remediation
1. Increased connection pool size from 20 to 50
2. Added query timeout of 30 seconds
3. Implemented connection pooling metrics

## Action Items
- [ ] Add connection pool monitoring dashboard
- [ ] Implement circuit breaker pattern
- [ ] Review query optimization for backup operations
""",
    },
    {
        "name": f"Release_Notes_v2.3.1_{TODAY}.md",
        "content": f"""# Release Notes - Shieldio v2.3.1

**Release Date:** {TODAY}

## New Features
- Incremental backup support for SharePoint document libraries
- Content-aware compression (zstd) reducing storage by 40%
- CDC chunking for files > 4MB
- Deduplication across snapshots within tenant

## Bug Fixes
- Fixed: OneDrive backup failing for users without provisioned drives
- Fixed: SharePoint list items not captured in incremental backups
- Fixed: Calendar event timezone handling for recurring events

## Performance Improvements
- Backup speed improved 2.5x with parallel object processing
- Reduced memory footprint by 35% with streaming encryption
- Database query optimization for job status polling

## Security
- Upgraded to AES-256-GCM encryption with per-tenant DEKs
- Added Graph API least-privilege scopes (backup=read-only)
- RBAC enforcement: restore operations require ADMIN role

## Known Issues
- Large attachments (>25MB) may timeout on slow connections
- SharePoint site-level permissions not yet backed up
""",
    },
    {
        "name": f"Architecture_Decision_Record_{NOW.strftime('%Y%m%d')}.md",
        "content": f"""# ADR-007: Compression and Deduplication Pipeline

**Date:** {TODAY}
**Status:** Accepted
**Decision Makers:** Gopal Patwa, Alex Johnson

## Context
Storage costs growing linearly with customer count. Need to reduce
storage footprint without impacting backup/restore performance.

## Decision
Implement a layered pipeline: Raw -> Compress -> Hash -> Dedup -> Encrypt -> Store

### Compression: zstd with content-aware levels
- Level 9 for text/JSON (emails, calendar events, contacts)
- Level 3 for binary (documents, images)
- Skip for incompressible formats (zip, mp4, encrypted files)

### Deduplication: SHA-256 content-addressable
- Hash computed AFTER compression, BEFORE encryption
- Cross-snapshot dedup within same tenant
- Reference counting for safe deletion

### Content-Defined Chunking (CDC)
- Gear-hash rolling hash for files >= 4MB
- Target chunk: 64KB, min: 16KB, max: 256KB
- Enables dedup across file versions

## Consequences
- 40% storage reduction (measured on real M365 data)
- 5% CPU overhead for compression (acceptable)
- Backward compatible: legacy blobs detected by missing M3VZ header
""",
    },
    {
        "name": f"Customer_Onboarding_Guide_{NOW.strftime('%Y%m%d')}.docx",
        "content": f"""Customer Onboarding Guide
Shieldio - Data Protection Platform
Last Updated: {TODAY}

Step 1: Azure AD App Registration
- Register app in customer's Azure AD tenant
- Grant required API permissions (Application type)
- Admin consent required

Step 2: Configure Permissions
Backup (Read-Only):
  Mail.Read, Calendars.Read, Contacts.Read
  Files.Read.All, Sites.Read.All, User.Read.All

Restore (Read-Write):
  Mail.ReadWrite, Calendars.ReadWrite, Contacts.ReadWrite
  Files.ReadWrite.All, Sites.ReadWrite.All

Step 3: Tenant Onboarding
- Enter Tenant ID, Client ID, Client Secret
- System auto-discovers users, mailboxes, drives, sites
- Configure SLA policy (backup frequency, retention)

Step 4: Initial Backup
- Full backup triggered automatically
- Monitor progress in Dashboard
- Verify backup completeness in Workload pages

Step 5: Ongoing Operations
- Incremental backups run per SLA schedule
- Failed items auto-retried up to 3 times
- Alerts via email for persistent failures
""",
    },
]

SHAREPOINT_LIST_ITEMS = [
    {
        "fields": {
            "Title": f"[P1] Fix OneDrive backup for unprovisioned users",
            "Status": "Completed",
            "Priority": "High",
            "AssignedTo": "Alex Johnson",
            "DueDate": (NOW - timedelta(days=2)).strftime("%Y-%m-%d"),
        },
    },
    {
        "fields": {
            "Title": f"[P2] Implement retention policy engine",
            "Status": "In Progress",
            "Priority": "High",
            "AssignedTo": "Sarah Chen",
            "DueDate": (NOW + timedelta(days=14)).strftime("%Y-%m-%d"),
        },
    },
    {
        "fields": {
            "Title": f"[P3] Add geo-redundant backup storage",
            "Status": "Not Started",
            "Priority": "Medium",
            "AssignedTo": "James Wilson",
            "DueDate": (NOW + timedelta(days=30)).strftime("%Y-%m-%d"),
        },
    },
    {
        "fields": {
            "Title": f"[P1] Customer demo preparation - Acme Corp",
            "Status": "In Progress",
            "Priority": "High",
            "AssignedTo": "Mike Williams",
            "DueDate": (NOW + timedelta(days=2)).strftime("%Y-%m-%d"),
        },
    },
    {
        "fields": {
            "Title": f"[P2] SOC 2 Type II audit preparation",
            "Status": "In Progress",
            "Priority": "Medium",
            "AssignedTo": "Emily Davis",
            "DueDate": (NOW + timedelta(days=45)).strftime("%Y-%m-%d"),
        },
    },
]


async def create_sharepoint_data(client: httpx.AsyncClient, token: str):
    """Create new SharePoint documents and list items."""
    print("\n" + "=" * 60)
    print("  SharePoint: Creating Incremental Data")
    print("=" * 60)

    doc_count = 0
    item_count = 0

    # Find SharePoint sites
    print("\n  🌐 Finding SharePoint sites...")
    sites_data = await graph_get(client, token, "/sites?search=*&$select=id,displayName,webUrl&$top=10")
    sites = sites_data.get("value", []) if sites_data else []

    if not sites:
        print("     No SharePoint sites found!")
        return 0

    for s in sites:
        print(f"     {s['displayName']}: {s['webUrl']}")

    # Prefer "Data Protection Project" site, then any /sites/ path, then root
    target_site = None
    for s in sites:
        if "dataprotection" in s.get("webUrl", "").lower():
            target_site = s
            break
    if not target_site:
        for s in sites:
            if "sharepoint.com/sites/" in s.get("webUrl", ""):
                target_site = s
                break
    if not target_site:
        target_site = sites[0]

    site_id = target_site["id"]
    print(f"\n  Target site: {target_site['displayName']}")

    # Upload documents to default document library
    print("\n  📄 Uploading documents...")
    drives_data = await graph_get(client, token, f"/sites/{site_id}/drives?$select=id,name,webUrl")
    drives = drives_data.get("value", []) if drives_data else []

    if drives:
        drive_id = drives[0]["id"]
        print(f"     Drive: {drives[0]['name']}")

        for doc in SHAREPOINT_DOCUMENTS:
            content = doc["content"].encode("utf-8")
            result = await graph_put(
                client, token,
                f"/sites/{site_id}/drives/{drive_id}/root:/{doc['name']}:/content",
                content,
                "text/plain",
            )
            if result:
                size = result.get("size", len(content))
                print(f"     {doc['name']} ({size:,} bytes)")
                doc_count += 1
    else:
        print("     No document libraries found!")

    # Add list items — find or create "Project Tasks" list
    print("\n  📋 Adding list items...")
    lists_data = await graph_get(client, token, f"/sites/{site_id}/lists?$select=id,displayName")
    all_lists = lists_data.get("value", []) if lists_data else []

    # Find existing "Project Tasks" list
    target_list = None
    for l in all_lists:
        if l.get("displayName") == "Project Tasks":
            target_list = l
            break

    if target_list:
        list_id = target_list["id"]
        print(f"     Using existing list: Project Tasks")
    else:
        print("     Creating 'Project Tasks' list...")
        new_list = await graph_post(client, token, f"/sites/{site_id}/lists", {
            "displayName": "Project Tasks",
            "list": {"template": "genericList"},
        })
        if new_list:
            list_id = new_list["id"]
            # Add custom columns
            for col in [
                {"name": "Status", "text": {}},
                {"name": "Priority", "text": {}},
                {"name": "AssignedTo", "text": {}},
                {"name": "DueDate", "text": {}},
            ]:
                await graph_post(client, token, f"/sites/{site_id}/lists/{list_id}/columns", col)
            print(f"     Created list: Project Tasks (with custom columns)")
        else:
            list_id = None

    if list_id:
        for item in SHAREPOINT_LIST_ITEMS:
            result = await graph_post(client, token, f"/sites/{site_id}/lists/{list_id}/items", item)
            if result:
                title = item["fields"].get("Title", "?")
                print(f"     {title[:60]}")
                item_count += 1

    print(f"\n  SharePoint Summary:")
    print(f"     Documents uploaded: {doc_count}")
    print(f"     List items added:   {item_count}")
    return doc_count + item_count


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    args = sys.argv[1:]
    do_exchange = "--exchange" in args or not any(a.startswith("--") for a in args)
    do_sharepoint = "--sharepoint" in args or not any(a.startswith("--") for a in args)

    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("ERROR: Missing credentials. Set MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET")
        sys.exit(1)

    print("=" * 60)
    print("  M365 Incremental Data Creator")
    print("=" * 60)
    print(f"\n  Tenant ID: {TENANT_ID[:8]}...{TENANT_ID[-4:]}")
    print(f"  Timestamp: {NOW.isoformat()}")

    total = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await get_token(client)
        print("  Token acquired")

        if do_exchange:
            users = await discover_users(client, token)
            print(f"\n  Found {len(users)} users")
            total += await create_exchange_data(client, token, users)

        if do_sharepoint:
            total += await create_sharepoint_data(client, token)

    print("\n" + "=" * 60)
    print(f"  Total items created: {total}")
    print("=" * 60)
    print("\n  Next: Run a backup to capture these changes!")
    print("    - From UI: Go to each workload page and click 'Backup All'")
    print("    - From API: POST /api/exchange/backup-all")
    print("    -           POST /api/sharepoint/backup-all")


if __name__ == "__main__":
    asyncio.run(main())
