"""Pydantic request/response models for the Cyphergy API.

Defines typed contracts for every endpoint. All models use strict
validation to reject malformed input at the boundary, before it reaches
agents, deadline calculators, or verification chains.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# POST /api/v1/chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat message routed to Lead Counsel."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="The user's legal question or request.",
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional jurisdiction context (e.g., 'federal', 'louisiana').",
    )


class ChatResponse(BaseModel):
    """Response from the Lead Counsel agent."""

    content: str = Field(description="The agent's textual response.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent's self-assessed confidence (0.0-1.0).",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="Legal citations referenced in the response.",
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Operational flags (e.g., 'needs_verification', 'deadline_critical').",
    )
    agent_id: str = Field(description="Unique identifier of the responding agent instance.")
    elapsed_seconds: float = Field(description="Wall-clock time for the LLM call.")
    input_tokens: int = Field(default=0, description="Tokens consumed in the prompt.")
    output_tokens: int = Field(default=0, description="Tokens generated in the response.")


# ---------------------------------------------------------------------------
# POST /api/v1/verify-citation
# ---------------------------------------------------------------------------


class VerifyCitationRequest(BaseModel):
    """Request to verify a single legal citation."""

    citation: str = Field(
        ...,
        min_length=1,
        max_length=1_000,
        description="The legal citation to verify (e.g., '347 U.S. 483').",
    )
    claimed_holding: Optional[str] = Field(
        default=None,
        max_length=10_000,
        description="What the citing document claims this case holds.",
    )


class VerifyCitationResponse(BaseModel):
    """Result of the 5-step citation verification chain."""

    citation: str = Field(description="The citation that was verified.")
    status: str = Field(description="Verification status: verified, unverified, partial, or error.")
    steps_passed: list[str] = Field(default_factory=list, description="Steps that passed.")
    steps_failed: list[str] = Field(default_factory=list, description="Steps that failed.")
    external_source: Optional[str] = Field(
        default=None,
        description="Where opinion text was retrieved from.",
    )
    holding_summary: Optional[str] = Field(
        default=None,
        description="What the case actually holds (from external text).",
    )
    holding_match: Optional[bool] = Field(
        default=None,
        description="Whether the claimed holding matches the actual holding.",
    )
    good_law: Optional[bool] = Field(
        default=None,
        description="Whether the case is still good law.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Verification confidence score.",
    )
    details: str = Field(default="", description="Human-readable explanation.")


# ---------------------------------------------------------------------------
# POST /api/v1/compute-deadline
# ---------------------------------------------------------------------------


class ComputeDeadlineRequest(BaseModel):
    """Request to compute a jurisdiction-aware filing deadline."""

    event_date: str = Field(
        ...,
        description="The triggering event date in YYYY-MM-DD format.",
    )
    deadline_type: str = Field(
        ...,
        description=(
            "Category of deadline: answer, motion_to_dismiss, "
            "discovery_response, appeal_notice, or motion_response."
        ),
    )
    jurisdiction: str = Field(
        ...,
        description=(
            "Governing jurisdiction: federal, louisiana, california, "
            "texas, new_york, or florida."
        ),
    )
    service_method: Optional[str] = Field(
        default=None,
        description=(
            "How papers were served: personal, mail, electronic, "
            "or certified_mail. Defaults to personal."
        ),
    )

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, v: str) -> str:
        """Ensure event_date is a valid ISO 8601 date string."""
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"event_date must be a valid YYYY-MM-DD date, got '{v}'")
        return v


class ComputeDeadlineResponse(BaseModel):
    """Result of a deadline computation."""

    event_date: str = Field(description="The triggering event date (YYYY-MM-DD).")
    deadline_date: str = Field(description="Computed filing deadline (YYYY-MM-DD).")
    jurisdiction: str = Field(description="The governing jurisdiction.")
    deadline_type: str = Field(description="The type of deadline computed.")
    service_method: str = Field(description="The service method used.")
    days_allowed: int = Field(description="Base number of days for this deadline type.")
    adjustments: list[str] = Field(
        default_factory=list,
        description="Audit trail of all adjustments (weekends, holidays, service extensions).",
    )
    rule_citation: str = Field(description="The governing rule citation.")
    confidence: str = Field(description="Confidence level: 'high' or 'verify'.")
    warning: Optional[str] = Field(
        default=None,
        description="Additional warning about the deadline computation.",
    )
    conservative: bool = Field(
        description="Whether this is a conservative (earlier) deadline.",
    )


# ---------------------------------------------------------------------------
# Health check responses
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str = Field(default="ok")
    agents: int = Field(default=5)
    tests_passing: int = Field(default=33)


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    ready: bool
    anthropic_api_key_set: bool
    llm_provider: str
    detail: str = Field(default="")


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standardized error response body."""

    error: str = Field(description="Human-readable error message.")
    detail: Optional[str] = Field(
        default=None,
        description="Additional error context (never PII).",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for correlation.",
    )
