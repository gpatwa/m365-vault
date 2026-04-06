#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# KavachIQ — Monitoring & Alerting Setup
#
# Sets up Azure Monitor alerts for container health, plus
# UptimeRobot-compatible health check endpoint verification.
#
# Usage:
#   ./scripts/setup-monitoring.sh [--env dev|prod]
#   make setup-monitoring ENV=dev
# ──────────────────────────────────────────────────────────────────────
set -eo pipefail

ENV="${1:-dev}"
[[ "$1" == "--env" ]] && ENV="${2:-dev}"

RG="rg-m365vault-${ENV}"
BACKEND="m365vault-backend-${ENV}"

echo "═══ KavachIQ Monitoring Setup (ENV=${ENV}) ═══"
echo ""

# ── 1. Azure Monitor: Container restart alert ──
echo "── Setting up container restart alert ──"
BACKEND_ID=$(az containerapp show --name "$BACKEND" --resource-group "$RG" --query id -o tsv 2>/dev/null)

if [ -n "$BACKEND_ID" ]; then
  # Create action group for email alerts
  az monitor action-group create \
    --name "kavachiq-alerts-${ENV}" \
    --resource-group "$RG" \
    --short-name "kiq-alert" \
    --email-receiver "admin" "admin@kavachiq.com" \
    --output none 2>/dev/null && echo "  ✅ Action group created" || echo "  ⏭️  Action group exists"

  # Alert: backend revision unhealthy
  az monitor metrics alert create \
    --name "backend-unhealthy-${ENV}" \
    --resource-group "$RG" \
    --scopes "$BACKEND_ID" \
    --condition "avg RestartCount > 3" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 1 \
    --description "Backend container restarted 3+ times in 5 min" \
    --action "kavachiq-alerts-${ENV}" \
    --output none 2>/dev/null && echo "  ✅ Restart alert created" || echo "  ⚠️  Alert creation failed (metric may not be available)"
else
  echo "  ⏭️  Backend container not found"
fi

# ── 2. Health check endpoints ──
echo ""
echo "── Health check endpoints for uptime monitoring ──"
echo ""
echo "  Configure these in UptimeRobot (free tier: 50 monitors):"
echo ""
echo "  Monitor 1: Backend Health"
echo "    URL:      https://api.kavachiq.com/health"
echo "    Type:     HTTP(S) - Keyword"
echo "    Keyword:  \"healthy\""
echo "    Interval: 1 minute"
echo ""
echo "  Monitor 2: Frontend"
echo "    URL:      https://app.kavachiq.com/"
echo "    Type:     HTTP(S)"
echo "    Interval: 5 minutes"
echo ""
echo "  Monitor 3: Root Domain"
echo "    URL:      https://kavachiq.com/"
echo "    Type:     HTTP(S)"
echo "    Interval: 5 minutes"
echo ""
echo "  Monitor 4: API Response"
echo "    URL:      https://api.kavachiq.com/api/status"
echo "    Type:     HTTP(S) - Keyword"
echo "    Keyword:  \"running\""
echo "    Interval: 1 minute"
echo ""

# ── 3. Verify health endpoints work ──
echo "── Verifying health endpoints ──"
for url in \
  "https://api.kavachiq.com/health" \
  "https://app.kavachiq.com/" \
  "https://kavachiq.com/" \
  "https://api.kavachiq.com/api/status"; do
  STATUS=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "FAIL")
  if [ "$STATUS" = "200" ]; then
    echo "  ✅ $url → $STATUS"
  else
    echo "  ❌ $url → $STATUS"
  fi
done

echo ""
echo "═══ Monitoring setup complete ═══"
