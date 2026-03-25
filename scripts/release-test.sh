#!/bin/bash
# Quick release gate test — run before deploying to Azure
# Tests core user flows against running Docker Compose stack
# Usage: make release-test (or ./scripts/release-test.sh)

set -e
BACKEND="http://localhost:8000"
FRONTEND="http://localhost:5173"
PASS=0
FAIL=0
TOTAL=0

check() {
  TOTAL=$((TOTAL + 1))
  local desc="$1"
  local result="$2"
  local expected="$3"

  if echo "$result" | grep -q "$expected"; then
    PASS=$((PASS + 1))
    echo "  ✅ $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  ❌ $desc"
    echo "     Expected: $expected"
    echo "     Got: $(echo "$result" | head -1 | cut -c1-100)"
  fi
}

echo "═══ SHIELDIO RELEASE TEST ═══"
echo ""

# 1. Backend health
echo "── Backend Health ──"
HEALTH=$(curl -s "$BACKEND/health")
check "Health endpoint" "$HEALTH" '"status"'
check "Database healthy" "$HEALTH" '"database":"healthy"'
check "Storage healthy" "$HEALTH" '"storage":"healthy"'

# 2. API info
echo ""
echo "── API Info ──"
ROOT=$(curl -s "$BACKEND/")
check "App name is Shieldio" "$ROOT" 'Shieldio'
check "Status running" "$ROOT" '"status":"running"'

ROUTES=$(curl -s "$BACKEND/openapi.json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['paths']))" 2>/dev/null)
check "API routes > 100" "$ROUTES" ""
if [ "$ROUTES" -lt 100 ] 2>/dev/null; then
  FAIL=$((FAIL + 1))
  echo "  ❌ Only $ROUTES routes (expected 100+)"
fi

# 3. Auth
echo ""
echo "── Authentication ──"
TOKEN=$(curl -s -X POST "$BACKEND/api/auth/login" -d "username=admin&password=admin123" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
  check "Login works" "OK" "OK"
else
  check "Login works" "FAILED" "OK"
  echo "  ⚠️  Cannot continue without auth — skipping remaining tests"
  echo ""
  echo "═══ RESULT: $PASS/$TOTAL passed, $FAIL failed ═══"
  exit 1
fi

AUTH="Authorization: Bearer $TOKEN"

# 4. Core API endpoints
echo ""
echo "── Core API Endpoints ──"
check "GET /tenants" "$(curl -s -H "$AUTH" "$BACKEND/api/tenants/" -o /dev/null -w "%{http_code}")" "200"
check "GET /sla-policies" "$(curl -s -H "$AUTH" "$BACKEND/api/sla-policies/" -o /dev/null -w "%{http_code}")" "200"
check "GET /dashboard/summary" "$(curl -s -H "$AUTH" "$BACKEND/api/dashboard/summary" -o /dev/null -w "%{http_code}")" "200"
check "GET /jobs/backup" "$(curl -s -H "$AUTH" "$BACKEND/api/jobs/backup" -o /dev/null -w "%{http_code}")" "200"
check "GET /jobs/restore" "$(curl -s -H "$AUTH" "$BACKEND/api/jobs/restore" -o /dev/null -w "%{http_code}")" "200"
check "GET /failed-items" "$(curl -s -H "$AUTH" "$BACKEND/api/failed-items" -o /dev/null -w "%{http_code}")" "200"
check "GET /audit/logs" "$(curl -s -H "$AUTH" "$BACKEND/api/audit/logs" -o /dev/null -w "%{http_code}")" "200"

# 5. Workload endpoints
echo ""
echo "── Workload Endpoints ──"
# Get tenant ID
TENANT_ID=$(curl -s -H "$AUTH" "$BACKEND/api/tenants/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if d else '0')" 2>/dev/null)
if [ "$TENANT_ID" != "0" ] && [ -n "$TENANT_ID" ]; then
  check "GET /exchange/mailboxes" "$(curl -s -H "$AUTH" "$BACKEND/api/exchange/mailboxes?tenant_id=$TENANT_ID" -o /dev/null -w "%{http_code}")" "200"
  check "GET /onedrive/accounts" "$(curl -s -H "$AUTH" "$BACKEND/api/onedrive/accounts?tenant_id=$TENANT_ID" -o /dev/null -w "%{http_code}")" "200"
  check "GET /sharepoint/sites" "$(curl -s -H "$AUTH" "$BACKEND/api/sharepoint/sites?tenant_id=$TENANT_ID" -o /dev/null -w "%{http_code}")" "200"
  check "GET /teams/teams" "$(curl -s -H "$AUTH" "$BACKEND/api/teams/teams?tenant_id=$TENANT_ID" -o /dev/null -w "%{http_code}")" "200"
  check "GET /entra-id/summary" "$(curl -s -H "$AUTH" "$BACKEND/api/entra-id/summary?tenant_id=$TENANT_ID" -o /dev/null -w "%{http_code}")" "200"
else
  echo "  ⏭️  No tenant — skipping workload endpoints"
fi

# 6. Intelligence endpoints
echo ""
echo "── Intelligence Endpoints ──"
check "GET /health/score" "$(curl -s -H "$AUTH" "$BACKEND/api/health/score?tenant_id=${TENANT_ID:-1}" -o /dev/null -w "%{http_code}")" "200"
check "GET /alerts/config" "$(curl -s -H "$AUTH" "$BACKEND/api/alerts/config" -o /dev/null -w "%{http_code}")" "200"
check "GET /auth/sso/config" "$(curl -s "$BACKEND/api/auth/sso/config" -o /dev/null -w "%{http_code}")" "200"
check "GET /usage/license" "$(curl -s -H "$AUTH" "$BACKEND/api/usage/license" -o /dev/null -w "%{http_code}")" "200"
check "GET /usage/platform" "$(curl -s -H "$AUTH" "$BACKEND/api/usage/platform" -o /dev/null -w "%{http_code}")" "200"

# 7. Search
echo ""
echo "── Search ──"
check "GET /search/intent" "$(curl -s -H "$AUTH" "$BACKEND/api/search/intent?q=test&tenant_id=${TENANT_ID:-1}" -o /dev/null -w "%{http_code}")" "200"

# 8. Frontend
echo ""
echo "── Frontend ──"
check "Frontend loads" "$(curl -s "$FRONTEND" -o /dev/null -w "%{http_code}")" "200"
FRONTEND_HTML=$(curl -s "$FRONTEND")
check "Frontend has Shieldio" "$FRONTEND_HTML" "Shieldio"

# 9. Worker health
echo ""
echo "── Worker (Data Plane) ──"
WORKER_STATUS=$(docker compose ps worker --format "{{.Status}}" 2>/dev/null)
check "Worker container running" "$WORKER_STATUS" "Up"

# 10. Redis
REDIS_STATUS=$(docker compose ps redis --format "{{.Status}}" 2>/dev/null)
check "Redis healthy" "$REDIS_STATUS" "healthy"

# Summary
echo ""
echo "═══════════════════════════════════════"
if [ $FAIL -eq 0 ]; then
  echo "  ✅ ALL $TOTAL TESTS PASSED — ready to deploy"
else
  echo "  ❌ $FAIL/$TOTAL FAILED — fix before deploying"
fi
echo "═══════════════════════════════════════"

exit $FAIL
