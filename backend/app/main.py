"""KavachIQ — SaaS Data Protection — FastAPI Application Entry Point."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.errors import KavachIQError, RATE_LIMIT_EXCEEDED
from app.services.scheduler import start_scheduler, stop_scheduler
from app.models.dedup import DedupEntry          # noqa: F401 — ensure table is created
from app.models.worker_queue import WorkerQueueEntry  # noqa: F401 — ensure table is created
from app.models.msp_branding import MSPBranding  # noqa: F401 — ensure table is created
from app.models.billing import BillingRecord     # noqa: F401 — ensure table is created
from app.models.saas_workload_app import SaaSWorkloadApp  # noqa: F401 — ensure table is created
from app.models.user_preference import UserPreference     # noqa: F401 — ensure table is created
from app.models.user_tenant import UserTenant             # noqa: F401 — ensure table is created
from app.models.onboarding_step import OnboardingStep     # noqa: F401 — ensure table is created
from app.models.usage_metric import TenantUsageMetric     # noqa: F401 — ensure table is created

# Configure structured JSON logging for production
if settings.LOG_FORMAT == "json":
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "service": "backend",
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            # Attach optional context fields
            for attr in ("correlation_id", "user_id", "tenant_id", "error_code", "action", "duration_ms"):
                if hasattr(record, attr):
                    log_data[attr] = getattr(record, attr)
            return json.dumps(log_data)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup with DB connection retry (handles cold-start of PostgreSQL container)
    import asyncio as _aio
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            await init_db()
            logger.info("Database initialized")
            break
        except Exception as e:
            if attempt < max_retries:
                wait = attempt * 5  # 5s, 10s, 15s, 20s, 25s
                logger.warning(f"DB connection failed (attempt {attempt}/{max_retries}): {e}. Retrying in {wait}s...")
                await _aio.sleep(wait)
            else:
                logger.error(f"DB connection failed after {max_retries} attempts. Exiting.")
                raise

    # Initialize pluggable storage backend
    from app.services.storage_factory import create_storage_backend
    from app.services import storage as storage_module
    backend = create_storage_backend()
    storage_module.storage_service = storage_module.StorageService(backend)
    logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")

    # ── Schema migration (PostgreSQL only — SQLite uses create_all) ──
    _is_sqlite = "sqlite" in settings.DATABASE_URL
    if not _is_sqlite:
        try:
            from app.database import engine as _engine
            from sqlalchemy import text as _text
            async with _engine.begin() as _conn:
                for sql in [
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified INTEGER DEFAULT 0",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMP",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider VARCHAR(50)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_subject_id VARCHAR(255)",
                    "ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS initiated_by_user_id INTEGER",
                    "ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS approval_required INTEGER DEFAULT 0",
                    "ALTER TABLE restore_jobs ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20)",
                    "ALTER TABLE tenant_workload_apps ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(20) DEFAULT 'disabled' NOT NULL",
                    "UPDATE tenant_workload_apps SET lifecycle_status = 'enabled' WHERE enabled = 1 AND lifecycle_status = 'disabled'",
                ]:
                    try:
                        await _conn.execute(_text(sql))
                    except Exception:
                        pass
            logger.info("Auto-migration: schema columns verified")
        except Exception as e:
            logger.warning(f"Auto-migration skipped: {e}")

    # ── Seed data: users, memberships, onboarding steps, counters ──
    # Single module handles everything — atomic, idempotent, complete.
    if not _is_sqlite:
        try:
            from app.database import engine as _engine
            from app.services.seed import ensure_seed_users, sync_tenant_counters
            await ensure_seed_users(_engine)
            await sync_tenant_counters(_engine)
        except Exception as e:
            logger.warning(f"Seed data: {e}")

    start_scheduler()
    logger.info("Scheduler started")

    # Startup health validation — log warnings for broken dependencies
    from app.services.system_health import validate_startup_health
    await validate_startup_health()

    # Auto-bootstrap per-workload Entra app registrations
    # Creates 5 multi-tenant apps in KavachIQ's Entra tenant if they don't exist.
    # Idempotent — skips if already in DB or env vars not configured.
    try:
        from app.services.workload_bootstrap import bootstrap_workload_apps
        await bootstrap_workload_apps()
    except Exception as e:
        logger.warning(f"Workload bootstrap skipped: {e}")

    # Demo mode: auto-seed data if DB is empty
    if settings.DEMO_MODE:
        try:
            from app.database import async_session as _session
            from app.models.tenant import Tenant
            from sqlalchemy import select as _select
            async with _session() as _db:
                has_tenants = (await _db.execute(_select(Tenant))).scalar_one_or_none()
                if not has_tenants:
                    logger.info("DEMO_MODE: No tenants found, seeding demo data...")
                    # Import and run seed inline
                    import importlib.util, sys
                    spec = importlib.util.spec_from_file_location("seed", "/app/seed-demo.py")
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        await mod.seed()
                        logger.info("DEMO_MODE: Demo data seeded successfully")
                else:
                    logger.info("DEMO_MODE: Data already exists, skipping seed")
        except Exception as e:
            logger.warning(f"DEMO_MODE: Failed to seed data: {e}")

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="KavachIQ — SaaS Data Protection for Exchange, OneDrive, SharePoint, Teams, and Entra ID",
    lifespan=lifespan,
)

# CORS — configurable via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "X-Request-ID"],
)


# ── Security Headers Middleware ──
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.FORCE_HTTPS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response


# ── HTTPS Redirect (production only) ──
if settings.FORCE_HTTPS:
    @app.middleware("http")
    async def https_redirect(request: Request, call_next):
        if request.headers.get("x-forwarded-proto") == "http":
            url = request.url.replace(scheme="https")
            return JSONResponse(
                status_code=301,
                headers={"Location": str(url)},
                content={"detail": "Redirecting to HTTPS"},
            )
        return await call_next(request)


# ── Tiered Rate Limiting (Redis-backed, cross-pod) ──
# Uses redis_state.increment_rate() for distributed counting.
# Falls back to in-memory when Redis unavailable (dev without Redis).

# Tiered limits: (path_prefix, requests_per_minute)
RATE_LIMIT_TIERS = {
    "/api/auth/login": 20,       # Aggressive: prevent brute force
    "/api/auth/register": 10,    # Very aggressive: prevent spam
    "/api/onboard/": 60,         # Moderate: OAuth flow has multiple calls
    "/api/": settings.RATE_LIMIT_REQUESTS_PER_MINUTE or 600,  # Default: generous for authenticated API
}
# Exempt paths (never rate limited)
RATE_LIMIT_EXEMPT = {"/health", "/api/health", "/api/diagnostics/", "/openapi.json", "/docs"}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Tiered rate limiter — different limits for auth vs data vs admin endpoints."""
    path = request.url.path

    # Skip rate limiting if disabled or exempt path
    if settings.RATE_LIMIT_REQUESTS_PER_MINUTE == 0:
        return await call_next(request)
    if any(path.startswith(exempt) for exempt in RATE_LIMIT_EXEMPT):
        return await call_next(request)

    # Determine rate limit tier
    limit = RATE_LIMIT_TIERS.get("/api/", 600)  # Default
    for prefix, tier_limit in RATE_LIMIT_TIERS.items():
        if path.startswith(prefix):
            limit = tier_limit
            break

    # Use forwarded IP (behind load balancer) or direct IP
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    bucket = f"{client_ip}:{path.split('/')[2] if path.startswith('/api/') else 'other'}"
    window = 60

    # Redis-backed rate counting (cross-pod, survives restart)
    from app.services.redis_state import increment_rate
    count = await increment_rate(bucket, window_seconds=window)

    if count > limit:
        retry_after = window  # Simplified — Redis handles exact window
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "E7001",
                    "message": "Rate limit exceeded",
                    "detail": f"Limit is {limit} requests per {window}s. Try again in {retry_after}s.",
                    "fix": "Slow down your request rate and try again",
                    "retry_after": retry_after,
                },
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    remaining = max(0, limit - count)

    response = await call_next(request)
    # Add rate limit headers to all responses so frontend knows its budget
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID + Prometheus metrics to every request."""
    from app.observability import http_requests_total, http_request_duration_seconds, normalize_path

    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
    request.state.correlation_id = correlation_id

    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 1)
    duration_s = duration_ms / 1000.0

    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"

    # Prometheus metrics (skip /metrics to avoid self-referential noise)
    path_template = normalize_path(request.url.path)
    if path_template != "/metrics":
        http_requests_total.labels(
            method=request.method, path_template=path_template, status=str(response.status_code)
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method, path_template=path_template
        ).observe(duration_s)

    # Log request (skip noisy health checks)
    if not request.url.path.startswith("/health"):
        extra = {"correlation_id": correlation_id, "duration_ms": duration_ms}
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms) [cid={correlation_id}]",
            extra=extra,
        )

    return response


# ── Global Error Handlers ──

@app.exception_handler(KavachIQError)
async def kavachiq_error_handler(request: Request, exc: KavachIQError):
    """Handle structured KavachIQ errors — returns standardized error JSON."""
    return exc.error_def.response(request=request, detail=exc.detail, extra=exc.extra)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Pydantic / FastAPI validation errors — return structured format."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    errors = exc.errors()
    detail = "; ".join(f"{e['loc'][-1]}: {e['msg']}" for e in errors) if errors else str(exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "E6001",
                "message": "Invalid input data",
                "detail": detail,
                "fix": "Check the request body and try again",
                "correlation_id": correlation_id,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions — return clean JSON, never leak stack traces."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "E5000",
                "message": "Internal server error",
                "detail": "An unexpected error occurred. Our team has been notified.",
                "fix": "If the problem persists, contact support with the correlation ID",
                "correlation_id": correlation_id,
            }
        },
    )


# Register API routers
from app.api.auth import router as auth_router
from app.api.tenants import router as tenants_router
from app.api.sla_policies import router as sla_router
from app.api.exchange import router as exchange_router
from app.api.onedrive import router as onedrive_router
from app.api.sharepoint import router as sharepoint_router
from app.api.jobs import router as jobs_router
from app.api.dashboard import router as dashboard_router
from app.api.audit import router as audit_router
from app.api.failed_items import router as failed_items_router
from app.api.entra_id import router as entra_id_router
from app.api.teams import router as teams_router
from app.api.alerts import router as alerts_router
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.sensitive_data import router as sensitive_data_router
from app.api.validation import router as validation_router
from app.api.self_restore import router as self_restore_router
from app.api.reports import router as reports_router
from app.api.usage import router as usage_router
from app.api.status import router as status_router
from app.api.export import router as export_router
from app.api.recovery import router as recovery_router
from app.api.org_context import router as org_context_router
from app.api.diagnostics import router as diagnostics_router

app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(sla_router)
app.include_router(exchange_router)
app.include_router(onedrive_router)
app.include_router(sharepoint_router)
app.include_router(entra_id_router)
app.include_router(teams_router)
app.include_router(jobs_router)
app.include_router(dashboard_router)
app.include_router(audit_router)
app.include_router(failed_items_router)
app.include_router(alerts_router)
app.include_router(health_router)
app.include_router(search_router)
app.include_router(sensitive_data_router)
app.include_router(validation_router)
app.include_router(self_restore_router)
app.include_router(reports_router)
app.include_router(usage_router)
app.include_router(status_router)
app.include_router(export_router)
app.include_router(recovery_router)

from app.api.onboarding import router as onboarding_router
from app.api.security import router as security_router
from app.api.benchmarks import router as benchmarks_router
from app.api.docs_api import router as docs_api_router
app.include_router(onboarding_router)
app.include_router(security_router)
app.include_router(benchmarks_router)
app.include_router(docs_api_router)
app.include_router(org_context_router)
app.include_router(diagnostics_router)

from app.api.msp import router as msp_router
from app.api.feature_flags import router as feature_flags_router
from app.api.agents import router as agents_router
from app.api.billing import router as billing_router
from app.api.security_posture import router as security_posture_router
from app.api.restore_approval import router as restore_approval_router
app.include_router(msp_router)
app.include_router(feature_flags_router)
app.include_router(agents_router)
app.include_router(billing_router)
app.include_router(security_posture_router)
app.include_router(restore_approval_router)

from app.api.restore_consent import router as restore_consent_router
app.include_router(restore_consent_router)

from app.api.workload_apps import router as workload_apps_router
app.include_router(workload_apps_router)

from app.api.ediscovery import router as ediscovery_router
app.include_router(ediscovery_router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint for Grafana/PagerDuty/Datadog.

    Uses prometheus-client library for proper metric types (Counter, Histogram, Gauge).
    Gauges are updated on each scrape; Counters/Histograms are updated by middleware.
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    from app.observability import tenants_active, db_pool_utilization, queue_depth

    # Update gauge metrics on each scrape
    try:
        from app.database import async_session, engine
        from sqlalchemy import text
        async with async_session() as db:
            tc = (await db.execute(text("SELECT COUNT(*) FROM tenants WHERE status = 'active'"))).scalar() or 0
            tenants_active.set(tc)
        pool = engine.pool
        total = pool.size() + pool.overflow()
        db_pool_utilization.set(pool.checkedout() / max(total, 1))
    except Exception:
        pass

    # Update queue depth gauges
    try:
        if settings.DISPATCH_MODE == "redis":
            from app.interfaces.dispatcher_factory import get_dispatcher
            dispatcher = get_dispatcher()
            lengths = await dispatcher.queue_length()
            for q, length in lengths.items():
                if length >= 0:
                    queue_depth.labels(queue=q).set(length)
    except Exception:
        pass

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# DEBUG ENDPOINTS REMOVED — were leaking password hashes and stack traces.
# Auto-migration handles schema changes in lifespan startup.
# Use /health/deep for diagnostics instead.


# /api/admin/migrate REMOVED — migrations run automatically in lifespan startup.
# Schema changes are handled by auto-migration in the startup sequence above.


@app.get("/health")
async def health():
    """Deep health check — verifies DB and storage connectivity."""
    checks = {"database": "unknown", "storage": "unknown"}
    healthy = True

    # Check database
    try:
        from app.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:100]}"
        healthy = False

    # Check storage
    try:
        from app.services.storage import storage_service
        if storage_service and storage_service.backend:
            checks["storage"] = "healthy"
        else:
            checks["storage"] = "not initialized"
    except Exception as e:
        checks["storage"] = f"unhealthy: {str(e)[:100]}"
        healthy = False

    # Check Redis queue depth (observability for KEDA auto-scaling)
    if settings.DISPATCH_MODE == "redis":
        try:
            from app.interfaces.dispatcher_factory import get_dispatcher
            dispatcher = get_dispatcher()
            checks["queues"] = await dispatcher.queue_length()
        except Exception as e:
            checks["queues"] = f"unavailable: {str(e)[:100]}"

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if healthy else "degraded",
            "version": settings.APP_VERSION,
            "checks": checks,
        },
    )


@app.get("/health/deep")
async def deep_health_check():
    """Deep health check — validates ALL external dependencies.

    Used by deploy scripts BEFORE routing traffic to a new revision.
    Checks: database, storage, M365 connector, Stripe, email, Redis,
    demo data, and secret expiry.
    """
    from datetime import datetime, timedelta
    checks = {}
    warnings = []

    # 1. Database
    try:
        from app.database import async_session
        from sqlalchemy import text, func
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
            # Check user count (fresh DB = problem)
            from app.models.user import User
            user_count = (await db.execute(func.count(User.id))).scalar() or 0
            checks["database"] = {"status": "healthy", "users": user_count}
            if user_count == 0:
                checks["database"]["status"] = "degraded"
                checks["database"]["issue"] = "No users — fresh DB needs seeding"

            # Pool health metrics (PostgreSQL only)
            try:
                pool = _engine.pool
                pool_size = pool.size()
                checked_out = pool.checkedout()
                overflow = pool.overflow()
                max_capacity = pool_size + (pool._max_overflow if hasattr(pool, '_max_overflow') else 50)
                utilization = checked_out / max(max_capacity, 1)
                checks["database"]["pool"] = {
                    "size": pool_size,
                    "checked_out": checked_out,
                    "overflow": overflow,
                    "max_capacity": max_capacity,
                    "utilization_pct": round(utilization * 100),
                }
                if utilization > 0.8:
                    checks["database"]["status"] = "degraded"
                    checks["database"]["pool"]["warning"] = f"Pool {utilization:.0%} utilized — approaching saturation"
                    warnings.append(f"DB pool at {utilization:.0%}")
            except Exception:
                pass  # NullPool (SQLite) doesn't have these attributes

    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)[:100]}

    # 2. Storage
    try:
        from app.services.storage import storage_service
        if storage_service and storage_service.backend:
            checks["storage"] = {"status": "healthy"}
        else:
            checks["storage"] = {"status": "degraded", "issue": "Not initialized"}
    except Exception as e:
        checks["storage"] = {"status": "unhealthy", "error": str(e)[:100]}

    # 3. M365 Connector (Entra app secret valid)
    try:
        if settings.CONNECTOR_APP_ID and settings.CONNECTOR_APP_SECRET:
            import msal
            app = msal.ConfidentialClientApplication(
                settings.CONNECTOR_APP_ID,
                authority="https://login.microsoftonline.com/common",
                client_credential=settings.CONNECTOR_APP_SECRET,
            )
            # Try to get a token (validates secret)
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            if "access_token" in result:
                checks["connector"] = {"status": "healthy", "app_id": settings.CONNECTOR_APP_ID[:8] + "..."}
            else:
                checks["connector"] = {"status": "unhealthy", "error": result.get("error_description", "Token acquisition failed")[:100]}
        else:
            checks["connector"] = {"status": "not_configured"}
    except Exception as e:
        checks["connector"] = {"status": "unhealthy", "error": str(e)[:100]}

    # 4. Stripe
    try:
        if settings.STRIPE_SECRET_KEY and "not-configured" not in settings.STRIPE_SECRET_KEY:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
            # Lightweight check — list 1 product
            stripe.Product.list(limit=1)
            checks["stripe"] = {"status": "healthy"}
        else:
            checks["stripe"] = {"status": "not_configured"}
    except Exception as e:
        checks["stripe"] = {"status": "unhealthy", "error": str(e)[:100]}

    # 5. Email (Resend)
    try:
        if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY and "not-configured" not in settings.RESEND_API_KEY:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            # Validate API key by listing domains
            domains = resend.Domains.list()
            checks["email"] = {"status": "healthy", "provider": "resend"}
        elif settings.EMAIL_PROVIDER == "console":
            checks["email"] = {"status": "healthy", "provider": "console (dev mode)"}
        else:
            checks["email"] = {"status": "not_configured"}
    except Exception as e:
        checks["email"] = {"status": "degraded", "error": str(e)[:100], "provider": settings.EMAIL_PROVIDER}

    # 6. Redis
    try:
        if settings.REDIS_URL:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
            await r.ping()
            await r.aclose()
            checks["redis"] = {"status": "healthy"}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "degraded", "error": str(e)[:100]}

    # 7. Demo data (tenants + objects)
    try:
        from app.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            tenant_count = (await db.execute(text("SELECT COUNT(*) FROM tenants"))).scalar() or 0
            object_count = (await db.execute(text("SELECT COUNT(*) FROM protected_objects"))).scalar() or 0
            checks["demo_data"] = {
                "status": "healthy" if tenant_count > 0 else "degraded",
                "tenants": tenant_count,
                "objects": object_count,
            }
            if tenant_count == 0:
                checks["demo_data"]["issue"] = "No tenants — run demo seed"
    except Exception as e:
        checks["demo_data"] = {"status": "unknown", "error": str(e)[:100]}

    # 8. Config validation
    config_issues = []
    if not settings.CONNECTOR_APP_ID:
        config_issues.append("CONNECTOR_APP_ID not set")
    if not settings.CONNECTOR_APP_SECRET or "not-configured" in str(settings.CONNECTOR_APP_SECRET):
        config_issues.append("CONNECTOR_APP_SECRET not set")
    if settings.FRONTEND_URL == "http://localhost:5173":
        config_issues.append("FRONTEND_URL still localhost (not production)")
    if settings.CORS_ORIGINS == "*":
        config_issues.append("CORS_ORIGINS is wildcard (not production)")

    checks["config"] = {
        "status": "healthy" if not config_issues else "degraded",
        "issues": config_issues if config_issues else None,
    }

    # 9. Stale jobs (stuck IN_PROGRESS beyond timeout)
    try:
        from app.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            stale_result = await db.execute(text(
                "SELECT COUNT(*) FROM backup_jobs "
                "WHERE status = 'in_progress' "
                f"AND started_at < NOW() - INTERVAL '{settings.JOB_TIMEOUT_MINUTES} minutes'"
            ))
            stale_count = stale_result.scalar() or 0
            checks["stale_jobs"] = {
                "status": "healthy" if stale_count == 0 else "degraded",
                "stuck_jobs": stale_count,
            }
            if stale_count > 0:
                checks["stale_jobs"]["issue"] = f"{stale_count} backup jobs stuck IN_PROGRESS beyond {settings.JOB_TIMEOUT_MINUTES}min timeout"
                warnings.append(f"{stale_count} stale backup jobs")
    except Exception as e:
        checks["stale_jobs"] = {"status": "unknown", "error": str(e)[:100]}

    # 10. Storage capacity (local filesystem)
    try:
        import shutil
        if settings.STORAGE_BACKEND == "local" or settings.STORAGE_BACKEND == "minio":
            storage_path = settings.BACKUP_STORAGE_PATH
            usage = shutil.disk_usage(storage_path)
            pct = usage.used / usage.total if usage.total > 0 else 0
            checks["storage_capacity"] = {
                "status": "healthy" if pct < 0.85 else ("degraded" if pct < 0.95 else "unhealthy"),
                "disk_used_pct": round(pct * 100),
                "free_gb": round(usage.free / (1024**3), 1),
                "total_gb": round(usage.total / (1024**3), 1),
            }
            if pct >= 0.85:
                checks["storage_capacity"]["warning"] = f"Disk {pct:.0%} full"
                warnings.append(f"Storage disk {pct:.0%} used")
        else:
            checks["storage_capacity"] = {"status": "healthy", "backend": settings.STORAGE_BACKEND}
    except Exception as e:
        checks["storage_capacity"] = {"status": "unknown", "error": str(e)[:100]}

    # Summary
    statuses = [c.get("status", "unknown") for c in checks.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    status_code = 200 if overall == "healthy" else (503 if overall == "unhealthy" else 200)
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        },
    )
