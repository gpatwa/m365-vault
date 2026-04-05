# KavachIQ — Tenant Security Guide

**Product:** KavachIQ v2.3.0
**Classification:** Internal — Confidential
**Audience:** Administrators, Security Engineers, Compliance Officers

---

## 1. Overview

Each Microsoft 365 tenant connected to KavachIQ represents a trust boundary. This document explains how KavachIQ secures tenant credentials, isolates tenant data, enforces least-privilege access to the Microsoft Graph API, and controls which users can perform operations against each tenant.

**Key principles:**

- **Credential encryption at rest** — Azure AD client secrets are AES-256-GCM encrypted before database storage
- **Least-privilege Graph API access** — Backup operations use read-only scopes; restore operations use read-write scopes
- **Tenant data isolation** — Each tenant's backup data is stored in a separate directory tree with per-**snapshot** encryption keys (unique DEK per snapshot, not per tenant)
- **Role-based access control** — Only ADMIN users can register tenants and perform restore operations

---

## 2. Azure AD App Registration

### 2.1 Prerequisites

Before connecting a tenant, create an **App Registration** in the target Azure AD tenant:

1. Navigate to **Azure Portal > Azure Active Directory > App Registrations > New Registration**
2. Name: `KavachIQ Backup` (or your organization's naming convention)
3. Supported account types: **Single tenant**
4. Click **Register**

### 2.2 Graph API Permissions (Least-Privilege)

KavachIQ v1.1.0 enforces separate permission sets for backup (read-only) and restore (read-write). Configure your Azure AD app with only the permissions you need:

#### Backup-Only Deployment (Recommended Starting Point)

If you only need backup capabilities, grant **read-only** application permissions:

| Permission | Type | Purpose |
|---|---|---|
| `Mail.Read` | Application | Read mailbox messages and folders |
| `Calendars.Read` | Application | Read calendar events |
| `Contacts.Read` | Application | Read contacts |
| `Files.Read.All` | Application | Read OneDrive files and folders |
| `Sites.Read.All` | Application | Read SharePoint sites and document libraries |
| `User.Read.All` | Application | Enumerate users for discovery |

With these permissions, the backup engine can read all M365 data but **cannot modify anything** in the tenant — even if an attacker compromises the backup system.

#### Full Backup + Restore Deployment

If you need both backup and restore capabilities, grant **read-write** application permissions:

| Permission | Type | Purpose |
|---|---|---|
| `Mail.ReadWrite` | Application | Read mailbox data (backup) and create messages (restore) |
| `Calendars.ReadWrite` | Application | Read events (backup) and create events (restore) |
| `Contacts.ReadWrite` | Application | Read contacts (backup) and create contacts (restore) |
| `Files.ReadWrite.All` | Application | Read files (backup) and upload files (restore) |
| `Sites.ReadWrite.All` | Application | Read sites (backup) and restore documents |
| `User.Read.All` | Application | Enumerate users for discovery |

### 2.3 Admin Consent

All permissions above are **Application** type (not Delegated), requiring **Azure AD Global Administrator** consent:

1. Navigate to **API Permissions** in your App Registration
2. Click **Grant admin consent for [Tenant Name]**
3. Confirm the consent prompt

### 2.4 Client Secret

1. Navigate to **Certificates & secrets > Client secrets > New client secret**
2. Set an appropriate expiry (recommended: 12 months with rotation reminders)
3. Copy the secret value immediately — it is shown only once
4. Store it securely until you register the tenant in KavachIQ

---

## 3. Tenant Registration & Credential Security

### 3.1 Registration Flow

Only users with the **ADMIN** role can register new tenants:

```
POST /api/tenants/
Authorization: Bearer <admin_token>

{
  "name": "Contoso Ltd",
  "ms_tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_secret": "your-client-secret-value"
}
```

### 3.2 Client Secret Encryption

When a tenant is registered, the `client_secret` is **immediately encrypted** before database storage:

```
client_secret (plaintext)
        |
        v
  EncryptionService.encrypt_string()
        |
        v
  AES-256-GCM encryption with KEK
  (12-byte random nonce + ciphertext + 128-bit GCM auth tag)
        |
        v
  Base64-encoded → stored as `client_secret_encrypted` in DB
```

| Property | Value |
|---|---|
| Algorithm | AES-256-GCM |
| Key | KEK (Key Encryption Key) derived from `ENCRYPTION_MASTER_KEY` |
| Nonce | 12-byte random per encryption (via `os.urandom(12)`) |
| Authentication | 128-bit GCM tag provides integrity verification |
| Storage format | Base64(nonce + ciphertext + tag) |

**The plaintext client secret is never stored on disk or in the database.** It exists in memory only during the registration API call and when creating a Graph API client for backup/restore operations.

### 3.3 Decryption (Runtime Only)

Client secrets are decrypted only when needed to authenticate with the Microsoft Graph API:

```python
# In BackupEngine / RestoreEngine:
client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
graph = GraphClient(tenant.ms_tenant_id, tenant.client_id, client_secret)
```

The decrypted secret is held in memory for the duration of the API session and is not persisted.

---

## 4. Tenant Data Isolation

### 4.1 Storage Isolation

Each tenant's backup data is stored in a completely separate directory tree:

```
data/
├── {tenant_1_id}/
│   ├── exchange/
│   │   └── {mailbox_object_id}/
│   │       └── {snapshot_id}/
│   │           ├── manifest.json
│   │           ├── wrapped_dek.key
│   │           └── items/
│   │               ├── {item_id}.blob    ← AES-256-GCM encrypted
│   │               └── ...
│   ├── onedrive/
│   │   └── ...
│   └── sharepoint/
│       └── ...
├── {tenant_2_id}/
│   └── ...                               ← Completely separate tree
```

**There is no cross-tenant data access** — a backup engine operating on Tenant 1's data cannot read or write Tenant 2's storage paths.

### 4.2 Encryption Isolation

Each snapshot within each tenant receives its own unique **Data Encryption Key (DEK)**:

```
Tenant 1, Snapshot A  →  DEK-A  (random 256-bit key)
Tenant 1, Snapshot B  →  DEK-B  (different random key)
Tenant 2, Snapshot C  →  DEK-C  (different random key)
```

Even if one DEK is compromised, only a single snapshot's data is exposed — not the entire tenant's history or other tenants' data.

### 4.3 Graph API Isolation

Each tenant connects to Microsoft Graph using its own Azure AD app credentials:

- **Separate `client_id` and `client_secret`** per tenant
- **Separate MSAL `ConfidentialClientApplication`** per tenant
- **Separate OAuth2 token cache** per Graph client instance
- **No token sharing** between tenants

---

## 5. Least-Privilege Graph API Access (v1.1.0)

### 5.1 Access Modes

KavachIQ v1.1.0 introduced access mode separation in the `GraphClient`:

| Access Mode | Graph Scopes | HTTP Methods Allowed | Used By |
|---|---|---|---|
| `backup` | Read-only (`Mail.Read`, `Files.Read.All`, etc.) | GET only | `BackupEngine` |
| `restore` | Read-write (`Mail.ReadWrite`, `Files.ReadWrite.All`, etc.) | GET, POST, PUT, DELETE | `RestoreEngine` |
| `default` | `.default` (all granted permissions) | All | Legacy / connection test |

### 5.2 Client-Level Write Guard

The backup client enforces read-only access at the code level — even if the Azure AD app has read-write permissions:

```python
# In GraphClient._ensure_write_allowed():
if self.access_mode == "backup" and method in ("POST", "PUT", "PATCH", "DELETE"):
    raise ReadOnlyViolationError(method, url)
```

This provides **defense in depth**: even if Azure AD permissions are over-provisioned, the backup client will refuse to perform write operations.

### 5.3 Recommended Azure AD Configuration

For maximum security, register **two separate Azure AD apps** per tenant:

| App | Permissions | Purpose |
|---|---|---|
| `KavachIQ Backup` | Read-only scopes | Used by BackupEngine |
| `KavachIQ Restore` | Read-write scopes | Used by RestoreEngine |

This ensures that a compromised backup credential cannot be used to write data to the tenant, even by an attacker who bypasses the application-level guard.

> **Note:** The current data model supports a single credential set per tenant. Supporting dual app registrations per tenant is a planned enhancement (see Section 8).

---

## 6. RBAC for Tenant Operations

### 6.1 Endpoint Permissions

| Operation | API Endpoint | Required Role |
|---|---|---|
| List tenants | `GET /api/tenants/` | Any authenticated user |
| Register tenant | `POST /api/tenants/` | **ADMIN only** |
| Test connection | `POST /api/tenants/{id}/test` | ADMIN, OPERATOR |
| Run discovery | `POST /api/tenants/{id}/discover` | ADMIN, OPERATOR |
| Delete tenant | `DELETE /api/tenants/{id}` | **ADMIN only** |
| Trigger backup | `POST /api/{workload}/.../backup` | ADMIN, OPERATOR |
| Trigger restore | `POST /api/{workload}/.../restore` | **ADMIN only** |
| Mass recovery | `POST /api/jobs/mass-recovery` | **ADMIN only** |

### 6.2 Permission Rationale

- **Tenant registration** (ADMIN only): Involves handling Azure AD client secrets — the most sensitive credentials in the system. Only administrators should onboard new tenants.
- **Connection test** (ADMIN + OPERATOR): Validates credentials without modifying data. Operators need this for troubleshooting.
- **Discovery** (ADMIN + OPERATOR): Reads user/site lists from Graph API (read-only). Operators need this for operational workflows.
- **Backup** (ADMIN + OPERATOR): Uses read-only Graph access. Safe for operators to trigger.
- **Restore** (ADMIN only): Uses read-write Graph access. Writes data to the production M365 tenant — high risk, requires administrator authorization.
- **Delete tenant** (ADMIN only): Removes the tenant record and its encrypted credentials. Irreversible.

---

## 7. Audit Trail

All tenant operations are logged in the audit system:

| Event | Severity | Details Captured |
|---|---|---|
| Tenant registered | `info` | Tenant name, ms_tenant_id, registered_by user |
| Connection tested | `info` | Tenant ID, success/failure, user_count |
| Discovery completed | `info` | Tenant ID, objects found per workload |
| Backup triggered | `info` | Tenant ID, workload, object count |
| Restore triggered | `warning` | Tenant ID, restore type, target object, initiated by |
| Tenant deleted | `critical` | Tenant ID, deleted_by user |

The audit log model (`AuditLog`) captures the `user_id`, `ip_address`, `timestamp`, `action`, `resource_type`, `resource_id`, `details`, and `severity` for each event.

---

## 8. Security Hardening Recommendations

The following items should be addressed for production deployment:

| # | Recommendation | Priority | Status |
|---|---|---|---|
| 1 | **Separate Azure AD apps** for backup (read-only) and restore (read-write) per tenant | P1 | Planned |
| 2 | **Azure Key Vault integration** for storing master encryption key instead of environment variable | P0 | Not implemented |
| 3 | **Client secret rotation** workflow with zero-downtime re-encryption of stored credentials | P1 | Not implemented |
| 4 | **Certificate-based authentication** instead of client secrets for Azure AD app auth | P1 | Not implemented |
| 5 | **Tenant-scoped RBAC** — allow operators to manage specific tenants, not all | P2 | Not implemented |
| 6 | **Client secret expiry monitoring** — alert before Azure AD client secrets expire | P1 | Not implemented |
| 7 | **Network-level isolation** — restrict outbound traffic to `graph.microsoft.com` and `login.microsoftonline.com` only | P2 | Not implemented |
| 8 | **Conditional Access policies** in Azure AD to restrict token issuance to known IP ranges | P1 | Configurable in Azure AD |
| 9 | **Dual-person authorization** for restore operations (require approval from a second admin) | P2 | Not implemented |
| 10 | **Tenant credential access logging** — log every decryption of client secrets, not just API calls | P1 | Not implemented |

---

## 9. Quick Reference: Tenant Security Checklist

Use this checklist when onboarding a new tenant:

- [ ] Azure AD App Registration created with **single-tenant** account type
- [ ] Only **required Graph API permissions** granted (read-only for backup-only; read-write only if restore is needed)
- [ ] **Admin consent** granted by Azure AD Global Administrator
- [ ] Client secret generated with appropriate expiry (12 months recommended)
- [ ] Client secret rotation reminder set in calendar/ticketing system
- [ ] Tenant registered in KavachIQ by an **ADMIN** user
- [ ] Connection test passed (`POST /api/tenants/{id}/test`)
- [ ] Discovery completed — expected mailboxes, OneDrive accounts, and SharePoint sites found
- [ ] SLA policy created and assigned to discovered objects
- [ ] First backup completed successfully
- [ ] Backup data verified in the storage directory (`data/{tenant_id}/`)
- [ ] Audit log reviewed for the onboarding sequence
