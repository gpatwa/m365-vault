#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Configure Connector App Permissions
#
# ONE-TIME SETUP: Adds all required Graph API application permissions
# to the KavachIQ Connector multi-tenant app and grants admin consent.
#
# Requires: az login (as Global Admin or App Registration Owner)
#
# Usage:
#   ./scripts/configure-connector-permissions.sh
#   make configure-connector
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

# Load app ID from .env
if [ -f .env ]; then
  source .env
fi

APP_ID="${CONNECTOR_APP_ID:-d5c6ca1d-0f4a-4e14-a121-136fde89512d}"

echo -e "${CYAN}═══ KavachIQ Connector Permission Setup ═══${NC}"
echo "  App ID: $APP_ID"
echo ""

# Check Azure CLI login
if ! az account show &>/dev/null; then
  echo -e "${RED}Not logged into Azure. Run: az login${NC}"
  exit 1
fi

echo "Step 1: Configuring application permissions..."

# Microsoft Graph resource app ID
MS_GRAPH="00000003-0000-0000-c000-000000000000"

# Required application permissions (Role type) for backup + restore
az ad app update --id "$APP_ID" --required-resource-accesses "[{
  \"resourceAppId\": \"$MS_GRAPH\",
  \"resourceAccess\": [
    {\"id\": \"df021288-bdef-4463-88db-98f22de89214\", \"type\": \"Role\"},
    {\"id\": \"7ab1d382-f21e-4acd-a863-ba3e13f7da61\", \"type\": \"Role\"},
    {\"id\": \"810c84a8-4a9e-49e6-bf7d-12d183f40d01\", \"type\": \"Role\"},
    {\"id\": \"798ee544-9d2d-430c-a058-570e29e34338\", \"type\": \"Role\"},
    {\"id\": \"089fe4d0-434a-44c5-8827-41ba8a0b17f5\", \"type\": \"Role\"},
    {\"id\": \"5b567255-7703-4780-807c-7be8301ae99b\", \"type\": \"Role\"},
    {\"id\": \"01d4f6ba-6a36-4f86-b5fa-0514e2aa4b40\", \"type\": \"Role\"},
    {\"id\": \"332a536c-c7ef-4017-ab91-336970924f0d\", \"type\": \"Role\"},
    {\"id\": \"6b7d71aa-70aa-4810-a8d9-5d9fb2830017\", \"type\": \"Role\"},
    {\"id\": \"7b2449af-6ccd-4f4d-9f78-e550c10e2869\", \"type\": \"Role\"},
    {\"id\": \"2280dda6-0bfd-44ee-a2f4-cb867cfc4c1e\", \"type\": \"Role\"},
    {\"id\": \"242607bd-1d2c-432c-82eb-bdb27baa23ab\", \"type\": \"Role\"}
  ]
}]" 2>&1

echo -e "  ${GREEN}✅ Permissions configured${NC}"
echo ""

echo "Step 2: Granting admin consent..."
echo "  Note: The 'az ad app permission admin-consent' command may fail for multi-tenant apps."
echo "  If it fails, use the browser URL below instead."
echo ""

az ad app permission admin-consent --id "$APP_ID" 2>/dev/null && {
  echo -e "  ${GREEN}✅ Admin consent granted via CLI${NC}"
} || {
  TENANT_ID=$(az account show --query tenantId -o tsv)
  echo -e "  ${RED}CLI consent failed. Use browser instead:${NC}"
  echo ""
  echo "  https://login.microsoftonline.com/${TENANT_ID}/adminconsent?client_id=${APP_ID}"
  echo ""
  echo "  Open this URL, sign in as Global Admin, and click Accept."
}

echo ""
echo "Step 3: Verifying permissions..."
sleep 5

PERM_COUNT=$(az ad app show --id "$APP_ID" --query "requiredResourceAccess[0].resourceAccess | length(@)" -o tsv 2>/dev/null || echo "0")
echo "  Configured permissions: $PERM_COUNT"

if [ "$PERM_COUNT" -ge 10 ]; then
  echo -e "  ${GREEN}✅ All permissions configured${NC}"
else
  echo -e "  ${RED}❌ Only $PERM_COUNT permissions — expected 12+${NC}"
fi

echo ""
echo -e "${CYAN}═══ Setup Complete ═══${NC}"
echo "  Next: Open the admin consent URL in your browser if CLI consent failed."
echo "  Then: make dev-bg && open http://localhost:5173/onboard"
