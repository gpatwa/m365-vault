"""Health baseline model — tracks running averages for anomaly detection."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from app.database import Base


class HealthBaseline(Base):
    __tablename__ = "health_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    workload_type = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)  # item_count, size_bytes, error_rate, duration_sec
    avg_value = Column(Float, default=0.0)
    std_dev = Column(Float, default=0.0)
    min_value = Column(Float, default=0.0)
    max_value = Column(Float, default=0.0)
    sample_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    workload_type = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    expected_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    z_score = Column(Float, nullable=False)
    severity = Column(String(20), default="warning")  # warning, critical
    message = Column(String(1000), nullable=True)
    resolved = Column(Integer, default=0)  # 0=active, 1=resolved
    detected_at = Column(DateTime, default=datetime.utcnow)
