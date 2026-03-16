"""JWT token creation and verification for the Cyphergy platform.

All secrets are sourced from environment variables (CPAA-compliant).
Tokens use HS256 signing with a configurable expiration window.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import jwt

logger = logging.getLogger("cyphergy.auth.jwt_handler")

# Default token lifetime: 30 minutes (in seconds)
_DEFAULT_EXPIRY_SECONDS = 1800


class JWTHandler:
    """Create and verify HS256-signed JWT tokens.

    Configuration:
        JWT_SECRET_KEY (required): Symmetric signing key. The service
            refuses to start if this variable is missing.
        JWT_ALGORITHM (optional): Signing algorithm. Default ``HS256``.
        JWT_EXPIRY_SECONDS (optional): Token lifetime in seconds.
            Default ``1800`` (30 minutes).
    """

    def __init__(self) -> None:
        self._secret_key = os.getenv("JWT_SECRET_KEY", "")
        if not self._secret_key:
            raise RuntimeError(
                "JWT_SECRET_KEY environment variable is not set. "
                "JWT authentication cannot function without a signing key."
            )
        self._algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        try:
            self._expiry_seconds = int(os.getenv("JWT_EXPIRY_SECONDS", str(_DEFAULT_EXPIRY_SECONDS)))
        except ValueError:
            self._expiry_seconds = _DEFAULT_EXPIRY_SECONDS

    def create_token(self, payload: dict[str, Any]) -> str:
        """Create a signed JWT with standard ``iat`` and ``exp`` claims.

        Args:
            payload: Arbitrary claims to embed in the token. Must not
                contain ``iat`` or ``exp`` keys — they are set automatically.

        Returns:
            An encoded JWT string.
        """
        now = int(time.time())
        token_payload = {
            **payload,
            "iat": now,
            "exp": now + self._expiry_seconds,
        }
        token: str = jwt.encode(token_payload, self._secret_key, algorithm=self._algorithm)
        return token

    def verify_token(self, token: str) -> dict[str, Any]:
        """Decode and verify a JWT.

        Args:
            token: The encoded JWT string.

        Returns:
            The decoded payload dictionary.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is malformed or
                signature verification fails.
        """
        decoded: dict[str, Any] = jwt.decode(
            token,
            self._secret_key,
            algorithms=[self._algorithm],
        )
        return decoded
