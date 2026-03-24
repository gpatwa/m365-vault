# Shieldio — Compliance & Security Report

**Product:** Shieldio v1.1.0
**Report Date:** 2026-03-16
**Classification:** Internal — Confidential
**Prepared By:** Security & Compliance Engineering

---

## 1. Executive Summary

Shieldio is a data protection platform for Microsoft 365 workloads. It provides automated backup, encrypted storage, and policy-driven retention for Exchange Online mailboxes, SharePoint Online document libraries, and associated collaboration data.

This report documents the security controls implemented in version 1.1.0, assesses their alignment with GDPR, SOC 2 Type II, and HIPAA regulatory frameworks, and identifies gaps that must be addressed before production deployment.

Key findings:

- **Encryption:** AES-256-GCM envelope encryption with per-snapshot Data Encryption Keys (DEKs) wrapped by a Key Encryption Key (KEK). All Graph API communication occurs over HTTPS/TLS.
- **Access Control:** Role-based access control (RBAC) with three defined roles, JWT-based authentication, and bcrypt password hashing.
- **Audit:** Append-only audit log model capturing user actions, resource changes, IP addresses, and severity levels.
- **Retention:** SLA-driven retention lifecycle with configurable retention periods, retention lock to prevent premature deletion, and automated expired-snapshot cleanup.
- **Reliability:** Structured error classification across 13 categories, exponential backoff with jitter, Graph API rate-limit compliance, and automated retry scheduling.

Several production-hardening gaps remain, most notably around key management (no HSM/KMS integration), the use of development-grade default secrets, and the absence of multi-factor authentication. These are detailed in Section 8.

---

## 2. Data Protection Controls

### 2.1 Encryption at Rest

Shieldio implements a two-layer envelope encryption scheme using AES-256-GCM, provided by the `cryptography` library's `AESGCM` primitive.

| Property | Implementation |
|---|---|
| Algorithm | AES-256-GCM (authenticated encryption with associated data) |
| DEK Generation | 256-bit random key via `os.urandom(32)`, unique per snapshot |
| KEK Derivation | Master key truncated/padded to 32 bytes; used as the KEK directly |
| Key Wrapping | DEK encrypted with KEK using AES-256-GCM; output includes nonce, ciphertext, and timestamp |
| Nonce | 96-bit (12-byte) random nonce per encryption operation via `os.urandom(12)` |
| Authentication Tag | 128-bit GCM tag appended to ciphertext, providing integrity verification |
| Encrypted Output Format | Nonce (12 bytes) concatenated with ciphertext + tag |
| String Encryption | Client secrets and sensitive configuration values encrypted directly with the KEK |

Each snapshot receives its own DEK, limiting the blast radius of any single key compromise to one point-in-time backup.

### 2.2 Encryption in Transit

All communication with Microsoft Graph API is conducted over HTTPS (TLS) via the `httpx` async client. The base URL is hardcoded to `https://graph.microsoft.com/v1.0`, and the authentication endpoint uses `https://login.microsoftonline.com`. No plaintext HTTP endpoints are configured.

### 2.3 Key Management

| Component | Current State |
|---|---|
| Master Key Source | `ENCRYPTION_MASTER_KEY` environment variable (via `.env` or `pydantic_settings`) |
| Default Value | Development placeholder (`change-me-32-byte-master-key-!!`) |
| Key Length Enforcement | Padded to 32 bytes if shorter; truncated if longer |
| HSM / KMS Integration | Not implemented |
| Key Rotation | Not implemented |

The master key is loaded at application startup and held in process memory for the lifetime of the service. Wrapped DEK records include a `wrapped_at` timestamp to support future key-rotation auditing.

---

## 3. Access Control

### 3.1 Role-Based Access Control (RBAC)

Three roles are defined in the `UserRole` enumeration with least-privilege enforcement (v1.1.0):

| Role | Intended Scope |
|---|---|
| `admin` | Full system access: user management, tenant configuration, SLA policy administration, backup triggers, and **restore/recovery operations** (write access) |
| `operator` | Operational access: trigger and monitor backups, retry failed jobs, SLA assignment, view audit logs. **Cannot perform restore or mass recovery** |
| `viewer` | Read-only access: view backup status, browse snapshots, search items, and view reports. **Cannot trigger any backup or restore operations** |

Role enforcement is implemented via the `require_role()` dependency factory and two convenience dependencies:
- `require_backup_permission` — allows ADMIN and OPERATOR (read-only Graph operations)
- `require_restore_permission` — allows ADMIN only (write Graph operations)

| Endpoint Category | Required Role | Graph Access |
|---|---|---|
| Browse / search / list (GET) | Any authenticated user | N/A |
| Trigger backup | Admin, Operator | Read-only scopes |
| Trigger restore / mass recovery | Admin only | Read-write scopes |
| Retry failed jobs | Admin, Operator | Read-only scopes |

This separation ensures that even if an operator's credentials are compromised, the attacker cannot write data back to the M365 tenant.

### 3.2 Authentication

| Control | Implementation |
|---|---|
| Token Format | JSON Web Token (JWT) via `python-jose` |
| Signing Algorithm | HS256 (HMAC-SHA256) |
| Token Expiration | Configurable; default 1440 minutes (24 hours) |
| Password Hashing | bcrypt with automatic salt generation |
| Token Endpoint | `POST /api/auth/login` (OAuth2 password flow) |
| Credential Validation | Token decoded and verified on every request; inactive users rejected |

### 3.3 Account Management

| Feature | Implementation |
|---|---|
| User Activation | `is_active` flag on User model; inactive users are denied authentication |
| Deactivation | Setting `is_active = 0` immediately invalidates all subsequent token validations |
| Unique Constraints | Username and email enforced unique at the database level |
| Timestamps | `created_at` and `updated_at` tracked automatically |

---

## 4. Audit Capabilities

### 4.1 Audit Log Model

The `AuditLog` model captures the following fields:

| Field | Type | Purpose |
|---|---|---|
| `id` | Integer (PK) | Unique, auto-incrementing log entry identifier |
| `user_id` | Foreign Key | Links to the acting user (nullable for system-initiated actions) |
| `action` | String(100) | Structured action identifier (e.g., `backup.start`, `restore.complete`) |
| `resource_type` | String(100) | Entity type affected (e.g., `tenant`, `sla_policy`, `protected_object`) |
| `resource_id` | Integer | Identifier of the affected resource |
| `details` | Text | JSON payload with action-specific context |
| `ip_address` | String(45) | Source IP address (supports IPv4 and IPv6) |
| `severity` | String(20) | Log level: `info`, `warning`, `error`, `critical` |
| `timestamp` | DateTime | UTC timestamp of the event, indexed for query performance |

### 4.2 Immutability

The audit log table is designed as append-only. The model defines no update or delete operations; records are inserted with server-generated timestamps and sequential primary keys. There is no application-level API endpoint for modifying or removing audit entries.

### 4.3 Queryable Filters

The `action` and `timestamp` columns are indexed, supporting efficient filtering by event type and time range. The `severity` field enables filtering for security-relevant events (e.g., `critical` or `error` severity).

---

## 5. Data Retention & Lifecycle

### 5.1 SLA-Based Retention

Retention periods are governed by SLA policies. Each protected object is assigned an SLA policy specifying `retention_days`. Snapshots are eligible for expiration once their age exceeds the configured retention period.

### 5.2 Retention Lock

SLA policies support a `is_locked` flag. When set to `1`:

- The retention period cannot be shortened.
- Expired snapshots under a locked policy are excluded from automated cleanup.
- Policy deletion is blocked.

This provides a compliance hold mechanism analogous to immutable retention in enterprise backup platforms.

### 5.3 Automated Cleanup

The scheduler runs `cleanup_expired_snapshots` every 6 hours. For each completed snapshot:

1. The snapshot's age is compared against its SLA policy's `retention_days`.
2. If expired and the policy is not locked, the snapshot status is set to `EXPIRED`.
3. Associated storage blobs are deleted from disk.

Cleanup errors are caught, logged, and the database transaction is rolled back to prevent partial state.

---

## 6. Backup Integrity & Reliability

### 6.1 Snapshot Immutability

Once a snapshot reaches `COMPLETED` status, its encrypted blob path and DEK reference are fixed. The snapshot model does not expose update endpoints for completed backup data. Snapshots transition only through a defined lifecycle: `IN_PROGRESS` -> `COMPLETED` | `FAILED` -> `EXPIRED`.

### 6.2 Failed Item Tracking

Every item that fails during backup is recorded in the `FailedItem` model with structured metadata. The system defines 13 error categories:

| Category | HTTP Trigger | Description |
|---|---|---|
| `permission_denied` | 403 | Insufficient Graph API permissions |
| `not_found` | 404 | Item deleted in M365 since discovery |
| `throttled` | 429 | Rate limit retries exhausted |
| `timeout` | 408 | Request timed out after retries |
| `quota_exceeded` | 507 | Storage or API quota reached |
| `file_too_large` | 413 | File exceeds Graph download limit |
| `encryption_error` | — | DEK or encryption subsystem failure |
| `storage_error` | — | Backup storage write failure |
| `invalid_data` | — | Malformed Graph API response |
| `auth_expired` | 401 | Token or credentials expired |
| `server_error` | 5xx | Microsoft Graph server error |
| `network_error` | — | Connection or DNS failure |
| `unknown` | — | Unclassified error |

Each failed item record includes the error category, HTTP status, Graph error code, retry count, a human-readable resolution hint, and resolution tracking fields (`is_resolved`, `resolved_at`, `resolved_by`).

### 6.3 Retry Engine

| Parameter | Value |
|---|---|
| Max Retries (Graph Client) | 5 |
| Base Delay | 1.0 second |
| Backoff Strategy | Exponential (2^attempt) with random jitter |
| Max Delay Cap | 120 seconds (Graph client), 60 seconds (retry decorator) |
| Retry Scheduling | Automated every 10 minutes via APScheduler |
| Permanent Error Detection | HTTP 400, 401, 403, 404, 405, 409, 410, 422 classified as non-retryable |
| Retryable Errors | HTTP 408, 429, 500, 502, 503, 504; plus specific Graph error codes |

The `classify_error()` function distinguishes retryable from permanent errors following Microsoft's published Graph API error-handling guidance. Permanent errors are never retried.

### 6.4 Graph API Rate Limit Compliance

| Control | Implementation |
|---|---|
| Concurrency Limiter | `asyncio.Semaphore` capped at 10 concurrent requests |
| Throttle Response Handling | Respects `Retry-After` header from 429 responses |
| Batch Requests | Up to 20 requests per `$batch` call (Graph API maximum) |
| Usage Statistics | `get_stats()` tracks total requests, throttle count, and throttle rate |

---

## 7. Regulatory Alignment

### 7.1 GDPR (General Data Protection Regulation)

| GDPR Requirement | Shieldio Control | Status |
|---|---|---|
| Data minimization | Backup scope defined by SLA policy and protected object assignment | Implemented |
| Encryption of personal data | AES-256-GCM envelope encryption at rest; TLS in transit | Implemented |
| Right to erasure | Retention-based automated deletion; retention lock for legal holds | Partial — no on-demand per-item purge |
| Audit trail | Append-only audit log with user, action, resource, IP, and timestamp | Implemented |
| Data breach notification | Audit log severity levels support breach event detection | Partial — no automated alerting |
| Tenant isolation | Per-tenant data paths and per-snapshot encryption keys | Implemented |
| Data portability | Restore API enables data export from backup | Implemented |

### 7.2 SOC 2 Type II

| SOC 2 Criterion | Shieldio Control | Status |
|---|---|---|
| CC6.1 — Logical access | RBAC with three roles; JWT authentication; inactive-user blocking | Implemented |
| CC6.2 — Credentials | bcrypt password hashing; configurable token expiration | Implemented |
| CC6.3 — Authorization | `require_role()` enforcement on API endpoints | Implemented |
| CC7.2 — System monitoring | Audit log with severity-based event capture | Implemented |
| CC7.3 — Change management | Audit log tracks configuration changes to SLA policies and tenants | Implemented |
| CC8.1 — Encryption | AES-256-GCM at rest; TLS in transit | Implemented |
| A1.2 — Backup recovery | Automated SLA-driven scheduling; retry engine; snapshot restore | Implemented |
| A1.3 — Recovery testing | No automated recovery validation | Gap |

### 7.3 HIPAA (Health Insurance Portability and Accountability Act)

| HIPAA Safeguard | Shieldio Control | Status |
|---|---|---|
| 164.312(a)(1) — Access control | RBAC; unique user identifiers; emergency access not implemented | Partial |
| 164.312(a)(2)(iv) — Encryption | AES-256-GCM meets the NIST standard for ePHI encryption | Implemented |
| 164.312(b) — Audit controls | Audit log with user, action, timestamp, IP address | Implemented |
| 164.312(c)(1) — Integrity | GCM authentication tags verify data integrity; content hashing on snapshot items | Implemented |
| 164.312(d) — Authentication | JWT tokens; bcrypt hashing; unique usernames | Implemented |
| 164.312(e)(1) — Transmission security | HTTPS/TLS for all Graph API communication | Implemented |
| 164.308(a)(5)(ii)(C) — Log-in monitoring | Audit log captures authentication events | Partial — no failed-login lockout |

---

## 8. Gaps & Recommendations

The following items must be addressed for production hardening:

| # | Gap | Risk | Recommendation | Priority |
|---|---|---|---|---|
| 1 | Default secret key and master encryption key are development placeholders | Critical — trivial key compromise | Require injection via secrets manager (e.g., AWS Secrets Manager, Azure Key Vault, HashiCorp Vault) at deployment time; fail startup if defaults are detected | P0 |
| 2 | No HSM or KMS integration for master key | High — master key exists in plaintext in process memory and environment variables | Integrate with a hardware security module or cloud KMS for KEK storage and key-wrapping operations | P0 |
| 3 | No key rotation mechanism | High — compromised key has unlimited exposure window | Implement DEK re-wrapping on KEK rotation; version-stamp wrapped DEKs | P1 |
| 4 | No multi-factor authentication (MFA) | High — single-factor JWT auth is insufficient for administrative access | Add TOTP or WebAuthn as a second factor for admin and operator roles | P1 |
| 5 | JWT algorithm is HS256 (symmetric) | Medium — secret key compromise allows token forgery | Migrate to RS256 (asymmetric) to separate signing and verification | P1 |
| 6 | Token expiration defaults to 24 hours | Medium — long-lived tokens increase session hijacking window | Reduce to 30-60 minutes; implement refresh token rotation | P1 |
| 7 | No failed-login lockout or brute-force protection | Medium — accounts vulnerable to credential stuffing | Implement progressive lockout after N failed attempts; add rate limiting on `/api/auth/login` | P1 |
| 8 | No automated alerting on critical audit events | Medium — security events may go unnoticed | Integrate with SIEM or notification pipeline for `critical` and `error` severity events | P2 |
| 9 | No automated backup recovery validation | Medium — restore integrity is unverified | Implement periodic restore-and-verify jobs with checksum validation | P2 |
| 10 | No TLS configuration for the application server itself | Medium — internal API traffic may be unencrypted | Deploy behind a TLS-terminating reverse proxy or configure TLS certificates directly | P1 |
| 11 | SQLite database in development mode | High — not suitable for concurrent production workloads | Migrate to PostgreSQL with connection pooling and encrypted connections | P0 |
| 12 | `DEBUG = True` in default configuration | Medium — exposes stack traces and internal state | Set `DEBUG = False` in production; gate debug mode behind environment variable validation | P1 |
| 13 | No data-at-rest encryption for the database itself | Medium — audit logs and metadata stored in plaintext database | Enable transparent data encryption (TDE) or full-disk encryption on the database volume | P2 |

---

## 9. Control Matrix

The following matrix maps implemented controls to applicable regulatory frameworks.

| Control ID | Control Description | GDPR | SOC 2 | HIPAA | Implementation |
|---|---|---|---|---|---|
| ENC-001 | AES-256-GCM encryption at rest | Art. 32(1)(a) | CC8.1 | 164.312(a)(2)(iv) | `EncryptionService` — per-snapshot DEK, KEK wrapping |
| ENC-002 | Per-snapshot unique DEK generation | Art. 32(1)(a) | CC8.1 | 164.312(a)(2)(iv) | `generate_dek()` — `os.urandom(32)` |
| ENC-003 | TLS for Graph API communication | Art. 32(1)(a) | CC8.1 | 164.312(e)(1) | HTTPS base URL enforced in `Settings` |
| ENC-004 | GCM authentication tag integrity | Art. 32(1)(b) | CC8.1 | 164.312(c)(1) | 128-bit tag on all encrypted payloads |
| ACC-001 | RBAC with admin/operator/viewer roles | Art. 32(1)(b) | CC6.1, CC6.3 | 164.312(a)(1) | `UserRole` enum, `require_role()`, `require_backup_permission`, `require_restore_permission` |
| ACC-005 | Least-privilege Graph API scopes | Art. 25, Art. 32(1)(b) | CC6.3 | 164.312(a)(1) | Backup uses read-only scopes; restore uses read-write scopes; `ReadOnlyViolationError` blocks writes on backup clients |
| ACC-002 | JWT token authentication | — | CC6.2 | 164.312(d) | `create_access_token()`, HS256 signing |
| ACC-003 | bcrypt password hashing | — | CC6.2 | 164.312(d) | `hash_password()` with auto-salt |
| ACC-004 | User activation/deactivation | — | CC6.1 | 164.312(a)(1) | `is_active` flag; inactive users blocked at token validation |
| AUD-001 | Append-only audit log | Art. 30 | CC7.2, CC7.3 | 164.312(b) | `AuditLog` model — insert-only, indexed timestamps |
| AUD-002 | Severity-classified events | Art. 33 | CC7.2 | 164.312(b) | `severity` field: info, warning, error, critical |
| AUD-003 | IP address capture | Art. 30 | CC7.2 | 164.312(b) | `ip_address` field (IPv4/IPv6) |
| RET-001 | SLA-based retention periods | Art. 5(1)(e) | A1.2 | 164.312(c)(1) | `retention_days` on SLA policy |
| RET-002 | Retention lock | Art. 17(3) | A1.2 | 164.312(c)(1) | `is_locked` flag prevents deletion of snapshots and policy modification |
| RET-003 | Automated expired-snapshot cleanup | Art. 5(1)(e) | A1.2 | — | `cleanup_expired_snapshots()` — runs every 6 hours |
| REL-001 | Failed item tracking (13 categories) | — | A1.2 | — | `FailedItem` model with `ErrorCategory` enum |
| REL-002 | Exponential backoff with jitter | — | A1.2 | — | `retry_async` decorator; Graph client retry logic |
| REL-003 | Graph API rate limit compliance | — | A1.2 | — | Semaphore (10 concurrent), `Retry-After` header, batch requests (20/batch) |
| REL-004 | Automated retry scheduling | — | A1.2 | — | `retry_failed_jobs()` — runs every 10 minutes |
| ISO-001 | Tenant data isolation | Art. 32(1)(b) | CC6.1 | 164.312(a)(1) | Per-tenant storage paths, per-tenant Graph credentials |

---

*End of Report*
