# Configuration Drift Detection — Design Document

**Date: 2026-04-04 | Status: Roadmap (Phase 6)**

---

## Executive Summary

KavachIQ backs up security-relevant configuration from every workload on every backup run.
Configuration Drift Detection compares consecutive snapshots to flag unauthorized changes
and enable one-click rollback — something Microsoft Secure Score, Veeam, and Rubrik cannot do.

**Key insight:** Microsoft tells you your current security posture. KavachIQ tells you **what changed** and lets you **undo it**.

---

## Why This Matters

| Scenario | Microsoft's Answer | KavachIQ's Answer |
|---|---|---|
| Attacker disables MFA policy at 3am | Audit log shows who did it (after the fact) | **Alert: CA policy changed. One-click revert.** |
| Employee creates mail forward to personal email | Admin discovers weeks later in compliance review | **Alert: New forwarding rule on CEO mailbox.** |
| Rogue app granted Directory.ReadWrite.All | Visible in app registrations (if admin checks) | **Alert: OAuth scope escalation. Revert grant.** |
| Copilot agent modifies mailbox rules | No native tracking of agent-initiated changes | **Agent Shield: Agent modified config. Revert.** |

**No competitor offers this.** This is a patent-worthy feature.

---

## Architecture

### How It Works

```
Backup Run #74 (Entra ID)          Backup Run #73 (Entra ID)
  ├── 5 CA Policies                   ├── 5 CA Policies
  ├── 3 Directory Roles               ├── 3 Directory Roles
  ├── 12 App Registrations            ├── 11 App Registrations ← 1 new
  └── 169 Service Principals          └── 169 Service Principals

                    ↓ Auto-Compare ↓

Config Drift Detected:
  ⚠️ New app registration: "Data Exporter v2"
     Permissions: Mail.ReadWrite, Directory.ReadWrite.All
     Created by: unknown-service-principal
     [View Details] [Revert] [Acknowledge]
```

### Per-Workload Drift Detection

| Workload | Config Objects Monitored | Drift Signals |
|---|---|---|
| **Entra ID** | CA policies, directory roles, role assignments, app registrations, named locations, OAuth grants, service principals | Policy state change, new admin, new app, permission escalation, trusted location removed |
| **Exchange** | Mail rules, forwarding rules, mailbox delegates, auto-replies | New forward to external, new delegate, rule modification |
| **SharePoint** (future) | External sharing settings, site permissions, DLP policies | Sharing opened to anonymous, permission grant, DLP disabled |
| **OneDrive** (future) | Sharing links, external access settings | Mass external sharing enabled |
| **Teams** (future) | Guest access, channel permissions, app permissions | Guest policy changed, external chat enabled |

### Data Flow

```
1. Scheduler triggers backup (every N hours per SLA)
2. Backup worker captures workload config as SnapshotItems
3. After backup completes → Auto-drift check:
   a. Get latest completed snapshot (N)
   b. Get previous completed snapshot (N-1)
   c. Compare using existing /entra-id/compare logic
   d. For each changed item, classify as:
      - INFORMATIONAL: Expected change (e.g., user profile update)
      - WARNING: Potentially risky (e.g., new app registration)
      - CRITICAL: Security-impacting (e.g., CA policy disabled, new Global Admin)
   e. Store drift events in new `config_drift_events` table
   f. Send alert if WARNING or CRITICAL
4. UI shows timeline of drift events across all workloads
```

---

## Data Model

### New Table: `config_drift_events`

```sql
CREATE TABLE config_drift_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    workload_type VARCHAR(50) NOT NULL,       -- entra_id, exchange, sharepoint, etc.
    snapshot_before_id INTEGER REFERENCES snapshots(id),
    snapshot_after_id INTEGER REFERENCES snapshots(id),

    -- What changed
    change_type VARCHAR(50) NOT NULL,          -- added, removed, modified
    object_type VARCHAR(100) NOT NULL,         -- conditional_access_policy, mail_rule, etc.
    object_id VARCHAR(255),                    -- MS Graph object ID
    object_name VARCHAR(500),                  -- Human-readable name

    -- Details
    severity VARCHAR(20) NOT NULL DEFAULT 'info', -- info, warning, critical
    summary TEXT NOT NULL,                     -- "CA policy 'Require MFA' state: enabled → disabled"
    field_changes JSONB,                       -- [{"field": "state", "old": "enabled", "new": "disabled"}]

    -- Status
    status VARCHAR(20) DEFAULT 'open',         -- open, acknowledged, reverted, false_positive
    acknowledged_by INTEGER REFERENCES users(id),
    acknowledged_at TIMESTAMP,
    reverted_at TIMESTAMP,

    detected_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Severity Classification Rules

```python
CRITICAL_CHANGES = {
    "conditional_access_policy": ["state"],                    # Policy enabled/disabled
    "directory_role": ["_members"],                            # New Global Admin
    "role_assignment": ["*"],                                  # Any role change
    "app_registration": ["requiredResourceAccess"],           # Permission escalation
    "oauth_permission_grant": ["scope"],                      # New OAuth scope
    "named_location": ["isTrusted"],                          # Trusted location removed
}

WARNING_CHANGES = {
    "app_registration": ["*"],                                # New app registered
    "service_principal": ["accountEnabled"],                  # App enabled/disabled
    "mail_rule": ["*"],                                       # Any mail rule change
    "group": ["_members"],                                    # Group membership change
}

# Everything else = INFORMATIONAL (user profile, domain, device changes)
```

---

## API Endpoints

```
GET  /api/config-drift/timeline?tenant_id=X&days=7
     → Returns drift events across all workloads, newest first

GET  /api/config-drift/summary?tenant_id=X
     → Returns counts: { critical: 2, warning: 5, info: 12, total: 19 }

GET  /api/config-drift/event/{id}
     → Returns full event detail with field-level changes

POST /api/config-drift/event/{id}/acknowledge
     → Mark as acknowledged (false positive or expected)

POST /api/config-drift/event/{id}/revert
     → Trigger restore of the object from previous snapshot

POST /api/config-drift/scan?tenant_id=X
     → Force a manual drift scan (compares latest 2 snapshots)
```

---

## Frontend: `/config-drift` Page

### Layout

```
Configuration Drift — Patwa Inc
Monitor security-relevant changes across all workloads

[CRITICAL 0] [WARNING 2] [INFO 5]          [Scan Now] [Settings]

TODAY
  ⚠️ Exchange — New mail forwarding rule
     gopal.patwa@patwainc.com → "Forward all to external@gmail.com"
     Detected: 2h ago | Snapshot #74 → #75
     [View Rule] [Revert Rule] [Acknowledge]

  ℹ️ Entra ID — User profile updated
     emily.davis@patwainc.com — department changed: "HR" → "People Ops"
     Detected: 3h ago | Snapshot #73 → #74
     [View Diff]

YESTERDAY
  ⚠️ Entra ID — New app registration with elevated permissions
     "Data Analytics Tool" — granted Mail.ReadWrite + Files.ReadWrite.All
     Detected: 18h ago | Snapshot #72 → #73
     [View App] [Revoke Permissions] [Acknowledge]

3 DAYS AGO
  ✅ No configuration drift detected
```

### Settings Panel

```
Drift Detection Settings
  ☑ Alert on CRITICAL changes (always on)
  ☑ Alert on WARNING changes
  ☐ Alert on INFO changes

  Notification: [Email ▼] [admin@kavachiq.com]

  Workloads:
  ☑ Entra ID (CA policies, roles, apps, OAuth grants)
  ☑ Exchange (mail rules, forwarding, delegates)
  ☐ SharePoint (coming soon)
  ☐ OneDrive (coming soon)
  ☐ Teams (coming soon)
```

---

## Feature Flag & Pricing

| Tier | What's Included |
|---|---|
| Community | No drift detection |
| Professional | Drift detection for Entra ID only (INFO + WARNING) |
| Business | All workloads + CRITICAL alerts + email notifications |
| Enterprise | All + auto-revert policies + Agent Shield integration |

Feature flag: `config_drift` (Professional+)

---

## Integration with Existing Features

### Smart Engine
- Drift events feed into anomaly detection
- "3 config changes in 1 hour" → elevated anomaly score

### Agent Shield
- If drift was caused by an AI agent (detected via audit log correlation):
  - Tag event as "Agent-initiated"
  - Show agent name + action in drift timeline
  - Enable Agent Rewind for the change

### Recovery Plans
- If CRITICAL drift detected (e.g., MFA disabled):
  - Auto-update MVB recovery plan priority
  - Flag affected users as "elevated risk"

### Protection Gaps
- If drift causes a backup to fail:
  - Auto-create Protection Gap entry
  - Link to the drift event as root cause

---

## Implementation Plan

### Phase 6A: Core Drift Detection (2 weeks)

| Task | Effort | Files |
|---|---|---|
| `config_drift_events` table + model | 2 hrs | `models/config_drift.py` |
| `DriftDetectionService` — compare snapshots, classify severity | 8 hrs | `services/drift_detection.py` |
| Auto-trigger after backup completion | 4 hrs | `services/backup_engine.py` |
| API endpoints (timeline, summary, acknowledge, revert) | 6 hrs | `api/config_drift.py` |
| Frontend `/config-drift` page | 8 hrs | `pages/ConfigDrift.tsx` |
| Feature flag + pricing tier | 2 hrs | `feature_flags.py`, `usage.py` |
| **Subtotal** | **30 hrs** | |

### Phase 6B: Exchange Mail Rule Drift (1 week)

| Task | Effort |
|---|---|
| Compare mail rules between snapshots | 4 hrs |
| Classify rule changes (forward to external = WARNING) | 4 hrs |
| Revert mail rule action | 4 hrs |
| **Subtotal** | **12 hrs** |

### Phase 6C: Agent Integration + Auto-Revert (1 week)

| Task | Effort |
|---|---|
| Correlate drift with Agent Shield activity | 4 hrs |
| Auto-revert policies (Enterprise tier) | 8 hrs |
| Email/webhook notifications for drift | 4 hrs |
| **Subtotal** | **16 hrs** |

**Total: ~58 hours (3-4 weeks)**

---

## Competitive Positioning

| Feature | Microsoft | Veeam | Rubrik | KavachIQ |
|---|---|---|---|---|
| Current security state | ✅ Secure Score | ❌ | ❌ | ✅ Security Posture |
| Config change detection | ✅ Audit logs (raw) | ❌ | ❌ | ✅ **Config Drift (analyzed, classified)** |
| Before/after config comparison | ❌ | ❌ | ❌ | ✅ **Snapshot diff** |
| One-click config revert | ❌ | ❌ | ❌ | ✅ **Revert from snapshot** |
| Agent-initiated change tracking | Partial (audit logs) | ❌ | ❌ | ✅ **Agent Shield + Drift** |
| Mail rule drift detection | ❌ | ❌ | ❌ | ✅ **Exchange rule monitoring** |
| Cross-workload drift timeline | ❌ | ❌ | ❌ | ✅ **Unified timeline** |

**This is KavachIQ's moat.** No one else turns backup data into security monitoring.

---

## Success Metrics

| Metric | Target |
|---|---|
| Drift events detected per tenant per week | 5-20 (shows value) |
| Critical drift → revert time | < 5 minutes |
| CISO demo "aha moment" | "You can undo a CA policy change?" |
| Feature adoption | 60%+ of Professional tier users enable it |

---

## Sources & References

- Microsoft Secure Score: security.microsoft.com
- NIST SP 800-128: Configuration Management
- CIS M365 Benchmarks: cisecurity.org
- OWASP Configuration Verification Standard
