"""Per-Workload Entra App Registration model.

Each workload (Entra ID, Exchange, SharePoint, OneDrive, Teams) gets its own
Entra app registration with only the permissions that workload needs.
"""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, ForeignKey, UniqueConstraint
from app.database import Base


class ConsentStatus(str, enum.Enum):
    PENDING = "pending"       # App created, admin has not consented
    CONSENTED = "consented"   # Admin granted consent, permissions active
    PARTIAL = "partial"       # Some permissions granted (e.g., backup only)
    REVOKED = "revoked"       # Admin revoked consent
    ERROR = "error"           # Consent flow failed


class WorkloadLifecycle(str, enum.Enum):
    """Workload lifecycle state machine: disabled → enabled → discovered → protected → paused.

    Only enabled+ workloads get discovered.
    Only discovered+ workloads get protected.
    Only protected workloads get backed up and monitored.
    Disabled workloads are invisible on the dashboard.
    """
    DISABLED = "disabled"       # Default — not activated
    ENABLED = "enabled"         # Customer opted in, ready for discovery
    DISCOVERED = "discovered"   # Objects found, not yet protected
    PROTECTED = "protected"     # SLA assigned, backup running, monitored
    PAUSED = "paused"           # Temporarily stopped, data retained


class TenantWorkloadApp(Base):
    __tablename__ = "tenant_workload_apps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    workload = Column(String(30), nullable=False)  # entra_id, exchange, sharepoint, onedrive, teams

    # Entra App Registration
    client_id = Column(String(255), nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)  # AES-256 encrypted
    app_object_id = Column(String(255), nullable=True)      # For managing the app
    sp_object_id = Column(String(255), nullable=True)       # For checking grants

    # Consent Status
    consent_status = Column(String(20), default="pending", nullable=False)

    # Workload Lifecycle (opt-in per workload, gated by subscription)
    lifecycle_status = Column(String(20), default="disabled", nullable=False)

    # Permission Tracking
    permissions_requested = Column(Text, nullable=True)   # JSON array
    permissions_granted = Column(Text, nullable=True)     # JSON array
    backup_ready = Column(Integer, default=0)
    restore_ready = Column(Integer, default=0)

    # Workload-specific Configuration
    config_json = Column(Text, nullable=True)  # JSON

    # Secret Lifecycle
    secret_expires_at = Column(DateTime, nullable=True)
    secret_rotation_warned = Column(Integer, default=0)

    # Metadata
    enabled = Column(Integer, default=1)
    last_used_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "workload", name="uq_tenant_workload"),
    )
