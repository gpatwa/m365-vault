"""M365 Data Protection — FastAPI Application Entry Point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.services.scheduler import start_scheduler, stop_scheduler

# Configure logging
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

    # Ensure backup storage directory exists
    import os
    os.makedirs(settings.BACKUP_STORAGE_PATH, exist_ok=True)

    start_scheduler()
    logger.info("Scheduler started")

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="M365 Vault — Enterprise Backup & Recovery for Exchange, OneDrive, and SharePoint",
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(sla_router)
app.include_router(exchange_router)
app.include_router(onedrive_router)
app.include_router(sharepoint_router)
app.include_router(jobs_router)
app.include_router(dashboard_router)
app.include_router(audit_router)
app.include_router(failed_items_router)


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
    return {"status": "healthy"}
