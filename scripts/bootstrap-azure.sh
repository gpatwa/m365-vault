#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# M365 Vault — One-time Azure + GitHub bootstrap
#
# This script automates all manual first-time setup:
#   1. Creates an Azure service principal with OIDC for GitHub Actions
#   2. Creates Terraform remote state storage
#   3. Sets all required GitHub repository secrets
#   4. Enables Terraform remote backend
#
# Prerequisites:
#   - Azure CLI (az) installed and logged in
#   - GitHub CLI (gh) installed and authenticated
#   - jq installed
#
# Usage:
#   ./scripts/bootstrap-azure.sh                          # interactive
#   ./scripts/bootstrap-azure.sh --subscription <id>      # non-interactive
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ── Configuration ────────────────────────────────────────────────────
GITHUB_REPO="gpatwa/m365-vault"
SP_NAME="sp-m365vault-github"
TFSTATE_RG="rg-m365vault-tfstate"
TFSTATE_SA="stm365vaulttfstate"
TFSTATE_CONTAINER="tfstate"
LOCATION="eastus"

# ── Prerequisite checks ─────────────────────────────────────────────
for cmd in az gh jq; do
  command -v "$cmd" >/dev/null 2>&1 || fail "$cmd is required but not installed."
done

# Check Azure login
az account show >/dev/null 2>&1 || fail "Not logged in to Azure. Run: az login"

# Check GitHub login
gh auth status >/dev/null 2>&1 || fail "Not logged in to GitHub. Run: gh auth login"

# ── Parse arguments ─────────────────────────────────────────────────
SUBSCRIPTION_ID=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --subscription) SUBSCRIPTION_ID="$2"; shift 2 ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

# ── Get subscription ─────────────────────────────────────────────────
if [[ -z "$SUBSCRIPTION_ID" ]]; then
  echo ""
  info "Available Azure subscriptions:"
  az account list --output table --query "[].{Name:name, ID:id, Default:isDefault}"
  echo ""
  read -rp "Enter subscription ID (or press Enter for default): " SUBSCRIPTION_ID
  if [[ -z "$SUBSCRIPTION_ID" ]]; then
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
  fi
fi

az account set --subscription "$SUBSCRIPTION_ID"
TENANT_ID=$(az account show --query tenantId -o tsv)
ok "Using subscription: $SUBSCRIPTION_ID"
ok "Tenant: $TENANT_ID"

# ── Step 1: Create Service Principal ─────────────────────────────────
echo ""
info "Step 1/5: Creating service principal '$SP_NAME'..."

# Check if SP already exists
EXISTING_SP=$(az ad app list --display-name "$SP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)

if [[ -n "$EXISTING_SP" && "$EXISTING_SP" != "None" ]]; then
  CLIENT_ID="$EXISTING_SP"
  warn "Service principal already exists (appId: $CLIENT_ID). Reusing."
else
  SP_OUTPUT=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role Contributor \
    --scopes "/subscriptions/$SUBSCRIPTION_ID" \
    --query "{clientId:appId, clientSecret:password}" \
    -o json)
  CLIENT_ID=$(echo "$SP_OUTPUT" | jq -r .clientId)
  ok "Service principal created (appId: $CLIENT_ID)"
fi

# ── Step 2: Create OIDC Federated Credential ────────────────────────
echo ""
info "Step 2/5: Creating OIDC federated credential for GitHub Actions..."

APP_OBJECT_ID=$(az ad app show --id "$CLIENT_ID" --query id -o tsv)

# Federated credentials for main branch and pull requests
for CRED in "github-main:ref:refs/heads/main" "github-pr:pull_request"; do
  CRED_NAME="${CRED%%:*}"
  SUBJECT="repo:${GITHUB_REPO}:${CRED#*:}"

  EXISTING_CRED=$(az ad app federated-credential list --id "$APP_OBJECT_ID" \
    --query "[?name=='$CRED_NAME'].name" -o tsv 2>/dev/null || true)

  if [[ -n "$EXISTING_CRED" ]]; then
    warn "Federated credential '$CRED_NAME' already exists. Skipping."
  else
    az ad app federated-credential create --id "$APP_OBJECT_ID" \
      --parameters "{
        \"name\": \"$CRED_NAME\",
        \"issuer\": \"https://token.actions.githubusercontent.com\",
        \"subject\": \"$SUBJECT\",
        \"audiences\": [\"api://AzureADTokenExchange\"]
      }" >/dev/null
    ok "Created federated credential: $CRED_NAME ($SUBJECT)"
  fi
done

# ── Step 3: Create Terraform Remote State Storage ────────────────────
echo ""
info "Step 3/5: Creating Terraform remote state storage..."

# Resource group
if az group show -n "$TFSTATE_RG" >/dev/null 2>&1; then
  warn "Resource group '$TFSTATE_RG' already exists."
else
  az group create -n "$TFSTATE_RG" -l "$LOCATION" -o none
  ok "Created resource group: $TFSTATE_RG"
fi

# Storage account
if az storage account show -n "$TFSTATE_SA" -g "$TFSTATE_RG" >/dev/null 2>&1; then
  warn "Storage account '$TFSTATE_SA' already exists."
else
  az storage account create \
    -n "$TFSTATE_SA" \
    -g "$TFSTATE_RG" \
    -l "$LOCATION" \
    --sku Standard_LRS \
    --allow-blob-public-access false \
    --min-tls-version TLS1_2 \
    -o none
  ok "Created storage account: $TFSTATE_SA"
fi

# Container
SA_KEY=$(az storage account keys list -n "$TFSTATE_SA" -g "$TFSTATE_RG" --query "[0].value" -o tsv)
if az storage container show -n "$TFSTATE_CONTAINER" --account-name "$TFSTATE_SA" --account-key "$SA_KEY" >/dev/null 2>&1; then
  warn "Container '$TFSTATE_CONTAINER' already exists."
else
  az storage container create \
    -n "$TFSTATE_CONTAINER" \
    --account-name "$TFSTATE_SA" \
    --account-key "$SA_KEY" \
    -o none
  ok "Created container: $TFSTATE_CONTAINER"
fi

# Grant SP access to tfstate storage
info "Granting service principal Storage Blob Data Contributor on tfstate..."
SP_OBJECT_ID=$(az ad sp show --id "$CLIENT_ID" --query id -o tsv)
az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$TFSTATE_RG/providers/Microsoft.Storage/storageAccounts/$TFSTATE_SA" \
  -o none 2>/dev/null || warn "Role assignment may already exist."
ok "Service principal can access tfstate storage."

# ── Step 4: Set GitHub Repository Secrets ────────────────────────────
echo ""
info "Step 4/5: Setting GitHub repository secrets..."

declare -A SECRETS=(
  [AZURE_CLIENT_ID]="$CLIENT_ID"
  [AZURE_TENANT_ID]="$TENANT_ID"
  [AZURE_SUBSCRIPTION_ID]="$SUBSCRIPTION_ID"
)

for SECRET_NAME in "${!SECRETS[@]}"; do
  gh secret set "$SECRET_NAME" --repo "$GITHUB_REPO" --body "${SECRETS[$SECRET_NAME]}"
  ok "Set secret: $SECRET_NAME"
done

# ACR name/login server will be set after first terraform apply
info "Note: ACR_NAME and ACR_LOGIN_SERVER will be set after first 'terraform apply'."

# ── Step 5: Enable Terraform Remote Backend ──────────────────────────
echo ""
info "Step 5/5: Enabling Terraform remote backend..."

BACKEND_FILE="$(cd "$(dirname "$0")/../infra" && pwd)/backend.tf"
cat > "$BACKEND_FILE" << 'TFEOF'
# Terraform remote state storage in Azure
# Auto-generated by bootstrap-azure.sh

terraform {
  backend "azurerm" {
    resource_group_name  = "rg-m365vault-tfstate"
    storage_account_name = "stm365vaulttfstate"
    container_name       = "tfstate"
    key                  = "m365vault.terraform.tfstate"
    use_oidc             = true
  }
}
TFEOF
ok "Enabled remote backend in $BACKEND_FILE"

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Bootstrap complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Subscription:    $SUBSCRIPTION_ID"
echo "  Tenant:          $TENANT_ID"
echo "  Service Principal: $CLIENT_ID"
echo "  TF State:        $TFSTATE_SA/$TFSTATE_CONTAINER"
echo "  GitHub Repo:     $GITHUB_REPO"
echo ""
echo "Next steps:"
echo "  1. Run Terraform to create infrastructure:"
echo "     cd infra"
echo "     terraform init -migrate-state    # migrate local → remote"
echo "     terraform plan -var-file=environments/dev.tfvars -var=\"subscription_id=$SUBSCRIPTION_ID\""
echo "     terraform apply -var-file=environments/dev.tfvars -var=\"subscription_id=$SUBSCRIPTION_ID\""
echo ""
echo "  2. After terraform apply, set ACR secrets:"
echo "     ACR_NAME=\$(terraform output -raw acr_login_server | cut -d. -f1)"
echo "     ACR_SERVER=\$(terraform output -raw acr_login_server)"
echo "     gh secret set ACR_NAME --repo $GITHUB_REPO --body \"\$ACR_NAME\""
echo "     gh secret set ACR_LOGIN_SERVER --repo $GITHUB_REPO --body \"\$ACR_SERVER\""
echo ""
echo "  3. Push to main — GitHub Actions will build & deploy automatically."
echo ""
