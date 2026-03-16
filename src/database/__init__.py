"""Cyphergy database layer.

Provides async SQLAlchemy engine, session factory, and ORM models
for PostgreSQL (production) and SQLite (testing). All connection
configuration is sourced from the DATABASE_URL environment variable
(CPAA-compliant).

Exports:
    engine: The async SQLAlchemy engine singleton.
    async_session_factory: Session factory for request-scoped sessions.
    Base: Declarative base for ORM models.
    get_db: FastAPI dependency yielding a database session.
"""

from src.database.engine import Base, async_session_factory, engine, get_db

__all__ = [
    "Base",
    "async_session_factory",
    "engine",
    "get_db",
]
