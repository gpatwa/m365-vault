"""Restore Approval model — tracks approval workflow for critical restores.

Critical restores (mass recovery, cross-user, cross-tenant, Entra ID config)
require a second admin/restore_operator to approve before execution.
Requester != approver is enforced.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, Index
from app.database import Base


class RestoreApproval(Base):
    __tablename__ = "restore_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restore_job_id = Column(Integer, ForeignKey("restore_jobs.id"), nullable=False, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, approved, rejected, expired
    reason = Column(Text, nullable=True)  # Approval/rejection reason
    requested_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)  # Auto-expire after 24h
