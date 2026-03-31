"""MSP Branding model — white-label configuration for managed service providers.

Singleton table: one row per Shieldio deployment. Stores the MSP's custom
company name, logo, and brand colors that replace Shieldio defaults throughout the UI.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from app.database import Base


class MSPBranding(Base):
    __tablename__ = "msp_branding"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False, default="Shieldio")
    tagline = Column(String(255), nullable=True, default="SaaS Data Protection")
    logo_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=False, default="#3b82f6")   # blue-500
    secondary_color = Column(String(7), nullable=False, default="#1e293b")  # slate-800
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
