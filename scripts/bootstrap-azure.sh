#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# Shieldio — Fully automated Azure + GitHub bootstrap
#
# Zero prerequisites required — this script handles everything:
#   1. Auto-installs missing tools (az, gh, jq, terraform) via Homebrew
#   2. Authenticates Azure CLI via browser (device code flow)
#   3. Authenticates GitHub CLI via browser (OAuth web flow)
#   4. Creates Azure service principal with OIDC for GitHub Actions
#   5. Creates Terraform remote state storage (Azure Blob)
#   6. Sets all required GitHub repository secrets automatically
#   7. Enables Terraform remote backend
#
# Usage:
#   make bootstrap                                        # interactive
#   make bootstrap SUBSCRIPTION_ID=<id>                   # non-interactive
#   ./scripts/bootstrap-azure.sh                          # direct run
#   ./scripts/bootstrap-azure.sh --subscription <id>      # direct + sub ID
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

# ── Auto-install prerequisites ─────────────────────────────────────
install_with_brew() {
  local pkg="$1"
  if ! command -v brew >/dev/null 2>&1; then
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon
    if [[ -f /opt/homebrew/bin/brew ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
  fi
  info "Installing $pkg via Homebrew..."
  brew install "$pkg"
}

for cmd in az gh jq terraform; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    warn "$cmd not found. Installing..."
    case "$cmd" in
      az)        install_with_brew azure-cli ;;
      gh)        install_with_brew gh ;;
      jq)        install_with_brew jq ;;
      terraform) install_with_brew hashicorp/tap/terraform ;;
    esac
    command -v "$cmd" >/dev/null 2>&1 || fail "Failed to install $cmd."
    ok "$cmd installed successfully."
  else
    ok "$cmd is available."
  fi
done

# Check Azure login (prompt if needed — opens browser)
if ! az account show >/dev/null 2>&1; then
  warn "Not logged in to Azure. Opening browser-based login..."
  az login --use-device-code
fi
ok "Azure CLI authenticated."

# Check GitHub login (prompt if needed — use browser-based auth, no token required)
if ! gh auth status >/dev/null 2>&1; then
  warn "Not logged in to GitHub. Opening browser-based login..."
  gh auth login --hostname github.com --git-protocol https --web
fi
ok "GitHub CLI authenticated."

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

# ── Step 4: Create Shieldio Connector App Registration ───────────────
echo ""
info "Step 4/6: Creating Shieldio Connector multi-tenant app registration..."

CONNECTOR_APP_NAME="Shieldio Connector"
EXISTING_CONNECTOR=$(az ad app list --display-name "$CONNECTOR_APP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)

if [[ -n "$EXISTING_CONNECTOR" ]]; then
  warn "Connector app '$CONNECTOR_APP_NAME' already exists: $EXISTING_CONNECTOR"
  CONNECTOR_APP_ID="$EXISTING_CONNECTOR"
else
  # Create multi-tenant app
  CONNECTOR_APP_ID=$(az ad app create \
    --display-name "$CONNECTOR_APP_NAME" \
    --sign-in-audience AzureADMultipleOrgs \
    --web-redirect-uris "http://localhost:5173/onboard/callback" "https://m365vault-frontend-dev.happyflower-239d5857.centralus.azurecontainerapps.io/onboard/callback" \
    --query appId -o tsv)
  ok "Created connector app: $CONNECTOR_APP_ID"

  # Add Microsoft Graph API permissions (Application type)
  GRAPH_API_ID="00000003-0000-0000-c000-000000000000"
  GRAPH_PERMISSIONS=(
    "7ab1d382-f21e-4acd-a863-ba3e13f7da61"  # Directory.Read.All
    "df021288-bdef-4463-88db-98f22de89214"  # User.Read.All
    "810c84a8-4a9e-49e6-bf7d-12d183f40d01"  # Mail.Read (Application)
    "798ee544-9d2d-430c-a058-570e29e34338"  # Calendars.Read (Application)
    "089fe4d0-434a-44c5-8827-41ba8a0b17f5"  # Contacts.Read (Application)
    "01d4f6ba-0c23-47de-97d7-1a3a6b296f38"  # Files.Read.All (Application)
    "332a536c-c7ef-4017-ab91-336970924f0d"  # Sites.Read.All (Application)
    "6b7d71aa-70aa-4810-a8d9-5d9fb2830017"  # Chat.Read.All (Application)
    "7b2449af-6ccd-4f4d-9f78-e550c10e2869"  # ChannelMessage.Read.All (Application)
    "2280dda6-0bfd-44ee-a2f4-cb867cfc4c1e"  # Team.ReadBasic.All
    "242607bd-1d2c-432c-82eb-bdb27baa23ab"  # TeamSettings.Read.All
    "5b567255-7703-4780-807c-7be8301ae99b"  # Group.Read.All (Application)
  )

  # Build required resource access JSON
  PERMISSIONS_JSON="["
  for perm_id in "${GRAPH_PERMISSIONS[@]}"; do
    PERMISSIONS_JSON+="{ \"id\": \"$perm_id\", \"type\": \"Role\" },"
  done
  PERMISSIONS_JSON="${PERMISSIONS_JSON%,}]"

  CONNECTOR_OBJECT_ID=$(az ad app show --id "$CONNECTOR_APP_ID" --query id -o tsv)
  az rest --method PATCH \
    --uri "https://graph.microsoft.com/v1.0/applications/$CONNECTOR_OBJECT_ID" \
    --body "{
      \"requiredResourceAccess\": [{
        \"resourceAppId\": \"$GRAPH_API_ID\",
        \"resourceAccess\": $PERMISSIONS_JSON
      }]
    }" 2>/dev/null
  ok "Added Microsoft Graph API permissions"
fi

# Create client secret if needed
EXISTING_SECRET=$(az ad app credential list --id "$CONNECTOR_APP_ID" --query "[0].keyId" -o tsv 2>/dev/null || true)
if [[ -n "$EXISTING_SECRET" ]]; then
  warn "Connector app already has a client secret."
  CONNECTOR_SECRET="(existing — check Key Vault or env vars)"
else
  CONNECTOR_SECRET=$(az ad app credential reset --id "$CONNECTOR_APP_ID" --years 2 --query password -o tsv)
  ok "Created client secret (expires in 2 years)"
fi

ok "Connector App ID: $CONNECTOR_APP_ID"

# ── Step 5: Set GitHub Repository Secrets ────────────────────────────
echo ""
info "Step 5/6: Setting GitHub repository secrets..."

gh secret set AZURE_CLIENT_ID --repo "$GITHUB_REPO" --body "$CLIENT_ID"
ok "Set secret: AZURE_CLIENT_ID"
gh secret set AZURE_TENANT_ID --repo "$GITHUB_REPO" --body "$TENANT_ID"
ok "Set secret: AZURE_TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID --repo "$GITHUB_REPO" --body "$SUBSCRIPTION_ID"
ok "Set secret: AZURE_SUBSCRIPTION_ID"

# Set Shieldio Connector secrets
gh secret set CONNECTOR_APP_ID --repo "$GITHUB_REPO" --body "$CONNECTOR_APP_ID"
ok "Set secret: CONNECTOR_APP_ID"
if [[ "$CONNECTOR_SECRET" != "(existing"* ]]; then
  gh secret set CONNECTOR_APP_SECRET --repo "$GITHUB_REPO" --body "$CONNECTOR_SECRET"
  ok "Set secret: CONNECTOR_APP_SECRET"
fi

# ACR name/login server will be set after first terraform apply
info "Note: ACR_NAME and ACR_LOGIN_SERVER will be set after first 'terraform apply'."

# ── Step 6: Enable Terraform Remote Backend ──────────────────────────
echo ""
info "Step 6/6: Enabling Terraform remote backend..."

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
echo "  Subscription:      $SUBSCRIPTION_ID"
echo "  Tenant:            $TENANT_ID"
echo "  Service Principal: $CLIENT_ID"
echo "  Connector App:     $CONNECTOR_APP_ID"
echo "  TF State:          $TFSTATE_SA/$TFSTATE_CONTAINER"
echo "  GitHub Repo:       $GITHUB_REPO"
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
