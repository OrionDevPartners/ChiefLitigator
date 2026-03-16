"""Beta gate system for invite-only access control with IP locking.

Modules:
    gate       -- BetaGate class with approve, verify, revoke logic
    models     -- BetaInvite SQLAlchemy ORM model
    middleware -- FastAPI middleware for IP enforcement on /api/v1/ routes
    email      -- Beta invite email sender (SES or console fallback)
    router     -- Admin-facing API endpoints for beta management
"""

from src.beta.gate import BetaGate
from src.beta.router import beta_router

__all__ = ["BetaGate", "beta_router"]
