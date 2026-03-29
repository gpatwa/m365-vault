# Observability, Throughput, Health Visibility & Auto-Scale Design

**Shieldio | Date: 2026-03-28 | Status: Design Proposal**

---

## 1. Microsoft Graph API Call Observability

### The Problem

Microsoft Graph API has **hard limits** that every M365 backup vendor hits:

| Scope | Limit | Impact |
|-------|-------|--------|
| Per-app per-tenant (Outlook) | 3,500-8,000 ResourceUnits / 10s (varies by tenant size) | Backup speed capped |
| Per-mailbox | 150 MB / 5 min | Can't speed up individual mailbox backup |
| Per-tenant overall | Shared across all apps | Other apps in tenant compete for budget |
| **Sep 2025 change** | Per-app limit cut to 50% of tenant total | Directly impacts Shieldio |

**All competitors are throttled equally** — Veeam reports ~15-20 MB/s, ~1TB per 12 hours. The new M365 Backup Storage API bypasses throttling (1+ TB/hr) but requires a separate integration.

### What We Need to Track

```
For EVERY Graph API call, capture:
  - timestamp
  - endpoint (e.g., /users/{id}/messages)
  - method (GET/POST)
  - tenant_id
  - response_status (200, 429, 5xx)
  - response_time_ms
  - retry_after_seconds (if 429)
  - request_cost (ResourceUnits consumed, from response headers)
  - remaining_budget (from response headers)
```

### Implementation: Graph API Metrics Collector

**Modify `backend/app/services/graph_client.py`** — add metrics to every request:

```python
class GraphMetrics:
    """Track Graph API usage per tenant."""

    def __init__(self):
        self._calls: dict[int, list] = {}  # tenant_id -> list of call records
        self._throttle_count: dict[int, int] = {}

    def record_call(self, tenant_id: int, endpoint: str, status: int,
                    duration_ms: int, retry_after: int = 0):
        if tenant_id not in self._calls:
            self._calls[tenant_id] = []
        self._calls[tenant_id].append({
            "ts": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "status": status,
            "duration_ms": duration_ms,
            "retry_after": retry_after,
        })
        # Keep last 1000 calls per tenant
        self._calls[tenant_id] = self._calls[tenant_id][-1000:]

        if status == 429:
            self._throttle_count[tenant_id] = self._throttle_count.get(tenant_id, 0) + 1

    def get_stats(self, tenant_id: int) -> dict:
        calls = self._calls.get(tenant_id, [])
        last_5min = [c for c in calls if ...]  # filter recent
        return {
            "total_calls": len(calls),
            "throttled_count": self._throttle_count.get(tenant_id, 0),
            "avg_latency_ms": mean([c["duration_ms"] for c in last_5min]) if last_5min else 0,
            "calls_per_minute": len(last_5min) / 5 if last_5min else 0,
            "budget_utilization": ...,  # from Retry-After headers
        }
```

**New API endpoint**: `GET /api/diagnostics/graph-metrics?tenant_id={id}`

### What Competitors Do

| Vendor | Graph API Handling |
|--------|-------------------|
| **Veeam** | Multiple backup proxies, app registration splitting, job scheduling to avoid peaks |
| **Druva** | Cloud-native with automatic throttle handling, no user visibility |
| **Rubrik** | "AI-driven orchestration" to bypass throttling (marketing) — actually uses M365 Backup Storage API |
| **Commvault** | Parallel streams with per-tenant throttle budgeting |

### Shieldio Approach

Phase 1 (now): Track and display Graph API metrics per tenant
Phase 2: Auto-adjust backup concurrency based on throttle rate
Phase 3: Integrate M365 Backup Storage API (bypass throttling entirely)

---

## 2. Throughput Metrics & Performance Benchmarks

### Key Metrics to Track

| Metric | Definition | Target |
|--------|-----------|--------|
| **Backup throughput** | Items backed up per minute | Baseline: measure first |
| **Backup time per mailbox** | End-to-end time for single mailbox | < 30 seconds (incremental) |
| **Restore RTO** | Time from restore request to data available | < 5 min (single item), < 30 min (full mailbox) |
| **RPO compliance** | % of objects backed up within SLA window | > 95% |
| **Discovery speed** | Time to discover all workloads | < 30 seconds |
| **Snapshot size** | Compressed size per snapshot | Track trend |
| **Dedup ratio** | Data reduction from deduplication | Track trend |
| **API response time (p50/p95/p99)** | Shieldio API latency | p50 < 50ms, p95 < 200ms |

### Implementation: Performance Dashboard

**New API endpoint**: `GET /api/diagnostics/performance`

```json
{
  "backup": {
    "throughput_items_per_min": 45,
    "avg_time_per_mailbox_sec": 12,
    "avg_time_per_site_sec": 25,
    "last_full_backup_duration_min": 8,
    "incremental_vs_full_ratio": 0.15,
    "compression_ratio": 2.1,
    "dedup_savings_pct": 35
  },
  "restore": {
    "avg_item_restore_sec": 3,
    "avg_full_restore_min": 12,
    "success_rate_pct": 98
  },
  "api": {
    "p50_ms": 12,
    "p95_ms": 85,
    "p99_ms": 450,
    "requests_per_minute": 120,
    "error_rate_pct": 0.5
  },
  "graph_api": {
    "calls_per_minute": 45,
    "throttle_rate_pct": 2,
    "avg_latency_ms": 180
  }
}
```

### Industry Benchmarks

| Metric | Veeam | Microsoft Native | Shieldio Target |
|--------|-------|-----------------|----------------|
| Mailbox backup | ~15-20 MB/s | 1+ TB/hr (Backup Storage API) | Track our actual numbers |
| Full tenant backup (1000 users) | 8-12 hours | 15 min initial | Depends on Graph limits |
| Single item restore | 2-5 min | 200-500 items/min | < 30 sec |
| Incremental backup | ~2-5 min/run | Near-instant | < 5 min |

---

## 3. System Health Visibility

### What Best-in-Class Shows

| Component | Datadog | Veeam | What Shieldio Needs |
|-----------|---------|-------|---------------------|
| **Uptime** | Service uptime % (99.99%) | Backup success rate | Both |
| **Latency** | P50/P95/P99 by endpoint | Job duration trends | API + backup latency |
| **Error rate** | % of 5xx responses | Failed job count | Both + Graph API errors |
| **Queue depth** | Messages pending | Jobs queued | Backup/restore queue size |
| **Dependency health** | External service checks | Storage, DB status | Graph API + Azure Blob + DB + Redis |
| **Resource usage** | CPU, memory, disk | Proxy utilization | Container CPU/memory |

### Implementation: Enhanced Health Dashboard

Extend existing `/api/diagnostics/health` to include:

```json
{
  "healthy": true,
  "score": "9/9",
  "checks": [...],  // existing 7 checks
  "performance": {
    "api_p95_ms": 85,
    "api_error_rate_pct": 0.1,
    "active_backup_jobs": 2,
    "queued_jobs": 0,
    "graph_api_throttle_rate": 0
  },
  "resources": {
    "cpu_pct": 35,
    "memory_pct": 60,
    "storage_used_gb": 1.2,
    "storage_limit_gb": 100,
    "db_connections_active": 5,
    "db_connections_max": 20
  },
  "uptime": {
    "backend_uptime_hours": 168,
    "last_restart": "2026-03-28T08:00:00Z",
    "backup_success_rate_7d": 98.5,
    "restore_success_rate_30d": 100
  }
}
```

### Frontend: System Health Page

Add to `/admin/diagnostics` (admin only):
- Real-time health cards (green/yellow/red)
- Graph API call budget visualization (gauge showing % consumed)
- API latency chart (last 24h)
- Backup throughput trend (last 7 days)
- Active/queued job count

---

## 4. Auto-Scale Based on Load

### Azure Container Apps Scaling Options

| Trigger | How It Works | Use Case |
|---------|-------------|----------|
| **HTTP concurrent requests** | Scale when requests > threshold per replica | API backend during peak |
| **CPU utilization** | Scale when CPU > 70% | Compute-intensive backup workers |
| **Custom KEDA scaler** | Scale on Redis queue depth, custom metrics | Backup worker scaling |
| **Schedule** | Scale up at 9am, down at 6pm | Predictable backup windows |
| **TCP connections** | Scale on connection count | WebSocket or streaming |

### Current Shieldio Config

```hcl
# From infra/environments/dev.tfvars
backend_min_replicas  = 1
backend_max_replicas  = 3
worker_min_replicas   = 1
worker_max_replicas   = 2

# From infra/environments/prod.tfvars
backend_min_replicas  = 2
backend_max_replicas  = 10
worker_min_replicas   = 2
worker_max_replicas   = 6
```

### Recommended Auto-Scale Configuration

#### Backend (API Server)
```yaml
# Scale on HTTP request concurrency
scale:
  minReplicas: 1  # dev: 1, prod: 2
  maxReplicas: 10
  rules:
    - name: http-scaling
      http:
        metadata:
          concurrentRequests: "50"  # Scale up when > 50 concurrent requests per replica
```

#### Worker (Backup/Restore Jobs)
```yaml
# Scale on Redis queue depth (KEDA)
scale:
  minReplicas: 1
  maxReplicas: 6
  rules:
    - name: queue-scaling
      custom:
        type: redis
        metadata:
          listName: "shieldio:backup_queue"
          listLength: "5"  # Scale up when > 5 jobs queued
          host: "<redis-host>"
          port: "6380"
```

#### Frontend (Nginx)
```yaml
# Fixed replicas (static content, low CPU)
scale:
  minReplicas: 1
  maxReplicas: 2
  rules:
    - name: http-scaling
      http:
        metadata:
          concurrentRequests: "200"
```

### What Competitors Do

| Vendor | Scaling Approach |
|--------|-----------------|
| **Veeam** | Backup proxies scale by adding proxy VMs; user-managed |
| **Druva** | Fully managed cloud — auto-scales internally, no user control |
| **Rubrik** | Dedicated appliance + cloud scale-out; hardware-limited |
| **Commvault** | MediaAgent pools, user-managed scaling |

### Shieldio Approach

| Phase | What | How |
|-------|------|-----|
| **Now** | Fixed replicas, manual scaling | Dev: 1 replica, Prod: 2 replicas |
| **Phase 1** | HTTP-based auto-scale for backend | `concurrentRequests: 50` trigger |
| **Phase 2** | Queue-based auto-scale for workers | KEDA Redis scaler |
| **Phase 3** | Predictive scaling | Scale workers before scheduled backup windows |

---

## 5. Implementation Priority

| Week | Deliverable | Business Value |
|------|-------------|---------------|
| **1** | Graph API metrics collection in GraphClient | Know API budget usage per tenant |
| **1** | Performance metrics endpoint (`/diagnostics/performance`) | Baseline throughput numbers |
| **2** | System health dashboard (frontend admin page) | Visual dependency health at a glance |
| **2** | HTTP auto-scale for backend (Terraform update) | Handle traffic spikes automatically |
| **3** | Graph API budget visualization in UI | Show customers their API usage |
| **3** | Queue-based worker auto-scale (KEDA) | Scale backup workers on demand |
| **4** | Throughput benchmark suite + report | Marketing: "X items/min" on landing page |

---

## Sources

- [Microsoft Graph Throttling Limits](https://learn.microsoft.com/en-us/graph/throttling-limits)
- [Microsoft Graph Throttling Guidance](https://learn.microsoft.com/en-us/graph/throttling)
- [Veeam M365 Backup Performance](https://community.veeam.com/discussion-boards-66/m365-backup-what-is-the-normal-throughput-10339)
- [M365 Backup & Archive Performance](https://kb.probax.io/overview-backup-for-microsoft-365-performance-limitations)
- [Azure Container Apps Scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)
