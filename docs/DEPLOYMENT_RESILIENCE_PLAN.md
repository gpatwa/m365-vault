# Deployment Resilience Plan — Preventing Production Outages

**Date:** 2026-04-05
**Trigger:** 2-hour production outage during v5.6.0 deploy
**Status:** P0 items actionable now

---

## Root Cause Summary

5 cascading failures turned a routine deploy into a 2-hour outage:

1. **bcrypt version drift** — Docker image had bcrypt 5.x, incompatible with passlib 1.7.4
2. **Migration ran after scheduler** — scheduler queried missing columns → crash loop
3. **Deactivated old revision prematurely** — total backend outage
4. **Azure Files incompatible with PostgreSQL** — `chmod` not supported → postgres failed
5. **No auto-seeding on fresh DB** — app "healthy" but no users exist

---

## P0 — Prevent Recurrence (This Week)

### 1. Pin All Dependencies
**Problem:** `requirements.txt` had `passlib[bcrypt]==1.7.4` but bcrypt itself wasn't pinned. Docker pulled bcrypt 5.x which broke auth.

**Fix:**
```bash
# Generate locked requirements from current working environment
pip freeze > requirements.lock.txt
# In Dockerfile, use the lock file
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
```

**Files:** `backend/requirements.txt`, `backend/Dockerfile`
**Effort:** 30 min

### 2. Pre-Deploy Container Test
**Problem:** Broken image pushed to ACR without local verification.

**Fix:** Add `make pre-deploy-check` that:
1. Builds Docker image locally
2. Starts it with test DB
3. Runs health check + login test inside the container
4. Only proceeds to ACR push if tests pass

```makefile
pre-deploy-check: ## Test Docker image locally before pushing
    docker build --platform linux/amd64 -t kavachiq-test ./backend
    docker run -d --name kavachiq-test-run -p 8001:8000 \
        -e DATABASE_URL=sqlite+aiosqlite:///./test.db \
        -e SECRET_KEY=test -e ENCRYPTION_MASTER_KEY=test \
        -e STORAGE_BACKEND=local kavachiq-test
    sleep 10
    curl -sf http://localhost:8001/health || (docker rm -f kavachiq-test-run && exit 1)
    docker rm -f kavachiq-test-run
    @echo "✅ Container test passed — safe to push"
```

**Files:** `Makefile`
**Effort:** 2 hrs

### 3. Auto-Seed Demo Users on Fresh DB
**Problem:** Fresh deploy had healthy backend but no users — login returned "Invalid credentials" not 500.

**Fix:** In `main.py` startup, after auto-migration:
```python
# If no users exist, create admin + demo (fresh deploy)
user_count = await conn.execute(text("SELECT COUNT(*) FROM users"))
if user_count.scalar() == 0:
    # Hash passwords and insert demo users
    await conn.execute(text("INSERT INTO users ..."))
    logger.info("Auto-seeded admin + demo users (fresh DB)")
```

**Files:** `backend/app/main.py`
**Effort:** 1 hr

### 4. Never Deactivate Without Health Check
**Problem:** Deactivated old revision before new one was confirmed healthy.

**Fix:** Add to `manage-secrets.sh` or a new `scripts/safe-deploy.sh`:
```bash
# Wait for new revision to be Running
NEW_REV=$(az containerapp revision list ... --query "[?properties.active].name" -o tsv | head -1)
STATE=$(az containerapp revision show ... --query "properties.runningState" -o tsv)
if [ "$STATE" != "Running" ]; then
    echo "❌ New revision not healthy. Keeping old revision active."
    exit 1
fi
# Only then deactivate old
```

**Files:** `scripts/safe-deploy.sh` (NEW)
**Effort:** 2 hrs

---

## P1 — Safety Infrastructure (Next 2 Weeks)

### 5. Staging Environment
**Problem:** Deployed untested changes directly to production.

**Design:**
- `ENV=staging` uses the same Terraform modules but separate resource group
- `make deploy-staging` → pushes to staging
- `make promote-prod` → copies staging image tag to prod (no rebuild)
- Staging gets real Stripe test keys, Resend sandbox, demo M365 tenant

**Cost:** ~$30/month (Container Apps scale to zero + Basic Redis)

**Files:** `infra/environments/staging.tfvars` (NEW), `Makefile`, `.github/workflows/deploy.yml`
**Effort:** 4 hrs

### 6. Health-Gated Revision Activation
**Problem:** Azure activates new revision and routes traffic before it's healthy.

**Fix:** In GitHub Actions deploy step:
```yaml
- name: Wait for healthy revision
  run: |
    for i in $(seq 1 30); do
      STATE=$(az containerapp revision list ... --query "[0].properties.runningState" -o tsv)
      if [ "$STATE" = "Running" ]; then
        echo "✅ Revision healthy"
        exit 0
      fi
      echo "Waiting... ($STATE)"
      sleep 10
    done
    echo "❌ Revision not healthy after 5 min — rolling back"
    az containerapp revision activate --revision $OLD_REV ...
    exit 1
```

**Files:** `.github/workflows/deploy.yml`
**Effort:** 2 hrs

### 7. Automated Rollback
**Problem:** When new revision failed, manual intervention was needed.

**Fix:** If new revision is `Degraded` or `Failed` after 5 minutes:
1. Re-activate previous revision
2. Send Slack/email alert
3. Mark deploy as failed in GitHub Actions

**Files:** `scripts/safe-deploy.sh`, `.github/workflows/deploy.yml`
**Effort:** 2 hrs

### 8. DB Migration in CI/CD Pipeline
**Problem:** Migrations were manual — had to remember to run them after deploy.

**Fix:** Add migration step to GitHub Actions:
```yaml
- name: Run DB migration
  run: |
    az containerapp exec --name m365vault-backend-dev \
      --resource-group rg-m365vault-dev \
      --command "python3 -c 'from app.database import engine, Base; import asyncio; asyncio.run(engine.begin().__aenter__().then(lambda c: c.run_sync(Base.metadata.create_all)))'"
```

Or better: the auto-migration in `main.py` handles this (already done).

**Files:** `.github/workflows/deploy.yml`
**Effort:** 1 hr

---

## P2 — Enterprise Resilience (Next Month)

### 9. Blue-Green Deployment
**Problem:** Single active revision — can't test new version before routing traffic.

**Design:**
```
1. Push new image → creates new revision (old still serves 100% traffic)
2. Route 10% traffic to new revision (canary)
3. Monitor for 5 min (error rate, latency)
4. If healthy → shift to 100%
5. If degraded → shift back to 0% + alert
```

Azure Container Apps supports traffic splitting natively:
```bash
az containerapp ingress traffic set \
  --name m365vault-backend-dev \
  --resource-group rg-m365vault-dev \
  --revision-weight "$OLD_REV=90" "$NEW_REV=10"
```

**Files:** `scripts/blue-green-deploy.sh` (NEW)
**Effort:** 4 hrs

### 10. Managed PostgreSQL
**Problem:** PostgreSQL as Container App with ephemeral storage loses data on restart.

**Options:**
| Option | Cost | Data Persistence | Effort |
|---|---|---|---|
| Azure Flexible Server B1ms | $13/mo | ✅ Persistent | 4 hrs |
| Neon serverless Postgres | $0-19/mo | ✅ Persistent | 2 hrs |
| Supabase | $0-25/mo | ✅ Persistent | 2 hrs |
| Current (Container App + EmptyDir) | $0 | ❌ Lost on restart | 0 |

**Recommendation:** Neon for dev (free tier, serverless), Azure Flexible Server for prod.

**Files:** `infra/modules/database/` (NEW), `infra/main.tf`
**Effort:** 4-8 hrs

### 11. Automated E2E in CI
**Problem:** Shipped broken builds — no automated verification after deploy.

**Fix:** Run the 23-test Azure E2E certification suite after every deploy:
```yaml
- name: E2E Certification
  run: |
    ./scripts/e2e-azure-test.sh
    if [ $? -ne 0 ]; then
      echo "❌ E2E failed — rolling back"
      # Rollback logic
    fi
```

**Files:** `scripts/e2e-azure-test.sh` (NEW from today's inline test), `.github/workflows/deploy.yml`
**Effort:** 4 hrs

---

## P3 — Operational Excellence (Next Quarter)

### 12. Dependency Scanning
**Problem:** bcrypt version conflict discovered at deploy time, not during development.

**Fix:**
- Enable Dependabot for Python + npm
- Add `pip-audit` to CI pipeline
- Pin major versions, allow patch updates
- Weekly automated dependency update PRs

**Files:** `.github/dependabot.yml` (NEW), `.github/workflows/ci.yml`
**Effort:** 2 hrs

### 13. Observability & Alerting
**Problem:** Had to manually check container logs to diagnose the outage.

**Fix:**
- Azure Monitor alerts: container restart count > 3 in 5 min
- Uptime monitoring: ping `api.kavachiq.com/health` every 1 min
- Slack webhook on deploy failure
- PostHog session replay for frontend errors

**Tools:** Azure Monitor (free tier), UptimeRobot (free), Slack webhook
**Effort:** 4 hrs

### 14. Disaster Recovery Runbook
**Problem:** The `az-cleanup + full-deploy` process had multiple manual steps and failures.

**Fix:** Document and automate the full DR procedure:
```
make dr-rebuild ENV=dev
  → Deletes resource group
  → Clears TF state
  → Purges Key Vault
  → Terraform apply (creates everything)
  → Push images
  → Push secrets
  → Bind custom domains + SSL certs
  → Seed demo users
  → Run E2E tests
  → Re-enable Cloudflare proxy
```

One command, zero manual steps, ~15 min total.

**Files:** `scripts/dr-rebuild.sh` (NEW), `Makefile`
**Effort:** 4 hrs

### 15. Custom Domain Automation
**Problem:** Binding custom domains + SSL certs required manual Cloudflare proxy toggling.

**Fix:** Add to Terraform or deploy script:
1. Create `asuid` TXT records for ALL domains during bootstrap
2. Add hostnames to Container Apps
3. Temporarily disable Cloudflare proxy via API
4. Bind managed certs (with retry loop)
5. Re-enable Cloudflare proxy

Requires Cloudflare API token stored in Key Vault.

**Files:** `scripts/bind-custom-domains.sh` (NEW)
**Effort:** 3 hrs

---

## Implementation Priority

| Week | Items | Impact |
|---|---|---|
| **This week** | P0: Pin deps, pre-deploy check, auto-seed, safe deploy | Prevents repeat of today's outage |
| **Week 2** | P1: Staging env, health-gated activation, rollback | Zero-downtime deploys |
| **Week 3-4** | P2: Blue-green, managed Postgres, E2E in CI | Enterprise-grade resilience |
| **Next quarter** | P3: Dependency scanning, observability, DR runbook | Operational maturity |

---

## Metrics to Track

| Metric | Current | Target |
|---|---|---|
| Deploy success rate | ~70% (manual recovery needed) | 99%+ |
| Time to deploy | ~30 min (with issues) | < 10 min |
| Mean time to recovery | 2 hours (today) | < 5 min (automated rollback) |
| Unplanned downtime/month | 2 hours | < 5 min |
| E2E test coverage | 23 tests (manual) | 23+ tests (automated in CI) |
