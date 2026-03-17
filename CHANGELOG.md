# Changelog

All notable changes to M365 Vault are documented in this file.

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
