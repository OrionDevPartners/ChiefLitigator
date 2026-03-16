"""Async SQLAlchemy engine and session factory.

All database configuration is sourced from the DATABASE_URL environment
variable (CPAA-compliant). Supports PostgreSQL (asyncpg) in production
and SQLite (aiosqlite) in testing.

Usage::

    from src.database.engine import get_db

    @app.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("cyphergy.database.engine")

# ---------------------------------------------------------------------------
# CPAA: DATABASE_URL from environment only. No hardcoded connection strings.
# ---------------------------------------------------------------------------
# Expected formats:
#   PostgreSQL: postgresql+asyncpg://user:pass@host:5432/cyphergy
#   SQLite:     sqlite+aiosqlite:///path/to/db.sqlite3
# ---------------------------------------------------------------------------

_DATABASE_URL = os.getenv("DATABASE_URL", "")

if not _DATABASE_URL:
    logger.warning(
        "database_url_not_set | DATABASE_URL environment variable is empty. "
        "Database operations will fail until it is configured."
    )


def _build_engine_kwargs() -> dict:
    """Build engine keyword arguments based on the database backend.

    PostgreSQL gets connection pooling; SQLite does not support it.
    """
    kwargs: dict = {
        "echo": os.getenv("DB_ECHO", "false").lower() == "true",
    }

    if _DATABASE_URL.startswith("sqlite"):
        # SQLite does not support pool_size or connect_args the same way.
        # StaticPool is used for testing (set externally when overriding).
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL connection pool tuning
        kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
        kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        kwargs["pool_timeout"] = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        kwargs["pool_recycle"] = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        kwargs["pool_pre_ping"] = True

    return kwargs


# ---------------------------------------------------------------------------
# Engine + Session factory
# ---------------------------------------------------------------------------

def _get_engine():
    """Lazy engine creation — only build when DATABASE_URL is set."""
    url = _DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure it in .env or environment. "
            "Expected: postgresql+asyncpg://user:pass@host:5432/cyphergy"
        )
    return create_async_engine(url, **_build_engine_kwargs())


# Lazy — created on first access via get_db()
engine = None

async_session_factory = None


def _get_session_factory():
    """Lazy session factory creation."""
    global engine, async_session_factory
    if async_session_factory is None:
        engine = _get_engine()
        async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_session_factory


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Declarative base for all Cyphergy ORM models."""

    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async database session.

    Usage as a FastAPI dependency::

        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    The session is automatically closed when the request completes,
    and any uncommitted changes are rolled back on error.
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
