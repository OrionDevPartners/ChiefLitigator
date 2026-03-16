"""Admin audit trail — logs every admin action with identity and context.

Every destructive or state-changing action taken through the admin panel
is recorded here. This is a legal-grade audit trail: no deletions, no
updates, append-only. The audit log is queryable for compliance reviews.

CPAA: Database connection sourced from DATABASE_URL environment variable.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.database.engine import Base
from src.database.models import GUID

logger = logging.getLogger("cyphergy.admin.audit")


# ---------------------------------------------------------------------------
# Audit Log Model
# ---------------------------------------------------------------------------


class AdminAuditLog(Base):
    """Append-only audit trail for admin actions.

    Every action taken through the admin panel is recorded with the
    admin's email, the action performed, structured details, the
    originating IP address, and a server-side timestamp.

    This table is append-only. No UPDATE or DELETE operations are
    permitted in application code.

    Attributes:
        id: Unique audit entry identifier (UUID4).
        admin_email: Email of the admin who performed the action.
        action: Short action identifier (e.g., "beta_invite", "deploy").
        details: Structured JSON payload with action-specific context.
        ip_address: IP address of the admin making the request.
        timestamp: Server-side timestamp of the action.
    """

    __tablename__ = "admin_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    admin_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_admin_audit_log_admin_email", "admin_email"),
        Index("ix_admin_audit_log_action", "action"),
        Index("ix_admin_audit_log_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AdminAuditLog id={self.id} admin={self.admin_email} "
            f"action={self.action} ts={self.timestamp}>"
        )


# ---------------------------------------------------------------------------
# Beta User Model
# ---------------------------------------------------------------------------


class BetaUser(Base):
    """Beta program user — invite-only access with IP locking.

    Created when an admin invites a user via /admin/beta/invite.
    The first login IP becomes the only allowed IP for that user
    (IP lock). Access can be revoked or IP can be reset by admin.

    Attributes:
        id: Unique beta user identifier (UUID4).
        email: Invited user's email address (unique).
        name: User's display name.
        status: Account status (invited, active, revoked).
        locked_ip: The IP address locked on first login (nullable until first login).
        invited_by: Admin email who sent the invite.
        invited_at: Timestamp of the invitation.
        first_login_at: Timestamp of the first successful login (nullable).
    """

    __tablename__ = "beta_users"

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
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="invited",
        nullable=False,
    )
    locked_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    invited_by: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    first_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_beta_users_email", "email"),
        Index("ix_beta_users_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<BetaUser id={self.id} email={self.email} status={self.status}>"


# ---------------------------------------------------------------------------
# Audit logging helper
# ---------------------------------------------------------------------------


async def log_admin_action(
    db,
    *,
    admin_email: str,
    action: str,
    details: dict | None = None,
    ip_address: str = "unknown",
) -> AdminAuditLog:
    """Record an admin action to the audit trail.

    This function is called by every admin endpoint that performs a
    state-changing operation. It creates an append-only record.

    Args:
        db: Active database session.
        admin_email: The authenticated admin's email.
        action: Short action identifier.
        details: Optional structured context for the action.
        ip_address: The admin's IP address.

    Returns:
        The created AdminAuditLog entry.
    """
    entry = AdminAuditLog(
        id=uuid.uuid4(),
        admin_email=admin_email,
        action=action,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    logger.info(
        "admin_audit | admin=%s action=%s ip=%s",
        admin_email,
        action,
        ip_address,
    )

    return entry
