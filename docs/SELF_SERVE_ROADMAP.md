# Shieldio Self-Serve Roadmap — Path to First 20 Paying Customers

**Date: 2026-04-03 | Status: Planning**

---

## Current State

Shieldio is **~70% feature-complete** as a product but **0% ready for self-serve revenue**.
The core backup/restore engine works well. What's missing is the commercial layer
(payments, email, auth flows) and several Exchange/Entra ID features that competitors offer.

---

## Phase 1: Revenue Infrastructure (Weeks 1-3) — CRITICAL BLOCKER

**Goal:** Accept first payment. Without this, no revenue is possible.

### 1.1 SendGrid Email Service (Week 1, 16 hrs)
**Why:** Unlocks password reset, email verification, alerts — everything needs email.

| Deliverable | Details |
|---|---|
| SendGrid integration | Replace SMTP with SendGrid API (free tier: 100 emails/day) |
| Email templates | Welcome, password reset, trial reminder, backup failure, invoice |
| Backend service | `backend/app/services/email.py` — send_welcome, send_reset, send_alert |
| Template rendering | Jinja2 templates with Shieldio branding |

### 1.2 Password Reset + Email Verification (Week 1, 16 hrs)
**Why:** Users WILL forget passwords. Can't trust unverified emails.

| Deliverable | Details |
|---|---|
| Forgot password flow | `POST /auth/forgot-password` → SendGrid email → `POST /auth/reset-password?token=` |
| Email verification | Registration → verification email → `GET /auth/verify?token=` → activated |
| Token model | `password_reset_token`, `email_verification_token` on User model |
| Frontend | Wire "Forgot password?" button, verification landing page |

### 1.3 Stripe Billing (Weeks 2-3, 40 hrs)
**Why:** Can't collect revenue without payment processing.

| Deliverable | Details |
|---|---|
| Stripe Checkout | `POST /api/billing/checkout` → redirect to Stripe hosted checkout |
| Webhook handler | `POST /api/billing/webhook` — handle payment success, failure, subscription changes |
| Customer Portal | `POST /api/billing/portal` → Stripe self-serve management |
| Subscription model | Add `stripe_customer_id`, `subscription_status`, `trial_ends_at` to Tenant |
| Billing page | `frontend/src/pages/Billing.tsx` — plan display, manage button, invoice history |
| Pricing CTAs | Wire Landing.tsx "Start Trial" → Stripe Checkout |
| Trial flow | 14-day free trial → auto-charge or downgrade to Community |
| Stripe Tax | Auto-calculate US sales tax per state (0.5% add-on) |

### 1.4 License Enforcement (Week 3, 12 hrs)
**Why:** Community users can exceed 25-object limit.

| Deliverable | Details |
|---|---|
| License middleware | `check_license(tenant_id)` — returns tier + remaining quota |
| Hard blocks | Block protected object creation at Community limit |
| Subscription check | Before backup: verify subscription active (not expired/past_due) |
| Upgrade prompts | Show "Upgrade to continue" when limit hit |
| Auto-downgrade | If trial expires without payment → Community tier |

---

## Phase 2: Exchange Feature Gaps (Weeks 4-6)

**Goal:** Match competitor feature parity for Exchange Online.

### What Competitors Have That We Don't

| Feature | Veeam | Rubrik | Druva | Shieldio | Priority |
|---|---|---|---|---|---|
| Shared mailboxes | Yes | Yes | Yes | **Missing** | **P1** |
| Archive mailboxes | Yes | Yes | Yes | **Missing** | **P1** |
| Mail rules / inbox rules | Yes | Yes | Yes | **Missing** | **P1** |
| PST export | Yes | Yes | Yes | **Missing** | **P1** |
| Public folders | Yes | Partial | Yes | **Missing** | P2 |
| Tasks | Yes | Partial | Yes | **Missing** | P2 |
| Journal items | Yes | Partial | No | **Missing** | P3 |
| Folder structure on restore | Yes | Yes | Yes | **Broken** | **P1** |
| Attachment restore | Yes | Yes | Yes | **Broken** | **P1** |

### 2.1 Shared Mailbox Support (Week 4, 16 hrs)
```
Discovery: GET /users?$filter=recipientType eq 'SharedMailbox'
Backup: Same as regular mailbox (messages, calendar, contacts)
Restore: Same restore flow, different target
```

### 2.2 Archive Mailbox Support (Week 4, 8 hrs)
```
Discovery: GET /users/{id}/mailFolders?includeHiddenFolders=true → filter for archive
Backup: Delta sync on archive folder tree
```

### 2.3 Mail Rules Backup (Week 5, 8 hrs)
```
Backup: GET /users/{id}/mailFolders/inbox/messageRules
Restore: POST /users/{id}/mailFolders/inbox/messageRules
```

### 2.4 PST Export (Week 5, 16 hrs)
```
Export: Convert snapshot items to PST format using libpst/pypff
Download: Generate signed URL for PST file from storage
UI: "Export as PST" button on mailbox snapshot page
```

### 2.5 Fix Restore Quality (Week 6, 12 hrs)
- Preserve folder structure on restore (create folders first, then messages)
- Restore attachments with messages (currently only body restored)
- Restore calendar event attendees and recurrence

---

## Phase 3: Entra ID Feature Gaps (Weeks 7-8)

**Goal:** Close the identity protection gap vs Druva and Rubrik.

### What Competitors Have That We Don't

| Feature | Rubrik | Druva | Shieldio | Priority |
|---|---|---|---|---|
| Group membership restore | Yes | Yes | **Missing** — groups restored empty | **P1** |
| PIM assignments | Yes | Partial | **Missing** | P2 |
| Authentication methods | Partial | No | **Missing** | P2 |
| Snapshot diff (full) | Yes | Yes | **Partial** — hash-based only | P2 |
| Relationship restore | Yes | Yes | **Missing** | **P1** |

### 3.1 Group Membership Restore (Week 7, 12 hrs)
```
Current: Group recreated but members NOT re-added
Fix: After creating group, POST /groups/{id}/members/$ref for each member
Challenge: Members must exist — restore order matters (users before groups)
```

### 3.2 PIM Assignment Backup (Week 7, 8 hrs)
```
Backup: GET /roleManagement/directory/roleEligibilitySchedules
        GET /roleManagement/directory/roleAssignmentSchedules
Store: As SnapshotItems with item_type='pim_eligibility' / 'pim_assignment'
```

### 3.3 Full Snapshot Diff (Week 8, 12 hrs)
```
Current: Hash-based added/removed/changed detection
Enhance: Deep diff showing specific field changes (e.g., "MFA requirement added to CA policy X")
UI: Side-by-side comparison view for CA policies, groups, app registrations
```

---

## Phase 4: Product Polish (Weeks 9-10)

### 4.1 Deployment Health Gate (Week 9, 12 hrs)
```
Pre-deploy: Check current system healthy
Post-deploy: Verify backend + DB + demo login work
Auto-rollback: If checks fail, revert to previous revision
Makefile: `make deploy` = build → push → health check → apply → verify
```

### 4.2 Graph API Re-auth Flow (Week 9, 12 hrs)
```
Problem: Token expires → backups fail silently
Fix: 401 handler → "Tenant needs re-authentication" banner in UI
     POST /api/tenants/{id}/reauth → redirect to OAuth consent
     Resume stalled backups after re-auth
```

### 4.3 Analytics Integration (Week 10, 8 hrs)
```
PostHog: Product analytics (autocapture + custom events)
Plausible: Landing page analytics (cookieless)
Clarity: Heatmaps + session replay (free)
Search Console: SEO basics
```

### 4.4 Admin Alerting (Week 10, 8 hrs)
```
Auto-email: backup failure, SLA violation, storage quota
PagerDuty/OpsGenie: Critical alerts (optional)
Status page: /status showing real-time system health
```

---

## Phase 5: GDPR + Account Management (Week 11)

### 5.1 Data Export (8 hrs)
```
Endpoint: POST /api/auth/export-my-data → ZIP with all user data
Contents: Profile, tenants, backup metadata, audit logs
Format: JSON + CSV
```

### 5.2 Account Deletion (8 hrs)
```
Endpoint: DELETE /api/auth/account → confirmation email → DELETE after 7-day grace
Cascade: Delete all tenants, protected objects, snapshots, audit logs
Soft delete: 7-day recovery window before permanent purge
```

---

## Summary Timeline

| Week | Phase | Deliverables | Revenue Impact |
|---|---|---|---|
| 1 | Email + Auth | SendGrid, password reset, email verification | Unlocks all comms |
| 2-3 | Stripe | Checkout, webhooks, portal, trial, billing page | **Enables revenue** |
| 3 | License | Hard enforcement, auto-downgrade, upgrade prompts | Conversion funnel |
| 4-6 | Exchange | Shared/archive mailbox, mail rules, PST, folder restore | Feature parity |
| 7-8 | Entra ID | Group membership restore, PIM, full diff | Identity gap closed |
| 9-10 | Polish | Health gate, re-auth, analytics, alerting | Operational readiness |
| 11 | Compliance | Data export, account deletion | GDPR ready |

**Total: ~11 weeks, 1 developer**
**First paying customer possible: Week 3** (after Stripe integration)

---

## Exchange Feature Comparison (Updated)

| Feature | Shieldio (Current) | After Phase 2 | Veeam | Rubrik | Druva |
|---|---|---|---|---|---|
| Email backup + restore | Yes | Yes | Yes | Yes | Yes |
| Calendar backup + restore | Yes | Yes | Yes | Yes | Yes |
| Contacts backup + restore | Yes | Yes | Yes | Yes | Yes |
| Shared mailboxes | No | **Yes** | Yes | Yes | Yes |
| Archive mailboxes | No | **Yes** | Yes | Yes | Yes |
| Mail rules | No | **Yes** | Yes | Yes | Yes |
| PST export | No | **Yes** | Yes | Yes | Yes |
| Public folders | No | Phase 3 | Yes | Partial | Yes |
| Tasks/Journal | No | Phase 3 | Yes | Partial | No |
| Cross-user restore | Yes | Yes | Yes | Yes | Yes |
| Search across snapshots | Yes | Yes | Yes | Yes | Yes |
| Point-in-time browse | Yes | Yes | Yes | Yes | Yes |
| Identity-first recovery | **Yes** | **Yes** | No | No | No |
| Criticality scoring | **Yes** | **Yes** | No | No | No |
| Agent Shield | **Yes** | **Yes** | Yes (expensive) | Yes (expensive) | No |
| Self-hosted option | **Yes** | **Yes** | No | No | No |
| Price | **$1.50** | **$1.50** | $3-5 | $6-10 | $4-8 |

---

## Entra ID Feature Comparison (Updated)

| Object Type | Shieldio (Current) | After Phase 3 | Veeam | Rubrik | Druva |
|---|---|---|---|---|---|
| Users | Backup | Backup | Backup+Restore | Backup+Restore | Backup+Restore |
| Groups | Backup (no members) | **Backup+Restore+Members** | Full | Full | Full |
| Directory Roles | Backup | Backup | Backup | Full | Backup |
| Role Assignments | Backup | Backup | Full | Full | Full |
| Conditional Access | **Backup+Restore** | **Backup+Restore** | Backup+Restore | Full | **Backup+Restore** |
| App Registrations | Backup+Restore | Backup+Restore | Full | Full | Full |
| Named Locations | **Backup+Restore** | **Backup+Restore** | Partial | Partial | Partial |
| Service Principals | Backup | Backup | Full | Full | Full |
| Administrative Units | **Backup** | **Backup** | No | No | **Backup** |
| OAuth Grants | **Backup** | **Backup** | Partial | Partial | Partial |
| Devices | Backup | Backup | Partial | Partial | Partial |
| Domains | **Backup** | **Backup** | No | No | No |
| PIM Assignments | No | **Backup** | Yes | Yes | Partial |
| Auth Methods | No | Phase 4 | Partial | Partial | No |
| Snapshot Diff | Partial | **Full** | Full | Full | Full |

**Shieldio wins on:** Named Locations, Administrative Units, Domains, OAuth Grants, self-hosted, pricing
**Competitors win on:** PIM, Auth Methods, relationship restore, full lifecycle management

---

## Sources

- [Veeam M365 + Entra ID Backup](https://www.veeam.com/products/saas/microsoft-office-365-entra-id-backup-service.html)
- [Veeam Entra ID Recovery](https://www.veeam.com/products/saas/microsoft-entra-id-backup-software.html)
- [Rubrik M365 Backup Storage](https://docs.rubrik.com/en-us/saas/m365_backup_storage/m365_backup_storage.html)
- [Druva Entra ID Conditional Access](https://www.druva.com/blog/entra-id-conditional-access-administrative-units)
- [Druva Entra ID Data Protected](https://help.druva.com/en/articles/9471194-microsoft-entra-id-data-that-druva-protects)
- [Best M365 Backup Solutions 2026](https://expertinsights.com/backup-and-recovery/the-top-backup-and-recovery-solutions-for-microsoft-office-365)
- [SaaS Security Checklist 2026](https://peiko.space/blog/article/saas-security-checklist-before-launch)
- [B2B SaaS Launch Checklist](https://aventigroup.com/blog/b2b-saas-product-launch-checklist-no-fail-framework/)
