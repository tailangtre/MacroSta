"""
MacroScope — Async database engine (SQLite via aiosqlite, swappable to Postgres).
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# Columns added after the initial schema. SQLAlchemy's create_all only
# creates missing tables, not missing columns, so we patch them in by hand
# for SQLite dev databases. For Postgres, switch to Alembic.
_NEW_COLUMNS = {
    "events": [
        ("provider", "VARCHAR(64)"),
    ],
}


async def _ensure_columns(conn) -> None:
    """Add any columns in _NEW_COLUMNS that the live DB is missing."""
    if "sqlite" not in settings.DATABASE_URL:
        return  # let Alembic handle Postgres
    for table, cols in _NEW_COLUMNS.items():
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        existing = {row[1] for row in result.fetchall()}
        for name, ddl in cols:
            if name not in existing:
                logger.info("Adding column %s.%s", table, name)
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


async def init_db():
    """Create all tables on startup, then patch in any new columns."""
    from app.models import event  # noqa: F401 — ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_columns(conn)