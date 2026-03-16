"""SQLAlchemy ORM model for beta invite records.

Each invite tracks the approval lifecycle: pending -> active -> revoked.
The locked_ip field is populated on first login and used by the beta
middleware to enforce single-IP access.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.engine import Base
from src.database.models import GUID


class BetaInvite(Base):
    """Beta program invite with IP-lock enforcement.

    Attributes:
        id: Unique invite identifier (UUID4).
        user_id: Foreign key to the invited user.
        invited_by: Email address of the admin who approved the invite.
        locked_ip: IP address locked on first login (nullable until first login).
        status: Invite lifecycle state (pending, active, revoked).
        created_at: Invite creation timestamp.
        activated_at: Timestamp of first login / IP lock (nullable).
        revoked_at: Timestamp of access revocation (nullable).
    """

    __tablename__ = "beta_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    invited_by: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    locked_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default="pending",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_beta_invites_user_id", "user_id"),
        Index("ix_beta_invites_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<BetaInvite id={self.id} user_id={self.user_id} status={self.status}>"
