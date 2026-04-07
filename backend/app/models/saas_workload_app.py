"""SaaS Workload App — Platform-owned per-workload Entra app registrations.

These are the 5 multi-tenant apps that KavachIQ registers in its OWN Entra
tenant. Each workload (entra_id, exchange, sharepoint, onedrive, teams) has
its own app with only the permissions that workload needs.

Customers consent to these apps during onboarding — they don't create their own.

This table is auto-populated on first startup by workload_bootstrap.py.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from app.database import Base


class SaaSWorkloadApp(Base):
    """KavachIQ's own per-workload Entra app registrations."""
    __tablename__ = "saas_workload_apps"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Workload key: entra_id, exchange, sharepoint, onedrive, teams
    workload = Column(String(30), nullable=False, unique=True)

    # Entra app registration details
    display_name = Column(String(255), nullable=False)
    app_id = Column(String(255), nullable=False)       # Application (client) ID
    app_object_id = Column(String(255))                 # Object ID in Entra
    client_secret_encrypted = Column(Text, nullable=False)  # AES-256 encrypted

    # Permissions configured on this app
    permissions_configured = Column(Text)  # JSON list of permission names
    sign_in_audience = Column(String(50), default="AzureADMultipleOrgs")

    # Redirect URIs registered
    redirect_uris = Column(Text)  # JSON list

    # Secret lifecycle
    secret_expires_at = Column(DateTime)
    secret_key_id = Column(String(255))  # Entra key ID for rotation

    # Status tracking
    status = Column(String(20), default="active")  # active, secret_expiring, error
    error_message = Column(Text)
    last_validated_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workload", name="uq_saas_workload"),
    )

    def __repr__(self):
        return f"<SaaSWorkloadApp {self.workload} app_id={self.app_id[:8]}...>"
