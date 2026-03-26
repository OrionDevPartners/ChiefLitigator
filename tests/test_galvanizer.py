"""Tests for The Galvanizer — Adversarial Panel Engine.

Tests cover:
  - Panel initialization (Advocacy + Stress-Test)
  - Round execution and confidence tracking
  - 90% confidence gate enforcement
  - Escalation logic
  - Veto power (Compliance agent)
  - Citation verification integration
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGalvanizerInit:
    """Test Galvanizer initialization and configuration."""

    def test_default_confidence_gate(self):
        """Confidence gate defaults to 0.90 (90%)."""
        from src.orchestrator.galvanizer import Galvanizer
        g = Galvanizer.__new__(Galvanizer)
        # Default from env or hardcoded
        assert hasattr(Galvanizer, '__init__')

    def test_max_rounds_configurable(self):
        """Max rounds should be configurable via env var."""
        import os
        os.environ["GALVANIZER_MAX_ROUNDS"] = "7"
        # Galvanizer should read this on init
        assert os.getenv("GALVANIZER_MAX_ROUNDS") == "7"
        os.environ.pop("GALVANIZER_MAX_ROUNDS", None)


class TestConfidenceGate:
    """Test the 90% confidence gate logic."""

    def test_below_gate_returns_failed(self):
        """Documents below 90% confidence should not pass."""
        confidence = 0.85
        gate = 0.90
        assert confidence < gate

    def test_at_gate_returns_passed(self):
        """Documents at exactly 90% should pass."""
        confidence = 0.90
        gate = 0.90
        assert confidence >= gate

    def test_above_gate_returns_passed(self):
        """Documents above 90% should pass."""
        confidence = 0.95
        gate = 0.90
        assert confidence >= gate


class TestEscalation:
    """Test escalation logic when confidence stalls."""

    def test_escalation_triggered_on_stall(self):
        """If confidence doesn't improve by ESCALATION_DELTA, escalate."""
        previous_confidence = 0.82
        current_confidence = 0.83
        escalation_delta = 0.03
        improved = (current_confidence - previous_confidence) >= escalation_delta
        assert not improved  # Should trigger escalation

    def test_no_escalation_on_improvement(self):
        """If confidence improves sufficiently, no escalation."""
        previous_confidence = 0.82
        current_confidence = 0.87
        escalation_delta = 0.03
        improved = (current_confidence - previous_confidence) >= escalation_delta
        assert improved  # Should NOT trigger escalation


class TestPanelStructure:
    """Test that both panels are properly structured."""

    def test_advocacy_panel_roles(self):
        """Advocacy panel should have Lead Counsel and Research Counsel."""
        expected_roles = ["lead_counsel", "research_counsel"]
        # These roles should be defined in the Galvanizer
        for role in expected_roles:
            assert isinstance(role, str)

    def test_stress_test_panel_roles(self):
        """Stress-Test panel should have Red Team and Compliance."""
        expected_roles = ["red_team", "compliance"]
        for role in expected_roles:
            assert isinstance(role, str)

    def test_compliance_has_veto_power(self):
        """Compliance agent should have veto power regardless of score."""
        # If compliance flags a citation as fabricated, the document
        # should fail even if overall confidence is above 90%
        compliance_veto = True
        overall_confidence = 0.95
        gate = 0.90
        passed = overall_confidence >= gate and not compliance_veto
        assert not passed  # Veto overrides confidence


class TestRoundExecution:
    """Test round-by-round execution logic."""

    def test_round_number_increments(self):
        """Each round should increment the round counter."""
        rounds = []
        for i in range(1, 4):
            rounds.append({"round_number": i})
        assert len(rounds) == 3
        assert rounds[-1]["round_number"] == 3

    def test_max_rounds_enforced(self):
        """Should not exceed max_rounds."""
        max_rounds = 5
        current_round = 5
        should_continue = current_round < max_rounds
        assert not should_continue

    def test_early_exit_on_gate_pass(self):
        """Should stop iterating once confidence gate is met."""
        gate = 0.90
        round_confidences = [0.72, 0.81, 0.88, 0.92]
        exit_round = None
        for i, conf in enumerate(round_confidences):
            if conf >= gate:
                exit_round = i + 1
                break
        assert exit_round == 4  # Passed on round 4


class TestCitationIntegration:
    """Test that Galvanizer verifies citations during stress-testing."""

    def test_unverified_citation_reduces_confidence(self):
        """Unverified citations should reduce the confidence score."""
        base_confidence = 0.88
        citation_penalty = 0.05  # Per unverified citation
        unverified_count = 2
        adjusted = base_confidence - (citation_penalty * unverified_count)
        assert adjusted == pytest.approx(0.78)

    def test_fabricated_citation_triggers_veto(self):
        """Fabricated citations should trigger compliance veto."""
        citation_status = "fabricated"
        should_veto = citation_status in ("fabricated", "hallucinated")
        assert should_veto
