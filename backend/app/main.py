"""Shieldio — SaaS Data Protection — FastAPI Application Entry Point."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.services.scheduler import start_scheduler, stop_scheduler
from app.models.dedup import DedupEntry          # noqa: F401 — ensure table is created
from app.models.worker_queue import WorkerQueueEntry  # noqa: F401 — ensure table is created

# Configure structured JSON logging for production
if settings.LOG_FORMAT == "json":
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            if hasattr(record, "correlation_id"):
                log_data["correlation_id"] = record.correlation_id
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
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    logger.info("Database initialized")

    # Initialize pluggable storage backend
    from app.services.storage_factory import create_storage_backend
    from app.services import storage as storage_module
    backend = create_storage_backend()
    storage_module.storage_service = storage_module.StorageService(backend)
    logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")

    start_scheduler()
    logger.info("Scheduler started")

    # Startup health validation — log warnings for broken dependencies
    from app.services.system_health import validate_startup_health
    await validate_startup_health()

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
    description="Shieldio — SaaS Data Protection for Exchange, OneDrive, SharePoint, Teams, and Entra ID",
    lifespan=lifespan,
)

# CORS — configurable via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ── Tiered Rate Limiting ──
# Different limits for different endpoint categories
_rate_limit_store: dict[str, list[float]] = {}

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
    now = time.time()
    window = 60

    if bucket not in _rate_limit_store:
        _rate_limit_store[bucket] = []

    _rate_limit_store[bucket] = [t for t in _rate_limit_store[bucket] if now - t < window]

    if len(_rate_limit_store[bucket]) >= limit:
        remaining = 0
        reset_at = int(_rate_limit_store[bucket][0] + window)
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Please slow down.",
                "limit": limit,
                "window": f"{window}s",
                "retry_after": max(1, reset_at - int(now)),
            },
            headers={
                "Retry-After": str(max(1, reset_at - int(now))),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
            },
        )

    _rate_limit_store[bucket].append(now)
    remaining = limit - len(_rate_limit_store[bucket])

    response = await call_next(request)
    # Add rate limit headers to all responses so frontend knows its budget
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to every request for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
    request.state.correlation_id = correlation_id

    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 1)

    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"

    # Log request (skip noisy health checks)
    if not request.url.path.startswith("/health"):
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms) [cid={correlation_id}]"
        )

    return response


# ── Global Error Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions — return clean JSON, never leak stack traces."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "correlation_id": correlation_id,
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


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


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

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if healthy else "degraded",
            "version": settings.APP_VERSION,
            "checks": checks,
        },
    )
