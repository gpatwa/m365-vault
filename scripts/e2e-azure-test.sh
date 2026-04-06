#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Azure E2E Release Certification Test
#
# Runs against a deployed Azure environment. Returns exit code 0 if
# all tests pass, non-zero otherwise. Used in CI for post-deploy gating.
#
# Usage:
#   ./scripts/e2e-azure-test.sh [--env dev|staging|prod]
#   make e2e-test ENV=dev
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

ENV="${1:-dev}"
[[ "$1" == "--env" ]] && ENV="${2:-dev}"

# Resolve URLs
if [ "$ENV" = "prod" ]; then
  BACKEND="https://api.kavachiq.com"
  FRONTEND="https://app.kavachiq.com"
else
  RG="rg-m365vault-${ENV}"
  BACKEND_FQDN=$(az containerapp show --name "m365vault-backend-${ENV}" --resource-group "$RG" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null)
  FRONTEND_FQDN=$(az containerapp show --name "m365vault-frontend-${ENV}" --resource-group "$RG" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null)
  BACKEND="https://$BACKEND_FQDN"
  FRONTEND="https://$FRONTEND_FQDN"

  # Also test custom domains if they exist
  if [ "$ENV" = "dev" ]; then
    BACKEND="https://api.kavachiq.com"
    FRONTEND="https://app.kavachiq.com"
  fi
fi

PASS=0; FAIL=0; TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  local desc="$1"; local result="$2"; local expected="$3"
  if echo "$result" | grep -q "$expected"; then
    PASS=$((PASS + 1)); echo "  ✅ $desc"
  else
    FAIL=$((FAIL + 1)); echo "  ❌ $desc"
  fi
}

echo "═══ KAVACHIQ E2E CERTIFICATION (ENV=${ENV}) ═══"
echo "  Backend:  $BACKEND"
echo "  Frontend: $FRONTEND"
echo ""

echo "── Infrastructure ──"
HEALTH=$(curl -sf --max-time 15 "$BACKEND/health" 2>&1 || echo '{}')
check "Backend healthy" "$HEALTH" '"status":"healthy"'
check "Database connected" "$HEALTH" '"database":"healthy"'
check "Storage connected" "$HEALTH" '"storage":"healthy"'
check "Frontend loads" "$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$FRONTEND/")" "200"

echo ""
echo "── Auth ──"
check "Login endpoint" "$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" -X POST "$BACKEND/api/auth/login" -d "username=x&password=x")" "401"
check "Register endpoint" "$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" -X POST "$BACKEND/api/auth/register" -H "Content-Type: application/json" -d '{}')" "422"

echo ""
echo "── Protected Endpoints (401) ──"
check "Tenants" "$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" "$BACKEND/api/tenants/")" "401"
check "Dashboard" "$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" "$BACKEND/api/dashboard/summary")" "401"
check "Approvals" "$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" "$BACKEND/api/restore-approvals/pending")" "401"

echo ""
echo "── Public Endpoints ──"
check "SSO config" "$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$BACKEND/api/auth/sso/config")" "200"
check "Status" "$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$BACKEND/api/status")" "200"
check "OpenAPI" "$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$BACKEND/openapi.json")" "200"

echo ""
echo "── New Features ──"
check "Restore approvals" "$(curl -s --max-time 10 "$BACKEND/api/restore-approvals/pending")" "Not authenticated"
check "Workload apps" "$(curl -s --max-time 10 "$BACKEND/api/tenants/1/workloads")" "Not authenticated"
check "Invite admin" "$(curl -s --max-time 10 "$BACKEND/api/onboard/invite/fake")" "not found"
check "Product tour" "$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$FRONTEND/tour")" "200"

echo ""
echo "── Security ──"
HEADERS=$(curl -sI --max-time 10 "$BACKEND/" 2>&1)
check "Correlation ID" "$HEADERS" "x-correlation-id"
check "Response time" "$HEADERS" "x-response-time"

echo ""
echo "── Branding ──"
check "API is KavachIQ" "$(curl -sf --max-time 10 "$BACKEND/")" "KavachIQ"
check "Frontend title" "$(curl -sf --max-time 10 "$FRONTEND/" | grep -o '<title>[^<]*</title>')" "KavachIQ"

echo ""
echo "═══════════════════════════════════════════════════════"
if [ $FAIL -eq 0 ]; then
  echo "  ✅ ALL $TOTAL TESTS PASSED — RELEASE CERTIFIED"
else
  echo "  ❌ $FAIL/$TOTAL FAILED"
fi
echo "═══════════════════════════════════════════════════════"

exit $FAIL
