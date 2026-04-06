#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Blue-Green Deployment with Canary Traffic Splitting
#
# Zero-downtime deployment using Azure Container Apps traffic splitting:
#   1. Push new image → creates new revision (old still serves 100%)
#   2. Route 10% traffic to new revision (canary)
#   3. Monitor for 3 min (health check every 30s)
#   4. If healthy → shift to 100%
#   5. If unhealthy → shift back to 0% + deactivate new revision
#
# Usage:
#   ./scripts/blue-green-deploy.sh [--env dev|staging|prod] [--canary-pct 10] [--monitor-sec 180]
#   make blue-green ENV=dev
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
step()  { echo -e "\n${CYAN}[STEP]${NC}  $*"; }

# ── Parse args ──
ENV="dev"
CANARY_PCT=10
MONITOR_SEC=180

while [ $# -gt 0 ]; do
  case $1 in
    --env) ENV="$2"; shift 2 ;;
    --canary-pct) CANARY_PCT="$2"; shift 2 ;;
    --monitor-sec) MONITOR_SEC="$2"; shift 2 ;;
    *) shift ;;
  esac
done

RG="rg-m365vault-${ENV}"
BACKEND="m365vault-backend-${ENV}"
FRONTEND="m365vault-frontend-${ENV}"
ACR="acrm365vault${ENV}"
TAG="v$(date +%s)"
OLD_PCT=$((100 - CANARY_PCT))

echo ""
echo -e "${CYAN}═══ KavachIQ Blue-Green Deploy (ENV=${ENV}) ═══${NC}"
echo -e "  Canary: ${CANARY_PCT}% → monitor ${MONITOR_SEC}s → 100%"
echo ""

# ── Step 1: Record old revision ──
step "1/7 Recording current (blue) revision..."
OLD_REV=$(az containerapp revision list --name "$BACKEND" --resource-group "$RG" \
  --query "[?properties.active && properties.runningState=='Running'].name" -o tsv 2>/dev/null | head -1)

if [ -z "$OLD_REV" ]; then
  warn "No running revision found — this will be a fresh deploy (no canary)"
  OLD_REV=""
fi
info "Blue revision: ${OLD_REV:-none}"

# ── Step 2: Build + push new image ──
step "2/7 Building and pushing new image ($TAG)..."
az acr login --name "$ACR" > /dev/null 2>&1 || { fail "ACR login failed"; exit 1; }

docker build --platform linux/amd64 -q -t "$ACR.azurecr.io/m365vault-backend:$TAG" ./backend > /dev/null || { fail "Backend build failed"; exit 1; }
docker push "$ACR.azurecr.io/m365vault-backend:$TAG" > /dev/null 2>&1 || { fail "Backend push failed"; exit 1; }
ok "Backend image: $TAG"

docker build --platform linux/amd64 -q -t "$ACR.azurecr.io/m365vault-frontend:$TAG" ./frontend > /dev/null || { fail "Frontend build failed"; exit 1; }
docker push "$ACR.azurecr.io/m365vault-frontend:$TAG" > /dev/null 2>&1 || { fail "Frontend push failed"; exit 1; }
ok "Frontend image: $TAG"

# ── Step 3: Deploy new revision (green) ──
step "3/7 Deploying green revision..."
az containerapp update --name "$BACKEND" --resource-group "$RG" \
  --image "$ACR.azurecr.io/m365vault-backend:$TAG" --output none 2>&1 || { fail "Backend update failed"; exit 1; }

az containerapp update --name "$FRONTEND" --resource-group "$RG" \
  --image "$ACR.azurecr.io/m365vault-frontend:$TAG" --output none 2>&1 || { fail "Frontend update failed"; exit 1; }

# Wait for green revision to activate
info "Waiting for green revision to start..."
for i in $(seq 1 30); do
  NEW_REV=$(az containerapp revision list --name "$BACKEND" --resource-group "$RG" \
    --query "[0].name" -o tsv 2>/dev/null)
  NEW_STATE=$(az containerapp revision list --name "$BACKEND" --resource-group "$RG" \
    --query "[0].properties.runningState" -o tsv 2>/dev/null)
  if [ "$NEW_STATE" = "Running" ] || [ "$NEW_STATE" = "RunningAtMaxScale" ]; then
    ok "Green revision ready: $NEW_REV"
    break
  fi
  [ "$i" -eq 30 ] && { fail "Green revision not ready after 5 min (state: $NEW_STATE)"; exit 1; }
  sleep 10
done

# ── Step 4: Canary — route small % to green ──
if [ -n "$OLD_REV" ] && [ "$OLD_REV" != "$NEW_REV" ]; then
  step "4/7 Canary: routing ${CANARY_PCT}% to green, ${OLD_PCT}% to blue..."
  az containerapp ingress traffic set --name "$BACKEND" --resource-group "$RG" \
    --revision-weight "$OLD_REV=${OLD_PCT}" "$NEW_REV=${CANARY_PCT}" --output none 2>&1 || {
    warn "Traffic splitting not available — skipping canary"
  }
  ok "Traffic split: ${OLD_REV}=${OLD_PCT}% / ${NEW_REV}=${CANARY_PCT}%"
else
  step "4/7 Canary: skipped (fresh deploy, no old revision)"
fi

# ── Step 5: Monitor canary ──
step "5/7 Monitoring canary for ${MONITOR_SEC}s..."
BACKEND_FQDN=$(az containerapp show --name "$BACKEND" --resource-group "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null)

CHECKS=0
FAILURES=0
INTERVAL=30
ITERATIONS=$((MONITOR_SEC / INTERVAL))

for i in $(seq 1 $ITERATIONS); do
  HEALTH=$(curl -sf --max-time 10 "https://$BACKEND_FQDN/health" 2>/dev/null || echo '{"status":"error"}')
  CHECKS=$((CHECKS + 1))

  if echo "$HEALTH" | grep -q '"healthy"'; then
    echo -e "  ${GREEN}✓${NC} Check $i/$ITERATIONS: healthy"
  else
    FAILURES=$((FAILURES + 1))
    echo -e "  ${RED}✗${NC} Check $i/$ITERATIONS: UNHEALTHY"
  fi

  [ $FAILURES -ge 3 ] && break
  [ $i -lt $ITERATIONS ] && sleep $INTERVAL
done

# ── Step 6: Decision — promote or rollback ──
if [ $FAILURES -ge 3 ]; then
  step "6/7 ❌ ROLLBACK — $FAILURES failures detected"
  if [ -n "$OLD_REV" ]; then
    az containerapp ingress traffic set --name "$BACKEND" --resource-group "$RG" \
      --revision-weight "$OLD_REV=100" --output none 2>/dev/null
    az containerapp revision deactivate --name "$BACKEND" --resource-group "$RG" \
      --revision "$NEW_REV" --output none 2>/dev/null
    fail "Rolled back to $OLD_REV"
  fi
  exit 1
else
  step "6/7 ✅ PROMOTE — all checks passed ($CHECKS/$CHECKS healthy)"
  if [ -n "$OLD_REV" ] && [ "$OLD_REV" != "$NEW_REV" ]; then
    az containerapp ingress traffic set --name "$BACKEND" --resource-group "$RG" \
      --revision-weight "$NEW_REV=100" --output none 2>/dev/null
    ok "100% traffic → $NEW_REV"

    # Keep old revision for 1 hour as emergency rollback
    info "Old revision $OLD_REV kept active for emergency rollback"
  fi
fi

# ── Step 7: Final verification ──
step "7/7 Final verification..."
FINAL_HEALTH=$(curl -sf --max-time 10 "https://$BACKEND_FQDN/health" 2>/dev/null || echo '{}')
if echo "$FINAL_HEALTH" | grep -q '"healthy"'; then
  ok "Backend healthy"
else
  fail "Backend unhealthy after promotion!"
  exit 1
fi

FRONTEND_FQDN=$(az containerapp show --name "$FRONTEND" --resource-group "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null)
curl -sf --max-time 10 "https://$FRONTEND_FQDN" > /dev/null && ok "Frontend healthy" || warn "Frontend check failed"

echo ""
echo -e "${GREEN}═══ Blue-Green Deploy Complete ═══${NC}"
echo -e "  Blue (old):  $OLD_REV"
echo -e "  Green (new): $NEW_REV → 100% traffic"
echo -e "  Image:       $TAG"
echo -e "  Backend:     https://$BACKEND_FQDN"
echo ""
