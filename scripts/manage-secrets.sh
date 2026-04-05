#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Secrets Management (Azure Key Vault)
#
# Single source of truth: .env.secrets → Azure Key Vault → Container Apps
#
# Commands:
#   ./scripts/manage-secrets.sh push [--env dev|prod]   Push .env.secrets → Key Vault
#   ./scripts/manage-secrets.sh pull [--env dev|prod]   Pull Key Vault → .env.secrets
#   ./scripts/manage-secrets.sh list [--env dev|prod]   List secrets in Key Vault
#   ./scripts/manage-secrets.sh verify [--env dev|prod] Verify all required secrets exist
#   ./scripts/manage-secrets.sh migrate-entra           Update Entra app redirect URI
#   ./scripts/manage-secrets.sh setup-stripe-webhook    Create Stripe webhook endpoint
#   ./scripts/manage-secrets.sh db-migrate [--env dev|prod] Run DB migration on Azure
#
# Usage via Makefile:
#   make secrets-push          Push secrets to dev Key Vault
#   make secrets-pull          Pull secrets from dev Key Vault
#   make secrets-verify        Verify all secrets exist
#   make deploy                Full deploy: build + push + secrets + terraform + migrate
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

# ── Parse arguments ─────────────────────────────────────────────────
COMMAND="${1:-help}"
shift || true

ENV="dev"
while [[ $# -gt 0 ]]; do
  case $1 in
    --env) ENV="$2"; shift 2 ;;
    *) shift ;;
  esac
done

VAULT_NAME="kv-m365vault-${ENV}"
SECRETS_FILE=".env.secrets"
SECRETS_EXAMPLE=".env.secrets.example"

# ── Secret name mapping: .env key → Key Vault secret name ──────────
# Key Vault names must be alphanumeric + hyphens only
declare -A SECRET_MAP=(
  ["STRIPE_SECRET_KEY"]="stripe-secret-key"
  ["STRIPE_WEBHOOK_SECRET"]="stripe-webhook-secret"
  ["STRIPE_PUBLISHABLE_KEY"]="stripe-publishable-key"
  ["STRIPE_PRICE_PROFESSIONAL"]="stripe-price-professional"
  ["STRIPE_PRICE_BUSINESS"]="stripe-price-business"
  ["STRIPE_PRICE_ENTERPRISE"]="stripe-price-enterprise"
  ["RESEND_API_KEY"]="resend-api-key"
  ["CONNECTOR_APP_ID"]="connector-app-id"
  ["CONNECTOR_APP_SECRET"]="connector-app-secret"
  ["POSTHOG_API_KEY"]="posthog-api-key"
)

# These are the secrets that MUST exist for the app to function
REQUIRED_SECRETS=(
  "STRIPE_SECRET_KEY"
  "RESEND_API_KEY"
  "CONNECTOR_APP_ID"
  "CONNECTOR_APP_SECRET"
)

# ── Helpers ─────────────────────────────────────────────────────────
check_azure_login() {
  if ! az account show &>/dev/null; then
    fail "Not logged into Azure. Run: az login"
  fi
}

check_vault_exists() {
  if ! az keyvault show --name "$VAULT_NAME" &>/dev/null; then
    fail "Key Vault '$VAULT_NAME' not found. Run: make tf-apply (ENV=$ENV)"
  fi
}

load_env_file() {
  if [[ ! -f "$SECRETS_FILE" ]]; then
    fail ".env.secrets not found. Create it:\n  cp .env.secrets.example .env.secrets\n  # Fill in real values"
  fi
}

# ── Commands ────────────────────────────────────────────────────────

cmd_push() {
  check_azure_login
  check_vault_exists
  load_env_file

  step "Pushing secrets from $SECRETS_FILE → $VAULT_NAME"
  local count=0
  local failed=0

  while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    [[ -z "$key" || -z "$value" ]] && continue
    # Skip CHANGEME placeholders
    if [[ "$value" == *"CHANGEME"* ]]; then
      warn "Skipping $key (still has CHANGEME placeholder)"
      continue
    fi

    local vault_name="${SECRET_MAP[$key]:-}"
    if [[ -z "$vault_name" ]]; then
      warn "Skipping $key (not in secret map)"
      continue
    fi

    if az keyvault secret set --vault-name "$VAULT_NAME" --name "$vault_name" --value "$value" --output none 2>/dev/null; then
      ok "$key → $vault_name"
      ((count++))
    else
      warn "Failed to set $vault_name"
      ((failed++))
    fi
  done < "$SECRETS_FILE"

  echo ""
  if [[ $failed -eq 0 ]]; then
    ok "Pushed $count secrets to $VAULT_NAME"
  else
    warn "Pushed $count secrets, $failed failed"
  fi
}

cmd_pull() {
  check_azure_login
  check_vault_exists

  step "Pulling secrets from $VAULT_NAME → $SECRETS_FILE"

  # Start with the example file as template
  if [[ -f "$SECRETS_FILE" ]]; then
    warn "$SECRETS_FILE exists — will update values in place"
  else
    cp "$SECRETS_EXAMPLE" "$SECRETS_FILE"
    info "Created $SECRETS_FILE from example template"
  fi

  local count=0
  for env_key in "${!SECRET_MAP[@]}"; do
    local vault_name="${SECRET_MAP[$env_key]}"
    local value
    value=$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$vault_name" --query "value" -o tsv 2>/dev/null || echo "")

    if [[ -n "$value" && "$value" != "not-configured" ]]; then
      # Update the value in .env.secrets (macOS + Linux compatible sed)
      if grep -q "^${env_key}=" "$SECRETS_FILE" 2>/dev/null; then
        # Use a temp file for portability
        awk -v key="$env_key" -v val="$value" 'BEGIN{FS=OFS="="} $1==key{$2=val}1' "$SECRETS_FILE" > "${SECRETS_FILE}.tmp"
        mv "${SECRETS_FILE}.tmp" "$SECRETS_FILE"
      else
        echo "${env_key}=${value}" >> "$SECRETS_FILE"
      fi
      ok "$vault_name → $env_key"
      ((count++))
    else
      warn "$vault_name not found in Key Vault"
    fi
  done

  echo ""
  ok "Pulled $count secrets from $VAULT_NAME"
}

cmd_list() {
  check_azure_login
  check_vault_exists

  step "Secrets in $VAULT_NAME:"
  echo ""

  az keyvault secret list --vault-name "$VAULT_NAME" --query "[].{Name:name, Enabled:attributes.enabled, Updated:attributes.updated}" -o table
}

cmd_verify() {
  check_azure_login
  check_vault_exists

  step "Verifying required secrets in $VAULT_NAME"
  echo ""

  local missing=0
  local total=0

  for env_key in "${!SECRET_MAP[@]}"; do
    local vault_name="${SECRET_MAP[$env_key]}"
    local is_required=false
    for req in "${REQUIRED_SECRETS[@]}"; do
      [[ "$req" == "$env_key" ]] && is_required=true
    done

    local value
    value=$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$vault_name" --query "value" -o tsv 2>/dev/null || echo "")

    ((total++))
    if [[ -n "$value" && "$value" != "not-configured" ]]; then
      ok "$vault_name (${env_key})"
    elif $is_required; then
      fail_msg="MISSING (REQUIRED)"
      echo -e "  ${RED}[MISS]${NC}  $vault_name (${env_key}) — ${RED}REQUIRED${NC}"
      ((missing++))
    else
      echo -e "  ${YELLOW}[----]${NC}  $vault_name (${env_key}) — optional"
    fi
  done

  # Also check infra-managed secrets
  echo ""
  step "Infrastructure secrets (managed by Terraform):"
  for name in "secret-key" "encryption-master-key" "database-url" "storage-connection-string"; do
    local value
    value=$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$name" --query "value" -o tsv 2>/dev/null || echo "")
    if [[ -n "$value" ]]; then
      ok "$name"
    else
      echo -e "  ${RED}[MISS]${NC}  $name — run make tf-apply first"
      ((missing++))
    fi
  done

  echo ""
  if [[ $missing -eq 0 ]]; then
    ok "All secrets verified ($total app + 4 infra)"
  else
    fail "$missing secrets missing. Run: make secrets-push"
  fi
}

cmd_db_migrate() {
  check_azure_login

  step "Running DB migration on Azure (ENV=$ENV)"

  # Get the backend container app name
  local rg="rg-m365vault-${ENV}"
  local app="m365vault-backend-${ENV}"

  info "Executing migration via container exec..."
  az containerapp exec \
    --resource-group "$rg" \
    --name "$app" \
    --command "python3" -- -c "
import asyncio
from app.database import engine, Base

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Migration complete')

asyncio.run(migrate())
" 2>&1 || {
    warn "Container exec not available. Trying direct psql..."
    info "Upload and run: backend/migrations/003_restore_permissions.sql"
    info "Use: az containerapp exec --resource-group $rg --name postgres-$ENV --command psql -- -U m365vault_admin -d m365vault"
  }
}

cmd_help() {
  echo ""
  echo -e "${CYAN}KavachIQ — Secrets Management${NC}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Commands:"
  echo "  push     Push .env.secrets → Azure Key Vault"
  echo "  pull     Pull Azure Key Vault → .env.secrets"
  echo "  list     List all secrets in Key Vault"
  echo "  verify   Verify all required secrets exist"
  echo "  db-migrate  Run DB migration on Azure"
  echo ""
  echo "Options:"
  echo "  --env dev|prod   Target environment (default: dev)"
  echo ""
  echo "Workflow:"
  echo "  1. cp .env.secrets.example .env.secrets"
  echo "  2. Fill in real values"
  echo "  3. make secrets-push"
  echo "  4. make deploy"
  echo ""
}

# ── Dispatch ────────────────────────────────────────────────────────
case "$COMMAND" in
  push)       cmd_push ;;
  pull)       cmd_pull ;;
  list)       cmd_list ;;
  verify)     cmd_verify ;;
  db-migrate) cmd_db_migrate ;;
  help|*)     cmd_help ;;
esac
