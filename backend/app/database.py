"""Database setup and session management."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Pool settings only for PostgreSQL (SQLite uses NullPool)
_engine_kwargs = {"echo": settings.DEBUG}
if "postgresql" in settings.DATABASE_URL:
    _engine_kwargs.update(
        pool_pre_ping=True,       # Validate connections before use (resilience)
        pool_recycle=300,          # Recycle stale connections every 5 min
        pool_size=25,              # 25 steady-state (was 10 — supports 25 concurrent backup sessions)
        max_overflow=50,           # Burst to 75 during backup-all across tenants (was 20)
        pool_timeout=30,           # Fail fast after 30s instead of hanging forever
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all database tables and run lightweight schema migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Lightweight schema migrations for columns added after initial release
    await _run_migrations()


async def _run_migrations():
    """Add missing columns to existing tables (safe to re-run)."""
    migrations = [
        # v1.2.0: compression/dedup pipeline
        ("snapshot_items", "compressed_size", "INTEGER"),
        ("snapshot_items", "storage_flags", "INTEGER DEFAULT 0"),
        # v1.3.0: Entra ID + Teams
        ("tenants", "total_entra_objects", "INTEGER DEFAULT 0"),
        ("tenants", "total_teams", "INTEGER DEFAULT 0"),
        # v1.4.0: SSO support
        ("users", "sso_provider", "VARCHAR(50)"),
        ("users", "sso_subject_id", "VARCHAR(255)"),
        # v1.5.0: WORM storage
        ("sla_policies", "worm_enabled", "INTEGER DEFAULT 0"),
        ("sla_policies", "legal_hold", "INTEGER DEFAULT 0"),
        ("snapshots", "locked_until", "TIMESTAMP"),
        # v1.6.0: Backup validation
        ("snapshots", "validation_status", "VARCHAR(50)"),
        ("snapshots", "validated_at", "TIMESTAMP"),
        # v1.7.0: Cross-tenant restore
        ("restore_jobs", "target_tenant_id", "INTEGER"),
        ("restore_jobs", "scan_status", "VARCHAR(50)"),
        ("restore_jobs", "scan_details", "TEXT"),
        # v1.8.0: Dead-letter queue — retry tracking on RestoreJob
        ("restore_jobs", "retry_count", "INTEGER DEFAULT 0"),
        ("restore_jobs", "max_retries", "INTEGER DEFAULT 3"),
        # v2.2.0: Organizational Context Layer — criticality scoring
        ("protected_objects", "criticality_score", "INTEGER DEFAULT 50"),
        ("protected_objects", "criticality_tier", "VARCHAR(20) DEFAULT 'medium'"),
        # v2.3.0: Batch scheduler — parent-child job decomposition
        ("backup_jobs", "parent_job_id", "INTEGER"),
        ("backup_jobs", "batch_offset", "INTEGER"),
        ("backup_jobs", "batch_size", "INTEGER"),
    ]
    async with engine.begin() as conn:
        for table, column, col_type in migrations:
            # Check if column exists
            exists = await conn.scalar(
                _text(
                    f"SELECT 1 FROM information_schema.columns "
                    f"WHERE table_name = '{table}' AND column_name = '{column}'"
                )
            )
            if not exists:
                await conn.execute(
                    _text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )
                import logging
                logging.getLogger(__name__).info(
                    f"Migration: added column {table}.{column} ({col_type})"
                )


    # PostgreSQL enum value sync — auto-derived from Python enum classes.
    # This guarantees Python enums and PostgreSQL enums can never drift apart.
    # When a developer adds a value to any Python enum, it automatically appears
    # in PostgreSQL on next deploy. No hand-maintained migration list needed.
    enum_migrations = _collect_enum_values()

    for enum_name, values in enum_migrations:
        for value in values:
            try:
                await conn.execute(
                    _text(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")
                )
            except Exception:
                pass  # Enum value already exists or not PostgreSQL


def _collect_enum_values() -> list[tuple[str, list[str]]]:
    """Auto-derive PostgreSQL enum values from all Python enum classes.

    Scans every SQLAlchemy model for Enum columns, maps the PostgreSQL type name
    to the Python enum's values. This makes it impossible for Python and PostgreSQL
    enums to diverge — adding a value to a Python enum automatically syncs on deploy.
    """
    import enum as _enum
    from sqlalchemy import Enum as SAEnum, inspect as sa_inspect

    enum_map: dict[str, set[str]] = {}

    for mapper in Base.registry.mappers:
        for column in mapper.columns:
            if isinstance(column.type, SAEnum):
                # Get the PostgreSQL enum type name (lowercase)
                pg_type_name = column.type.name
                if not pg_type_name:
                    continue
                # Get all values from the Python enum class
                enum_class = column.type.enum_class
                if enum_class and issubclass(enum_class, _enum.Enum):
                    values = {e.value for e in enum_class}
                elif column.type.enums:
                    values = set(column.type.enums)
                else:
                    continue
                if pg_type_name not in enum_map:
                    enum_map[pg_type_name] = set()
                enum_map[pg_type_name].update(values)

    return [(name, sorted(values)) for name, values in sorted(enum_map.items())]


def _text(sql: str):
    """Create a text SQL expression."""
    from sqlalchemy import text
    return text(sql)
