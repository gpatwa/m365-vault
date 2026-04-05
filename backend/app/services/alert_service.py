"""Alert service — sends notifications via email and webhooks.

Supports:
- Email alerts via SMTP
- Webhook alerts via HTTP POST (Slack, Teams, custom endpoints)
- Configurable alert routing based on event type
"""
import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Sends alerts via email and webhooks."""

    async def notify(
        self,
        event_type: str,
        title: str,
        details: str,
        severity: str = "info",
        tenant_name: str = None,
        workload: str = None,
    ):
        """Send alert to all configured channels.

        Event types: backup.failed, backup.partial, sla.violation,
                     anomaly.detected, auth.expired, storage.warning
        """
        payload = {
            "event_type": event_type,
            "title": title,
            "details": details,
            "severity": severity,
            "tenant": tenant_name,
            "workload": workload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Send email if configured
        if settings.SMTP_HOST and settings.ALERT_EMAIL_RECIPIENTS:
            try:
                await self._send_email(
                    to=settings.ALERT_EMAIL_RECIPIENTS,
                    subject=f"[KavachIQ] [{severity.upper()}] {title}",
                    body=self._format_email(payload),
                )
            except Exception as e:
                logger.error(f"Email alert failed: {e}")

        # Send webhook if configured
        if settings.ALERT_WEBHOOK_URL:
            try:
                await self._send_webhook(settings.ALERT_WEBHOOK_URL, payload)
            except Exception as e:
                logger.error(f"Webhook alert failed: {e}")

        logger.info(f"Alert sent: [{severity}] {title}")

    async def _send_email(self, to: str, subject: str, body: str):
        """Send email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or f"m365vault@{settings.SMTP_HOST}"
        msg["To"] = to
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_PORT == 587:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], to.split(","), msg.as_string())

    async def _send_webhook(self, url: str, payload: dict):
        """Send webhook via HTTP POST."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 400:
                logger.warning(f"Webhook returned {response.status_code}: {response.text[:200]}")

    def _format_email(self, payload: dict) -> str:
        """Format alert as HTML email."""
        severity_colors = {
            "info": "#3b82f6",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "critical": "#dc2626",
        }
        color = severity_colors.get(payload["severity"], "#6b7280")

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">{payload['title']}</h2>
                <p style="margin: 4px 0 0; opacity: 0.9; font-size: 13px;">
                    {payload['severity'].upper()} &bull; {payload['timestamp'][:19]}
                </p>
            </div>
            <div style="background: #f9fafb; padding: 24px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
                <p style="margin: 0 0 12px; color: #374151;">{payload['details']}</p>
                {'<p style="margin: 0; color: #6b7280; font-size: 13px;">Tenant: ' + payload['tenant'] + '</p>' if payload.get('tenant') else ''}
                {'<p style="margin: 0; color: #6b7280; font-size: 13px;">Workload: ' + payload['workload'] + '</p>' if payload.get('workload') else ''}
            </div>
            <p style="color: #9ca3af; font-size: 11px; margin-top: 12px;">
                Sent by KavachIQ &bull; <a href="#" style="color: #9ca3af;">Manage alerts</a>
            </p>
        </div>
        """

    async def send_test_alert(self):
        """Send a test alert to verify configuration."""
        await self.notify(
            event_type="test",
            title="Test Alert — KavachIQ",
            details="This is a test alert to verify your notification configuration is working correctly.",
            severity="info",
        )
        return {"status": "sent", "channels": {
            "email": bool(settings.SMTP_HOST and settings.ALERT_EMAIL_RECIPIENTS),
            "webhook": bool(settings.ALERT_WEBHOOK_URL),
        }}


# Singleton
alert_service = AlertService()
