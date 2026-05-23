"""Database engines and sessions for fgc_flow_api.

Two databases:
1. Shared auth DB (from fgc_core) — User authentication, accessed via fgc_core.database
2. Local jobs DB (fgc_flow_jobs.db) — Job queue, models owned by this package
"""
from pathlib import Path

from fgc_flow_api.config import settings
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


# ── JobsBase ─────────────────────────────────────────────────────────────────
# Separate declarative base for the jobs database (different SQLite file).


class JobsBase(DeclarativeBase):
    """Base class for all job queue models in the jobs database."""
    pass


# ── Jobs DB Engine ────────────────────────────────────────────────────────────
_jobs_db_path = Path(settings.jobs_database_url.replace("sqlite+aiosqlite:///", ""))
_jobs_db_path.parent.mkdir(parents=True, exist_ok=True)

jobs_engine = create_async_engine(
    settings.jobs_database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)


@event.listens_for(jobs_engine.sync_engine, "connect")
def _set_jobs_db_pragma(dbapi_connection, connection_record):
    """Apply WAL mode and busy timeout on every new connection to the jobs DB."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


JobsAsyncSession = async_sessionmaker(
    jobs_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_jobs_db() -> AsyncSession:
    """Dependency that yields a session to the jobs database."""
    async with JobsAsyncSession() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_jobs_db():
    """Create all tables in the jobs database."""
    async with jobs_engine.begin() as conn:
        await conn.run_sync(JobsBase.metadata.create_all)
