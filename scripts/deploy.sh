#!/bin/bash
# Shieldio Deploy Script — build, push, deploy with health gates.
#
# Usage:
#   ./scripts/deploy.sh              # Full deploy: build → push → apply → verify
#   ./scripts/deploy.sh --skip-build # Skip build, just deploy + verify
#   ./scripts/deploy.sh --verify-only # Just run health checks
#
# Prerequisites:
#   - az cli logged in
#   - docker running
#   - terraform initialized in infra/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Config
ACR="acrm365vaultdev.azurecr.io"
RG="rg-m365vault-dev"
BACKEND_APP="m365vault-backend-dev"
FRONTEND_URL="https://m365vault-frontend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io"
BACKEND_URL="https://m365vault-backend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io"
SUBSCRIPTION="fb665ec0-d69f-49ef-a6e8-40b4a805ad8e"
MAX_WAIT=120  # seconds to wait for health

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[deploy]${NC} $1"; }
ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
fail() { echo -e "${RED}  ✗${NC} $1"; }

# ═══════════════════════════════════════════
# Health Check Functions
# ═══════════════════════════════════════════

check_backend_health() {
    local url="$BACKEND_URL/health"
    local response
    response=$(curl -s --max-time 10 "$url" 2>/dev/null) || { fail "Backend unreachable at $url"; return 1; }

    local status
    status=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)

    if [ "$status" = "healthy" ]; then
        local version
        version=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
        ok "Backend healthy (v$version)"
        return 0
    else
        fail "Backend unhealthy: $response"
        return 1
    fi
}

check_frontend() {
    local response
    response=$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" "$FRONTEND_URL/welcome" 2>/dev/null)
    if [ "$response" = "200" ]; then
        ok "Frontend serving (HTTP $response)"
        return 0
    else
        fail "Frontend not responding (HTTP $response)"
        return 1
    fi
}

check_demo_login() {
    local response
    response=$(curl -s --max-time 10 -X POST "$BACKEND_URL/api/auth/login" \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        -d 'username=demo&password=ShieldiDemo2026!' 2>/dev/null)

    local token
    token=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','')[:10])" 2>/dev/null)

    if [ -n "$token" ] && [ "$token" != "" ]; then
        ok "Demo login works"
        return 0
    else
        warn "Demo login failed (may need seeding)"
        return 1
    fi
}

check_database() {
    local response
    response=$(curl -s --max-time 10 "$BACKEND_URL/health" 2>/dev/null)
    local db_status
    db_status=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('checks',{}).get('database','unknown'))" 2>/dev/null)

    if [ "$db_status" = "healthy" ]; then
        ok "Database connected"
        return 0
    else
        fail "Database: $db_status"
        return 1
    fi
}

run_all_checks() {
    log "Running health checks..."
    local failures=0

    check_backend_health || ((failures++))
    check_database || ((failures++))
    check_frontend || ((failures++))
    check_demo_login || ((failures++))

    echo ""
    if [ $failures -eq 0 ]; then
        log "${GREEN}All health checks passed ✓${NC}"
        return 0
    else
        log "${RED}$failures health check(s) failed ✗${NC}"
        return 1
    fi
}

wait_for_healthy() {
    log "Waiting for backend to become healthy (max ${MAX_WAIT}s)..."
    local start=$SECONDS
    while [ $((SECONDS - start)) -lt $MAX_WAIT ]; do
        if check_backend_health 2>/dev/null; then
            return 0
        fi
        sleep 5
        echo -n "."
    done
    echo ""
    fail "Backend did not become healthy within ${MAX_WAIT}s"
    return 1
}

# ═══════════════════════════════════════════
# Deploy Steps
# ═══════════════════════════════════════════

step_pre_check() {
    log "=== PRE-DEPLOY CHECKS ==="
    echo ""

    # Check Azure CLI
    if ! az account show &>/dev/null; then
        fail "Azure CLI not logged in. Run: az login"
        exit 1
    fi
    ok "Azure CLI authenticated"

    # Check Docker
    if ! docker info &>/dev/null; then
        fail "Docker not running"
        exit 1
    fi
    ok "Docker running"

    # Check current system health (non-blocking)
    log "Current system status:"
    check_backend_health 2>/dev/null || warn "Backend currently unhealthy (will be replaced)"
    check_frontend 2>/dev/null || warn "Frontend currently unavailable"
    echo ""
}

step_build() {
    log "=== BUILDING IMAGES ==="
    echo ""

    az acr login --name acrm365vaultdev 2>/dev/null
    ok "ACR authenticated"

    log "Building backend (linux/amd64)..."
    docker build --platform linux/amd64 -t "$ACR/m365vault-backend:latest" backend/ --quiet
    ok "Backend image built"

    log "Building frontend (linux/amd64)..."
    docker build --platform linux/amd64 -t "$ACR/m365vault-frontend:latest" frontend/ --quiet
    ok "Frontend image built"

    log "Pushing images to ACR..."
    docker push "$ACR/m365vault-backend:latest" --quiet
    docker push "$ACR/m365vault-frontend:latest" --quiet
    ok "Images pushed to $ACR"
    echo ""
}

step_deploy() {
    log "=== DEPLOYING TO AZURE ==="
    echo ""

    # Save current backend revision for rollback
    PREV_REVISION=$(az containerapp revision list --name "$BACKEND_APP" --resource-group "$RG" \
        --query "[0].name" -o tsv 2>/dev/null)
    ok "Previous revision: $PREV_REVISION"

    log "Applying Terraform..."
    cd infra
    terraform apply -auto-approve \
        -var-file=environments/dev.tfvars \
        -var="subscription_id=$SUBSCRIPTION" \
        2>&1 | tail -3
    cd ..
    ok "Terraform applied"
    echo ""
}

step_verify() {
    log "=== POST-DEPLOY VERIFICATION ==="
    echo ""

    # Wait for backend to start
    if ! wait_for_healthy; then
        fail "Post-deploy health check FAILED"

        if [ -n "$PREV_REVISION" ]; then
            log "Rolling back to previous revision: $PREV_REVISION"
            az containerapp revision restart --name "$BACKEND_APP" --resource-group "$RG" \
                --revision "$PREV_REVISION" 2>/dev/null
            warn "Rollback initiated. Check manually."
        fi
        exit 1
    fi

    # Full health check suite
    run_all_checks
}

# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Shieldio Deploy — Health Gated     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

case "${1:-}" in
    --verify-only)
        run_all_checks
        ;;
    --skip-build)
        step_pre_check
        step_deploy
        step_verify
        ;;
    *)
        step_pre_check
        step_build
        step_deploy
        step_verify
        ;;
esac

echo ""
log "Deploy complete! Frontend: $FRONTEND_URL"
