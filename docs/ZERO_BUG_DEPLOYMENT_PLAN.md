# Zero-Bug Production Deployment Plan

**Goal:** Every deployment to production has zero customer-facing bugs.
**Date:** 2026-04-06
**Trigger:** 20+ reactive deploy cycles in one day, each fixing a new bug

---

## Why Bugs Reach Production Today

Every bug found today was **detectable before deployment**:

| Bug | When Found | When It Should Be Found |
|---|---|---|
| bcrypt version drift | Azure deploy | `make pre-deploy-check` |
| Missing import (ProtectedObject) | Azure deploy | Local build test |
| MSAL offline_access scope | Azure deploy | Local unit test |
| config.js wrong API base | Azure deploy | Local Docker test |
| Stale tenant counters (0 objects) | Azure deploy | Local integration test |
| Field name mismatch (mailboxes vs exchange) | Azure deploy | Local frontend-backend integration test |
| Silent button failure (no error feedback) | Manual browser test | Local UX test |
| Protection Gaps shows -255 | Manual browser test | Local math test |

**Pattern:** We deploy → discover → fix → deploy → discover → fix. Each cycle takes 5-10 minutes. 20 cycles = 2-3 hours of reactive debugging.

**Root cause:** No local integration testing before deploy.

---

## The Zero-Bug Workflow

```
1. Code change
   ↓
2. Local unit test (pytest — 10 sec)
   ↓ Pass?
3. Local Docker build + health check (pre-deploy-check — 30 sec)
   ↓ Pass?
4. Local integration test (docker compose — 60 sec)
   ↓ Pass?
5. Push to Azure (single deploy — 5 min)
   ↓
6. Azure E2E certification (56 tests — 2 min)
   ↓ Pass?
7. ✅ Production ready
```

**Total time: 8 minutes per deployment, zero bugs.**

Today's workflow: 5-10 min per deploy × 20 deploys = 2-3 hours + bugs found by users.

---

## What To Build

### Phase 1: Local Integration Test (make test-local)

A single command that spins up Docker Compose, tests the full stack, and tears down:

```makefile
test-local: ## Full local integration test (unit + API + frontend-backend)
    @echo "═══ Local Integration Test ═══"
    # 1. Unit tests (fast)
    python3 -m pytest backend/tests/ -q --tb=short
    # 2. Docker build (catches import errors)
    docker compose build backend frontend
    # 3. Start stack
    docker compose up -d
    sleep 15
    # 4. API smoke test
    ./scripts/test-local-api.sh
    # 5. Frontend-backend connectivity
    curl -sf http://localhost:5173/config.js | grep "localhost:8000"
    # 6. Login flow
    TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -d "username=demo&password=...")
    # 7. Onboarding callback
    curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/onboard/callback?...
    # 8. Tear down
    docker compose down
    @echo "✅ All local tests passed — safe to deploy"
```

### Phase 2: Pre-Push Gate (git hook)

```bash
# .git/hooks/pre-push
#!/bin/bash
make test-local || { echo "❌ Local tests failed. Push blocked."; exit 1; }
```

### Phase 3: Single Deploy Command

```makefile
release: test-local acr-push safe-deploy e2e-test ## Full release: local test → build → deploy → verify
    @echo "✅ Release complete — zero bugs"
```

### Phase 4: Contract Tests (Frontend ↔ Backend)

The field name mismatch (mailboxes vs exchange) was a **contract violation** — frontend expects one shape, backend returns another. Fix: shared TypeScript/Pydantic schema validation.

```
# Generate OpenAPI spec → validate frontend expectations
backend: openapi.json → defines response shapes
frontend: api.types.ts → generated from openapi.json
build fails if types don't match
```

---

## Metrics

| Metric | Today | Target |
|---|---|---|
| Deploy cycles per feature | 5-20 | 1-2 |
| Bugs found in production | 10+ per session | 0 |
| Time from code to production | 2-3 hours (with bugs) | < 10 min |
| Local test coverage | 0% integration | 100% critical paths |
| Deploy confidence | "hope it works" | "proven locally" |

---

## Priority

| # | Action | Effort | Impact |
|---|---|---|---|
| 1 | `make test-local` (Docker Compose integration test) | 2 hrs | Catches 90% of today's bugs |
| 2 | `make release` (single command: test → deploy → verify) | 1 hr | Eliminates multi-deploy cycles |
| 3 | Pre-push git hook | 30 min | Prevents broken code from reaching Azure |
| 4 | Contract tests (OpenAPI → TypeScript) | 4 hrs | Prevents field name mismatches |
