"""Agent Shield models — tracks AI agent activity and profiles."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base


class AgentProfile(Base):
    """Tracks known AI agents interacting with tenant M365 data."""
    __tablename__ = "agent_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(String(255), nullable=False)  # MS app/service principal ID
    agent_name = Column(String(255), nullable=False)
    agent_type = Column(String(50), nullable=False)  # copilot, custom, openclaw, unknown
    app_registration_id = Column(String(255))
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    total_actions = Column(Integer, default=0)
    is_managed = Column(Integer, default=0)  # 1 = IT-approved, 0 = unknown
    is_shadow = Column(Integer, default=0)   # 1 = detected as unmanaged
    permissions = Column(Text)  # JSON: list of Graph API scopes
    risk_score = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentActivity(Base):
    """Individual agent actions detected from Graph API audit logs."""
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    agent_profile_id = Column(Integer, index=True)
    agent_name = Column(String(255), nullable=False)
    agent_type = Column(String(50))
    action = Column(String(50), nullable=False)  # read, modify, delete, permission_change
    resource_type = Column(String(50), nullable=False)  # email, file, identity, config, oauth
    resource_name = Column(String(500))
    resource_count = Column(Integer, default=1)
    affected_users_count = Column(Integer, default=0)
    risk_level = Column(String(20), default="low")  # low, medium, high, critical
    graph_audit_id = Column(String(255))  # correlation to MS audit log
    raw_data = Column(Text)  # JSON
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
