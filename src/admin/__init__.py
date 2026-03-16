"""Cyphergy admin module — FULLY SEPARATE from user-facing code.

Provides admin-only JWT authentication, beta user management,
system health monitoring, and an internal chat agent for
admin.cyphergy.ai. All configuration is sourced from environment
variables with a DIFFERENT JWT secret than user auth (CPAA-compliant).

Exports:
    admin_router: FastAPI router with all /admin/ endpoints.
    AdminAgent: Internal admin agent with elevated access.
"""

from src.admin.agent import AdminAgent
from src.admin.routes import admin_router

__all__ = [
    "admin_router",
    "AdminAgent",
]
