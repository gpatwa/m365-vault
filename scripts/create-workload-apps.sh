#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Create Per-Workload Multi-Tenant App Registrations
#
# Creates separate Entra app registrations for each workload with
# ONLY the permissions that workload needs. Apps live in KavachIQ's
# tenant (SaaS model). Customers consent per-workload.
#
# Usage:
#   ./scripts/create-workload-apps.sh
#   make create-workload-apps
#
# Requires: az login (as app registration owner)
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${CYAN}═══ KavachIQ Per-Workload App Registration ═══${NC}"
echo ""

if ! az account show &>/dev/null; then
  echo -e "${RED}Not logged into Azure. Run: az login${NC}"
  exit 1
fi

# Microsoft Graph resource app ID
MS_GRAPH="00000003-0000-0000-c000-000000000000"

# Output file for storing app credentials
OUTPUT_FILE=".env.workload-apps"
echo "# KavachIQ Per-Workload App Credentials (generated $(date +%Y-%m-%d))" > "$OUTPUT_FILE"
echo "# Store these in Key Vault — DO NOT commit to git" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

create_workload_app() {
  local NAME="$1"
  local WORKLOAD_KEY="$2"
  local PERMISSIONS_JSON="$3"
  local REDIRECT_URIS="$4"

  echo -e "${CYAN}Creating: $NAME${NC}"

  # Check if already exists
  EXISTING=$(az ad app list --filter "displayName eq '$NAME'" --query "[0].appId" -o tsv 2>/dev/null)
  if [ -n "$EXISTING" ]; then
    echo -e "  ${YELLOW}Already exists: $EXISTING${NC}"
    echo "${WORKLOAD_KEY}_APP_ID=$EXISTING" >> "$OUTPUT_FILE"
    return
  fi

  # Create multi-tenant app registration
  APP_JSON=$(az ad app create \
    --display-name "$NAME" \
    --sign-in-audience "AzureADMultipleOrgs" \
    --required-resource-accesses "$PERMISSIONS_JSON" \
    --web-redirect-uris $REDIRECT_URIS \
    --query "{appId:appId, id:id}" -o json 2>&1)

  APP_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['appId'])" 2>/dev/null)
  OBJ_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

  if [ -z "$APP_ID" ]; then
    echo -e "  ${RED}Failed to create app: $APP_JSON${NC}"
    return
  fi

  echo -e "  App ID: $APP_ID"
  echo -e "  Object ID: $OBJ_ID"

  # Create client secret (1 year)
  SECRET_JSON=$(az ad app credential reset \
    --id "$APP_ID" \
    --display-name "KavachIQ Backup Secret" \
    --years 1 \
    --query "{password:password}" -o json 2>&1)

  SECRET=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])" 2>/dev/null)

  if [ -z "$SECRET" ]; then
    echo -e "  ${RED}Failed to create secret: $SECRET_JSON${NC}"
    return
  fi

  echo -e "  Secret: ${SECRET:0:8}..."

  # Save to output file
  echo "${WORKLOAD_KEY}_APP_ID=$APP_ID" >> "$OUTPUT_FILE"
  echo "${WORKLOAD_KEY}_APP_SECRET=$SECRET" >> "$OUTPUT_FILE"
  echo "${WORKLOAD_KEY}_APP_OBJECT_ID=$OBJ_ID" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"

  echo -e "  ${GREEN}✅ Created${NC}"
  echo ""
}

# ─── Entra ID App ───────────────────────────────────────────────────
create_workload_app \
  "KavachIQ-EntraID" \
  "ENTRA_ID" \
  "[{
    \"resourceAppId\": \"$MS_GRAPH\",
    \"resourceAccess\": [
      {\"id\": \"7ab1d382-f21e-4acd-a863-ba3e13f7da61\", \"type\": \"Role\"},
      {\"id\": \"df021288-bdef-4463-88db-98f22de89214\", \"type\": \"Role\"},
      {\"id\": \"5b567255-7703-4780-807c-7be8301ae99b\", \"type\": \"Role\"}
    ]
  }]" \
  "http://localhost:5173/onboard/callback https://kavachiq.com/onboard/callback"

# ─── Exchange App ───────────────────────────────────────────────────
create_workload_app \
  "KavachIQ-Exchange" \
  "EXCHANGE" \
  "[{
    \"resourceAppId\": \"$MS_GRAPH\",
    \"resourceAccess\": [
      {\"id\": \"810c84a8-4a9e-49e6-bf7d-12d183f40d01\", \"type\": \"Role\"},
      {\"id\": \"798ee544-9d2d-430c-a058-570e29e34338\", \"type\": \"Role\"},
      {\"id\": \"089fe4d0-434a-44c5-8827-41ba8a0b17f5\", \"type\": \"Role\"},
      {\"id\": \"df021288-bdef-4463-88db-98f22de89214\", \"type\": \"Role\"}
    ]
  }]" \
  "http://localhost:5173/onboard/callback https://kavachiq.com/onboard/callback"

# ─── SharePoint App ─────────────────────────────────────────────────
create_workload_app \
  "KavachIQ-SharePoint" \
  "SHAREPOINT" \
  "[{
    \"resourceAppId\": \"$MS_GRAPH\",
    \"resourceAccess\": [
      {\"id\": \"332a536c-c7ef-4017-ab91-336970924f0d\", \"type\": \"Role\"},
      {\"id\": \"df021288-bdef-4463-88db-98f22de89214\", \"type\": \"Role\"}
    ]
  }]" \
  "http://localhost:5173/onboard/callback https://kavachiq.com/onboard/callback"

# ─── OneDrive App ───────────────────────────────────────────────────
create_workload_app \
  "KavachIQ-OneDrive" \
  "ONEDRIVE" \
  "[{
    \"resourceAppId\": \"$MS_GRAPH\",
    \"resourceAccess\": [
      {\"id\": \"01d4f6ba-6a36-4f86-b5fa-0514e2aa4b40\", \"type\": \"Role\"},
      {\"id\": \"df021288-bdef-4463-88db-98f22de89214\", \"type\": \"Role\"}
    ]
  }]" \
  "http://localhost:5173/onboard/callback https://kavachiq.com/onboard/callback"

# ─── Teams App ──────────────────────────────────────────────────────
create_workload_app \
  "KavachIQ-Teams" \
  "TEAMS" \
  "[{
    \"resourceAppId\": \"$MS_GRAPH\",
    \"resourceAccess\": [
      {\"id\": \"6b7d71aa-70aa-4810-a8d9-5d9fb2830017\", \"type\": \"Role\"},
      {\"id\": \"7b2449af-6ccd-4f4d-9f78-e550c10e2869\", \"type\": \"Role\"},
      {\"id\": \"2280dda6-0bfd-44ee-a2f4-cb867cfc4c1e\", \"type\": \"Role\"},
      {\"id\": \"242607bd-1d2c-432c-82eb-bdb27baa23ab\", \"type\": \"Role\"},
      {\"id\": \"5b567255-7703-4780-807c-7be8301ae99b\", \"type\": \"Role\"}
    ]
  }]" \
  "http://localhost:5173/onboard/callback https://kavachiq.com/onboard/callback"

# ─── Summary ────────────────────────────────────────────────────────
echo -e "${CYAN}═══ Summary ═══${NC}"
echo ""
echo "Per-workload apps created. Credentials saved to: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Push secrets to Key Vault: add to .env.secrets + make secrets-push"
echo "  2. Grant admin consent for YOUR tenant (KavachIQ):"

for WL in ENTRA_ID EXCHANGE SHAREPOINT ONEDRIVE TEAMS; do
  WL_APP_ID=$(grep "${WL}_APP_ID=" "$OUTPUT_FILE" | head -1 | cut -d= -f2)
  if [ -n "$WL_APP_ID" ]; then
    echo "     $WL: az ad app permission admin-consent --id $WL_APP_ID"
  fi
done

echo ""
echo "  3. For each customer tenant, generate admin consent URLs:"
echo "     https://login.microsoftonline.com/{tenant}/adminconsent?client_id={app_id}"
echo ""
echo -e "${GREEN}Done ✅${NC}"
