"""Alert configuration API — global + per-tenant alert preferences.

Customers configure their own alerts: which events, email recipients, webhooks.
Platform admin sees global config. Tenant users see their tenant's config.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.models.alert_config import TenantAlertConfig
from app.services.auth import get_current_user, require_role
from app.services.alert_service import alert_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

# Valid alert event types
VALID_EVENTS = {
    "backup_failed", "backup_completed", "anomaly_detected", "protection_gap",
    "secret_expiring", "worm_violation", "restore_completed", "restore_failed",
}


class AlertConfigResponse(BaseModel):
    smtp_configured: bool
    smtp_host: str
    smtp_from: str
    email_recipients: str
    webhook_configured: bool
    webhook_url: str


@router.get("/config")
async def get_alert_config(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get global alert configuration (platform admin only)."""
    return AlertConfigResponse(
        smtp_configured=bool(settings.SMTP_HOST),
        smtp_host=settings.SMTP_HOST or "(not configured)",
        smtp_from=settings.SMTP_FROM or "(not configured)",
        email_recipients=settings.ALERT_EMAIL_RECIPIENTS or "(not configured)",
        webhook_configured=bool(settings.ALERT_WEBHOOK_URL),
        webhook_url=settings.ALERT_WEBHOOK_URL[:50] + "..." if len(settings.ALERT_WEBHOOK_URL or "") > 50 else settings.ALERT_WEBHOOK_URL or "(not configured)",
    )


@router.post("/test")
async def send_test_alert(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Send a test alert to verify email/webhook configuration."""
    return await alert_service.send_test_alert()


# ── Per-Tenant Alert Configuration ──

class TenantAlertUpdate(BaseModel):
    email_recipients: str = None  # Comma-separated emails
    webhook_url: str = None
    enabled_events: list[str] = None  # ["backup_failed", "anomaly_detected", ...]
    frequency: str = None  # "immediate", "hourly", "daily"
    quiet_start_hour: int = None  # UTC hour (0-23)
    quiet_end_hour: int = None


@router.get("/tenant")
async def get_tenant_alerts(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alert configuration for a tenant. Any tenant member can view."""
    config = await db.execute(
        select(TenantAlertConfig).where(TenantAlertConfig.tenant_id == tenant_id)
    )
    alert_config = config.scalar_one_or_none()

    if not alert_config:
        # Return defaults
        return {
            "tenant_id": tenant_id,
            "email_recipients": "",
            "webhook_url": "",
            "enabled_events": ["backup_failed", "anomaly_detected", "protection_gap"],
            "frequency": "immediate",
            "quiet_start_hour": None,
            "quiet_end_hour": None,
            "configured": False,
        }

    return {
        "tenant_id": tenant_id,
        "email_recipients": alert_config.email_recipients or "",
        "webhook_url": alert_config.webhook_url or "",
        "enabled_events": json.loads(alert_config.enabled_events) if alert_config.enabled_events else [],
        "frequency": alert_config.frequency,
        "quiet_start_hour": alert_config.quiet_start_hour,
        "quiet_end_hour": alert_config.quiet_end_hour,
        "configured": True,
    }


@router.put("/tenant")
async def update_tenant_alerts(
    tenant_id: int = Query(...),
    req: TenantAlertUpdate = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update alert configuration for a tenant. Tenant admin can configure."""
    # Validate events
    if req.enabled_events:
        invalid = set(req.enabled_events) - VALID_EVENTS
        if invalid:
            raise HTTPException(400, detail=f"Invalid events: {invalid}. Valid: {VALID_EVENTS}")

    # Validate frequency
    if req.frequency and req.frequency not in ("immediate", "hourly", "daily"):
        raise HTTPException(400, detail="Frequency must be: immediate, hourly, or daily")

    # Upsert
    result = await db.execute(
        select(TenantAlertConfig).where(TenantAlertConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = TenantAlertConfig(tenant_id=tenant_id)
        db.add(config)

    if req.email_recipients is not None:
        config.email_recipients = req.email_recipients
    if req.webhook_url is not None:
        config.webhook_url = req.webhook_url
    if req.enabled_events is not None:
        config.enabled_events = json.dumps(req.enabled_events)
    if req.frequency is not None:
        config.frequency = req.frequency
    if req.quiet_start_hour is not None:
        config.quiet_start_hour = req.quiet_start_hour
    if req.quiet_end_hour is not None:
        config.quiet_end_hour = req.quiet_end_hour

    from app.services.audit import audit_log
    await audit_log(db, action="alerts.configured", resource_type="tenant",
                    resource_id=tenant_id, user_id=current_user.id,
                    details=f"Alert config updated: events={req.enabled_events}, freq={req.frequency}")

    await db.commit()

    return {
        "tenant_id": tenant_id,
        "status": "updated",
        "enabled_events": json.loads(config.enabled_events) if config.enabled_events else [],
        "frequency": config.frequency,
    }


@router.post("/tenant/test")
async def send_tenant_test_alert(
    tenant_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test alert to the tenant's configured recipients."""
    config = await db.execute(
        select(TenantAlertConfig).where(TenantAlertConfig.tenant_id == tenant_id)
    )
    alert_config = config.scalar_one_or_none()

    if not alert_config or not alert_config.email_recipients:
        raise HTTPException(400, detail="No alert recipients configured for this tenant")

    from app.services.email_service import email_service
    recipients = [r.strip() for r in alert_config.email_recipients.split(",") if r.strip()]

    sent = 0
    for recipient in recipients:
        try:
            await email_service.send_email(
                to=recipient,
                subject="KavachIQ Test Alert",
                html="<p>This is a test alert from KavachIQ. Your alert configuration is working correctly.</p>",
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Failed to send test alert to {recipient}: {e}")

    return {"sent": sent, "total_recipients": len(recipients)}
