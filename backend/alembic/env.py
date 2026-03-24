"""Alembic env.py — configured for Shieldio SQLAlchemy models."""
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
