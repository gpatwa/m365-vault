# ──────────────────────────────────────────────────────────────────────
# M365 Vault — Unified Task Runner
# ──────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
SHELL := /bin/bash

# ── Variables ────────────────────────────────────────────────────────
DOCKER_COMPOSE = docker compose
TF_DIR         = infra
ENV           ?= dev

# ── Help ─────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@echo ""
	@echo "M365 Vault — Available Commands"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
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
test-backend: ## Run backend tests
	cd backend && python3 -m pytest -v

.PHONY: lint
lint: ## Run linting checks
	cd backend && python3 -m ruff check .
	cd frontend && npx eslint src/

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Docker Build
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: build
build: ## Build Docker images locally
	docker build -t m365vault-backend:local ./backend
	docker build -t m365vault-frontend:local ./frontend
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Deploy (via GitHub Actions)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

.PHONY: fresh
fresh: dev-clean seed-clean dev ## Full clean restart: wipe everything + rebuild + start
