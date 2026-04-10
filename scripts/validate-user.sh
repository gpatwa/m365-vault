#!/bin/bash
# KavachIQ User Onboarding Validation
#
# Validates every dashboard metric, page endpoint, and data consistency
# for a specific user. Catches tenant scoping bugs, stale data, and
# misconfigured seed data.
#
# Usage:
#   ./scripts/validate-user.sh <username> <password> [backend_url]
#
# Examples:
#   ./scripts/validate-user.sh prospect Prospect2026!
#   ./scripts/validate-user.sh demo ShieldiDemo2026! https://api.kavachiq.com
#   ./scripts/validate-user.sh admin ShieldiAdmin2026!

set -uo pipefail
# Don't exit on individual check failures — we report them at the end

USER="${1:?Usage: $0 <username> <password> [backend_url]}"
PASS="${2:?Usage: $0 <username> <password> [backend_url]}"
BACKEND="${3:-https://api.kavachiq.com}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

check() {
  local name="$1" condition="$2" detail="${3:-}"
  if [ "$condition" = "true" ]; then
    echo -e "  ${GREEN}✅${NC} $name ${detail:+($detail)}"
    ((PASS_COUNT++))
  else
    echo -e "  ${RED}❌${NC} $name ${detail:+($detail)}"
    ((FAIL_COUNT++))
  fi
}

warn() {
  local name="$1" detail="${2:-}"
  echo -e "  ${YELLOW}⚠️${NC}  $name ${detail:+($detail)}"
  ((WARN_COUNT++))
}

# ── Login ──
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  KavachIQ User Validation: $USER"
echo "  Backend: $BACKEND"
echo "═══════════════════════════════════════════════════════"
echo ""

TOKEN=$(curl -s --max-time 10 -X POST "$BACKEND/api/auth/login" \
  -d "username=$USER&password=$PASS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -z "$TOKEN" ] || [ ${#TOKEN} -lt 10 ]; then
  echo -e "${RED}LOGIN FAILED for $USER${NC}"
  exit 1
fi
echo -e "Logged in as ${GREEN}$USER${NC}"

AUTH="Authorization: Bearer $TOKEN"
API() { sleep 1; curl -s --max-time 15 -H "$AUTH" "$BACKEND/api$1" 2>/dev/null; }
PY() { python3 -c "$1" 2>/dev/null; }

# ── 1. Session & Onboarding ──
echo ""
echo "── 1. Session & Onboarding ──"

SESSION=$(API "/auth/session")
HAS_TENANTS=$(echo "$SESSION" | PY "import sys,json; print('true' if json.load(sys.stdin).get('has_tenants') else 'false')")
TENANT_COUNT=$(echo "$SESSION" | PY "import sys,json; print(json.load(sys.stdin).get('tenant_count',0))")
ONBOARDING=$(echo "$SESSION" | PY "import sys,json; d=json.load(sys.stdin).get('onboarding',{}); print(f\"{d.get('completed',0)}/{d.get('total',6)}\")")
ROLE=$(echo "$SESSION" | PY "import sys,json; print(json.load(sys.stdin).get('role','?'))")

check "Has tenants" "$HAS_TENANTS" "tenant_count=$TENANT_COUNT"
check "Onboarding progress" "$([ "$(echo "$ONBOARDING" | cut -d/ -f1)" -ge 4 ] && echo true || echo false)" "$ONBOARDING steps"
echo "  ℹ️  Role: $ROLE"

# ── 2. Tenants ──
echo ""
echo "── 2. Tenants ──"

TENANTS=$(API "/tenants/")
TENANT_NAMES=$(echo "$TENANTS" | PY "import sys,json; ts=json.load(sys.stdin); [print(f\"  id={t['id']} {t['name']} ({t['status']})\") for t in ts]")
TENANT_IDS=$(echo "$TENANTS" | PY "import sys,json; print(','.join(str(t['id']) for t in json.load(sys.stdin)))")
FIRST_TENANT=$(echo "$TENANTS" | PY "import sys,json; ts=json.load(sys.stdin); print(ts[0]['id'] if ts else '')")
echo "$TENANT_NAMES"

# Consistency: tenant_count in session should match actual tenants
ACTUAL_COUNT=$(echo "$TENANTS" | PY "import sys,json; print(len(json.load(sys.stdin)))")
check "Session tenant_count matches actual" "$([ "$TENANT_COUNT" = "$ACTUAL_COUNT" ] && echo true || echo false)" "session=$TENANT_COUNT actual=$ACTUAL_COUNT"

# ── 3. Dashboard Summary ──
echo ""
echo "── 3. Dashboard Summary ──"

SUMMARY=$(API "/dashboard/summary")
PROTECTED=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('total_protected',0))")
TOTAL_OBJ=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('total_objects',0))")
SUMMARY_TENANTS=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('tenants',0))")
BACKUP_SUCCESS=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('jobs_24h',{}).get('backup_successful',0))")
BACKUP_FAILED=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('jobs_24h',{}).get('backup_failed',0))")
BACKUP_TOTAL=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('jobs_24h',{}).get('backup_total',0))")
SNAPSHOTS=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('snapshots',{}).get('total',0))")
SIZE_GB=$(echo "$SUMMARY" | PY "import sys,json; print(json.load(sys.stdin).get('snapshots',{}).get('total_size_gb',0))")

echo "  Protected: $PROTECTED/$TOTAL_OBJ objects"
echo "  Backups (24h): $BACKUP_SUCCESS successful, $BACKUP_FAILED failed (total: $BACKUP_TOTAL)"
echo "  Snapshots: $SNAPSHOTS, Size: ${SIZE_GB} GB"

# Consistency: summary tenants should match session
check "Summary tenant count matches session" "$([ "$SUMMARY_TENANTS" = "$ACTUAL_COUNT" ] && echo true || echo false)" "summary=$SUMMARY_TENANTS session=$ACTUAL_COUNT"

# Consistency: protected should be > 0 if user has tenants
check "Has protected objects" "$([ "$PROTECTED" -gt 0 ] && echo true || echo false)" "$PROTECTED objects"

# Consistency: successful backups should be > 0
if [ "$BACKUP_SUCCESS" -gt 0 ]; then
  check "Backups running" "true" "$BACKUP_SUCCESS successful"
else
  warn "No successful backups in 24h" "backup_successful=0"
fi

# ── 4. Health Score ──
echo ""
echo "── 4. Health Score ──"

if [ -n "$FIRST_TENANT" ]; then
  HEALTH=$(API "/health/score?tenant_id=$FIRST_TENANT")
  SCORE=$(echo "$HEALTH" | PY "import sys,json; print(json.load(sys.stdin).get('score','?'))")
  ANOMALIES=$(echo "$HEALTH" | PY "import sys,json; print(json.load(sys.stdin).get('details',{}).get('active_anomalies','?'))")
  SUCCESS_RATE=$(echo "$HEALTH" | PY "import sys,json; print(json.load(sys.stdin).get('components',{}).get('success_rate','?'))")

  echo "  Score: $SCORE/100"
  echo "  Success rate: $SUCCESS_RATE%"
  echo "  Active anomalies: $ANOMALIES"

  check "Health score > 0" "$([ "$SCORE" != "?" ] && [ "$SCORE" -gt 0 ] && echo true || echo false)" "score=$SCORE"
  check "Anomalies within ceiling (≤10)" "$([ "$ANOMALIES" != "?" ] && [ "$ANOMALIES" -le 10 ] && echo true || echo false)" "anomalies=$ANOMALIES"
fi

# ── 5. License & Usage ──
echo ""
echo "── 5. License & Usage ──"

LICENSE=$(API "/usage/license")
LIC_OBJECTS=$(echo "$LICENSE" | PY "import sys,json; u=json.load(sys.stdin).get('usage',[]); print(next((x['current'] for x in u if x['name']=='Protected Objects'),0))")
LIC_TENANTS=$(echo "$LICENSE" | PY "import sys,json; u=json.load(sys.stdin).get('usage',[]); print(next((x['current'] for x in u if x['name']=='Tenants'),0))")
LIC_TIER=$(echo "$LICENSE" | PY "import sys,json; print(json.load(sys.stdin).get('tier','?'))")

echo "  Tier: $LIC_TIER"
echo "  Objects: $LIC_OBJECTS, Tenants: $LIC_TENANTS"

# Consistency: license objects should match dashboard protected
check "License objects = dashboard protected" "$([ "$LIC_OBJECTS" = "$PROTECTED" ] && echo true || echo false)" "license=$LIC_OBJECTS dashboard=$PROTECTED"

# Consistency: license tenants should match actual
check "License tenants = actual" "$([ "$LIC_TENANTS" = "$ACTUAL_COUNT" ] && echo true || echo false)" "license=$LIC_TENANTS actual=$ACTUAL_COUNT"

# ── 6. Recovery Confidence ──
echo ""
echo "── 6. Recovery Confidence ──"

if [ -n "$FIRST_TENANT" ]; then
  RECOVERY=$(API "/recovery/confidence?tenant_id=$FIRST_TENANT")
  REC_SCORE=$(echo "$RECOVERY" | PY "import sys,json; print(json.load(sys.stdin).get('score','?'))")
  REC_GRADE=$(echo "$RECOVERY" | PY "import sys,json; print(json.load(sys.stdin).get('grade','?'))")
  FRESHNESS=$(echo "$RECOVERY" | PY "import sys,json; print(json.load(sys.stdin).get('factors',{}).get('freshness',{}).get('score','?'))")
  COMPLETENESS=$(echo "$RECOVERY" | PY "import sys,json; print(json.load(sys.stdin).get('factors',{}).get('completeness',{}).get('score','?'))")
  VALIDATION=$(echo "$RECOVERY" | PY "import sys,json; print(json.load(sys.stdin).get('factors',{}).get('validation',{}).get('score','?'))")

  echo "  Score: $REC_SCORE/100 (Grade: $REC_GRADE)"
  echo "  Freshness: $FRESHNESS%, Completeness: $COMPLETENESS%, Validation: $VALIDATION%"

  check "Recovery endpoint works" "$([ "$REC_SCORE" != "?" ] && echo true || echo false)" "score=$REC_SCORE"
fi

# ── 7. Workload Pages ──
echo ""
echo "── 7. Workload Pages ──"

# Workload list endpoints (factory-generated, different paths per workload)
for WL_ENTRY in "exchange:/exchange/mailboxes" "onedrive:/onedrive/accounts" "sharepoint:/sharepoint/sites" "teams:/teams/teams" "entra-id:/entra-id/summary"; do
  WL_NAME="${WL_ENTRY%%:*}"
  WL_PATH="${WL_ENTRY#*:}"
  sleep 1
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "$AUTH" "$BACKEND/api$WL_PATH?tenant_id=$FIRST_TENANT" 2>/dev/null)
  if [ "$STATUS" = "200" ]; then
    check "$WL_NAME page" "true" "HTTP 200"
  elif [ "$STATUS" = "403" ]; then
    warn "$WL_NAME page" "HTTP 403 — tenant access denied"
  else
    check "$WL_NAME page" "false" "HTTP $STATUS"
  fi
done

# ── 8. Jobs Page ──
echo ""
echo "── 8. Jobs ──"

JOBS=$(API "/jobs/backup?page_size=5")
JOBS_TOTAL=$(echo "$JOBS" | PY "import sys,json; print(json.load(sys.stdin).get('total','?'))")
JOBS_TIDS=$(echo "$JOBS" | PY "import sys,json; d=json.load(sys.stdin); print(','.join(sorted(set(str(i.get('tenant_id','?')) for i in d.get('items',[])))))")

echo "  Backup jobs: $JOBS_TOTAL total"
check "Jobs scoped to user tenants" "$(echo "$JOBS_TIDS" | python3 -c "
import sys
tids = set(sys.stdin.read().strip().split(',')) - {''}
allowed = set('$TENANT_IDS'.split(','))
print('true' if not tids or tids <= allowed else 'false')
")" "tenant_ids in jobs: {$JOBS_TIDS}"

# ── 9. Failed Items ──
echo ""
echo "── 9. Failed Items ──"

FAILED=$(API "/failed-items/")
FAILED_STATUS=$(echo "$FAILED" | PY "import sys,json; d=json.load(sys.stdin); print(d.get('total',0) if isinstance(d,dict) else 'error')")
check "Failed items endpoint" "$([ "$FAILED_STATUS" != "error" ] && echo true || echo false)" "total=$FAILED_STATUS"

# ── 10. Reports ──
echo ""
echo "── 10. Reports ──"

for REPORT in backup-performance storage-analytics sla-compliance; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "$AUTH" "$BACKEND/api/reports/$REPORT" 2>/dev/null)
  check "Report: $REPORT" "$([ "$STATUS" = "200" ] && echo true || echo false)" "HTTP $STATUS"
done

# ── 11. Diagnostics ──
echo ""
echo "── 11. Diagnostics ──"

SECRETS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "$AUTH" "$BACKEND/api/diagnostics/secrets" 2>/dev/null)
check "Secret diagnostics" "$([ "$SECRETS_STATUS" = "200" ] && echo true || echo false)" "HTTP $SECRETS_STATUS"

METRICS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$BACKEND/metrics" 2>/dev/null)
check "Prometheus /metrics" "$([ "$METRICS_STATUS" = "200" ] && echo true || echo false)" "HTTP $METRICS_STATUS"

# ── 12. Cost Attribution ──
echo ""
echo "── 12. Cost Attribution ──"

if [ -n "$FIRST_TENANT" ]; then
  USAGE=$(API "/usage/tenant/$FIRST_TENANT")
  HAS_COST=$(echo "$USAGE" | PY "import sys,json; print('true' if 'cost_breakdown' in json.load(sys.stdin) else 'false')")
  check "Cost breakdown in usage" "$HAS_COST"
fi

# ── SUMMARY ──
echo ""
echo "═══════════════════════════════════════════════════════"
TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "  ${GREEN}✅ ALL $TOTAL CHECKS PASSED${NC} ($WARN_COUNT warnings)"
else
  echo -e "  ${RED}❌ $FAIL_COUNT/$TOTAL FAILED${NC} ($WARN_COUNT warnings)"
fi
echo "═══════════════════════════════════════════════════════"

exit $FAIL_COUNT
