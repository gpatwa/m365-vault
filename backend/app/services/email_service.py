"""Transactional email service — sends branded emails for auth, billing, and alerts.

Uses the EmailProvider abstraction for provider-agnostic delivery.
Templates are inline HTML (no external template files needed).
"""
import logging
from app.services.email_provider import get_email_provider

logger = logging.getLogger(__name__)


def _base_template(title: str, content: str) -> str:
    """Shieldio-branded HTML email template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#171717;border-radius:12px;border:1px solid rgba(255,255,255,0.1);">
  <!-- Header -->
  <tr><td style="padding:24px 32px 16px;border-bottom:1px solid rgba(255,255,255,0.1);">
    <span style="color:#14b8a6;font-size:20px;font-weight:700;">&#9737; Shieldio</span>
  </td></tr>
  <!-- Title -->
  <tr><td style="padding:24px 32px 8px;">
    <h1 style="margin:0;color:#fafafa;font-size:22px;font-weight:700;">{title}</h1>
  </td></tr>
  <!-- Content -->
  <tr><td style="padding:8px 32px 24px;color:#b5b5b5;font-size:14px;line-height:1.6;">
    {content}
  </td></tr>
  <!-- Footer -->
  <tr><td style="padding:16px 32px;border-top:1px solid rgba(255,255,255,0.1);color:#737373;font-size:11px;">
    Shieldio — SaaS Data Protection | <a href="https://shieldio.io" style="color:#14b8a6;text-decoration:none;">shieldio.io</a>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _button(text: str, url: str) -> str:
    """Teal CTA button."""
    return f'<a href="{url}" style="display:inline-block;padding:12px 24px;background:#14b8a6;color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;margin:16px 0;">{text}</a>'


class EmailService:
    """High-level transactional email methods."""

    def __init__(self):
        self.provider = get_email_provider()

    async def send_welcome(self, email: str, full_name: str):
        """Welcome email after registration."""
        name = full_name or email.split("@")[0]
        content = f"""
        <p>Hi {name},</p>
        <p>Welcome to Shieldio! Your account is ready.</p>
        <p>Here's what you can do next:</p>
        <ul style="color:#b5b5b5;">
          <li>Connect your Microsoft 365 tenant</li>
          <li>Discover your Exchange mailboxes and Entra ID directory</li>
          <li>See your criticality-scored recovery plan</li>
        </ul>
        {_button("Go to Dashboard", _frontend_url("/"))}
        <p style="color:#737373;font-size:12px;margin-top:16px;">Free for up to 25 objects. No credit card required.</p>
        """
        await self.provider.send(to=email, subject="Welcome to Shieldio", html=_base_template("Welcome to Shieldio", content))

    async def send_email_verification(self, email: str, token: str):
        """Email verification link."""
        url = f"{_frontend_url('/verify-email')}?token={token}"
        content = f"""
        <p>Please verify your email address to complete your registration.</p>
        {_button("Verify Email", url)}
        <p style="color:#737373;font-size:12px;">If you didn't create a Shieldio account, you can ignore this email.</p>
        """
        await self.provider.send(to=email, subject="Verify your email — Shieldio", html=_base_template("Verify Your Email", content))

    async def send_password_reset(self, email: str, token: str):
        """Password reset link (expires in 1 hour)."""
        url = f"{_frontend_url('/reset-password')}?token={token}"
        content = f"""
        <p>We received a request to reset your password.</p>
        {_button("Reset Password", url)}
        <p style="color:#737373;font-size:12px;">This link expires in 1 hour. If you didn't request a reset, ignore this email.</p>
        """
        await self.provider.send(to=email, subject="Reset your password — Shieldio", html=_base_template("Reset Your Password", content))

    async def send_trial_reminder(self, email: str, full_name: str, days_remaining: int):
        """Trial ending reminder."""
        name = full_name or "there"
        content = f"""
        <p>Hi {name},</p>
        <p>Your Shieldio trial ends in <strong>{days_remaining} day{'s' if days_remaining != 1 else ''}</strong>.</p>
        <p>To keep protecting your M365 data, upgrade to a paid plan:</p>
        <ul style="color:#b5b5b5;">
          <li><strong>Professional</strong> — $1.50/user/month (unlimited objects)</li>
          <li><strong>Business</strong> — $3.00/user/month (PST export, group restore)</li>
          <li><strong>Enterprise</strong> — $5.00/user/month (PIM backup, Agent Shield)</li>
        </ul>
        {_button("Upgrade Now", _frontend_url("/billing"))}
        <p style="color:#737373;font-size:12px;">If you don't upgrade, your account will revert to the free Community plan (25 objects).</p>
        """
        await self.provider.send(to=email, subject=f"Your Shieldio trial ends in {days_remaining} days", html=_base_template("Trial Ending Soon", content))

    async def send_payment_failed(self, email: str, full_name: str):
        """Payment declined notification."""
        name = full_name or "there"
        content = f"""
        <p>Hi {name},</p>
        <p>We couldn't process your payment for Shieldio. Please update your payment method to continue protecting your data.</p>
        {_button("Update Payment Method", _frontend_url("/billing"))}
        <p style="color:#737373;font-size:12px;">If your payment isn't updated within 7 days, your account will revert to the free Community plan.</p>
        """
        await self.provider.send(to=email, subject="Payment failed — Shieldio", html=_base_template("Payment Failed", content))

    async def send_backup_failure(self, email: str, tenant_name: str, workload: str, error: str):
        """Backup failure alert."""
        content = f"""
        <p>A backup job failed for <strong>{tenant_name}</strong>:</p>
        <table style="width:100%;border-collapse:collapse;margin:12px 0;">
          <tr><td style="padding:8px;color:#737373;border-bottom:1px solid rgba(255,255,255,0.1);">Workload</td><td style="padding:8px;color:#fafafa;border-bottom:1px solid rgba(255,255,255,0.1);">{workload}</td></tr>
          <tr><td style="padding:8px;color:#737373;">Error</td><td style="padding:8px;color:#f87171;">{error}</td></tr>
        </table>
        {_button("View Failed Items", _frontend_url("/failed-items"))}
        """
        await self.provider.send(to=email, subject=f"Backup failed — {tenant_name} ({workload})", html=_base_template("Backup Failed", content))


def _frontend_url(path: str) -> str:
    """Get frontend URL for email links."""
    from app.config import settings
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}{path}"


# Singleton
email_service = EmailService()
