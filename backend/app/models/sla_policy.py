"""SLA Policy (Domain) model for backup scheduling and retention."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    backup_frequency_hours = Column(Integer, default=24, nullable=False)  # How often to backup
    retention_days = Column(Integer, default=30, nullable=False)  # How long to keep snapshots
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest
    is_locked = Column(Integer, default=0)  # Retention lock (1=locked)
    worm_enabled = Column(Integer, default=0)  # WORM: write-once-read-many (1=enabled)
    legal_hold = Column(Integer, default=0)    # Legal hold: prevents any deletion (1=enabled)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
