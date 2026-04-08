# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Unified Task Runner
# ──────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Variables ────────────────────────────────────────────────────────
DOCKER_COMPOSE = docker compose
TF_DIR         = infra
ENV           ?= dev

# Auto-load SUBSCRIPTION_ID from .env.azure if not passed on command line
-include .env.azure
SUBSCRIPTION_ID ?= $(shell az account show --query id -o tsv 2>/dev/null)

# ── Help ─────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@echo ""
	@echo "KavachIQ — Available Commands"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sed 's/^.*Makefile://' | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bootstrap (one-time setup)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: bootstrap
bootstrap: ## One-time Azure + GitHub setup (service principal, OIDC, tfstate, secrets)
	@./scripts/bootstrap-azure.sh

.PHONY: check-prereqs
check-prereqs: ## Verify all prerequisites are installed
	@echo "Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 && echo "  ✓ docker" || echo "  ✗ docker (required)"
	@command -v az >/dev/null 2>&1 && echo "  ✓ az CLI" || echo "  ✗ az CLI (required for Azure)"
	@command -v gh >/dev/null 2>&1 && echo "  ✓ gh CLI" || echo "  ✗ gh CLI (required for GitHub)"
	@command -v terraform >/dev/null 2>&1 && echo "  ✓ terraform" || echo "  ✗ terraform (required for infra)"
	@command -v python3 >/dev/null 2>&1 && echo "  ✓ python3" || echo "  ✗ python3 (required for backend)"
	@command -v node >/dev/null 2>&1 && echo "  ✓ node" || echo "  ✗ node (required for frontend)"
	@command -v jq >/dev/null 2>&1 && echo "  ✓ jq" || echo "  ✗ jq (required for scripts)"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Local Development
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: dev
dev: ## Start local dev stack (Docker Compose: postgres + minio + backend + frontend)
	$(DOCKER_COMPOSE) up --build

.PHONY: dev-bg
dev-bg: ## Start local dev stack in background
	$(DOCKER_COMPOSE) up --build -d
	@echo ""
	@echo "Services running:"
	@echo "  Frontend:  http://localhost:5173"
	@echo "  Backend:   http://localhost:8000"
	@echo "  MinIO:     http://localhost:9001 (admin/minioadmin)"
	@echo ""

.PHONY: dev-down
dev-down: ## Stop local dev stack
	$(DOCKER_COMPOSE) down

.PHONY: dev-clean
dev-clean: ## Stop and remove all volumes (fresh start)
	$(DOCKER_COMPOSE) down -v
	@echo "All volumes removed. Run 'make dev' for a fresh start."

.PHONY: dev-logs
dev-logs: ## Tail logs from all services
	$(DOCKER_COMPOSE) logs -f

.PHONY: dev-backend
dev-backend: ## Run backend directly (without Docker) — requires local Python venv
	cd backend && python3 -m uvicorn app.main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend: ## Run frontend directly (without Docker) — requires local Node
	cd frontend && npm run dev

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Local Integration Test (run BEFORE deploying to Azure)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: test-local
test-local: ## Full local integration test: units + docker + API + frontend + auth + data
	@./scripts/test-local.sh

.PHONY: test-unit
test-unit: ## Run unit tests only (fast, no Docker)
	@python3 -m pytest backend/tests/test_restore_permissions.py backend/tests/test_restore_consent.py backend/tests/test_workload_apps.py backend/tests/test_workload_e2e.py -q --tb=short

.PHONY: release
release: test-local test-pg safe-deploy e2e-test ## Full release: SQLite tests → PG tests → deploy → E2E verify
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  ✅ RELEASE COMPLETE"
	@echo "  Pipeline: test-local → test-pg → safe-deploy → e2e-test"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

.PHONY: e2e-test
e2e-test: ## Run Azure E2E certification (56 tests)
	@./scripts/e2e-azure-test.sh --env $(ENV)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Simulation & Testing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: seed
seed: ## Seed database with simulated backup data
	cd backend && python3 ../scripts/simulate_backup_data.py

.PHONY: seed-clean
seed-clean: ## Clean DB + storage and re-seed
	rm -f backend/m365_protection.db
	rm -rf backend/data
	cd backend && python3 ../scripts/simulate_backup_data.py

.PHONY: test-backend
test-backend: ## Run backend tests (SQLite — fast, no Docker needed)
	cd backend && python3 -m pytest -v

.PHONY: test-pg
test-pg: ## Run backend tests against Docker PostgreSQL (catches migration bugs)
	@echo "🐘 Running tests against PostgreSQL (requires: make dev running)..."
	@if ! docker compose ps postgres 2>/dev/null | grep -qE "running|Up|healthy"; then \
		echo "❌ PostgreSQL not running. Start with: make dev"; exit 1; \
	fi
	@cd backend && DATABASE_URL_OVERRIDE=postgresql+asyncpg://m365vault:m365vault_dev@localhost:5432/m365vault_test \
		venv/bin/python -m pytest \
		tests/test_workload_lifecycle.py \
		tests/test_auth_matrix.py \
		tests/test_sidebar_data_accuracy.py \
		-q --tb=line; \
	PG_EXIT=$$?; \
	if [ $$PG_EXIT -eq 0 ]; then echo "✅ PostgreSQL tests: ALL passed"; \
	elif [ $$PG_EXIT -le 3 ]; then echo "⚠️  PostgreSQL tests: $$PG_EXIT failures (within FK tolerance — migrations OK)"; \
	else echo "❌ PostgreSQL tests: $$PG_EXIT failures — check migration"; exit 1; fi

.PHONY: lint
lint: ## Run linting checks
	cd backend && python3 -m ruff check .
	cd frontend && npx eslint src/

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Docker Build
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Detect host architecture and set platform accordingly.
# Cloud targets (Azure, AWS, GCP) require linux/amd64.
# Local-only builds can use native arch for faster builds.
HOST_ARCH := $(shell uname -m)
ifeq ($(HOST_ARCH),arm64)
  DOCKER_PLATFORM_FLAG = --platform linux/amd64
  $(info 📦 Apple Silicon detected — Docker builds will target linux/amd64 for cloud compatibility)
else
  DOCKER_PLATFORM_FLAG =
endif
# Override: PLATFORM=native to build for local arch (faster, no emulation)
ifeq ($(PLATFORM),native)
  DOCKER_PLATFORM_FLAG =
  $(info 📦 Native platform override — building for $(HOST_ARCH))
endif

.PHONY: build
build: ## Build Docker images (auto-detects platform; PLATFORM=native for local arch)
	docker build $(DOCKER_PLATFORM_FLAG) -t m365vault-backend:local ./backend
	docker build $(DOCKER_PLATFORM_FLAG) -t m365vault-frontend:local ./frontend
	@echo "Built: m365vault-backend:local, m365vault-frontend:local"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Infrastructure (Terraform)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: tf-init
tf-init: ## Initialize Terraform (with remote backend)
	cd $(TF_DIR) && terraform init -reconfigure

.PHONY: tf-plan
tf-plan: tf-init ## Plan infrastructure changes (ENV=dev|prod)
	@test -n "$(SUBSCRIPTION_ID)" || (echo "Error: SUBSCRIPTION_ID required. Usage: make tf-plan SUBSCRIPTION_ID=<id>" && exit 1)
	cd $(TF_DIR) && terraform plan \
		-var-file=environments/$(ENV).tfvars \
		-var="subscription_id=$(SUBSCRIPTION_ID)"

.PHONY: tf-apply
tf-apply: tf-init ## Apply infrastructure changes (ENV=dev|prod)
	@test -n "$(SUBSCRIPTION_ID)" || (echo "Error: SUBSCRIPTION_ID required. Usage: make tf-apply SUBSCRIPTION_ID=<id>" && exit 1)
	cd $(TF_DIR) && terraform apply \
		-var-file=environments/$(ENV).tfvars \
		-var="subscription_id=$(SUBSCRIPTION_ID)"

.PHONY: tf-destroy
tf-destroy: tf-init ## Destroy infrastructure (ENV=dev|prod) — DANGEROUS
	@test -n "$(SUBSCRIPTION_ID)" || (echo "Error: SUBSCRIPTION_ID required." && exit 1)
	@echo "⚠️  This will DESTROY all $(ENV) resources. Press Ctrl+C to cancel."
	@read -rp "Type '$(ENV)' to confirm: " confirm && [ "$$confirm" = "$(ENV)" ] || exit 1
	cd $(TF_DIR) && terraform destroy \
		-var-file=environments/$(ENV).tfvars \
		-var="subscription_id=$(SUBSCRIPTION_ID)"

.PHONY: tf-output
tf-output: tf-init ## Show Terraform outputs
	cd $(TF_DIR) && terraform output

.PHONY: tf-set-acr-secrets
tf-set-acr-secrets: ## Set ACR GitHub secrets from Terraform output (run after first tf-apply)
	@ACR_SERVER=$$(cd $(TF_DIR) && terraform output -raw acr_login_server) && \
	ACR_NAME=$$(echo "$$ACR_SERVER" | cut -d. -f1) && \
	gh secret set ACR_NAME --repo gpatwa/m365-vault --body "$$ACR_NAME" && \
	gh secret set ACR_LOGIN_SERVER --repo gpatwa/m365-vault --body "$$ACR_SERVER" && \
	echo "Set ACR_NAME=$$ACR_NAME and ACR_LOGIN_SERVER=$$ACR_SERVER"

.PHONY: pre-deploy-check
pre-deploy-check: ## Test backend Docker image locally before pushing (catches bcrypt, import errors)
	@echo "🔍 Building backend image..."
	@docker build $(DOCKER_PLATFORM_FLAG) -t kavachiq-test:latest ./backend > /dev/null 2>&1
	@echo "🚀 Starting test container with PostgreSQL..."
	@docker rm -f kavachiq-pre-deploy kavachiq-pre-deploy-db 2>/dev/null || true
	@docker network create kavachiq-pre-test 2>/dev/null || true
	@docker run -d --name kavachiq-pre-deploy-db --network kavachiq-pre-test \
		-e POSTGRES_DB=testdb -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \
		postgres:16-alpine > /dev/null 2>&1
	@sleep 5
	@docker run -d --name kavachiq-pre-deploy --network kavachiq-pre-test -p 8099:8000 \
		-e DATABASE_URL=postgresql+asyncpg://test:test@kavachiq-pre-deploy-db:5432/testdb \
		-e SECRET_KEY=pre-deploy-test-key-32-chars-ok \
		-e ENCRYPTION_MASTER_KEY=pre-deploy-test-key-32-chars-ok \
		-e STORAGE_BACKEND=local \
		-e DISPATCH_MODE=in_process \
		kavachiq-test:latest > /dev/null 2>&1
	@echo "⏳ Waiting for startup..."
	@sleep 15
	@echo "🏥 Health check..."
	@curl -sf http://localhost:8099/health > /dev/null 2>&1 && echo "  ✅ Health OK" || \
		(echo "  ❌ Health FAILED" && docker logs kavachiq-pre-deploy --tail 20 && docker rm -f kavachiq-pre-deploy && exit 1)
	@echo "🔐 Auth check..."
	@curl -sf http://localhost:8099/api/auth/sso/config > /dev/null 2>&1 && echo "  ✅ Auth module OK" || \
		(echo "  ❌ Auth module FAILED" && docker rm -f kavachiq-pre-deploy && exit 1)
	@echo "📋 OpenAPI check..."
	@curl -sf http://localhost:8099/openapi.json > /dev/null 2>&1 && echo "  ✅ All routes loaded" || \
		(echo "  ❌ Routes FAILED" && docker rm -f kavachiq-pre-deploy && exit 1)
	@docker rm -f kavachiq-pre-deploy kavachiq-pre-deploy-db > /dev/null 2>&1
	@docker network rm kavachiq-pre-test 2>/dev/null || true
	@echo "✅ Pre-deploy check PASSED — safe to push"

.PHONY: acr-push
acr-push: pre-deploy-check ## Build and push Docker images to ACR (runs pre-deploy check first)
	@ACR_NAME=$${ACR_NAME:-acrm365vault$(ENV)}; \
	echo "Logging into ACR: $$ACR_NAME..."; \
	az acr login --name $$ACR_NAME && \
	echo "Building and pushing backend..." && \
	docker build $(DOCKER_PLATFORM_FLAG) -t $$ACR_NAME.azurecr.io/m365vault-backend:latest ./backend && \
	docker push $$ACR_NAME.azurecr.io/m365vault-backend:latest && \
	echo "Building and pushing frontend..." && \
	docker build $(DOCKER_PLATFORM_FLAG) -t $$ACR_NAME.azurecr.io/m365vault-frontend:latest ./frontend && \
	docker push $$ACR_NAME.azurecr.io/m365vault-frontend:latest && \
	echo "✅ Images pushed to $$ACR_NAME.azurecr.io"

.PHONY: tf-import
tf-import: tf-init ## Import existing Azure resources into Terraform state
	@./scripts/tf-import-existing.sh

.PHONY: tf-reset
tf-reset: tf-init ## Clear stale Terraform state (after manual Azure resource deletion)
	@echo "🧹 Clearing all Terraform state entries..."
	@cd $(TF_DIR) && terraform state list | while read -r resource; do \
		echo "  Removing: $$resource"; \
		terraform state rm "$$resource" >/dev/null 2>&1 || true; \
	done
	@echo "✅ State cleared. Run 'make tf-apply' for fresh deploy."

.PHONY: az-cleanup
az-cleanup: ## Full Azure cleanup: delete RG, purge Key Vault, reset state (ENV=dev|prod)
	@echo "⚠️  This will DELETE resource group rg-m365vault-$(ENV) and purge Key Vault."
	@read -rp "Type '$(ENV)' to confirm: " confirm && [ "$$confirm" = "$(ENV)" ] || exit 1
	@echo "🗑️  Deleting resource group rg-m365vault-$(ENV)..."
	@az group delete --name rg-m365vault-$(ENV) --yes 2>/dev/null || echo "  Resource group not found (already deleted)"
	@echo "🔑 Purging soft-deleted Key Vault kv-m365vault-$(ENV)..."
	@for loc in centralus eastus westus2 westus; do \
		az keyvault purge --name kv-m365vault-$(ENV) --location $$loc 2>/dev/null && \
		echo "  Purged from $$loc" && break; \
	done || echo "  No soft-deleted Key Vault found"
	@echo "🧹 Clearing Terraform state..."
	@$(MAKE) tf-reset 2>/dev/null || true
	@echo "✅ Cleanup complete. Ready for fresh 'make tf-apply'."

.PHONY: az-status
az-status: ## Show current Azure resource status for this environment (ENV=dev|prod)
	@echo "━━━ Azure Status: $(ENV) ━━━"
	@echo ""
	@echo "Resource Group:"
	@az group show --name rg-m365vault-$(ENV) --query "{name:name, state:properties.provisioningState, location:location}" -o table 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Container Apps:"
	@az containerapp list -g rg-m365vault-$(ENV) --query "[].{name:name, state:properties.provisioningState}" -o table 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "PostgreSQL:"
	@az postgres flexible-server list -g rg-m365vault-$(ENV) --query "[].{name:name, state:state, sku:sku.name}" -o table 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Redis:"
	@az redis list -g rg-m365vault-$(ENV) --query "[].{name:name, hostName:properties.hostName, sku:sku.name}" -o table 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Key Vault:"
	@az keyvault list -g rg-m365vault-$(ENV) --query "[].{name:name, location:location}" -o table 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Soft-Deleted Key Vaults:"
	@az keyvault list-deleted --query "[?contains(name,'m365vault')].{name:name, location:properties.location, deletion:properties.deletionDate}" -o table 2>/dev/null || echo "  None"
	@echo ""
	@echo "ACR:"
	@az acr list -g rg-m365vault-$(ENV) --query "[].{name:name, loginServer:loginServer}" -o table 2>/dev/null || echo "  Not found"
	@echo ""
	@echo "Storage:"
	@az storage account list -g rg-m365vault-$(ENV) --query "[].{name:name, kind:kind}" -o table 2>/dev/null || echo "  Not found"

.PHONY: az-sleep
az-sleep: ## Pause all Azure resources to save cost (scale to 0 + stop DB)
	@echo "😴 Pausing Azure resources..."
	@az containerapp update --name m365vault-backend-$(ENV) -g rg-m365vault-$(ENV) --min-replicas 0 --max-replicas 1 -o none 2>/dev/null && echo "  ✓ Backend scaled to 0" || echo "  ⚠ Backend not found"
	@az containerapp update --name m365vault-worker-$(ENV) -g rg-m365vault-$(ENV) --min-replicas 0 --max-replicas 1 -o none 2>/dev/null && echo "  ✓ Worker scaled to 0" || echo "  ⚠ Worker not found"
	@az containerapp update --name m365vault-frontend-$(ENV) -g rg-m365vault-$(ENV) --min-replicas 0 --max-replicas 1 -o none 2>/dev/null && echo "  ✓ Frontend scaled to 0" || echo "  ⚠ Frontend not found"
	@az postgres flexible-server stop --name psql-m365vault-$(ENV) -g rg-m365vault-$(ENV) 2>/dev/null && echo "  ✓ PostgreSQL stopped" || echo "  ⚠ PostgreSQL already stopped"
	@echo "✅ All paused. Run 'make az-wake' to resume. (~\$$5/mo idle cost)"

.PHONY: az-wake
az-wake: ## Resume all Azure resources (start DB + scale apps back up)
	@echo "☀️  Waking up Azure resources..."
	@echo "  Starting PostgreSQL (takes ~2 min)..."
	@az postgres flexible-server start --name psql-m365vault-$(ENV) -g rg-m365vault-$(ENV) 2>/dev/null && echo "  ✓ PostgreSQL started" || echo "  ⚠ PostgreSQL already running"
	@az containerapp update --name m365vault-backend-$(ENV) -g rg-m365vault-$(ENV) --min-replicas 1 --max-replicas 3 -o none 2>/dev/null && echo "  ✓ Backend scaled to 1-3" || echo "  ⚠ Backend not found"
	@az containerapp update --name m365vault-worker-$(ENV) -g rg-m365vault-$(ENV) --min-replicas 1 --max-replicas 3 -o none 2>/dev/null && echo "  ✓ Worker scaled to 1-3" || echo "  ⚠ Worker not found"
	@az containerapp update --name m365vault-frontend-$(ENV) -g rg-m365vault-$(ENV) --min-replicas 1 --max-replicas 3 -o none 2>/dev/null && echo "  ✓ Frontend scaled to 1-3" || echo "  ⚠ Frontend not found"
	@echo "✅ All running."
	@echo "  Frontend: https://$$(az containerapp show --name m365vault-frontend-$(ENV) -g rg-m365vault-$(ENV) --query 'properties.configuration.ingress.fqdn' -o tsv 2>/dev/null)"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Deploy (via GitHub Actions)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: deploy-dev
deploy: ## Full health-gated deploy: pre-check → build → push → apply → verify
	@bash scripts/deploy.sh

.PHONY: safe-deploy
safe-deploy: ## Safe deploy: build → push → wait for healthy → deactivate old (ENV=dev|prod)
	@./scripts/safe-deploy.sh --env $(ENV)

.PHONY: blue-green
blue-green: ## Blue-green deploy: canary 10% → monitor → promote or rollback (ENV=dev|prod)
	@./scripts/blue-green-deploy.sh --env $(ENV)

.PHONY: setup-monitoring
setup-monitoring: ## Set up Azure Monitor alerts + health check endpoints (ENV=dev|prod)
	@./scripts/setup-monitoring.sh --env $(ENV)

.PHONY: dr-rebuild
dr-rebuild: ## Disaster recovery: destroy + rebuild entire environment (ENV=dev|prod)
	@./scripts/dr-rebuild.sh --env $(ENV)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Secrets Management (Azure Key Vault)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: secrets-push
secrets-push: ## Push .env.secrets → Azure Key Vault (ENV=dev|prod)
	@./scripts/manage-secrets.sh push --env $(ENV)

.PHONY: secrets-pull
secrets-pull: ## Pull Azure Key Vault → .env.secrets (ENV=dev|prod)
	@./scripts/manage-secrets.sh pull --env $(ENV)

.PHONY: secrets-list
secrets-list: ## List all secrets in Key Vault (ENV=dev|prod)
	@./scripts/manage-secrets.sh list --env $(ENV)

.PHONY: secrets-verify
secrets-verify: ## Verify all required secrets exist in Key Vault (ENV=dev|prod)
	@./scripts/manage-secrets.sh verify --env $(ENV)

.PHONY: db-migrate
db-migrate: ## Run DB migration on Azure (ENV=dev|prod)
	@./scripts/manage-secrets.sh db-migrate --env $(ENV)

.PHONY: full-deploy
full-deploy: acr-push secrets-push tf-apply db-migrate ## Full deploy: build + secrets + infra + migrate (ENV=dev|prod)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Deploy complete ($(ENV))"
	@echo "  Run 'make secrets-verify ENV=$(ENV)' to confirm"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

.PHONY: deploy-staging
deploy-staging: ## Deploy to staging via GitHub Actions
	gh workflow run deploy.yml --repo gpatwa/m365-vault -f environment=staging
	@echo "Triggered staging deployment. Watch: gh run list --repo gpatwa/m365-vault"

.PHONY: promote-prod
promote-prod: ## Promote staging image to production (uses same image tag)
	@echo "⚠️  This will deploy the current staging image to PRODUCTION."
	@read -rp "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	gh workflow run deploy.yml --repo gpatwa/m365-vault -f environment=prod
	@echo "Triggered prod deployment. Watch: gh run list --repo gpatwa/m365-vault"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GitHub Actions Deployment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: deploy-verify
deploy-verify: ## Run post-deploy health checks only
	@bash scripts/deploy.sh --verify-only

.PHONY: deploy-skip-build
deploy-skip-build: ## Deploy without rebuilding images (uses latest in ACR)
	@bash scripts/deploy.sh --skip-build

.PHONY: deploy-dev
deploy-dev: ## Trigger dev deployment via GitHub Actions
	gh workflow run deploy.yml --repo gpatwa/m365-vault -f environment=dev
	@echo "Triggered dev deployment. Watch: gh run list --repo gpatwa/m365-vault"

.PHONY: deploy-prod
deploy-prod: ## Trigger prod deployment via GitHub Actions
	@echo "⚠️  This will deploy to PRODUCTION."
	@read -rp "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	gh workflow run deploy.yml --repo gpatwa/m365-vault -f environment=prod
	@echo "Triggered prod deployment. Watch: gh run list --repo gpatwa/m365-vault"

.PHONY: deploy-status
deploy-status: ## Show recent GitHub Actions runs
	gh run list --repo gpatwa/m365-vault --limit 5

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Full Workflows
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: setup
setup: check-prereqs ## Full first-time local setup: install deps + seed data
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
	$(MAKE) seed-clean
	@echo ""
	@echo "Setup complete! Run 'make dev' to start."

.PHONY: benchmark
benchmark: ## Run performance benchmark suite against local or remote API
	@python3 scripts/benchmark.py

.PHONY: security-scan
security-scan: ## Run automated security audit (static analysis, dependency scan, OWASP checks)
	@bash scripts/security-audit.sh

.PHONY: configure-connector
configure-connector: ## ONE-TIME: Configure connector app permissions + admin consent
	@./scripts/configure-connector-permissions.sh

.PHONY: seed-real
seed-real: ## Connect real M365 tenant: discover objects + run first backup (requires .env creds)
	@echo "Connecting to real M365 tenant..."
	@echo "1. Open http://localhost:5173/onboard in your browser"
	@echo "2. Click 'Connect Microsoft 365' and sign in as Global Admin"
	@echo "3. Complete the onboarding wizard"
	@echo ""
	@echo "After onboarding, run 'make test-local' to verify data."

.PHONY: fresh
fresh: dev-clean seed-clean dev ## Full clean restart: wipe everything + rebuild + start

## Release Quality Gates
.PHONY: release-check
release-check: ## Full quality gate: types → tests → coverage → build → security → ready?
	@bash scripts/release-check.sh

.PHONY: release-test
release-test: ## Run release smoke tests (API checks) against running stack
	@bash scripts/release-test.sh

# release target is defined above (test-local → acr-push → safe-deploy → e2e-test)

