#!/usr/bin/env python3
"""
M365 Sample Data Population Script

Creates sample users, sends emails, uploads OneDrive files,
and creates SharePoint sites in your M365 tenant.

Usage:
    python scripts/populate_sample_data.py

Required: Set these environment variables (or use .env file):
    MS_TENANT_ID     - Your Azure AD Tenant ID
    MS_CLIENT_ID     - Your App Registration Client ID
    MS_CLIENT_SECRET - Your App Registration Client Secret

Required API Permissions (Application):
    User.ReadWrite.All, Mail.ReadWrite, Mail.Send,
    Files.ReadWrite.All, Sites.ReadWrite.All,
    Directory.ReadWrite.All
"""

import asyncio
import json
import os
import sys
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
import msal


# ─── Configuration ───────────────────────────────────────────────────────────

TENANT_ID = os.getenv("MS_TENANT_ID", "")
CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")

# Try loading from .env if not set
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

# ─── Sample Data Definitions ────────────────────────────────────────────────

SAMPLE_USERS = [
    {
        "displayName": "Alex Johnson",
        "mailNickname": "alexj",
        "userPrincipalName": None,  # Set dynamically with domain
        "department": "Engineering",
        "jobTitle": "Senior Developer",
    },
    {
        "displayName": "Sarah Chen",
        "mailNickname": "sarahc",
        "userPrincipalName": None,
        "department": "Marketing",
        "jobTitle": "Marketing Manager",
    },
    {
        "displayName": "Mike Williams",
        "mailNickname": "mikew",
        "userPrincipalName": None,
        "department": "Sales",
        "jobTitle": "Sales Representative",
    },
    {
        "displayName": "Emily Davis",
        "mailNickname": "emilyd",
        "userPrincipalName": None,
        "department": "HR",
        "jobTitle": "HR Specialist",
    },
    {
        "displayName": "James Wilson",
        "mailNickname": "jamesw",
        "userPrincipalName": None,
        "department": "Finance",
        "jobTitle": "Financial Analyst",
    },
]

SAMPLE_EMAILS = [
    {
        "subject": "Q1 2026 Project Roadmap Review",
        "body": """Hi Team,

Please review the Q1 roadmap attached. Key highlights:

1. Cloud migration Phase 2 - Target completion March 30
2. New customer portal - Beta launch Feb 15
3. Security audit - Scheduled for March 10-14

Let me know if you have any questions or concerns.

Best regards,
Alex""",
    },
    {
        "subject": "Weekly Status Update - Sprint 14",
        "body": """Team,

Sprint 14 summary:
- Completed: 23 story points
- In Progress: 8 story points
- Blocked: 2 items (dependency on API team)

Velocity is trending up. Great work everyone!

Regards,
Sarah""",
    },
    {
        "subject": "Important: Security Policy Update",
        "body": """All,

We're implementing new security policies effective immediately:

- Multi-factor authentication required for all accounts
- Password rotation every 90 days
- VPN required for remote access
- Quarterly security training mandatory

Please review the full policy document on SharePoint.

IT Security Team""",
    },
    {
        "subject": "Customer Feedback Report - February 2026",
        "body": """Hi Team,

Here's the monthly customer feedback summary:

- NPS Score: 72 (up from 68)
- Support tickets: 245 (down 12%)
- Feature requests: 34 new submissions
- Top request: Dark mode for dashboard

Full report available in the shared drive.

Best,
Mike""",
    },
    {
        "subject": "Team Building Event - March 20",
        "body": """Hey everyone!

We're organizing a team building event:

Date: March 20, 2026
Time: 2:00 PM - 5:00 PM
Location: Conference Room A + Outdoor area

Activities planned:
- Problem solving workshop
- Team trivia
- BBQ social

Please RSVP by March 15.

Cheers,
Emily""",
    },
    {
        "subject": "Budget Approval - Cloud Infrastructure",
        "body": """Hi Leadership,

Requesting approval for Q2 cloud infrastructure budget:

- Azure compute: $12,500/month
- Storage & backup: $3,200/month
- Monitoring & security: $2,100/month
- Total: $17,800/month ($213,600 annual)

This represents a 15% increase from Q1, driven by the new data
protection platform deployment.

Attached: Detailed cost breakdown and ROI analysis.

Best regards,
James""",
    },
    {
        "subject": "RE: API Integration Documentation",
        "body": """Thanks for the updated docs, Alex.

A few notes:
- The authentication section needs the new OAuth2 flow
- Rate limiting details are missing for the batch endpoints
- Can we add code samples in Python and JavaScript?

I'll update the SharePoint wiki once we finalize.

Sarah""",
    },
    {
        "subject": "Urgent: Production Incident - Database Latency",
        "body": """Team,

We're seeing elevated database latency in production:

- Started: 14:23 UTC
- Impact: API response times 3x normal
- Root cause: Under investigation
- Severity: P2

Current actions:
1. Scaled up read replicas
2. Enabled query caching
3. Monitoring dashboards shared in Teams

Will send updates every 30 minutes.

On-call team""",
    },
    {
        "subject": "New Hire Onboarding - March Cohort",
        "body": """Managers,

We have 3 new hires starting March 3rd:

1. Lisa Park - Engineering (reports to Alex)
2. Tom Baker - Sales (reports to Mike)
3. Anna Lee - Marketing (reports to Sarah)

Please ensure:
- Laptops are ready with required software
- M365 accounts provisioned
- Onboarding buddy assigned
- First week schedule shared

HR Team""",
    },
    {
        "subject": "Monthly All-Hands Meeting Recap",
        "body": """Hi All,

Key takeaways from today's all-hands:

- Revenue up 22% YoY
- 3 new enterprise clients signed
- Data protection product launch on track
- Hiring plan: 8 new positions in Q2
- Office renovation starting April 1

Recording available on SharePoint.

Thanks,
Leadership Team""",
    },
]

SAMPLE_FILES = [
    {"name": "Project_Roadmap_2026.docx", "content": "Project Roadmap 2026\n\nQ1 Goals:\n- Complete cloud migration\n- Launch customer portal\n- Implement data protection platform\n\nQ2 Goals:\n- Mobile app release\n- API v3 launch\n- International expansion prep"},
    {"name": "Budget_Analysis_Q1.xlsx", "content": "Department,Budget,Actual,Variance\nEngineering,150000,142000,-8000\nMarketing,80000,85000,5000\nSales,60000,58000,-2000\nHR,40000,39000,-1000\nFinance,35000,34000,-1000"},
    {"name": "Architecture_Design.md", "content": "# System Architecture\n\n## Overview\nMicroservices-based architecture with event-driven communication.\n\n## Components\n- API Gateway (nginx)\n- Auth Service (OAuth2/JWT)\n- Data Service (PostgreSQL)\n- Cache Layer (Redis)\n- Message Queue (RabbitMQ)\n\n## Deployment\nKubernetes on Azure AKS with Helm charts."},
    {"name": "Meeting_Notes_Feb28.txt", "content": "Meeting Notes - Feb 28, 2026\n\nAttendees: Alex, Sarah, Mike, Emily, James\n\nAgenda:\n1. Sprint review\n2. Q1 deliverables status\n3. New tool evaluation\n4. Team feedback\n\nAction Items:\n- Alex: Finalize API docs by March 5\n- Sarah: Schedule customer demos\n- Mike: Prepare sales forecast\n- Emily: Send onboarding schedule\n- James: Submit budget proposal"},
    {"name": "Security_Policy_v2.pdf", "content": "Security Policy v2.0\n\nEffective Date: March 1, 2026\n\n1. Access Control\n2. Data Classification\n3. Encryption Standards\n4. Incident Response\n5. Compliance Requirements"},
    {"name": "API_Documentation.md", "content": "# API Documentation v3.0\n\n## Authentication\nAll requests require Bearer token.\n\n## Endpoints\n\n### GET /api/users\nReturns list of users.\n\n### POST /api/backup\nInitiate a backup job.\n\n### GET /api/status/{jobId}\nCheck backup job status."},
    {"name": "reports/Sales_Report_Feb.csv", "content": "Date,Region,Product,Revenue,Units\n2026-02-01,North,Enterprise,45000,3\n2026-02-05,South,Standard,12000,8\n2026-02-10,East,Enterprise,67000,4\n2026-02-15,West,Premium,34000,5\n2026-02-20,North,Standard,8000,6"},
    {"name": "reports/Performance_Metrics.txt", "content": "Performance Metrics - February 2026\n\nUptime: 99.97%\nAvg Response Time: 145ms\nP99 Latency: 890ms\nError Rate: 0.03%\nDaily Active Users: 12,450\nAPI Calls/Day: 2.3M"},
]

SHAREPOINT_SITE_NAME = "DataProtectionProject"
SHAREPOINT_SITE_DESC = "KavachIQ Data Protection Project collaboration site"

SHAREPOINT_DOCS = [
    {"name": "Project_Charter.docx", "content": "Data Protection Project Charter\n\nObjective: Build enterprise-grade M365 backup and recovery solution.\n\nScope: Exchange, OneDrive, SharePoint workloads.\n\nTimeline: Q1-Q2 2026\n\nTeam: Engineering, Security, Operations"},
    {"name": "Technical_Spec.md", "content": "# Technical Specification\n\n## Backup Architecture\n- Forever incremental backups\n- Envelope encryption (AES-256-GCM)\n- Delta query-based change tracking\n\n## Recovery Options\n- Full restore\n- Item-level restore\n- Cross-user restore\n- Export to file"},
    {"name": "Compliance_Checklist.txt", "content": "Compliance Checklist\n\n[x] Data encryption at rest\n[x] Data encryption in transit\n[x] Role-based access control\n[x] Audit logging\n[ ] SOC 2 Type II certification\n[ ] GDPR data residency\n[ ] Retention lock compliance"},
]


# ─── Graph API Helper ────────────────────────────────────────────────────────

class GraphHelper:
    def __init__(self):
        self.app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET,
        )
        self._token = None

    def get_token(self) -> str:
        result = self.app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            print(f"❌ Failed to get token: {result.get('error_description', result)}")
            sys.exit(1)
        return result["access_token"]

    @property
    def headers(self):
        if not self._token:
            self._token = self.get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request_with_retry(self, method: str, client: httpx.AsyncClient, url: str, retries: int = 2, **kwargs) -> httpx.Response:
        for attempt in range(retries + 1):
            try:
                resp = await getattr(client, method)(url, **kwargs)
                return resp
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout) as e:
                if attempt < retries:
                    wait = 5 * (attempt + 1)
                    print(f"  ⏳ Timeout on {method.upper()} {url.split('/')[-1]}, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    print(f"  ❌ Timeout on {method.upper()} {url.split('/')[-1]} after {retries + 1} attempts")
                    raise

    async def get(self, client: httpx.AsyncClient, url: str) -> dict:
        try:
            resp = await self._request_with_retry("get", client, url, headers=self.headers)
            if resp.status_code >= 400:
                print(f"  ⚠️  GET {url} → {resp.status_code}: {resp.text[:200]}")
            return resp.json() if resp.status_code < 400 else {}
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            return {}

    async def post(self, client: httpx.AsyncClient, url: str, data: dict) -> dict:
        try:
            resp = await self._request_with_retry("post", client, url, headers=self.headers, json=data)
            if resp.status_code >= 400:
                print(f"  ⚠️  POST {url} → {resp.status_code}: {resp.text[:200]}")
                return {"error": resp.status_code}
            return resp.json() if resp.content else {}
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            return {"error": "timeout"}

    async def put(self, client: httpx.AsyncClient, url: str, content: bytes, content_type: str = "application/octet-stream") -> dict:
        try:
            headers = {**self.headers, "Content-Type": content_type}
            resp = await self._request_with_retry("put", client, url, headers=headers, content=content)
            if resp.status_code >= 400:
                print(f"  ⚠️  PUT {url} → {resp.status_code}: {resp.text[:200]}")
                return {"error": resp.status_code}
            return resp.json() if resp.content else {}
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            return {"error": "timeout"}


# ─── Main Population Functions ───────────────────────────────────────────────

async def get_domain(graph: GraphHelper, client: httpx.AsyncClient) -> str:
    """Get the tenant's default domain."""
    result = await graph.get(client, f"{GRAPH_URL}/organization")
    orgs = result.get("value", [])
    if orgs:
        domains = orgs[0].get("verifiedDomains", [])
        for d in domains:
            if d.get("isDefault"):
                return d["name"]
    print("❌ Could not determine tenant domain")
    sys.exit(1)


async def get_license_sku(graph: GraphHelper, client: httpx.AsyncClient) -> str:
    """Get available license SKU ID."""
    result = await graph.get(client, f"{GRAPH_URL}/subscribedSkus")
    skus = result.get("value", [])
    for sku in skus:
        available = sku.get("prepaidUnits", {}).get("enabled", 0) - sku.get("consumedUnits", 0)
        if available > 0:
            print(f"  Found license: {sku['skuPartNumber']} ({available} available)")
            return sku["skuId"]
    return None


async def create_users(graph: GraphHelper, client: httpx.AsyncClient, domain: str, license_sku: str) -> list:
    """Create sample users with licenses."""
    print("\n👥 Creating sample users...")
    created_users = []
    password = "M365Demo!" + "".join(random.choices(string.digits, k=4))

    for user_data in SAMPLE_USERS:
        upn = f"{user_data['mailNickname']}@{domain}"
        user_data["userPrincipalName"] = upn

        # Check if user already exists
        check = await graph.get(client, f"{GRAPH_URL}/users/{upn}")
        if check.get("id"):
            print(f"  ✅ User already exists: {upn}")
            created_users.append(check)
            continue

        payload = {
            "accountEnabled": True,
            "displayName": user_data["displayName"],
            "mailNickname": user_data["mailNickname"],
            "userPrincipalName": upn,
            "department": user_data["department"],
            "jobTitle": user_data["jobTitle"],
            "passwordProfile": {
                "forceChangePasswordNextSignIn": False,
                "password": password,
            },
            "usageLocation": "US",
        }

        result = await graph.post(client, f"{GRAPH_URL}/users", payload)
        if "error" not in result:
            print(f"  ✅ Created user: {upn}")
            created_users.append(result)

            # Assign license
            if license_sku:
                await asyncio.sleep(2)  # Wait for user provisioning
                license_payload = {
                    "addLicenses": [{"skuId": license_sku}],
                    "removeLicenses": [],
                }
                lic_result = await graph.post(
                    client,
                    f"{GRAPH_URL}/users/{result['id']}/assignLicense",
                    license_payload,
                )
                if "error" not in lic_result:
                    print(f"  📋 License assigned to {upn}")
                else:
                    print(f"  ⚠️  Could not assign license to {upn}")
        else:
            print(f"  ❌ Failed to create user: {upn}")

    print(f"\n  📝 User password for all new users: {password}")
    return created_users


async def send_emails(graph: GraphHelper, client: httpx.AsyncClient, users: list, domain: str):
    """Send sample emails between users."""
    print("\n📧 Sending sample emails...")

    # Get admin user
    admin_result = await graph.get(client, f"{GRAPH_URL}/me")
    if not admin_result.get("id"):
        # Use first user as sender fallback
        admin_result = await graph.get(client, f"{GRAPH_URL}/users?$top=1")
        admin_result = admin_result.get("value", [{}])[0]

    all_users = []
    users_result = await graph.get(client, f"{GRAPH_URL}/users?$select=id,displayName,mail,userPrincipalName")
    all_users = users_result.get("value", [])

    if len(all_users) < 1:
        print("  ⚠️  No users found to send emails to")
        return

    sent_count = 0
    for i, email_data in enumerate(SAMPLE_EMAILS):
        sender = all_users[i % len(all_users)]
        recipients = [u for u in all_users if u["id"] != sender["id"]]
        if not recipients:
            recipients = all_users[:1]

        # Pick 1-3 random recipients
        to_users = random.sample(recipients, min(random.randint(1, 3), len(recipients)))

        mail_payload = {
            "message": {
                "subject": email_data["subject"],
                "body": {
                    "contentType": "Text",
                    "content": email_data["body"],
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": u.get("mail") or u.get("userPrincipalName"),
                            "name": u["displayName"],
                        }
                    }
                    for u in to_users
                ],
            },
            "saveToSentItems": True,
        }

        result = await graph.post(
            client,
            f"{GRAPH_URL}/users/{sender['id']}/sendMail",
            mail_payload,
        )
        if "error" not in result:
            to_names = ", ".join(u["displayName"] for u in to_users)
            print(f"  ✅ Email sent: \"{email_data['subject'][:40]}...\" → {to_names}")
            sent_count += 1
        else:
            print(f"  ❌ Failed to send: \"{email_data['subject'][:40]}...\"")

        await asyncio.sleep(1)  # Rate limiting

    print(f"\n  📬 {sent_count}/{len(SAMPLE_EMAILS)} emails sent")


async def provision_onedrive(graph: GraphHelper, client: httpx.AsyncClient):
    """Force-provision OneDrive for all licensed users by accessing their drive."""
    print("\n🔧 Provisioning OneDrive for all users...")

    users_result = await graph.get(client, f"{GRAPH_URL}/users?$select=id,displayName,userPrincipalName")
    users = users_result.get("value", [])

    provisioned = []
    for user in users:
        user_id = user["id"]
        display = user["displayName"]

        # Trigger OneDrive provisioning by accessing the drive
        # This creates the personal site if it doesn't exist
        resp = await client.get(
            f"{GRAPH_URL}/users/{user_id}/drive",
            headers=graph.headers,
        )
        if resp.status_code == 200:
            print(f"  ✅ {display}: OneDrive already provisioned")
            provisioned.append(user_id)
        elif resp.status_code == 404:
            # Try to trigger provisioning via personal site request
            # Access the drive/root which can trigger auto-provisioning
            print(f"  ⏳ {display}: OneDrive not yet provisioned, triggering...")
        else:
            print(f"  ⚠️  {display}: unexpected status {resp.status_code}")

    if len(provisioned) < len(users):
        not_provisioned = len(users) - len(provisioned)
        print(f"\n  ⚠️  {not_provisioned} user(s) OneDrive not yet provisioned.")
        print("  💡 OneDrive provisioning can take up to 24 hours for new users.")
        print("  💡 To speed it up, have each user visit https://onedrive.com and sign in once.")
        print("  💡 Or run this from SharePoint Admin PowerShell:")
        print('     Request-SPOPersonalSite -UserEmails "user1@domain.com","user2@domain.com"')
        print(f"\n  ⏳ Waiting 90 seconds for provisioning to complete...")
        await asyncio.sleep(90)

        # Retry after waiting
        print("  🔄 Retrying OneDrive access...")
        for user in users:
            user_id = user["id"]
            if user_id in provisioned:
                continue
            display = user["displayName"]
            resp = await client.get(
                f"{GRAPH_URL}/users/{user_id}/drive",
                headers=graph.headers,
            )
            if resp.status_code == 200:
                print(f"  ✅ {display}: OneDrive now provisioned!")
                provisioned.append(user_id)
            else:
                print(f"  ⚠️  {display}: still not provisioned (status {resp.status_code})")

    return provisioned


async def upload_onedrive_files(graph: GraphHelper, client: httpx.AsyncClient):
    """Upload sample files to users' OneDrive."""
    print("\n📁 Uploading OneDrive files...")

    users_result = await graph.get(client, f"{GRAPH_URL}/users?$select=id,displayName,userPrincipalName")
    users = users_result.get("value", [])

    # First check which users have OneDrive provisioned
    available_users = []
    for user in users:
        user_id = user["id"]
        resp = await client.get(
            f"{GRAPH_URL}/users/{user_id}/drive",
            headers=graph.headers,
        )
        if resp.status_code == 200:
            available_users.append(user)

    if not available_users:
        print("  ⚠️  No users have OneDrive provisioned yet.")
        print("  💡 Quick fix: Have each user sign in at https://onedrive.com once.")
        print("  💡 Then re-run this script to upload files.")
        print(f"\n  📂 0 files uploaded to OneDrive")
        return

    print(f"  Found {len(available_users)}/{len(users)} users with OneDrive ready")

    uploaded = 0
    for user in available_users:
        user_id = user["id"]
        display = user["displayName"]

        # Upload 2-4 files per user
        files_for_user = random.sample(SAMPLE_FILES, min(random.randint(2, 4), len(SAMPLE_FILES)))

        for file_data in files_for_user:
            file_name = file_data["name"]
            content = file_data["content"].encode("utf-8")

            result = await graph.put(
                client,
                f"{GRAPH_URL}/users/{user_id}/drive/root:/{file_name}:/content",
                content,
                "text/plain",
            )
            if "error" not in result:
                print(f"  ✅ {display}: uploaded {file_name}")
                uploaded += 1
            else:
                print(f"  ⚠️  {display}: failed to upload {file_name}")

            await asyncio.sleep(0.5)

    print(f"\n  📂 {uploaded} files uploaded to OneDrive")


async def create_sharepoint_content(graph: GraphHelper, client: httpx.AsyncClient, domain: str):
    """Create SharePoint site and upload documents."""
    print("\n🌐 Creating SharePoint content...")

    # Create a new group (which auto-creates a SharePoint site)
    group_payload = {
        "displayName": "Data Protection Project",
        "description": SHAREPOINT_SITE_DESC,
        "groupTypes": ["Unified"],
        "mailEnabled": True,
        "mailNickname": SHAREPOINT_SITE_NAME.lower(),
        "securityEnabled": False,
        "visibility": "Private",
    }

    # Check if group already exists
    existing = await graph.get(
        client,
        f"{GRAPH_URL}/groups?$filter=mailNickname eq '{SHAREPOINT_SITE_NAME.lower()}'",
    )
    existing_groups = existing.get("value", [])

    if existing_groups:
        group = existing_groups[0]
        print(f"  ✅ Group already exists: {group['displayName']}")
    else:
        group = await graph.post(client, f"{GRAPH_URL}/groups", group_payload)
        if "error" in group:
            print("  ⚠️  Could not create SharePoint group/site. Skipping.")
            return
        print(f"  ✅ Created group: {group['displayName']}")
        # Wait for SharePoint site provisioning
        print("  ⏳ Waiting for SharePoint site provisioning (30s)...")
        await asyncio.sleep(30)

    group_id = group["id"]

    # Get the SharePoint site
    site = await graph.get(client, f"{GRAPH_URL}/groups/{group_id}/sites/root")
    if site.get("id"):
        print(f"  ✅ SharePoint site ready: {site.get('webUrl', 'N/A')}")
    else:
        print("  ⚠️  SharePoint site not ready yet. Try again in a few minutes.")
        return

    # Upload documents to the site's document library
    uploaded = 0
    for doc in SHAREPOINT_DOCS:
        content = doc["content"].encode("utf-8")
        result = await graph.put(
            client,
            f"{GRAPH_URL}/groups/{group_id}/drive/root:/{doc['name']}:/content",
            content,
            "text/plain",
        )
        if "error" not in result:
            print(f"  ✅ Uploaded to SharePoint: {doc['name']}")
            uploaded += 1
        else:
            print(f"  ⚠️  Failed to upload: {doc['name']}")

        await asyncio.sleep(0.5)

    # Create a SharePoint list
    list_payload = {
        "displayName": "Project Tasks",
        "columns": [
            {"name": "Task", "text": {}},
            {"name": "Assignee", "text": {}},
            {"name": "Status", "choice": {"choices": ["Not Started", "In Progress", "Completed"]}},
            {"name": "Priority", "choice": {"choices": ["High", "Medium", "Low"]}},
        ],
        "list": {"template": "genericList"},
    }

    list_result = await graph.post(client, f"{GRAPH_URL}/sites/{site['id']}/lists", list_payload)
    if "error" not in list_result:
        print(f"  ✅ Created SharePoint list: Project Tasks")

        # Add list items
        tasks = [
            {"Task": "Set up backup infrastructure", "Assignee": "Alex Johnson", "Status": "Completed", "Priority": "High"},
            {"Task": "Configure Exchange protection", "Assignee": "Sarah Chen", "Status": "In Progress", "Priority": "High"},
            {"Task": "Test OneDrive backup flow", "Assignee": "Mike Williams", "Status": "In Progress", "Priority": "Medium"},
            {"Task": "SharePoint site discovery", "Assignee": "Emily Davis", "Status": "Not Started", "Priority": "Medium"},
            {"Task": "Write compliance documentation", "Assignee": "James Wilson", "Status": "Not Started", "Priority": "Low"},
        ]

        list_id = list_result["id"]
        for task in tasks:
            item_payload = {"fields": task}
            await graph.post(client, f"{GRAPH_URL}/sites/{site['id']}/lists/{list_id}/items", item_payload)
            await asyncio.sleep(0.3)

        print(f"  ✅ Added {len(tasks)} tasks to Project Tasks list")

    print(f"\n  🌐 {uploaded} documents uploaded to SharePoint")


async def create_calendar_events(graph: GraphHelper, client: httpx.AsyncClient):
    """Create sample calendar events."""
    print("\n📅 Creating calendar events...")

    users_result = await graph.get(client, f"{GRAPH_URL}/users?$select=id,displayName")
    users = users_result.get("value", [])
    if not users:
        print("  ⚠️  No users found")
        return

    events = [
        {"subject": "Weekly Team Standup", "days_from_now": 1, "hour": 9, "duration": 0.5},
        {"subject": "Sprint Planning", "days_from_now": 2, "hour": 10, "duration": 2},
        {"subject": "Architecture Review", "days_from_now": 3, "hour": 14, "duration": 1},
        {"subject": "1:1 with Manager", "days_from_now": 4, "hour": 11, "duration": 0.5},
        {"subject": "All Hands Meeting", "days_from_now": 5, "hour": 15, "duration": 1},
    ]

    created = 0
    for user in users[:3]:  # Create events for first 3 users
        for event in events:
            start = datetime.now(tz=None) + timedelta(days=event["days_from_now"])
            start = start.replace(hour=event["hour"], minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=event["duration"])

            event_payload = {
                "subject": event["subject"],
                "body": {"contentType": "Text", "content": f"Recurring {event['subject']} meeting."},
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
                "isOnlineMeeting": True,
            }

            result = await graph.post(
                client,
                f"{GRAPH_URL}/users/{user['id']}/events",
                event_payload,
            )
            if "error" not in result:
                created += 1
            await asyncio.sleep(0.3)

    print(f"  ✅ Created {created} calendar events")


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("  M365 Sample Data Population Script")
    print("=" * 60)

    # Validate credentials
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("\n❌ Missing credentials! Set environment variables:")
        print("   export MS_TENANT_ID='your-tenant-id'")
        print("   export MS_CLIENT_ID='your-client-id'")
        print("   export MS_CLIENT_SECRET='your-client-secret'")
        print("\n   Or add them to backend/.env file")
        sys.exit(1)

    print(f"\n🔑 Tenant ID: {TENANT_ID[:8]}...{TENANT_ID[-4:]}")
    print(f"🔑 Client ID: {CLIENT_ID[:8]}...{CLIENT_ID[-4:]}")

    graph = GraphHelper()

    async with httpx.AsyncClient(timeout=120) as client:
        # 1. Get tenant domain
        print("\n🔍 Getting tenant info...")
        domain = await get_domain(graph, client)
        print(f"  ✅ Domain: {domain}")

        # 2. Get available licenses
        print("\n📋 Checking available licenses...")
        license_sku = await get_license_sku(graph, client)
        if not license_sku:
            print("  ⚠️  No available licenses — users will be created without licenses")

        # 3. Create users
        users = await create_users(graph, client, domain, license_sku)

        # 4. Wait for mailbox provisioning
        if users:
            print("\n⏳ Waiting for mailbox/OneDrive provisioning (60s)...")
            await asyncio.sleep(60)

        # 5. Provision OneDrive for all users
        await provision_onedrive(graph, client)

        # 6. Send emails
        await send_emails(graph, client, users, domain)

        # 7. Create calendar events
        await create_calendar_events(graph, client)

        # 8. Upload OneDrive files
        await upload_onedrive_files(graph, client)

        # 9. Create SharePoint content
        await create_sharepoint_content(graph, client, domain)

    print("\n" + "=" * 60)
    print("  ✅ Sample data population complete!")
    print("=" * 60)
    print(f"""
Next steps:
  1. Open the app at http://localhost:5173
  2. Go to Settings → + Add Tenant
  3. Enter your credentials:
     - Tenant ID: {TENANT_ID}
     - Client ID: {CLIENT_ID}
     - Client Secret: (your secret)
  4. Click 'Test Connection'
  5. Click 'Run Discovery'
  6. Go to Exchange/OneDrive/SharePoint to see your data!
""")


if __name__ == "__main__":
    asyncio.run(main())
