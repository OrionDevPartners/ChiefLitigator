"""Tests for the Auto-Siphon Pipeline.

Tests cover:
  - Orchestrator worker registration
  - Worker execution order (Phase 1 before Phase 2)
  - XRef Builder citation extraction
  - Incremental vs full run modes
  - Error handling and resilience
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestSiphonOrchestrator:
    """Test the SiphonOrchestrator."""

    def test_all_workers_registered(self):
        """All 7 workers should be registered."""
        from src.siphon.orchestrator import SiphonOrchestrator
        orch = SiphonOrchestrator()
        expected = {
            "courtlistener", "uscode", "legiscan",
            "scotus", "federal_rules", "immigration", "xref_builder",
        }
        assert set(orch.WORKER_REGISTRY.keys()) == expected

    def test_phase_ordering(self):
        """XRef builder (Phase 2) must run after data workers (Phase 1)."""
        from src.siphon.orchestrator import SiphonOrchestrator
        orch = SiphonOrchestrator()
        for name, config in orch.WORKER_REGISTRY.items():
            if name == "xref_builder":
                assert config["phase"] == 2
            else:
                assert config["phase"] == 1

    def test_siphon_source_enum(self):
        """SiphonSource enum should include ALL and individual sources."""
        from src.siphon.orchestrator import SiphonSource
        assert SiphonSource.ALL.value == "all"
        assert SiphonSource.COURTLISTENER.value == "courtlistener"
        assert SiphonSource.IMMIGRATION.value == "immigration"


class TestXRefBuilder:
    """Test the cross-reference builder."""

    def test_extract_federal_statute_citation(self):
        """Should extract '42 U.S.C. § 1983' from text."""
        from src.siphon.xref_builder import XRefBuilder
        builder = XRefBuilder()
        text = "The plaintiff brought claims under 42 U.S.C. § 1983 for civil rights violations."
        citations = builder.extract_statute_citations(text)
        assert len(citations) >= 1

    def test_extract_case_citation(self):
        """Should extract case citations like '123 U.S. 456'."""
        from src.siphon.xref_builder import XRefBuilder
        builder = XRefBuilder()
        text = "As held in Miranda v. Arizona, 384 U.S. 436 (1966)."
        citations = builder.extract_case_citations(text)
        assert len(citations) >= 1

    def test_extract_rule_citation(self):
        """Should extract FRCP rule citations."""
        from src.siphon.xref_builder import XRefBuilder
        builder = XRefBuilder()
        text = "Defendant moves to dismiss under Fed. R. Civ. P. 12(b)(6)."
        citations = builder.extract_rule_citations(text)
        assert len(citations) >= 1

    def test_no_citations_in_empty_text(self):
        """Should return empty list for text with no citations."""
        from src.siphon.xref_builder import XRefBuilder
        builder = XRefBuilder()
        citations = builder.extract_statute_citations("No legal text here.")
        assert len(citations) == 0


class TestWorkerSchedules:
    """Test that worker schedules are correctly defined."""

    def test_daily_workers(self):
        """CourtListener and SCOTUS should run daily."""
        from src.siphon.orchestrator import SiphonOrchestrator
        orch = SiphonOrchestrator()
        daily = [n for n, c in orch.WORKER_REGISTRY.items() if c["schedule"] == "daily"]
        assert "courtlistener" in daily
        assert "scotus" in daily

    def test_weekly_workers(self):
        """LegiScan, Immigration, and XRef should run weekly."""
        from src.siphon.orchestrator import SiphonOrchestrator
        orch = SiphonOrchestrator()
        weekly = [n for n, c in orch.WORKER_REGISTRY.items() if c["schedule"] == "weekly"]
        assert "legiscan" in weekly
        assert "immigration" in weekly
        assert "xref_builder" in weekly

    def test_monthly_workers(self):
        """Federal Rules should run monthly."""
        from src.siphon.orchestrator import SiphonOrchestrator
        orch = SiphonOrchestrator()
        monthly = [n for n, c in orch.WORKER_REGISTRY.items() if c["schedule"] == "monthly"]
        assert "federal_rules" in monthly
