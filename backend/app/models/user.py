"""User model for authentication and RBAC."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MSP_ADMIN = "msp_admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for SSO-only users
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Integer, default=1)
    sso_provider = Column(String(50), nullable=True)   # "entra_id", "google", etc.
    sso_subject_id = Column(String(255), nullable=True, index=True)  # IdP unique ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
