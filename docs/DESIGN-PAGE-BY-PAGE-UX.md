# KavachIQ — Page-by-Page UX Redesign

## Author
Principal Product Manager | April 2026

## Design Principle

> **Every metric earns its place by answering a persona's question.**
> If the IT admin doesn't ask it daily, the CISO doesn't need it quarterly,
> and the auditor doesn't request it annually — it doesn't belong on that page.

**Three personas, three cadences:**
- **IT Admin** — daily, < 30 seconds, "anything broken?"
- **CISO** — monthly/quarterly, "are we protected against threats?"
- **Compliance** — quarterly/annual, "can I prove adherence?"

---

## 1. DASHBOARD

**10-second question:** "Do I need to act on anything right now?"

### Current State (Issues)
- Shows 4 hero cards: Protection, Health Score, Backups (24h), Action Items ✅ Good
- Shows anomaly banner "10 active anomalies" — creates anxiety without actionable path
- License card shows "Workloads: 5" — license limit, not active count
- Microsoft 365 tenant card is good — shows per-workload status at a glance

### Redesign

**Keep as-is (working well):**
- Protection card (25/25 objects, 100%)
- Health Score card (80, Healthy)
- Microsoft 365 tenant card with Entra ID + Exchange sub-cards
- 7-Day Backup Trend chart

**Change:**
| Current | Change To | Why |
|---------|-----------|-----|
| Backups (24h): "13" with subtitle | "All backups succeeded today ✅" or "2 failures need attention ⚠️" | Binary is faster than counting |
| Action Items: "0, All clear" | Remove when 0 — empty card wastes space | Nothing to act on = nothing to show |
| "10 active anomalies" banner | Show only if anomaly is NEW (not stale). Or hide behind Intelligence section | Stale anomalies create alert fatigue |
| License card "Workloads: 5" | "2 active workloads" (match enabled, not license limit) | Already fixed via scoping |
| Compliance section at bottom | Move up — CISO persona scans for this | SLA Adherence 100% is a key proof point |

**Remove:**
- Storage "0 GB Backup Size" — meaningless to customer when near-zero. Show only when > 1 GB
- Snapshots count "131" — internal metric, not customer value
- "Included Workloads" tag list — already shown in sidebar

**Add:**
- Recovery Confidence score next to Health Score (answers "can I recover?" without navigating)

---

## 2. JOBS

**10-second question:** "Did today's backups succeed?"

### Current State (Issues)
- Shows "100 Total Jobs, 11 Completed, 11% success rate" — misleading
- Shows dead-lettered jobs in main view — internal system state
- Success rate includes all-time jobs — no competitor does this
- Per-workload breakdown shows "Exchange: 47 jobs, 4% success" — alarming

### Redesign (from previous research)

**Success path (5-second glance):**
```
✅ All backups succeeded today
25/25 objects protected • Last backup: just now
Recovery Confidence: 65/100
```

**Failure path (actionable in 10 seconds):**
```
⚠️ 2 items failed in Exchange
sarah@patwa.com → Permission denied → [Fix Guide]
alex@patwa.com  → Throttled → Will retry automatically
```

**Remove from customer view:**
- Dead-letter status/count
- All-time total job count
- All-time success rate percentage
- Individual rows for successful jobs
- Duration/timing details
- Worker/queue metrics

**Keep behind "Show details ▾":**
- Job table with filtering (for admins who want to drill down)
- Date range selector
- Export to CSV

---

## 3. RECOVERY

**10-second question:** "Can I recover right now, and how fast?"

### Current State (Good)
- Recovery Confidence: 65/100 with 4-factor breakdown ✅
- RPO/RTO Compliance per workload ✅
- Recommendations with action buttons ✅
- Tabs: Overview / Runbooks / Test Restore ✅

### Changes (minor)

**Keep as-is (strong page):**
- Recovery Confidence donut + factor bars
- RPO compliance per workload
- Recommendations section

**Change:**
| Current | Change To | Why |
|---------|-----------|-----|
| "Restore Success: 43.8%" | Show only if restores have been attempted. If 0 attempts, show "No restores tested yet → Run Test Restore" | 43.8% from 0/1 is misleading |
| "Validation: 15.3%" | "Validating... 15% complete (auto-running)" | Show it's in progress, not a failing grade |

**Remove:**
- Nothing — this is the strongest page. It answers the CISO's question directly.

**Add:**
- "Last recovery test: never" with prominent CTA if no test restore has been run
- Estimated recovery time for full tenant restore

---

## 4. WORKLOAD DETAIL (Entra ID, Exchange)

**10-second question:** "Is this workload fully protected? What's stale?"

### Current State (Good for enabled workloads)
- Exchange: 6/6 protected, 48 items, Last backup just now ✅
- Entra ID: 1/1 protected, 1926 items ✅
- Table with per-object status, criticality, items, size ✅

### Changes

**Keep as-is:**
- Hero cards (Protected, Last Backup, Total Items, Success Rate)
- Object table with status column

**Change:**
| Current | Change To | Why |
|---------|-----------|-----|
| "Backup All" button always visible | Show only when objects are unprotected or backup is stale | Don't encourage unnecessary manual backups |
| Success Rate "100%" as hero card | Replace with "SLA Status: On Track ✅" | Success rate is a Jobs metric, not a workload metric. SLA adherence is what the admin cares about |

**Remove:**
- Size column (840 B, 852 B) — too granular, not actionable per-object
- Criticality column for prospects — useful for enterprise only (show after 50+ objects)

**For non-enabled workloads (SharePoint, OneDrive, Teams):**
- Do NOT show full pages with data
- Show: "SharePoint is available. Enable it to start protecting your sites → [Enable in Organization]"

---

## 5. REPORTS

**10-second question:** "Can I prove compliance to an auditor?"

### Current State
- Backup Performance, Storage Analytics, SLA Compliance tabs ✅
- Data present but not exportable as PDF

### Redesign

**Keep:**
- SLA Compliance report (100% adherence)
- Backup Performance trend

**Change:**
| Current | Change To | Why |
|---------|-----------|-----|
| Storage Analytics with dedup/compression ratios | Remove or move to Admin section | Customers don't act on compression ratios |
| No export to PDF | Add "Download PDF" for each report | Auditors need evidence as files |
| No scheduled delivery | Add "Email this report monthly" | Compliance officers need recurring evidence |

**Add — persona-specific reports:**
- **IT Admin**: Daily backup summary (auto-emailed, 1 paragraph)
- **CISO**: Monthly security posture (anomalies, encryption status, recovery readiness)
- **Compliance**: Quarterly SLA adherence + retention proof + recovery test log

---

## 6. SMART ENGINE / INTELLIGENCE

**10-second question:** "Am I under attack? What changed abnormally?"

### Current State
- Health score with component breakdown ✅
- Anomaly list with z-scores and severity ✅
- Baselines view ✅

### Changes

**Keep:**
- Health score donut with components
- Anomaly list with severity

**Change:**
| Current | Change To | Why |
|---------|-----------|-----|
| Z-score numbers (7.2, 24.5) | Remove raw z-scores | Customers don't understand z-scores. Show "Unusual: 3x normal size" instead |
| "Active anomalies: 10" | "2 anomalies this week" (time-scoped, deduplicated) | 10 stale anomalies = alert fatigue |
| Baselines tab with raw avg/stddev | Remove from customer view | Internal ML data. Keep for admin/debug only |

**Remove:**
- Raw baseline values (avg_value, std_dev, min, max, sample_count)
- Z-score numbers

**Add:**
- "Data change timeline" — visual of when unusual activity happened
- "Recommended action" per anomaly (not just "Investigate")

---

## 7. ORGANIZATION / SETTINGS

**10-second question:** "Is my policy correct? Is my platform connected?"

### Current State (Broken)
- Shows "Not Connected" for a connected tenant ❌
- Shows "0/6 workloads configured" ❌
- "Get Started" button for an active tenant ❌

### Redesign (from Phase 2 of previous plan)

**Replace with:**
```
Patwa Inc                                    ✅ Connected
Microsoft 365 • 2 workloads active

ACTIVE WORKLOADS
┌──────────┐  ┌──────────┐
│ Entra ID │  │ Exchange │
│ Protected│  │ Protected│
│ 1 object │  │ 6 objects│
└──────────┘  └──────────┘

AVAILABLE WORKLOADS (click to enable)
┌───────────┐ ┌──────────┐ ┌────────┐
│ SharePoint│ │ OneDrive │ │ Teams  │
│ Available │ │ Available│ │Available│
│ [Enable →]│ │ [Enable→]│ │[Enable→│
└───────────┘ └──────────┘ └────────┘
```

**Remove:**
- "Connect Microsoft 365" button (already connected)
- "Get Started" button (already past onboarding)
- "No workloads configured" empty state (workloads ARE configured)

---

## 8. PROTECTION GAPS / FAILED ITEMS

**10-second question:** "What's not protected and why?"

### Current State
- Shows failed items with error categories ✅
- Resolution guidance exists in the model ✅

### Changes

**Keep:**
- Failed item list with error category
- Resolution guidance per error type

**Change:**
| Current | Change To | Why |
|---------|-----------|-----|
| Technical error messages | Human-readable: "Microsoft blocked access to sarah's mailbox. Re-grant permission in Azure AD → [Fix Guide]" | Actionable, not technical |
| Flat list of all failures | Group by error category, most impactful first | Permission issues (fixable) before throttling (auto-resolves) |

**Remove:**
- Raw error codes (E5001, etc.)
- Snapshot IDs, job IDs in the customer view

---

## Summary: What Changes Per Page

| Page | Remove | Change | Keep | Add |
|------|--------|--------|------|-----|
| **Dashboard** | Empty Action Items card, Snapshots count, Storage < 1GB, Workload tag list | Backups card → binary pass/fail, anomaly banner → only new | Protection, Health, Tenant card, Trend chart | Recovery Confidence |
| **Jobs** | Dead-letter, all-time rate, raw counts, successful job rows | → "All succeeded today" or failure drill-down | Per-workload summary, Export | Inline resolution guidance |
| **Recovery** | Nothing | Restore Success → conditional, Validation → show progress | Confidence score, RPO/RTO, Recommendations | Last test date, Est. recovery time |
| **Workloads** | Size column, Success Rate hero | SLA Status replaces Success Rate, Backup All conditional | Object table, Hero cards | "Enable" page for non-active workloads |
| **Reports** | Storage compression ratios | Add PDF export, email scheduling | SLA Compliance, Backup Performance | CISO monthly report, Compliance quarterly |
| **Smart Engine** | Z-scores, raw baselines, stale anomalies | Human-readable anomaly descriptions | Health score, Anomaly list | Change timeline, Action per anomaly |
| **Organization** | "Not Connected", "0 configured", "Get Started" | Show actual status + active/available workloads | Billing, SLA Policies links | Available workload cards with Enable |
| **Failed Items** | Raw error codes, job/snapshot IDs | Human-readable messages, grouped by category | Error list, resolution guidance | Impact priority ordering |

---

## Implementation Priority

| Priority | Page | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Organization (broken — says "Not Connected") | 3-4h | Eliminates confusion |
| **P0** | Sidebar (shows non-enabled workloads) | 2-3h | Eliminates confusion |
| **P1** | Jobs (misleading success rate) | 3-4h | Prevents customer alarm |
| **P1** | Non-enabled workloads (show "Available" instead of data) | 2-3h | Prevents "why is this backing up?" |
| **P2** | Smart Engine (hide z-scores, human-readable) | 2h | Cleaner intelligence view |
| **P2** | Dashboard (minor polish — Recovery Confidence, binary backups) | 2h | Better at-a-glance |
| **P2** | Reports (PDF export, email scheduling) | 4-6h | Compliance requirement |
| **P3** | Failed Items (human-readable errors) | 2h | Better failure UX |
| **P3** | Workload detail (SLA Status, conditional Backup All) | 2h | Minor polish |

**Total: ~3-4 days for P0+P1, ~2 weeks for all priorities**
