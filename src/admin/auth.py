"""Admin authentication — COMPLETELY SEPARATE from user auth.

Admin authentication uses:
- ADMIN_EMAIL env var: The admin's email address.
- ADMIN_PASSWORD_HASH env var: Bcrypt hash of the admin password.
- ADMIN_JWT_SECRET env var: A DIFFERENT signing secret than user JWT.

This ensures that admin tokens cannot be forged using user JWT secrets
and vice versa. The admin JWT includes a {"role": "admin"} claim that
is verified by the admin middleware on every /admin/ request.

CPAA-compliant: all secrets from environment variables.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.audit import log_admin_action
from src.database.engine import get_db

logger = logging.getLogger("cyphergy.admin.auth")

# Default admin token lifetime: 4 hours (shorter sessions for admin)
_ADMIN_EXPIRY_SECONDS = 14400


# ---------------------------------------------------------------------------
# Admin JWT Handler — uses ADMIN_JWT_SECRET (NOT JWT_SECRET_KEY)
# ---------------------------------------------------------------------------


class AdminJWTHandler:
    """Create and verify admin-specific HS256-signed JWT tokens.

    Uses ADMIN_JWT_SECRET which is completely separate from the user
    JWT_SECRET_KEY. Admin tokens carry a role=admin claim.
    """

    def __init__(self) -> None:
        self._secret_key = os.getenv("ADMIN_JWT_SECRET", "")
        if not self._secret_key:
            raise RuntimeError(
                "ADMIN_JWT_SECRET environment variable is not set. "
                "Admin authentication cannot function without a signing key."
            )
        self._algorithm = os.getenv("ADMIN_JWT_ALGORITHM", "HS256")
        try:
            self._expiry_seconds = int(
                os.getenv("ADMIN_JWT_EXPIRY_SECONDS", str(_ADMIN_EXPIRY_SECONDS))
            )
        except ValueError:
            self._expiry_seconds = _ADMIN_EXPIRY_SECONDS

    def create_token(self, payload: dict[str, Any]) -> str:
        """Create a signed admin JWT with role=admin claim.

        Args:
            payload: Claims to embed. The role=admin claim is always
                added/overwritten to prevent privilege escalation.

        Returns:
            An encoded JWT string.
        """
        now = int(time.time())
        token_payload = {
            **payload,
            "role": "admin",
            "iat": now,
            "exp": now + self._expiry_seconds,
        }
        token: str = jwt.encode(
            token_payload, self._secret_key, algorithm=self._algorithm
        )
        return token

    def verify_token(self, token: str) -> dict[str, Any]:
        """Decode, verify, and validate admin JWT.

        Checks both signature validity and the presence of the
        role=admin claim. A valid user JWT will fail here because
        it uses a different secret and lacks the admin role claim.

        Args:
            token: The encoded JWT string.

        Returns:
            The decoded payload dictionary.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is malformed or
                signature verification fails.
            ValueError: If the role claim is not "admin".
        """
        decoded: dict[str, Any] = jwt.decode(
            token,
            self._secret_key,
            algorithms=[self._algorithm],
        )
        if decoded.get("role") != "admin":
            raise ValueError("Token does not have admin role.")
        return decoded


# ---------------------------------------------------------------------------
# Admin credential verification
# ---------------------------------------------------------------------------


def verify_admin_credentials(email: str, password: str) -> bool:
    """Verify admin email and password against environment variables.

    ADMIN_EMAIL and ADMIN_PASSWORD_HASH must be set in the environment.
    The password is verified against the stored bcrypt hash.

    Args:
        email: The submitted email address.
        password: The submitted plaintext password.

    Returns:
        True if credentials match, False otherwise.
    """
    admin_email = os.getenv("ADMIN_EMAIL", "")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

    if not admin_email or not admin_password_hash:
        logger.error(
            "admin_auth_misconfigured | ADMIN_EMAIL or ADMIN_PASSWORD_HASH not set"
        )
        return False

    if email != admin_email:
        return False

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            admin_password_hash.encode("utf-8"),
        )
    except Exception:
        logger.error("admin_password_verify_failed | bcrypt error")
        return False


# ---------------------------------------------------------------------------
# FastAPI dependency — extract and validate admin JWT from request
# ---------------------------------------------------------------------------


def _get_admin_jwt_handler() -> AdminJWTHandler:
    """Lazy-initialize AdminJWTHandler to avoid import-time env var reads."""
    return AdminJWTHandler()


async def require_admin(request: Request) -> dict[str, Any]:
    """FastAPI dependency that enforces admin authentication.

    Extracts the Bearer token from the Authorization header, verifies
    it with ADMIN_JWT_SECRET, and confirms the role=admin claim.

    Returns:
        The decoded admin JWT payload with guaranteed role=admin.

    Raises:
        HTTPException 401: If the token is missing, expired, invalid,
            or does not carry the admin role.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        handler = _get_admin_jwt_handler()
        payload = handler.verify_token(token)
    except jwt.ExpiredSignatureError:
        logger.warning("admin_auth_expired | path=%s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError) as exc:
        logger.warning(
            "admin_auth_invalid | path=%s error=%s",
            request.url.path,
            str(exc)[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach admin payload to request state for downstream use
    request.state.admin_payload = payload
    return payload


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting proxy headers.

    Checks X-Forwarded-For (set by ALB/Cloudflare) first, then
    falls back to the direct client address.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs: client, proxy1, proxy2
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
