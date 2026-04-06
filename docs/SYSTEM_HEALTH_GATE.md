# System Health Gate — Never Serve Broken Traffic

**Problem:** We keep shipping deployments where the system is "healthy" but broken for users:
- Backend returns 200 on /health but connector secret is expired
- Login works via API but frontend config.js points to wrong URL
- Database is connected but no users/demo data exist
- E2E tests pass but only check after deployment, not before traffic switch

**Solution:** A comprehensive health gate that runs BEFORE traffic is routed to a new deployment. If any check fails, traffic stays on the old revision.

---

## Architecture

```
New code pushed
  ↓
Build Docker image
  ↓
Pre-deploy check (local container test)  ← P0 (done)
  ↓
Deploy new revision (0% traffic)
  ↓
═══ HEALTH GATE ═══════════════════════
  1. Backend /health → DB + Storage
  2. Connector health → Entra app secret valid
  3. Login test → all 4 user accounts work
  4. Config.js → API_BASE correct
  5. Demo data → tenants + objects exist
  6. CORS → both domains allowed
  7. Custom domains → SSL valid
  8. Secret expiry → no secrets expiring within 30 days
═══════════════════════════════════════
  ↓ ALL PASS?
  ↓
Yes → Route 100% traffic to new revision
No  → Keep old revision, alert, exit 1
```

---

## What's Missing from Current E2E

| Check | Current E2E | Health Gate |
|---|---|---|
| Backend health | ✅ | ✅ |
| All user logins | ✅ | ✅ |
| Connector secret valid | ❌ | ✅ NEW |
| Secret expiry warning | ❌ | ✅ NEW |
| Demo data populated | ✅ (checks count) | ✅ |
| Config.js correct | ✅ | ✅ |
| CORS both domains | ✅ | ✅ |
| Stripe webhook reachable | ❌ | ✅ NEW |
| Resend email deliverable | ❌ | ✅ NEW |
| OAuth redirect URI valid | ❌ | ✅ NEW |
| SSL cert expiry > 30 days | ❌ | ✅ NEW |
| Rate limiting works | ❌ | ✅ NEW |
| Runs BEFORE traffic switch | ❌ | ✅ KEY DIFFERENCE |

---

## Implementation

### 1. Add `/health/deep` endpoint (backend)

The current `/health` only checks DB + storage. Add a deep health check that validates ALL external dependencies:

```python
@router.get("/health/deep")
async def deep_health_check(db: AsyncSession = Depends(get_db)):
    checks = {}

    # 1. Database
    checks["database"] = await _check_db(db)

    # 2. Storage
    checks["storage"] = await _check_storage()

    # 3. Connector (Entra app secret)
    checks["connector"] = await _check_connector()

    # 4. Email (Resend)
    checks["email"] = await _check_email_provider()

    # 5. Stripe
    checks["stripe"] = await _check_stripe()

    # 6. Redis
    checks["redis"] = await _check_redis()

    # 7. Demo data
    checks["demo_data"] = await _check_demo_data(db)

    # 8. Secret expiry
    checks["secret_expiry"] = await _check_secret_expiry()

    all_healthy = all(c["status"] == "healthy" for c in checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### 2. Health gate in deploy script

The safe-deploy.sh and blue-green-deploy.sh should call `/health/deep` instead of `/health`:

```bash
# After new revision starts, before traffic switch:
DEEP_HEALTH=$(curl -sf "https://$BACKEND_FQDN/health/deep")
ALL_HEALTHY=$(echo "$DEEP_HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
if [ "$ALL_HEALTHY" != "healthy" ]; then
    echo "❌ Deep health check FAILED — keeping old revision"
    echo "$DEEP_HEALTH" | python3 -m json.tool
    exit 1
fi
```

### 3. Scheduled health monitoring

Run deep health check every 5 minutes. Alert on degradation:

```python
# In scheduler:
@scheduler.scheduled_job('interval', minutes=5)
async def check_system_health():
    result = await deep_health_check()
    if result["status"] != "healthy":
        await alert_service.send_alert(
            severity="critical",
            title="System Health Degraded",
            details=result["checks"],
        )
```

### 4. Dashboard health widget

Show system health on the admin dashboard — not just backup health, but:
- Connector: ✅ Connected / ❌ Secret expired
- Email: ✅ Deliverable / ❌ Provider down
- Stripe: ✅ Configured / ❌ Webhook failing
- SSL: ✅ Valid / ⚠️ Expiring in 14 days

---

## Priority

| Item | Effort | Impact |
|---|---|---|
| `/health/deep` endpoint | 3 hrs | Catches connector/stripe/email issues before users hit them |
| Health gate in deploy scripts | 1 hr | Prevents bad deployments |
| Scheduled monitoring | 2 hrs | Catches degradation between deploys |
| Dashboard widget | 2 hrs | Admin visibility |
