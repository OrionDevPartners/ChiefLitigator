"""Beta gate access control for the Cyphergy platform.

Manages beta invitations, IP locking on first login, and access
validation. During beta, only approved users can access the platform,
and their access is locked to the IP address of their first login.

Functions:
    approve_beta_user: Create a user account and beta invite record.
    lock_ip: Lock a beta invite to the first login IP address.
    check_ip: Verify that a request IP matches the locked IP.
    revoke_beta_access: Revoke a user's beta access.
    reset_beta_ip: Reset the locked IP to allow re-login from a new IP.
    send_beta_invite_email: Send a beta invite email (stub for production).

Classes:
    BetaGateMiddleware: Middleware enforcing IP locking on protected routes.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.auth.signup import hash_password
from src.database.crud import create_user
from src.database.models import BetaInvite, User

logger = logging.getLogger("cyphergy.security.beta_gate")


# ---------------------------------------------------------------------------
# Beta gate CRUD operations
# ---------------------------------------------------------------------------


async def approve_beta_user(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    password: str,
) -> tuple[User, BetaInvite]:
    """Approve a user for beta access.

    Creates a User record with a hashed password and a BetaInvite
    record with a unique invite code. The invite starts approved
    with no locked IP (set on first login).

    Args:
        db: Active database session.
        email: User email address.
        name: Display name.
        password: Plaintext password (hashed with bcrypt before storage).

    Returns:
        Tuple of (User, BetaInvite) instances.
    """
    password_hash = hash_password(password)
    user = await create_user(
        db,
        email=email,
        password_hash=password_hash,
        name=name,
    )

    invite = BetaInvite(
        id=uuid.uuid4(),
        email=email,
        invite_code=secrets.token_urlsafe(32),
        is_approved=True,
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)

    logger.info("beta_user_approved | email=%s user_id=%s", email, user.id)
    return user, invite


async def lock_ip(
    db: AsyncSession,
    *,
    email: str,
    ip_address: str,
) -> BetaInvite | None:
    """Lock a beta invite to the first login IP address.

    Only locks if the invite has no locked_ip yet (first login).
    Subsequent calls with the same email are no-ops if already locked.

    Args:
        db: Active database session.
        email: The beta user's email.
        ip_address: The IP address to lock.

    Returns:
        The updated BetaInvite, or None if no valid invite found.
    """
    stmt = select(BetaInvite).where(
        BetaInvite.email == email,
        BetaInvite.is_approved.is_(True),
        BetaInvite.is_revoked.is_(False),
    )
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite is None:
        return None

    if invite.locked_ip is None:
        invite.locked_ip = ip_address
        await db.flush()
        await db.refresh(invite)
        logger.info("beta_ip_locked | email=%s ip=%s", email, ip_address)

    return invite


async def check_ip(
    db: AsyncSession,
    *,
    email: str,
    ip_address: str,
) -> bool:
    """Check if the given IP matches the locked IP for a beta invite.

    Returns True if:
      - The invite exists, is approved, and is not revoked, AND
      - The locked_ip is None (first login, not yet locked), OR
      - The locked_ip matches the given ip_address.

    Returns False otherwise.

    Args:
        db: Active database session.
        email: The beta user's email.
        ip_address: The IP address to check.

    Returns:
        True if access should be allowed, False otherwise.
    """
    stmt = select(BetaInvite).where(
        BetaInvite.email == email,
        BetaInvite.is_approved.is_(True),
        BetaInvite.is_revoked.is_(False),
    )
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite is None:
        return False

    if invite.locked_ip is None:
        return True

    return invite.locked_ip == ip_address


async def revoke_beta_access(
    db: AsyncSession,
    *,
    email: str,
) -> bool:
    """Revoke beta access for a user.

    Sets is_revoked=True on the invite record. Revoked invites
    fail all subsequent check_ip calls.

    Args:
        db: Active database session.
        email: The beta user's email.

    Returns:
        True if the invite was found and revoked, False otherwise.
    """
    stmt = select(BetaInvite).where(BetaInvite.email == email)
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite is None:
        return False

    invite.is_revoked = True
    await db.flush()
    logger.info("beta_access_revoked | email=%s", email)
    return True


async def reset_beta_ip(
    db: AsyncSession,
    *,
    email: str,
) -> bool:
    """Reset the locked IP for a beta invite.

    Clears the locked_ip field, allowing the user to re-login
    from a new IP address. The next login will lock to the new IP.

    Args:
        db: Active database session.
        email: The beta user's email.

    Returns:
        True if the invite was found and reset, False otherwise.
    """
    stmt = select(BetaInvite).where(BetaInvite.email == email)
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite is None:
        return False

    invite.locked_ip = None
    await db.flush()
    logger.info("beta_ip_reset | email=%s", email)
    return True


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class BetaGateMiddleware(BaseHTTPMiddleware):
    """Enforce beta IP locking on protected API routes.

    Reads ``request.state.jwt_payload`` (set by JWTAuthMiddleware) to
    identify the user, and ``request.state.client_ip`` (set by
    SecurityMiddleware) to get the connecting IP. Compares the IP
    against ``request.state.beta_locked_ip`` which should be set by
    an upstream dependency or middleware that performed the DB lookup.

    Routes outside ``/api/v1/`` and auth routes are always allowed.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,  # type: ignore[type-arg]
    ) -> Response:
        # Skip non-API routes
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        # Skip auth endpoints (signup/login are public)
        if request.url.path.startswith("/api/v1/auth/"):
            return await call_next(request)

        # Read JWT payload — if absent, let JWTAuthMiddleware handle it
        jwt_payload = getattr(request.state, "jwt_payload", None)
        if jwt_payload is None:
            return await call_next(request)

        # Extract client IP
        client_ip = getattr(request.state, "client_ip", None)
        if not client_ip and request.client:
            client_ip = request.client.host

        # Check beta locked IP against client IP
        beta_locked_ip = getattr(request.state, "beta_locked_ip", None)
        if beta_locked_ip is not None and beta_locked_ip != client_ip:
            logger.warning(
                "beta_gate_blocked | email=%s expected_ip=%s actual_ip=%s",
                jwt_payload.get("email", "unknown"),
                beta_locked_ip,
                client_ip,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Access denied. IP address does not match registered device.",
                },
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Email stub
# ---------------------------------------------------------------------------


def send_beta_invite_email(email: str, invite_code: str) -> dict[str, str]:
    """Send a beta program invite email.

    In production this integrates with an email service (SES, SendGrid).
    Returns a dict with email metadata for confirmation.

    Args:
        email: Recipient email address.
        invite_code: The unique invite code for the invitation link.

    Returns:
        Dict with to, subject, invite_code, and status fields.
    """
    logger.info("beta_invite_sent | email=%s", email)
    return {
        "to": email,
        "subject": "You're invited to the Cyphergy Beta",
        "invite_code": invite_code,
        "status": "sent",
    }
