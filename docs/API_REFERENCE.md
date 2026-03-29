# Shieldio — API Reference

Base URL: `/api`

---

## Common Patterns

### Authentication

All endpoints (except `/api/auth/register` and `/api/auth/login`) require a JWT Bearer token.

```
Authorization: Bearer <access_token>
```

Obtain a token via `POST /api/auth/login`. Tokens expire after the configured `ACCESS_TOKEN_EXPIRE_MINUTES`.

### Role-Based Access (v1.1.0 — Least Privilege)

| Role | Description |
|------|-------------|
| `admin` | Full access: tenant/SLA management, backup triggers, **restore/recovery** (write access) |
| `operator` | Backup triggers, retry failed jobs, discovery, SLA assignment. **Cannot restore** |
| `viewer` | Read-only: browse snapshots, search items, view job status. **Cannot trigger backup or restore** |

**Endpoint permission matrix:**

| Operation | Required Role | Auth Dependency |
|-----------|---------------|-----------------|
| GET (browse/search/list) | Any authenticated | `get_current_user` |
| POST backup / backup-all | Admin, Operator | `require_backup_permission` |
| POST restore / mass-recovery | **Admin only** | `require_restore_permission` |
| POST retry / retry-all-failed | Admin, Operator | `require_backup_permission` |

### Pagination

Paginated endpoints accept:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number (1-based) |
| `page_size` | int | `20` | Items per page (max varies: 100 or 200) |

Response shape:

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "items": [...]
}
```

### Error Responses

| Status | Meaning |
|--------|---------|
| `400` | Bad request / duplicate resource / validation error |
| `401` | Missing or invalid token |
| `403` | Insufficient role / retention-locked resource |
| `404` | Resource not found |
| `422` | Request body validation failure (FastAPI) |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Service unavailable (circuit breaker open, dependency down) |

Error body (structured format):

```json
{
  "error": {
    "code": "E2001",
    "message": "Invalid username or password",
    "detail": "Credentials did not match any active account",
    "fix": "Check your credentials and try again",
    "correlation_id": "a1b2c3d4"
  }
}
```

Error code ranges: `E1xxx` (Connector), `E2xxx` (Auth), `E3xxx` (Backup), `E4xxx` (Recovery), `E5xxx` (Infrastructure), `E6xxx` (Validation), `E7xxx` (Rate Limiting).

### Request Headers

| Header | Direction | Description |
|--------|-----------|-------------|
| `Authorization: Bearer <token>` | Request | JWT authentication |
| `X-Correlation-ID` | Both | Request tracing ID (auto-generated if not sent) |
| `X-Idempotency-Key` | Request | Safe retry for mutations (backup-all endpoints) |
| `X-Response-Time` | Response | Request duration |
| `X-RateLimit-Limit` | Response | Rate limit for current tier |
| `X-RateLimit-Remaining` | Response | Remaining requests in window |
| `Retry-After` | Response | Seconds to wait on 429 |

---

## Authentication

Prefix: `/api/auth`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | None | Register a new user |
| POST | `/api/auth/login` | None | Login, returns JWT token |
| GET | `/api/auth/me` | Bearer | Get current user info |

### POST `/api/auth/register`

**Request:**

```json
{
  "username": "admin1",
  "email": "admin@example.com",
  "password": "s3cret",
  "full_name": "Admin User",
  "role": "admin"
}
```

**Response** `200`:

```json
{
  "id": 1,
  "username": "admin1",
  "email": "admin@example.com",
  "full_name": "Admin User",
  "role": "admin",
  "is_active": 1
}
```

### POST `/api/auth/login`

Form-encoded (`application/x-www-form-urlencoded`):

| Field | Type | Required |
|-------|------|----------|
| `username` | string | Yes |
| `password` | string | Yes |

**Response** `200`:

```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "admin1", "email": "...", "full_name": "...", "role": "admin", "is_active": 1 }
}
```

---

## Tenants

Prefix: `/api/tenants`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/tenants/` | Bearer | List all tenants |
| POST | `/api/tenants/` | Admin | Onboard a new M365 tenant |
| POST | `/api/tenants/{tenant_id}/test` | Admin, Operator | Test Graph API connectivity |
| POST | `/api/tenants/{tenant_id}/discover` | Admin, Operator | Run object discovery (mailboxes, drives, sites) |
| DELETE | `/api/tenants/{tenant_id}` | Admin | Remove a tenant |

### POST `/api/tenants/`

**Request:**

```json
{
  "name": "Contoso",
  "ms_tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_id": "app-client-id",
  "client_secret": "app-client-secret"
}
```

**Response** `200` (`TenantResponse`):

```json
{
  "id": 1,
  "name": "Contoso",
  "ms_tenant_id": "xxxxxxxx-...",
  "client_id": "app-client-id",
  "status": "onboarding",
  "total_mailboxes": 0,
  "total_onedrives": 0,
  "total_sites": 0,
  "last_discovery_at": null,
  "created_at": "2025-01-15T10:30:00"
}
```

### POST `/api/tenants/{tenant_id}/test`

**Response** `200`:

```json
{ "success": true, "message": "Connection successful", "user_count": 1 }
```

### POST `/api/tenants/{tenant_id}/discover`

**Response** `200`:

```json
{ "status": "completed", "results": { ... } }
```

---

## SLA Policies

Prefix: `/api/sla-policies`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sla-policies/` | Bearer | List all SLA policies |
| POST | `/api/sla-policies/` | Admin | Create a new SLA policy |
| PUT | `/api/sla-policies/{policy_id}` | Admin | Update an SLA policy (blocked if locked) |
| DELETE | `/api/sla-policies/{policy_id}` | Admin | Delete an SLA policy (blocked if locked) |
| POST | `/api/sla-policies/assign` | Admin, Operator | Assign SLA to objects |
| POST | `/api/sla-policies/unassign` | Admin, Operator | Remove SLA from objects |

### POST `/api/sla-policies/`

**Request** (`SLAPolicyCreate`):

```json
{
  "name": "Gold - 4h RPO",
  "description": "Mission-critical mailboxes",
  "backup_frequency_hours": 4,
  "retention_days": 365,
  "priority": 1,
  "is_locked": true
}
```

### POST `/api/sla-policies/assign`

**Request** (`SLAAssignRequest`):

```json
{
  "sla_policy_id": 1,
  "object_ids": [10, 11, 12],
  "assignment_type": "individual"
}
```

Application-level (all objects of a workload in a tenant):

```json
{
  "sla_policy_id": 2,
  "workload_type": "exchange",
  "tenant_id": 1,
  "assignment_type": "application"
}
```

**Response** `200`:

```json
{ "status": "assigned", "objects_updated": 3 }
```

### POST `/api/sla-policies/unassign`

**Request body:** `list[int]` (array of object IDs)

**Response** `200`:

```json
{ "status": "unassigned", "objects_updated": 2 }
```

---

## Exchange

Prefix: `/api/exchange`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/exchange/mailboxes` | Bearer | List mailboxes for a tenant |
| GET | `/api/exchange/mailboxes/{mailbox_id}/snapshots` | Bearer | List snapshots for a mailbox |
| GET | `/api/exchange/mailboxes/{mailbox_id}/snapshots/{snapshot_id}/browse` | Bearer | Browse items in a snapshot |
| GET | `/api/exchange/search` | Bearer | Search emails across snapshots |
| POST | `/api/exchange/mailboxes/{mailbox_id}/restore` | Admin | Restore mailbox data (write access) |
| POST | `/api/exchange/mailboxes/{mailbox_id}/backup` | Admin, Operator | Trigger on-demand backup |
| POST | `/api/exchange/backup-all` | Admin, Operator | Backup all Exchange mailboxes in a tenant |

### GET `/api/exchange/mailboxes`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | Yes | -- | Tenant to query |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 20 | Items per page (max 100) |
| `search` | string | No | -- | Filter by display name |

### GET `/api/exchange/mailboxes/{mailbox_id}/snapshots/{snapshot_id}/browse`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `path` | string | No | -- | Folder path to browse |
| `item_type` | string | No | -- | Filter by item type |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 50 | Items per page (max 200) |

### GET `/api/exchange/search`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | Yes | -- | Tenant to search |
| `query` | string | Yes | -- | Search text (min 1 char) |
| `mailbox_id` | int | No | -- | Limit to specific mailbox |
| `limit` | int | No | 50 | Max results (max 200) |

### POST `/api/exchange/mailboxes/{mailbox_id}/restore`

**Request** (`RestoreRequest`):

```json
{
  "snapshot_id": 5,
  "restore_type": "item_level",
  "item_ids": [101, 102],
  "target_object_id": null
}
```

`restore_type` values: `full_inplace`, `item_level`, `cross_user`, `export`

**Response** `200`:

```json
{ "restore_job_id": 7, "status": "queued", "items_restored": 0 }
```

### POST `/api/exchange/backup-all`

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `tenant_id` | int | 1 | Tenant ID |

**Response** `200`:

```json
{
  "total": 25,
  "succeeded": 24,
  "failed": 1,
  "job_id": 12,
  "results": [{ "mailbox": "...", "email": "...", "status": "success", "snapshot_id": 50, "item_count": 340, "size_bytes": 524288 }]
}
```

---

## OneDrive

Prefix: `/api/onedrive`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/onedrive/accounts` | Bearer | List OneDrive accounts for a tenant |
| GET | `/api/onedrive/accounts/{account_id}/snapshots` | Bearer | List snapshots for an account |
| GET | `/api/onedrive/accounts/{account_id}/snapshots/{snapshot_id}/browse` | Bearer | Browse files in a snapshot |
| GET | `/api/onedrive/search` | Bearer | Search files across snapshots |
| POST | `/api/onedrive/accounts/{account_id}/restore` | Admin | Restore OneDrive data (write access) |
| POST | `/api/onedrive/accounts/{account_id}/backup` | Admin, Operator | Trigger on-demand backup |
| POST | `/api/onedrive/backup-all` | Admin, Operator | Backup all OneDrive accounts in a tenant |

### GET `/api/onedrive/accounts`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | Yes | -- | Tenant to query |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 20 | Items per page (max 100) |
| `search` | string | No | -- | Filter by display name |

### GET `/api/onedrive/search`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | Yes | -- | Tenant to search |
| `query` | string | Yes | -- | Search text (min 1 char) |
| `account_id` | int | No | -- | Limit to specific account |
| `limit` | int | No | 50 | Max results (max 200) |

### POST `/api/onedrive/accounts/{account_id}/restore`

**Request** (`RestoreRequest`):

```json
{
  "snapshot_id": 10,
  "restore_type": "full_inplace",
  "item_ids": null,
  "target_object_id": null
}
```

---

## SharePoint

Prefix: `/api/sharepoint`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/sharepoint/sites` | Bearer | List SharePoint sites for a tenant |
| GET | `/api/sharepoint/sites/{site_id}/snapshots` | Bearer | List snapshots for a site |
| GET | `/api/sharepoint/sites/{site_id}/snapshots/{snapshot_id}/browse` | Bearer | Browse items in a snapshot |
| GET | `/api/sharepoint/search` | Bearer | Search files across snapshots |
| POST | `/api/sharepoint/sites/{site_id}/restore` | Admin | Restore site data (write access) |
| POST | `/api/sharepoint/sites/{site_id}/backup` | Admin, Operator | Trigger on-demand backup |
| POST | `/api/sharepoint/backup-all` | Admin, Operator | Backup all SharePoint sites in a tenant |

### GET `/api/sharepoint/sites`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | Yes | -- | Tenant to query |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 20 | Items per page (max 100) |
| `search` | string | No | -- | Filter by display name |

### GET `/api/sharepoint/search`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | Yes | -- | Tenant to search |
| `query` | string | Yes | -- | Search text (min 1 char) |
| `site_id` | int | No | -- | Limit to specific site |
| `limit` | int | No | 50 | Max results (max 200) |

### POST `/api/sharepoint/sites/{site_id}/restore`

**Request** (`RestoreRequest`):

```json
{
  "snapshot_id": 15,
  "restore_type": "item_level",
  "item_ids": [200, 201]
}
```

Note: SharePoint restore does not support `target_object_id` (no cross-site restore).

---

## Jobs

Prefix: `/api/jobs`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/jobs/backup` | Bearer | List backup jobs (filterable) |
| GET | `/api/jobs/restore` | Bearer | List restore jobs (filterable) |
| GET | `/api/jobs/backup/{job_id}` | Bearer | Get backup job details |
| GET | `/api/jobs/restore/{job_id}` | Bearer | Get restore job details |
| GET | `/api/jobs/failed-summary` | Bearer | Summary of failed/partial jobs with retry eligibility |
| POST | `/api/jobs/backup/{job_id}/retry` | Admin, Operator | Retry a single failed backup job |
| POST | `/api/jobs/retry-all-failed` | Admin, Operator | Retry all eligible failed jobs |
| POST | `/api/jobs/snapshots/{snapshot_id}/retry` | Admin, Operator | Retry a failed snapshot |
| POST | `/api/jobs/mass-recovery` | Admin | Mass recovery for multiple objects (write access) |

### GET `/api/jobs/backup`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | No | -- | Filter by tenant |
| `status` | string | No | -- | Filter by status |
| `workload_type` | string | No | -- | Filter by workload (`exchange`, `onedrive`, `sharepoint`) |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 20 | Items per page (max 100) |

### GET `/api/jobs/restore`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | No | -- | Filter by tenant |
| `status` | string | No | -- | Filter by status |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 20 | Items per page (max 100) |

### POST `/api/jobs/mass-recovery`

**Request** (`MassRecoveryRequest`):

```json
{
  "tenant_id": 1,
  "object_ids": [5, 6, 7, 8],
  "restore_type": "full_inplace"
}
```

**Response** `200`:

```json
{
  "status": "completed",
  "total_jobs": 4,
  "jobs": [
    { "id": 20, "status": "completed", "items_restored": 150 }
  ]
}
```

---

## Dashboard

Prefix: `/api/dashboard`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dashboard/summary` | Bearer | Protection stats, job counts (24h), snapshot/storage totals |
| GET | `/api/dashboard/activity` | Bearer | Daily backup/restore activity over time |
| GET | `/api/dashboard/compliance` | Bearer | SLA compliance status with violation details |
| GET | `/api/dashboard/unprotected` | Bearer | Unprotected and at-risk objects grouped by workload |

### GET `/api/dashboard/summary`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | No | -- | Scope to a single tenant |

### GET `/api/dashboard/activity`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | No | -- | Scope to a single tenant |
| `days` | int | No | 7 | Number of days (1-90) |

### GET `/api/dashboard/compliance`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | No | -- | Scope to a single tenant |

**Response** `200`:

```json
{
  "total": 100,
  "compliant": 95,
  "non_compliant": 5,
  "pending_first_backup": 3,
  "compliance_rate": 95.0,
  "violations": [
    {
      "object_name": "john@contoso.com",
      "workload": "exchange",
      "sla_name": "Gold",
      "last_backup": "2025-01-14T08:00:00",
      "last_backup_status": "success",
      "frequency_hours": 4,
      "reason": "overdue"
    }
  ]
}
```

### GET `/api/dashboard/unprotected`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `tenant_id` | int | No | -- | Scope to a single tenant |

---

## Audit

Prefix: `/api/audit`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/audit/logs` | Bearer | List audit log entries with filtering |

### GET `/api/audit/logs`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `action` | string | No | -- | Filter by action (partial match) |
| `resource_type` | string | No | -- | Filter by resource type (exact) |
| `severity` | string | No | -- | Filter by severity (exact) |
| `search` | string | No | -- | Search within details text |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 50 | Items per page (max 200) |

**Response item:**

```json
{
  "id": 1,
  "user_id": 1,
  "action": "backup.completed",
  "resource_type": "mailbox",
  "resource_id": "42",
  "details": "Backed up 340 items",
  "severity": "info",
  "ip_address": "10.0.0.1",
  "timestamp": "2025-01-15T12:00:00"
}
```

---

## Failed Items

Prefix: `/api/failed-items`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/failed-items` | Bearer | List failed items with filtering |
| GET | `/api/failed-items/summary` | Bearer | Aggregated counts by error category |
| GET | `/api/failed-items/by-snapshot/{snapshot_id}` | Bearer | Failed items for a specific snapshot |
| POST | `/api/failed-items/resolve` | Bearer | Mark items as resolved |
| POST | `/api/failed-items/dismiss-category` | Bearer | Dismiss all items of a category in a snapshot |
| POST | `/api/failed-items/retry` | Bearer | Retry retriable failed items |

### GET `/api/failed-items`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `snapshot_id` | int | No | -- | Filter by snapshot |
| `protected_object_id` | int | No | -- | Filter by protected object |
| `error_category` | string | No | -- | Filter by error category |
| `is_resolved` | bool | No | -- | Filter resolved/unresolved |
| `can_retry` | bool | No | -- | Filter retriable items |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 50 | Items per page (max 200) |

### GET `/api/failed-items/summary`

| Query Param | Type | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `snapshot_id` | int | No | -- | Scope to snapshot |
| `protected_object_id` | int | No | -- | Scope to object |

**Response** `200`:

```json
{
  "total_failed": 42,
  "total_unresolved": 30,
  "categories": [
    {
      "category": "permission_denied",
      "count": 15,
      "resolved": 5,
      "unresolved": 10,
      "retriable": 0,
      "resolution_hint": "Check app permissions in Azure AD"
    }
  ]
}
```

### POST `/api/failed-items/resolve`

**Request** (`ResolveRequest`):

```json
{ "item_ids": [1, 2, 3], "notes": "Acknowledged, items no longer needed" }
```

**Response** `200`:

```json
{ "resolved": 3 }
```

### POST `/api/failed-items/dismiss-category`

| Query Param | Type | Required | Description |
|-------------|------|----------|-------------|
| `snapshot_id` | int | Yes | Target snapshot |
| `category` | string | Yes | Error category to dismiss |

**Response** `200`:

```json
{ "dismissed": 8, "category": "throttled" }
```

### POST `/api/failed-items/retry`

| Query Param | Type | Required | Description |
|-------------|------|----------|-------------|
| `item_ids` | list[int] | Yes | IDs of failed items to retry |

**Response** `200`:

```json
{
  "total_items": 5,
  "objects_retried": 2,
  "results": [
    { "object_id": 10, "object_name": "john@contoso.com", "status": "success", "new_snapshot_id": 55, "items_retried": 3 }
  ]
}
```

---

## Diagnostics

Prefix: `/api/diagnostics` | Requires: Admin or Operator role

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/diagnostics/health` | Full system health check (DB, storage, connector, encryption) |
| GET | `/api/diagnostics/connector-test` | Test M365 connector secret against Azure AD |
| GET | `/api/diagnostics/msal-test` | Direct MSAL token acquisition test |
| GET | `/api/diagnostics/graph-metrics` | Graph API call metrics per tenant/workload |
| GET | `/api/diagnostics/performance` | Backup throughput, restore duration, snapshot stats |
| GET | `/api/diagnostics/circuit-breaker` | Per-tenant circuit breaker state (open/closed/cooldown) |
| GET | `/api/diagnostics/resilience` | Overview of all resilience mechanisms |
| GET | `/api/diagnostics/env` | Non-sensitive environment configuration |

---

## Usage & License

Prefix: `/api/usage` | Requires: Authenticated user

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/usage/tenant/{tenant_id}` | Per-tenant usage metrics (objects, storage, jobs, workloads) |
| GET | `/api/usage/platform` | Platform-wide summary with estimated monthly cost |
| GET | `/api/usage/license` | Current license tier, usage vs limits, alerts |
| GET | `/api/usage/trends` | Usage trends over time (30d/90d) |

---

## Onboarding

Prefix: `/api/onboard` | Requires: Authenticated user

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/onboard/connector-health` | Check connector app configuration health |
| GET | `/api/onboard/platforms` | List available SaaS platforms for connection |
| GET | `/api/onboard/workloads` | List available workloads with metadata |
| GET | `/api/onboard/connect/{platform}` | Start OAuth connection flow (returns auth URL) |
| GET | `/api/onboard/callback` | Handle OAuth callback from Microsoft |
| POST | `/api/onboard/complete` | Finalize onboarding (assign SLA, activate tenant) |
| POST | `/api/onboard/discover` | Run workload-selective discovery |
| GET | `/api/onboard/status/{platform}/{tenant_ms_id}` | Check connection health |

---

## Org Context

Prefix: `/api/org-context` | Requires: Authenticated user

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/org-context/tenant/{tenant_id}` | Full organizational context (hierarchy, VIP groups, criticality) |

## Recovery

Prefix: `/api/recovery` | Requires: Authenticated user

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recovery/mvb-plan/{tenant_id}` | Get MVB recovery plan for a tenant |
| GET | `/api/recovery/confidence/v2/{tenant_id}` | Criticality-weighted recovery confidence score |
