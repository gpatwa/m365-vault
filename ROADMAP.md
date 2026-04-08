# KavachIQ Frontend Roadmap — Staff Engineer Design Specs

Three backend features have working APIs with no frontend UI.
Each is designed for progressive disclosure: basic users see simple controls,
power users get depth. All follow the existing Tailwind dark-mode card pattern.

---

## P0: Workload Lifecycle UI (Organization Page Enhancement)

**Why P0**: The workload lifecycle state machine is the core change — customers
opt in per workload, gated by subscription. Without UI, they can't enable/disable
workloads. The backend enforces it but the frontend doesn't expose it.

**Where**: Enhance existing `/settings` → `Organization.tsx`

**Current state**: Organization page shows "Protected Workloads" as a read-only list
based on `total_mailboxes > 0`. It has an "Available to Enable" section that just
links to `/onboard` (the old flow).

### Design: Workload Toggle Cards

Replace the passive workload list with interactive toggle cards:

```
┌─────────────────────────────────────────────────────────┐
│  ⚡ Exchange                              [PROTECTED ▼] │
│  Emails, calendars, contacts                            │
│  15 mailboxes · Last backup: 2h ago                     │
│  ──────────────────────────────────                     │
│  Lifecycle: disabled → enabled → discovered → PROTECTED │
│                                                    ●●●● │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  🔐 Entra ID                             [PROTECTED ▼] │
│  Users, groups, roles, policies                         │
│  1 directory · Last backup: 2h ago                      │
│  ──────────────────────────────────                     │
│  Lifecycle: disabled → enabled → discovered → PROTECTED │
│                                                    ●●●● │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  💾 OneDrive                               [DISABLED]   │
│  Personal files and folders                             │
│  Not enabled · Enable to start protecting               │
│                                                         │
│  [Enable Workload →]                                    │
└─────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  ⚠️  Subscription: Professional (4/5 workloads enabled)    │
│  [Upgrade to Enterprise →]                                 │
└────────────────────────────────────────────────────────────┘
```

### API Integration

```typescript
// Fetch current workload states
GET /api/tenants/{id}/workloads
→ { workloads: [{ workload, lifecycle_status, consent_status, ... }] }

// Enable a workload (subscription-gated)
POST /api/tenants/{id}/workloads
→ { workloads: ["onedrive"], consent_urls: { onedrive: "https://..." } }

// Disable a workload (→ DISABLED, keeps data)
POST /api/tenants/{id}/workloads/{workload}/disable
→ { lifecycle_status: "disabled" }

// Subscription limit check
GET /api/billing/subscription
→ { tier, workload_limit, workloads_used }
```

### Component Architecture

```
Organization.tsx
├── ConnectionStatusCard (existing — keep)
├── WorkloadLifecycleSection (NEW)
│   ├── WorkloadCard × N
│   │   ├── WorkloadIcon + Label + Description
│   │   ├── LifecycleProgressBar (4 dots: disabled→enabled→discovered→protected)
│   │   ├── StatusBadge (disabled/enabled/discovered/protected/paused)
│   │   └── ActionButton (Enable / Pause / Disable)
│   └── SubscriptionGateBanner (shows limit, upgrade CTA)
└── QuickLinks (existing — keep)
```

### Interaction Flow

1. **Enable**: Click "Enable" → POST workloads → if consent needed, redirect to
   Microsoft admin consent URL → return → workload shows "enabled"
2. **Disable**: Click dropdown "Pause" or "Disable" → confirmation modal →
   POST disable → card greys out
3. **Subscription gate**: If at limit, "Enable" button shows tooltip
   "Upgrade to Professional to enable more workloads" with link to `/billing`

### Trade-offs

| Decision | Why |
|---|---|
| Toggle cards, not a table | Cards work better on mobile, match existing dashboard pattern |
| Lifecycle progress bar (4 dots) | Visual cue shows where each workload is in the pipeline |
| Dropdown for Pause/Disable | Prevents accidental clicks on destructive actions |
| Subscription banner at bottom | Non-blocking — doesn't hide enabled workloads |

### Files to modify

- `frontend/src/pages/Organization.tsx` — Replace passive list with WorkloadCard components
- `frontend/src/components/WorkloadCard.tsx` — NEW reusable card with lifecycle indicator
- `frontend/src/api/client.ts` — Already has credential:include, no changes needed

### Estimated effort: 4-6 hours

---

## P1: Per-Tenant Alert Configuration UI

**Why P1**: Backend has `GET/PUT /api/alerts/tenant?tenant_id=N` for per-tenant
alert preferences (email recipients, event toggles, frequency). Current AlertSettings
page only shows global SMTP config (admin env vars). Customers need self-service.

**Where**: New tab/section in existing `/alerts` → `AlertSettings.tsx`, OR new
sub-route `/alerts/preferences`

### Design: Alert Preferences Panel

```
┌─────────────────────────────────────────────────────────────┐
│  Alert Preferences for [Patwa Inc]                          │
│                                                             │
│  📧 Email Recipients                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ admin@patwa.com, ops@patwa.com           [+ Add]    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  🔔 Alert Events                                            │
│  ☑ Backup Failed          ☑ Anomaly Detected                │
│  ☑ Protection Gap         ☐ Backup Completed                │
│  ☑ Secret Expiring        ☐ Restore Completed               │
│  ☑ WORM Violation         ☐ Restore Failed                  │
│                                                             │
│  ⏰ Delivery Frequency                                      │
│  ○ Immediate   ● Hourly digest   ○ Daily digest             │
│                                                             │
│  🌙 Quiet Hours (UTC)                                       │
│  From [22:00] to [06:00]                                    │
│                                                             │
│  🔗 Webhook URL (Slack/Teams/PagerDuty)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ https://hooks.slack.com/services/...                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Save Preferences]                     [Send Test Alert]   │
└─────────────────────────────────────────────────────────────┘
```

### API Integration

```typescript
// Get current config (returns defaults if none set)
GET /api/alerts/tenant?tenant_id=1
→ { configured: false, enabled_events: [...], frequency: "immediate", ... }

// Update config
PUT /api/alerts/tenant?tenant_id=1
→ { email_recipients, enabled_events, frequency, quiet_start_hour, ... }
```

### Component Architecture

```
AlertSettings.tsx (ENHANCED)
├── Tab: "System Config" (existing — global SMTP, admin only)
├── Tab: "Alert Preferences" (NEW — per-tenant, all users)
│   ├── EmailRecipientsInput (tag-style email chips)
│   ├── EventToggles (checkbox grid of alert event types)
│   ├── FrequencySelector (radio: immediate/hourly/daily)
│   ├── QuietHoursRange (time inputs)
│   ├── WebhookInput (URL input with validation)
│   └── SaveButton + TestButton
```

### Validation Rules (match backend)

```typescript
const VALID_EVENTS = [
  "backup_failed", "backup_completed", "anomaly_detected",
  "protection_gap", "secret_expiring", "worm_violation",
  "restore_completed", "restore_failed"
];
const VALID_FREQUENCIES = ["immediate", "hourly", "daily"];
```

### Trade-offs

| Decision | Why |
|---|---|
| Tabs (System / Preferences) | Separates admin config from customer preferences |
| Checkbox grid for events | Customers see all options at once, not buried in dropdowns |
| Quiet hours optional | Most customers don't need it, so default to hidden with expand |
| Optimistic save | Save button with loading state, toast on success |

### Estimated effort: 3-4 hours

---

## P2: eDiscovery UI (Enterprise Tier)

**Why P2**: Enterprise-only feature. Backend has search + legal hold APIs.
Most tenants won't need this initially. Can ship as "coming soon" badge and
build when first Enterprise customer signs up.

**Where**: New page `/ediscovery` → `eDiscovery.tsx`, add to sidebar under
Intelligence section with tier gate.

### Design: Compliance Search + Legal Hold

```
┌─────────────────────────────────────────────────────────────┐
│  eDiscovery & Legal Hold                    [Enterprise]    │
│                                                             │
│  🔍 Search Across Backups                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Search: [confidential merger documents     ] [🔍]   │    │
│  │ Workloads: [All ▼]  Date Range: [Last 90 days ▼]    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Results: 23 items across 3 workloads                       │
│  ┌─ Exchange (12) ─────────────────────────────────────┐    │
│  │  📧 Merger Update — ceo@patwa.com — Mar 15, 2026    │    │
│  │  📧 Board Meeting Notes — cfo@... — Mar 10, 2026    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  📋 Legal Holds                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Active: SEC Investigation Hold                      │    │
│  │  Custodians: 3 · Created: Jan 5, 2026               │    │
│  │  [View] [Release Hold]                               │    │
│  └─────────────────────────────────────────────────────┘    │
│  [+ Create Legal Hold]                                      │
└─────────────────────────────────────────────────────────────┘
```

### API Integration

```typescript
// Check availability
GET /api/ediscovery/status
→ { available: true/false, tier_required: "enterprise" }

// Search across backup snapshots
POST /api/ediscovery/search
→ { query, tenant_id, workload_types?, date_range? }

// Create legal hold (prevents snapshot deletion)
POST /api/ediscovery/hold
→ { tenant_id, name, custodians: ["ceo@..."], reason? }
```

### Component Architecture

```
eDiscovery.tsx (NEW)
├── TierGate (if not Enterprise, show upgrade CTA)
├── SearchPanel
│   ├── SearchInput + Filters (workload, date range)
│   └── SearchResults (grouped by workload)
├── LegalHoldSection
│   ├── ActiveHolds (list with status)
│   └── CreateHoldModal (name, custodians, reason)
```

### Sidebar Addition

```typescript
// In Layout.tsx navGroups, add to Intelligence section:
{ path: '/ediscovery', label: 'eDiscovery', icon: Search,
  roles: ['admin'], featureFlag: 'ediscovery' }
```

### Trade-offs

| Decision | Why |
|---|---|
| Tier gate (not hidden) | Enterprise prospects see value proposition + upgrade CTA |
| Search-first UX | Legal hold is secondary — most users start with search |
| Custodian email input | Simple text input, not user picker (avoid Graph dependency in UI) |
| Feature flag gated | Can ship sidebar item immediately, page behind `ediscovery` flag |

### Estimated effort: 6-8 hours

---

## Implementation Priority

| Priority | Feature | Effort | Impact | Dependency |
|---|---|---|---|---|
| **P0** | Workload Lifecycle UI | 4-6h | Critical — core onboarding UX | Backend complete |
| **P1** | Per-Tenant Alerts UI | 3-4h | High — customer self-service | Backend complete |
| **P2** | eDiscovery UI | 6-8h | Medium — Enterprise only | Backend complete |

**Total estimated: 13-18 hours of frontend work.**

---

## Deferred Items

| Feature | Reason | When |
|---|---|---|
| Full Tenant Data Export (GDPR) | Complex backend — multi-format, streaming, 10GB+ | v2.0 |
| Power Platform Workload | Enterprise tier, needs separate Graph permissions | v2.0 |
| Customer Data Portability | Regulatory requirement, not customer-blocking | v2.0 |

---

## Design Principles (Staff Engineer Lens)

1. **Server is source of truth** — UI reads lifecycle state from API, never from localStorage
2. **Progressive disclosure** — Basic users see enable/disable. Power users see lifecycle steps
3. **Subscription-aware** — Every enable action checks tier limits client-side AND server-side
4. **Optimistic UI with server confirmation** — Toggle immediately, revert on 4xx/5xx
5. **Reusable components** — WorkloadCard, EventToggle, TierGateBanner used across pages
6. **No manual steps** — Enable → Consent → Discover → Protect is a guided flow, not docs
7. **Mobile-first cards** — All new UI uses card patterns, not tables (matches existing design)
