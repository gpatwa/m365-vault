# Changelog

All notable changes to M365 Vault are documented in this file.

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
