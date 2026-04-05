# KavachIQ — Option A (Hybrid) Cost, Pricing & Margin Model

**Date: 2026-03-30 | Status: Analysis**

---

## 1. How the Hybrid Model Works

```
                     ┌─────────────────────────┐
                     │     KavachIQ Platform     │
                     │  (Intelligence + Control) │
                     └────────┬───────┬──────────┘
                              │       │
              ┌───────────────┘       └───────────────┐
              ▼                                       ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│  Microsoft Backup Storage │          │   KavachIQ Own Storage   │
│  (Exchange, SharePoint,   │          │  (Teams, Entra ID,       │
│   OneDrive)               │          │   long-term retention,   │
│                           │          │   WORM, eDiscovery)      │
│  Cost: $0.15/GB/mo        │          │  Cost: $0.02/GB/mo       │
│  Speed: 10-min RPO        │          │  Speed: SLA-driven       │
│  Restore: Seconds-minutes │          │  Restore: Minutes        │
└──────────────────────────┘          └──────────────────────────┘
```

**Microsoft Backup Storage handles**: Exchange, SharePoint, OneDrive — the bulk data
**KavachIQ pipeline handles**: Teams, Entra ID, intelligence layer, anomaly detection, MVB plans

---

## 2. Typical Data Footprint Per User

Industry averages (actual usage, not allocation limits):

| Workload | Avg Storage/User | Source |
|----------|-----------------|--------|
| Exchange mailbox | 3-5 GB | Industry average (50-100 GB limit, ~5-10% used) |
| OneDrive | 2-5 GB | Most users store < 5 GB despite 1 TB allocation |
| SharePoint (per user share) | 1-3 GB | Pooled: 1 TB base + 10 GB/user; actual usage varies |
| **Total per user** | **6-13 GB** | Conservative estimate |
| **Estimate used below** | **10 GB/user** | Middle of range |

For Enterprise with heavy usage: 15-25 GB/user (executives, designers, legal)

---

## 3. Cost Model: Current (Pure KavachIQ) vs Hybrid

### A. Current Model — KavachIQ Stores Everything

| Component | Cost Source | Per User/Mo |
|-----------|-----------|-------------|
| Azure Blob Storage (10 GB × $0.02/GB) | KavachIQ pays | $0.20 |
| Compute (Container Apps — amortized) | KavachIQ pays | $0.15 |
| Database (PostgreSQL — amortized) | KavachIQ pays | $0.10 |
| **Total infrastructure per user** | | **$0.45** |

At $1.50/user (Professional tier): **70% gross margin**
At $3.00/user (Business tier): **85% gross margin**

### B. Hybrid Model — Microsoft Stores Bulk, KavachIQ Stores Intelligence

| Component | Who Pays | Per User/Mo |
|-----------|----------|-------------|
| Microsoft Backup Storage (10 GB × $0.15/GB) | Customer pays Microsoft | $1.50 |
| KavachIQ compute (intelligence, API, UI) | KavachIQ pays | $0.15 |
| KavachIQ storage (Teams + Entra ID ~1 GB) | KavachIQ pays | $0.02 |
| Database (PostgreSQL — amortized) | KavachIQ pays | $0.10 |
| **Total KavachIQ infrastructure per user** | | **$0.27** |
| **Total customer cost (KavachIQ + Microsoft)** | | **KavachIQ price + $1.50** |

---

## 4. Pricing Strategies for Hybrid

### Strategy 1: Transparent Pass-Through
Customer pays Microsoft directly for backup storage. KavachIQ charges for intelligence only.

| Tier | KavachIQ Price | Microsoft Cost | Total Customer Cost |
|------|---------------|----------------|-------------------|
| Professional | $1.50/user | $1.50/user (10 GB avg) | **$3.00/user** |
| Business | $3.00/user | $1.50/user | **$4.50/user** |
| Enterprise | $5.00/user | $1.50/user | **$6.50/user** |

**KavachIQ margin**: 82-94% (we only pay $0.27/user in infra)
**Customer total**: Competitive with Druva ($4-7) and Rubrik ($6-10)
**Advantage**: Transparent — customer sees exactly what they pay for

### Strategy 2: Bundled (KavachIQ Absorbs Microsoft Cost)
KavachIQ pays Microsoft's $0.15/GB and bundles into price.

| Tier | KavachIQ Price | Our Cost (infra + MSFT) | Gross Margin |
|------|---------------|------------------------|-------------|
| Professional | $3.00/user | $1.77/user ($0.27 infra + $1.50 MSFT) | **41%** |
| Business | $4.50/user | $1.77/user | **61%** |
| Enterprise | $7.00/user | $1.77/user | **75%** |

**Advantage**: Simpler billing, customer pays one vendor
**Risk**: Margin compressed at Professional tier; heavy users (>10 GB) erode margins

### Strategy 3: Hybrid Pricing (Recommended)
Keep current pricing for intelligence. Offer Microsoft Backup Storage as optional add-on.

| Tier | Base Price (Intelligence) | + MSFT Backup (Optional) | Total |
|------|--------------------------|--------------------------|-------|
| Professional | $1.50/user | +$0.15/GB (pass-through) | $1.50 + usage |
| Business | $3.00/user | +$0.15/GB (pass-through) | $3.00 + usage |
| Enterprise | $5.00/user | Included (KavachIQ absorbs) | $5.00 flat |

**Why this works**:
- Professional/Business: Customers who want fast restore pay for it, transparent
- Enterprise: All-inclusive — simplest for large deals, we absorb $1.50 but at $5/user still have 65% margin
- Keeps our $1.50 starting price competitive vs Veeam ($2.00)

---

## 5. Margin Analysis: Strategy 3 (Recommended)

### Small Customer (50 users, Professional $1.50 + optional MSFT)

**Without Microsoft Backup Storage:**
| Item | Monthly |
|------|---------|
| Revenue | $75 |
| Infra ($0.27 × 50) | $14 |
| **Gross Margin** | **$61 (81%)** |

**With Microsoft Backup Storage (customer pays Microsoft directly):**
| Item | Monthly |
|------|---------|
| KavachIQ revenue | $75 |
| KavachIQ infra | $14 |
| Customer pays Microsoft (10 GB × 50 users × $0.15) | $75 (not our cost) |
| **KavachIQ gross margin** | **$61 (81%)** |
| **Customer total cost** | **$150 ($3/user)** |

### Mid-Market (200 users, Business $3.00 + optional MSFT)

**Without Microsoft Backup Storage:**
| Item | Monthly |
|------|---------|
| Revenue | $600 |
| Infra ($0.27 × 200) | $54 |
| **Gross Margin** | **$546 (91%)** |

**With Microsoft Backup Storage (customer pays Microsoft):**
| Item | Monthly |
|------|---------|
| KavachIQ revenue | $600 |
| KavachIQ infra | $54 |
| Customer pays Microsoft (10 GB × 200 × $0.15) | $300 |
| **KavachIQ gross margin** | **$546 (91%)** |
| **Customer total cost** | **$900 ($4.50/user)** |

### Enterprise (1,000 users, Enterprise $5.00 — MSFT absorbed)

| Item | Monthly |
|------|---------|
| Revenue | $5,000 |
| KavachIQ infra ($0.27 × 1,000) | $270 |
| Microsoft Backup cost ($1.50 × 1,000) | $1,500 |
| **Total cost** | **$1,770** |
| **Gross Margin** | **$3,230 (65%)** |

Even absorbing Microsoft's cost at Enterprise tier, margin is 65%. At Business, margin is 91% because customer pays Microsoft directly.

---

## 6. Operating Cost Comparison

### Current (Pure KavachIQ) — Medium Prod (50 tenants)

| Component | Monthly Cost |
|-----------|-------------|
| Container Apps | $76 |
| PostgreSQL | $198 |
| Azure Blob Storage | $6 |
| Redis | $75 |
| ACR + Logs | $90 |
| **Total** | **$445** |

### Hybrid — Medium Prod (50 tenants)

| Component | Monthly Cost | Change |
|-----------|-------------|--------|
| Container Apps | $65 (reduced — less backup compute) | -15% |
| PostgreSQL | $198 (same — metadata still ours) | Same |
| Azure Blob Storage | $1 (only Teams + Entra ID) | **-83%** |
| Redis | $75 | Same |
| ACR + Logs | $90 | Same |
| Microsoft Backup Storage | $0 (customer pays) | N/A |
| **Total KavachIQ infra** | **$429** | **-4%** |

**Key insight**: Hybrid barely changes our infrastructure cost because storage was already cheap ($6/mo). The real benefit is **faster restore for customers** and **competitive positioning** as a Microsoft-integrated ISV.

---

## 7. What We Keep vs What Microsoft Handles

| Capability | Current (KavachIQ) | Hybrid | Who Benefits |
|-----------|-------------------|--------|-------------|
| Exchange/SharePoint/OneDrive backup | KavachIQ (Graph API reads) | Microsoft Backup Storage | Customer (faster restore) |
| Teams backup | KavachIQ | KavachIQ (MSFT doesn't cover) | Customer (full coverage) |
| Entra ID backup | KavachIQ | KavachIQ (MSFT doesn't cover) | Customer (unique value) |
| Org Context / Criticality | KavachIQ | KavachIQ | Both (intelligence layer) |
| MVB Recovery Plans | KavachIQ | KavachIQ | Customer (recovery speed) |
| Anomaly Detection | KavachIQ | KavachIQ | Customer (ransomware defense) |
| Recovery Confidence Score | KavachIQ | KavachIQ | Customer (audit evidence) |
| WORM / Legal Hold | KavachIQ | KavachIQ | Customer (compliance) |
| RPO/RTO Compliance | KavachIQ | KavachIQ | Customer (SLA tracking) |
| Storage encryption | KavachIQ (AES-256-GCM) | Microsoft (SSE) + KavachIQ (Teams/Entra) | Both |

**Our moat stays intact**: Intelligence, Teams, Entra ID, compliance tools. Microsoft provides fast bulk backup/restore for the commodity workloads.

---

## 8. Strategic Positioning

### Without Hybrid
"We're a backup vendor competing with Veeam and Rubrik on price and features"

### With Hybrid
"We're the **intelligence layer** on top of Microsoft's backup infrastructure. Use Microsoft for speed. Use KavachIQ for recovery plans, criticality scoring, anomaly detection, and the workloads Microsoft doesn't cover."

This is the Veeam/AvePoint playbook — they're all doing it. The ISVs that DON'T integrate with Microsoft Backup Storage will look outdated.

---

## 9. Implementation Effort

| Phase | Work | Effort |
|-------|------|--------|
| 1. Register as ISV | Register app, get OAuth scopes, billing policy | 1-2 days |
| 2. Protection policies | Create/manage backup policies via Graph API | 1 week |
| 3. Restore integration | Browse, search, restore via Backup Storage API | 1-2 weeks |
| 4. Billing integration | Pass-through billing or absorbed billing | 1 week |
| 5. UI integration | Admin toggle: "Use Microsoft Backup Storage" | 1 week |
| **Total** | | **4-6 weeks** |

### Recommended Timeline
- **Now (Q1 2026)**: Keep current Graph API approach — it works
- **Q3 2026**: Integrate Backup Storage API as optional backend
- **Q4 2026**: Default new tenants to hybrid mode

---

## Sources

- [Microsoft 365 Backup Pricing Model](https://learn.microsoft.com/en-us/microsoft-365/backup/backup-pricing?view=o365-worldwide)
- [Microsoft 365 Backup Storage API Overview](https://learn.microsoft.com/en-us/graph/backup-storage-concept-overview)
- [Third-Party Developer Overview](https://learn.microsoft.com/en-us/microsoft-365/backup/storage/backup-3p-overview?view=o365-worldwide)
- [Microsoft 365 Backup GA Announcement](https://techcommunity.microsoft.com/blog/microsoft_365_backup_blog/microsoft-announces-general-availability-of-microsoft-365-backup-and-microsoft-3/4205300)
- [Microsoft 365 Backup Cost Analysis](https://office365itpros.com/2024/03/20/microsoft-365-backup-costs/)
- [EWS Retirement Timeline](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/deprecation-of-ews-exchange-online)
