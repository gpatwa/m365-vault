# Production Resilience & Operational Excellence Design

**KavachIQ | Date: 2026-03-28 | Status: Design Proposal**

---

## 1. What Best-in-Class SaaS Products Do

Companies like Stripe, Datadog, Linear, and Vercel have set the bar for SaaS reliability. Here's what they get right that we need to adopt:

| Practice | Who Does It | Why It Matters |
|----------|-------------|----------------|
| **Idempotent operations** | Stripe | Every API call can be safely retried without duplicate side effects |
| **Circuit breakers** | Netflix, Stripe | Stop cascading failures when a dependency is down |
| **Structured observability** | Datadog, Vercel | Unified logs + metrics + traces → diagnose any issue in seconds |
| **Canary deployments** | Google, Vercel | New code rolls out to 1% of traffic first, auto-rollbacks on errors |
| **Feature flags** | LaunchDarkly, Linear | Decouple deploy from release — ship code dark, enable for specific users |
| **Self-healing** | AWS, Kubernetes | Auto-restart failed containers, auto-scale on load |
| **Chaos engineering** | Netflix (Chaos Monkey) | Inject failures in production to prove resilience |
| **Status page** | Every serious SaaS | Public transparency on uptime and incidents |
| **User-facing error context** | Stripe, Clerk | Every error has an error code, human message, and link to docs |

---

## 2. Current KavachIQ Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| **No structured logging** | Can't search/filter logs, debug requires SSH/CLI | P0 |
| **No error codes** | Users see raw AADSTS codes, no actionable guidance | P0 |
| **No deployment verification** | New deploys serve traffic before health validation | P0 |
| **No pre-flight checks** | OAuth redirect fails after user already went to Microsoft | P1 |
| **No retry on external calls** | Single failure = user-visible error | P1 |
| **No feature flags** | Can't disable broken features without redeploying | P1 |
| **No status page** | Users have no visibility into platform health | P2 |
| **No canary deployments** | All-or-nothing deploys — one bug affects all users | P2 |
| **No distributed tracing** | Can't trace a request across frontend → backend → Graph API | P2 |
| **No idempotency keys** | Retry a backup or restore could create duplicates | P3 |

---

## 3. Implementation Plan — Phased

### Phase A: Observability Foundation (1-2 weeks)

**Goal: Every error is visible, searchable, and actionable within 30 seconds.**

#### A1. Structured JSON Logging

Replace print/basic logging with structured JSON output. Every log entry has:

```json
{
  "timestamp": "2026-03-28T10:00:00Z",
  "level": "ERROR",
  "service": "backend",
  "correlation_id": "abc-123",
  "user_id": 1,
  "tenant_id": 5,
  "action": "oauth_callback",
  "error_code": "CONNECTOR_SECRET_INVALID",
  "message": "Token acquisition failed for tenant 9e0cfba8",
  "detail": "AADSTS7000215: Invalid client secret",
  "fix": "Regenerate secret in Azure Portal",
  "duration_ms": 1200,
  "tags": ["onboarding", "microsoft365", "auth"]
}
```

**Files to modify:**
- `backend/app/main.py` — configure `structlog` or JSON formatter
- Every API endpoint — add correlation_id from middleware
- `backend/app/connectors/m365_connector.py` — structured error logging

#### A2. Error Code System

Define error codes so every error is identifiable and documentable:

```python
# backend/app/errors.py
class KavachIQError:
    # Connector errors (1000s)
    CONNECTOR_NOT_CONFIGURED = "E1001"
    CONNECTOR_SECRET_INVALID = "E1002"
    CONNECTOR_CONSENT_PENDING = "E1003"
    CONNECTOR_TENANT_NOT_FOUND = "E1004"

    # Auth errors (2000s)
    AUTH_TOKEN_EXPIRED = "E2001"
    AUTH_RATE_LIMITED = "E2002"

    # Backup errors (3000s)
    BACKUP_GRAPH_THROTTLED = "E3001"
    BACKUP_STORAGE_FAILED = "E3002"

    # Recovery errors (4000s)
    RECOVERY_NO_SNAPSHOT = "E4001"
    RECOVERY_MALWARE_DETECTED = "E4002"
```

Every API error response includes:
```json
{
  "error": {
    "code": "E1002",
    "message": "The connector app secret is invalid",
    "detail": "Azure AD rejected the client secret for app d5c6ca1d...",
    "fix": "Go to Azure Portal → App Registrations → Certificates & Secrets → create new secret",
    "docs": "https://docs.kavachiq.com/errors/E1002",
    "correlation_id": "abc-123"
  }
}
```

#### A3. Request Tracing

Every request gets a `correlation_id` that flows through:
- Frontend (sent as `X-Correlation-Id` header)
- Backend middleware (generates if not present, logs it)
- Graph API calls (logged with correlation_id)
- Response headers (returned to frontend for user error reports)

**When a user sees an error, they can share the correlation_id and support can find the exact log chain in seconds.**

### Phase B: Resilient External Calls (1-2 weeks)

**Goal: No single external failure causes a user-visible error.**

#### B1. Pre-flight Validation

Before any user-facing action that depends on external services, validate the dependency:

```python
# Before OAuth redirect
async def connect_platform(platform):
    # Pre-flight: can we actually complete this flow?
    health = await preflight_check(platform)
    if not health.ok:
        return {"error": health.user_message}  # Don't redirect to Microsoft

    # Proceed with redirect
    return {"auth_url": connector.get_auth_url(...)}
```

Already built in this session for the connector. Extend to:
- Backup: verify Graph API is reachable before starting
- Restore: verify target tenant is accessible before dispatching
- Discovery: verify permissions before running

#### B2. Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Stops calling a failing service after N consecutive failures."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service is down, fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.state = self.CLOSED
        self.failure_count = 0
        self.threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
```

Apply to:
- Microsoft Graph API calls
- Azure Blob Storage operations
- PostgreSQL (via connection pool health)

#### B3. Retry with Exponential Backoff + Jitter

Already partially implemented. Standardize:

```python
async def retry_with_backoff(fn, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return await fn()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(delay)
```

#### B4. Idempotency Keys for Mutations

```python
# Client sends: X-Idempotency-Key: <uuid>
# Server stores result keyed by (user_id, idempotency_key)
# On retry with same key, return stored result without re-executing

@router.post("/backup-all")
async def backup_all(
    idempotency_key: str = Header(None, alias="X-Idempotency-Key"),
):
    if idempotency_key:
        cached = await get_idempotent_result(idempotency_key)
        if cached:
            return cached

    result = await execute_backup(...)

    if idempotency_key:
        await store_idempotent_result(idempotency_key, result, ttl=3600)

    return result
```

### Phase C: Deployment Safety (1 week)

**Goal: Bad deploys are caught automatically before users are affected.**

#### C1. Deployment Health Gate

After deploying a new container revision:
1. New revision starts with 0% traffic
2. Health check runs (`GET /api/diagnostics/health`)
3. If all checks pass → shift 100% traffic
4. If any critical check fails → keep old revision, alert ops

```yaml
# In Terraform / Container App config
revision_mode: "multiple"
traffic_rules:
  - latest_revision: true
    weight: 0  # Start at 0%

# Post-deploy script
az containerapp ingress traffic set \
  --revision-weight "$NEW_REVISION=10" \  # Canary: 10%
  # Wait 5 minutes, check error rate
  --revision-weight "$NEW_REVISION=100"   # Full rollout
```

#### C2. Automated Rollback

```bash
# deploy.sh
NEW_REV=$(deploy_new_revision)
sleep 30

HEALTH=$(curl -s "$BACKEND_URL/api/diagnostics/health" | jq '.healthy')
if [ "$HEALTH" != "true" ]; then
    echo "ROLLING BACK — health check failed"
    az containerapp revision deactivate --revision $NEW_REV
    send_alert "Deploy rolled back: health check failed"
    exit 1
fi
```

#### C3. Feature Flags (Lightweight)

```python
# backend/app/config.py
FEATURE_FLAGS = {
    "org_context_enabled": True,
    "mvb_plans_enabled": True,
    "oauth_preflight_check": True,
    "new_onboarding_flow": True,
}

# Usage
if settings.feature_flag("oauth_preflight_check"):
    await preflight_check(platform)
```

Can be extended to LaunchDarkly/Flagsmith later. Start with config-based flags.

### Phase D: User Experience Resilience (1 week)

**Goal: Users never see a raw technical error. Every failure has clear guidance.**

#### D1. Frontend Error Boundary with Context

```tsx
// Global error boundary
class KavachIQErrorBoundary extends React.Component {
    render() {
        if (this.state.hasError) {
            return (
                <ErrorPage
                    title="Something went wrong"
                    message="We hit an unexpected error. Our team has been notified."
                    correlationId={this.state.correlationId}
                    actions={[
                        { label: "Try Again", onClick: () => window.location.reload() },
                        { label: "Go to Dashboard", href: "/" },
                        { label: "Contact Support", href: "/support" },
                    ]}
                />
            );
        }
        return this.props.children;
    }
}
```

#### D2. Optimistic UI with Rollback

For operations like "Backup All":
1. Show success immediately (optimistic)
2. Run the operation in background
3. If it fails, show a non-intrusive toast with retry option
4. Never block the user with a spinner for > 3 seconds

#### D3. Offline/Degraded Mode

If the backend is unreachable:
- Show cached data from last successful fetch
- Disable mutation buttons (backup, restore)
- Show a banner: "Some features are temporarily unavailable"

#### D4. Status Page

`/status` — public page showing:
- Current system status (operational / degraded / outage)
- Last 90 days uptime percentage
- Component health (API, Database, Storage, Graph API)
- Active incidents with ETA

### Phase E: Operational Tooling (Ongoing)

#### E1. Admin Dashboard Enhancements

Build into the existing admin UI:
- **System Health page** (`/admin/diagnostics`) — real-time health of all dependencies
- **Connector Test button** — one-click validation before customer demos
- **Tenant Health** — per-tenant backup status, last successful backup, error count
- **Error Log viewer** — searchable structured logs in the UI

#### E2. Alerting

```python
# Alert on critical events
alert_rules = [
    {"condition": "connector_health != healthy", "severity": "critical", "channel": "slack"},
    {"condition": "backup_failure_rate > 10%", "severity": "high", "channel": "email"},
    {"condition": "api_error_rate > 5%", "severity": "medium", "channel": "slack"},
    {"condition": "disk_usage > 80%", "severity": "warning", "channel": "email"},
]
```

#### E3. Runbook Automation

For common issues, auto-detect and auto-fix:

| Issue | Detection | Auto-Fix |
|-------|-----------|----------|
| Stale DB connections | Pool health check fails | Recycle connection pool |
| Graph API throttling | 429 count > threshold | Reduce concurrency, alert |
| Container memory leak | Memory > 80% for 10 min | Restart container |
| Expired connector secret | Health check fails | Alert admin with exact fix steps |
| Stale backup jobs | IN_PROGRESS > 60 min | Reset to QUEUED (already built) |

---

## 4. Priority Implementation Order

| Week | Deliverable | Impact | Status |
|------|-------------|--------|--------|
| **Week 1** | Structured logging + error codes + correlation IDs | Debug any issue in 30s | **DONE** (2026-03-29) |
| **Week 2** | Pre-flight checks + circuit breakers + idempotency | No single-failure user errors | **DONE** (2026-03-29) |
| **Week 3** | Deployment health gate + automated rollback | Zero-downtime deploys | TODO |
| **Week 4** | Status page + admin diagnostics UI | Professional user experience | TODO |
| **Ongoing** | Alerting, chaos testing, feature flags, canary deploys | Operational maturity | TODO |

### What's Implemented (as of 2026-03-29)

**Phase A (Observability Foundation) — COMPLETE:**
- A1. Structured JSON logging with enhanced formatter (service, correlation_id, user_id, duration_ms)
- A2. Error code system: `backend/app/errors.py` with 30+ codes (E1xxx-E7xxx), `KavachIQError` exception class
- A3. Correlation ID middleware: auto-generates `X-Correlation-ID`, logs with every request, returns in response

**Phase B (Resilient External Calls) — COMPLETE:**
- B1. Pre-flight validation: `preflight_graph_api()`, `preflight_storage()`, `preflight_database()`
- B2. Circuit breaker: Integrated into `GraphClient._request()`, per-tenant state, alerts on open
- B3. Retry with exponential backoff: Already in GraphClient, standardized via `retry_async` decorator
- B4. Idempotency keys: `IdempotencyStore` with `X-Idempotency-Key` header on backup-all endpoints

**Phase D (UX Resilience) — PARTIAL:**
- D1. Frontend `ErrorBoundary` with correlation ID and copy button
- D2. `ToastProvider` with success/error/warning/info notifications
- D3. Offline/degraded mode — NOT DONE
- D4. Status page — NOT DONE

**Phase E (Operational Tooling) — PARTIAL:**
- E1. Diagnostics endpoints: `/circuit-breaker`, `/resilience`, `/health`, `/graph-metrics`, `/performance`
- E2. Alerting — alert service exists, full rules engine NOT DONE
- E3. Stale job detection — DONE (scheduler)

---

## 5. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| **MTTR (Mean Time to Resolve)** | Hours (manual debugging) | < 15 minutes | Time from alert to fix deployed |
| **Error visibility** | Check container logs | 100% in UI | Admin diagnostics page |
| **Deploy success rate** | Unknown | > 99% | Health gate pass rate |
| **User-facing errors with guidance** | ~20% | 100% | Error code coverage |
| **Pre-flight check coverage** | 1 endpoint | All external calls | Audit |
| **Uptime** | Unknown | 99.9% | Status page |

---

## Sources

- [Stripe: Designing Robust APIs with Idempotency](https://stripe.com/blog/idempotency)
- [SRE SaaS Framework 2026](https://gainhq.com/blog/site-reliability-engineering-saas/)
- [Observability Best Practices 2026](https://spacelift.io/blog/observability-best-practices)
- [Managing Reliability in Cloud-Native Environments](https://www.harness.io/harness-devops-academy/managing-reliability-in-cloud-native-environments)
- [How Systems Handle Failure](https://iam.slys.dev/p/how-systems-handle-failure-retries)
- [Error Handling in Distributed Systems (Temporal)](https://temporal.io/blog/error-handling-in-distributed-systems)
