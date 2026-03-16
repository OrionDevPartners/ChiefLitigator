"""SQLAlchemy ORM models for the Cyphergy platform.

All models use UUID primary keys and server-side timestamps.
The schema is designed for PostgreSQL 16 in production and
supports SQLite for local development and testing.

Models:
    User     -- Platform users (email + bcrypt password hash)
    Case     -- Legal cases belonging to a user
    Message  -- Chat messages within a case (user or assistant)
    Deadline -- Jurisdiction-aware filing deadlines for a case
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from src.database.engine import Base


# ---------------------------------------------------------------------------
# Cross-dialect UUID type
# ---------------------------------------------------------------------------


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's native UUID type when available, otherwise stores
    as a 36-character string (for SQLite compatibility in tests).
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    """Platform user account.

    Attributes:
        id: Unique user identifier (UUID4).
        email: User email address (unique, indexed for login lookups).
        password_hash: Bcrypt hash of the user password.
        name: Display name.
        created_at: Account creation timestamp (server-side default).
        is_active: Whether the account is active. Disabled accounts
            cannot authenticate.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    cases: Mapped[list[Case]] = relationship(
        "Case",
        back_populates="user",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class Case(Base):
    """Legal case belonging to a user.

    Attributes:
        id: Unique case identifier (UUID4).
        user_id: Foreign key to the owning user.
        name: Case name (e.g., "Smith v. Jones").
        jurisdiction: Jurisdiction code (nullable).
        status: Case status (active, archived, closed).
        created_at: Case creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    jurisdiction: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="cases",
    )
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="case",
        lazy="selectin",
        order_by="Message.created_at",
    )
    deadlines: Mapped[list[Deadline]] = relationship(
        "Deadline",
        back_populates="case",
        lazy="selectin",
        order_by="Deadline.deadline_date",
    )

    __table_args__ = (
        Index("ix_cases_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} name={self.name!r}>"


class Message(Base):
    """Chat message within a case.

    Attributes:
        id: Unique message identifier (UUID4).
        case_id: Foreign key to the parent case.
        role: Message author role ("user" or "assistant").
        content: Full message text.
        agent_id: Which agent produced this response (nullable, assistant only).
        confidence: Agent confidence score 0.0-1.0 (nullable).
        citations: JSON list of citation strings (nullable).
        created_at: Message timestamp.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    citations: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    case: Mapped[Case] = relationship(
        "Case",
        back_populates="messages",
    )

    __table_args__ = (
        Index("ix_messages_case_id", "case_id"),
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} case_id={self.case_id}>"


class Deadline(Base):
    """Jurisdiction-aware filing deadline for a case.

    Attributes:
        id: Unique deadline identifier (UUID4).
        case_id: Foreign key to the parent case.
        title: Human-readable deadline description.
        deadline_date: The computed filing deadline date.
        deadline_type: Type of deadline (e.g., "answer", "motion").
        jurisdiction: Jurisdiction code for this deadline.
        rule_citation: The procedural rule backing this deadline.
        status: Deadline status (pending, filed, missed, waived).
        created_at: Deadline creation timestamp.
    """

    __tablename__ = "deadlines"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    deadline_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    deadline_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    jurisdiction: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    rule_citation: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    case: Mapped[Case] = relationship(
        "Case",
        back_populates="deadlines",
    )

    __table_args__ = (
        Index("ix_deadlines_case_id", "case_id"),
    )

    @property
    def days_remaining(self) -> int:
        """Compute days between today and the deadline date.

        Returns a negative number if the deadline has passed.
        """
        return (self.deadline_date - date.today()).days

    def __repr__(self) -> str:
        return f"<Deadline id={self.id} title={self.title!r} date={self.deadline_date}>"
