"""Microsoft 365 Tenant model."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from app.database import Base


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    ONBOARDING = "onboarding"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    ms_tenant_id = Column(String(255), unique=True, nullable=False, index=True)
    client_id = Column(String(255), nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)  # AES-256 encrypted
    status = Column(Enum(TenantStatus), default=TenantStatus.ONBOARDING, nullable=False)
    last_discovery_at = Column(DateTime, nullable=True)
    total_mailboxes = Column(Integer, default=0)
    total_onedrives = Column(Integer, default=0)
    total_sites = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
