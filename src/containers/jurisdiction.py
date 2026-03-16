"""Jurisdiction Container — Self-contained AI + Data unit for a single legal jurisdiction.

Novel architecture by Bo Pennington.

Each container encapsulates:
1. A jurisdiction's complete legal corpus (statutes, case law, court rules, bar rules)
2. AI agents that live WITH the data (data-resident, not API-remote)
3. Dual-brain consensus: Opus 4.6 + Llama Scout + Cohere must AGREE on legal output
4. Persistent context memory that learns from WDC debates
5. MCP interface for inter-container communication

The container trains over time from:
- WDC debate transcripts (what the panel agreed on)
- Case outcomes (E14 outcome-based learning)
- Citation verification results (what was correct vs incorrect)
- User corrections and feedback

Eventually each jurisdiction container's benchmark will outperform
any general-purpose AI in that specific legal domain.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field

from src.providers.model_router import (
    ModelRouter,
    ModelRole,
    DualBrainResult,
    run_dual_brain_check,
)
from src.providers.llm_provider import get_provider

logger = logging.getLogger("cyphergy.containers.jurisdiction")


# ---------------------------------------------------------------------------
# Jurisdiction Definitions
# ---------------------------------------------------------------------------


class JurisdictionType(str, Enum):
    """Types of legal jurisdictions."""

    STATE = "state"
    FEDERAL = "federal"
    TERRITORY = "territory"
    TRIBAL = "tribal"
    MILITARY = "military"


class JurisdictionConfig(BaseModel):
    """Configuration for a jurisdiction container."""

    code: str = Field(description="Jurisdiction code (e.g., 'LA', 'CA', 'FED')")
    name: str = Field(description="Full name (e.g., 'Louisiana', 'Federal')")
    type: JurisdictionType = Field(description="Type of jurisdiction")

    # Legal corpus identifiers
    statute_source: str = Field(
        default="",
        description="API/data source for statutes (e.g., CourtListener, state legislature API)",
    )
    case_law_source: str = Field(
        default="courtlistener",
        description="Source for case law",
    )
    court_rules_source: str = Field(
        default="",
        description="Source for court rules and local rules",
    )

    # Model configuration — overridable per jurisdiction via env
    primary_model: str = Field(
        default="",
        description="Override primary model for this jurisdiction (env: MODEL_JURISDICTION_{CODE}_PRIMARY)",
    )
    scout_model: str = Field(
        default="",
        description="Override scout model (env: MODEL_JURISDICTION_{CODE}_SCOUT)",
    )
    cohere_model: str = Field(
        default="",
        description="Override cohere model (env: MODEL_JURISDICTION_{CODE}_COHERE)",
    )

    # Training state
    wdc_debates_ingested: int = Field(default=0, description="Number of WDC debates used for training")
    case_outcomes_ingested: int = Field(default=0, description="Number of case outcomes ingested")
    benchmark_score: float = Field(default=0.0, description="Current benchmark accuracy score")
    last_training_at: Optional[str] = Field(default=None, description="Last training timestamp")


# ---------------------------------------------------------------------------
# Container Context Memory
# ---------------------------------------------------------------------------


class ContainerMemory(BaseModel):
    """Persistent context memory for a jurisdiction container.

    This is what makes the container learn over time.
    Stored in Aurora PostgreSQL per-jurisdiction.
    """

    jurisdiction_code: str
    # Accumulated legal knowledge from WDC debates
    verified_holdings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Case holdings verified through dual-brain consensus",
    )
    # Statutes confirmed current
    verified_statutes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Statutes confirmed current and correctly interpreted",
    )
    # Common legal patterns in this jurisdiction
    legal_patterns: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Patterns learned from case outcomes (E14)",
    )
    # Corrections — where the AI was wrong and human corrected
    corrections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Human corrections to AI output — highest-value training data",
    )


# ---------------------------------------------------------------------------
# Jurisdiction Container
# ---------------------------------------------------------------------------


class JurisdictionContainer:
    """A self-contained AI + Data unit for a single legal jurisdiction.

    The container is the fundamental building block of Cyphergy's
    legal knowledge architecture. Each jurisdiction gets its own
    container with embedded AI agents and data.

    Usage::

        container = JurisdictionContainer(JurisdictionConfig(
            code="LA", name="Louisiana", type=JurisdictionType.STATE
        ))

        # Ask a legal question — dual-brain consensus required
        result = await container.query(
            "What is the prescriptive period for breach of contract in Louisiana?"
        )

        # result.consensus == True means all 3 brains agreed
        # result.primary_response has the detailed answer from Opus 4.6
    """

    def __init__(self, config: JurisdictionConfig) -> None:
        self._config = config
        self._router = ModelRouter()
        self._provider = get_provider()
        self._memory = ContainerMemory(jurisdiction_code=config.code)

        # Apply per-jurisdiction model overrides from env
        self._apply_env_overrides()

        logger.info(
            "JurisdictionContainer initialized: %s (%s) type=%s",
            config.code,
            config.name,
            config.type.value,
        )

    def _apply_env_overrides(self) -> None:
        """Check for jurisdiction-specific model overrides.

        Format: MODEL_JURISDICTION_LA_PRIMARY=some-model-id
        """
        code = self._config.code.upper()
        for field, role in [
            ("primary_model", "PRIMARY"),
            ("scout_model", "SCOUT"),
            ("cohere_model", "COHERE"),
        ]:
            env_key = f"MODEL_JURISDICTION_{code}_{role}"
            override = os.getenv(env_key)
            if override:
                setattr(self._config, field, override)
                logger.info(
                    "jurisdiction_model_override | jurisdiction=%s role=%s model=%s",
                    code, role, override,
                )

    @property
    def code(self) -> str:
        return self._config.code

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def config(self) -> JurisdictionConfig:
        return self._config

    @property
    def memory(self) -> ContainerMemory:
        return self._memory

    async def query(self, question: str) -> DualBrainResult:
        """Query this jurisdiction's dual-brain system.

        All 3 models (Opus + Llama Scout + Cohere) answer independently.
        If they disagree on law/statutes/case law, consensus=False and
        the output requires human review.
        """
        result = await run_dual_brain_check(
            question=question,
            jurisdiction=f"{self._config.name} ({self._config.code})",
            router=self._router,
            provider=self._provider,
        )

        # Log the query for training pipeline
        logger.info(
            "jurisdiction_query | code=%s consensus=%s confidence=%.2f",
            self._config.code,
            result.consensus,
            result.confidence,
        )

        return result

    async def ingest_wdc_debate(self, debate_transcript: dict[str, Any]) -> None:
        """Ingest a WDC debate transcript for training.

        When the WDC panel reaches consensus on a legal question for this
        jurisdiction, the consensus output becomes training data.
        """
        self._config.wdc_debates_ingested += 1
        self._config.last_training_at = datetime.utcnow().isoformat()

        # Extract verified holdings from the debate
        if debate_transcript.get("citations_verified"):
            for citation in debate_transcript["citations_verified"]:
                self._memory.verified_holdings.append({
                    "citation": citation,
                    "verified_at": datetime.utcnow().isoformat(),
                    "source": "wdc_consensus",
                })

        logger.info(
            "wdc_debate_ingested | jurisdiction=%s total_debates=%d",
            self._config.code,
            self._config.wdc_debates_ingested,
        )

    async def ingest_case_outcome(self, outcome: dict[str, Any]) -> None:
        """Ingest a real case outcome for E14 learning.

        Actual case results (won/lost/settled) are the highest-value
        training signal for improving jurisdiction-specific accuracy.
        """
        self._config.case_outcomes_ingested += 1
        self._memory.legal_patterns.append({
            "outcome": outcome,
            "ingested_at": datetime.utcnow().isoformat(),
        })

        logger.info(
            "case_outcome_ingested | jurisdiction=%s total_outcomes=%d",
            self._config.code,
            self._config.case_outcomes_ingested,
        )

    async def record_correction(self, original: str, corrected: str, reason: str) -> None:
        """Record a human correction — highest-value training data.

        When a lawyer corrects the AI's interpretation of this
        jurisdiction's law, that correction is gold for training.
        """
        self._memory.corrections.append({
            "original": original,
            "corrected": corrected,
            "reason": reason,
            "corrected_at": datetime.utcnow().isoformat(),
        })

        logger.info(
            "correction_recorded | jurisdiction=%s total_corrections=%d",
            self._config.code,
            len(self._memory.corrections),
        )

    def get_status(self) -> dict[str, Any]:
        """Return container status for admin dashboard."""
        return {
            "code": self._config.code,
            "name": self._config.name,
            "type": self._config.type.value,
            "wdc_debates_ingested": self._config.wdc_debates_ingested,
            "case_outcomes_ingested": self._config.case_outcomes_ingested,
            "benchmark_score": self._config.benchmark_score,
            "last_training_at": self._config.last_training_at,
            "verified_holdings": len(self._memory.verified_holdings),
            "verified_statutes": len(self._memory.verified_statutes),
            "corrections": len(self._memory.corrections),
        }
