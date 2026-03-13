"""
SQLAlchemy 2.0 async database engine.
Uses aiosqlite (SQLite) by default; swap DATABASE_URL in .env for asyncpg (PostgreSQL).
"""
import sys
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base ──────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Startup helper ────────────────────────────────────────────────────────────
async def create_tables() -> None:
    """Create all tables. Called once at startup."""
    async with engine.begin() as conn:
        # Import models so their metadata is registered
        import core.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
