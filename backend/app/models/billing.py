"""Billing model — per-tenant monthly usage records for MSP invoicing.

Records are generated on-demand from live usage data when the MSP
views the billing portal or triggers a billing snapshot.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from app.database import Base


class BillingRecord(Base):
    __tablename__ = "billing_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "month", name="uq_billing_tenant_month"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # "2026-03" format
    tenant_name = Column(String(255), nullable=True)
    user_count = Column(Integer, default=0)
    storage_gb = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)       # per-user price applied
    storage_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    status = Column(String(20), default="draft")  # draft, invoiced, paid
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
