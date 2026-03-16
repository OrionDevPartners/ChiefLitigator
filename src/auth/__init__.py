"""Cyphergy JWT authentication module.

Provides JWT token creation, verification, and FastAPI middleware
for protecting API endpoints. Configuration is sourced exclusively
from environment variables (CPAA-compliant).

Exports:
    JWTHandler: Token creation and verification.
    JWTAuthMiddleware: FastAPI middleware for route-level JWT enforcement.
"""

from src.auth.jwt_handler import JWTHandler
from src.auth.middleware import JWTAuthMiddleware

__all__ = [
    "JWTHandler",
    "JWTAuthMiddleware",
]
