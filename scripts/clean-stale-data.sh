#!/bin/bash
# KavachIQ — Clean Stale Data
#
# Removes dead-lettered jobs, stale failed items, orphan protected objects,
# and excess anomalies. Safe for pre-launch environments with no customers.
#
# Usage:
#   ./scripts/clean-stale-data.sh [backend_url]
#
# Prerequisites:
#   - Admin credentials (uses admin user)
#   - No active customers (this deletes data permanently)

set -uo pipefail

BACKEND="${1:-https://api.kavachiq.com}"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════"
echo "  KavachIQ Stale Data Cleanup"
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
echo -e "${GREEN}Logged in as admin${NC}"
AUTH="Authorization: Bearer $TOKEN"

echo ""
echo "── Pre-cleanup state ──"

# Check current state
curl -s -H "$AUTH" "$BACKEND/api/jobs/backup?page_size=1&status=dead_letter" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  Dead-lettered jobs: {d.get(\"total\", 0)}')
" 2>/dev/null

curl -s -H "$AUTH" "$BACKEND/api/failed-items/summary" | python3 -c "
import sys, json
d = json.load(sys.stdin)
total = sum(w.get('total',0) for w in d.get('by_workload',{}).values())
print(f'  Failed items (all): {total}')
" 2>/dev/null

curl -s -H "$AUTH" "$BACKEND/api/health/anomalies?active_only=false&page_size=1" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  Anomaly events: {d.get(\"total\", 0)}')
" 2>/dev/null

echo ""
echo "── Cleanup (via direct DB — requires Docker PG or Azure PG access) ──"
echo ""
echo "Run these SQL commands against the production database:"
echo ""

cat << 'SQL'
-- 1. Delete dead-lettered backup jobs (internal failures, not recoverable)
DELETE FROM backup_jobs WHERE status::text = 'dead_letter';

-- 2. Delete failed items with internal error messages (not customer-actionable)
DELETE FROM failed_items
WHERE error_message ILIKE '%sqlalchemy%'
   OR error_message ILIKE '%concurrent operations%'
   OR error_message ILIKE '%session is provisioning%'
   OR error_message ILIKE '%asyncpg%'
   OR error_message ILIKE '%no active connection%'
   OR error_category::text = 'internal_transient';

-- 3. Delete resolved anomaly events (already cleaned up, just noise)
DELETE FROM anomaly_events WHERE resolved = 1;

-- 4. Resolve all remaining stale anomalies (cap already handles display)
UPDATE anomaly_events SET resolved = 1 WHERE resolved = 0;

-- 5. Verify clean state
SELECT 'backup_jobs' as table_name, COUNT(*) as total,
       COUNT(*) FILTER (WHERE status::text = 'dead_letter') as dead_letter
FROM backup_jobs;

SELECT 'failed_items' as table_name, COUNT(*) as total FROM failed_items;
SELECT 'anomaly_events' as table_name, COUNT(*) as total,
       COUNT(*) FILTER (WHERE resolved = 0) as active
FROM anomaly_events;
SQL

echo ""
echo "After running the SQL, restart the backend to verify clean state:"
echo "  ./scripts/validate-user.sh prospect Prospect2026!"
echo "  ./scripts/validate-user.sh demo ShieldiDemo2026!"
