"""Organizational Context models — user/site criticality, VIP groups."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from app.database import Base


class UserContext(Base):
    """Per-user organizational context synced from Microsoft Graph."""
    __tablename__ = "user_contexts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ms_user_id", name="uq_user_context_tenant_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    protected_object_id = Column(Integer, ForeignKey("protected_objects.id"), nullable=True, index=True)
    ms_user_id = Column(String(255), nullable=False, index=True)

    # Hierarchy
    display_name = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    office_location = Column(String(255), nullable=True)
    manager_ms_id = Column(String(255), nullable=True)
    manager_chain = Column(Text, nullable=True)  # JSON array of manager IDs up to CEO
    direct_reports_count = Column(Integer, default=0)

    # VIP / Privileged
    is_vip = Column(Integer, default=0)
    has_privileged_role = Column(Integer, default=0)
    privileged_roles = Column(Text, nullable=True)  # JSON array of role names
    is_global_admin = Column(Integer, default=0)

    # Security context
    risk_level = Column(String(50), nullable=True)  # none/low/medium/high from Identity Protection
    last_sign_in_at = Column(DateTime, nullable=True)

    # Data sensitivity
    highest_sensitivity_label = Column(String(255), nullable=True)
    has_legal_hold = Column(Integer, default=0)
    external_sharing_active = Column(Integer, default=0)

    # OCSF-ready: future SIEM threat signal integration
    threat_exposure_score = Column(Integer, default=0)

    # Criticality (Silver layer — computed)
    criticality_score = Column(Integer, default=50)  # 0-100
    criticality_tier = Column(String(20), default="medium")  # critical/high/medium/low

    # Medallion layers
    signals = Column(Text, nullable=True)  # Silver: which signals contributed to score (JSON)
    raw_graph_data = Column(Text, nullable=True)  # Bronze: raw Graph API response (JSON)

    # Timestamps
    synced_at = Column(DateTime, nullable=True)
    computed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SiteContext(Base):
    """Per-site organizational context for SharePoint/Teams."""
    __tablename__ = "site_contexts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ms_site_id", name="uq_site_context_tenant_site"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    protected_object_id = Column(Integer, ForeignKey("protected_objects.id"), nullable=True, index=True)
    ms_site_id = Column(String(255), nullable=False, index=True)

    # Site metadata
    site_url = Column(String(1000), nullable=True)
    site_name = Column(String(500), nullable=True)
    site_type = Column(String(50), nullable=True)  # team_site, communication_site, hub_site

    # Activity (from usage reports)
    page_view_count = Column(Integer, default=0)
    unique_visitors = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    active_file_count = Column(Integer, default=0)
    storage_used_bytes = Column(Integer, default=0)
    last_activity_at = Column(DateTime, nullable=True)

    # Sensitivity
    sensitivity_label = Column(String(255), nullable=True)
    external_sharing_enabled = Column(Integer, default=0)

    # OCSF-ready
    threat_exposure_score = Column(Integer, default=0)

    # Criticality (Silver layer)
    criticality_score = Column(Integer, default=50)
    criticality_tier = Column(String(20), default="medium")

    # Medallion layers
    signals = Column(Text, nullable=True)
    raw_graph_data = Column(Text, nullable=True)

    # Timestamps
    synced_at = Column(DateTime, nullable=True)
    computed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VIPGroup(Base):
    """Admin-defined critical user groups."""
    __tablename__ = "vip_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    criticality_boost = Column(Integer, default=20)  # Points added to members' scores
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VIPGroupMember(Base):
    """Members of VIP groups."""
    __tablename__ = "vip_group_members"
    __table_args__ = (
        UniqueConstraint("vip_group_id", "protected_object_id", name="uq_vip_member"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    vip_group_id = Column(Integer, ForeignKey("vip_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    protected_object_id = Column(Integer, ForeignKey("protected_objects.id"), nullable=False)
    ms_user_id = Column(String(255), nullable=True)  # Cross-reference even if protected_object removed
    created_at = Column(DateTime, default=datetime.utcnow)


class RecoveryPlan(Base):
    """Pre-computed recovery plan — phased, criticality-ordered, ready to execute."""
    __tablename__ = "recovery_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    plan_type = Column(String(50), nullable=False)  # mvb, ransomware, full
    status = Column(String(50), default="ready")  # ready, executing, completed, stale

    # MVB set
    mvb_user_count = Column(Integer, default=0)  # Users in Minimum Viable Business set
    mvb_object_count = Column(Integer, default=0)  # Protected objects in MVB
    total_object_count = Column(Integer, default=0)  # All objects in plan

    # Plan content (Gold layer — pre-computed, ready to execute)
    phases_json = Column(Text, nullable=False)  # JSON array of recovery phases
    # Example:
    # [
    #   {"phase": 1, "name": "Identity Controls", "priority": "immediate", "objects": [...], "estimated_minutes": 5},
    #   {"phase": 2, "name": "Executive & Legal (MVB)", "priority": "critical", "objects": [...], "estimated_minutes": 15},
    #   {"phase": 3, "name": "Finance Department", "priority": "high", "objects": [...], "estimated_minutes": 30},
    #   {"phase": 4, "name": "Full Recovery", "priority": "normal", "objects": [...], "estimated_minutes": 120}
    # ]

    # Summary stats
    total_items = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    estimated_minutes = Column(Integer, default=0)

    # Agent reasoning (for future Claude integration)
    reasoning = Column(Text, nullable=True)  # Why this plan was generated this way

    # Timestamps
    computed_at = Column(DateTime, nullable=False)
    stale_after = Column(DateTime, nullable=True)  # Plan should be refreshed after this time
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
