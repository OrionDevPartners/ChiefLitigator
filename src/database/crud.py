"""CRUD operations for cases and messages."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Case, Message


async def create_case(
    session: AsyncSession,
    *,
    user_id: str,
    title: str,
    description: str = "",
    jurisdiction: Optional[str] = None,
) -> Case:
    """Create a new case and return it."""
    case = Case(
        user_id=user_id,
        title=title,
        description=description,
        jurisdiction=jurisdiction,
    )
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


async def list_cases(
    session: AsyncSession,
    *,
    user_id: str,
) -> Sequence[Case]:
    """Return all cases belonging to *user_id*, newest first."""
    stmt = (
        select(Case)
        .where(Case.user_id == user_id)
        .order_by(Case.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_case(
    session: AsyncSession,
    *,
    case_id: str,
    user_id: str,
) -> Optional[Case]:
    """Return a single case with its messages, or ``None``."""
    stmt = (
        select(Case)
        .options(selectinload(Case.messages))
        .where(Case.id == case_id, Case.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_message(
    session: AsyncSession,
    *,
    case_id: str,
    role: str,
    content: str,
) -> Message:
    """Append a message to a case and return it."""
    message = Message(case_id=case_id, role=role, content=content)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message
