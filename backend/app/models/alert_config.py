"""Per-Tenant Alert Configuration — customers configure their own alert preferences.

Each tenant can set:
- Which events trigger alerts (backup_failed, anomaly_detected, etc.)
- Email recipients for alerts
- Webhook URL for integration
- Alert frequency (immediate, hourly digest, daily digest)
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class TenantAlertConfig(Base):
    """Per-tenant alert preferences. One row per tenant."""
    __tablename__ = "tenant_alert_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Alert recipients (comma-separated emails)
    email_recipients = Column(Text, default="")

    # Webhook (Slack, Teams, PagerDuty)
    webhook_url = Column(String(500), default="")

    # Alert triggers (JSON array of event types)
    # Events: backup_failed, backup_completed, anomaly_detected, protection_gap,
    #         secret_expiring, worm_violation, restore_completed, restore_failed
    enabled_events = Column(Text, default='["backup_failed","anomaly_detected","protection_gap"]')

    # Frequency: immediate, hourly, daily
    frequency = Column(String(20), default="immediate")

    # Quiet hours (don't send during these hours, UTC)
    quiet_start_hour = Column(Integer, default=None)  # e.g., 22 (10pm UTC)
    quiet_end_hour = Column(Integer, default=None)    # e.g., 6 (6am UTC)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TenantAlertConfig tenant={self.tenant_id}>"
