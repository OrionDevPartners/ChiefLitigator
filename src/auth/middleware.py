"""FastAPI middleware for JWT-based route protection.

All ``/api/v1/`` routes require a valid ``Authorization: Bearer <token>``
header. Health and documentation endpoints are public.
"""

from __future__ import annotations

import logging
from typing import Callable

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.auth.jwt_handler import JWTHandler

logger = logging.getLogger("cyphergy.auth.middleware")

# Paths that never require authentication.
_PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Enforce JWT authentication on protected routes.

    Protected routes: any path starting with ``/api/v1/``.
    Public routes: ``/health``, ``/health/ready``, ``/docs``, ``/redoc``,
    ``/openapi.json``, and any other path not under ``/api/v1/``.

    Usage::

        from src.auth.middleware import JWTAuthMiddleware
        app.add_middleware(JWTAuthMiddleware)
    """

    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._handler = JWTHandler()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,  # type: ignore[type-arg]
    ) -> Response:
        path = request.url.path

        # Allow public paths through without authentication
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        for prefix in _PUBLIC_PATH_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Allow CORS preflight requests through
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract and validate the Bearer token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("auth_missing | path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"error": "Missing Authorization header."},
            )

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("auth_malformed | path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid Authorization header format. Expected 'Bearer <token>'."},
            )

        token = parts[1]

        try:
            payload = self._handler.verify_token(token)
            # Attach decoded claims to request state for downstream handlers
            request.state.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            logger.warning("auth_expired | path=%s", path)
            return JSONResponse(
                status_code=401,
                content={"error": "Token has expired."},
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("auth_invalid | path=%s error=%s", path, str(exc)[:200])
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid token."},
            )

        return await call_next(request)
