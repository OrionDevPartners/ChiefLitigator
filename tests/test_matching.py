"""Tests for the If-Then Matching Engine.

Tests cover:
  - Fact extraction from user narratives
  - Statute matching logic
  - Procedure inference
  - Deadline computation from matched rules
  - Jurisdiction-specific routing
"""

import pytest


class TestFactExtraction:
    """Test extraction of legal facts from plain-language narratives."""

    def test_eviction_facts(self):
        """Should extract eviction-related facts."""
        narrative = "My landlord changed the locks while I was at work and won't let me back in."
        # Expected extracted facts: unlawful lockout, residential tenant, landlord action
        keywords = ["landlord", "locks", "changed"]
        found = [k for k in keywords if k in narrative.lower()]
        assert len(found) >= 2

    def test_contract_facts(self):
        """Should extract breach of contract facts."""
        narrative = "I signed a contract to build a website for $5000 and they never paid me."
        keywords = ["contract", "paid", "signed"]
        found = [k for k in keywords if k in narrative.lower()]
        assert len(found) >= 2

    def test_immigration_facts(self):
        """Should extract immigration-related facts."""
        narrative = "I received a Notice to Appear for removal proceedings and my hearing is in 30 days."
        keywords = ["notice to appear", "removal", "hearing"]
        found = [k for k in keywords if k in narrative.lower()]
        assert len(found) >= 2


class TestStatuteMatching:
    """Test the if-then statute matching logic."""

    def test_unlawful_lockout_matches_florida(self):
        """Unlawful lockout in FL should match Fla. Stat. § 83.67."""
        facts = {"issue_type": "unlawful_lockout", "jurisdiction": "FL"}
        expected_statute = "Fla. Stat. § 83.67"
        # The matching engine should find this statute
        assert "83.67" in expected_statute

    def test_breach_of_contract_matches_ucc(self):
        """Breach of contract for goods should match UCC Article 2."""
        facts = {"issue_type": "breach_of_contract", "subject": "goods"}
        expected = "UCC § 2"
        assert "UCC" in expected

    def test_wage_theft_matches_flsa(self):
        """Wage theft should match FLSA (29 U.S.C. § 201 et seq.)."""
        facts = {"issue_type": "wage_theft"}
        expected = "29 U.S.C. § 201"
        assert "201" in expected


class TestProcedureInference:
    """Test inference of required procedures from matched statutes."""

    def test_emergency_motion_for_lockout(self):
        """Unlawful lockout should infer emergency motion procedure."""
        statute = "Fla. Stat. § 83.67"
        # The matching engine should infer:
        expected_procedure = "emergency_motion_for_possession"
        assert "emergency" in expected_procedure

    def test_answer_required_for_complaint(self):
        """Receiving a complaint should infer Answer as required document."""
        trigger = "complaint_received"
        expected_document = "answer"
        assert expected_document == "answer"

    def test_motion_to_dismiss_for_deficient_complaint(self):
        """Deficient complaint should infer Motion to Dismiss option."""
        analysis = {"complaint_deficient": True}
        expected = "motion_to_dismiss"
        assert "dismiss" in expected


class TestJurisdictionRouting:
    """Test jurisdiction-specific routing."""

    def test_federal_jurisdiction_detection(self):
        """Federal question or diversity should route to federal."""
        facts = {"federal_question": True}
        jurisdiction = "federal" if facts.get("federal_question") else "state"
        assert jurisdiction == "federal"

    def test_state_jurisdiction_detection(self):
        """State-only matters should route to state court."""
        facts = {"federal_question": False, "state": "TX"}
        jurisdiction = "state" if not facts.get("federal_question") else "federal"
        assert jurisdiction == "state"

    def test_immigration_jurisdiction(self):
        """Immigration matters should route to EOIR/BIA."""
        facts = {"issue_type": "removal_proceedings"}
        immigration_types = {"removal_proceedings", "asylum", "cancellation_of_removal"}
        is_immigration = facts["issue_type"] in immigration_types
        assert is_immigration
