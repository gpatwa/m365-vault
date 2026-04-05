"""Admin Invite model — allows non-admin users to invite their Global Admin for OAuth consent."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from app.database import Base


class AdminInvite(Base):
    __tablename__ = "admin_invites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_name = Column(String(255), nullable=False)     # Proposed tenant name
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_email = Column(String(255), nullable=False)     # Email to send invite to
    token = Column(String(255), unique=True, nullable=False)  # Secure invite token
    status = Column(String(20), default="pending")        # pending, completed, expired
    ms_tenant_id = Column(String(255), nullable=True)     # Filled after admin completes OAuth
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
