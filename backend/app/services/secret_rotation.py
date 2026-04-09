"""Secret rotation — expiry monitoring and alerting.

Checks SaaS workload app secrets for approaching expiry dates.
Alerts at configurable thresholds (30 days = warning, 7 days = critical).
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


async def check_expiring_secrets():
    """Check all SaaS workload app secrets for approaching expiry.

    Called by scheduler every 6 hours. Alerts via alert_service.
    """
    from app.database import async_session
    from app.models.saas_workload_app import SaaSWorkloadApp

    warning_threshold = timedelta(days=settings.SECRET_ROTATION_WARNING_DAYS)
    critical_threshold = timedelta(days=settings.SECRET_ROTATION_CRITICAL_DAYS)
    now = datetime.utcnow()

    async with async_session() as db:
        result = await db.execute(
            select(SaaSWorkloadApp).where(
                SaaSWorkloadApp.secret_expires_at.isnot(None)
            )
        )
        apps = result.scalars().all()

        expiring = []
        for app in apps:
            days_until = (app.secret_expires_at - now).days

            if days_until <= 0:
                severity = "critical"
                status = "expired"
            elif days_until <= critical_threshold.days:
                severity = "critical"
                status = "critical"
            elif days_until <= warning_threshold.days:
                severity = "warning"
                status = "warning"
            else:
                continue  # Healthy

            expiring.append({
                "app_id": app.id,
                "workload": app.workload,
                "client_id": app.app_id[:8] + "...",
                "expires_at": app.secret_expires_at.isoformat(),
                "days_until_expiry": days_until,
                "severity": severity,
                "status": status,
            })

            # Send alert
            try:
                from app.services.alert_service import alert_service
                await alert_service.notify(
                    event_type="secret.expiring",
                    title=f"SaaS app secret {status}: {app.workload}",
                    details=f"Client ID {app.app_id[:8]}... expires in {days_until} days ({app.secret_expires_at.strftime('%Y-%m-%d')})",
                    severity=severity,
                )
            except Exception:
                pass

        if expiring:
            logger.warning(f"Secret rotation: {len(expiring)} secrets need attention")

        return expiring


async def get_secret_status() -> list[dict]:
    """Get expiry status for all SaaS workload app secrets.

    Used by /api/diagnostics/secrets endpoint. Returns status without
    exposing actual secret values.
    """
    from app.database import async_session
    from app.models.saas_workload_app import SaaSWorkloadApp

    now = datetime.utcnow()

    async with async_session() as db:
        result = await db.execute(select(SaaSWorkloadApp))
        apps = result.scalars().all()

        statuses = []
        for app in apps:
            if not app.secret_expires_at:
                status = "no_expiry_set"
                days_until = None
            else:
                days_until = (app.secret_expires_at - now).days
                if days_until <= 0:
                    status = "expired"
                elif days_until <= settings.SECRET_ROTATION_CRITICAL_DAYS:
                    status = "critical"
                elif days_until <= settings.SECRET_ROTATION_WARNING_DAYS:
                    status = "warning"
                else:
                    status = "healthy"

            statuses.append({
                "workload": app.workload,
                "client_id": app.app_id[:8] + "..." if app.app_id else None,
                "status": status,
                "expires_at": app.secret_expires_at.isoformat() if app.secret_expires_at else None,
                "days_until_expiry": days_until,
            })

        return statuses
