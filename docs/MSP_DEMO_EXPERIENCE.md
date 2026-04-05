# KavachIQ — MSP Interactive Demo Experience

**Date: 2026-03-30 | Status: Design + Implementation**

---

## 1. Overview

An in-product interactive demo at `/msp/demo` that walks through the **complete MSP lifecycle** in 8 scenes. Designed for two audiences:

- **MSP partners** evaluating whether to resell KavachIQ
- **Investors** seeing the full product capability

The demo uses pre-seeded data (no real M365 tenants needed) and guides the user through onboarding clients, managing multi-tenant operations, responding to incidents, billing, and offboarding — all from one console.

---

## 2. Demo Flow: 8 Scenes

```
Scene 1: MSP Console Overview
    ↓
Scene 2: Onboard New Clients (Bulk)
    ↓
Scene 3: Configure Your Brand (White-Label)
    ↓
Scene 4: Monitor Client Health (Drill-Down)
    ↓
Scene 5: Respond to an Incident (Attack Simulation)
    ↓
Scene 6: Prove Compliance (HIPAA/SOC2/GDPR Reports)
    ↓
Scene 7: Bill Your Clients (Wholesale Pricing)
    ↓
Scene 8: Offboard + Summary (Complete Lifecycle)
```

---

## 3. Scene Details

### Scene 1: "Welcome to the MSP Console"

**What the user sees:**
- MSP Dashboard with 3 pre-seeded demo tenants
- Animated count-up: tenants, protected users, health score
- Each tenant card shows health badge, protection %, workloads, alerts

**Narrative:** "This is your single pane of glass. Every client tenant, health score, and alert — in one view."

**Engagement gate:** Auto-engages after 3 seconds (user absorbs the data)

---

### Scene 2: "Onboard a New Client in 60 Seconds"

**What the user sees:**
- Pre-filled bulk onboard table with 2 new tenants
- User clicks "Onboard All"
- Animated per-row progress: encrypting → creating → done
- New tenants appear on the MSP Dashboard

**Narrative:** "Upload a CSV or enter credentials manually. Secrets are encrypted with AES-256-GCM before storage. Each tenant gets isolated encryption keys."

**Engagement gate:** User clicks "Onboard All" and sees success

---

### Scene 3: "Your Brand, Your Platform"

**What the user sees:**
- MSP Branding admin page
- Pre-filled with "Acme Cyber Solutions" and custom blue color
- Live sidebar preview updates as they type
- Save button applies branding across the platform

**Narrative:** "Your clients see YOUR brand — not ours. Custom logo, company name, and colors. Every report, every page."

**Engagement gate:** User saves branding (or clicks Next)

---

### Scene 4: "Monitor Every Client from One Console"

**What the user sees:**
- MSP Dashboard with tenant cards
- User clicks "Acme Healthcare" tenant
- Dashboard filters to show that tenant's data
- 5 workloads, protection %, health score, backup activity

**Narrative:** "Click any tenant to drill down. See protection status per workload — including Entra ID, which no competitor backs up."

**Engagement gate:** User clicks a tenant card

---

### Scene 5: "When Ransomware Hits Your Client"

**What the user sees:**
- 4-phase interactive recovery simulation (reuses CyberRecoverySimulation)
- Phase 1: Backup overview with animated metrics
- Phase 2: Anomaly detected — 1,847 files renamed to .encrypted
- Phase 3: Confidence score reveals (0-100 with breakdown)
- Phase 4: One-click recovery plan generated from real backup data

**Narrative:** "KavachIQ detects the attack WHILE backups run. The recovery plan is already built — identity controls first, then critical users, then everyone else. Your client is back online before their morning coffee."

**Engagement gate:** User completes all 4 phases

---

### Scene 6: "Audit-Ready in One Click"

**What the user sees:**
- Compliance report modal opens for the selected tenant
- HIPAA tab: 6 safeguards mapped with green checkmarks
- SOC 2 tab: 6 criteria mapped
- GDPR tab: 6 articles mapped
- Print/PDF button

**Narrative:** "Generate compliance evidence for every client, for every audit. HIPAA, SOC 2, GDPR, DORA — covered. One click. No consultant needed."

**Engagement gate:** User views at least 2 report types

---

### Scene 7: "Your Margin, Your Business"

**What the user sees:**
- Billing portal with per-tenant breakdown
- Wholesale tier pricing highlighted: $1.50/user (you) vs $6/user (client)
- Margin calculation: "$450/mo cost → $1,500/mo revenue → 70% margin"
- CSV export button

**Narrative:** "You pay $1.50/user. You sell at $5-8/user. Your margin: 70-85%. With 15 clients, that's $10K+/month in recurring revenue from one platform."

**Engagement gate:** Auto-engages after 3 seconds

---

### Scene 8: "The Complete MSP Lifecycle"

**What the user sees:**
- Tenant deactivation flow: "Offboard Pacific Finance"
- Confirmation dialog with data retention notice
- After offboard: tenant status → INACTIVE, backups retained per SLA
- Summary dashboard:
  - Tenants managed: 5
  - Users protected: 125+
  - Compliance reports: 4 frameworks
  - Incidents resolved: 1
  - Monthly revenue: $937.50
- CTA: "Start Your MSP Pilot — 3 Months Free"

**Narrative:** "You just onboarded, protected, monitored, recovered, reported, billed, and offboarded — all from one console. This is KavachIQ for MSPs."

**Engagement gate:** None (final scene)

---

## 4. Demo Data Seed

`POST /api/msp/demo-seed` creates:

| Tenant | Segment | Users | Workloads | Health | SLA |
|--------|---------|-------|-----------|--------|-----|
| **Acme Healthcare** | HIPAA | 50 | Exchange, OneDrive, SharePoint, Teams, Entra ID | 95 | Gold (4h/365d) |
| **Summit Legal Group** | Legal | 30 | Exchange, OneDrive, SharePoint, Entra ID | 85 | Gold (4h/365d) |
| **Pacific Finance** | SOC 2 | 45 | Exchange, OneDrive, SharePoint, Teams, Entra ID | 100 | Silver (12h/90d) |

Each tenant gets: SLA policy, protected objects with `last_backup_at`, completed backup jobs, snapshot records.

The seed is **idempotent** — re-running it skips existing demo tenants.

---

## 5. Offboard Flow

`POST /api/msp/offboard/{tenant_id}`:
1. Sets tenant status to `INACTIVE`
2. Preserves all backup data (respects SLA retention)
3. Returns retention info and deactivation timestamp
4. Tenant disappears from active tenant list but data is retained

---

## 6. Technical Implementation

### Entry Point
- URL: `/msp/demo`
- Component: `MSPDemo.tsx`
- Requires: admin or msp_admin role

### Scene Architecture
- 8 scenes rendered by a single `MSPDemo` component
- Step state managed with `useState(0)` (0-7)
- Progress bar at top with scene labels
- Each scene is a render function returning JSX
- Engagement gates: boolean state per scene that unlocks "Next"
- Reuses existing components: MSPDashboard, BulkOnboard, MSPBranding, BillingPortal, ComplianceReport, CyberRecoverySimulation

### API Endpoints
- `POST /api/msp/demo-seed` — seed demo tenants (idempotent)
- `POST /api/msp/offboard/{tenant_id}` — deactivate tenant

### Demo Account
- Login as `admin` / `Admin123` → navigate to `/msp/demo`
- Or direct URL: `https://app.kavachiq.com/msp/demo`

---

## 7. Demo Script (10 minutes)

| Time | Scene | Talking Point |
|------|-------|---------------|
| 0:00 | Scene 1 | "This is your MSP console. 5 clients, 125 users, all in one view." |
| 1:00 | Scene 2 | "Onboard 3 new clients in 60 seconds. CSV upload, secrets encrypted." |
| 2:00 | Scene 3 | "Your brand, not ours. Custom logo, colors, company name." |
| 3:00 | Scene 4 | "Drill into any client. 5 workloads including Entra ID — no competitor has this." |
| 4:00 | Scene 5 | "Ransomware hits. KavachIQ detects it, builds a recovery plan, CEO restored first." |
| 6:00 | Scene 6 | "Generate HIPAA/SOC2 compliance evidence. One click per client." |
| 7:00 | Scene 7 | "You pay $1.50/user. Sell at $6. That's 75% margin on $10K+/month." |
| 8:00 | Scene 8 | "Offboard when you're done. Data retained per SLA. Full lifecycle." |
| 9:00 | CTA | "Start your 3-month free pilot today." |
