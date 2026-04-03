# Shieldio — Session State (2026-04-03)

## Resume Instructions
Paste this at the start of a new Claude Code session:
```
Read /Users/gopalpatwa/opt/m365-data-protection/.claude/SESSION_STATE.md and resume from where we left off.
```

## Current State

### Version: 5.1.0 (commit 6a8a609)
- **Git**: `main` branch, pushed to `gpatwa/m365-vault`
- **Azure**: Live at https://m365vault-frontend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io
- **Brand**: Teal/Cyan (#14b8a6) — Geist font, glassmorphism, dark theme
- **Focus**: Entra ID + Exchange (priority workloads), other 3 behind feature flags

### What's Built & Deployed
1. **Core backup/restore** — 2 priority workloads (Entra ID, Exchange) + 3 more behind feature flags (SharePoint, OneDrive, Teams)
2. **Org Context Layer** — auto-synced from Graph API OR populated via `populate-tenant.py` script
3. **MVB Recovery Plans** — pre-computed 4-phase NIST-ordered recovery plans
4. **Interactive onboarding** — 7-step wizard with real tenant data
5. **6-scene Cyber Recovery Playbook** — Browse tenant → Browse backup → Cyber attack → Confidence → Recovery → Protected
6. **Agent Shield Phase 1** — Agent audit dashboard, shadow agent detection, 3 demo profiles (Copilot, HR Bot, OpenClaw)
7. **OpenClaw attack scenario** — AI agent attack simulation in recovery playbook
8. **System diagnostics** — 7 health checks, Graph API metrics, performance benchmarks
9. **Tiered rate limiting** — auth=20, onboard=60, API=600/min
10. **Session management** — sessionStorage tokens, auto-logout on expired tokens
11. **Azure deployment** — Container Apps, Key Vault secrets, ACR images
12. **Landing page** — Teal/Cyan brand, animated ransomware scenario, pricing, FAQ
13. **Contact + About pages** — /contact (form + links), /about (mission + differentiators)
14. **Dark theme** — Full dark mode across all 50+ pages, bg-*-50 → bg-*-500/10 migration
15. **Feature flags** — Workload gating per tier (Community: 2 workloads, Professional+: 5)
16. **Priority workload system** — PRIORITY_WORKLOADS config, sidebar/dashboard/jobs/SLA filtered

### Demo Accounts
- `admin` / `Admin123` — full data (Patwa Inc tenant, 15 org users, 74 objects)
- `demo` / `ShieldiDemo2026!` — clean onboarding experience
- `prospect` / `Prospect2026!` — post-auth onboarding
- `msp` / `MSPDemo2026!` — MSP dashboard
- `viewer` / `Viewer2026!` — read-only

### Data Status (Patwa Inc, tenant_id=3)

| Data | Source | Count |
|---|---|---|
| Exchange mailboxes | Real Graph API | 6 mailboxes, 8 items each |
| Entra ID objects | Real Graph API | 169+ items (users, groups, roles, policies) |
| Snapshots | Real backups | 140 |
| Backup jobs | Real | 103 (91 success, 5 failed, 7 partial) |
| Org Intelligence | Populated via script | 15 users across 4 tiers |
| Agent Shield profiles | Simulated demo | 3 agents (Copilot, HR Bot, OpenClaw) |
| Agent activity | Simulated demo | 20 records |
| Recovery confidence | Computed from jobs | 100/A |

### Tenant Population Script
```bash
# Populate any tenant with 15 realistic users across 4 criticality tiers
docker compose exec backend python3 scripts/populate-tenant.py --tenant-id <ID>
docker compose exec backend python3 scripts/populate-tenant.py --tenant-id <ID> --skip-graph  # DB only
```

Creates: CEO (critical, 92) → 3 VPs (high, 68-76) → 5 Directors (medium, 45-58) → 6 Staff (low, 22-35)

### Feature Flags by Tier

| Tier | Workloads | Intelligence | Recovery |
|---|---|---|---|
| Community (Free) | entra_id, exchange | anomaly_detection, openclaw_attack_demo | mass_recovery |
| Professional ($1.50) | + sharepoint, onedrive, teams | + health_scoring, agent_audit | + test_restore |
| Business ($3.00) | same | + org_context, mvb_plans, criticality_scoring | same |
| Enterprise ($5.00) | + power_platform | + agent_rewind, agent_governance | + agentic_recovery, cleanroom |

### Key Architecture Decisions
- **Priority workloads**: Entra ID + Exchange shown by default, SharePoint/OneDrive/Teams behind Professional+ feature flag
- **Sidebar**: "Workloads" (2 priority) + "More Workloads" (gated by feature flag)
- **Brand**: Teal/Cyan (#14b8a6) — `--primary` CSS variable, all CTAs teal
- **Dark theme**: bg-*-500/10 opacity pattern, no bg-white anywhere
- **Org context**: Auto-syncs from Graph API during onboarding intelligence step; falls back to `populate-tenant.py` data

### Roadmap

#### Completed
- [x] Phase 1: Enterprise Foundation
- [x] Phase 2: Intelligence (Smart Engine, Org Context, Criticality Scoring)
- [x] Phase 2.5A: Smart Backup (criticality, VIP groups)
- [x] Phase 2.5B: Smart Recovery (MVB plans, confidence v2)
- [x] Production Resilience Week 1-2: Error codes, circuit breaker, pre-flight checks
- [x] Teal/Cyan brand + LoopIQ-inspired design polish
- [x] Dark theme migration (52 files, bg-*-50 → bg-*-500/10)
- [x] Priority workload system (Entra ID + Exchange focus)
- [x] Agent Shield Phase 1: Agent audit dashboard + OpenClaw attack demo
- [x] Contact + About pages
- [x] Real org data from Graph API + populate-tenant.py script

#### Planned
- [ ] Agent Shield Phase 2: Agent Rewind (pre-action snapshots, selective rollback)
- [ ] Agent Shield Phase 3: Agent Governance (policy engine, Copilot integration)
- [ ] Stripe Billing integration (see `docs/STRIPE_INTEGRATION_PLAN.md`)
- [ ] Analytics: PostHog + Plausible + Clarity (see research docs)
- [ ] Enhanced Recovery Playbook: Browse tenant → Browse backup → Attack → Recover with real data
- [ ] Hybrid Backup (Microsoft Backup Storage API) — Target Q3 2026

### Key Files

| Area | Files |
|---|---|
| Workload Config | `frontend/src/config/workloads.ts` (PRIORITY_WORKLOADS, MORE_WORKLOADS) |
| Feature Flags | `backend/app/services/feature_flags.py` (TIER_FEATURES per tier) |
| Agent Shield | `backend/app/api/agents.py`, `backend/app/services/agent_monitor.py`, `frontend/src/pages/AgentShield.tsx` |
| Org Context | `backend/app/services/context_collector.py`, `criticality_scorer.py`, `frontend/src/pages/OrgContext.tsx` |
| Onboarding | `frontend/src/pages/Onboard.tsx` (7-step wizard + 6-scene recovery playbook) |
| Landing | `frontend/src/pages/Landing.tsx` (teal brand, pricing, FAQ) |
| Contact/About | `frontend/src/pages/Contact.tsx`, `About.tsx` |
| Layout/Sidebar | `frontend/src/components/Layout.tsx` (feature-flag gated nav groups) |
| Design Tokens | `frontend/src/styles/tokens.css` (--primary: #14b8a6 teal) |
| Tenant Script | `scripts/populate-tenant.py` (15 users, 4 tiers) |

### Docs

| Document | Purpose |
|---|---|
| `docs/STRIPE_INTEGRATION_PLAN.md` | 6-phase Stripe Billing integration plan |
| `docs/RESEARCH_AGENTIC_AI_DATA_PROTECTION.md` | Agent Shield market research + 3-phase roadmap |
| `docs/GO_TO_MARKET_FIRST_20.md` | GTM strategy (updated v5 with demo script) |
| `docs/GROWTH_STRATEGY_ANALYSIS.md` | Land & Expand strategy |
| `docs/MARKET_ANALYSIS_AND_STRATEGY.md` | $1.27B market, platform roadmap |
| `docs/MSP_CHANNEL_STRATEGY.md` | Wholesale tiers, MSP partnerships |
| `docs/COST_MARGIN_ANALYSIS.md` | Unit economics, margin analysis |

### Azure Infrastructure
- Backend: `acrm365vaultdev.azurecr.io/m365vault-backend:latest`
- Frontend: `acrm365vaultdev.azurecr.io/m365vault-frontend:latest`
- Frontend URL: https://m365vault-frontend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io
- Connector App ID: `d5c6ca1d-0f4a-4e14-a121-136fde89512d`
- Resource Group: `rg-m365vault-dev`
- Key Vault: `kv-m365vault-dev`
