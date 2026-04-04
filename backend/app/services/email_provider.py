"""Email provider abstraction — switch between Resend, SMTP, or console.

Architecture:
  EmailProvider (abstract base)
    ├── ResendProvider — production (Resend API)
    ├── SMTPProvider — self-hosted (existing SMTP)
    └── ConsoleProvider — dev/test (logs to stdout)

Usage:
  from app.services.email_provider import get_email_provider
  provider = get_email_provider()
  await provider.send(to="user@example.com", subject="Hello", html="<h1>Hi</h1>")
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract email provider — all providers implement send()."""

    @abstractmethod
    async def send(self, to: str, subject: str, html: str, from_email: str = None) -> bool:
        """Send an email. Returns True on success, False on failure."""
        ...


class ConsoleProvider(EmailProvider):
    """Dev/test provider — prints emails to stdout instead of sending."""

    async def send(self, to: str, subject: str, html: str, from_email: str = None) -> bool:
        logger.info(f"\n{'='*60}\n[EMAIL] To: {to}\n[EMAIL] Subject: {subject}\n[EMAIL] From: {from_email or 'default'}\n[EMAIL] Body: {html[:200]}...\n{'='*60}")
        return True


class ResendProvider(EmailProvider):
    """Production provider — uses Resend API (resend.com)."""

    def __init__(self, api_key: str):
        import resend
        resend.api_key = api_key
        self._resend = resend

    async def send(self, to: str, subject: str, html: str, from_email: str = None) -> bool:
        try:
            from app.config import settings
            self._resend.Emails.send({
                "from": from_email or settings.EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": html,
            })
            logger.info(f"Email sent via Resend to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Resend email failed to {to}: {e}")
            return False


class SMTPProvider(EmailProvider):
    """Self-hosted provider — uses SMTP (existing infrastructure)."""

    async def send(self, to: str, subject: str, html: str, from_email: str = None) -> bool:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from app.config import settings

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or settings.SMTP_FROM or settings.EMAIL_FROM
            msg["To"] = to
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent via SMTP to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"SMTP email failed to {to}: {e}")
            return False


def get_email_provider() -> EmailProvider:
    """Factory — returns the configured email provider."""
    from app.config import settings

    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend":
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set, falling back to console provider")
            return ConsoleProvider()
        return ResendProvider(settings.RESEND_API_KEY)
    elif provider == "smtp":
        if not settings.SMTP_HOST:
            logger.warning("SMTP_HOST not set, falling back to console provider")
            return ConsoleProvider()
        return SMTPProvider()
    else:
        return ConsoleProvider()
