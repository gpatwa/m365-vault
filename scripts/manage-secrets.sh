#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Secrets Management (Azure Key Vault)
#
# Single source of truth: .env.secrets → Azure Key Vault → Container Apps
#
# Commands:
#   ./scripts/manage-secrets.sh push [--env dev|prod]
#   ./scripts/manage-secrets.sh pull [--env dev|prod]
#   ./scripts/manage-secrets.sh list [--env dev|prod]
#   ./scripts/manage-secrets.sh verify [--env dev|prod]
#   ./scripts/manage-secrets.sh db-migrate [--env dev|prod]
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

# ── Parse arguments
COMMAND="${1:-help}"
shift || true

ENV="dev"
while [ $# -gt 0 ]; do
  case $1 in
    --env) ENV="$2"; shift 2 ;;
    *) shift ;;
  esac
done

VAULT_NAME="kv-m365vault-${ENV}"
SECRETS_FILE=".env.secrets"

# ── Secret mapping: env_key:vault_name (portable, no associative arrays)
SECRET_PAIRS="
STRIPE_SECRET_KEY:stripe-secret-key
STRIPE_WEBHOOK_SECRET:stripe-webhook-secret
STRIPE_PUBLISHABLE_KEY:stripe-publishable-key
STRIPE_PRICE_PROFESSIONAL:stripe-price-professional
STRIPE_PRICE_BUSINESS:stripe-price-business
STRIPE_PRICE_ENTERPRISE:stripe-price-enterprise
RESEND_API_KEY:resend-api-key
CONNECTOR_APP_ID:connector-app-id
CONNECTOR_APP_SECRET:connector-app-secret
POSTHOG_API_KEY:posthog-api-key
"

REQUIRED_SECRETS="STRIPE_SECRET_KEY RESEND_API_KEY CONNECTOR_APP_ID CONNECTOR_APP_SECRET"

# ── Helpers
get_vault_name() {
  local env_key="$1"
  echo "$SECRET_PAIRS" | grep "^${env_key}:" | cut -d: -f2 | tr -d ' '
}

check_azure() {
  az account show &>/dev/null || fail "Not logged into Azure. Run: az login"
  az keyvault show --name "$VAULT_NAME" &>/dev/null || fail "Key Vault '$VAULT_NAME' not found. Run: make tf-apply"
}

# ── Commands

cmd_push() {
  check_azure
  [ -f "$SECRETS_FILE" ] || fail ".env.secrets not found. Run: cp .env.secrets.example .env.secrets"

  step "Pushing secrets from $SECRETS_FILE → $VAULT_NAME"
  local count=0

  while IFS= read -r line; do
    # Skip comments and empty lines
    case "$line" in
      ""|\#*) continue ;;
    esac

    local key="${line%%=*}"
    local value="${line#*=}"
    key="$(echo "$key" | tr -d ' ')"
    value="$(echo "$value" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"

    [ -z "$key" ] || [ -z "$value" ] && continue
    echo "$value" | grep -q "CHANGEME" && { warn "Skipping $key (CHANGEME placeholder)"; continue; }

    local vault_name
    vault_name="$(get_vault_name "$key")"
    [ -z "$vault_name" ] && continue

    if az keyvault secret set --vault-name "$VAULT_NAME" --name "$vault_name" --value "$value" --output none 2>/dev/null; then
      ok "$key → $vault_name"
      count=$((count + 1))
    else
      warn "Failed to set $vault_name"
    fi
  done < "$SECRETS_FILE"

  echo ""
  ok "Pushed $count secrets to $VAULT_NAME"
}

cmd_pull() {
  check_azure

  step "Pulling secrets from $VAULT_NAME → $SECRETS_FILE"

  if [ ! -f "$SECRETS_FILE" ]; then
    cp .env.secrets.example "$SECRETS_FILE"
    info "Created $SECRETS_FILE from template"
  fi

  local count=0
  for pair in $SECRET_PAIRS; do
    [ -z "$pair" ] && continue
    local env_key="${pair%%:*}"
    local vault_name="${pair##*:}"

    local value
    value="$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$vault_name" --query value -o tsv 2>/dev/null || echo "")"

    if [ -n "$value" ] && [ "$value" != "not-configured" ]; then
      if grep -q "^${env_key}=" "$SECRETS_FILE" 2>/dev/null; then
        sed -i.bak "s|^${env_key}=.*|${env_key}=${value}|" "$SECRETS_FILE"
        rm -f "${SECRETS_FILE}.bak"
      else
        echo "${env_key}=${value}" >> "$SECRETS_FILE"
      fi
      ok "$vault_name → $env_key"
      count=$((count + 1))
    fi
  done

  echo ""
  ok "Pulled $count secrets from $VAULT_NAME"
}

cmd_list() {
  check_azure
  step "Secrets in $VAULT_NAME:"
  echo ""
  az keyvault secret list --vault-name "$VAULT_NAME" \
    --query "[].{Name:name, Enabled:attributes.enabled}" -o table
}

cmd_verify() {
  check_azure
  step "Verifying secrets in $VAULT_NAME"
  echo ""

  local missing=0

  # App secrets
  for pair in $SECRET_PAIRS; do
    [ -z "$pair" ] && continue
    local env_key="${pair%%:*}"
    local vault_name="${pair##*:}"
    local is_required=false
    for req in $REQUIRED_SECRETS; do
      [ "$req" = "$env_key" ] && is_required=true
    done

    local value
    value="$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$vault_name" --query value -o tsv 2>/dev/null || echo "")"

    if [ -n "$value" ] && [ "$value" != "not-configured" ]; then
      ok "$vault_name"
    elif $is_required; then
      echo -e "  ${RED}[MISS]${NC}  $vault_name — ${RED}REQUIRED${NC}"
      missing=$((missing + 1))
    else
      echo -e "  ${YELLOW}[----]${NC}  $vault_name — optional"
    fi
  done

  # Infra secrets
  echo ""
  step "Infrastructure secrets (Terraform-managed):"
  for name in secret-key encryption-master-key database-url storage-connection-string; do
    local value
    value="$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$name" --query value -o tsv 2>/dev/null || echo "")"
    if [ -n "$value" ]; then
      ok "$name"
    else
      echo -e "  ${RED}[MISS]${NC}  $name"
      missing=$((missing + 1))
    fi
  done

  echo ""
  if [ "$missing" -eq 0 ]; then
    ok "All secrets verified!"
  else
    warn "$missing secrets missing"
    exit 1
  fi
}

cmd_db_migrate() {
  check_azure
  local rg="rg-m365vault-${ENV}"
  local app="m365vault-backend-${ENV}"

  step "Running DB migration on Azure (ENV=$ENV)"
  info "Using container exec on $app..."

  az containerapp exec \
    --resource-group "$rg" \
    --name "$app" \
    --command "python3 -c \"
import asyncio
from app.database import engine, Base
async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Migration complete')
asyncio.run(migrate())
\"" 2>&1 || {
    warn "Container exec failed. Run migration manually:"
    info "  az containerapp exec --resource-group $rg --name postgres-$ENV --command psql -- -U m365vault_admin -d m365vault"
    info "  Then run: backend/migrations/003_restore_permissions.sql"
  }
}

cmd_help() {
  echo ""
  echo -e "${CYAN}KavachIQ — Secrets Management${NC}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Commands:"
  echo "  push       Push .env.secrets → Azure Key Vault"
  echo "  pull       Pull Azure Key Vault → .env.secrets"
  echo "  list       List all secrets in Key Vault"
  echo "  verify     Verify all required secrets exist"
  echo "  db-migrate Run DB migration on Azure"
  echo ""
  echo "Options:"
  echo "  --env dev|prod   Target environment (default: dev)"
  echo ""
  echo "Workflow:"
  echo "  1. cp .env.secrets.example .env.secrets"
  echo "  2. Fill in real values"
  echo "  3. make secrets-push"
  echo "  4. make full-deploy"
  echo ""
}

# ── Dispatch
case "$COMMAND" in
  push)       cmd_push ;;
  pull)       cmd_pull ;;
  list)       cmd_list ;;
  verify)     cmd_verify ;;
  db-migrate) cmd_db_migrate ;;
  help|*)     cmd_help ;;
esac
