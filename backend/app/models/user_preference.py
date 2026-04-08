"""User Preferences — server-side storage for all user settings.

Replaces ALL localStorage/sessionStorage usage. Enterprise SaaS pattern:
server owns all state, browser stores only the JWT token.

Preferences follow the user across devices, browsers, and sessions.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class UserPreference(Base):
    """Key-value store for user preferences."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_preference"),
    )

    def __repr__(self):
        return f"<UserPreference user={self.user_id} key={self.key}>"


# Standard preference keys (documented, not enforced)
PREF_KEYS = {
    "selected_tenant": "Active tenant ID in the tenant switcher",
    "theme": "UI theme: 'dark' or 'light'",
    "tour_completed": "Product tour dismissed: 'true'",
    "checklist_dismissed": "Dashboard onboarding checklist hidden: 'true'",
    "recent_commands": "JSON array of recent command palette entries",
}
