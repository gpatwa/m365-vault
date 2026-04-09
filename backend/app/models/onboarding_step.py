"""Onboarding step model — immutable server-side step completion records."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from app.database import Base


ONBOARDING_STEPS = [
    "create_account",
    "connect_platform",
    "discover_workloads",
    "assign_protection",
    "first_backup",
    "explore_recovery",
]


class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    step = Column(String(50), nullable=False)
    completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "step", name="uq_user_step"),
    )
