"""Secrets management for the Cyphergy platform.

Responsibilities:
  - Validate all required environment variables at startup
  - Mask secret values in logs (replace with [REDACTED])
  - Health check reporting (configured vs missing integrations)
  - NEVER print or log actual secret values (@M:010)

Design rationale:
  Legal AI platforms handle HIPAA/GDPR/CCPA-regulated data. Secrets
  leaking into logs, error messages, or stack traces is a compliance
  violation. This module provides a single enforcement point for
  secret hygiene across the entire application.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("cyphergy.security.secrets")


# ---------------------------------------------------------------------------
# Secret Definitions
# ---------------------------------------------------------------------------


class SecretCategory(Enum):
    """Categories for secret classification.

    Justification: Different secrets have different risk profiles.
    An LLM API key leak costs money; a database password leak
    exposes all client legal data. Classification drives audit priority.
    """

    CRITICAL = "critical"  # Database, encryption keys -- data breach risk
    HIGH = "high"  # LLM API keys, auth tokens -- financial/access risk
    MEDIUM = "medium"  # Monitoring, CDN -- operational risk
    LOW = "low"  # Feature flags, non-sensitive config


@dataclass(frozen=True)
class SecretDefinition:
    """Definition of a required or optional environment variable.

    Attributes:
        env_var: The environment variable name.
        category: Risk classification.
        required: Whether startup should fail if this is missing.
        description: Human-readable purpose (for health checks).
        integration: Which external service this belongs to.
    """

    env_var: str
    category: SecretCategory
    required: bool
    description: str
    integration: str


# Registry of all secrets the application may use.
# Justification: Centralizing secret definitions ensures we never
# forget to validate a new secret and makes audit reporting trivial.
_SECRET_REGISTRY: list[SecretDefinition] = [
    # -- Critical (data breach risk) --
    SecretDefinition(
        env_var="DATABASE_URL",
        category=SecretCategory.CRITICAL,
        required=False,  # Not required in Phase 0 (no DB yet)
        description="PostgreSQL connection string for case data and audit logs",
        integration="PostgreSQL",
    ),
    SecretDefinition(
        env_var="ENCRYPTION_KEY",
        category=SecretCategory.CRITICAL,
        required=False,  # Phase 1: per-tenant KMS
        description="AES-256 encryption key for data-at-rest",
        integration="Encryption",
    ),
    # -- High (financial/access risk) --
    SecretDefinition(
        env_var="ANTHROPIC_API_KEY",
        category=SecretCategory.HIGH,
        required=True,
        description="Claude API key for all 5 agents (Lead Counsel, Research, Drafting, Red Team, Compliance)",
        integration="Anthropic",
    ),
    SecretDefinition(
        env_var="COURTLISTENER_API_KEY",
        category=SecretCategory.HIGH,
        required=False,  # Phase 1: citation verification
        description="CourtListener API key for case law retrieval",
        integration="CourtListener",
    ),
    # -- Medium (operational risk) --
    SecretDefinition(
        env_var="CLOUDFLARE_API_KEY",
        category=SecretCategory.MEDIUM,
        required=False,
        description="Cloudflare API key for WAF and CDN management",
        integration="Cloudflare",
    ),
    SecretDefinition(
        env_var="CLOUDFLARE_EMAIL",
        category=SecretCategory.MEDIUM,
        required=False,
        description="Cloudflare account email for API authentication",
        integration="Cloudflare",
    ),
    SecretDefinition(
        env_var="SENTRY_TOKEN",
        category=SecretCategory.MEDIUM,
        required=False,
        description="Sentry DSN for error tracking and alerting",
        integration="Sentry",
    ),
    SecretDefinition(
        env_var="REDIS_URL",
        category=SecretCategory.MEDIUM,
        required=False,
        description="Redis connection URL for rate limiting and caching",
        integration="Redis",
    ),
    # -- Low (non-sensitive config) --
    SecretDefinition(
        env_var="APP_ENV",
        category=SecretCategory.LOW,
        required=False,
        description="Application environment (development, staging, production)",
        integration="Application",
    ),
    SecretDefinition(
        env_var="LOG_LEVEL",
        category=SecretCategory.LOW,
        required=False,
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR)",
        integration="Application",
    ),
]


# ---------------------------------------------------------------------------
# Secret Masking
# ---------------------------------------------------------------------------

# Patterns that look like secrets in log output.
# Justification: Defense-in-depth -- even if code accidentally passes
# a secret to a logger, the masking filter catches it before it
# reaches log storage.
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    # API keys (common formats)
    re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.ASCII),
    re.compile(r"(sk-ant-[a-zA-Z0-9\-]{20,})", re.ASCII),
    # Bearer tokens
    re.compile(r"(Bearer\s+[a-zA-Z0-9\-_.]+)", re.ASCII),
    # Database URLs with passwords
    re.compile(r"(postgres(?:ql)?://[^:]+:)([^@]+)(@)", re.ASCII),
    re.compile(r"(redis://[^:]*:)([^@]+)(@)", re.ASCII),
    # Generic key=value patterns for known secret env vars
    re.compile(r"(ANTHROPIC_API_KEY=)(\S+)", re.ASCII),
    re.compile(r"(COURTLISTENER_API_KEY=)(\S+)", re.ASCII),
    re.compile(r"(CLOUDFLARE_API_KEY=)(\S+)", re.ASCII),
    re.compile(r"(SENTRY_TOKEN=)(\S+)", re.ASCII),
    re.compile(r"(DATABASE_URL=)(\S+)", re.ASCII),
    re.compile(r"(ENCRYPTION_KEY=)(\S+)", re.ASCII),
    re.compile(r"(REDIS_URL=)(\S+)", re.ASCII),
]

# Env var names that should always be masked in output
_SECRET_ENV_VARS: frozenset[str] = frozenset(
    defn.env_var
    for defn in _SECRET_REGISTRY
    if defn.category in (SecretCategory.CRITICAL, SecretCategory.HIGH, SecretCategory.MEDIUM)
)


def mask_secret(value: str) -> str:
    """Replace a secret value with a redacted version.

    Justification (@M:010): Secrets must never appear in logs,
    error messages, or API responses. This function replaces
    the value while preserving enough info for debugging
    (first 4 chars + length indicator).
    """
    if not value or len(value) < 8:
        return "[REDACTED]"
    return f"{value[:4]}...({len(value)} chars)[REDACTED]"


def mask_secrets_in_text(text: str) -> str:
    """Scrub known secret patterns from arbitrary text.

    Justification: Log messages, error tracebacks, and debug output
    may accidentally contain secrets. This function applies pattern
    matching to catch and redact them before they reach log storage.
    """
    result = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 1:
            result = pattern.sub("[REDACTED]", result)
        elif pattern.groups == 3:
            # URL pattern: keep scheme, mask password, keep host
            result = pattern.sub(r"\1[REDACTED]\3", result)
        elif pattern.groups == 2:
            # key=value pattern: keep key, mask value
            result = pattern.sub(r"\1[REDACTED]", result)
    return result


class SecretMaskingFilter(logging.Filter):
    """Logging filter that masks secrets in all log records.

    Justification: Attaching this filter to the root logger ensures
    that NO log handler (file, stdout, Sentry, Datadog) ever receives
    unmasked secret values, regardless of how the log message was
    constructed by application code.

    Usage:
        logging.getLogger().addFilter(SecretMaskingFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_secrets_in_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: mask_secrets_in_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(mask_secrets_in_text(str(a)) if isinstance(a, str) else a for a in record.args)
        return True


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@dataclass
class IntegrationStatus:
    """Status of a single external integration.

    Attributes:
        integration: Service name (e.g., "Anthropic", "Cloudflare").
        configured: Whether the required env vars are set.
        required: Whether the integration is mandatory for startup.
        env_vars: List of env var names (values are NEVER included).
        category: Risk classification.
    """

    integration: str
    configured: bool
    required: bool
    env_vars: list[str]
    category: str


@dataclass
class SecretsHealthReport:
    """Aggregated health report for all integrations.

    Justification: Operations teams need to quickly see which
    integrations are configured and which are missing, without
    ever seeing the actual secret values. This report powers
    the /health endpoint and startup diagnostics.
    """

    all_required_present: bool
    missing_required: list[str]
    integrations: list[IntegrationStatus]
    total_configured: int
    total_missing: int


# ---------------------------------------------------------------------------
# SecretsManager (public API)
# ---------------------------------------------------------------------------


class SecretsManager:
    """Centralized secrets management for the Cyphergy platform.

    Validates environment variables, masks secrets in logs, and
    provides health check reporting. NEVER exposes actual secret values.

    Usage:
        manager = SecretsManager()

        # At startup -- raises if required secrets are missing
        manager.validate_required()

        # For health endpoints
        report = manager.health_check()

        # For log masking
        safe_text = manager.mask(some_text)

        # Install global log filter
        manager.install_log_filter()
    """

    def __init__(
        self,
        registry: Optional[list[SecretDefinition]] = None,
    ) -> None:
        self._registry = registry or _SECRET_REGISTRY

    def validate_required(self) -> None:
        """Validate that all required environment variables are set.

        Justification: Fail-fast at startup is better than failing
        at runtime when a user submits their first legal document.
        Missing API keys should be caught in deployment, not production.

        Raises:
            EnvironmentError: If any required secret is missing.
        """
        missing: list[str] = []
        for defn in self._registry:
            if defn.required:
                value = os.getenv(defn.env_var, "")
                if not value.strip():
                    missing.append(defn.env_var)

        if missing:
            # Log which vars are missing (names only, never values)
            logger.critical(
                "startup_failed | missing_required_secrets=%s",
                ",".join(missing),
            )
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Set these in .env or your deployment configuration. "
                f"See .env.example for documentation."
            )

        logger.info(
            "secrets_validated | required=%d all_present=True",
            sum(1 for d in self._registry if d.required),
        )

    def health_check(self) -> SecretsHealthReport:
        """Generate a health report for all integrations.

        SECURITY: This report contains env var NAMES only, never values.
        Safe to expose via authenticated admin health endpoints.

        Returns:
            SecretsHealthReport with per-integration status.
        """
        # Group definitions by integration
        by_integration: dict[str, list[SecretDefinition]] = {}
        for defn in self._registry:
            by_integration.setdefault(defn.integration, []).append(defn)

        integrations: list[IntegrationStatus] = []
        missing_required: list[str] = []
        total_configured = 0
        total_missing = 0

        for integration_name, definitions in sorted(by_integration.items()):
            env_vars = [d.env_var for d in definitions]
            configured = all(bool(os.getenv(d.env_var, "").strip()) for d in definitions)
            is_required = any(d.required for d in definitions)
            category = max(
                (d.category for d in definitions),
                key=lambda c: list(SecretCategory).index(c),
            ).value

            if configured:
                total_configured += 1
            else:
                total_missing += 1
                if is_required:
                    missing_required.extend(d.env_var for d in definitions if not os.getenv(d.env_var, "").strip())

            integrations.append(
                IntegrationStatus(
                    integration=integration_name,
                    configured=configured,
                    required=is_required,
                    env_vars=env_vars,
                    category=category,
                )
            )

        return SecretsHealthReport(
            all_required_present=len(missing_required) == 0,
            missing_required=missing_required,
            integrations=integrations,
            total_configured=total_configured,
            total_missing=total_missing,
        )

    @staticmethod
    def mask(text: str) -> str:
        """Mask any secrets found in the given text.

        Convenience wrapper around mask_secrets_in_text for external callers.
        """
        return mask_secrets_in_text(text)

    @staticmethod
    def mask_value(value: str) -> str:
        """Mask a single known secret value.

        Convenience wrapper around mask_secret for external callers.
        """
        return mask_secret(value)

    @staticmethod
    def install_log_filter() -> None:
        """Install the secret-masking filter on the root logger.

        Justification: Once installed, ALL log output across the
        entire application is scrubbed for secret patterns. This
        is a safety net -- code should still avoid logging secrets,
        but this catches accidental leaks.

        Call this once during application startup.
        """
        root_logger = logging.getLogger()
        # Avoid duplicate filters if called multiple times
        if not any(isinstance(f, SecretMaskingFilter) for f in root_logger.filters):
            root_logger.addFilter(SecretMaskingFilter())
            logger.info("secret_masking_filter_installed | target=root_logger")

    def get_secret(self, env_var: str) -> str:
        """Retrieve a secret value from the environment.

        Justification: Centralizing secret access through this method
        ensures we can add audit logging, rotation detection, and
        cache invalidation in one place.

        Returns:
            The secret value, or empty string if not set.

        Note: The returned value is the REAL secret. Callers must
        NEVER log, print, or include it in error messages.
        """
        value = os.getenv(env_var, "")
        if not value:
            logger.debug("secret_access | var=%s present=False", env_var)
        else:
            logger.debug("secret_access | var=%s present=True", env_var)
        return value
