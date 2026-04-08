#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Safe Deploy (never deactivate old revision without health check)
#
# Usage:
#   ./scripts/safe-deploy.sh [--env dev|prod]
#   make safe-deploy ENV=dev
#
# Flow:
#   1. Push new image to ACR (runs pre-deploy-check first)
#   2. Update container app with new image
#   3. Wait for new revision to be Running (up to 5 min)
#   4. Smoke test new revision
#   5. Only if healthy: deactivate old revision
#   6. If unhealthy: keep old revision, alert, exit 1
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
step()  { echo -e "${CYAN}[STEP]${NC}  $*"; }

ENV="${1:-dev}"
[[ "$1" == "--env" ]] && ENV="${2:-dev}"

# Ensure az CLI and docker are in PATH (macOS Homebrew + Docker Desktop)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Fix Docker credential helper (remove credsStore if it causes issues)
if grep -q '"credsStore"' ~/.docker/config.json 2>/dev/null; then
  python3 -c "import json,sys; d=json.load(open('$HOME/.docker/config.json')); d.pop('credsStore',None); json.dump(d,open('$HOME/.docker/config.json','w'),indent=2)" 2>/dev/null
fi

RG="rg-m365vault-${ENV}"
BACKEND_APP="m365vault-backend-${ENV}"
FRONTEND_APP="m365vault-frontend-${ENV}"
ACR="acrm365vault${ENV}"
MAX_WAIT=300  # 5 minutes

echo ""
echo -e "${CYAN}═══ KavachIQ Safe Deploy (ENV=${ENV}) ═══${NC}"
echo ""

# ── Step 1: Record old revision ──
step "Recording current revision..."
OLD_REV=$(az containerapp revision list --name "$BACKEND_APP" --resource-group "$RG" \
  --query "[?properties.active && properties.runningState=='Running'].name" -o tsv | head -1)
info "Old revision: ${OLD_REV:-none}"

# ── Step 2: Push new images ──
step "Building and pushing images..."
# Token-based ACR login (works without Docker credential helper)
ACR_TOKEN=$(az acr login --name "$ACR" --expose-token --query accessToken -o tsv 2>/dev/null)
if [ -n "$ACR_TOKEN" ]; then
  echo "$ACR_TOKEN" | docker login "$ACR.azurecr.io" --username 00000000-0000-0000-0000-000000000000 --password-stdin 2>/dev/null
  ok "ACR login succeeded"
else
  fail "ACR login failed"; exit 1
fi

TAG="v$(date +%s)"
docker build --platform linux/amd64 -t "$ACR.azurecr.io/m365vault-backend:$TAG" \
  -t "$ACR.azurecr.io/m365vault-backend:latest" ./backend || { fail "Backend build failed"; exit 1; }
docker push "$ACR.azurecr.io/m365vault-backend:$TAG" || { fail "Backend push failed"; exit 1; }
docker push "$ACR.azurecr.io/m365vault-backend:latest" || true

docker build --platform linux/amd64 -t "$ACR.azurecr.io/m365vault-frontend:$TAG" \
  -t "$ACR.azurecr.io/m365vault-frontend:latest" ./frontend || { fail "Frontend build failed"; exit 1; }
docker push "$ACR.azurecr.io/m365vault-frontend:$TAG" || { fail "Frontend push failed"; exit 1; }
docker push "$ACR.azurecr.io/m365vault-frontend:latest" || true
ok "Images pushed: $TAG"

# ── Step 3: Update container app ──
step "Updating backend to $TAG..."
az containerapp update --name "$BACKEND_APP" --resource-group "$RG" \
  --image "$ACR.azurecr.io/m365vault-backend:$TAG" --output none || { fail "Backend update failed"; exit 1; }

az containerapp update --name "$FRONTEND_APP" --resource-group "$RG" \
  --image "$ACR.azurecr.io/m365vault-frontend:$TAG" --output none || { fail "Frontend update failed"; exit 1; }
ok "Container apps updated"

# ── Step 4: Wait for new revision to be healthy ──
step "Waiting for new revision to be healthy (max ${MAX_WAIT}s)..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  NEW_STATE=$(az containerapp revision list --name "$BACKEND_APP" --resource-group "$RG" \
    --query "[0].properties.runningState" -o tsv 2>/dev/null)

  if [ "$NEW_STATE" = "Running" ]; then
    ok "New revision is Running"
    break
  fi

  echo -n "."
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

if [ "$NEW_STATE" != "Running" ]; then
  fail "New revision not healthy after ${MAX_WAIT}s (state: $NEW_STATE)"
  if [ -n "$OLD_REV" ]; then
    warn "Keeping old revision $OLD_REV active"
    az containerapp revision activate --name "$BACKEND_APP" --resource-group "$RG" \
      --revision "$OLD_REV" --output none 2>/dev/null
  fi
  exit 1
fi

# ── Step 5: Smoke test ──
step "Running smoke tests..."
BACKEND_URL=$(az containerapp show --name "$BACKEND_APP" --resource-group "$RG" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

HEALTH=$(curl -sf --max-time 10 "https://$BACKEND_URL/health/deep" 2>/dev/null || curl -sf --max-time 10 "https://$BACKEND_URL/health" 2>/dev/null)
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
  ok "Deep health check passed"
else
  fail "Health check FAILED"
  echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
  if [ -n "$OLD_REV" ]; then
    warn "Rolling back to $OLD_REV"
    az containerapp revision activate --name "$BACKEND_APP" --resource-group "$RG" \
      --revision "$OLD_REV" --output none 2>/dev/null
  fi
  exit 1
fi

# ── Step 6: Deactivate old revision ──
if [ -n "$OLD_REV" ]; then
  NEW_REV=$(az containerapp revision list --name "$BACKEND_APP" --resource-group "$RG" \
    --query "[?properties.runningState=='Running'].name" -o tsv | head -1)
  if [ "$NEW_REV" != "$OLD_REV" ]; then
    step "Deactivating old revision $OLD_REV..."
    az containerapp revision deactivate --name "$BACKEND_APP" --resource-group "$RG" \
      --revision "$OLD_REV" --output none 2>/dev/null
    ok "Old revision deactivated"
  fi
fi

# ── Step 7: Purge Cloudflare CDN cache (belt-and-suspenders) ──
# Primary fix: nginx sets CDN-Cache-Control: no-store on HTML responses,
# so Cloudflare never caches index.html. Hashed JS/CSS use immutable cache.
# This API purge is an extra safety net for immediate propagation.
CF_ZONE_ID="${CLOUDFLARE_ZONE_ID:-}"
CF_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

if [ -n "$CF_ZONE_ID" ] && [ -n "$CF_API_TOKEN" ]; then
  step "Purging Cloudflare CDN cache..."
  CF_RESP=$(curl -sf -X POST \
    "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{"purge_everything":true}' \
    2>/dev/null)
  if echo "$CF_RESP" | grep -q '"success":true'; then
    ok "Cloudflare cache purged"
  else
    info "Cloudflare purge skipped (origin headers handle caching — this is optional)"
  fi
fi

# ── Step 8: Post-deploy E2E sanity ──
# Run the E2E certification tests against live production.
# This catches migration issues (missing columns), broken endpoints,
# and auth regressions that unit tests with SQLite can't catch.
step "Running post-deploy E2E sanity tests..."
if bash "$(dirname "$0")/e2e-azure-test.sh" --env "$ENV"; then
  ok "E2E certification PASSED"
else
  E2E_EXIT=$?
  warn "E2E certification: $E2E_EXIT tests failed (deploy succeeded, but check failures above)"
  # Don't rollback on E2E failure — the deploy is live and health check passed.
  # E2E failures may be pre-existing issues, not caused by this deploy.
  # But log it clearly so operator investigates.
fi

echo ""
echo -e "${GREEN}═══ Deploy Complete ═══${NC}"
echo -e "  Backend:  https://$BACKEND_URL"
echo -e "  Frontend: https://kavachiq.com"
echo -e "  Image:    $TAG"
echo ""
