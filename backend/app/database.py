"""Database setup and session management."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
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


def _text(sql: str):
    """Create a text SQL expression."""
    from sqlalchemy import text
    return text(sql)
