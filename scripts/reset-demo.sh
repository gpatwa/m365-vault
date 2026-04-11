#!/bin/bash
# KavachIQ — Reset Demo User for Onboarding Testing
#
# Offboards the tenant + clears onboarding state so the user
# sees the full "Connect Microsoft 365" wizard on next login.
#
# Usage:
#   ./scripts/reset-demo.sh <username> <tenant_id> [backend_url]
#
# Examples:
#   ./scripts/reset-demo.sh demo 5
#   ./scripts/reset-demo.sh prospect 4
#   ./scripts/reset-demo.sh demo 5 https://api.kavachiq.com

set -uo pipefail

USERNAME="${1:?Usage: $0 <username> <tenant_id> [backend_url]}"
TENANT_ID="${2:?Usage: $0 <username> <tenant_id> [backend_url]}"
BACKEND="${3:-https://api.kavachiq.com}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  KavachIQ Demo Reset"
echo "  User: $USERNAME | Tenant: $TENANT_ID"
echo "  Backend: $BACKEND"
echo "═══════════════════════════════════════════════════════"
echo ""

# Login as admin
TOKEN=$(curl -s --max-time 10 -X POST "$BACKEND/api/auth/login" \
  -d "username=admin&password=Admin123!" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ] || [ ${#TOKEN} -lt 10 ]; then
  echo -e "${RED}Admin login failed${NC}"
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"

# Step 1: Offboard tenant
echo "── Step 1: Offboard tenant $TENANT_ID ──"
OFFBOARD=$(curl -s --max-time 15 -X POST -H "$AUTH" \
  "$BACKEND/api/msp/offboard/$TENANT_ID?confirm=true")
STATUS=$(echo "$OFFBOARD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null)

if [ "$STATUS" = "offboarded" ] || [ "$STATUS" = "already_inactive" ]; then
  echo -e "  ${GREEN}✅${NC} Tenant offboarded ($STATUS)"
else
  echo -e "  ${RED}❌${NC} Offboard failed: $OFFBOARD"
  echo "  (If active jobs exist, wait for them to complete)"
  exit 1
fi

# Step 2: Reset onboarding (full — clears steps + membership + preferences)
echo ""
echo "── Step 2: Reset onboarding for $USERNAME ──"
sleep 1
RESET=$(curl -s --max-time 10 -X DELETE -H "$AUTH" \
  "$BACKEND/api/onboard/steps/reset/$USERNAME?full=true")
echo "  $RESET" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read().strip())
print(f'  Steps cleared: {d.get(\"steps_cleared\",0)}')
print(f'  Memberships cleared: {d.get(\"tenant_memberships_cleared\",0)}')
print(f'  Preferences cleared: {d.get(\"preferences_cleared\",0)}')
" 2>/dev/null
echo -e "  ${GREEN}✅${NC} User reset to day-zero"

# Summary
echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "  ${GREEN}✅ Demo reset complete${NC}"
echo ""
echo "  Next login as '$USERNAME' will show:"
echo "    → Full onboarding wizard (Connect Microsoft 365)"
echo "    → No tenant, no workloads, no data"
echo ""
echo "  To re-onboard, use the onboarding flow in the UI"
echo "  or re-activate tenant via: POST /api/msp/reactivate/$TENANT_ID"
echo "═══════════════════════════════════════════════════════"
