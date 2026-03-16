"""Invite-only beta access control with IP locking.

BetaGate handles the full lifecycle of beta invitations:
1. Admin approves a user (generates credentials, creates invite record)
2. First login locks the user to their originating IP address
3. Subsequent requests are verified against the locked IP
4. Admin can revoke access at any time

All configuration from environment variables (CPAA-compliant).
"""

from __future__ import annotations

import logging
import secrets
import string
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.signup import hash_password
from src.beta.models import BetaInvite
from src.database.crud import create_user, get_user_by_email
from src.database.models import User

logger = logging.getLogger("cyphergy.beta.gate")

# Password generation: 16 chars from uppercase + lowercase + digits
_PASSWORD_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
_PASSWORD_LENGTH = 16


def _generate_password() -> str:
    """Generate a cryptographically secure random password.

    Returns a 16-character string containing uppercase letters,
    lowercase letters, and digits. Uses secrets module for
    cryptographic randomness.
    """
    # Ensure at least one of each required character class
    password_chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    # Fill remaining characters from full alphabet
    for _ in range(_PASSWORD_LENGTH - 3):
        password_chars.append(secrets.choice(_PASSWORD_ALPHABET))

    # Shuffle to avoid predictable positions
    # Use Fisher-Yates via secrets for uniform distribution
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)


class BetaGate:
    """Invite-only beta access control with IP locking."""

    async def approve_user(
        self,
        email: str,
        name: str,
        db: AsyncSession,
        invited_by: str = "admin@cyphergy.ai",
    ) -> dict:
        """Admin approves a beta user. Generates random password, creates account.

        If the user already exists, raises ValueError. Creates both the User
        record and the BetaInvite record in a single transaction.

        Args:
            email: Email address for the new beta user.
            name: Display name for the new beta user.
            db: Active database session.
            invited_by: Email of the approving admin.

        Returns:
            Dict with email, password (plaintext -- for the invite email only),
            and invite_id.

        Raises:
            ValueError: If a user with this email already exists.
        """
        existing = await get_user_by_email(db, email=email)
        if existing is not None:
            raise ValueError(f"User with email {email} already exists.")

        password = _generate_password()
        password_hash = hash_password(password)

        user = await create_user(
            db,
            email=email,
            password_hash=password_hash,
            name=name,
        )

        invite = BetaInvite(
            id=uuid.uuid4(),
            user_id=user.id,
            invited_by=invited_by,
            status="pending",
        )
        db.add(invite)
        await db.flush()
        await db.refresh(invite)

        logger.info("beta_user_approved | user_id=%s invite_id=%s", user.id, invite.id)

        return {
            "email": email,
            "password": password,
            "invite_id": str(invite.id),
            "user_id": str(user.id),
        }

    async def get_invite_by_user_id(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> BetaInvite | None:
        """Look up a beta invite by user ID.

        Args:
            user_id: The user's UUID.
            db: Active database session.

        Returns:
            The BetaInvite if found, otherwise None.
        """
        stmt = select(BetaInvite).where(BetaInvite.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def record_first_login(
        self,
        user_id: uuid.UUID,
        ip_address: str,
        db: AsyncSession,
    ) -> None:
        """Lock user to their first login IP.

        Updates the BetaInvite record with the locked IP address
        and sets the status to active.

        Args:
            user_id: The user's UUID.
            ip_address: The IP address from the first login request.
            db: Active database session.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(BetaInvite)
            .where(BetaInvite.user_id == user_id)
            .values(
                locked_ip=ip_address,
                status="active",
                activated_at=now,
            )
        )
        await db.execute(stmt)
        await db.flush()

        logger.info(
            "beta_first_login | user_id=%s ip_locked=True",
            user_id,
        )

    async def verify_ip(
        self,
        user_id: uuid.UUID,
        ip_address: str,
        db: AsyncSession,
    ) -> bool:
        """Check if login IP matches the locked IP.

        If no locked IP yet (first login), locks the IP and returns True.
        If the user has been revoked, returns False.

        Args:
            user_id: The user's UUID.
            ip_address: The IP address from the current request.
            db: Active database session.

        Returns:
            True if access is permitted, False otherwise.
        """
        invite = await self.get_invite_by_user_id(user_id, db)

        if invite is None:
            # No beta invite record -- deny access
            return False

        if invite.status == "revoked":
            return False

        if invite.locked_ip is None:
            # First login -- lock the IP
            await self.record_first_login(user_id, ip_address, db)
            return True

        return ip_address == invite.locked_ip

    async def revoke_user(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        """Admin revokes beta access.

        Sets BetaInvite status to revoked and deactivates the User account.

        Args:
            user_id: The user's UUID.
            db: Active database session.
        """
        now = datetime.now(timezone.utc)

        # Revoke the invite
        stmt = (
            update(BetaInvite)
            .where(BetaInvite.user_id == user_id)
            .values(
                status="revoked",
                revoked_at=now,
            )
        )
        await db.execute(stmt)

        # Deactivate the user account
        stmt = update(User).where(User.id == user_id).values(is_active=False)
        await db.execute(stmt)
        await db.flush()

        logger.info("beta_user_revoked | user_id=%s", user_id)
