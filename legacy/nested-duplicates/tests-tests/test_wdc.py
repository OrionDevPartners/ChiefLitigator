"""Tests for the WDC v2.0 scoring engine.

All tests are pure unit tests — no LLM calls. They construct
WDCScore objects directly and verify engine behavior.
"""

from __future__ import annotations

import math

import pytest

from src.agents.base_agent import AgentRole, WDCScore
from src.config.settings import Settings
from src.orchestrator.wdc import WDCEngine, WDCVerdict

# ── Helpers ──────────────────────────────────────────────────────────


def _make_settings(**overrides: object) -> Settings:
    """Create a Settings instance with test defaults.

    Overrides are applied on top of the base test config.
    """
    defaults = {
        "anthropic_api_key": "test-key-not-real",
        "llm_provider": "anthropic",
        "llm_model": "claude-opus-4-6",
        "llm_temperature": 0.0,
        "weight_lead_counsel": 0.30,
        "weight_research_counsel": 0.25,
        "weight_drafting_counsel": 0.15,
        "weight_red_team": 0.20,
        "weight_compliance_counsel": 0.10,
        "wdc_certification_threshold": 8.5,
        "wdc_notes_threshold": 7.0,
        "wdc_revision_threshold": 5.0,
        "wdc_max_revision_cycles": 3,
        "external_retrieval_required": True,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_score(
    role: AgentRole,
    score: float,
    weight: float,
    reasoning: str = "Test reasoning",
    flags: list[str] | None = None,
    veto: bool = False,
    veto_reason: str | None = None,
) -> WDCScore:
    """Build a WDCScore for testing."""
    return WDCScore(
        score=score,
        reasoning=reasoning,
        flags=flags or [],
        veto=veto,
        veto_reason=veto_reason,
        scorer_role=role,
        scorer_weight=weight,
    )


def _all_scores(score_value: float) -> list[WDCScore]:
    """Create a full set of 5 agent scores, all with the same value."""
    return [
        _make_score(AgentRole.LEAD_COUNSEL, score_value, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, score_value, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, score_value, 0.15),
        _make_score(AgentRole.RED_TEAM, score_value, 0.20),
        _make_score(AgentRole.COMPLIANCE_COUNSEL, score_value, 0.10),
    ]


# ── Test 1: All high scores -> CERTIFIED ────────────────────────────


def test_all_high_scores_certified() -> None:
    """When all agents score 9.0+, the verdict should be CERTIFIED."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 9.5, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, 9.0, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, 9.2, 0.15),
        _make_score(AgentRole.RED_TEAM, 8.8, 0.20),
        _make_score(AgentRole.COMPLIANCE_COUNSEL, 9.0, 0.10),
    ]

    result = engine.score(scores)

    assert result.verdict == WDCVerdict.CERTIFIED
    assert result.composite_score >= 8.5
    assert result.vetoed is False
    assert result.veto_reason is None
    assert result.revision_feedback is None


# ── Test 2: Mixed scores -> CERTIFIED_WITH_NOTES ────────────────────


def test_mixed_scores_certified_with_notes() -> None:
    """Mixed scores producing composite between 7.0 and 8.5
    should yield CERTIFIED_WITH_NOTES."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    # Weighted: 9.0*0.30 + 7.0*0.25 + 8.0*0.15 + 6.5*0.20 + 8.0*0.10
    # = 2.70 + 1.75 + 1.20 + 1.30 + 0.80 = 7.75
    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 9.0, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, 7.0, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, 8.0, 0.15),
        _make_score(AgentRole.RED_TEAM, 6.5, 0.20),
        _make_score(AgentRole.COMPLIANCE_COUNSEL, 8.0, 0.10),
    ]

    result = engine.score(scores)

    assert result.verdict == WDCVerdict.CERTIFIED_WITH_NOTES
    assert 7.0 <= result.composite_score < 8.5
    assert result.vetoed is False


# ── Test 3: Low scores -> REVISION_REQUIRED ─────────────────────────


def test_low_scores_revision_required() -> None:
    """Composite between 5.0 and 7.0 yields REVISION_REQUIRED."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = _all_scores(6.0)
    result = engine.score(scores)

    assert result.verdict == WDCVerdict.REVISION_REQUIRED
    assert 5.0 <= result.composite_score < 7.0
    assert result.revision_feedback is not None
    assert len(result.revision_feedback) > 0


# ── Test 4: Very low scores -> REJECTED ─────────────────────────────


def test_very_low_scores_rejected() -> None:
    """Composite below 5.0 yields REJECTED."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = _all_scores(3.0)
    result = engine.score(scores)

    assert result.verdict == WDCVerdict.REJECTED
    assert result.composite_score < 5.0
    assert result.revision_feedback is not None


# ── Test 5: Compliance veto overrides high composite -> VETOED ───────


def test_compliance_veto_overrides_high_score() -> None:
    """A Compliance veto must override any composite score, even 10.0."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 10.0, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, 10.0, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, 10.0, 0.15),
        _make_score(AgentRole.RED_TEAM, 10.0, 0.20),
        _make_score(
            AgentRole.COMPLIANCE_COUNSEL,
            10.0,
            0.10,
            veto=True,
            veto_reason="Procedural error: motion filed after deadline",
        ),
    ]

    result = engine.score(scores)

    assert result.verdict == WDCVerdict.VETOED
    assert result.vetoed is True
    assert result.veto_reason is not None
    assert "deadline" in result.veto_reason.lower()
    # Composite is still computed (for the record) but verdict is VETOED
    assert result.composite_score == 10.0


# ── Test 6: Weights sum to 1.0 ──────────────────────────────────────


def test_weights_sum_to_one() -> None:
    """Agent weights from settings must sum to exactly 1.0."""
    settings = _make_settings()
    assert math.isclose(settings.total_weight, 1.0, rel_tol=1e-6)


def test_invalid_weights_raises() -> None:
    """Engine initialization with weights that don't sum to 1.0 must raise."""
    settings = _make_settings(weight_lead_counsel=0.50)
    # Weights now sum to 0.50 + 0.25 + 0.15 + 0.20 + 0.10 = 1.20
    with pytest.raises(ValueError, match="must sum to 1.0"):
        WDCEngine(settings=settings)


# ── Test 7: Missing agent score raises error ─────────────────────────


def test_missing_agent_score_raises() -> None:
    """Submitting fewer than 5 agent scores must raise ValueError."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    # Only 4 scores — missing Compliance
    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 9.0, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, 9.0, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, 9.0, 0.15),
        _make_score(AgentRole.RED_TEAM, 9.0, 0.20),
    ]

    with pytest.raises(ValueError, match="Missing agent scores"):
        engine.score(scores)


# ── Test 8: Exact boundary — 8.5 is CERTIFIED ───────────────────────


def test_exact_certification_boundary() -> None:
    """A composite of exactly 8.5 should be CERTIFIED (>=, not >)."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = _all_scores(8.5)
    result = engine.score(scores)

    assert result.verdict == WDCVerdict.CERTIFIED
    assert math.isclose(result.composite_score, 8.5, rel_tol=1e-4)


# ── Test 9: Exact boundary — 7.0 is CERTIFIED_WITH_NOTES ────────────


def test_exact_notes_boundary() -> None:
    """A composite of exactly 7.0 should be CERTIFIED_WITH_NOTES."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = _all_scores(7.0)
    result = engine.score(scores)

    assert result.verdict == WDCVerdict.CERTIFIED_WITH_NOTES


# ── Test 10: Exact boundary — 5.0 is REVISION_REQUIRED ──────────────


def test_exact_revision_boundary() -> None:
    """A composite of exactly 5.0 should be REVISION_REQUIRED."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = _all_scores(5.0)
    result = engine.score(scores)

    assert result.verdict == WDCVerdict.REVISION_REQUIRED


# ── Test 11: Weighted score calculation is correct ───────────────────


def test_weighted_score_calculation() -> None:
    """Verify the weighted composite is computed correctly."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 10.0, 0.30),  # 3.00
        _make_score(AgentRole.RESEARCH_COUNSEL, 8.0, 0.25),  # 2.00
        _make_score(AgentRole.DRAFTING_COUNSEL, 6.0, 0.15),  # 0.90
        _make_score(AgentRole.RED_TEAM, 7.0, 0.20),  # 1.40
        _make_score(AgentRole.COMPLIANCE_COUNSEL, 9.0, 0.10),  # 0.90
    ]

    result = engine.score(scores)

    expected_composite = (10.0 * 0.30) + (8.0 * 0.25) + (6.0 * 0.15) + (7.0 * 0.20) + (9.0 * 0.10)
    assert math.isclose(result.composite_score, expected_composite, rel_tol=1e-4)

    # Verify individual weighted scores
    assert math.isclose(result.weighted_scores["lead_counsel"], 3.0, rel_tol=1e-4)
    assert math.isclose(result.weighted_scores["research_counsel"], 2.0, rel_tol=1e-4)
    assert math.isclose(result.weighted_scores["drafting_counsel"], 0.9, rel_tol=1e-4)
    assert math.isclose(result.weighted_scores["red_team"], 1.4, rel_tol=1e-4)
    assert math.isclose(result.weighted_scores["compliance_counsel"], 0.9, rel_tol=1e-4)


# ── Test 12: Notes are collected from flagged agents ─────────────────


def test_notes_collected_from_flags() -> None:
    """Agents with flags should contribute to the result notes."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 9.0, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, 9.0, 0.25, flags=["citation_unverified"]),
        _make_score(AgentRole.DRAFTING_COUNSEL, 9.0, 0.15),
        _make_score(AgentRole.RED_TEAM, 9.0, 0.20, flags=["deadline_risk", "jurisdiction_unclear"]),
        _make_score(AgentRole.COMPLIANCE_COUNSEL, 9.0, 0.10),
    ]

    result = engine.score(scores)

    assert result.verdict == WDCVerdict.CERTIFIED
    assert len(result.notes) >= 2
    assert any("citation_unverified" in note for note in result.notes)
    assert any("deadline_risk" in note for note in result.notes)


# ── Test 13: Duplicate role raises error ─────────────────────────────


def test_duplicate_role_raises() -> None:
    """Submitting two scores for the same role must raise ValueError."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 9.0, 0.30),
        _make_score(AgentRole.LEAD_COUNSEL, 8.0, 0.30),  # duplicate
        _make_score(AgentRole.RESEARCH_COUNSEL, 9.0, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, 9.0, 0.15),
        _make_score(AgentRole.RED_TEAM, 9.0, 0.20),
        _make_score(AgentRole.COMPLIANCE_COUNSEL, 9.0, 0.10),
    ]

    with pytest.raises(ValueError, match="Expected exactly"):
        engine.score(scores)


# ── Test 14: External retrieval hard constraint ──────────────────────


def test_external_retrieval_hard_constraint() -> None:
    """Setting external_retrieval_required=False must raise."""
    with pytest.raises(ValueError, match="HARD CONSTRAINT"):
        _make_settings(external_retrieval_required=False)


# ── Test 15: Veto without reason provides default ────────────────────


def test_veto_without_reason_has_default() -> None:
    """A veto with no explicit reason should still produce a veto_reason."""
    settings = _make_settings()
    engine = WDCEngine(settings=settings)

    scores = [
        _make_score(AgentRole.LEAD_COUNSEL, 10.0, 0.30),
        _make_score(AgentRole.RESEARCH_COUNSEL, 10.0, 0.25),
        _make_score(AgentRole.DRAFTING_COUNSEL, 10.0, 0.15),
        _make_score(AgentRole.RED_TEAM, 10.0, 0.20),
        _make_score(
            AgentRole.COMPLIANCE_COUNSEL,
            10.0,
            0.10,
            veto=True,
            veto_reason=None,
        ),
    ]

    result = engine.score(scores)

    assert result.verdict == WDCVerdict.VETOED
    assert result.veto_reason is not None
    assert "no reason provided" in result.veto_reason.lower()
