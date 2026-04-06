"""System Health Service — validates all critical dependencies at startup and on-demand.

Provides:
1. Startup validation gate — prevents serving traffic if critical config is broken
2. On-demand diagnostics — admin can test every dependency from the UI
3. Structured health reporting — every check returns status, detail, and fix action
"""
import logging
import time
from datetime import datetime
from typing import Optional

import msal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


class HealthCheck:
    """Result of a single health check."""
    def __init__(self, name: str, healthy: bool, detail: str = "", fix: str = "", latency_ms: int = 0):
        self.name = name
        self.healthy = healthy
        self.detail = detail
        self.fix = fix
        self.latency_ms = latency_ms

    def to_dict(self):
        return {
            "name": self.name,
            "healthy": self.healthy,
            "detail": self.detail,
            "fix": self.fix if not self.healthy else "",
            "latency_ms": self.latency_ms,
        }


class SystemHealthService:
    """Validates all critical system dependencies."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def run_all_checks(self) -> dict:
        """Run all health checks and return structured report."""
        checks = []

        checks.append(self.check_secret_key())
        checks.append(self.check_encryption_key())
        checks.append(self.check_connector_config())
        checks.append(await self.check_connector_secret())

        if self.db:
            checks.append(await self.check_database())

        checks.append(self.check_storage_config())
        checks.append(self.check_cors_config())

        healthy_count = sum(1 for c in checks if c.healthy)
        total = len(checks)
        all_healthy = healthy_count == total

        return {
            "healthy": all_healthy,
            "score": f"{healthy_count}/{total}",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [c.to_dict() for c in checks],
            "critical_failures": [c.to_dict() for c in checks if not c.healthy],
        }

    def check_secret_key(self) -> HealthCheck:
        """Verify JWT secret key is configured."""
        key = settings.SECRET_KEY
        if not key or key == "change-me-in-production":
            return HealthCheck("secret_key", False,
                "JWT secret key not configured or using default",
                "Set SECRET_KEY environment variable to a secure random string (64+ chars)")
        return HealthCheck("secret_key", True, f"Configured ({len(key)} chars)")

    def check_encryption_key(self) -> HealthCheck:
        """Verify encryption master key is configured."""
        key = settings.ENCRYPTION_MASTER_KEY
        if not key:
            return HealthCheck("encryption_key", False,
                "Encryption master key not configured",
                "Set ENCRYPTION_MASTER_KEY environment variable (base64-encoded 32-byte key)")
        return HealthCheck("encryption_key", True, "Configured")

    def check_connector_config(self) -> HealthCheck:
        """Verify M365 connector app ID is configured."""
        app_id = settings.CONNECTOR_APP_ID
        secret = settings.CONNECTOR_APP_SECRET
        if not app_id:
            return HealthCheck("connector_app_id", False,
                "CONNECTOR_APP_ID not set — M365 onboarding will be disabled",
                "Set CONNECTOR_APP_ID to the Azure AD multi-tenant app registration ID")
        if not secret:
            return HealthCheck("connector_app_secret", False,
                "CONNECTOR_APP_SECRET not set — M365 token exchange will fail",
                "Set CONNECTOR_APP_SECRET to the app registration client secret value")
        return HealthCheck("connector_config", True,
            f"App ID: {app_id[:8]}..., Secret: {secret[:4]}... ({len(secret)} chars)")

    async def check_connector_secret(self) -> HealthCheck:
        """Actually test the connector secret against Azure AD."""
        app_id = settings.CONNECTOR_APP_ID
        secret = settings.CONNECTOR_APP_SECRET
        if not app_id or not secret:
            return HealthCheck("connector_secret_test", False,
                "Cannot test — credentials not configured", "Configure CONNECTOR_APP_ID and CONNECTOR_APP_SECRET")

        start = time.time()
        try:
            msal_app = msal.ConfidentialClientApplication(
                client_id=app_id,
                client_credential=secret,
                authority="https://login.microsoftonline.com/common",
            )
            token = msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            latency = int((time.time() - start) * 1000)

            if "error" in token:
                error_desc = token.get("error_description", "")
                # AADSTS7000215 = bad secret
                if "AADSTS7000215" in error_desc:
                    return HealthCheck("connector_secret_test", False,
                        f"INVALID SECRET — Azure AD rejected the client secret (latency: {latency}ms)",
                        "The secret value is wrong. Go to Azure Portal > App Registrations > "
                        f"{app_id} > Certificates & Secrets > create a new secret > update CONNECTOR_APP_SECRET",
                        latency)
                # AADSTS7000229 = no SP in home tenant (OK for multi-tenant)
                if "AADSTS7000229" in error_desc:
                    return HealthCheck("connector_secret_test", True,
                        f"Multi-tenant app ready (no SP in home tenant, which is normal) — latency: {latency}ms",
                        latency_ms=latency)
                # AADSTS53003 = Conditional Access blocking — secret is valid but policy blocks
                if "AADSTS53003" in error_desc:
                    return HealthCheck("connector_secret_test", True,
                        f"Credentials valid (CA policy active in home tenant) — latency: {latency}ms",
                        latency_ms=latency)
                return HealthCheck("connector_secret_test", False,
                    f"Token error: {error_desc[:150]}", "Check Azure AD app configuration", latency)

            return HealthCheck("connector_secret_test", True,
                f"Token acquired successfully — latency: {latency}ms", latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return HealthCheck("connector_secret_test", False,
                f"Exception: {str(e)[:150]}", "Check network connectivity to login.microsoftonline.com", latency)

    async def check_database(self) -> HealthCheck:
        """Test database connectivity."""
        if not self.db:
            return HealthCheck("database", False, "No DB session", "Check DATABASE_URL")
        start = time.time()
        try:
            await self.db.execute(text("SELECT 1"))
            latency = int((time.time() - start) * 1000)
            return HealthCheck("database", True, f"Connected — latency: {latency}ms", latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return HealthCheck("database", False, f"Connection failed: {str(e)[:100]}",
                "Check DATABASE_URL and PostgreSQL connectivity", latency)

    def check_storage_config(self) -> HealthCheck:
        """Verify storage backend is configured."""
        backend = settings.STORAGE_BACKEND
        if backend == "azure":
            conn_str = settings.AZURE_STORAGE_CONNECTION_STRING
            if not conn_str:
                return HealthCheck("storage", False,
                    "Azure storage backend selected but AZURE_STORAGE_CONNECTION_STRING not set",
                    "Set AZURE_STORAGE_CONNECTION_STRING")
            return HealthCheck("storage", True, f"Azure Blob Storage configured")
        elif backend == "local":
            return HealthCheck("storage", True, f"Local storage at {getattr(settings, 'STORAGE_LOCAL_PATH', '/tmp/kavachiq-storage')}")
        elif backend == "minio":
            return HealthCheck("storage", True, "MinIO S3-compatible storage")
        return HealthCheck("storage", False, f"Unknown backend: {backend}", "Set STORAGE_BACKEND to azure, local, or minio")

    def check_cors_config(self) -> HealthCheck:
        """Check CORS configuration."""
        origins = settings.CORS_ORIGINS
        if origins == "*":
            return HealthCheck("cors", True, "CORS: allow all origins (dev mode)")
        if not origins:
            return HealthCheck("cors", False, "No CORS origins configured", "Set CORS_ORIGINS")
        return HealthCheck("cors", True, f"CORS: {origins[:100]}")


async def validate_startup_health():
    """Run at startup — log warnings for any broken dependencies."""
    service = SystemHealthService()
    report = await service.run_all_checks()

    if report["healthy"]:
        logger.info(f"Startup health check: ALL PASSED ({report['score']})")
    else:
        for failure in report["critical_failures"]:
            logger.error(
                f"STARTUP HEALTH FAILURE: {failure['name']} — {failure['detail']} "
                f"FIX: {failure['fix']}"
            )
        logger.warning(f"Startup health check: {report['score']} passed. "
                       f"{len(report['critical_failures'])} critical failures. "
                       f"Some features may not work.")

    return report
