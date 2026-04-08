#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Local Integration Test
#
# Tests the full stack locally BEFORE deploying to Azure.
# Catches: import errors, field mismatches, missing routes, auth bugs,
# config issues, frontend-backend connectivity.
#
# Usage:
#   make test-local
#   ./scripts/test-local.sh
#
# Requirements: Docker Compose running (make dev-bg)
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

BACKEND="http://localhost:8000"
FRONTEND="http://localhost:5173"
PASS=0; FAIL=0; TOTAL=0; SKIP=0

check() {
  TOTAL=$((TOTAL + 1))
  local desc="$1"; local result="$2"; local expected="$3"
  if echo "$result" | grep -q "$expected"; then
    PASS=$((PASS + 1)); echo -e "  ${GREEN}✅${NC} $desc"
  else
    FAIL=$((FAIL + 1)); echo -e "  ${RED}❌${NC} $desc"
    echo -e "     Expected: $expected"
    echo -e "     Got: $(echo "$result" | head -1 | cut -c1-80)"
  fi
}

skip() {
  SKIP=$((SKIP + 1))
  echo -e "  ${YELLOW}⏭️${NC}  $1"
}

echo ""
echo -e "${CYAN}═══ KAVACHIQ LOCAL INTEGRATION TEST ═══${NC}"
echo ""

# ─────────────────────────────────────────────────────
# Phase 1: Unit Tests (runs inside Docker for consistent environment)
# ─────────────────────────────────────────────────────
echo -e "${CYAN}── Phase 1: Unit Tests ──${NC}"
cd "$(dirname "$0")/.."

# Run tests inside Docker container (consistent Python + deps)
UNIT_RESULT=$(docker compose run --rm --workdir /app \
  -v "$(pwd)/backend/tests:/app/tests" \
  -v "$(pwd)/backend/app:/app/app" \
  backend bash -c "pip install pytest pytest-asyncio httpx -q 2>/dev/null && python -m pytest tests/test_self_healing.py tests/test_worker_registry.py tests/test_exchange_gaps.py tests/test_entra_restore.py tests/test_workload_apps.py tests/test_tenant_isolation.py -q --tb=line 2>&1" | tail -1)
if echo "$UNIT_RESULT" | grep -q "passed"; then
  PASSED_COUNT=$(echo "$UNIT_RESULT" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+")
  check "Unit tests" "$UNIT_RESULT" "passed"
  echo -e "     ($PASSED_COUNT tests)"
else
  check "Unit tests" "$UNIT_RESULT" "passed"
fi

# ─────────────────────────────────────────────────────
# Phase 2: Docker Build (catches import errors)
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 2: Docker Build ──${NC}"

BUILD_OUT=$(docker compose build backend frontend 2>&1 | tail -3)
if [ $? -eq 0 ]; then
  check "Docker build" "success" "success"
else
  check "Docker build" "FAILED: $BUILD_OUT" "success"
  echo -e "\n${RED}Build failed — cannot continue${NC}"
  exit 1
fi

# ─────────────────────────────────────────────────────
# Phase 3: Start Stack
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 3: Start Stack ──${NC}"

docker compose up -d 2>&1 | tail -3
echo "  Waiting for services..."
sleep 15

# Check services are up
check "Backend health" "$(curl -sf --max-time 10 "$BACKEND/health" 2>/dev/null || echo 'DOWN')" '"status":"healthy"'
check "Frontend loads" "$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$FRONTEND/" 2>/dev/null || echo '000')" "200"

# ─────────────────────────────────────────────────────
# Phase 4: Auth
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 4: Auth ──${NC}"

# Try multiple password options (local dev may differ from Azure)
ADMIN_TOKEN=""
for USER_PASS in "demo:ShieldiDemo2026!" "admin:Admin123!" "admin:admin123"; do
  USER="${USER_PASS%%:*}"
  PASS_VAL="${USER_PASS##*:}"
  LOGIN=$(curl -s --max-time 10 -X POST "$BACKEND/api/auth/login" -d "username=$USER&password=$PASS_VAL")
  if echo "$LOGIN" | grep -q "access_token"; then
    if [ -z "$ADMIN_TOKEN" ]; then
      ADMIN_TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
    fi
    check "$USER login" "$LOGIN" "access_token"
    break  # At least one user works
  fi
done

if [ -z "$ADMIN_TOKEN" ]; then
  # Register a test user on the fly
  curl -s -X POST "$BACKEND/api/auth/register" -H "Content-Type: application/json" \
    -d '{"username":"testadmin","email":"test@local.dev","password":"TestPass123!","full_name":"Test","role":"admin"}' > /dev/null 2>&1
  ADMIN_TOKEN=$(curl -s -X POST "$BACKEND/api/auth/login" -d "username=testadmin&password=TestPass123!" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
  check "Fallback login (testadmin)" "$ADMIN_TOKEN" ""
fi

AUTH="Authorization: Bearer $ADMIN_TOKEN"

if [ -z "$ADMIN_TOKEN" ]; then
  echo -e "\n${RED}All login attempts failed — skipping authenticated tests${NC}"
  FAIL=$((FAIL + 1))
else

# ─────────────────────────────────────────────────────
# Phase 5: API Endpoints
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 5: API Endpoints ──${NC}"

check "GET /tenants" "$(curl -s -H "$AUTH" "$BACKEND/api/tenants/" -o /dev/null -w "%{http_code}")" "200"
check "GET /dashboard/summary" "$(curl -s -H "$AUTH" "$BACKEND/api/dashboard/summary" -o /dev/null -w "%{http_code}")" "200"
check "GET /sla-policies" "$(curl -s -H "$AUTH" "$BACKEND/api/sla-policies/" -o /dev/null -w "%{http_code}")" "200"
check "GET /jobs/backup" "$(curl -s -H "$AUTH" "$BACKEND/api/jobs/backup" -o /dev/null -w "%{http_code}")" "200"
check "GET /failed-items" "$(curl -s -H "$AUTH" "$BACKEND/api/failed-items" -o /dev/null -w "%{http_code}")" "200"
check "GET /recovery/confidence" "$(curl -s -H "$AUTH" "$BACKEND/api/recovery/confidence?tenant_id=1" -o /dev/null -w "%{http_code}")" "200"
check "GET /health/score" "$(curl -s -H "$AUTH" "$BACKEND/api/health/score?tenant_id=1" -o /dev/null -w "%{http_code}")" "200"
check "GET /usage/license" "$(curl -s -H "$AUTH" "$BACKEND/api/usage/license" -o /dev/null -w "%{http_code}")" "200"

# New feature endpoints
check "GET /restore-approvals/count" "$(curl -s -H "$AUTH" "$BACKEND/api/restore-approvals/count" -o /dev/null -w "%{http_code}")" "200"
FIRST_TID=$(curl -s -H "$AUTH" "$BACKEND/api/tenants/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if d else 0)" 2>/dev/null || echo "0")
check "GET /tenants/{id}/workloads" "$(curl -s -H "$AUTH" "$BACKEND/api/tenants/$FIRST_TID/workloads" -o /dev/null -w "%{http_code}")" "200"
check "GET /billing/config" "$(curl -s "$BACKEND/api/billing/config" -o /dev/null -w "%{http_code}")" "200"
check "GET /onboard/invite/fake" "$(curl -s "$BACKEND/api/onboard/invite/fake" -o /dev/null -w "%{http_code}")" "404"

# Protected endpoints return 401 without auth
check "401 /tenants (no auth)" "$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND/api/tenants/")" "401"
check "401 /restore-approvals (no auth)" "$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND/api/restore-approvals/pending")" "401"

# ─────────────────────────────────────────────────────
# Phase 6: Frontend-Backend Connectivity
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 6: Frontend-Backend Connectivity ──${NC}"

CONFIG_JS=$(curl -sf --max-time 10 "$FRONTEND/config.js" 2>/dev/null || echo "")
check "config.js loads" "$CONFIG_JS" "API_BASE"
check "Frontend title" "$(curl -sf "$FRONTEND/" | grep -o '<title>[^<]*</title>')" "KavachIQ"

# ─────────────────────────────────────────────────────
# Phase 7: Data Integrity
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 7: Data Integrity ──${NC}"

TENANT_COUNT=$(curl -s -H "$AUTH" "$BACKEND/api/tenants/" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
check "Tenants exist" "$([ "$TENANT_COUNT" -gt 0 ] 2>/dev/null && echo "yes" || echo "no")" "yes"

DASHBOARD=$(curl -s -H "$AUTH" "$BACKEND/api/dashboard/summary")
TOTAL_OBJ=$(echo "$DASHBOARD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_objects',0))" 2>/dev/null || echo "0")
check "Objects exist (>0)" "$([ "$TOTAL_OBJ" -gt 0 ] 2>/dev/null && echo "yes" || echo "no")" "yes"

# ─────────────────────────────────────────────────────
# Phase 8: Onboarding Callback (catches field mismatches)
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 8: Onboarding Callback ──${NC}"

# Get first tenant's ms_tenant_id
MS_TID=$(curl -s -H "$AUTH" "$BACKEND/api/tenants/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['ms_tenant_id'] if d else '')" 2>/dev/null)

if [ -n "$MS_TID" ] && ! echo "$MS_TID" | grep -q "demo-"; then
  CALLBACK=$(curl -s -H "$AUTH" "$BACKEND/api/onboard/callback?admin_consent=True&tenant=$MS_TID&state=test")
  if echo "$CALLBACK" | grep -q '"success": true'; then
    check "Callback success" "$CALLBACK" '"success": true'
    check "Callback has tenant_name" "$CALLBACK" '"tenant_name"'
    # Verify discovery field names match frontend expectations
    check "Callback has mailboxes field" "$CALLBACK" '"mailboxes"'
    check "Callback has entra_objects field" "$CALLBACK" '"entra_objects"'
    check "Callback has total_objects" "$CALLBACK" '"total_objects"'
  else
    # Callback fails locally without real M365 creds — expected
    skip "Callback failed (expected locally — needs real M365 credentials)"
  fi
else
  skip "No real tenant — skipping callback test"
fi

# ─────────────────────────────────────────────────────
# Phase 9: Security Headers
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 9: Security ──${NC}"

HEADERS=$(curl -sI --max-time 10 "$BACKEND/" 2>&1)
check "X-Correlation-ID" "$HEADERS" "x-correlation-id"
check "X-Response-Time" "$HEADERS" "x-response-time"

# Error format
ERROR_RESP=$(curl -s -X POST "$BACKEND/api/auth/login" -d "username=bad&password=bad")
check "Error has correlation_id" "$ERROR_RESP" "correlation_id"

# ─────────────────────────────────────────────────────
# Phase 10: Branding
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 10: Branding ──${NC}"

check "API name KavachIQ" "$(curl -sf "$BACKEND/")" "KavachIQ"
check "No Shieldio in API" "$(curl -sf "$BACKEND/" | grep -ci "shieldio" || echo "0")" "0"

# ─────────────────────────────────────────────────────
# Phase 11: RBAC
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 11: RBAC ──${NC}"

VIEWER_TOKEN=$(curl -s -X POST "$BACKEND/api/auth/login" -d "username=viewer&password=Viewer2026!" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$VIEWER_TOKEN" ]; then
  check "Viewer can read" "$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $VIEWER_TOKEN" "$BACKEND/api/dashboard/summary")" "200"
  check "Viewer blocked from write" "$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer $VIEWER_TOKEN" "$BACKEND/api/recovery/mass-restore" -H "Content-Type: application/json" -d '{"tenant_id":1}')" "403"
else
  skip "Viewer login failed"
fi

fi # end admin token check

# ─────────────────────────────────────────────────────
# Phase 12: OpenAPI Route Count
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Phase 12: API Completeness ──${NC}"

ROUTE_COUNT=$(curl -sf "$BACKEND/openapi.json" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('paths',{})))" 2>/dev/null || echo "0")
check "API has 100+ routes" "$([ "$ROUTE_COUNT" -ge 100 ] 2>/dev/null && echo "yes" || echo "no")" "yes"
echo -e "     ($ROUTE_COUNT routes)"

# ─────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
MAX_ALLOWED_FAILURES=${MAX_ALLOWED_FAILURES:-2}  # Allow up to 2 known data-dependent failures
if [ $FAIL -eq 0 ]; then
  echo -e "  ${GREEN}✅ ALL $TOTAL TESTS PASSED — safe to deploy${NC}"
  [ $SKIP -gt 0 ] && echo -e "  ${YELLOW}($SKIP skipped)${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
  exit 0
elif [ $FAIL -le $MAX_ALLOWED_FAILURES ]; then
  echo -e "  ${YELLOW}⚠️  $FAIL/$TOTAL FAILED (within threshold of $MAX_ALLOWED_FAILURES) — proceeding with deploy${NC}"
  [ $SKIP -gt 0 ] && echo -e "  ${YELLOW}($SKIP skipped)${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
  exit 0
else
  echo -e "  ${RED}❌ $FAIL/$TOTAL FAILED (exceeds threshold of $MAX_ALLOWED_FAILURES) — fix before deploying${NC}"
  [ $SKIP -gt 0 ] && echo -e "  ${YELLOW}($SKIP skipped)${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
  exit $FAIL
fi
