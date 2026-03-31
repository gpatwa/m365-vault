# Shieldio — Market Analysis, Opex/Capex/Margin, and Growth Strategy

**Date: 2026-03-31 | Status: Strategic Analysis**

---

## 1. Where the Market Is Going

### Total Addressable Market (TAM)

| Market | 2026 Size | 2034 Projection | CAGR |
|--------|-----------|-----------------|------|
| **Data Protection (total)** | $199 billion | $656 billion | 16.1% |
| **Data Protection as a Service (DPaaS)** | $40 billion | $275 billion | 22.5% |
| **SaaS Backup Software** | $1.27 billion | $3 billion | 10% |
| **Cloud Backup** | $8.7 billion | $51.6 billion | 24.9% |

### SaaS Backup Market Share by Platform

| Platform | Market Share | TAM (2026 est.) | Protection Gap |
|----------|-------------|-----------------|----------------|
| **Microsoft 365** | 42% | ~$533M | 20% unprotected |
| **Salesforce** | 26% | ~$330M | 47% unprotected |
| **Google Workspace** | 22% | ~$279M | 34% unprotected |
| **Other** | 10% | ~$127M | Unknown |

### Key Insight: The Unprotected Are the Opportunity

- **61% of businesses** have experienced SaaS data loss
- **Only 40% of IT pros** are confident they can recover in a crisis
- **34% of organizations** still lack ANY third-party SaaS backup
- **47% of Salesforce users** have no dedicated backup strategy
- Salesforce's recycle bin? **15 days.** Google Workspace? **55 days max.** Microsoft 365? **93 days.**

---

## 2. Where Competitors Are Lacking

### Gap Analysis: What Nobody Does Well

| Gap | Impact | Who's Affected |
|-----|--------|----------------|
| **No single vendor covers M365 + Google + Salesforce + intelligence** | Enterprises stitch together 2-3 backup tools | Everyone except Commvault/Rubrik (expensive) |
| **Intelligence is always an upsell** | Rubrik charges $10/user for what should be standard | Mid-market can't afford it |
| **Salesforce backup is wildly overpriced** | OwnBackup: $2.50-5.85/user, GRAX: $48K/yr, Odaseva: $1,750/mo | SMB Salesforce customers |
| **Google Workspace backup is ignored by majors** | Veeam, Veritas don't offer it. <1% of backup market. | 11M+ Google Workspace enterprises |
| **No auto-detected recovery intelligence** | Every competitor requires manual priority config | All orgs without dedicated backup admin |
| **Entra ID / identity config backup** | Rubrik, Veeam, Datto, AvePoint don't cover it | Everyone using Conditional Access |
| **MSP tooling is bolted on, not built-in** | Rubrik just launched MSP program March 2026 | MSPs serving SMB |
| **Compliance evidence generation** | Manual, expensive, requires consultants | Regulated industries (healthcare, legal, finance) |

### Competitor Positioning Map

```
                    High Price ($6-10/user)
                          │
               Rubrik ●   │   ● Druva
                          │
          ─────────────────┼─────────────── Multi-Platform
                          │
   Single Platform        │        ● Commvault
                          │
           Veeam ●        │   ● AvePoint
                          │
                    Low Price ($1-3/user)
                          │
                  Shieldio ●  ← OPPORTUNITY: Low price + Intelligence + Multi-platform
```

**The gap we exploit: Low price + built-in intelligence + multi-platform.** Nobody occupies this position.

---

## 3. Our Opex, Capex, and Unit Economics

### Current Opex (Monthly Operating Cost)

| Phase | Infra | Support | Sales | Marketing | Total | MRR Needed to Break Even |
|-------|-------|---------|-------|-----------|-------|-------------------------|
| **Now (0 customers)** | $35 | $0 | $0 | $0 | $35 | $35 |
| **Phase 1 (10 customers)** | $110 | $50 | $0 (founder) | $100 | $260 | $260 |
| **Phase 2 (50 customers)** | $445 | $3,500 | $3,000 | $500 | $7,445 | $7,445 |
| **Phase 3 (200 customers)** | $1,500 | $13,000 | $10,000 | $2,000 | $26,500 | $26,500 |

### Capex (One-Time Investments)

| Investment | Cost | When | ROI Timeline |
|-----------|------|------|-------------|
| Product development (built) | $0 (founder + Claude) | Done | Immediate |
| Azure infrastructure setup | ~$500 (bootstrap) | Done | Immediate |
| Sales collateral + KB | $0 (built) | Done | Month 1 |
| Google Workspace connector | ~$0 (2-3 weeks dev) | Q3 2026 | Month 3 after launch |
| Salesforce connector | ~$0 (3-4 weeks dev) | Q4 2026 | Month 4 after launch |
| MSP Dashboard (built) | $0 | Done | Month 3 (MSP channel) |
| Design system (built) | $0 | Done | Immediate (mobile demos) |

**Key advantage: Near-zero Capex.** Product is built. Infrastructure is pay-as-you-go. No hardware. No office. No team (yet).

### Unit Economics Per Customer

| Metric | Professional ($1.50) | Business ($3.00) | Enterprise ($5.00) |
|--------|---------------------|------------------|-------------------|
| ARPU per user/month | $1.50 | $3.00 | $5.00 |
| Avg users per customer | 100 | 200 | 500 |
| Revenue per customer/month | $150 | $600 | $2,500 |
| Infra cost per customer | $5.50 | $8.90 | $22.25 |
| Support cost per customer | $50 | $70 | $130 |
| **Gross margin per customer** | **$94.50 (63%)** | **$521 (87%)** | **$2,348 (94%)** |
| LTV (3yr) | $3,402 | $18,756 | $84,528 |
| Target CAC | <$1,134 | <$6,252 | <$28,176 |

### Pricing vs Competitors

| Platform | Shieldio | Cheapest Competitor | Premium Competitor |
|----------|----------|--------------------|--------------------|
| **Microsoft 365** | $1.50/user | Veeam $2.00 | Rubrik $6-10 |
| **Google Workspace** (roadmap) | $1.50/user | CubeBackup $0.42 (self-hosted) | Afi.ai $3.00 |
| **Salesforce** (roadmap) | $2.00/user (est.) | Own $2.50 | Odaseva $5+ |
| **Multi-platform bundle** | $2.50/user (est.) | Spanning $4.00 | Commvault $5-8 |

---

## 4. The Winning Strategy: Multi-SaaS Recovery Intelligence Platform

### Phase 1: Win M365 (Now — Q3 2026)

**What we have:** Full M365 backup with intelligence nobody else offers.

**Target:** 20 direct customers + 5 MSP partners = ~$5K MRR

| Action | Timeline | Cost |
|--------|----------|------|
| Direct sales to healthcare/legal/finance | Month 1-3 | $0 (founder-led) |
| MSP pilot partnerships | Month 2-4 | $0 (free pilot) |
| Content marketing (HIPAA blog, KB) | Ongoing | $0 (built) |
| Compliance consultant referrals | Month 3+ | 10-20% referral fee |

### Phase 2: Add Google Workspace (Q3-Q4 2026)

**Why:** 22% of SaaS backup market. 34% unprotected. Major vendors ignoring it. Google Workspace has 11M+ enterprise customers.

**What to build:**
- Google Workspace connector (Gmail, Drive, Calendar, Contacts, Sites, Chat)
- Reuse: encryption, storage, intelligence, UI — all platform-agnostic
- Estimated build: 3-4 weeks (Graph API → Google Admin SDK)

**Competitive advantage:** We'd be one of few vendors offering M365 + Google + intelligence at $1.50/user. Most Google backup vendors are specialists without M365 support.

**New pricing:**
- M365 only: $1.50/user (existing)
- Google only: $1.50/user (new)
- M365 + Google bundle: $2.00/user (20% discount)

**New TAM:** $279M Google Workspace backup market + cross-sell to existing M365 customers

### Phase 3: Add Salesforce (Q4 2026 — Q1 2027)

**Why:** 26% of SaaS backup market. **47% unprotected.** Salesforce acquired OwnBackup for $1.9B — prices will rise. Independent alternatives needed.

**What to build:**
- Salesforce connector (Accounts, Contacts, Opportunities, Cases, custom objects, metadata)
- Salesforce has REST API + Bulk API — similar pattern to Graph API
- Estimated build: 4-5 weeks

**Competitive advantage:**
- Own (Salesforce-owned) starts at $2.50/user. We'd be at $2.00.
- GRAX costs $48K/year. We'd be $2/user × 200 users = $400/month.
- Odaseva costs $1,750/month minimum. We'd serve the same size org for ~$600/month.

**New pricing:**
- Salesforce only: $2.00/user
- M365 + Salesforce: $2.50/user
- All three (M365 + Google + Salesforce): $3.00/user

### Phase 4: Platform Play (2027)

**The endgame:** Shieldio becomes the **recovery intelligence platform** — not just backup, but context-aware recovery across ALL SaaS.

| SaaS | Connector | Status |
|------|-----------|--------|
| Microsoft 365 | Exchange, OneDrive, SharePoint, Teams, Entra ID | **Built** |
| Google Workspace | Gmail, Drive, Calendar, Contacts, Sites, Chat | Q3 2026 |
| Salesforce | All objects + metadata + custom | Q4 2026 |
| Dynamics 365 | CRM data | Q2 2027 |
| Slack | Messages, files, channels | Q2 2027 |
| Zendesk | Tickets, users, macros | Q3 2027 |
| HubSpot | CRM, marketing, service | Q3 2027 |

**Intelligence layer applies to ALL platforms:**
- Org context (who matters) — works across M365 + Salesforce + Google
- Criticality scoring — cross-platform: "this user is a VP in M365 AND a Salesforce admin"
- Recovery plans — "restore M365 identity first, then Salesforce CRM, then Google Drive"
- Anomaly detection — unified baselines across all SaaS

**This is the gap nobody fills.** Rubrik has multi-platform backup but charges $6-10/user. Commvault has it but is complex and expensive. Nobody has cross-platform recovery intelligence.

---

## 5. Revenue Projections: Multi-Platform

### Conservative Scenario

| Quarter | M365 Customers | Google Customers | SF Customers | Total Users | MRR | ARR |
|---------|---------------|-----------------|-------------|-------------|-----|-----|
| Q2 2026 | 15 | 0 | 0 | 1,500 | $3,000 | $36K |
| Q3 2026 | 30 | 5 | 0 | 4,500 | $7,500 | $90K |
| Q4 2026 | 50 | 15 | 5 | 10,000 | $18,000 | $216K |
| Q1 2027 | 70 | 30 | 15 | 20,000 | $40,000 | $480K |
| Q2 2027 | 100 | 50 | 30 | 35,000 | $70,000 | $840K |
| Q4 2027 | 200 | 100 | 60 | 75,000 | $150,000 | $1.8M |

### Margin at Scale

| At $150K MRR | Monthly |
|-------------|---------|
| Revenue | $150,000 |
| Infrastructure | $5,000 |
| Support (3 FTE + AI) | $20,000 |
| Sales (2 AE + founder) | $25,000 |
| Marketing | $5,000 |
| **Total cost** | **$55,000** |
| **Net margin** | **$95,000 (63%)** |
| **ARR** | **$1.8M** |

---

## 6. Where Competitors Are NOT Investing

### Opportunities They're Missing

| Opportunity | Why Competitors Skip It | Why We Should Take It |
|-------------|------------------------|----------------------|
| **SMB Salesforce backup** | OwnBackup targets enterprise ($2.50+). GRAX = $48K/yr minimum. | 47% of SF users unprotected. $2/user would dominate SMB. |
| **Google Workspace intelligence** | Google backup vendors do basic backup only (no anomaly, no scoring). | We already have the intelligence engine — just add a connector. |
| **Cross-platform recovery plans** | Nobody maps org context across M365 + Salesforce. | "Your VP of Sales is in both M365 and Salesforce — restore both together." |
| **MSP multi-SaaS bundle** | MSP tools focus on M365 only (Veeam, Datto). | MSPs manage clients using M365 + Google + Salesforce. Bundle = $2-3/user. |
| **Self-hosted / data sovereignty** | Cloud-only vendors can't serve EU data residency needs. | Our open-source, self-hosted option is unique. |
| **Compliance-as-a-Service for MSPs** | No competitor auto-generates per-client HIPAA/SOC2 reports. | We already built this — it's a demo highlight. |
| **Entra ID / identity backup** | Only Shieldio backs up CA policies, directory roles, OAuth grants. | In ransomware, identity is the FIRST thing to restore. |

### The #1 Gap: Intelligence at Affordable Price

Every competitor either:
- **Has no intelligence** (Veeam, Datto, AvePoint, Google backup vendors)
- **Charges enterprise prices for intelligence** (Rubrik $6-10/user, Druva $4-7)
- **Doesn't exist for Google/Salesforce intelligence** (nobody)

**Shieldio's position: Intelligence included at $1.50-3.00/user across M365, Google, and Salesforce.** This position is unoccupied.

---

## 7. Go-to-Market Strategy to Win Market Share

### Strategy: Land → Expand → Platform

```
LAND (M365, Now):
  Win 50 M365 customers on intelligence + price
  Prove recovery intelligence works in production
  Build case studies in healthcare/legal/finance

EXPAND (Add Google + Salesforce, Q3-Q4 2026):
  Cross-sell Google Workspace to M365 customers
  New customer segment: Salesforce-heavy orgs
  Bundle pricing: $2-3/user for multi-platform

PLATFORM (Intelligence Layer, 2027):
  Cross-platform org context + recovery plans
  MSP channel: one vendor for all client SaaS
  Enterprise deals: unified SaaS protection
```

### Why This Wins

1. **Price disruption** — $1.50 for what Rubrik charges $6-10
2. **Intelligence included** — competitors charge extra or don't have it
3. **Multi-platform** — most vendors are M365-only or single-platform
4. **MSP-native** — built from day 1, not bolted on
5. **Open source** — trust, auditability, data sovereignty
6. **Cross-platform intelligence** — nobody maps org context across M365 + Google + Salesforce

### The 18-Month Goal

**$1.8M ARR** from 360 customers across 3 platforms, with 63% net margin, and a clear path to $5M ARR by end of 2027.

---

## 8. What to Build Next (Prioritized)

| Priority | Initiative | Effort | Revenue Impact |
|----------|-----------|--------|---------------|
| **P0** | Start selling M365 (Direct + MSP) | 0 weeks (ready now) | $36K ARR in 3 months |
| **P1** | Google Workspace connector | 3-4 weeks | Opens $279M market |
| **P2** | Salesforce connector | 4-5 weeks | Opens $330M market, 47% unprotected |
| **P3** | Multi-platform bundle pricing | 1 week | $2-3/user bundle = higher ARPU |
| **P4** | Cross-platform org context | 2-3 weeks | Unique differentiator, enterprise deals |
| **P5** | Hybrid Backup (MSFT Backup Storage API) | 4-6 weeks | Faster M365 restore |
| **P6** | Agentic Recovery (Claude-powered) | 4-6 weeks | Phase 2.5D roadmap |

---

## Sources

- [SaaS Backup Market Size 2026-2035](https://www.statsndata.org/report/saas-backup-software-market-37242)
- [2025 State of SaaS Backup and Recovery Report](https://thehackernews.com/2025/01/insights-from-2025-saas-backup-and-recovery-report.html)
- [Salesforce Acquires Own for $1.9B](https://techcrunch.com/2024/09/05/salesforce-acquires-data-management-firm-own-for-1-9b-in-cash/)
- [Rubrik: The SaaS Data Gap](https://www.rubrik.com/blog/technology/25/9/the-saas-data-gap-how-to-consolidate-your-cloud-apps-onto-a-single-data-protection-platform)
- [Top SaaS Data Challenges 2026](https://www.msp360.com/resources/blog/top-saas-data-protection-challenges-of-2026/)
- [Google Workspace Backup Guide 2026](https://ifeeltech.com/blog/google-workspace-backup-guide)
- [Data Protection Market $656B by 2034](https://www.fortunebusinessinsights.com/data-protection-market-109715)
- [DPaaS Market $275B by 2033](https://www.imarcgroup.com/data-protection-as-a-service-market)
- [Rubrik Adds Google Workspace Backup](https://www.techzine.eu/news/security/139765/rubrik-adds-google-workspace-backup-with-air-gapped-protection/)
- [Own Pricing from Salesforce](https://www.owndata.com/pricing)
