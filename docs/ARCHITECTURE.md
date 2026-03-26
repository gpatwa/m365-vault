# Shieldio — Architecture Guide

## 1. System Overview

Shieldio is a SaaS data protection platform for Microsoft 365 workloads
(Exchange Online, OneDrive for Business, SharePoint Online). It connects to tenants via
the Microsoft Graph API, discovers protectable objects, runs SLA-driven backup schedules,
stores encrypted point-in-time snapshots, and provides granular restore capabilities.

```mermaid
graph TB
    subgraph Frontend["Frontend (React 19 + Vite)"]
        UI[Dashboard / Workload Pages]
        CMD[Command Palette ⌘K]
        Tour[Product Tour]
    end

    subgraph Backend["Backend (FastAPI + Python)"]
        API[REST API - 115+ endpoints]
        Auth[Auth - JWT / SSO / RBAC]
        Sched[Scheduler - APScheduler]

        subgraph Services
            Backup[Backup Engine]
            Restore[Restore Engine]
            Discovery[Discovery Service]
            Smart[Smart Engine]
            Alert[Alert Service]
        end

        subgraph Workers
            EX[Exchange Worker]
            OD[OneDrive Worker]
            SP[SharePoint Worker]
            TM[Teams Worker]
            EN[Entra ID Worker]
        end
    end

    subgraph Storage["Storage Layer"]
        PG[(PostgreSQL)]
        Blob[(Azure Blob / MinIO)]
        KV[(Key Vault)]
        Redis[(Redis Queue)]
    end

    subgraph External["External"]
        Graph[Microsoft Graph API]
        SMTP[SMTP / Webhook]
    end

    UI --> API
    CMD --> API
    API --> Auth
    API --> Services
    Sched --> Backup
    Services --> Workers
    Workers --> Graph
    Backup --> Blob
    Backup --> PG
    Smart --> PG
    Alert --> SMTP
    Auth --> PG
    Backup --> KV

    style Frontend fill:#dbeafe,stroke:#3b82f6
    style Backend fill:#f0fdf4,stroke:#22c55e
    style Storage fill:#fef3c7,stroke:#f59e0b
    style External fill:#fce7f3,stroke:#ec4899
```

```
+---------------------+       +----------------------------+
|   React 19 SPA      |       |  Microsoft Graph API       |
|   (Vite + TS)       |       |  graph.microsoft.com/v1.0  |
|   TanStack Query    |       +------------^---------------+
+--------+------------+                    |
         | HTTP/JSON                       | OAuth2 Client
         v                                 | Credentials
+--------+----------------------------+    |
|           FastAPI Backend           |    |
|  +------+  +--------+  +---------+ |    |
|  | Auth |  | Router |  | Sched.  | |    |
|  | (JWT)|  | Layer  |  |(APSched)| |    |
|  +------+  +---+----+  +----+----+ |    |
|                |             |      |    |
|  +-------------v-------------v--+   |    |
|  |       Service Layer          |   |    |
|  | Backup | Restore | Discovery |---+    |
|  | Retry  | Catalog | Graph CLI |        |
|  +-------------+----------------+        |
|                |                         |
|  +-------------v----------------+        |
|  |        Worker Layer          |        |
|  | Exchange | OneDrive | SP     |        |
|  +-------------+----------------+        |
|                |                         |
|  +------+------v------+                  |
|  | SQLAlchemy (async)  |                 |
|  | SQLite / PostgreSQL |                 |
|  +------+--------------+                 |
|         |                                |
|  +------v--------------+                 |
|  | Encrypted Blob Store|                 |
|  | AES-256-GCM (local) |                 |
|  +----------------------+                |
+------------------------------------------+
```

### Request Lifecycle

1. Browser sends JWT-authenticated request to FastAPI.
2. Router validates token, enforces RBAC, and calls the service layer.
3. Service layer coordinates business logic (backup, restore, discovery).
4. Workers interact with the Graph API and the encrypted storage layer.
5. Results flow back through the service layer to the API response.


## 2. Backend Architecture

### Framework and Async Lifecycle

The backend is a **FastAPI** application (`backend/app/main.py`) using Python's
`asynccontextmanager`-based lifespan for startup/shutdown:

**Startup sequence:**
1. `init_db()` -- creates all SQLAlchemy tables via `Base.metadata.create_all`.
2. Ensure `BACKUP_STORAGE_PATH` directory exists on disk.
3. `start_scheduler()` -- registers three APScheduler interval jobs.

**Shutdown sequence:**
1. `stop_scheduler()` -- gracefully shuts down APScheduler.

### Router Registration

Ten API routers are mounted on the app:

| Router          | Prefix             | Purpose                        |
|-----------------|--------------------|---------------------------------|
| `auth`          | `/api/auth`        | Login, register, user mgmt     |
| `tenants`       | `/api/tenants`     | Tenant CRUD and discovery       |
| `sla_policies`  | `/api/sla`         | SLA policy management           |
| `exchange`      | `/api/exchange`    | Exchange backup/restore/search  |
| `onedrive`      | `/api/onedrive`    | OneDrive backup/restore/search  |
| `sharepoint`    | `/api/sharepoint`  | SharePoint backup/restore       |
| `jobs`          | `/api/jobs`        | Backup job monitoring + retry   |
| `dashboard`     | `/api/dashboard`   | Aggregated stats and metrics    |
| `audit`         | `/api/audit`       | Audit log queries               |
| `failed_items`  | `/api/failed-items`| Failed item tracking/resolution |

### Dependency Injection

FastAPI's `Depends()` system provides:
- **Database sessions** via `get_db()` -- async generator that auto-commits or
  rolls back on error.
- **Authentication** via `get_current_user()` -- decodes JWT, loads `User` from DB.
- **Role enforcement** via `require_role(*roles)` -- factory that returns a dependency
  checking `current_user.role` against allowed roles.

### Configuration

`backend/app/config.py` uses `pydantic_settings.BaseSettings` to load config from
environment variables or a `.env` file. Key settings groups:

- **App:** name, version, secret key, JWT algorithm, token expiry.
- **Database:** async SQLAlchemy URL (default `sqlite+aiosqlite`).
- **Storage:** backup path on disk, encryption master key.
- **Graph API:** base URL, auth URL, scope, throttle limits.
- **Scheduler:** check interval in seconds.


## 3. Data Model

Nine models (eight domain tables plus one join) in `backend/app/models/`:

```
+----------+       +-------------+        +-----------+
|  User    |       |   Tenant    |        | SLAPolicy |
|----------|       |-------------|        |-----------|
| id (PK)  |       | id (PK)     |        | id (PK)   |
| username |       | name        |        | name      |
| email    |       | ms_tenant_id|        | freq_hrs  |
| pass_hash|       | client_id   |        | ret_days  |
| role     |       | client_sec* |        | priority  |
| is_active|       | status      |        | is_locked |
+----------+       +------+------+        +-----+-----+
     |                    |                      |
     |  +----------------+|+---------------------+
     |  |                 ||
     |  |   +-------------v|------------+
     |  |   |  ProtectedObject          |
     |  |   |---------------------------|
     |  |   | id (PK)                   |
     |  |   | tenant_id (FK -> Tenant)  |
     |  |   | sla_policy_id (FK -> SLA) |
     |  |   | workload_type (enum)      |
     |  |   | ms_object_id              |
     |  |   | status (enum)             |
     |  |   +-------------+-------------+
     |  |                 |
     |  |   +-------------v-------------+
     |  |   |  BackupJob                |     +----------------+
     |  |   |---------------------------|     |  Snapshot       |
     |  |   | id (PK)                   |     |----------------|
     |  |   | tenant_id (FK)            |     | id (PK)        |
     |  |   | workload_type             |     | prot_obj_id(FK)|
     |  |   | sla_policy_id (FK)        |     | snapshot_type  |
     |  |   | status (enum)             |     | status (enum)  |
     |  |   | retry_count / max_retries |     | delta_token    |
     |  |   | retry_of_job_id (self-FK) |     | blob_path      |
     |  |   | failed_object_ids (JSON)  |     | encryption_key |
     |  |   +---------------------------+     +-------+--------+
     |  |                                             |
     |  |                                   +---------+---------+
     |  |                                   |                   |
     |  |                            +------v------+   +--------v-------+
     |  |                            | SnapshotItem|   | FailedItem     |
     |  |                            |-------------|   |----------------|
     |  |                            | id (PK)     |   | id (PK)        |
     |  |                            | snapshot_id |   | snapshot_id(FK)|
     |  |                            | item_type   |   | prot_obj_id(FK)|
     |  |                            | ms_item_id  |   | error_category |
     |  |                            | blob_path   |   | error_message  |
     |  |                            | subject     |   | resolution_hint|
     |  |                            | sender      |   | is_resolved    |
     |  |                            | file_name   |   | can_retry      |
     |  |                            +-------------+   +----------------+
     |  |
     |  |   +-----------------------+
     +--+-->|  AuditLog             |
            |-----------------------|
            | id (PK)               |
            | user_id (FK -> User)  |
            | action                |
            | resource_type/id      |
            | severity              |
            | timestamp             |
            +-----------------------+
```

### Model Details

| Model             | Table               | Purpose                                                 |
|-------------------|----------------------|----------------------------------------------------------|
| **User**          | `users`              | Admin accounts with role-based access (admin/operator/viewer). |
| **Tenant**        | `tenants`            | M365 tenant with encrypted OAuth credentials and discovery counts. |
| **SLAPolicy**     | `sla_policies`       | Backup frequency (hours), retention (days), priority, retention lock. |
| **ProtectedObject** | `protected_objects` | A mailbox, OneDrive account, or SharePoint site linked to a tenant and SLA. |
| **BackupJob**     | `backup_jobs`        | Tracks a backup run across multiple objects with JSON progress details. Self-referencing FK for retry lineage. |
| **Snapshot**      | `snapshots`          | Point-in-time backup of one protected object. Stores delta token for incremental sync and encrypted blob path. |
| **SnapshotItem**  | `snapshot_items`     | Individual item within a snapshot (email, file, calendar event, contact, list, list item). |
| **FailedItem**    | `failed_items`       | Items that failed during backup with categorized errors and resolution hints. |
| **AuditLog**      | `audit_logs`         | Immutable record of every significant operation (backup, restore, config change). |

### Key Enumerations

- **WorkloadType:** `exchange`, `onedrive`, `sharepoint`
- **ProtectionStatus:** `protected`, `unprotected`, `paused`, `error`
- **JobStatus:** `queued`, `in_progress`, `completed`, `failed`, `cancelled`, `partial`
- **SnapshotType:** `full`, `incremental`
- **RestoreType:** `full_inplace`, `item_level`, `cross_user`, `export`, `mass_recovery`
- **ErrorCategory:** 13 categories from `permission_denied` to `unknown`, each with a human-readable resolution hint.
- **ItemType:** `email`, `calendar_event`, `contact`, `file`, `folder`, `list`, `list_item`, `document_library`


## 4. Service Layer

Ten services in `backend/app/services/`:

### 4.1 AuthService (`auth.py`)
- Password hashing via **bcrypt**.
- JWT creation and validation using **python-jose** (HS256).
- `get_current_user` dependency extracts the user from the `Authorization` header.
- `require_role(*roles)` dependency factory for RBAC enforcement at the route level.

### 4.2 GraphClient (`graph_client.py`)
- OAuth2 client credentials flow via **MSAL** with automatic token caching and refresh.
- **Least-privilege access modes** (v1.1.0):
  - `backup` mode — read-only scopes (`Mail.Read`, `Files.Read.All`, etc.); POST/PUT/PATCH/DELETE blocked at the client level with `ReadOnlyViolationError`.
  - `restore` mode — read-write scopes (`Mail.ReadWrite`, `Files.ReadWrite.All`, etc.); all HTTP methods allowed.
  - `default` mode — legacy `.default` scope for backward compatibility.
- Concurrency-limited requests (`asyncio.Semaphore`, default 10 concurrent).
- **Throttle handling:** exponential backoff with jitter on HTTP 429, honoring `Retry-After`.
- **Server error retry:** exponential backoff on 5xx responses.
- **Timeout retry:** retries on `httpx.TimeoutException`.
- **Pagination:** `get_all_pages()` follows `@odata.nextLink` automatically.
- **Delta queries:** `get_delta()` supports incremental sync via `@odata.deltaLink`.
- **Batch API:** `batch_request()` sends up to 20 requests per `$batch` call.
- Tracks request/throttle counters for observability.

### 4.3 DiscoveryService (`discovery.py`)
- Discovers all Exchange mailboxes and OneDrive accounts from `/users` endpoint.
- Discovers SharePoint sites via three fallback methods:
  1. `/sites/getAllSites` (preferred, requires `Sites.Read.All`).
  2. `/sites?search=*` (search-based fallback).
  3. M365 Groups -> group site roots (last resort).
- Upserts `ProtectedObject` records (insert or update by tenant + workload + ms_object_id).
- Updates tenant discovery counts and timestamp.

### 4.4 BackupEngine (`backup_engine.py`)
- Orchestrates backup jobs across all workload types.
- Uses a **read-only** (`access_mode="backup"`) Graph client — write operations are blocked at the client level.
- Determines snapshot type (full vs. incremental based on prior snapshot existence).
- Creates `Snapshot` record, initializes encrypted storage, dispatches to the appropriate worker.
- Tracks per-object progress in `BackupJob.progress_details` (JSON with status, item counts, errors).
- Saves a `manifest.json` alongside each snapshot's encrypted blobs.
- Final job status: `completed` if all objects succeed, `partial` if some fail, `failed` if all fail.

### 4.5 RestoreEngine (`restore_engine.py`)
- Supports five restore types: full in-place, item-level, cross-user, export, and mass recovery.
- Uses a **read-write** (`access_mode="restore"`) Graph client — full POST/PUT access for restoring data.
- Decrypts the snapshot's wrapped DEK, then dispatches to the appropriate worker.
- Mass recovery runs multiple restore jobs in parallel with `asyncio.Semaphore` concurrency control (default 5).

### 4.6 RetryEngine (`retry_engine.py`)
- Scans for `FAILED` or `PARTIAL` backup jobs eligible for retry.
- Enforces exponential backoff between retries: 5 min, 15 min, 45 min.
- For `PARTIAL` jobs: retries only the failed objects (targeted retry).
- For `FAILED` jobs: retries all objects.
- Tracks `retry_count` and `failed_object_ids` on the job for lineage.
- Exposes `retry_single_job()` and `retry_failed_snapshot()` for manual API-triggered retries.

### 4.7 EncryptionService (`encryption.py`)
- AES-256-GCM envelope encryption (see Section 8 for full flow).
- Generates random 256-bit DEKs per snapshot.
- Wraps/unwraps DEKs with the KEK (derived from master key).
- Encrypts/decrypts backup data blobs.
- Convenience methods for string encryption (tenant client secrets).

### 4.8 StorageService (`storage.py`)
- Manages encrypted blob storage on the local filesystem.
- Directory hierarchy: `data/{tenant_id}/{workload}/{object_id}/{snapshot_id}/`
- Each snapshot directory contains:
  - `wrapped_dek.key` -- the encrypted DEK for the snapshot.
  - `manifest.json` -- snapshot metadata.
  - `items/{item_id}.blob` -- individually encrypted item blobs.
- Supports snapshot deletion for retention cleanup.
- Reports storage usage stats (total size, file count).

### 4.9 CatalogService (`catalog.py`)
- Cross-snapshot search for emails (by subject, sender, recipients, date range).
- Cross-snapshot search for files (by name, path, workload type).
- Browse items within a specific snapshot with path/type filtering.
- Snapshot statistics (item count, total size).

### 4.10 Scheduler (`scheduler.py`)
- Uses **APScheduler** `AsyncIOScheduler` to manage three periodic jobs (see Section 6).


## 5. Background Workers

Three workload-specific workers in `backend/app/workers/`. Each worker implements both
backup and restore logic and follows the same constructor pattern, receiving `db`,
`graph`, `storage`, and `encryption` dependencies.

### 5.1 ExchangeWorker (`exchange_worker.py`)
**Backup:** Messages (per-folder delta queries), calendar events, contacts, and attachments.
- Discovers all mail folders for a user, then runs delta sync on each folder independently.
- Stores per-folder delta tokens as a JSON dict for incremental backups.
- Falls back to well-known folders (Inbox, Sent Items, Drafts) if folder listing fails.
- Uses `@retry_async` decorator for item-level retries (3 attempts, 2s base delay).
- Records `FailedItem` entries for items that fail after all retries.

**Restore:** Full mailbox restore (creates messages in target mailbox via Graph),
item-level restore, and `.eml` export.

### 5.2 OneDriveWorker (`onedrive_worker.py`)
**Backup:** Files and folders with full directory structure via `/drive/root/delta`.
- Downloads actual file content via `/drive/items/{id}/content`.
- Falls back to metadata-only backup if file download fails.
- Tracks `content_hash` (SHA-256) for dedup detection.
- Item-level retry with `@retry_async`.

**Restore:** Full account restore (recreates folder structure, then uploads files),
item-level restore, and direct file download from backup.

### 5.3 SharePointWorker (`sharepoint_worker.py`)
**Backup:** Document libraries (files/folders via delta), lists, and list items.
- Enumerates all drives on a site, then delta-syncs each drive.
- Separately backs up non-hidden SharePoint lists and their items (with field expansion).
- Item-level retry with `@retry_async`.

**Restore:** Full site restore (files uploaded to original drive paths),
item-level restore for specific files.


## 6. Scheduler

The scheduler (`backend/app/services/scheduler.py`) registers three jobs at startup via
APScheduler's `AsyncIOScheduler`:

| Job ID               | Interval    | Function                      | Purpose |
|----------------------|-------------|-------------------------------|---------|
| `backup_scheduler`   | 60 seconds  | `check_and_schedule_backups`  | Scans all protected objects with active SLA policies. Creates `BackupJob` records for objects whose `last_backup_at` + SLA frequency has elapsed. Then executes all queued jobs. |
| `retention_cleanup`  | 6 hours     | `cleanup_expired_snapshots`   | Finds completed snapshots past their SLA retention period. Marks them `expired` and deletes their on-disk encrypted storage. Respects retention lock (`is_locked`). |
| `retry_failed_jobs`  | 10 minutes  | `retry_failed_jobs`           | Invokes the RetryEngine to scan and re-execute eligible failed/partial jobs with exponential backoff (5/15/45 min delays). |

Each job opens its own `async_session` and handles errors independently to avoid
cascading failures.


## 7. Frontend Architecture

### Technology Stack
- **React 19** with TypeScript, built with **Vite**.
- **TanStack Query** (React Query) for server state management, caching, and automatic refetching.
- **Tailwind CSS** for styling.
- **Lucide React** for iconography.
- **React Router v6** for client-side routing.

### Page Structure

The app uses a sidebar layout (`components/Layout.tsx`) with an `<Outlet />` for
nested routes. All authenticated routes are wrapped in a `ProtectedRoute` guard
that checks for a stored JWT token.

| Route             | Page Component  | Purpose                              |
|-------------------|-----------------|---------------------------------------|
| `/`               | `Dashboard`     | Aggregated backup stats and metrics   |
| `/exchange`       | `Exchange`      | Exchange mailbox management + search  |
| `/onedrive`       | `OneDrive`      | OneDrive account management + search  |
| `/sharepoint`     | `SharePoint`    | SharePoint site management            |
| `/sla-policies`   | `SLAPolicies`   | SLA policy CRUD                       |
| `/jobs`           | `Jobs`          | Backup job monitoring with progress   |
| `/failed-items`   | `FailedItems`   | Failed item tracking and resolution   |
| `/settings`       | `Settings`      | Tenant configuration                  |
| `/audit`          | `AuditLog`      | Audit log viewer                      |
| `/login`          | `Login`         | Authentication (unauthenticated)      |

### State Management

- **Server state:** TanStack Query manages all API data with automatic background
  refetching, cache invalidation on mutations, and optimistic updates.
- **Auth state:** JWT token stored in the API client singleton (`api.getToken()` /
  `api.clearToken()`), checked by `ProtectedRoute` on every navigation.
- **No global client state store** (no Redux/Zustand) -- component-local state and
  TanStack Query cover all needs.


## 8. Security Architecture

### Encryption Flow (DEK/KEK Envelope Encryption)

```
                    +------------------+
                    |  Master Key      |
                    |  (32-byte, env)  |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  KEK             |
                    |  (AES-256-GCM)   |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
   +-------------------+        +-------------------+
   | Wrap DEK           |        | Encrypt tenant    |
   | (per snapshot)     |        | client_secret     |
   +-------------------+        +-------------------+
              |
              v
   +-------------------+
   | DEK                |
   | (random 256-bit)   |
   | encrypts item data |
   +-------------------+
```

1. **Master Key** is loaded from `ENCRYPTION_MASTER_KEY` env var (must be 32 bytes).
2. **KEK** (Key Encryption Key) is derived directly from the master key.
3. Each **Snapshot** gets a unique random **DEK** (Data Encryption Key).
4. The DEK is **wrapped** (encrypted) with the KEK using AES-256-GCM and stored as
   `wrapped_dek.key` alongside the snapshot.
5. Each backup item is encrypted with the snapshot's DEK (AES-256-GCM, 12-byte random
   nonce prepended to ciphertext).
6. Tenant `client_secret` values are encrypted with the KEK before database storage.

**At-rest guarantees:** All backup data and sensitive credentials are AES-256-GCM
encrypted. The master key never touches disk -- it comes from the environment.

### Authentication Flow

1. User submits credentials to `/api/auth/login`.
2. Server verifies password hash (bcrypt) and returns a signed JWT (HS256).
3. JWT contains `sub` (username) and `exp` claims; default expiry is 24 hours.
4. Frontend stores the token in memory and sends it as `Authorization: Bearer <token>`.
5. `get_current_user` dependency decodes the JWT and loads the `User` from the database.

### RBAC Enforcement

Three roles with least-privilege permissions (updated in v1.1.0):

| Role       | Capabilities                                              |
|------------|-----------------------------------------------------------|
| `admin`    | Full access: tenant management, user management, backup triggers, **restore/recovery** |
| `operator` | Backup triggers, discovery, SLA assignment, retry failed jobs, view audit logs |
| `viewer`   | Read-only access to dashboards, job status, snapshots, and audit logs |

**Endpoint-level enforcement (v1.1.0):**

| Operation | Required Role | Dependency |
|-----------|---------------|------------|
| Browse / search / list (GET) | Any authenticated user | `get_current_user` |
| Trigger backup | Admin, Operator | `require_backup_permission` |
| Trigger restore / mass recovery | **Admin only** | `require_restore_permission` |
| Retry failed jobs | Admin, Operator | `require_backup_permission` |
| Tenant / SLA management | Admin | `require_role(ADMIN)` |

Enforcement is at the route level using `Depends(require_role(UserRole.ADMIN))` or
the convenience dependencies `require_backup_permission` / `require_restore_permission`.
The dependency raises HTTP 403 if the user's role is not in the permitted set.

### CORS

Development CORS allows `localhost:5173`, `localhost:5174`, `localhost:3000`, and
`127.0.0.1:5173`. This must be restricted to the production frontend origin in
deployment.


## 9. Deployment Considerations

### Database: SQLite to PostgreSQL Migration

The default database is **SQLite** (`sqlite+aiosqlite`) for development simplicity.
For production:

1. Change `DATABASE_URL` to a PostgreSQL async URL:
   `postgresql+asyncpg://user:pass@host:5432/shieldio`
2. SQLAlchemy models use standard types compatible with both engines.
3. Consider adding Alembic for schema migrations in production.
4. SQLite's single-writer limitation makes it unsuitable for concurrent backup jobs.

### TLS / HTTPS

- The FastAPI server does not terminate TLS itself.
- Deploy behind a reverse proxy (Nginx, Caddy, or a cloud load balancer) with TLS
  termination.
- Ensure the frontend-to-backend connection uses HTTPS in production.
- Update CORS `allow_origins` to the production domain only.

### Secrets Management

- Replace the default `SECRET_KEY` and `ENCRYPTION_MASTER_KEY` with cryptographically
  random values (`openssl rand -hex 32`).
- Use a secrets manager (Vault, AWS Secrets Manager, Azure Key Vault) rather than
  environment variables for the master key in production.
- Never commit `.env` files to version control.

### Scaling

- **Horizontal API scaling:** Stateless FastAPI instances behind a load balancer.
  Ensure only one instance runs the APScheduler (use a leader election mechanism or
  separate scheduler process).
- **Worker concurrency:** `GRAPH_MAX_CONCURRENT_REQUESTS` (default 10) limits
  parallel Graph API calls per tenant. Tune based on Microsoft throttling limits.
- **Storage:** Replace local filesystem with S3-compatible object storage for
  durability and scalability. The `StorageService` abstraction makes this a
  contained change.
- **Queue-based workers:** For large-scale deployments, replace the in-process
  backup execution with a task queue (Celery, Dramatiq) to distribute backup
  work across multiple worker nodes.
- **Monitoring:** Instrument with Prometheus/OpenTelemetry metrics for backup
  job duration, failure rates, Graph API throttle rates, and storage consumption.
