# KavachIQ — Next Session Plan

## Session Context

**Date**: April 8, 2026
**Branch**: `main` (all work merged)
**Deployed**: `v1775693680` on `kavachiq.com`
**Tests**: 401 total (351 backend + 50 frontend), `make release ENV=dev` passes

## What Was Shipped This Session

| Feature | Files Changed | Status |
|---|---|---|
| Workload Lifecycle state machine | `workload_lifecycle.py`, `onboarding.py`, `dashboard.py`, `scheduler.py`, `smart_engine.py` | Deployed |
| 3 Frontend UIs (Organization, Alerts, eDiscovery) | `Organization.tsx`, `AlertSettings.tsx`, `eDiscovery.tsx` | Deployed |
| Auth matrix + data accuracy tests | `test_auth_matrix.py` (185), `test_sidebar_data_accuracy.py` (26), `test_workload_lifecycle.py` (14) | Passing |
| Frontend test infrastructure | Vitest + testing-library, `RoleGate.test.tsx` (8), `Layout.test.tsx` (40) | Passing |
| RoleGate route guards | `RoleGate.tsx`, `App.tsx` (MSP/tenants/features gated) | Deployed |
| Sidebar progressive disclosure | `Layout.tsx` (More Workloads, Admin hidden for prospects), `CommandPalette.tsx` (uses visiblePaths) | Deployed |
| CDN caching | `nginx.conf.template` (CDN-Cache-Control: no-store for HTML, immutable for hashed assets) | Deployed |
| Performance | 4→1 session calls, lazy permissions, staleTime on all queries, removed /dashboard/summary from OnboardingContext | Deployed |
| Onboarding fixes | Auto-enable workloads in /discover, Azure redirect URI, lifecycle_status migration | Deployed |
| Release pipeline | `make release` = test-local → test-pg → safe-deploy → e2e-test (65 checks) | Working |
| PostgreSQL test target | `make test-pg` (225 tests against Docker PG) | Working |
| Landing page refresh | Pricing with workload limits, 6 feature cards, competitor comparison, FAQ | Deployed |

## Three Systemic Issues for Next Session

### 1. Scalable Batch Scheduler (RESEARCH NEEDED)

**Problem**: Current scheduler creates 1 job per workload type per SLA cycle. That 1 job processes ALL objects of that type sequentially. For a tenant with 100K Exchange mailboxes, one job takes 20+ hours with no parallelism.

**What exists today**:
- `backend/app/services/scheduler.py` — `check_and_schedule_backups()` creates jobs
- `backend/app/services/fair_scheduler.py` — `TenantFairScheduler` with per-tenant semaphore (max 3 concurrent)
- `backend/app/services/adaptive_concurrency.py` — AIMD limiter for Graph API (auto-reduces on 429)
- `backend/app/models/backup_job.py` — BackupJob model (no parent/child relationship)
- `backend/app/services/graph_client.py` — `batch_request()` with `GRAPH_BATCH_SIZE` chunking

**Research needed**: How do Veeam, Druva, Commvault, Rubrik handle 100K+ item workloads?
- Parent-child job model (batch coordinator + workers)?
- Graph API pagination strategy ($top=999, delta queries)?
- Checkpoint/resume for long-running jobs?
- KEDA auto-scaling based on queue depth?
- How to split 100K items into optimal batch sizes?

**Proposed direction** (needs validation via research):
```
BackupJob (parent) — tenant_id=1, workload=exchange, objects_total=100000
  ├── BackupJob (child) — batch_offset=0, batch_size=500
  ├── BackupJob (child) — batch_offset=500, batch_size=500
  └── ... (200 batches)
```
- TenantFairScheduler runs 3 child batches concurrently per tenant
- Each batch uses AdaptiveConcurrencyLimiter for Graph API
- Parent aggregates results when all children complete
- Add: `parent_job_id`, `batch_offset`, `batch_size` to BackupJob model

### 2. Anomaly Detection Ceiling + Auto-Resolution

**Problem**: `AnomalyEvent` table grows unbounded. No dedup, no auto-resolve, no TTL. 3442 anomalies accumulated for demo tenant. `resolved` field exists but nothing ever sets it to 1.

**What exists today**:
- `backend/app/services/smart_engine.py` — `detect_anomalies()` creates events, `_check_metric()` creates AnomalyEvent
- `backend/app/models/health_baseline.py` — AnomalyEvent model has `resolved` int field (default 0)
- Grace period: tenants with <3 snapshots skip detection ✅
- Health score: `anomaly_score = max(100 - (active_anomalies * 20), 0)` — drops to 0 at 5+ anomalies

**Fix (3 mechanisms)**:
1. **Dedup**: Before creating event, check if identical unresolved anomaly exists → skip. Max 10 active per tenant (5 workloads × 2 metrics).
2. **Auto-resolve**: After detection cycle, mark anomalies as resolved if their metric is now normal.
3. **TTL cleanup**: Scheduler job deletes resolved >90 days, auto-resolves unresolved >30 days.

**Files to modify**:
- `backend/app/services/smart_engine.py` — add dedup check in `_check_metric()`, add auto-resolve in `detect_anomalies()`
- `backend/app/services/scheduler.py` — add `cleanup_old_anomalies()` job

### 3. Server-Side Onboarding State Machine

**Problem**: Onboarding state spread across 5 places (session response, localStorage ×2, sessionStorage, URL params). Frontend derives steps with OR logic. Steps can un-complete if data changes.

**What exists today**:
- `backend/app/api/auth.py` GET /auth/session returns: `has_tenants`, `has_protected_objects`, `has_backups`, `onboarding_status`
- `frontend/src/contexts/OnboardingContext.tsx` derives 6 steps from session + localStorage `manualSteps`
- `frontend/src/pages/Dashboard.tsx` renders checklist from OnboardingContext

**Fix**: New `onboarding_steps` table — records step completion as immutable events:
```sql
CREATE TABLE onboarding_steps (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  step VARCHAR(50) NOT NULL,
  completed_at TIMESTAMP NOT NULL,
  metadata_json TEXT,
  UNIQUE(user_id, step)
);
```

**Mark steps at the point they happen**:
- `create_account` → `POST /auth/register`
- `connect_platform` → `GET /onboard/callback`
- `discover_workloads` → `POST /onboard/discover`
- `assign_protection` → `POST /onboard/complete`
- `first_backup` → backup engine job completion
- `explore_recovery` → `POST /api/onboarding/steps/explore_recovery/complete`

**Session response** enriched: `{ onboarding: { steps: { create_account: "2026-04-08T...", ... }, completed: 4, total: 6 } }`

**Frontend** simplified: reads `session.onboarding.steps`, no localStorage, no derivation.

## Known Issues in Production

| Issue | Severity | Notes |
|---|---|---|
| Backend degraded (1.3% backup success rate) | HIGH | Pre-existing, backup engine issue |
| 3442 active anomalies for demo tenant | MEDIUM | Will be fixed by anomaly ceiling |
| 1 E2E failure (Demo → recovery endpoint) | LOW | Pre-existing, recovery endpoint returns 403 |
| 3 PG test failures (FK violations on alerts PUT) | LOW | SQLite doesn't enforce FK, PG does |

## Architecture Reference

```
Frontend: React 19 + Vite 8 + TypeScript + Tailwind
Backend: Python 3.12 + FastAPI 0.135 + SQLAlchemy (asyncpg for PG, aiosqlite for tests)
Database: PostgreSQL 16 (Azure Flexible Server in prod, Docker locally)
Storage: Azure Blob Storage (prod), MinIO (dev)
CDN: Cloudflare (origin-controlled caching via CDN-Cache-Control headers)
Deployment: Azure Container Apps, ACR, Terraform
Auth: httpOnly cookies + Redis sessions (BFF pattern)
Scheduler: APScheduler (in-process), dispatches to workers via Redis queue
```

## How to Start Next Session

```bash
# Verify everything works
make dev              # Start Docker Compose (PG + MinIO + Redis)
make test-backend     # 351 SQLite tests
make test-pg          # 225 PostgreSQL tests
cd frontend && npx vitest run  # 50 frontend tests

# Deploy
make release ENV=dev  # Full pipeline
```

**First task**: Research enterprise SaaS backup scheduler patterns (Veeam, Druva, Commvault) for 100K+ item handling. Then implement all 3 systemic fixes.
