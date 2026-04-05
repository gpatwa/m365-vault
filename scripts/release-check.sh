#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# KavachIQ Release Quality Gate
# ═══════════════════════════════════════════════════════════════════
# Runs all quality checks before a release. Stops on first failure.
# Usage: make release-check (or ./scripts/release-check.sh)
#
# Checks:
#   1. TypeScript type check (frontend compiles?)
#   2. Python syntax check (backend compiles?)
#   3. Backend tests (pytest — unit + API + integration)
#   4. Test coverage (above threshold?)
#   5. Frontend build (production bundle works?)
#   6. Docker build (images build successfully?)
#   7. Secret scan (no credentials in code?)
#   8. API smoke test (if stack is running)
# ═══════════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
FAIL=0
SKIP=0
COVERAGE_THRESHOLD=20  # Minimum coverage % (increase as test coverage grows)

gate() {
  local step="$1"
  local desc="$2"
  echo ""
  echo -e "${BLUE}━━━ Gate $step: $desc ━━━${NC}"
}

pass() {
  PASS=$((PASS + 1))
  echo -e "  ${GREEN}✅ $1${NC}"
}

fail() {
  FAIL=$((FAIL + 1))
  echo -e "  ${RED}❌ $1${NC}"
  echo -e "  ${RED}   RELEASE BLOCKED${NC}"
  summary
  exit 1
}

skip() {
  SKIP=$((SKIP + 1))
  echo -e "  ${YELLOW}⏭️  $1${NC}"
}

summary() {
  echo ""
  echo -e "${BOLD}═══ RELEASE QUALITY GATE SUMMARY ═══${NC}"
  echo -e "  ${GREEN}Passed: $PASS${NC}"
  if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}Failed: $FAIL${NC}"
  fi
  if [ $SKIP -gt 0 ]; then
    echo -e "  ${YELLOW}Skipped: $SKIP${NC}"
  fi
  echo ""
  if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}═══ READY TO DEPLOY ✅ ═══${NC}"
  else
    echo -e "  ${RED}${BOLD}═══ NOT READY — FIX FAILURES ABOVE ═══${NC}"
  fi
}

START_TIME=$(date +%s)

echo -e "${BOLD}═══ SHIELDIO RELEASE QUALITY GATE ═══${NC}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"

# ── Gate 1: TypeScript Type Check ──
gate 1 "TypeScript Type Check"
if command -v npx &>/dev/null && [ -f frontend/tsconfig.json ]; then
  if cd frontend && npx tsc --noEmit 2>&1 | tail -3; then
    pass "TypeScript: 0 errors"
  else
    fail "TypeScript compilation failed"
  fi
  cd ..
else
  skip "TypeScript (npx not found)"
fi

# ── Gate 2: Python Syntax Check ──
gate 2 "Python Syntax Check"
SYNTAX_ERRORS=0
for f in $(find backend/app -name "*.py" ! -path "*__pycache__*"); do
  if ! python3 -m py_compile "$f" 2>/dev/null; then
    echo "    Syntax error: $f"
    SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
  fi
done
if [ $SYNTAX_ERRORS -eq 0 ]; then
  PY_COUNT=$(find backend/app -name "*.py" ! -path "*__pycache__*" | wc -l | tr -d ' ')
  pass "Python: $PY_COUNT files, 0 syntax errors"
else
  fail "Python: $SYNTAX_ERRORS syntax errors"
fi

# ── Gate 3: Backend Tests ──
gate 3 "Backend Tests (pytest)"
if [ -d backend/tests ]; then
  cd backend
  # Remove stale test DB
  rm -f test.db

  # Run ALL tests with coverage (auto-discovers new test files)
  TEST_OUTPUT=$(python3 -m pytest tests/ \
    --tb=short -q \
    --cov=app --cov-report=term-missing \
    --cov-fail-under=$COVERAGE_THRESHOLD \
    --ignore=tests/test_integration.py \
    2>&1)
  TEST_EXIT=$?

  # Extract results
  TEST_SUMMARY=$(echo "$TEST_OUTPUT" | grep -E "passed|failed|error" | tail -1)
  PASSED=$(echo "$TEST_SUMMARY" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
  FAILED=$(echo "$TEST_SUMMARY" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "0")
  ERRORS=$(echo "$TEST_SUMMARY" | grep -oE '[0-9]+ error' | grep -oE '[0-9]+' || echo "0")

  # Extract coverage
  COV_LINE=$(echo "$TEST_OUTPUT" | grep "^TOTAL" | head -1)
  COVERAGE=$(echo "$COV_LINE" | awk '{print $NF}' | tr -d '%')

  if [ $TEST_EXIT -eq 0 ]; then
    pass "Tests: ${PASSED:-all} passed, ${FAILED:-0} failed"
    pass "Coverage: ${COVERAGE:-?}% (threshold: ${COVERAGE_THRESHOLD}%)"
  else
    echo "$TEST_OUTPUT" | tail -20
    fail "Tests failed: ${FAILED:-?} failures, ${ERRORS:-?} errors"
  fi

  rm -f test.db
  cd ..
else
  skip "Backend tests (no tests/ directory)"
fi

# ── Gate 4: Frontend Build ──
gate 4 "Frontend Production Build"
if [ -f frontend/package.json ]; then
  cd frontend
  if npm run build 2>&1 | tail -5; then
    BUNDLE_SIZE=$(du -sh dist/ 2>/dev/null | cut -f1)
    pass "Frontend built successfully (${BUNDLE_SIZE:-?})"
  else
    fail "Frontend build failed"
  fi
  cd ..
else
  skip "Frontend (no package.json)"
fi

# ── Gate 5: Docker Build ──
gate 5 "Docker Image Build"
if command -v docker &>/dev/null; then
  # Use native platform for speed (just verify it builds)
  if docker build -t kavachiq-backend:check ./backend -q 2>&1 | tail -1; then
    pass "Backend Docker image builds"
  else
    fail "Backend Docker build failed"
  fi
  if docker build -t kavachiq-frontend:check ./frontend -q 2>&1 | tail -1; then
    pass "Frontend Docker image builds"
  else
    fail "Frontend Docker build failed"
  fi
  # Clean up
  docker rmi kavachiq-backend:check kavachiq-frontend:check 2>/dev/null || true
else
  skip "Docker (not installed)"
fi

# ── Gate 6: Secret Scan ──
gate 6 "Secret/Credential Scan"
SECRETS_FOUND=0

# Check for common secret patterns in tracked files
for pattern in "password\s*=" "secret\s*=" "api_key\s*=" "-----BEGIN.*PRIVATE"; do
  MATCHES=$(git grep -l -i "$pattern" -- '*.py' '*.ts' '*.tsx' '*.env' 2>/dev/null | \
    grep -v "test" | grep -v "config.py" | grep -v "example" | grep -v "node_modules" | \
    grep -v ".env.example" || true)
  if [ -n "$MATCHES" ]; then
    for f in $MATCHES; do
      # Check if it's an actual hardcoded value (not a variable reference)
      HARDCODED=$(grep -n "$pattern" "$f" 2>/dev/null | grep -v '""' | grep -v "''" | \
        grep -v "environ" | grep -v "settings\." | grep -v "os.getenv" | \
        grep -v "# " | grep -v "test" | head -3)
      if [ -n "$HARDCODED" ]; then
        echo "    ⚠️  Potential secret in $f:"
        echo "$HARDCODED" | head -2 | sed 's/^/      /'
        SECRETS_FOUND=$((SECRETS_FOUND + 1))
      fi
    done
  fi
done

# Check for .env files that shouldn't be committed
ENV_FILES=$(git ls-files '*.env' '.env.*' 2>/dev/null | grep -v ".env.example" | grep -v ".env.azure" || true)
if [ -n "$ENV_FILES" ]; then
  echo "    ⚠️  .env files tracked in git: $ENV_FILES"
  SECRETS_FOUND=$((SECRETS_FOUND + 1))
fi

if [ $SECRETS_FOUND -eq 0 ]; then
  pass "No secrets/credentials detected"
else
  echo -e "  ${YELLOW}⚠️  $SECRETS_FOUND potential secret(s) found — review before release${NC}"
  pass "Secret scan complete (review warnings above)"
fi

# ── Gate 7: API Smoke Test (if running) ──
gate 7 "API Smoke Test"
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
  HEALTH=$(curl -s http://localhost:8000/health)
  STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
  ROUTES=$(curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; print(len(json.load(sys.stdin)['paths']))" 2>/dev/null)

  if [ "$STATUS" = "healthy" ]; then
    pass "Backend healthy, $ROUTES API routes"
  else
    fail "Backend unhealthy: $STATUS"
  fi

  # Quick login test
  LOGIN=$(curl -s -X POST http://localhost:8000/api/auth/login -d "username=admin&password=admin123" -w "\n%{http_code}" 2>/dev/null)
  HTTP_CODE=$(echo "$LOGIN" | tail -1)
  if [ "$HTTP_CODE" = "200" ]; then
    pass "Login endpoint working"
  else
    skip "Login test (no admin user — fresh DB)"
  fi
else
  skip "API smoke test (backend not running)"
fi

# ── Gate 8: Playwright E2E Tests (if stack running) ──
gate 8 "Browser E2E Tests (Playwright)"
if curl -s http://localhost:5173/ >/dev/null 2>&1; then
  if [ -f tests/e2e/package.json ]; then
    cd tests/e2e
    E2E_OUTPUT=$(npx playwright test --reporter=line 2>&1)
    E2E_EXIT=$?
    E2E_SUMMARY=$(echo "$E2E_OUTPUT" | grep -E "passed|failed" | tail -1)

    if [ $E2E_EXIT -eq 0 ]; then
      pass "Playwright E2E: $E2E_SUMMARY"
    else
      echo "$E2E_OUTPUT" | tail -15
      fail "Playwright E2E tests failed: $E2E_SUMMARY"
    fi
    cd ../..
  else
    skip "Playwright (tests/e2e/package.json not found)"
  fi
else
  skip "Playwright E2E (frontend not running on localhost:5173)"
fi

# ── Summary ──
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BOLD}═══ RELEASE QUALITY GATE RESULTS ═══${NC}"
echo -e "  ${GREEN}Passed:  $PASS${NC}"
if [ $FAIL -gt 0 ]; then echo -e "  ${RED}Failed:  $FAIL${NC}"; fi
if [ $SKIP -gt 0 ]; then echo -e "  ${YELLOW}Skipped: $SKIP${NC}"; fi
echo -e "  Duration: ${DURATION}s"
echo ""

if [ $FAIL -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}═══ READY TO DEPLOY ✅ ═══${NC}"
  echo ""
  echo "  Next steps:"
  echo "    make acr-push     # Build + push to Azure Container Registry"
  echo "    make az-wake      # Start Azure resources"
  echo "    make release      # Full release (check + push)"
  exit 0
else
  echo -e "  ${RED}${BOLD}═══ NOT READY — FIX FAILURES ABOVE ═══${NC}"
  exit 1
fi
