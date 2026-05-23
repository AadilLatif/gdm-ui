"""Database engines and sessions for fgc_flow_api.

Two databases:
1. Flow DB (fgc_flow.db) — Uploaded model metadata for simulations
2. Local jobs DB (fgc_flow_jobs.db) — Job queue, models owned by this package
"""

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from fgc_flow_api.config import settings


def _sqlite_path(url: str) -> Path:
    return Path(url.replace("sqlite+aiosqlite:///", ""))


def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class FlowBase(DeclarativeBase):
    """Base class for uploaded model metadata."""


class JobsBase(DeclarativeBase):
    """Base class for all job queue models in the jobs database."""


_flow_db_path = _sqlite_path(settings.database_url)
_flow_db_path.parent.mkdir(parents=True, exist_ok=True)
flow_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)
event.listens_for(flow_engine.sync_engine, "connect")(_set_sqlite_pragmas)
FlowAsyncSession = async_sessionmaker(flow_engine, class_=AsyncSession, expire_on_commit=False)


_jobs_db_path = _sqlite_path(settings.jobs_database_url)
_jobs_db_path.parent.mkdir(parents=True, exist_ok=True)
jobs_engine = create_async_engine(
    settings.jobs_database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)
event.listens_for(jobs_engine.sync_engine, "connect")(_set_sqlite_pragmas)
JobsAsyncSession = async_sessionmaker(jobs_engine, class_=AsyncSession, expire_on_commit=False)


async def get_flow_db() -> AsyncSession:
    """Dependency that yields a session to the flow metadata database."""

    async with FlowAsyncSession() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_jobs_db() -> AsyncSession:
    """Dependency that yields a session to the jobs database."""

    async with JobsAsyncSession() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_flow_db():
    """Create all tables in the flow database."""

    async with flow_engine.begin() as conn:
        await conn.run_sync(FlowBase.metadata.create_all)


async def init_jobs_db():
    """Create all tables in the jobs database."""

    async with jobs_engine.begin() as conn:
        await conn.run_sync(JobsBase.metadata.create_all)
