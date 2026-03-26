# Shieldio — Onboarding Guide

This guide walks you through setting up Shieldio, connecting your first Microsoft 365 tenant, and running your first backup.

---

## Prerequisites

### Azure AD App Registration

Before connecting Shieldio to your tenant, create an App Registration in Azure AD:

1. Go to **Azure Portal > Azure Active Directory > App Registrations > New Registration**
2. Name: `Shieldio Backup` (or your preferred name)
3. Supported account types: **Single tenant**
4. Click **Register**

### Required API Permissions (Application type)

| Permission | Type | Purpose |
|-----------|------|---------|
| `Mail.Read` | Application | Read Exchange mailbox messages |
| `Calendars.Read` | Application | Read Exchange calendar events |
| `Contacts.Read` | Application | Read Exchange contacts |
| `Files.Read.All` | Application | Read OneDrive files |
| `Sites.Read.All` | Application | Read SharePoint sites and documents |
| `User.Read.All` | Application | Discover users for mailbox/OneDrive enumeration |

> **Important:** Click **Grant admin consent** after adding all permissions.

### Collect Credentials

From your App Registration, note these values:
- **Tenant ID** (Directory ID)
- **Client ID** (Application ID)
- **Client Secret** (create under Certificates & secrets)

---

## Step 1: System Setup

### Start the Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start the Frontend

```bash
cd frontend
npm run dev
```

### Create Admin Account

Register your first admin user:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@company.com",
    "password": "your-secure-password",
    "role": "admin"
  }'
```

Then log in at [http://localhost:5173](http://localhost:5173).

---

## Step 2: Register Your M365 Tenant

Navigate to **Settings** in the sidebar, or use the API:

```bash
curl -X POST http://localhost:8000/api/tenants/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Contoso Corp",
    "ms_tenant_id": "your-azure-tenant-id",
    "client_id": "your-app-client-id",
    "client_secret": "your-app-client-secret"
  }'
```

> The client secret is encrypted with AES-256-GCM before storage.

---

## Step 3: Test Connection

Verify that Shieldio can authenticate with your tenant:

```bash
curl -X POST http://localhost:8000/api/tenants/{tenant_id}/test \
  -H "Authorization: Bearer $TOKEN"
```

**Expected response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "user_count": 25
}
```

If the test fails, verify:
- Tenant ID, Client ID, and Client Secret are correct
- Admin consent has been granted for all permissions
- The App Registration is not expired

---

## Step 4: Discover M365 Objects

Run auto-discovery to find all mailboxes, OneDrive accounts, and SharePoint sites:

```bash
curl -X POST http://localhost:8000/api/tenants/{tenant_id}/discover \
  -H "Authorization: Bearer $TOKEN"
```

This populates the system with:
- **Exchange mailboxes** for each licensed user
- **OneDrive accounts** for each user with OneDrive provisioned
- **SharePoint sites** across the tenant

Check the discovered objects in the Dashboard, Exchange, OneDrive, and SharePoint pages.

---

## Step 5: Create SLA Policies

SLA policies define backup frequency and retention. Create policies via **SLA Policies** in the sidebar:

| Policy | Frequency | Retention | Use Case |
|--------|-----------|-----------|----------|
| Gold | Every 4 hours | 365 days | Executive mailboxes, critical sites |
| Silver | Every 12 hours | 90 days | Standard users |
| Bronze | Every 24 hours | 30 days | Shared mailboxes, archive sites |

```bash
curl -X POST http://localhost:8000/api/sla-policies/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gold",
    "backup_frequency_hours": 4,
    "retention_days": 365,
    "priority": 1,
    "is_locked": false
  }'
```

---

## Step 6: Assign SLA Policies

Assign policies to discovered objects to begin protection:

```bash
curl -X POST http://localhost:8000/api/sla-policies/assign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": 1,
    "object_ids": [1, 2, 3, 4, 5]
  }'
```

Or use the **SLA Policies** page to assign via the UI. Objects transition to **Protected** status once an SLA is assigned.

---

## Step 7: Verify First Backup

The scheduler automatically creates backup jobs based on SLA frequency. Monitor progress:

1. **Dashboard** — Check backup counts and SLA compliance
2. **Jobs** — View individual backup job status and progress
3. **Exchange / OneDrive / SharePoint** pages — Browse snapshots and backed-up items

To trigger an immediate backup:

```bash
# Backup a single mailbox
curl -X POST http://localhost:8000/api/exchange/mailboxes/{id}/backup \
  -H "Authorization: Bearer $TOKEN"

# Backup all Exchange mailboxes
curl -X POST http://localhost:8000/api/exchange/backup-all \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": 1}'
```

---

## Ongoing Operations

### SLA Compliance Monitoring

The Dashboard shows real-time SLA compliance. Objects are flagged as non-compliant when their last backup exceeds the SLA frequency window. Newly assigned objects get a grace period of one SLA cycle before being marked as violations.

### Unprotected Item Visibility

The Dashboard highlights objects without SLA policies or with failed backups. Expand the collapsible **Attention Required** card to see details grouped by workload.

### Failed Item Management

Navigate to **Failed Items** to view items that failed during backup. Each item shows:
- Error category (permission denied, throttled, timeout, etc.)
- Resolution guidance (e.g., "Grant Graph API permission in Azure AD")
- Retry or dismiss actions

### Restore Operations

Restore data from any snapshot via the workload pages:
- **Full in-place** — Restore all items back to the original location
- **Item-level** — Restore specific emails, files, or documents
- **Cross-user** — Restore to a different user's mailbox/OneDrive
- **Export** — Download backed-up data

### Audit Trail

All operations are logged in the **Audit Log** page with timestamps, user attribution, and severity levels.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection failed" on tenant test | Verify Azure AD credentials and admin consent |
| Discovery returns 0 objects | Ensure `User.Read.All` permission is granted |
| Backup fails with 403 | Check that specific workload permissions are granted |
| Backup fails with 429 | Normal throttling — the retry engine handles this automatically |
| SLA shows 100% but backups failing | Check if objects are within the grace period for first backup |
| Login returns 401 | Token may be expired — log in again (tokens expire after 24h in dev) |
