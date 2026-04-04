# Restore Permission Model — Design Document

**Date: 2026-04-04 | Status: Implemented (Phase 7)**

---

## Executive Summary

KavachIQ's restore operations now include enterprise-grade permission controls:
audit logging, user tracking, role-based access (RESTORE_OPERATOR), self-restore
hardening, and an approval workflow for critical restores.

The app registration model remains single-app-per-tenant for now, with a planned
migration to per-workload app separation in a future initiative.

---

## Problem Statement

| Gap | Risk | Impact |
|---|---|---|
| No audit logging on restore endpoints | Compliance failure | Can't trace who restored what |
| No `initiated_by` on RestoreJob | Accountability gap | Restore jobs are anonymous |
| Admin-only restore | Operational bottleneck | Operators who need restore must be full admins |
| Self-restore allows export/cross-user | Data exfiltration | Non-admins can PST export or cross-user restore |
| No approval workflow | Insider threat | Critical restores execute with no second-party sign-off |

---

## Solution Architecture

### 1. Audit Logging (P0)

All 5 restore endpoints now log to the `audit_logs` table:

| Endpoint | Action | Severity |
|---|---|---|
| POST /api/recovery/mass-restore | `restore.mass_recovery` | warning |
| POST /api/recovery/test-restore | `restore.test` | info |
| POST /api/exchange/mailboxes/{id}/restore | `restore.exchange` | warning |
| POST /api/entra-id/restore | `restore.entra_id` | warning |
| POST /api/self-restore/restore | `restore.self_service` | info |

Each audit entry includes: `user_id`, `action`, `resource_type`, `resource_id`, `details`, `severity`, `timestamp`.

### 2. User Tracking (P0)

RestoreJob model now includes:
- `initiated_by_user_id` (FK to users) — set on every restore job creation
- `approval_required` (0/1) — whether this job needs approval
- `approval_status` (pending/approved/rejected) — current approval state

### 3. RESTORE_OPERATOR Role (P1)

New role between OPERATOR and ADMIN:

| Role | Backup | Restore | Self-Restore | PST Export | Admin Settings |
|---|---|---|---|---|---|
| ADMIN | Yes | Yes | Yes | Yes | Yes |
| RESTORE_OPERATOR | No | Yes | Yes | Yes | No |
| OPERATOR | Yes | No | No | No | No |
| VIEWER | No | No | No | No | No |

### 4. Self-Restore Hardening (P1)

Non-admin/non-restore-operator users:
- Can only restore their own items (email match enforced)
- Limited to `ITEM_LEVEL` restore type (no cross-user, no export)
- PST export requires ADMIN or RESTORE_OPERATOR role

### 5. Approval Workflow (P2)

Critical restores require a second admin/restore_operator to approve:

**Approval required for:**
- Mass recovery (MASS_RECOVERY)
- Cross-user restore (CROSS_USER)
- Cross-tenant restore (CROSS_TENANT)
- All Entra ID config restores

**Flow:**
1. Admin requests critical restore -> RestoreJob created
2. RestoreApproval record created (pending, expires in 24h)
3. Different admin/restore_operator reviews and approves/rejects
4. Separation of duties enforced: requester != approver
5. On approval -> job dispatched for execution
6. On rejection -> job marked FAILED with reason
7. On expiry (24h) -> auto-expired

**API Endpoints:**
- `GET /api/restore-approvals/pending` — list pending (excludes own requests)
- `POST /api/restore-approvals/{job_id}/approve` — approve (enforces requester != approver)
- `POST /api/restore-approvals/{job_id}/reject` — reject with reason
- `GET /api/restore-approvals/count` — pending count (for UI badge)

---

## Competitive Positioning

| Capability | Rubrik | Veeam | Druva | **KavachIQ** |
|---|---|---|---|---|
| Audit trail on restore | Yes | Yes | Yes | **Yes** |
| User tracking per job | Yes | Yes | Yes | **Yes** |
| Restore Operator role | Custom roles | Dedicated role | Role hierarchy | **RESTORE_OPERATOR** |
| Self-restore hardening | In-place only | Web portal | User/admin/web | **In-place only for non-admins** |
| Approval workflow | Quorum Auth (N-of-M) | None | None | **Requester != Approver** |
| PST export restriction | N/A | N/A | N/A | **Admin/Restore Operator only** |

---

## Microsoft Alignment

Our architecture aligns with Microsoft's recommendations:

| Microsoft Recommendation | KavachIQ Status |
|---|---|
| Single app per purpose | Single app (per-workload separation planned) |
| Least privilege (Read vs ReadWrite) | GraphClient enforces backup=read-only, restore=read-write |
| Audit all data access | All restore endpoints now audited |
| Certificate auth over secrets | Roadmap (currently client secrets) |
| Application Access Policies | Roadmap (mailbox-level scoping) |
| Sites.Selected for SharePoint | Roadmap (when SharePoint workload activates) |

---

## Future: Per-Workload App Separation

**Separate initiative** — not part of this implementation.

When implemented, each workload gets its own Entra app registration:
- Customers consent only to workloads they use
- Workload can be revoked without affecting others
- Aligns with Rubrik's per-workload enterprise app pattern

---

## Data Model

### RestoreJob (updated)
```sql
ALTER TABLE restore_jobs ADD COLUMN initiated_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE restore_jobs ADD COLUMN approval_required INTEGER DEFAULT 0;
ALTER TABLE restore_jobs ADD COLUMN approval_status VARCHAR(20);
```

### RestoreApproval (new)
```sql
CREATE TABLE restore_approvals (
    id SERIAL PRIMARY KEY,
    restore_job_id INTEGER NOT NULL REFERENCES restore_jobs(id),
    requested_by_user_id INTEGER NOT NULL REFERENCES users(id),
    approved_by_user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    reason TEXT,
    requested_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

### UserRole (updated)
```sql
ALTER TYPE userrole ADD VALUE 'restore_operator';
```

---

## Files Modified

| File | Change |
|---|---|
| `backend/migrations/003_restore_permissions.sql` | New migration |
| `backend/app/models/restore_job.py` | Added 3 fields |
| `backend/app/models/user.py` | Added RESTORE_OPERATOR enum |
| `backend/app/models/restore_approval.py` | New model |
| `backend/app/services/auth.py` | Updated require_restore_permission |
| `backend/app/api/recovery.py` | Audit logging + initiated_by on 2 endpoints |
| `backend/app/api/exchange.py` | Audit logging + initiated_by + PST restriction |
| `backend/app/api/entra_id.py` | Audit logging + initiated_by |
| `backend/app/api/self_restore.py` | Audit + initiated_by + hardening + fixed broken fields |
| `backend/app/api/restore_approval.py` | New approval workflow API |
| `backend/app/main.py` | Registered restore_approval router |
