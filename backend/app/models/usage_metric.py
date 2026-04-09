"""Per-tenant daily usage metrics for cost attribution."""
from datetime import date

from sqlalchemy import Column, Date, Integer, BigInteger, ForeignKey, UniqueConstraint
from app.database import Base


class TenantUsageMetric(Base):
    __tablename__ = "tenant_usage_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    metric_date = Column(Date, nullable=False, index=True)
    graph_api_calls = Column(Integer, default=0)
    graph_api_throttled = Column(Integer, default=0)
    backup_duration_seconds = Column(Integer, default=0)
    restore_duration_seconds = Column(Integer, default=0)
    storage_bytes_delta = Column(BigInteger, default=0)
    items_backed_up = Column(Integer, default=0)
    items_restored = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "metric_date", name="uq_tenant_metric_date"),
    )
