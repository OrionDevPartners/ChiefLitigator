"""FastAPI middleware for beta gate IP enforcement.

Intercepts all /api/v1/ requests (except /api/v1/auth/) and validates
that the requesting IP matches the IP locked during first login.

IP extraction priority (for Cloudflare/proxy environments):
1. CF-Connecting-IP (Cloudflare)
2. X-Real-IP (nginx)
3. X-Forwarded-For (first entry -- closest to client)
4. request.client.host (direct connection fallback)
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.beta.gate import BetaGate

logger = logging.getLogger("cyphergy.beta.middleware")

# Paths exempt from beta IP enforcement
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/",
)


def extract_client_ip(request: Request) -> str:
    """Extract the real client IP from proxy headers.

    Priority order:
    1. CF-Connecting-IP (Cloudflare edge)
    2. X-Real-IP (reverse proxy)
    3. X-Forwarded-For (first IP in chain)
    4. request.client.host (direct connection)

    Args:
        request: The incoming Starlette request.

    Returns:
        The best-effort client IP address string.
    """
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # Nginx / generic proxy
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Standard forwarding chain (take first = original client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Direct connection
    if request.client and request.client.host:
        return request.client.host

    return "0.0.0.0"


class BetaGateMiddleware(BaseHTTPMiddleware):
    """Enforce beta gate IP locking on protected routes.

    This middleware runs AFTER JWT authentication middleware. It expects
    request.state.jwt_payload to be populated with decoded JWT claims
    including a 'sub' field containing the user ID.

    Usage::

        from src.beta.middleware import BetaGateMiddleware
        app.add_middleware(BetaGateMiddleware, db_factory=get_db)
    """

    def __init__(self, app: object, db_factory: Callable) -> None:  # type: ignore[type-arg]
        super().__init__(app)  # type: ignore[arg-type]
        self._gate = BetaGate()
        self._db_factory = db_factory

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,  # type: ignore[type-arg]
    ) -> Response:
        path = request.url.path

        # Skip non-API routes entirely
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        # Skip exempt paths (auth, docs, health)
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Allow CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract user ID from JWT claims (set by JWTAuthMiddleware)
        jwt_payload = getattr(request.state, "jwt_payload", None)
        if jwt_payload is None:
            # JWT middleware should have caught this -- pass through
            return await call_next(request)

        sub = jwt_payload.get("sub")
        if not sub:
            return await call_next(request)

        try:
            user_id = uuid.UUID(sub)
        except (ValueError, AttributeError):
            logger.warning("beta_gate_invalid_sub | sub=%s", sub)
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied -- invalid user identity."},
            )

        client_ip = extract_client_ip(request)

        # Get a database session for the IP check
        async for db in self._db_factory():
            try:
                invite = await self._gate.get_invite_by_user_id(user_id, db)

                if invite is None:
                    # No beta invite -- deny
                    logger.warning(
                        "beta_gate_no_invite | user_id=%s ip=%s",
                        user_id,
                        client_ip,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Beta access required. Contact admin for an invitation."},
                    )

                if invite.status == "revoked":
                    logger.warning(
                        "beta_gate_revoked | user_id=%s",
                        user_id,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Beta access revoked."},
                    )

                if invite.locked_ip is None:
                    # First login -- lock the IP
                    await self._gate.record_first_login(user_id, client_ip, db)
                    await db.commit()
                    logger.info(
                        "beta_gate_ip_locked | user_id=%s",
                        user_id,
                    )
                elif client_ip != invite.locked_ip:
                    logger.warning(
                        "beta_gate_ip_mismatch | user_id=%s",
                        user_id,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Access denied -- IP address not authorized."},
                    )
            except Exception:
                await db.rollback()
                raise
            break

        return await call_next(request)
