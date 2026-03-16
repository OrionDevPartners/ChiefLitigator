"""Integration tests — real API calls, no mocks.

These tests hit the live Anthropic API and (optionally) CourtListener.
They are SKIPPED when ANTHROPIC_API_KEY is not set in the environment,
so they never block the regular test suite.

Run explicitly:
    ANTHROPIC_API_KEY=sk-... pytest -m integration -v
"""

from __future__ import annotations

import os
from datetime import date

import pytest

# ---------------------------------------------------------------------------
# Skip the entire module when the API key is absent
# ---------------------------------------------------------------------------

_HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _HAS_API_KEY,
        reason="ANTHROPIC_API_KEY not set — skipping integration tests",
    ),
]


# ---------------------------------------------------------------------------
# Test 1: LeadCounsel.invoke() — real LLM call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lead_counsel_invoke_returns_content() -> None:
    """LeadCounsel should return a non-empty response with legal content."""
    from src.agents.lead_counsel import LeadCounsel

    lead = LeadCounsel()
    response = await lead.invoke(
        "I was served with a civil lawsuit in federal court in Louisiana. What are my deadlines to respond?"
    )

    # Response must have substantive content
    assert response.content, "LeadCounsel returned empty content"
    assert len(response.content) > 50, (
        f"Response too short ({len(response.content)} chars) — expected substantive legal guidance"
    )

    # Confidence must be populated (the prompt asks about deadlines)
    assert 0.0 <= response.confidence <= 1.0

    # The agent should identify itself as lead_counsel
    assert response.role.value == "lead_counsel"

    # Token counts must be populated from a real API call
    assert response.input_tokens > 0, "input_tokens should be >0 for a real API call"
    assert response.output_tokens > 0, "output_tokens should be >0 for a real API call"
    assert response.elapsed_seconds > 0.0, "elapsed_seconds should be >0"


# ---------------------------------------------------------------------------
# Test 2: CitationVerifier.verify() — real CourtListener call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_verifier_brown_v_board() -> None:
    """Verify Brown v. Board of Education via the full 5-step chain.

    CourtListener availability varies, so we accept VERIFIED or PARTIAL.
    UNVERIFIED is also acceptable if CourtListener is down — the point is
    that the chain runs to completion without crashing.
    """
    from src.verification.citation_chain import CitationVerifier, VerificationStatus

    verifier = CitationVerifier()
    result = await verifier.verify(
        citation="Brown v. Board of Education, 347 U.S. 483 (1954)",
        claimed_holding="Separate educational facilities are inherently unequal",
    )

    # The chain must complete without raising
    assert result.citation, "citation field should echo back the input"
    assert result.status in (
        VerificationStatus.VERIFIED,
        VerificationStatus.PARTIAL,
        VerificationStatus.UNVERIFIED,
    ), f"Unexpected status: {result.status}"

    # At least some steps should have been attempted
    total_steps = len(result.steps_passed) + len(result.steps_failed)
    assert total_steps > 0, "No verification steps were executed"

    # Details should provide a human-readable explanation
    assert isinstance(result.details, str)

    # Confidence should be between 0 and 1
    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Test 3: DeadlineCalculator.compute() — full API path exercise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deadline_calculator_full_path() -> None:
    """Exercise DeadlineCalculator.compute() through the same path the API uses.

    This mirrors the exact flow in POST /api/v1/compute-deadline:
    parse enums, call compute(), validate the result.
    """
    from src.legal.deadline_calc import (
        DeadlineCalculator,
        DeadlineType,
        Jurisdiction,
        ServiceMethod,
    )

    calc = DeadlineCalculator()

    # Federal answer deadline served by mail — the API parses these from strings
    event = date(2026, 4, 1)
    result = calc.compute(
        event_date=event,
        deadline_type=DeadlineType.ANSWER,
        jurisdiction=Jurisdiction.FEDERAL,
        service_method=ServiceMethod.MAIL,
    )

    # Deadline must be after the event date
    assert result.deadline_date > result.event_date, (
        f"Deadline {result.deadline_date} should be after event {result.event_date}"
    )

    # Federal answer = 21 days base (FRCP 12(a)(1)(A)(i))
    assert result.days_allowed == 21, f"Expected 21 days for federal answer, got {result.days_allowed}"

    # Mail service adds 3 days (FRCP 6(d))
    assert any("mail" in adj.lower() for adj in result.adjustments), (
        "Expected a mail service extension adjustment in the audit trail"
    )

    # Rule citation must reference FRCP
    assert "FRCP" in result.rule_citation or "Fed" in result.rule_citation, (
        f"Expected FRCP citation, got: {result.rule_citation}"
    )

    # Conservative flag must be True (Cyphergy always picks earlier deadline)
    assert result.conservative is True

    # Confidence should be 'high' for a well-defined federal deadline
    assert result.confidence in ("high", "verify")

    # Jurisdiction and type should echo back correctly
    assert result.jurisdiction == Jurisdiction.FEDERAL
    assert result.deadline_type == DeadlineType.ANSWER
    assert result.service_method == ServiceMethod.MAIL
