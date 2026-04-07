"""User-Tenant membership model — scopes users to their assigned tenants.

Each user can belong to one or more tenants. API endpoints enforce this
membership to prevent cross-tenant data access.

Standard SaaS pattern: Users are global identities. Memberships connect
users to tenants (organizations). Everything else is tenant-owned.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class UserTenant(Base):
    """Maps users to the tenants they can access."""
    __tablename__ = "user_tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role within this tenant: owner (connected it), admin, member, viewer
    role = Column(String(20), default="member")

    # If user has multiple tenants, which is their default?
    is_default = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
    )

    def __repr__(self):
        return f"<UserTenant user={self.user_id} tenant={self.tenant_id} role={self.role}>"
