"""Prometheus metrics — central registry for all KavachIQ metrics.

Usage:
    from app.observability import http_requests_total, http_request_duration
    http_requests_total.labels(method="GET", path="/api/tenants", status="200").inc()
"""
from prometheus_client import Counter, Histogram, Gauge
import re

# ── HTTP Request Metrics ──
http_requests_total = Counter(
    "kavachiq_http_requests_total",
    "Total HTTP requests",
    ["method", "path_template", "status"],
)

http_request_duration_seconds = Histogram(
    "kavachiq_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path_template"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── Backup Job Metrics ──
backup_jobs_total = Counter(
    "kavachiq_backup_jobs_total",
    "Total backup jobs by outcome",
    ["workload", "status"],
)

backup_job_duration_seconds = Histogram(
    "kavachiq_backup_job_duration_seconds",
    "Backup job execution time in seconds",
    ["workload"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600],
)

# ── Graph API Metrics ──
graph_api_calls_total = Counter(
    "kavachiq_graph_api_calls_total",
    "Total Microsoft Graph API calls",
    ["workload", "status"],
)

graph_api_duration_seconds = Histogram(
    "kavachiq_graph_api_duration_seconds",
    "Graph API call latency in seconds",
    ["workload"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ── Scheduler Metrics ──
scheduler_task_duration_seconds = Histogram(
    "kavachiq_scheduler_task_duration_seconds",
    "Scheduler task execution time in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

# ── Infrastructure Gauges ──
queue_depth = Gauge(
    "kavachiq_queue_depth",
    "Redis queue depth",
    ["queue"],
)

tenants_active = Gauge(
    "kavachiq_tenants_active",
    "Number of active tenants",
)

db_pool_utilization = Gauge(
    "kavachiq_db_pool_utilization_ratio",
    "Database connection pool utilization (0-1)",
)


# ── Path Normalization ──
# Prevents label cardinality explosion by replacing numeric IDs with {id}
_ID_PATTERN = re.compile(r"/\d+")
_KNOWN_PREFIXES = {
    "/api/jobs", "/api/tenants", "/api/exchange", "/api/onedrive",
    "/api/sharepoint", "/api/teams", "/api/entra_id", "/api/recovery",
    "/api/msp", "/api/billing", "/api/sla-policies", "/api/usage",
    "/api/onboard", "/api/auth", "/api/dashboard", "/api/health",
    "/api/diagnostics", "/api/alerts",
}

def normalize_path(path: str) -> str:
    """Normalize URL path for Prometheus labels.

    /api/jobs/backup/123 → /api/jobs/backup/{id}
    /api/tenants/5/workloads → /api/tenants/{id}/workloads
    /health → /health
    """
    if path in ("/health", "/health/deep", "/metrics", "/openapi.json"):
        return path
    # Replace numeric segments with {id}
    normalized = _ID_PATTERN.sub("/{id}", path)
    # Truncate unknown deep paths to prevent cardinality
    for prefix in _KNOWN_PREFIXES:
        if normalized.startswith(prefix):
            return normalized
    # Unknown path — just return first two segments
    parts = normalized.split("/")
    return "/".join(parts[:4]) if len(parts) > 4 else normalized
