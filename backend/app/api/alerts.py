"""Alert configuration API routes."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.user import User, UserRole
from app.services.auth import get_current_user, require_role
from app.services.alert_service import alert_service
from app.config import settings

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


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
    """Get current alert configuration."""
    return AlertConfigResponse(
        smtp_configured=bool(settings.SMTP_HOST),
        smtp_host=settings.SMTP_HOST or "(not configured)",
        smtp_from=settings.SMTP_FROM or "(not configured)",
        email_recipients=settings.ALERT_EMAIL_RECIPIENTS or "(not configured)",
        webhook_configured=bool(settings.ALERT_WEBHOOK_URL),
        webhook_url=settings.ALERT_WEBHOOK_URL[:50] + "..." if len(settings.ALERT_WEBHOOK_URL) > 50 else settings.ALERT_WEBHOOK_URL or "(not configured)",
    )


@router.post("/test")
async def send_test_alert(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Send a test alert to verify email/webhook configuration."""
    return await alert_service.send_test_alert()
