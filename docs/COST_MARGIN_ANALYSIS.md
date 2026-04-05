# KavachIQ — Cost, Margin & Pricing Analysis

**Date: 2026-03-29 | Version 2.3.0 | Pricing: Option B**

---

## 1. Pricing Model (Option B — Competitive)

### SaaS Pricing Tiers

| Tier | Price/user/mo | Retention | Key Differentiator | Target |
|------|--------------|-----------|-------------------|--------|
| **Community** | Free | 30 days | 25 objects, 3 workloads | Developers, POC |
| **Professional** | $1.50 | 90 days | All 5 workloads, Full Smart Engine | SMB (10-500 users) |
| **Business** | $3.00 | 1 year | Org Context, MVB Plans, Criticality Scoring | Mid-Market (100-1,000) |
| **Enterprise** | $5.00 | 1 year | Agentic Recovery, WORM, eDiscovery, Cleanroom | Enterprise (500+) |

### Competitive Positioning

| Vendor | Price/user/mo | vs KavachIQ |
|--------|--------------|-------------|
| **Microsoft Native M365 Backup** | ~$0.75/user (est.) | Cheaper, but no intelligence/MVB/recovery orchestration |
| **Veeam Data Cloud** | $2.00 (reseller) | KavachIQ Professional beats at $1.50 |
| **AvePoint** | $3-5 | KavachIQ Business matches at $3.00 with more intelligence |
| **Druva** | $4-7 | KavachIQ Enterprise undercuts at $5.00 |
| **Commvault Cloud** | $4-6 | KavachIQ Business/Enterprise cheaper with more automation |
| **Rubrik M365** | $6-10 | KavachIQ Enterprise at $5.00 is 50% less |

**Why we win:** Auto-detected MVB recovery plans, org context, criticality scoring, and agentic recovery at 50-70% of Rubrik/Druva pricing. Intelligence is the moat, not storage.

---

## 2. Azure Infrastructure Costs

### Current Costs (Pay-as-you-go)

| Component | Dev/Demo | Small Prod (5 tenants) | Medium Prod (50 tenants) |
|-----------|---------|----------------------|------------------------|
| Container Apps (backend + worker + frontend) | $30 | $30 | $76 |
| PostgreSQL Flexible Server | $26 | $198 | $432 |
| Redis Cache | $16 | $75 | $200 |
| Azure Blob Storage | $2 | $2 | $6 |
| Container Registry | $5 | $10 | $50 |
| Log Analytics | $10 | $35 | $120 |
| Key Vault | ~$0 | ~$0 | ~$0 |
| Networking/Egress | ~$0 | ~$5 | ~$50 |
| **Total** | **$89** | **$355** | **$934** |

### Optimized Costs (Applied Savings)

| Optimization | Dev | Small Prod | Medium Prod |
|-------------|-----|-----------|-------------|
| PostgreSQL: Neon Serverless or stop-on-idle | $26 → $0-15 | $198 → $40 | $432 → $150 |
| Redis: In-process dispatch (single instance) | $16 → $0 | $75 → $0 | $200 → $52 (reserved) |
| Container Apps: Scale-to-zero + savings plan | $30 → $10 | $30 → $25 | $76 → $65 |
| Log Analytics: 7-day retention (dev) | $10 → $2 | $35 → $35 | $120 → $120 |
| ACR: Purge old images | $5 → $3 | $10 → $5 | $50 → $50 |
| **Optimized Total** | **$20-35** | **$110** | **$445** |
| **Savings** | **60-78%** | **69%** | **52%** |

### Cost-Saving Levers

| Lever | Savings | Notes |
|-------|---------|-------|
| **Neon Serverless PostgreSQL** | 65-92% on DB | Scale-to-zero, $0.35/GB storage, Azure native |
| **In-process dispatch** | $16-75/mo | Already built (`DISPATCH_MODE=in_process`) |
| **Reserved Instances (1yr)** | 30-40% on compute | PostgreSQL + Redis + Container Apps |
| **Scale-to-zero** | $25-45/mo | Frontend + worker min_replicas=0 |
| **`make az-sleep`** | ~$60/mo for dev | Scales to 0, stops DB |
| **Log retention tuning** | $8-28/mo | 30d → 7d for non-prod |
| **Compression + CDC** | 40-60% less storage | Already implemented (zstd + CDC dedup) |

---

## 3. Margin Analysis (Option B Pricing + Optimized Infrastructure)

### Small Customer (50 users, Professional $1.50)

| Line Item | Monthly |
|-----------|---------|
| Revenue (50 x $1.50) | $75 |
| Infrastructure (optimized dev) | $35 |
| **Gross Margin** | **$40 (53%)** |

### Mid-Market Customer (200 users, Business $3.00)

| Line Item | Monthly |
|-----------|---------|
| Revenue (200 x $3.00) | $600 |
| Infrastructure (optimized small prod) | $110 |
| **Gross Margin** | **$490 (82%)** |

### Enterprise Customer (1,000 users, Enterprise $5.00)

| Line Item | Monthly |
|-----------|---------|
| Revenue (1,000 x $5.00) | $5,000 |
| Infrastructure (optimized medium prod) | $445 |
| **Gross Margin** | **$4,555 (91%)** |

### Multi-Tenant (10 customers, avg 100 users, Business $3.00)

| Line Item | Monthly |
|-----------|---------|
| Revenue (1,000 users x $3.00) | $3,000 |
| Infrastructure (shared medium, optimized) | $445 |
| Support staff (0.5 FTE) | $3,000 |
| **Net Margin** | **-$445 (-15%)** |
| **At 20 customers (2,000 users)** | **$2,555 (43%)** |

### Key Insight
At Option B pricing, **breakeven on multi-tenant with support staff is ~13 customers** (1,300 users at Business tier). Below that, infrastructure costs are negligible — it's the support FTE that drives the breakeven. At 20+ customers on shared infrastructure, net margins exceed 40%.

---

## 4. Unit Economics

| Metric | Value | Industry Benchmark |
|--------|-------|--------------------|
| **ARPU (Professional)** | $1.50/mo ($18/yr) | $48-96/yr for M365 backup |
| **ARPU (Business)** | $3.00/mo ($36/yr) | Competitive with AvePoint |
| **ARPU (Enterprise)** | $5.00/mo ($60/yr) | 50% below Rubrik |
| **Infrastructure/user (at scale)** | ~$0.45/user/mo | Optimized medium tier |
| **Gross Margin** | 53-91% | Best-in-class SaaS: 70-80% |
| **LTV (3yr, Business)** | $108 | Conservative |
| **LTV:CAC Target** | >3:1 | $36 max CAC per user |

---

## 5. Pricing vs Competitors — Feature Matrix

| Feature | Microsoft Native | Veeam | AvePoint | KavachIQ Pro ($1.50) | KavachIQ Biz ($3) | KavachIQ Ent ($5) |
|---------|-----------------|-------|----------|---------------------|-------------------|-------------------|
| Exchange backup | Yes | Yes | Yes | Yes | Yes | Yes |
| OneDrive backup | Yes | Yes | Yes | Yes | Yes | Yes |
| SharePoint backup | Yes | Yes | Yes | Yes | Yes | Yes |
| Teams backup | Yes | Yes | Yes | Yes | Yes | Yes |
| Entra ID config backup | No | No | No | Yes | Yes | Yes |
| Smart anomaly detection | No | Basic | No | Yes | Yes | Yes |
| Org Context (auto-detected) | No | No | No | No | Yes | Yes |
| MVB Recovery Plans | No | No | No | No | Yes | Yes |
| Criticality scoring | No | No | No | No | Yes | Yes |
| Agentic Recovery | No | No | No | No | No | Yes |
| WORM immutable storage | No | Yes | Yes | No | No | Yes |
| eDiscovery | No | No | Yes | No | No | Yes |
| Cleanroom Recovery | No | No | No | No | No | Yes |

---

## 6. Operational Scaling

| Phase | Customers | Users | Monthly Revenue | Infrastructure | Margin |
|-------|-----------|-------|-----------------|----------------|--------|
| **Demo/POC** | 1-3 | <100 | Free | $35/mo | N/A |
| **Early** | 3-10 | 100-500 | $150-1,500 | $110/mo | 27-93% |
| **Growth** | 10-50 | 500-5,000 | $1,500-15,000 | $445/mo | 70-97% |
| **Scale** | 50-200 | 5,000-50,000 | $15,000-150,000 | $1,500-5,000/mo | 90-97% |

### Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Veeam drops to $1/user | Margin squeeze on Professional | Free tier captures leads, differentiate on intelligence |
| Microsoft enhances native backup | Baseline protection commoditized | Pivot messaging to recovery intelligence, not backup |
| Azure cost increases | Margin reduction | Neon Serverless + reserved instances hedge |
| Graph API throttling at scale | Backup delays | Circuit breaker + exponential backoff (built) |
| Competitor pricing war | Race to bottom | Intelligence features (MVB, Org Context) have no peer |

---

## 7. Implementation Priority for Cost Optimization

| # | Action | Monthly Savings | Effort |
|---|--------|-----------------|--------|
| 1 | Dev: in-process dispatch (drop Redis) | $16 | Config change |
| 2 | Dev: scale-to-zero (frontend + worker) | $25 | Terraform |
| 3 | Dev: 7-day log retention | $8 | Terraform |
| 4 | Small prod: drop Redis (in-process) | $75 | Config change |
| 5 | Evaluate Neon Serverless (POC) | $150-180 | 1-2 days |
| 6 | Prod: 1yr reserved instances | $100+ | Procurement |
| 7 | Aggressive scale-to-zero (all envs) | $25-45 | Terraform |
