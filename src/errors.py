"""Centralized error hierarchy for the Cyphergy Legal AI platform.

Every domain-specific error inherits from CyphergyError, which carries
a default HTTP status code. The API layer registers exception handlers
for each subclass so that:
- Users always get a safe, human-readable message.
- Stack traces never leak to the client.
- PII is never included in error payloads or log messages (@M:010).

Usage::

    from src.errors import LLMProviderError

    raise LLMProviderError("Anthropic API returned 500")
"""

from __future__ import annotations


class CyphergyError(Exception):
    """Base exception for all Cyphergy errors.

    Attributes
    ----------
    status_code : int
        HTTP status code to return to the client.
    safe_message : str
        User-facing message that is safe to expose. Never contains PII,
        stack traces, or internal implementation details.
    """

    status_code: int = 500
    safe_message: str = "An unexpected error occurred. Please try again."

    def __init__(self, detail: str = "", *, safe_message: str | None = None) -> None:
        """Initialize with an internal-only detail string.

        Parameters
        ----------
        detail:
            Technical detail for server-side logging. Never exposed to
            the user.
        safe_message:
            Override the default user-facing message for this instance.
        """
        super().__init__(detail)
        if safe_message is not None:
            self.safe_message = safe_message


class LLMProviderError(CyphergyError):
    """Anthropic/Bedrock API is unreachable or returned an error.

    Raised when the LLM provider (Anthropic direct or AWS Bedrock)
    fails to respond, times out, or returns a non-retryable error.
    The API layer returns 503 so load balancers can route around the
    failure, and the user sees a reassuring message about data safety.
    """

    status_code = 503
    safe_message = "Legal AI service temporarily unavailable. Your case data is safe. Please try again in a moment."


class CitationVerificationError(CyphergyError):
    """CourtListener API failed during citation verification.

    Raised when external citation verification sources (CourtListener,
    Google Scholar) are unreachable or return errors. The API layer
    returns 502 (bad gateway) and the citation is marked PARTIAL rather
    than failing the entire request.
    """

    status_code = 502
    safe_message = (
        "External citation verification service is temporarily unavailable. Citations will be marked as unverified."
    )


class RateLimitExceeded(CyphergyError):
    """User or tenant has exceeded their rate limit.

    Raised by the rate limiting middleware when any of the 4 rate limit
    layers (per-IP, per-user, per-tenant, global) is exceeded. The API
    layer returns 429 with a Retry-After header.
    """

    status_code = 429
    safe_message = "Too many requests. Please wait before trying again."

    def __init__(
        self,
        detail: str = "",
        *,
        retry_after: int = 60,
        layer: str = "unknown",
        safe_message: str | None = None,
    ) -> None:
        super().__init__(detail, safe_message=safe_message)
        self.retry_after = retry_after
        self.layer = layer


class AuthenticationError(CyphergyError):
    """JWT token is invalid, expired, or missing.

    Raised when the JWT authentication middleware cannot validate the
    bearer token. The API layer returns 401 and never reveals whether
    the token was expired, malformed, or missing -- all cases return
    the same generic message to prevent enumeration attacks.
    """

    status_code = 401
    safe_message = "Authentication required. Please sign in and try again."


class AgentError(CyphergyError):
    """A specific agent in the 5-agent pipeline failed.

    Used by the orchestrator to track which agent failed without
    blocking the remaining agents. The role is safe to log; user
    data is never attached.
    """

    status_code = 500
    safe_message = "One of our legal analysis agents encountered an issue."

    def __init__(
        self,
        detail: str = "",
        *,
        agent_role: str = "unknown",
        safe_message: str | None = None,
    ) -> None:
        super().__init__(detail, safe_message=safe_message)
        self.agent_role = agent_role


class ValidationError(CyphergyError):
    """Input validation failed beyond what Pydantic catches.

    Raised for domain-specific validation (e.g., invalid jurisdiction
    code, unsupported deadline type) that passes Pydantic's structural
    validation but fails business-rule validation.
    """

    status_code = 400
    safe_message = "Invalid input. Please check your request and try again."
