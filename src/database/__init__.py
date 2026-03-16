"""Database package — async SQLAlchemy engine, session factory, and base model."""

from __future__ import annotations

import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/cyphergy",
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session and ensure it is closed after use."""
    async with async_session_factory() as session:
        yield session
