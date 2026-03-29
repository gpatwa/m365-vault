# Shieldio — Cost, Margin, Profit & Operations Analysis

**Date: 2026-03-28 | Version 2.2.0**

---

## 1. Azure Infrastructure Costs (Monthly)

### Per-Tier Breakdown

| Component | Small (Dev/Demo) | Medium (10 tenants) | Large (50+ tenants) |
|-----------|-----------------|---------------------|---------------------|
| **Container Apps** (backend + worker + frontend) | $30 | $76 | $207 |
| **PostgreSQL** (Flexible Server) | $26 | $198 | $432 |
| **Redis Cache** | $16 | $75 | $200 |
| **Azure Blob Storage** (backup data) | $2 | $6 | $40 |
| **Container Registry** | $5 | $10 | $50 |
| **Log Analytics** | $10 | $35 | $120 |
| **Key Vault** | ~$0 | ~$0 | ~$0 |
| **Networking/Egress** | ~$0 | ~$5 | ~$50 |
| **Total Infrastructure** | **~$89/mo** | **~$405/mo** | **~$1,100/mo** |

### Cost-Saving Levers

| Lever | Savings | Notes |
|-------|---------|-------|
| Reserved Instances (1yr) | 30-40% on compute | PostgreSQL + Container Apps |
| `make az-sleep` for dev | ~$60/mo | Scales to 0, stops DB |
| Compression + CDC | 40-60% less storage | Already implemented (zstd + CDC) |
| Auto-scaling (min replicas) | Variable | Backend: 1-10 replicas, scales with load |
| Log retention tuning | $10-50/mo | 30d → 7d for non-prod |

---

## 2. Pricing Model & Revenue

### SaaS Pricing (Per-User/Month)

| Tier | Price/user/mo | Includes | Target Segment |
|------|--------------|----------|----------------|
| **Starter** | $3/user | Exchange + OneDrive backup, 30-day retention | SMB (10-100 users) |
| **Business** | $5/user | All 5 workloads, 90-day retention, Smart Engine | Mid-Market (100-500 users) |
| **Enterprise** | $8/user | All workloads + Org Context + MVB + WORM + eDiscovery | Enterprise (500+ users) |

### Competitive Pricing Context

| Vendor | Price/user/mo | Notes |
|--------|--------------|-------|
| **Veeam M365** | $2.50-4.50 | Per-user, basic backup only |
| **Druva M365** | $4-7 | Cloud-native, per-user |
| **Rubrik M365** | $6-10 | Enterprise, includes MVB (when GA) |
| **Commvault M365** | $5-8 | Cleanroom recovery extra |
| **AvePoint** | $3-5 | Per-user, compliance focused |
| **Shieldio** | $3-8 | Competitive with auto-detected MVB differentiator |

---

## 3. Margin Analysis

### Small Customer (50 users, Business tier)

| Line Item | Monthly |
|-----------|---------|
| Revenue (50 × $5) | $250 |
| Infrastructure (shared dev) | $89 |
| **Gross Margin** | **$161 (64%)** |

### Medium Customer (200 users, Business tier)

| Line Item | Monthly |
|-----------|---------|
| Revenue (200 × $5) | $1,000 |
| Infrastructure (dedicated medium) | $405 |
| **Gross Margin** | **$595 (60%)** |

### Enterprise Customer (1,000 users, Enterprise tier)

| Line Item | Monthly |
|-----------|---------|
| Revenue (1,000 × $8) | $8,000 |
| Infrastructure (large, dedicated) | $1,100 |
| **Gross Margin** | **$6,900 (86%)** |

### Multi-Tenant (10 customers, avg 100 users, Business tier)

| Line Item | Monthly |
|-----------|---------|
| Revenue (1,000 users × $5) | $5,000 |
| Infrastructure (shared medium) | $405 |
| Support staff (0.5 FTE) | $3,000 |
| **Net Margin** | **$1,595 (32%)** |

### Key Insight
**SaaS margins improve dramatically with scale.** At 10+ tenants on shared infrastructure, infrastructure cost per user drops below $0.50/user/mo while revenue stays $3-8/user/mo. The 60-86% gross margin is in line with top SaaS companies.

---

## 4. Unit Economics

| Metric | Value | Industry Benchmark |
|--------|-------|--------------------|
| **CAC (Customer Acquisition Cost)** | TBD (currently $0 — founder-led sales) | $500-2,000 for SMB SaaS |
| **ARPU (Avg Revenue Per User)** | $5/mo ($60/yr) | $48-96/yr for M365 backup |
| **LTV (Lifetime Value)** | $180 (3yr × $60/yr) | Assumes 3-year retention |
| **LTV:CAC Ratio** | >3:1 target | Healthy SaaS benchmark |
| **Payback Period** | <12 months target | Based on subscription revenue |
| **Gross Margin** | 60-86% | Best-in-class SaaS: 70-80% |

---

## 5. Operational Considerations

### Day-to-Day Operations

| Responsibility | Effort | Notes |
|----------------|--------|-------|
| Infrastructure monitoring | Low | Azure Monitor + Log Analytics handles alerts |
| Backup job monitoring | Low | Smart Engine auto-detects anomalies, sends alerts |
| Customer onboarding | 15-30 min | Self-service OAuth + guided wizard |
| Support tickets | 1-2 hrs/week at scale | Most issues are M365 API throttling (auto-retried) |
| Security patches | Monthly | Docker base image updates |
| Database maintenance | Minimal | Azure handles backups, scaling |

### Scaling Strategy

| Phase | Users | Infrastructure | Team |
|-------|-------|----------------|------|
| **Demo/POC** (now) | 1-5 tenants | Small ($89/mo) | Founder |
| **Early Customers** | 5-20 tenants | Medium ($405/mo) | Founder + 1 support |
| **Growth** | 20-100 tenants | Large ($1,100/mo) | 2-3 people (eng + support) |
| **Scale** | 100+ tenants | Multi-region ($3-5K/mo) | 5-8 people |

### Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Microsoft Graph API throttling | Backup delays | Exponential backoff + circuit breaker (built) |
| Azure outage | Service down | Multi-region deployment (Phase 3 roadmap) |
| Data breach | Critical | AES-256 encryption, per-tenant DEKs (built) |
| M365 API changes | Feature breakage | Version pinning, delta token fallback (built) |
| Competitor pricing war | Margin pressure | Differentiate on MVB + agentic recovery |

---

## 6. Go-to-Market for Prospect Demo

### Demo Infrastructure

| Resource | Purpose | Monthly Cost |
|----------|---------|-------------|
| Azure Container Apps (dev tier) | Backend + Frontend | $30 |
| PostgreSQL (burstable) | Metadata | $26 |
| Redis (Basic) | Task queue | $16 |
| Blob Storage | Demo backup data | $2 |
| ACR + monitoring | Images + logs | $15 |
| **Total Demo Infra** | | **~$89/mo** |

### Demo Flow (10 minutes)
1. **Connect** — OAuth to prospect's M365 tenant (2 min)
2. **Discover** — Auto-discover mailboxes, sites, teams (1 min)
3. **Protect** — Assign SLA policy, one-click (30 sec)
4. **Backup** — Run first backup, see live progress (2 min)
5. **Recovery Playbook** — Interactive 4-scene demo with their real data (3 min)
6. **Org Context** — Show auto-detected criticality scores (1 min)
7. **MVB Plan** — Generate recovery plan showing their CEO/CFO first (30 sec)

### What Makes the Demo Win
- "We just backed up your CEO's mailbox. If ransomware hit right now, she'd be restored in 5 minutes. Rubrik can't even tell you who your CEO is without you typing it in."
