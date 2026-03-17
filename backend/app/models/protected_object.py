"""Protected Object model — represents mailboxes, OneDrive accounts, SharePoint sites."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, ForeignKey
from app.database import Base


class WorkloadType(str, enum.Enum):
    EXCHANGE = "exchange"
    ONEDRIVE = "onedrive"
    SHAREPOINT = "sharepoint"


class ProtectionStatus(str, enum.Enum):
    PROTECTED = "protected"
    UNPROTECTED = "unprotected"
    PAUSED = "paused"
    ERROR = "error"


class ProtectedObject(Base):
    __tablename__ = "protected_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    workload_type = Column(Enum(WorkloadType), nullable=False, index=True)
    ms_object_id = Column(String(255), nullable=False, index=True)  # Graph API object ID
    display_name = Column(String(500), nullable=False)
    email = Column(String(255), nullable=True)  # For Exchange/OneDrive users
    user_principal_name = Column(String(255), nullable=True)
    site_url = Column(String(1000), nullable=True)  # For SharePoint
    sla_policy_id = Column(Integer, ForeignKey("sla_policies.id"), nullable=True)
    sla_assignment_type = Column(String(50), default="application")  # application, group, individual
    status = Column(Enum(ProtectionStatus), default=ProtectionStatus.UNPROTECTED, nullable=False)
    last_backup_at = Column(DateTime, nullable=True)
    last_backup_status = Column(String(50), nullable=True)
    total_items_backed_up = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)  # Extra metadata as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
