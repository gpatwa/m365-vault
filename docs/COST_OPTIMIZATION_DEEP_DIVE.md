# Shieldio — Cost Optimization & Competitive Pricing Deep Dive

**Date: 2026-03-29 | Status: Analysis & Recommendations**

---

## 0. Pricing Inconsistency (Fix Required)

The codebase has **two conflicting pricing models**:

| Source | Free | Mid | Top |
|--------|------|-----|-----|
| `COST_MARGIN_ANALYSIS.md` | Starter $3 | Business $5 | Enterprise $8 |
| `usage.py` (actual code) | Community $0 | Professional $1.50 | Enterprise $3.00 |

**Decision needed:** Which is the real pricing? The code-level pricing ($1.50/$3.00) is dramatically lower and would change all margin calculations. The rest of this analysis models both scenarios.

---

## 1. Current Cost Structure — Where the Money Goes

### Medium Tier ($405/mo) Breakdown

```
PostgreSQL Flexible Server ████████████████████ $198 (49%)
Redis Cache               ██████████          $75  (19%)
Container Apps            ██████████          $76  (19%)
Log Analytics             ████                $35  (9%)
Container Registry        ██                  $10  (2%)
Blob Storage              █                   $6   (1%)
Networking                █                   $5   (1%)
                                              ────
                                              $405/mo
```

**Top 3 cost drivers are PostgreSQL (49%), Redis (19%), and Container Apps (19%).**

---

## 2. Savings Opportunity Map

### Tier 1: Quick Wins (No Architecture Change)

| Action | Current Cost | New Cost | Monthly Savings | Effort |
|--------|-------------|----------|-----------------|--------|
| **PostgreSQL: Stop when idle (dev)** | $198 | $6 (storage only) | $192 | 1 hour — already built (`make az-sleep`) |
| **Redis: Downgrade to C0 (dev)** | $75 | $16 | $59 | Config change in `dev.tfvars` |
| **Log Analytics: 7-day retention (dev)** | $35 | $7 | $28 | Config change |
| **ACR: Purge old images** | $10 | $5 | $5 | Cron job |
| **Dev total** | **$405** | **~$110** | **~$295** | |

### Tier 2: Reserved Instances (Commitment Required)

| Resource | Pay-as-you-go | 1yr Reserved | 3yr Reserved | Savings |
|----------|--------------|--------------|--------------|---------|
| PostgreSQL B1ms (dev) | $12.41/mo compute | ~$8/mo | ~$5/mo | 35-60% |
| PostgreSQL GP D2s_v3 (prod) | $198/mo | ~$130/mo | ~$90/mo | 35-55% |
| Container Apps (savings plan) | $76/mo | ~$65/mo (15% off) | ~$63/mo (17% off) | 15-17% |
| Redis Standard C1 (prod) | $75/mo | ~$52/mo | ~$38/mo | 30-50% |

**Prod savings with 1yr reserved: ~$405 → ~$260/mo (36% reduction)**

### Tier 3: Architecture Changes (High Impact)

#### A. Replace Azure PostgreSQL with Neon Serverless

Neon (acquired by Databricks) offers true serverless PostgreSQL with scale-to-zero. Available as Azure native integration.

| Scenario | Azure Flexible Server | Neon Serverless | Savings |
|----------|----------------------|-----------------|---------|
| Dev (idle 20hrs/day) | $198/mo (always on) | ~$15/mo (billed per CU-hour) | **92%** |
| Small prod (5 tenants) | $198/mo | ~$40/mo | **80%** |
| Medium prod (50 tenants) | $432/mo | ~$150/mo | **65%** |

**Key benefits:**
- Scale-to-zero (zero cost when idle)
- $0.35/GB-month storage (down from $1.75 after Databricks acquisition)
- Database branching for dev/test
- Native Azure Marketplace integration

**Trade-offs:**
- Less Azure-native (no Azure AD auth integration)
- Newer service — less battle-tested for production
- Vendor lock-in to Neon/Databricks

#### B. Replace Redis with In-Process Queue (for small deploys)

Current Redis usage: job dispatch queue. For single-instance dev/small prod, this can be done in-process.

| Scenario | With Redis | In-Process | Savings |
|----------|-----------|------------|---------|
| Dev | $16/mo (C0) | $0 | **$16/mo** |
| Small prod (1 instance) | $75/mo (C1) | $0 | **$75/mo** |

Already supported: `DISPATCH_MODE=in_process` exists in config. Only need Redis for multi-worker deployments.

**Recommendation:** Default to `in_process` for dev and small prod. Only provision Redis when `WORKER_CONCURRENCY > 1` across multiple instances.

#### C. Container Apps: Aggressive Scale-to-Zero

Current config allows min_replicas=1 even in dev. The frontend is static (nginx) — it can scale to 0 with fast cold start.

| Change | Savings |
|--------|---------|
| Frontend min_replicas: 0 | ~$10/mo |
| Worker min_replicas: 0 (when no jobs) | ~$15/mo |
| Backend min_replicas: 0 (dev only) | ~$20/mo |

Container Apps free grant: 180,000 vCPU-seconds/mo (~50 vCPU-hours). A 0.5 vCPU backend running 24/7 uses 360 hours — well above the free tier. But with scale-to-zero, intermittent dev usage could stay within free tier.

---

## 3. Optimized Cost Projections

### Dev Environment (After Optimization)

| Component | Current | Optimized | Notes |
|-----------|---------|-----------|-------|
| Container Apps | $30 | $10 | Scale-to-zero, free tier covers light usage |
| PostgreSQL | $26 | $0-15 | Neon free tier (100 CU-hours) or stop-on-idle |
| Redis | $16 | $0 | In-process mode |
| Blob Storage | $2 | $2 | Minimal |
| ACR + Logs | $15 | $8 | 7-day retention, image pruning |
| **Total** | **$89** | **$20-35** | **60-78% reduction** |

### Small Production (5 tenants, 50 users)

| Component | Current | Optimized | Notes |
|-----------|---------|-----------|-------|
| Container Apps | $30 | $25 | Min 1 replica backend, 0 for worker/frontend |
| PostgreSQL | $198 | $40 | Neon serverless or Burstable B1ms with auto-stop |
| Redis | $75 | $0 | In-process dispatch (single instance) |
| Blob Storage | $2 | $2 | |
| Other | $25 | $15 | |
| **Total** | **$405** | **$82** | **80% reduction** |

### Medium Production (50 tenants, 500 users) — 1yr Reserved

| Component | Current | Optimized | Notes |
|-----------|---------|-----------|-------|
| Container Apps | $76 | $65 | Savings plan (15%) |
| PostgreSQL | $198 | $90 | Neon or reserved GP D2s_v3 |
| Redis | $75 | $52 | Reserved C1 |
| Blob Storage | $6 | $6 | |
| Other | $50 | $30 | Retention tuning |
| **Total** | **$405** | **$243** | **40% reduction** |

---

## 4. Competitive Pricing Landscape (Updated)

### Market Pricing (2026)

| Vendor | Per User/Mo | Storage Model | Key Feature |
|--------|------------|---------------|-------------|
| **Microsoft Native M365 Backup** | ~$0.15/GB (~$10/user est.) | Consumption | Ultra-fast restore, but expensive at scale |
| **Veeam Data Cloud** | $1.67-2.00 | Per-user | Dominant market share, reseller discounts |
| **AvePoint Cloud Backup** | $3-5 | Per-user | Compliance, unlimited storage |
| **Druva** | $4-7 | Per-user/consumption | Cloud-native, but complex credits |
| **Commvault Cloud** | $4-6 | Per-user | Managed storage included |
| **Rubrik M365** | $6-10 | Per-user | Enterprise MVB, but expensive |
| **Shieldio (current)** | $3-8 | Per-user | Auto-MVB, org context, agentic recovery |

### Critical Insight: Veeam Has Moved Downmarket

Veeam through resellers is now **$2.00/user/mo** — cheaper than our Starter tier ($3). This means:
- Our Starter at $3 is **not competitive** against Veeam for basic backup
- Our Business at $5 competes with Druva/Commvault but needs Smart Engine differentiation
- Our Enterprise at $8 competes with Rubrik — must deliver on MVB/agentic recovery

### Microsoft Native Backup Threat

Microsoft's own M365 Backup at $0.15/GB is a new competitor. For a 100-user org with 500GB total data, that's **$75/mo** ($0.75/user) — cheaper than everyone. However:
- Only 1-year retention
- No cross-tenant restore
- No ransomware detection
- No compliance/eDiscovery
- No recovery orchestration

**Our differentiation must be on intelligence, not storage.**

---

## 5. Recommended Pricing Strategy

### Option A: Keep Current Tiers, Optimize Costs

Keep $3/$5/$8 pricing but cut infrastructure costs 40-80%. Margins improve dramatically.

| Scenario (50 users Business) | Current | Optimized |
|------------------------------|---------|-----------|
| Revenue | $250/mo | $250/mo |
| Infrastructure | $89/mo | $35/mo |
| **Gross Margin** | **64%** | **86%** |

### Option B: Aggressive Undercut (Recommended)

Drop prices to win market share, enabled by lower infrastructure costs.

| Tier | Current | New Price | Positioning |
|------|---------|-----------|-------------|
| **Free** | — | $0 (25 objects) | Lead gen, developers |
| **Starter** | $3 | **$1.50** | Beat Veeam on price, match `usage.py` |
| **Business** | $5 | **$3.00** | Match AvePoint, beat Druva |
| **Enterprise** | $8 | **$5.00** | Beat Rubrik, match Commvault |

**Margin check at new prices (optimized infra):**

| Customer | Revenue | Infra | Gross Margin |
|----------|---------|-------|-------------|
| 50 users (Starter $1.50) | $75/mo | $35/mo | **53%** |
| 200 users (Business $3) | $600/mo | $82/mo | **86%** |
| 1,000 users (Enterprise $5) | $5,000/mo | $243/mo | **95%** |
| 10 tenants avg 100 (Business) | $3,000/mo | $243/mo | **92%** |

Even at 50% lower prices, margins stay healthy because infrastructure costs drop more.

### Option C: Consumption-Based (Like Microsoft)

Charge per GB protected per month instead of per user. Advantages:
- Aligns cost to value (more data = more protection = more revenue)
- No "empty seat" problem
- Transparent, like cloud billing

| Tier | Price | Included |
|------|-------|----------|
| **Free** | $0 | 5 GB, 1 tenant, basic backup |
| **Pro** | $0.10/GB/mo | All workloads, 90d retention, Smart Engine |
| **Enterprise** | $0.08/GB/mo + $500/mo platform fee | MVB, Org Context, WORM, eDiscovery |

At $0.10/GB: A 200-user org with 1TB data pays $100/mo ($0.50/user) — undercutting everyone including Microsoft.

---

## 6. Fix Pricing Inconsistency

The code in `usage.py` defines $1.50/$3.00 while docs say $3/$5/$8.

**Recommendation:** Update to Option B pricing (which aligns with `usage.py` for Professional/Enterprise) and update the COST_MARGIN doc to match.

| Code Tier | `usage.py` Price | Proposed |
|-----------|-----------------|----------|
| community | $0 | $0 (Free, 25 objects) |
| professional | $1.50 | $1.50 (Starter → Professional) |
| enterprise | $3.00 | $3.00 (matches, add $5 "Premium" tier later) |

---

## 7. Implementation Priority

| # | Action | Savings/Impact | Effort |
|---|--------|----------------|--------|
| 1 | **Fix pricing inconsistency** — align docs to code | Clarity | 30 min |
| 2 | **Dev: in-process dispatch** — drop Redis | $16/mo | Already done (config) |
| 3 | **Dev: scale-to-zero** — frontend + worker | $25/mo | Terraform change |
| 4 | **Dev: 7-day log retention** | $28/mo | Terraform change |
| 5 | **Small prod: drop Redis** — use in-process | $75/mo | Config change |
| 6 | **Evaluate Neon Serverless** — POC for dev | $150-180/mo | 1-2 days |
| 7 | **Prod: 1yr reserved instances** — PostgreSQL + Redis | $100+/mo | Procurement |
| 8 | **Update pricing page/tiers** — Option B or C | Revenue positioning | 1 day |

---

## Sources

- [Azure Container Apps Pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
- [Azure PostgreSQL Flexible Server Pricing](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/)
- [Neon vs Azure PostgreSQL Cost Comparison](https://dev.to/bobur/cost-comparison-neon-vs-azure-database-for-postgresql-flexible-server-2lpp)
- [Neon Serverless Postgres Pricing](https://neon.com/pricing)
- [Microsoft 365 Backup Pricing](https://learn.microsoft.com/en-us/microsoft-365/backup/backup-pricing)
- [Veeam Data Cloud Pricing](https://www.veeam.com/products/veeam-data-cloud/purchasing-options.html)
- [Azure Container Apps Cost Optimization](https://azure-finops-essentials.mindbyte.nl/p/azure-container-apps-cost-optimization)
