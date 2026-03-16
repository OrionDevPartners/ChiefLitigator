"""Cyphergy security module.

Provides security middleware, rate limiting, and secrets management
for the Cyphergy legal AI platform. All controls are designed for
legal-grade data protection (HIPAA, GDPR, CCPA).

Exports:
    SecurityMiddleware: FastAPI middleware for headers, CORS, request tracing.
    RateLimiter: 4-layer rate limiting (per-IP, per-user, per-tenant, global).
    SecretsManager: Environment validation, secret masking, health checks.
"""

from src.security.middleware import SecurityMiddleware
from src.security.rate_limiter import RateLimiter
from src.security.secrets import SecretsManager

__all__ = [
    "SecurityMiddleware",
    "RateLimiter",
    "SecretsManager",
]
