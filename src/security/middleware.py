"""FastAPI security middleware for the Cyphergy platform.

Responsibilities:
  - CORS enforcement (strict origin allow-list)
  - Security response headers (HSTS, CSP, X-Frame-Options, etc.)
  - Request ID generation (UUID v4 per request for audit trail)
  - Request logging (method, path, status, duration -- NO body or PII)
  - IP extraction for downstream rate limiting

Design rationale:
  Legal data platforms are high-value targets. Every response must carry
  defense-in-depth headers. Every request must be traceable via a unique
  ID for incident investigation and HIPAA audit requirements.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI

logger = logging.getLogger("cyphergy.security.middleware")


# ---------------------------------------------------------------------------
# Configuration from environment (CPAA-compliant -- zero hardcoding)
# ---------------------------------------------------------------------------

def _get_allowed_origins() -> list[str]:
    """Read allowed CORS origins from env.

    Justification: Strict origin allow-listing prevents cross-origin
    attacks against the API. Only explicitly approved frontends may
    make requests.
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not raw:
        # Default: only localhost for development. Production deployments
        # MUST set CORS_ALLOWED_ORIGINS explicitly.
        return ["http://localhost:3000", "http://localhost:8000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _get_csp_policy() -> str:
    """Build Content-Security-Policy header value.

    Justification: CSP prevents XSS and data injection attacks.
    Legal document previews must never load external scripts.
    """
    return os.getenv(
        "CSP_POLICY",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

# Justification for each header:
#   HSTS: Forces HTTPS for all future connections. max-age=31536000 (1 year)
#         is the OWASP recommendation. includeSubDomains covers all subdomains.
#   X-Content-Type-Options: Prevents MIME-type sniffing attacks.
#   X-Frame-Options: Prevents clickjacking by disallowing framing.
#   Referrer-Policy: strict-origin-when-cross-origin prevents URL leakage
#         (case IDs, document paths) to third-party sites.
#   Permissions-Policy: Disables browser features we do not use (camera,
#         microphone, geolocation) to reduce attack surface.
#   X-XSS-Protection: Legacy header still respected by some browsers.

_SECURITY_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-XSS-Protection": "1; mode=block",
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
}


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------

_REQUEST_ID_HEADER = "X-Request-ID"


def _generate_request_id() -> str:
    """Generate a UUID v4 for each inbound request.

    Justification: Unique request IDs enable end-to-end audit trails
    required by HIPAA (45 CFR 164.312(b)) and are essential for
    incident investigation in legal data systems.
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# IP Extraction
# ---------------------------------------------------------------------------

def extract_client_ip(request: Request) -> str:
    """Extract the real client IP from the request.

    Justification: When behind Cloudflare or a load balancer, the client
    IP is in headers, not the socket address. We check in priority order:
    CF-Connecting-IP (Cloudflare), X-Real-IP (nginx), X-Forwarded-For
    (generic proxy), then fall back to the direct connection.
    """
    # Cloudflare sets this header and it cannot be spoofed when
    # requests flow through CF's network.
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # nginx reverse proxy header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Generic proxy chain -- take the first (leftmost) IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Direct connection
    if request.client:
        return request.client.host

    return "unknown"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class SecurityMiddleware(BaseHTTPMiddleware):
    """Production security middleware for Cyphergy.

    Attaches security headers, generates audit-trail request IDs,
    and logs request metadata (never body/PII) for every request.

    Usage:
        app = FastAPI()
        app.add_middleware(SecurityMiddleware)
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # --- Request phase ---
        request_id = _generate_request_id()
        # Attach request ID to request state so downstream handlers can access it
        request.state.request_id = request_id
        # Attach client IP for rate limiting
        request.state.client_ip = extract_client_ip(request)

        start_time = time.monotonic()

        # --- Process request ---
        try:
            response = await call_next(request)
        except Exception:
            # Log the failure with request context but never log exception
            # details that might contain PII from request body
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "request_failed | request_id=%s method=%s path=%s ip=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                request.state.client_ip,
                duration_ms,
            )
            raise

        # --- Response phase ---
        duration_ms = (time.monotonic() - start_time) * 1000

        # Attach security headers to every response
        # Justification: Defense-in-depth -- even error responses must
        # carry security headers to prevent downgrade attacks.
        for header_name, header_value in _SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        # CSP as a separate call since it's configurable
        response.headers["Content-Security-Policy"] = _get_csp_policy()

        # Request ID header for client-side correlation
        response.headers[_REQUEST_ID_HEADER] = request_id

        # --- Audit log ---
        # Justification: HIPAA requires access logging (45 CFR 164.312(b)).
        # We log method, path, status, duration, and IP. We NEVER log
        # request body, query parameters with PII, or response body.
        logger.info(
            "request_completed | request_id=%s method=%s path=%s status=%d "
            "duration_ms=%.1f ip=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.state.client_ip,
        )

        return response


# ---------------------------------------------------------------------------
# CORS Configuration Helper
# ---------------------------------------------------------------------------

def configure_cors(app: FastAPI) -> None:
    """Apply strict CORS configuration to the FastAPI app.

    Justification: Legal data APIs must restrict which origins can make
    requests. We use an explicit allow-list (never wildcard "*") and
    limit allowed methods and headers to the minimum required set.

    Usage:
        app = FastAPI()
        configure_cors(app)
    """
    allowed_origins = _get_allowed_origins()

    app.add_middleware(
        CORSMiddleware,
        # Explicit origin allow-list -- never use ["*"] for legal data
        allow_origins=allowed_origins,
        # Credentials required for session-based auth
        allow_credentials=True,
        # Only the HTTP methods our API actually uses
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        # Only headers our API expects
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            _REQUEST_ID_HEADER,
            "X-Tenant-ID",
        ],
        # Headers the client is allowed to read from responses
        expose_headers=[
            _REQUEST_ID_HEADER,
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
        # Preflight cache: 1 hour (reduces OPTIONS request volume)
        max_age=3600,
    )

    logger.info(
        "cors_configured | origins=%s",
        ",".join(allowed_origins),
    )
