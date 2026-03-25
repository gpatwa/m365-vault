# Changelog

All notable changes to Shieldio are documented in this file.

## [2.0.0] - 2026-03-25

### Rebranded
- **M365 Vault renamed to Shieldio** — repositioned as SaaS Data Protection Platform
- New landing page with story-driven design (problem → solution → proof)
- Redesigned login page with split-panel layout and SSO button
- All docs, UI, API responses updated to Shieldio branding

### New Workloads
- **Microsoft Teams Backup** — channels, messages (Export API), channel files, team settings
- **Teams Chat Backup** — 1-to-1 and group chats via Export API (per-user backup)
- **Teams Restore** — Migration/Import API preserves original timestamps and sender identity
- **Entra ID expanded to 12 object types** — added Service Principals, Admin Units, OAuth Grants, Devices, Domains

### Intelligence & Security
- **Smart Engine** — health baselines, anomaly detection (z-score), health scoring (0-100)
- **Self-Healing + Alerts** — auto-retry by error category, email/webhook notifications
- **WORM Storage** — write-once-read-many with retention locks and legal hold
- **Malware Scan on Restore** — YARA rule-based scanning before restore
- **Sensitive Data Discovery** — PII/PHI/PCI regex scanner on backup data
- **Backup Validation Engine** — automated restore-and-verify with checksum validation
- **Snapshot Diff/Compare** — compare two Entra ID snapshots to detect configuration drift

### Authentication & Access
- **SSO/OIDC (Entra ID)** — MSAL-based SSO with auto-provisioning of users on first login
- **Refresh tokens** — 7-day rotation via POST /auth/refresh
- **Password policy** — configurable min length, uppercase, digit requirements

### Architecture
- **Control Plane / Data Plane separation** — Redis dispatcher + standalone worker process
- **BaseWorker framework** — common worker with parallel processing, retry, checkpointing
- **Circuit breaker** — Graph API protection (50% failure rate → 15-min cooldown)
- **Stale job detection** — auto-requeue jobs stuck IN_PROGRESS for >60 minutes
- **Database connection pooling** — pool_pre_ping, pool_recycle for resilience

### UI & UX
- **Unified search (Cmd+K)** — intent-aware command palette with category grouping
- **WorkloadPageLayout** — shared design system with breadcrumbs, hero stats, action banners
- **DataTable component** — server-side pagination, sorting, filtering, CSV export
- **Dashboard redesign** — platform-grouped workload cards, health score, license status
- **Self-Service Restore** — cross-workload search with inline restore actions
- **Reports & Analytics** — 5-tab reports (performance, storage, failures, compliance, security)
- **Usage & License tracking** — per-tenant usage, license tier, growth trends

### Production Readiness
- **Automated test suite** — 40+ pytest tests (auth, health, API, Entra ID, Teams)
- **Release quality gate** — `make release-check` (7 gates, 10 checks, ~70s)
- **Rate limiting** — 120 req/min/IP middleware
- **Structured logging** — JSON format with correlation IDs and response times
- **Global error handler** — clean JSON errors, no stack trace leaks
- **Deep health check** — DB + storage connectivity verification
- **Performance indexes** — 30+ PostgreSQL indexes for scale
- **Tenant lifecycle** — deactivate/reactivate/purge with cascade cleanup
- **Permission auto-provisioning** — Graph API permissions managed from product

### API
- **107 REST API endpoints**
- Intent-aware search API (GET /search/intent)
- Snapshot compare API (GET /entra-id/compare)
- Status page API (GET /status)
- CSV export API (GET /export)
- Health score API (GET /health/score)

### Infrastructure
- **Redis** for job queue dispatch
- **Worker container** for data plane operations
- **Docker Compose** with 6 services (backend, frontend, worker, postgres, redis, minio)
- **Azure Container Apps** deployment via Terraform IaC
- **GitHub Actions** CI/CD pipeline

### Codebase
- Backend: 15,000+ lines Python (80 files)
- Frontend: 8,000+ lines TypeScript
- Tests: 2,000+ lines
- API Routes: 107
- Git commits: 90+

## [1.5.0] - 2026-03-20

### Added

**Jobs UI Redesign — Workload Swimlanes**
- Replaced flat job table with per-workload swimlane architecture (Exchange, OneDrive, SharePoint)
- Each swimlane shows live stats: total/completed/failed/in-progress counts, segmented progress bar, success rate, average duration, total size
- Click-to-expand drill-down with backup/restore tabs, status filter bar, and per-object progress details
- Color-coded workloads: Exchange (blue), OneDrive (purple), SharePoint (green)
- Scales cleanly to additional workloads — just add to the `WORKLOADS` array
- New components: `WorkloadSwimlane`, `JobTable`, `StatusFilterBar`
- New shared utilities: `formatSize()`, `formatDuration()`, `timeAgo()`

**M365 Workload Discovery Script**
- `scripts/discover_m365.py` discovers users, Exchange mailboxes, OneDrive accounts, and SharePoint sites via Microsoft Graph API
- `--provision` flag triggers OneDrive provisioning for users without activated OneDrive
- Outputs JSON manifest with all discovered objects for onboarding

**Incremental Data Creation Script**
- `scripts/create_incremental_data.py` creates real test data in M365 tenants
- Exchange: emails between users, calendar events, contacts
- SharePoint: document uploads, list creation with custom columns and items

**Cost Management**
- `make az-sleep` — scale Container Apps to zero replicas and stop PostgreSQL to minimize idle costs
- `make az-wake` — resume all Azure resources (start DB + scale apps back up)
- `make az-status` — show current Azure resource status for any environment

**Product Roadmap**
- `docs/M365_Vault_Product_Roadmap.docx` — comprehensive product roadmap with competitive analysis, 4-phase feature plan, pricing strategy, and go-to-market strategy

### Fixed

- Graph API client: client credential flows now use `/.default` scope (individual scopes like `Mail.Read` only work for delegated flows)
- Timezone-aware datetime handling across backup workers (consistent UTC timestamps)
- `make help` now correctly displays target names instead of "Makefile" for each row
- `az-sleep`/`az-wake` use `--min-replicas 0/1` instead of `revision deactivate/activate` (deactivate permanently destroys revisions)

### Changed

- Makefile now auto-loads `SUBSCRIPTION_ID` from `.env.azure` file
- Makefile `help` target fixed to strip filename prefix from `$(MAKEFILE_LIST)` grep output
- Version bumped to 1.5.0

---

## [1.4.0] - 2026-03-17

### Added

**Azure Deployment — Terraform + GitHub Actions**
- Terraform infrastructure-as-code with 6 modules: resource group, ACR, Blob Storage, PostgreSQL Flexible Server, Key Vault, Container Apps
- Two environment configurations: dev (burstable, LRS) and prod (general purpose, GRS, 2+ replicas)
- GitHub Actions CI pipeline: backend/frontend build verification, Terraform validate
- GitHub Actions CD pipeline: build Docker images → push to ACR → deploy Container Apps (OIDC auth, no stored secrets)
- Manual production deployment with approval gate
- Azure Deployment Guide (`docs/AZURE_DEPLOYMENT.md`)

**Deployment Automation**
- `scripts/bootstrap-azure.sh` — one-command Azure + GitHub bootstrap: creates service principal, OIDC federated credentials, Terraform remote state storage, and sets all GitHub secrets
- Terraform remote state backend (Azure Blob Storage) for shared state across CI/CD and developers
- `Makefile` with 25+ targets: `make dev`, `make build`, `make bootstrap`, `make tf-plan`, `make deploy-dev`, `make deploy-prod`, `make seed`, and more
- Deploy workflow updated with OIDC-authenticated Terraform remote state initialization
- `make tf-set-acr-secrets` to auto-populate ACR secrets from Terraform output after first apply

### Changed

- CORS origins now configurable via `CORS_ORIGINS` environment variable (comma-separated)
- Backend health probes (`/health`) used by Container Apps for liveness and readiness
- Terraform backend migrated from local state to Azure Blob Storage remote state

---

## [1.3.0] - 2026-03-17

### Added

**Pluggable Storage Backend**
- Abstract `StorageBackend` interface with three implementations: `LocalStorageBackend` (filesystem), `AzureBlobStorageBackend` (Azure Blob Storage), `MinIOStorageBackend` (S3-compatible / MinIO)
- `STORAGE_BACKEND` config switch: `local` (default), `azure`, `minio`
- Storage factory (`storage_factory.py`) creates the appropriate backend from environment config
- All storage I/O goes through the backend interface — no direct filesystem coupling in business logic

**Docker Compose — Local-Production Parity**
- `docker-compose.yml` with PostgreSQL 16, MinIO, Backend, and Frontend services
- Backend Dockerfile (Python 3.12-slim) and Frontend Dockerfile (Node 20 build + nginx)
- nginx reverse proxy: `/api` routes to backend, SPA fallback for client-side routing
- MinIO auto-initialization: creates `m365vault-backups` bucket on startup
- Health checks for PostgreSQL and MinIO with dependency ordering
- Volume persistence for database and object storage

**Cloud Database Support**
- Added `asyncpg>=0.29.0` for PostgreSQL async driver
- `DATABASE_URL` already supports both SQLite and PostgreSQL — now with the driver installed

### Changed

- Storage service refactored from filesystem-coupled to backend-agnostic: all `os.path`, `os.makedirs`, `aiofiles.open`, `shutil.rmtree` replaced with `StorageBackend.write/read/delete/exists/delete_prefix`
- `ChunkStore` moved into `storage.py` and uses `StorageBackend` for all chunk I/O
- Frontend API client uses `VITE_API_BASE` env var (relative `/api` for Docker, absolute URL for dev)
- Added `azure-storage-blob>=12.0` and `aioboto3>=13.0` dependencies

---

## [1.2.0] - 2026-03-17

### Added

**Storage Efficiency — Compression + Deduplication Pipeline**
- Content-aware **zstd compression** with adaptive levels: level 9 for JSON/text (70-85% reduction), level 3 for unknown binary, automatic skip for pre-compressed formats (.zip, .docx, .jpg, .mp4, .pdf, etc.)
- **SHA-256 content-addressable deduplication** across snapshots within each tenant — identical items stored once with reference counting
- **Content-Defined Chunking (CDC)** for large files (≥ 4 MB) using gear-hash rolling hash with variable-size chunks (target 64 KB, min 16 KB, max 256 KB)
- Per-chunk dedup with 2-level directory fan-out: `data/{tenant}/.chunks/{hash[:2]}/{hash[2:4]}/{hash}.chunk`
- **M3VZ header protocol** (5-byte magic + flags) placed inside the encrypted envelope for backward-compatible format detection
- New `StoreResult` dataclass returned by `store_item()` with compression ratio, content hash, and storage flags
- New `DedupEntry` model with reference counting for safe garbage collection on snapshot deletion
- New `compressed_size` and `storage_flags` columns on `SnapshotItem` for per-item storage metrics
- Configurable settings: `COMPRESSION_ENABLED`, `COMPRESSION_ZSTD_LEVEL_TEXT/BINARY`, `COMPRESSION_MIN_SIZE`, `DEDUP_ENABLED`, `CDC_THRESHOLD_BYTES`, `CDC_TARGET/MIN/MAX_CHUNK_BYTES`

**Data Simulation Script**
- Added `scripts/simulate_backup_data.py` for local testing without a live M365 tenant
- Covers three use cases: initial full backup, incremental with dedup, and large file CDC chunking
- Seeds tenant, users, SLA policies, protected objects, backup/restore jobs, failed items, and audit logs
- Exercises the real compression + dedup + encryption pipeline end-to-end

### Changed

- Storage pipeline order: Raw data → Compress → M3VZ Header → SHA-256 Hash → Dedup Check → CDC (if large) → AES-256-GCM Encrypt → Write → Register Dedup Index
- Retrieval pipeline: Read → Decrypt → Header Check → Dechunk (if chunked) → Decompress → Return
- Legacy blobs (pre-compression) are returned as-is — zero migration required
- All three backup workers (Exchange, OneDrive, SharePoint) now pass `filename`, `mime_type`, and `db` to `store_item()` and populate `compressed_size`, `content_hash`, `storage_flags` on `SnapshotItem`
- Snapshot deletion decrements dedup reference counts; blobs/chunks deleted only when ref_count reaches 0
- Added `zstandard>=0.23.0` dependency

---

## [1.1.0] - 2026-03-16

### Security

**Least-Privilege Graph API Access**
- Separated Microsoft Graph API scopes into read-only (backup) and read-write (restore) scope sets
- Backup operations now use read-only scopes: `Mail.Read`, `Calendars.Read`, `Contacts.Read`, `Files.Read.All`, `Sites.Read.All`
- Restore operations use read-write scopes: `Mail.ReadWrite`, `Calendars.ReadWrite`, `Contacts.ReadWrite`, `Files.ReadWrite.All`, `Sites.ReadWrite.All`
- Added `access_mode` parameter to `GraphClient` with three modes: `backup` (read-only), `restore` (read-write), `default` (legacy)
- Read-only enforcement: backup clients block POST/PUT/PATCH/DELETE at the client level with `ReadOnlyViolationError`

**RBAC Enforcement on All Endpoints**
- Backup trigger endpoints (`POST backup`, `POST backup-all`) now require ADMIN or OPERATOR role
- Restore endpoints (`POST restore`, `POST mass-recovery`) now require ADMIN role only
- Retry endpoints (`POST retry`, `POST retry-all-failed`) now require ADMIN or OPERATOR role
- VIEWER role is restricted to read-only browsing (GET endpoints only)
- Added `require_backup_permission` and `require_restore_permission` convenience dependencies

### Documentation

- Added **Tenant Security Guide** (`docs/TENANT_SECURITY.md`) — comprehensive guide covering Azure AD app registration, credential encryption, tenant data isolation, least-privilege Graph API access, RBAC for tenant operations, and production hardening recommendations
- Added tenant onboarding security checklist

### Changed

- License changed from MIT to **Apache License 2.0** for stronger patent protection

---

## [1.0.0] - 2026-03-16

### Added

**Core Platform**
- Multi-tenant Microsoft 365 data protection for Exchange Online, OneDrive for Business, and SharePoint Online
- FastAPI backend with async SQLAlchemy and aiosqlite
- React 19 frontend with TypeScript, TailwindCSS, and Recharts

**Backup & Restore**
- SLA policy-based automated backup scheduling with configurable frequency and retention
- Point-in-time restore with four modes: full in-place, item-level, cross-user, and export
- Per-workload backup workers for Exchange (mail, calendar, contacts), OneDrive (files), and SharePoint (document libraries)
- Snapshot browsing with folder navigation and item search
- Mass recovery operations for bulk restore across workloads

**Microsoft Graph Integration**
- OAuth2 client credentials flow via MSAL
- Rate limiting with 429 Retry-After header compliance
- Exponential backoff with jitter for transient errors
- Concurrent request semaphore (configurable, default 10)
- Batch API support (up to 20 requests per batch)
- Delta query support for incremental backups

**Security**
- AES-256-GCM envelope encryption with two-layer DEK/KEK key scheme
- JWT authentication with configurable token expiration
- bcrypt password hashing
- Role-based access control: Admin, Operator, Viewer
- Tenant client secret encryption at rest

**Reliability**
- Failed item tracking with 13 error categories and resolution guidance
- Automatic retry engine with exponential backoff (runs every 10 minutes)
- Manual retry for individual jobs, snapshots, or all failed jobs
- Retention management with automated expired snapshot cleanup (runs every 6 hours)

**Observability**
- Dashboard with protection coverage, backup activity charts, and SLA compliance
- Collapsible unprotected item visibility grouped by workload
- Comprehensive audit logging with severity levels and full-text search
- Failed items page with error categorization and fix actions

**API**
- 50+ REST endpoints across 10 resource routers
- Auto-generated OpenAPI documentation at `/docs`
- Pagination, filtering, and search across all list endpoints

**Documentation**
- README with quickstart guide
- Onboarding documentation for new tenant setup
- Complete API reference
- Architecture guide
- Compliance and security report
