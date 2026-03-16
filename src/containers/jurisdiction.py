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


class PracticeArea(str, Enum):
    """Practice area classifications within a jurisdiction.

    Each jurisdiction container holds law across all practice areas,
    but the dual-brain consensus routes to specialized knowledge
    based on the practice area of the query.

    CIVIL: Contract disputes, torts, property, family law, employment
    CRIMINAL: Felonies, misdemeanors, traffic, DUI, white collar
    OVERLAP: Where civil meets criminal — punitive damages, RICO,
             fraud, conversion, restitution, contempt

    Example — Florida punitive damages:
      Civil claim filed → Fla. Stat. § 768.72 requires leave of court
      before punitive damages can be pled → this is OVERLAP law because
      punitive damages are civil remedies that require proof of criminal-
      level misconduct (intentional, grossly negligent, or fraudulent).
      The gate (leave of court) is the bridge from civil to criminal
      standards of proof.
    """

    CIVIL = "civil"
    CRIMINAL = "criminal"
    OVERLAP = "overlap"          # Civil-criminal bridge (punitive, RICO, fraud)
    ADMINISTRATIVE = "administrative"  # Agency proceedings, licensing, regulatory
    APPELLATE = "appellate"      # Appellate procedure (distinct from trial)
    BANKRUPTCY = "bankruptcy"    # Federal + state exemptions


class PracticeSubArea(str, Enum):
    """Specific sub-areas within practice areas."""

    # Civil
    CONTRACT = "contract"
    TORT = "tort"
    PROPERTY = "property"
    FAMILY = "family"
    EMPLOYMENT = "employment"
    INSURANCE = "insurance"
    CONSTRUCTION = "construction"
    CONSUMER_PROTECTION = "consumer_protection"

    # Criminal
    FELONY = "felony"
    MISDEMEANOR = "misdemeanor"
    WHITE_COLLAR = "white_collar"
    DUI = "dui"
    DRUG = "drug"
    DOMESTIC_VIOLENCE = "domestic_violence"

    # Overlap (civil-criminal bridge)
    PUNITIVE_DAMAGES = "punitive_damages"    # Civil remedy, criminal-level proof
    RICO = "rico"                            # Civil + criminal statutes
    FRAUD = "fraud"                          # Civil fraud + criminal fraud
    CONVERSION = "conversion"                # Civil tort with criminal theft overlap
    RESTITUTION = "restitution"              # Criminal sentence + civil remedy
    CONTEMPT = "contempt"                    # Civil + criminal contempt
    FORFEITURE = "forfeiture"                # Civil + criminal asset forfeiture
    QUI_TAM = "qui_tam"                      # False Claims Act — civil/criminal
    TREBLE_DAMAGES = "treble_damages"        # Antitrust, LUTPA, consumer protection

    # Administrative
    LICENSING = "licensing"
    REGULATORY = "regulatory"
    IMMIGRATION = "immigration"
    TAX = "tax"
    WORKERS_COMP = "workers_comp"


# ---------------------------------------------------------------------------
# Jurisdiction-specific overlap rules
# ---------------------------------------------------------------------------

# These are the "bridge laws" — where civil procedure requires
# criminal-level proof or vice versa. Each jurisdiction has unique gates.

OVERLAP_RULES: dict[str, list[dict[str, str]]] = {
    "FL": [
        {
            "area": PracticeSubArea.PUNITIVE_DAMAGES.value,
            "rule": "Fla. Stat. § 768.72 — Punitive damages require leave of court. "
                    "Plaintiff must proffer reasonable evidence showing basis for recovery. "
                    "Court acts as gatekeeper before jury sees punitive claim. "
                    "Standard: clear and convincing evidence of intentional misconduct or gross negligence.",
            "gate_type": "judicial_leave",
            "proof_standard": "clear_and_convincing",
        },
    ],
    "CA": [
        {
            "area": PracticeSubArea.PUNITIVE_DAMAGES.value,
            "rule": "Cal. Civ. Code § 3294 — Punitive damages require clear and convincing evidence "
                    "of oppression, fraud, or malice. No pre-filing gate (unlike FL), but defendant can "
                    "move to strike under CCP § 435.",
            "gate_type": "motion_to_strike",
            "proof_standard": "clear_and_convincing",
        },
    ],
    "TX": [
        {
            "area": PracticeSubArea.PUNITIVE_DAMAGES.value,
            "rule": "Tex. Civ. Prac. & Rem. Code § 41.003 — Exemplary damages require clear and convincing "
                    "evidence of fraud, malice, or gross negligence. Capped at greater of 2x economic + "
                    "non-economic up to $750K, or $200K.",
            "gate_type": "cap",
            "proof_standard": "clear_and_convincing",
        },
    ],
    "LA": [
        {
            "area": PracticeSubArea.PUNITIVE_DAMAGES.value,
            "rule": "La. C.C. art. 2315.4 — Punitive (exemplary) damages generally NOT available in Louisiana "
                    "EXCEPT by specific statute (e.g., child pornography, drunk driving, domestic violence). "
                    "Louisiana is a civil law jurisdiction — punitive damages are the exception, not the rule.",
            "gate_type": "statutory_exception_only",
            "proof_standard": "statutory",
        },
    ],
    "NY": [
        {
            "area": PracticeSubArea.PUNITIVE_DAMAGES.value,
            "rule": "No statutory cap. Punitive damages available when defendant's conduct is 'aimed at the public generally' "
                    "or involves 'high moral culpability.' Standard: gross, wanton, or willful fraud or other "
                    "morally culpable conduct. Rocanova v. Equitable Life Assur. Soc., 83 N.Y.2d 603 (1994).",
            "gate_type": "none",
            "proof_standard": "preponderance_with_moral_culpability",
        },
    ],
    "FED": [
        {
            "area": PracticeSubArea.RICO.value,
            "rule": "18 U.S.C. §§ 1961-1968 — RICO provides both criminal penalties (imprisonment, fines, forfeiture) "
                    "and civil remedies (treble damages + attorney fees under § 1964(c)). "
                    "Civil RICO requires pattern of racketeering activity (minimum 2 predicate acts).",
            "gate_type": "predicate_acts",
            "proof_standard": "preponderance_civil_brd_criminal",
        },
        {
            "area": PracticeSubArea.QUI_TAM.value,
            "rule": "31 U.S.C. §§ 3729-3733 — False Claims Act. Civil action brought by relator on behalf of US. "
                    "Treble damages + $11K-$23K per false claim. DOJ can intervene or decline. "
                    "Criminal false claims under 18 U.S.C. § 287 carry imprisonment.",
            "gate_type": "doj_intervention",
            "proof_standard": "preponderance_civil_brd_criminal",
        },
    ],
}


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

    # Practice areas supported
    practice_areas: list[str] = Field(
        default_factory=lambda: [PracticeArea.CIVIL.value, PracticeArea.CRIMINAL.value, PracticeArea.OVERLAP.value],
        description="Practice areas this container covers",
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

    async def query(
        self,
        question: str,
        practice_area: Optional[str] = None,
        sub_area: Optional[str] = None,
    ) -> DualBrainResult:
        """Query this jurisdiction's dual-brain system.

        All 3 models (Opus + Llama Scout + Cohere) answer independently.
        If they disagree on law/statutes/case law, consensus=False and
        the output requires human review.

        The practice area and sub-area are injected into the system prompt
        so the dual-brain focuses on the correct body of law. Overlap
        rules (e.g., Florida punitive damages gate) are automatically
        included when relevant.
        """
        # Build jurisdiction-aware context
        jurisdiction_label = f"{self._config.name} ({self._config.code})"
        context_parts = [jurisdiction_label]

        if practice_area:
            context_parts.append(f"Practice area: {practice_area}")
        if sub_area:
            context_parts.append(f"Sub-area: {sub_area}")

        # Inject overlap rules if this is an overlap query
        overlap_rules = OVERLAP_RULES.get(self._config.code, [])
        if sub_area and overlap_rules:
            matching = [r for r in overlap_rules if r["area"] == sub_area]
            if matching:
                context_parts.append("OVERLAP RULES (civil-criminal bridge):")
                for rule in matching:
                    context_parts.append(f"  {rule['rule']}")
                    context_parts.append(f"  Gate: {rule['gate_type']}, Proof: {rule['proof_standard']}")

        jurisdiction_context = "\n".join(context_parts)

        result = await run_dual_brain_check(
            question=question,
            jurisdiction=jurisdiction_context,
            router=self._router,
            provider=self._provider,
        )

        logger.info(
            "jurisdiction_query | code=%s area=%s sub=%s consensus=%s confidence=%.2f",
            self._config.code,
            practice_area or "general",
            sub_area or "none",
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
