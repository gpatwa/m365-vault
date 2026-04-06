# KavachIQ — Deployment Strategy

**Date:** 2026-04-05
**Status:** Active

---

## Environments

| Environment | Purpose | URL | Deploy Trigger | Cost |
|---|---|---|---|---|
| **Local** | Development | localhost:5173 | `make dev` | $0 |
| **Staging** | Pre-prod testing | staging.kavachiq.com | `make deploy-staging` (manual) | ~$16/mo |
| **Dev** | Integration testing | app.kavachiq.com | Push to `main` (auto) | ~$50/mo |
| **Prod** | Production | app.kavachiq.com | `make promote-prod` (manual) | ~$100/mo |

---

## Deploy Commands

```bash
# Local development
make dev                    # Start Docker Compose stack
make test                   # Run 53 unit + E2E tests

# Deploy to Azure
make safe-deploy ENV=dev    # Safe deploy: health gate + auto-rollback
make blue-green ENV=dev     # Blue-green: canary 10% → monitor → promote
make deploy-staging         # Deploy to staging via GitHub Actions
make promote-prod           # Promote to production via GitHub Actions

# Verification
make e2e-test ENV=dev       # Run 21-test E2E certification against Azure
make secrets-verify ENV=dev # Verify all secrets in Key Vault

# Full rebuild (disaster recovery)
make full-deploy ENV=dev    # ACR push + secrets + Terraform + migrate
```

---

## Deploy Flow

### Standard Deploy (push to main)

```
Developer pushes to main
        ↓
GitHub Actions CI
  ├── Backend tests (53 pytest)
  ├── Frontend TypeScript check
  ├── Docker build verification
  ├── Terraform validate
  └── Dependency audit (pip-audit)
        ↓
GitHub Actions Deploy (dev)
  ├── Record old revision
  ├── Terraform apply
  ├── Wait for healthy revision (5 min timeout)
  ├── Smoke test (health + frontend)
  └── On failure: auto-rollback to old revision
        ↓
Dev environment live
```

### Blue-Green Deploy (zero downtime)

```
make blue-green ENV=dev
        ↓
1. Record blue (old) revision
2. Build + push new image
3. Deploy green (new) revision
4. Route 10% traffic → green (canary)
5. Monitor 3 min (health check every 30s)
        ↓
   Healthy?
   ├── YES → Route 100% → green, keep blue for rollback
   └── NO  → Route 100% → blue, deactivate green
```

### Production Deploy

```
make deploy-staging         # Test on staging first
   ↓ (verify manually)
make promote-prod           # Trigger production deploy
   ↓
GitHub Actions (production environment)
  ├── Record old revision
  ├── Terraform apply
  ├── Wait for healthy (5 min)
  ├── Smoke test
  └── On failure: AUTO-ROLLBACK
```

---

## Safety Gates

| Gate | When | What Happens on Failure |
|---|---|---|
| **Pre-deploy check** | Before ACR push | Docker image tested locally; blocks push if unhealthy |
| **CI tests** | On every push/PR | 53 tests must pass; blocks merge if failing |
| **Dependency audit** | On every push/PR | Warns on vulnerable deps (non-blocking) |
| **Pinned deps check** | On every push/PR | Blocks if any `>=` or `~=` found in requirements.txt |
| **Health gate** | After deploy | 5 min timeout; new revision must be Running |
| **Smoke test** | After health gate | Backend health + frontend load check |
| **Auto-rollback** | On any failure | Re-activates previous revision |
| **E2E certification** | Manual or CI | 21-test suite against live environment |

---

## Secrets Management

```
.env.secrets (local, gitignored)
        ↓
make secrets-push ENV=dev
        ↓
Azure Key Vault (kv-m365vault-dev)
        ↓
Container Apps (managed identity, key_vault_secret_id)
```

Secrets never touch Terraform state. Rotation: update `.env.secrets` → `make secrets-push`.

---

## Rollback Procedures

### Automatic (CI handles this)
- Deploy fails → old revision re-activated within seconds
- Blue-green canary unhealthy → traffic shifted back to blue

### Manual Emergency
```bash
# List revisions
az containerapp revision list --name m365vault-backend-dev \
  --resource-group rg-m365vault-dev -o table

# Activate old revision
az containerapp revision activate --name m365vault-backend-dev \
  --resource-group rg-m365vault-dev --revision <old-revision-name>
```

### Full Rebuild (nuclear option)
```bash
make az-cleanup ENV=dev     # Delete everything
make full-deploy ENV=dev    # Recreate from scratch (~15 min)
```

---

## Database

**Current:** PostgreSQL as Container App with ephemeral storage (EmptyDir).
Data is lost on restart. Auto-seed creates demo users on fresh DB.

**Planned (P2):** Migrate to Neon serverless PostgreSQL or Azure Flexible Server
for persistent storage.

---

## Monitoring

| What | Tool | Alert |
|---|---|---|
| Container health | Azure Monitor | Restart count > 3 in 5 min |
| Uptime | UptimeRobot (planned) | api.kavachiq.com/health every 1 min |
| Deploy failures | GitHub Actions | Auto-rollback + notification |
| Dependencies | Dependabot | Weekly PRs for updates |
| Security vulns | pip-audit in CI | Warning on known CVEs |
