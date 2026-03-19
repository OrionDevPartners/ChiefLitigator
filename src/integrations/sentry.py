"""
Cyphergy Legal — Sentry Integration
Error monitoring and performance tracing for the Cyphergy API.

CPAA: SENTRY_DSN loaded from environment at runtime.
PII Scrubbing: Case data, client names, and legal content are stripped
before events reach Sentry. Legal data never leaves the tenant boundary.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Sensitive field names that must be scrubbed before sending to Sentry.
# These patterns cover case content, client PII, and legal document text.
_PII_DENYLIST: set[str] = {
    "case_text",
    "case_content",
    "client_name",
    "client_email",
    "client_phone",
    "ssn",
    "social_security",
    "date_of_birth",
    "legal_notes",
    "motion_text",
    "brief_text",
    "filing_content",
    "witness_name",
    "opposing_party",
    "medical_records",
    "financial_records",
    "attorney_notes",
    "privileged_content",
}


def _scrub_pii(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Before-send hook that removes PII and case data from Sentry events.

    Sentry must never receive actual legal content — only structural
    metadata about the error (stack trace, module path, error class).
    """
    # Scrub request body data
    request = event.get("request", {})
    if "data" in request and isinstance(request["data"], dict):
        for key in list(request["data"].keys()):
            if key.lower() in _PII_DENYLIST:
                request["data"][key] = "[REDACTED]"

    # Scrub breadcrumb messages
    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if "message" in breadcrumb:
            for field in _PII_DENYLIST:
                if field in breadcrumb["message"].lower():
                    breadcrumb["message"] = "[REDACTED — contains PII field]"
                    break

    # Scrub extra context
    extra = event.get("extra", {})
    for key in list(extra.keys()):
        if key.lower() in _PII_DENYLIST:
            extra[key] = "[REDACTED]"

    # Scrub user context (keep only id for correlation)
    user = event.get("user", {})
    for field in ("email", "username", "ip_address", "name"):
        user.pop(field, None)

    return event


def init_sentry() -> bool:
    """Initialize Sentry SDK with FastAPI integration.

    Returns True if Sentry was initialized, False if SENTRY_DSN is not set.
    Sentry is optional — the app runs fine without it.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("SENTRY_DSN not set — Sentry disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed. Run: pip install 'sentry-sdk[fastapi]'")
        return False

    app_env = os.environ.get("APP_ENV", "development")

    sentry_sdk.init(
        dsn=dsn,
        environment=app_env,
        release=os.environ.get("SENTRY_RELEASE"),
        # Performance: sample 10% of transactions in production,
        # 100% in development for full visibility.
        traces_sample_rate=0.1 if app_env == "production" else 1.0,
        # Profiles: sample 10% for performance profiling.
        profiles_sample_rate=0.1 if app_env == "production" else 1.0,
        # PII scrubbing — strip case data before it leaves the boundary.
        before_send=_scrub_pii,
        send_default_pii=False,
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        # Tags
        server_name=os.environ.get("HOSTNAME", "cyphergy-api"),
    )

    # Set global tags for filtering in the Sentry dashboard.
    sentry_sdk.set_tag("service", "cyphergy-api")
    sentry_sdk.set_tag("app_env", app_env)

    logger.info("Sentry initialized for environment=%s", app_env)
    return True
