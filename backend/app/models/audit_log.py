"""Audit Log model — tracks all significant operations."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # backup.start, restore.complete, etc.
    resource_type = Column(String(100), nullable=True)  # tenant, sla_policy, protected_object, etc.
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)  # JSON with action details
    ip_address = Column(String(45), nullable=True)
    severity = Column(String(20), default="info")  # info, warning, error, critical
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
