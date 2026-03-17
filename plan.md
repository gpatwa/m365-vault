# M365 SaaS Data Protection — Implementation Plan

## Overview
Build a Rubrik-style M365 data protection product covering **Exchange, OneDrive, and SharePoint** with:
- **Control Plane** — FastAPI backend (orchestration, scheduling, RBAC, API)
- **Data Plane** — Background workers (backup/restore via Microsoft Graph API)
- **Storage** — Local filesystem (backup blobs) + SQLite (metadata, catalog)
- **Frontend** — React + TypeScript dashboard

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Dashboard                     │
│  (Status, Browse, Search, Restore, SLA Management)   │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Control Plane                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Auth/RBAC│ │SLA Engine│ │Job Sched.│ │REST API│ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Catalog  │ │ Audit Log│ │ Reports  │            │
│  └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Data Plane (Workers)                     │
│  ┌───────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │Exchange Worker│ │OneDrive Wrkr │ │SharePt Wrkr│  │
│  └───────┬───────┘ └──────┬───────┘ └─────┬──────┘  │
│          │ Graph API       │ Graph API     │ Graph   │
│  ┌───────▼─────────────────▼───────────────▼──────┐  │
│  │         Microsoft Graph API Client             │  │
│  │  (OAuth2, Throttle-aware, Retry, Batching)     │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Storage Layer                           │
│  ┌────────────┐  ┌─────────────────────────────┐    │
│  │  SQLite DB │  │  Local Filesystem            │    │
│  │ (metadata, │  │  (encrypted backup blobs,    │    │
│  │  catalog,  │  │   organized by snapshot/     │    │
│  │  jobs,     │  │   workload/user)             │    │
│  │  audit)    │  │                              │    │
│  └────────────┘  └─────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
m365-data-protection/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── config.py                # Settings & env config
│   │   ├── database.py              # SQLite setup (aiosqlite)
│   │   ├── models/                  # SQLAlchemy/Pydantic models
│   │   │   ├── user.py              # App users & RBAC
│   │   │   ├── tenant.py            # M365 tenant config
│   │   │   ├── sla_policy.py        # SLA domain definitions
│   │   │   ├── protected_object.py  # Mailboxes, drives, sites
│   │   │   ├── backup_job.py        # Job tracking
│   │   │   ├── snapshot.py          # Point-in-time snapshots
│   │   │   ├── restore_job.py       # Restore job tracking
│   │   │   └── audit_log.py         # Audit entries
│   │   ├── api/                     # REST API routes
│   │   │   ├── auth.py              # Login, JWT tokens
│   │   │   ├── tenants.py           # M365 tenant onboarding
│   │   │   ├── sla_policies.py      # SLA CRUD + assignment
│   │   │   ├── exchange.py          # Exchange browse/search/restore
│   │   │   ├── onedrive.py          # OneDrive browse/search/restore
│   │   │   ├── sharepoint.py        # SharePoint browse/search/restore
│   │   │   ├── jobs.py              # Job status & history
│   │   │   ├── dashboard.py         # Dashboard stats
│   │   │   └── audit.py             # Audit log queries
│   │   ├── services/                # Business logic
│   │   │   ├── graph_client.py      # MS Graph API client (throttle-aware)
│   │   │   ├── discovery.py         # Auto-discover M365 objects
│   │   │   ├── backup_engine.py     # Backup orchestration
│   │   │   ├── restore_engine.py    # Restore orchestration
│   │   │   ├── scheduler.py         # SLA-based job scheduling (APScheduler)
│   │   │   ├── encryption.py        # AES-256 envelope encryption
│   │   │   ├── storage.py           # Local filesystem blob storage
│   │   │   └── catalog.py           # Metadata catalog & search
│   │   └── workers/                 # Data plane workers
│   │       ├── exchange_worker.py   # Exchange backup/restore
│   │       ├── onedrive_worker.py   # OneDrive backup/restore
│   │       └── sharepoint_worker.py # SharePoint backup/restore
│   ├── requirements.txt
│   ├── alembic.ini                  # DB migrations (optional)
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                     # API client layer
│       │   └── client.ts
│       ├── components/
│       │   ├── Layout.tsx           # Shell with sidebar
│       │   ├── Sidebar.tsx
│       │   ├── ProtectionStatus.tsx # Protection health cards
│       │   ├── JobsTable.tsx        # Running/recent jobs
│       │   ├── ObjectBrowser.tsx    # Browse backup contents
│       │   └── RestoreWizard.tsx    # Multi-step restore flow
│       ├── pages/
│       │   ├── Dashboard.tsx        # Overview with stats
│       │   ├── Exchange.tsx         # Exchange management
│       │   ├── OneDrive.tsx         # OneDrive management
│       │   ├── SharePoint.tsx       # SharePoint management
│       │   ├── SLAPolicies.tsx      # SLA policy management
│       │   ├── Jobs.tsx             # Job history & monitoring
│       │   ├── Settings.tsx         # Tenant & app config
│       │   └── AuditLog.tsx         # Audit trail viewer
│       ├── hooks/
│       │   └── useApi.ts
│       └── types/
│           └── index.ts
└── README.md
```

## Implementation Steps (In Order)

### Phase 1: Foundation (Backend Core)
1. **Project scaffolding** — Initialize Python project, install deps (FastAPI, uvicorn, aiosqlite, SQLAlchemy, httpx, cryptography, APScheduler, python-jose, passlib)
2. **Database models & schema** — Define all SQLAlchemy models (Tenant, SLAPolicy, ProtectedObject, BackupJob, Snapshot, SnapshotItem, RestoreJob, AuditLog, User)
3. **Config & database setup** — Environment config, SQLite connection, auto-create tables
4. **Auth system** — JWT-based auth with login/register, password hashing, RBAC middleware
5. **Encryption service** — AES-256 envelope encryption (DEK per snapshot, KEK for DEKs, stored securely)
6. **Storage service** — Local filesystem blob manager with directory structure: `data/{tenant_id}/{workload}/{object_id}/{snapshot_id}/`

### Phase 2: Microsoft Graph Integration
7. **Graph API client** — OAuth2 client credentials flow, token caching, auto-refresh, throttle-aware with exponential backoff, request batching ($batch endpoint)
8. **M365 tenant onboarding API** — Register tenant with client_id/client_secret, validate connectivity, store config
9. **Discovery service** — Auto-discover all Exchange mailboxes, OneDrive accounts, SharePoint sites via Graph API, store as ProtectedObjects

### Phase 3: SLA Policy Engine
10. **SLA domain model** — Define policies with: name, backup frequency (hours), retention period (days), priority
11. **SLA assignment** — Hierarchical assignment: Application-level → Group-level → Individual object level (with inheritance + override)
12. **SLA-based scheduler** — APScheduler integration that reads SLA policies and auto-schedules backup jobs per the defined frequency

### Phase 4: Backup Engine (Data Plane)
13. **Exchange backup worker** — Backup mailbox messages, calendars, contacts via Graph API. Forever-incremental using delta queries. Store as encrypted blobs + metadata in SQLite catalog
14. **OneDrive backup worker** — Backup files/folders via Graph delta API. Download file content, store encrypted. Track file metadata (name, path, size, modified)
15. **SharePoint backup worker** — Backup site document libraries, lists, list items via Graph API. Delta-based incremental
16. **Snapshot management** — Create point-in-time snapshots, link to backup items, track full vs incremental, manage retention/expiry

### Phase 5: Restore Engine
17. **Exchange restore** — In-place full mailbox restore, individual item restore, restore to different user, export as .eml files
18. **OneDrive restore** — Full account restore, individual file/folder restore, restore to different user, download files
19. **SharePoint restore** — Full site restore, item-level restore (files, list items)
20. **Mass recovery** — Bulk restore multiple objects in parallel using asyncio

### Phase 6: Frontend Dashboard
21. **React project setup** — Vite + React + TypeScript + React Router + TailwindCSS + React Query + Recharts
22. **Layout & navigation** — App shell with sidebar (Dashboard, Exchange, OneDrive, SharePoint, SLA Policies, Jobs, Settings, Audit Log)
23. **Dashboard page** — Protection summary cards (total protected, last backup status, storage used), backup/restore job activity chart, compliance status
24. **SLA Policies page** — Create/edit/delete SLA policies, assign to workloads/groups/objects
25. **Exchange page** — List protected mailboxes, browse snapshots, search emails across snapshots, trigger restore with wizard
26. **OneDrive page** — List protected accounts, browse file trees from snapshots, search files, restore wizard
27. **SharePoint page** — List protected sites, browse document libraries/lists, restore wizard
28. **Jobs page** — Real-time job table (running, completed, failed), filters by workload/status/date
29. **Settings page** — Tenant configuration (client ID, secret, tenant ID), test connection button
30. **Audit Log page** — Searchable/filterable audit trail of all operations

### Phase 7: Polish & Integration
31. **Audit logging** — Log all significant operations (backup start/complete/fail, restore, config changes, login)
32. **Error handling & notifications** — Global error handling, job failure alerts on dashboard
33. **API throttling dashboard** — Show Graph API usage/throttling stats

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph API auth | Client credentials (app-only) | No user interaction needed for backups |
| Incremental backup | MS Graph delta queries | Built-in change tracking, efficient |
| Job scheduling | APScheduler | Lightweight, in-process, SQLite job store |
| Encryption | AES-256-GCM envelope | Industry standard, per-snapshot DEK |
| Frontend state | React Query | Server-state caching, auto-refresh |
| Styling | TailwindCSS | Rapid UI development, consistent design |
| Charts | Recharts | React-native, good for dashboards |

## Database Schema (Key Tables)

- **tenants** — id, name, tenant_id, client_id, client_secret (encrypted), status, created_at
- **sla_policies** — id, name, backup_frequency_hours, retention_days, priority, is_locked, created_at
- **protected_objects** — id, tenant_id, workload_type (exchange/onedrive/sharepoint), object_id (Graph ID), display_name, email, sla_policy_id, status, last_backup_at
- **snapshots** — id, protected_object_id, snapshot_type (full/incremental), status, started_at, completed_at, size_bytes, item_count, delta_token
- **snapshot_items** — id, snapshot_id, item_type (email/file/list_item), item_id, name, path, size, metadata_json, blob_path
- **backup_jobs** — id, tenant_id, workload_type, sla_policy_id, status, started_at, completed_at, objects_processed, objects_failed, error_message
- **restore_jobs** — id, tenant_id, source_snapshot_id, restore_type (full/item/export/cross_user), target_object_id, status, started_at, completed_at, items_restored, error_message
- **audit_logs** — id, user_id, action, resource_type, resource_id, details_json, timestamp
- **users** — id, username, email, password_hash, role (admin/operator/viewer), created_at

## Microsoft Graph API Endpoints Used

### Exchange
- `GET /users/{id}/messages` — List emails (with delta: `GET /users/{id}/messages/delta`)
- `GET /users/{id}/messages/{msgId}` — Get email with body
- `GET /users/{id}/messages/{msgId}/$value` — Get MIME content
- `GET /users/{id}/calendars` — List calendars
- `GET /users/{id}/events` — List calendar events
- `GET /users/{id}/contacts` — List contacts
- `POST /users/{id}/messages` — Restore email

### OneDrive
- `GET /users/{id}/drive/root/children` — List root items
- `GET /users/{id}/drive/root/delta` — Delta changes
- `GET /users/{id}/drive/items/{itemId}/content` — Download file
- `PUT /users/{id}/drive/items/{parentId}:/{filename}:/content` — Upload/restore file

### SharePoint
- `GET /sites` — List sites
- `GET /sites/{siteId}/drives` — Document libraries
- `GET /sites/{siteId}/drives/{driveId}/root/delta` — Delta changes
- `GET /sites/{siteId}/lists` — Lists
- `GET /sites/{siteId}/lists/{listId}/items` — List items
- `PUT /sites/{siteId}/drives/{driveId}/items/{parentId}:/{name}:/content` — Restore file

### Discovery
- `GET /users` — List all users (for Exchange + OneDrive)
- `GET /sites?search=*` — List all SharePoint sites
- `GET /groups` — List groups for SLA assignment
