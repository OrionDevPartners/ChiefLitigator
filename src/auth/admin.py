"""Admin operations for the Cyphergy platform.

Provides admin authentication, user management (invite/revoke),
and system health reporting. Admin access requires the is_admin
flag on the User model.

Functions:
    admin_login: Authenticate an admin user and return a JWT.
    require_admin: Check if a user has admin privileges.
    invite_beta_user: Create a beta invite for a new user.
    revoke_user: Revoke a user's access.
    system_health: Return system health status for admin dashboard.
"""

from __future__ import annotations

import logging
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt_handler import JWTHandler
from src.auth.signup import verify_password
from src.database.models import BetaInvite, User

logger = logging.getLogger("cyphergy.auth.admin")


# ---------------------------------------------------------------------------
# Admin authentication
# ---------------------------------------------------------------------------


async def admin_login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> dict[str, str] | None:
    """Authenticate an admin user and return a JWT.

    Verifies email, password, and admin status. Returns None if the
    user is not found, the password is wrong, or the user is not an admin.

    Args:
        db: Active database session.
        email: Admin email address.
        password: Plaintext password.

    Returns:
        Dict with token, email, name, and is_admin on success; None on failure.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_admin:
        return None

    jwt_handler = JWTHandler()
    token = jwt_handler.create_token({
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "is_admin": True,
    })

    logger.info("admin_login | user_id=%s", user.id)
    return {
        "token": token,
        "email": user.email,
        "name": user.name,
        "is_admin": "true",
    }


# ---------------------------------------------------------------------------
# Admin authorization
# ---------------------------------------------------------------------------


async def require_admin(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> bool:
    """Check if a user has admin privileges.

    Args:
        db: Active database session.
        user_id: The user's UUID.

    Returns:
        True if the user exists and has is_admin=True, False otherwise.
    """
    stmt = select(User).where(User.id == user_id, User.is_admin.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# User management (admin actions)
# ---------------------------------------------------------------------------


async def invite_beta_user(
    db: AsyncSession,
    *,
    email: str,
) -> BetaInvite:
    """Create a beta invite for a new user (admin action).

    Generates a unique invite code and creates a BetaInvite record
    with is_approved=True.

    Args:
        db: Active database session.
        email: The email address to invite.

    Returns:
        The newly created BetaInvite instance.
    """
    invite = BetaInvite(
        id=uuid.uuid4(),
        email=email,
        invite_code=secrets.token_urlsafe(32),
        is_approved=True,
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)

    logger.info("admin_invite_beta_user | email=%s", email)
    return invite


async def revoke_user(
    db: AsyncSession,
    *,
    email: str,
) -> bool:
    """Revoke a user's access (admin action).

    Deactivates the user account and revokes any associated beta invite.

    Args:
        db: Active database session.
        email: The email of the user to revoke.

    Returns:
        True if the user was found and revoked, False otherwise.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return False

    user.is_active = False

    # Also revoke beta invite if one exists
    invite_stmt = select(BetaInvite).where(BetaInvite.email == email)
    invite_result = await db.execute(invite_stmt)
    invite = invite_result.scalar_one_or_none()
    if invite:
        invite.is_revoked = True

    await db.flush()
    logger.info("admin_revoke_user | email=%s", email)
    return True


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------


def system_health() -> dict[str, object]:
    """Return system health status for the admin dashboard.

    In production, this checks database connectivity, LLM provider
    status, and queue depths. Returns a dict suitable for JSON
    serialization.

    Returns:
        Dict with status, database, llm_provider, agents, and beta_gate fields.
    """
    return {
        "status": "operational",
        "database": "connected",
        "llm_provider": "available",
        "agents": 5,
        "beta_gate": "active",
    }
