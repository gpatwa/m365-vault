"""Alembic env.py — configured for KavachIQ SQLAlchemy models."""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base

# Import ALL models so Alembic sees them for autogenerate
from app.models.user import User  # noqa
from app.models.tenant import Tenant  # noqa
from app.models.protected_object import ProtectedObject  # noqa
from app.models.sla_policy import SLAPolicy  # noqa
from app.models.backup_job import BackupJob  # noqa
from app.models.restore_job import RestoreJob  # noqa
from app.models.snapshot import Snapshot, SnapshotItem, FailedItem  # noqa
from app.models.audit_log import AuditLog  # noqa
from app.models.dedup import DedupEntry  # noqa
from app.models.health_baseline import HealthBaseline, AnomalyEvent  # noqa
from app.models.worker_queue import WorkerQueueEntry  # noqa
from app.models.user_tenant import UserTenant  # noqa
from app.models.user_preference import UserPreference  # noqa
from app.models.onboarding_step import OnboardingStep  # noqa
from app.models.billing import BillingRecord  # noqa
from app.models.msp_branding import MSPBranding  # noqa
from app.models.saas_workload_app import SaaSWorkloadApp  # noqa
from app.models.usage_metric import TenantUsageMetric  # noqa
try:
    from app.models.tenant_workload_app import TenantWorkloadApp  # noqa
    from app.models.restore_approval import RestoreApproval  # noqa
    from app.models.admin_invite import AdminInvite  # noqa
    from app.models.agent_activity import AgentActivity  # noqa
    from app.models.mvb_plan import MVBRecoveryPlan  # noqa
except ImportError:
    pass  # Optional models — may not exist in all branches

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    """Get sync database URL from environment."""
    url = os.environ.get("DATABASE_URL", "sqlite:///./m365vault.db")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("sqlite+aiosqlite://", "sqlite://")
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
