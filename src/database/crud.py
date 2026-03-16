"""Async CRUD operations for the Cyphergy database layer.

All functions accept an AsyncSession and return ORM model instances.
These are designed to be called from FastAPI endpoint handlers using
the ``get_db`` dependency.

No business logic lives here -- only data access. Validation and
authorization belong in the endpoint or service layer.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Case, Deadline, Message, User


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password_hash: str,
    name: str,
) -> User:
    """Create a new user and flush to obtain the generated ID.

    Args:
        db: Active database session.
        email: User email address (must be unique).
        password_hash: Pre-hashed password (bcrypt).
        name: Display name.

    Returns:
        The newly created User instance with its ID populated.
    """
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=password_hash,
        name=name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user_by_email(
    db: AsyncSession,
    *,
    email: str,
) -> User | None:
    """Look up a user by email address.

    Args:
        db: Active database session.
        email: The email to search for.

    Returns:
        The User if found, otherwise None.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> User | None:
    """Look up a user by their UUID.

    Args:
        db: Active database session.
        user_id: The user's UUID.

    Returns:
        The User if found, otherwise None.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Case CRUD
# ---------------------------------------------------------------------------


async def create_case(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    jurisdiction: str | None = None,
) -> Case:
    """Create a new legal case for a user.

    Args:
        db: Active database session.
        user_id: The owning user's UUID.
        name: Case name (e.g., "Smith v. Jones").
        jurisdiction: Optional jurisdiction code.

    Returns:
        The newly created Case instance.
    """
    case = Case(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        jurisdiction=jurisdiction,
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


async def get_cases_for_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[Case]:
    """Retrieve all cases belonging to a user, ordered by creation date.

    Args:
        db: Active database session.
        user_id: The user's UUID.

    Returns:
        List of Case instances (may be empty).
    """
    stmt = (
        select(Case)
        .where(Case.user_id == user_id)
        .order_by(Case.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_case_by_id(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
) -> Case | None:
    """Look up a case by its UUID.

    Args:
        db: Active database session.
        case_id: The case UUID.

    Returns:
        The Case if found, otherwise None.
    """
    stmt = select(Case).where(Case.id == case_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Message CRUD
# ---------------------------------------------------------------------------


async def create_message(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    role: str,
    content: str,
    agent_id: str | None = None,
    confidence: float | None = None,
    citations: list[str] | None = None,
) -> Message:
    """Record a chat message in a case.

    Args:
        db: Active database session.
        case_id: The parent case UUID.
        role: Message role ("user" or "assistant").
        content: Full message text.
        agent_id: Which agent produced the response (assistant only).
        confidence: Agent confidence score 0.0-1.0 (assistant only).
        citations: List of citation strings (assistant only).

    Returns:
        The newly created Message instance.
    """
    message = Message(
        id=uuid.uuid4(),
        case_id=case_id,
        role=role,
        content=content,
        agent_id=agent_id,
        confidence=confidence,
        citations=citations,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_messages_for_case(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
) -> list[Message]:
    """Retrieve all messages for a case, ordered chronologically.

    Args:
        db: Active database session.
        case_id: The case UUID.

    Returns:
        List of Message instances in chronological order.
    """
    stmt = (
        select(Message)
        .where(Message.case_id == case_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Deadline CRUD
# ---------------------------------------------------------------------------


async def create_deadline(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
    title: str,
    deadline_date: date,
    deadline_type: str,
    jurisdiction: str,
    rule_citation: str,
    status: str = "pending",
) -> Deadline:
    """Create a filing deadline for a case.

    Args:
        db: Active database session.
        case_id: The parent case UUID.
        title: Human-readable deadline description.
        deadline_date: The computed filing deadline.
        deadline_type: Type of deadline (e.g., "answer", "motion").
        jurisdiction: Jurisdiction code.
        rule_citation: The procedural rule backing this deadline.
        status: Initial status (default "pending").

    Returns:
        The newly created Deadline instance.
    """
    deadline = Deadline(
        id=uuid.uuid4(),
        case_id=case_id,
        title=title,
        deadline_date=deadline_date,
        deadline_type=deadline_type,
        jurisdiction=jurisdiction,
        rule_citation=rule_citation,
        status=status,
    )
    db.add(deadline)
    await db.flush()
    await db.refresh(deadline)
    return deadline


async def get_deadlines_for_case(
    db: AsyncSession,
    *,
    case_id: uuid.UUID,
) -> list[Deadline]:
    """Retrieve all deadlines for a case, ordered by deadline date.

    Args:
        db: Active database session.
        case_id: The case UUID.

    Returns:
        List of Deadline instances ordered by deadline_date ascending.
    """
    stmt = (
        select(Deadline)
        .where(Deadline.case_id == case_id)
        .order_by(Deadline.deadline_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
