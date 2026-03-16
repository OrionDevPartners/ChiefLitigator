"""Cyphergy authentication module.

Provides JWT token creation, verification, FastAPI middleware for
protecting API endpoints, and signup/login endpoints with bcrypt
password hashing. Configuration is sourced exclusively from
environment variables (CPAA-compliant).

Exports:
    JWTHandler: Token creation and verification.
    JWTAuthMiddleware: FastAPI middleware for route-level JWT enforcement.
    auth_router: FastAPI router with /api/v1/auth/signup and /api/v1/auth/login.
"""

from src.auth.jwt_handler import JWTHandler
from src.auth.middleware import JWTAuthMiddleware
from src.auth.signup import router as auth_router

__all__ = [
    "JWTHandler",
    "JWTAuthMiddleware",
    "auth_router",
]
