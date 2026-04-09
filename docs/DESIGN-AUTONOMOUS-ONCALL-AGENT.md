# KavachIQ — Autonomous On-Call Agent Design

## Author
Principal SRE Engineer | April 2026

## Problem Statement

KavachIQ has Prometheus metrics flowing to `/metrics`, but nobody watches them. The errorcategory enum bug ran for weeks before discovery. When the next production issue happens — and it will — the detection-to-resolution time is measured in human response time.

Enterprise SLA commitments require:
- Detection: < 5 minutes
- Acknowledgment: < 15 minutes
- Resolution (P1): < 1 hour
- Resolution (P2): < 4 hours

An autonomous on-call agent meets these commitments 24/7 without human staffing costs.

## Design Principles

1. **AI diagnoses, code remediates.** The agent reasons about root cause. The runbook executes the fix. The agent never has ad-hoc write access.
2. **Deterministic first, intelligent second.** 80% of incidents match known patterns. Handle those with runbooks. Use Claude for the 20% that don't.
3. **Blast radius limits.** Every automated action is bounded: max 1 pod restart per 5 minutes, max 1 scale operation per 10 minutes, never touch the database schema.
4. **Dead-man's switch.** If the agent takes no successful action within 5 minutes, auto-escalate to human.
5. **Scoped, short-lived credentials.** Per-action tokens, not standing admin access.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Alert Sources                    │
                    │  Prometheus → Grafana Alerting → Webhook     │
                    │  Azure Monitor → Action Group → Webhook      │
                    │  Smart Engine (anomaly) → alert_service      │
                    └──────────────┬──────────────────────────────┘
                                   │ webhook POST
                                   ▼
                    ┌─────────────────────────────────────────────┐
                    │           Alert Router (FastAPI)              │
                    │  POST /api/alerts/ingest                     │
                    │  - Normalize alert format                    │
                    │  - Deduplicate (same alert within 5 min)     │
                    │  - Classify severity (P1/P2/P3)              │
                    │  - Store in incidents table                   │
                    └──────────────┬──────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────────┐
                    │         Layer 1: Runbook Engine               │
                    │  Pattern match alert → known runbook          │
                    │  If match: execute deterministic fix          │
                    │  If no match: escalate to Layer 2             │
                    │                                              │
                    │  Runbooks:                                    │
                    │  - worker_crash → restart pod                 │
                    │  - queue_backup → scale workers               │
                    │  - pg_pool_exhaustion → kill idle conns       │
                    │  - graph_throttle → reduce concurrency        │
                    │  - secret_expiring → alert + pause tenant     │
                    │  - consent_revoked → pause tenant + notify    │
                    │  - delta_token_invalid → trigger full sync    │
                    │  - backup_failure_spike → check enum/schema   │
                    └──────────────┬──────────────────────────────┘
                                   │ no match
                    ┌──────────────▼──────────────────────────────┐
                    │       Layer 2: Claude Diagnosis Agent         │
                    │  MCP tools (read-only):                      │
                    │  - prometheus_query(promql)                   │
                    │  - container_logs(app, lines)                 │
                    │  - redis_info()                               │
                    │  - db_pool_stats()                            │
                    │  - graph_api_metrics(tenant_id)               │
                    │  - recent_deploys()                           │
                    │  - active_incidents()                         │
                    │                                              │
                    │  Decision:                                    │
                    │  - Select runbook (if root cause identified)  │
                    │  - Escalate to human (if novel/risky)         │
                    │  - Correlate (if multiple tenants affected)   │
                    └──────────────┬──────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────────┐
                    │          Verification + Close                 │
                    │  After remediation:                           │
                    │  - Re-query the metric that fired             │
                    │  - If healthy: close incident                 │
                    │  - If still firing: escalate to human         │
                    │  - Post incident summary to Slack/Teams       │
                    └─────────────────────────────────────────────┘
```

## Incident Lifecycle

```
ALERT → ACKNOWLEDGED → TRIAGING → DIAGNOSING → REMEDIATING → VERIFYING → RESOLVED
  │         │              │           │             │            │           │
  │     < 30s          < 1 min     < 3 min       < 5 min     < 2 min    auto-close
  │                                                                         │
  └── at any stage, if stuck > 5 min ──────────────────────────► ESCALATED (human)
```

## Layer 1: Runbook Definitions

Each runbook is a deterministic sequence. No LLM reasoning. Auditable.

### Runbook 1: Worker Crash / Stuck

```yaml
id: worker_crash
trigger:
  metric: kavachiq_queue_depth{queue="backup_queue"} > 50
  duration: 10m
  # OR: worker pod count = 0 for > 5 min
diagnosis:
  - check: container_status(m365vault-worker-dev)
  - check: redis_queue_length(kavachiq:backup_queue)
actions:
  - az containerapp revision restart --name m365vault-worker-{env}
  - wait: 60s
verify:
  - kavachiq_queue_depth < 50 within 5 min
escalate_if: queue_depth still > 50 after restart
blast_radius: 1 pod restart per 5 min max
```

### Runbook 2: Redis Queue Backup

```yaml
id: queue_backup
trigger:
  metric: kavachiq_queue_depth{queue="backup_queue"} > 100
  duration: 5m
diagnosis:
  - check: worker pod count (should be > 0)
  - check: worker CPU utilization
actions:
  - scale: az containerapp update --max-replicas (current + 2), cap at 10
  - wait: 120s for KEDA to scale
verify:
  - queue_depth decreasing trend over 5 min
escalate_if: queue_depth still growing after scale
blast_radius: max 2 additional pods per action
```

### Runbook 3: PostgreSQL Connection Pool

```yaml
id: pg_pool_exhaustion
trigger:
  metric: kavachiq_db_pool_utilization_ratio > 0.8
  duration: 5m
diagnosis:
  - check: db_pool_stats (size, checked_out, overflow)
  - check: slow_queries (pg_stat_activity)
actions:
  - terminate idle connections: SELECT pg_terminate_backend(pid) WHERE state = 'idle' AND query_start < NOW() - INTERVAL '5 min'
  - if still > 80%: increase pool_size via env var update
verify:
  - kavachiq_db_pool_utilization_ratio < 0.6 within 5 min
escalate_if: utilization persists > 90%
blast_radius: only idle connections terminated, never active
```

### Runbook 4: Graph API Mass Throttling

```yaml
id: graph_throttle
trigger:
  metric: rate(kavachiq_graph_api_calls_total{status="429"}[5m]) > 10
  duration: 5m
diagnosis:
  - check: graph_api_metrics per tenant — is it one tenant or all?
  - check: AIMD limiter state
actions:
  - if single tenant: already handled by per-tenant AIMD, no action needed
  - if all tenants (correlated): reduce WORKER_CONCURRENCY to 1, wait for Microsoft
verify:
  - 429 rate < 5% within 15 min
escalate_if: 429 rate persists > 20% after 30 min (Microsoft outage — nothing we can do)
blast_radius: concurrency reduction only, no data loss
```

### Runbook 5: Connector Secret Expiring

```yaml
id: secret_expiring
trigger:
  metric: /api/diagnostics/secrets returns status "critical" or "expired"
  # Also: scheduler check_expiring_secrets() alert
diagnosis:
  - check: which workload app secret is expiring
  - check: days until expiry
actions:
  - if > 7 days: alert only (Slack/email), no auto-action
  - if < 7 days: pause backup scheduling for affected workload
  - if expired: pause ALL backups for tenant, notify admin
verify:
  - secret rotated (manual — requires Azure AD admin)
escalate_if: always escalate to human (secret rotation requires admin action)
blast_radius: pause only, never delete or modify secrets
```

### Runbook 6: Consent Revoked (403 Insufficient Privileges)

```yaml
id: consent_revoked
trigger:
  pattern: 3+ consecutive 403 "Insufficient privileges" for same tenant within 10 min
diagnosis:
  - check: graph_api_metrics for tenant — all 403s or mixed?
  - check: which API endpoints fail (scoped or global revocation?)
actions:
  - pause backup scheduling for tenant (set workload lifecycle to PAUSED)
  - send alert to tenant admin: "M365 permissions revoked — re-consent required"
  - create incident record
verify:
  - tenant admin re-consents → connector-health returns healthy
escalate_if: always notify human (customer relationship issue)
blast_radius: single tenant paused, others unaffected
```

### Runbook 7: Delta Token Invalid (410 Gone)

```yaml
id: delta_token_invalid
trigger:
  pattern: Graph API returns 410 Gone on delta query
diagnosis:
  - check: which tenant + workload
  - check: when was the last successful delta sync
actions:
  - clear delta_token on affected protected object (set to NULL)
  - next scheduled backup will automatically run a full sync
  - log: "Delta token expired for tenant X workload Y — falling back to full sync"
verify:
  - next backup for this object completes successfully
escalate_if: full sync also fails
blast_radius: one object gets a full backup instead of incremental — no data loss
```

### Runbook 8: Microsoft Regional Outage

```yaml
id: microsoft_outage
trigger:
  pattern: > 50% of tenants failing Graph API calls within 5 min window
  # Correlated failure across multiple tenants = not our bug
diagnosis:
  - check: graph_api_metrics — failure rate per tenant
  - check: Microsoft Service Health API (if available)
  - check: https://status.office.com
actions:
  - pause scheduler (stop creating new backup jobs)
  - log: "Microsoft outage detected — scheduler paused"
  - post to status page: "Backups paused due to Microsoft service degradation"
  - poll: check graph health every 5 min
  - resume when > 80% of test calls succeed
verify:
  - Graph API calls succeeding at > 95% for 10 min
escalate_if: outage > 4 hours (SLA impact)
blast_radius: scheduler paused globally — no individual tenant actions
```

## Layer 2: Claude Diagnosis Agent

### MCP Tool Definitions

```python
tools = [
    # Read-only observability tools
    {
        "name": "prometheus_query",
        "description": "Execute a PromQL query against the metrics endpoint",
        "parameters": {"query": "string", "range_minutes": "int (default 15)"},
        "example": "rate(kavachiq_http_requests_total{status=~'5..'}[5m])"
    },
    {
        "name": "container_logs",
        "description": "Fetch recent logs from a container app",
        "parameters": {"app": "backend|worker|frontend", "lines": "int (max 200)", "filter": "string"},
    },
    {
        "name": "redis_info",
        "description": "Get Redis server info: memory, connections, queue lengths",
        "parameters": {},
    },
    {
        "name": "db_pool_stats",
        "description": "Get PostgreSQL connection pool statistics",
        "parameters": {},
    },
    {
        "name": "graph_api_metrics",
        "description": "Get Graph API call stats for a tenant: calls/min, throttle rate, errors",
        "parameters": {"tenant_id": "int (optional, omit for all)"},
    },
    {
        "name": "recent_deploys",
        "description": "List recent container app revisions with deploy times",
        "parameters": {"hours": "int (default 24)"},
    },
    {
        "name": "active_incidents",
        "description": "List currently open incidents",
        "parameters": {},
    },
    {
        "name": "job_status_summary",
        "description": "Get backup/restore job status distribution (last N hours)",
        "parameters": {"hours": "int (default 1)"},
    },

    # Remediation tools (bounded, audited)
    {
        "name": "execute_runbook",
        "description": "Execute a pre-defined runbook by ID. Only works for known runbook IDs.",
        "parameters": {"runbook_id": "string", "params": "dict"},
    },
    {
        "name": "escalate_to_human",
        "description": "Page the human on-call via PagerDuty with a summary",
        "parameters": {"severity": "P1|P2|P3", "summary": "string", "diagnosis": "string"},
    },
]
```

### Agent System Prompt

```
You are the KavachIQ on-call SRE agent. You have been paged for an alert.

Your job:
1. ACKNOWLEDGE the alert immediately
2. DIAGNOSE the root cause using your read-only tools
3. DECIDE: execute a known runbook OR escalate to human
4. VERIFY the fix worked

Rules:
- You can ONLY remediate via execute_runbook(). You cannot run arbitrary commands.
- If you are not confident in the root cause, escalate. Do not guess.
- If the alert involves data loss, credential rotation, or database schema: always escalate.
- You have 5 minutes. If you haven't resolved by then, auto-escalate.
- After remediation, re-check the metric that triggered the alert.
- Write a 3-sentence incident summary when done.

Available runbooks: worker_crash, queue_backup, pg_pool_exhaustion, graph_throttle,
secret_expiring, consent_revoked, delta_token_invalid, microsoft_outage
```

### Decision Flow

```
Claude receives alert context
  │
  ├─ Reads alert name + metric value
  ├─ Queries prometheus_query() for related metrics
  ├─ Queries container_logs() for error patterns
  │
  ├─ If error matches known runbook pattern:
  │    └─ execute_runbook(runbook_id, params)
  │         └─ Verify fix → close incident
  │
  ├─ If correlated failure across tenants:
  │    └─ execute_runbook("microsoft_outage")
  │
  ├─ If single tenant failing:
  │    ├─ Check consent (403 pattern) → execute_runbook("consent_revoked")
  │    ├─ Check delta (410 pattern) → execute_runbook("delta_token_invalid")
  │    └─ Unknown → escalate_to_human(P2, summary, diagnosis)
  │
  └─ If novel failure (no pattern match):
       └─ escalate_to_human(P1, summary, diagnosis)
```

## Data Model

### incidents table

```sql
CREATE TABLE incidents (
    id SERIAL PRIMARY KEY,
    alert_name VARCHAR(100) NOT NULL,
    severity VARCHAR(10) NOT NULL,        -- P1, P2, P3
    status VARCHAR(20) NOT NULL,          -- acknowledged, triaging, diagnosing, remediating, verifying, resolved, escalated
    source VARCHAR(50),                   -- grafana, azure_monitor, smart_engine, manual
    alert_payload JSON,                   -- raw alert webhook body
    diagnosis TEXT,                       -- agent's root cause analysis
    runbook_id VARCHAR(50),               -- which runbook was executed (null if escalated)
    actions_taken JSON,                   -- list of actions the agent performed
    resolution_summary TEXT,              -- 3-sentence summary
    resolved_by VARCHAR(50),             -- agent or human username
    acknowledged_at TIMESTAMP,
    diagnosed_at TIMESTAMP,
    resolved_at TIMESTAMP,
    escalated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    tenant_id INTEGER,                    -- affected tenant (null if platform-wide)
    ttl_seconds INTEGER                   -- time to resolution
);
```

### runbook_executions table

```sql
CREATE TABLE runbook_executions (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER REFERENCES incidents(id),
    runbook_id VARCHAR(50) NOT NULL,
    parameters JSON,
    status VARCHAR(20),                  -- started, succeeded, failed, rolled_back
    output TEXT,                          -- execution output/logs
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    rolled_back_at TIMESTAMP
);
```

## Safety Boundaries

### What the Agent CAN Do (Autonomously)

- Restart a worker pod (max 1 per 5 min)
- Scale worker replicas up by 2 (max 10 total)
- Terminate idle database connections (> 5 min idle)
- Reduce WORKER_CONCURRENCY setting
- Pause backup scheduling for a single tenant
- Clear a delta token (triggers full sync on next backup)
- Post status updates to Slack/Teams
- Close incidents when metrics normalize

### What the Agent CANNOT Do (Must Escalate)

- Modify database schema or run migrations
- Rotate credentials or secrets
- Delete any data (snapshots, backups, audit logs)
- Change DNS, TLS, or network configuration
- Modify Terraform infrastructure
- Access customer data content (only metadata)
- Scale beyond configured max_replicas
- Take any action on > 1 tenant simultaneously (except Microsoft outage pause)

### Rate Limits on Agent Actions

```yaml
pod_restart: max 1 per 5 minutes
scale_operation: max 1 per 10 minutes
connection_kill: max 10 idle connections per action
concurrency_change: max 1 per 15 minutes
tenant_pause: max 3 tenants per hour
escalation: unlimited (safe action)
```

## Implementation Phases

### Phase 1: Alert Ingestion + Deterministic Runbooks (1 week)

- POST /api/alerts/ingest webhook endpoint
- incidents + runbook_executions tables
- 8 runbook implementations as Python functions
- Pattern matching: alert name → runbook
- Verification loop (re-check metric after fix)
- Slack/Teams notification on resolve/escalate
- Dead-man's switch (5-min timeout → escalate)

### Phase 2: Claude Diagnosis Layer (1 week)

- MCP tool server with 8 read-only tools
- Claude Agent SDK integration
- System prompt with runbook selection logic
- Correlation detection (multi-tenant failure → outage)
- Incident summary generation
- Confidence-based routing (high → auto-fix, low → escalate)

### Phase 3: Grafana + PagerDuty Integration (2-3 days)

- Azure Monitor Prometheus scraping of /metrics
- Grafana dashboard: backup success rate, queue depth, pool utilization, recovery score
- Grafana alerting rules → webhook to /api/alerts/ingest
- PagerDuty as escalation target (agent pages human when needed)
- Runbook links in PagerDuty incidents

### Phase 4: Learning + Feedback Loop (ongoing)

- Post-incident review: was the agent's diagnosis correct?
- Track: auto-resolved vs escalated vs false positive
- Tune pattern matching thresholds based on incident history
- Add new runbooks for recurring novel issues
- Monthly SLA report: MTTD, MTTA, MTTR per severity

## Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| Grafana Cloud (free tier: 10K metrics, 50GB logs) | $0 |
| PagerDuty (1 user, free tier) | $0 |
| Claude API (Agent SDK, ~100 incidents/month × ~5 tool calls) | ~$15 |
| Azure Monitor (Prometheus scraping, included in ACA) | $0 |
| Total | ~$15/month |

At scale (1000 incidents/month), Claude API cost rises to ~$150/month — still cheaper than one hour of a human SRE's time.

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mean Time to Detect (MTTD) | < 5 min | Alert fires → incident created |
| Mean Time to Acknowledge (MTTA) | < 30 sec | Incident created → acknowledged |
| Auto-resolution rate | > 70% | Resolved by agent / total incidents |
| False positive rate | < 10% | Incidents closed without action / total |
| Escalation rate | < 30% | Escalated to human / total |
| Mean Time to Resolve (MTTR) | < 10 min (auto) | Incident created → resolved |
| SLA compliance | > 99% | Incidents resolved within SLA window |
