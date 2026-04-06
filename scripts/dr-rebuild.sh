#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Disaster Recovery Rebuild
#
# One command, zero manual steps, ~15 min total.
# Destroys and recreates the entire Azure environment from scratch.
#
# Usage:
#   ./scripts/dr-rebuild.sh [--env dev|prod]
#   make dr-rebuild ENV=dev
#
# Prerequisites:
#   - Azure CLI logged in (az login)
#   - .env.secrets file exists with all API keys
#   - Docker running (for image builds)
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
step()  { echo -e "\n${CYAN}[STEP]${NC}  $*"; }

ENV="${1:-dev}"
[[ "$1" == "--env" ]] && ENV="${2:-dev}"

RG="rg-m365vault-${ENV}"
VAULT="kv-m365vault-${ENV}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

echo ""
echo -e "${RED}═══ DISASTER RECOVERY REBUILD (ENV=${ENV}) ═══${NC}"
echo -e "${RED}This will DESTROY all resources in ${RG} and rebuild from scratch.${NC}"
echo ""
read -rp "Type '${ENV}' to confirm: " confirm
[ "$confirm" = "$ENV" ] || { echo "Aborted."; exit 1; }

# ── Step 1: Delete resource group ──
step "1/8 Deleting resource group ${RG}..."
az group delete --name "$RG" --yes --no-wait 2>/dev/null || warn "RG not found"
info "Waiting for deletion..."
while az group show --name "$RG" &>/dev/null 2>&1; do
  sleep 10
  echo -n "."
done
ok "Resource group deleted"

# ── Step 2: Purge Key Vault ──
step "2/8 Purging Key Vault ${VAULT}..."
az keyvault purge --name "$VAULT" 2>/dev/null || warn "KV not found or already purged"
ok "Key Vault purged"

# ── Step 3: Clear Terraform state ──
step "3/8 Clearing Terraform state..."
az storage blob lease break --blob-name "m365vault.terraform.tfstate" \
  --container-name "tfstate" --account-name "stm365vaulttfstate" 2>/dev/null || true
cd infra
for r in $(terraform state list 2>/dev/null); do
  terraform state rm "$r" 2>/dev/null || true
done
ok "State cleared"

# ── Step 4: Terraform apply (creates everything) ──
step "4/8 Terraform apply (creating all resources)..."
terraform init -reconfigure \
  -backend-config="resource_group_name=rg-m365vault-tfstate" \
  -backend-config="storage_account_name=stm365vaulttfstate" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=m365vault.terraform.tfstate" > /dev/null 2>&1

terraform apply \
  -var-file="environments/${ENV}.tfvars" \
  -var="subscription_id=${SUBSCRIPTION_ID}" \
  -var="connector_app_id=$(grep CONNECTOR_APP_ID ../.env.secrets | cut -d= -f2)" \
  -var="posthog_api_key=$(grep POSTHOG_API_KEY ../.env.secrets | cut -d= -f2)" \
  -auto-approve 2>&1 | tail -5
ok "Infrastructure created"
cd ..

# ── Step 5: Push Docker images ──
step "5/8 Building and pushing Docker images..."
ACR="acrm365vault${ENV}"
az acr login --name "$ACR" > /dev/null 2>&1
docker build --platform linux/amd64 -q -t "$ACR.azurecr.io/m365vault-backend:latest" ./backend > /dev/null
docker push "$ACR.azurecr.io/m365vault-backend:latest" > /dev/null 2>&1
docker build --platform linux/amd64 -q -t "$ACR.azurecr.io/m365vault-frontend:latest" ./frontend > /dev/null
docker push "$ACR.azurecr.io/m365vault-frontend:latest" > /dev/null 2>&1
ok "Images pushed"

# ── Step 6: Push secrets to Key Vault ──
step "6/8 Pushing secrets to Key Vault..."
./scripts/manage-secrets.sh push --env "$ENV" 2>&1 | tail -2
ok "Secrets pushed"

# ── Step 7: Wait for backend healthy ──
step "7/8 Waiting for backend to be healthy..."
BACKEND_FQDN=$(cd infra && terraform output -raw backend_fqdn 2>/dev/null)
for i in $(seq 1 30); do
  HEALTH=$(curl -sf --max-time 10 "https://$BACKEND_FQDN/health" 2>/dev/null || echo "")
  if echo "$HEALTH" | grep -q '"healthy"'; then
    ok "Backend healthy"
    break
  fi
  [ $i -eq 30 ] && fail "Backend not healthy after 5 min"
  sleep 10
done

# ── Step 8: Run E2E verification ──
step "8/8 Running E2E certification..."
./scripts/e2e-azure-test.sh --env "$ENV" 2>&1 | tail -5

echo ""
echo -e "${GREEN}═══ DISASTER RECOVERY COMPLETE ═══${NC}"
echo -e "  Backend:  https://$BACKEND_FQDN"
echo -e "  Frontend: $(cd infra && terraform output -raw frontend_url 2>/dev/null)"
echo ""
echo -e "${YELLOW}Manual steps remaining:${NC}"
echo "  1. Bind custom domains (api.kavachiq.com, app.kavachiq.com, kavachiq.com)"
echo "  2. Update Cloudflare DNS CNAMEs if FQDN changed"
echo "  3. Re-enable Cloudflare proxy on all CNAMEs"
echo ""
