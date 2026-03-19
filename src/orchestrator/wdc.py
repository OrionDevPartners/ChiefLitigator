"""Weighted Debate Consensus (WDC) v2.0 Scoring Engine.

Every substantive output produced by the Cyphergy agent network
passes through this engine before reaching the user.

Scoring tiers:
    8.5+   CERTIFIED               — output approved for user delivery
    7.0-8.4 CERTIFIED_WITH_NOTES   — approved with advisory notes attached
    5.0-6.9 REVISION_REQUIRED      — returned to agents for improvement
    <5.0   REJECTED                — output discarded
    VETOED                          — Compliance agent exercised absolute veto

Architecture:
    5 agents score every output in parallel via ``run_debate``.
    Compliance Counsel (10% weight) holds an ABSOLUTE VETO on procedural
    errors — a veto overrides any composite score, regardless of how
    high the other agents scored.
"""

from __future__ import annotations

import asyncio
import logging
import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base_agent import AgentRole, WDCScore
from src.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


# ── Verdict Enum ─────────────────────────────────────────────────────


class WDCVerdict(str, Enum):
    """Possible outcomes of a WDC scoring round."""

    CERTIFIED = "certified"
    CERTIFIED_WITH_NOTES = "certified_with_notes"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"
    VETOED = "vetoed"


# ── Result Model ─────────────────────────────────────────────────────


class WDCResult(BaseModel):
    """Complete result of a WDC scoring round."""

    verdict: WDCVerdict = Field(description="Final verdict for the evaluated output")
    composite_score: float = Field(
        ge=0.0,
        le=10.0,
        description="Weighted composite score across all agents",
    )
    agent_scores: dict[str, float] = Field(
        description="Raw score per agent role (role -> score 0-10)",
    )
    weighted_scores: dict[str, float] = Field(
        description="Weighted contribution per agent role (role -> score * weight)",
    )
    vetoed: bool = Field(description="Whether the Compliance agent exercised a veto")
    veto_reason: str | None = Field(
        default=None,
        description="Explanation if a veto was exercised",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Advisory notes collected from agents",
    )
    revision_feedback: list[str] | None = Field(
        default=None,
        description="Specific feedback for revision if REVISION_REQUIRED",
    )
    cycle: int = Field(
        default=1,
        description="Which revision cycle produced this result (1 = first pass)",
    )


# ── Engine ───────────────────────────────────────────────────────────


class WDCEngine:
    """WDC v2.0 scoring engine.

    Consumes WDCScore objects from each of the 5 agents and produces
    a WDCResult with a verdict, composite score, and optional revision
    feedback.

    Usage::

        engine = WDCEngine()
        result = engine.score(agent_scores)  # synchronous scoring
        result = await engine.run_debate(output, agents, context)  # full async debate
    """

    # Expected agent roles in every scoring round
    REQUIRED_ROLES: frozenset[str] = frozenset(role.value for role in AgentRole)

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or get_settings()

        # Build weight map from settings: role_value -> weight
        self._weights: dict[str, float] = {
            AgentRole.LEAD_COUNSEL.value: self._settings.weight_lead_counsel,
            AgentRole.RESEARCH_COUNSEL.value: self._settings.weight_research_counsel,
            AgentRole.DRAFTING_COUNSEL.value: self._settings.weight_drafting_counsel,
            AgentRole.RED_TEAM.value: self._settings.weight_red_team,
            AgentRole.COMPLIANCE_COUNSEL.value: self._settings.weight_compliance_counsel,
        }

        # Validate weights sum to 1.0 (with floating-point tolerance)
        total = sum(self._weights.values())
        if not math.isclose(total, 1.0, rel_tol=1e-6):
            raise ValueError(f"Agent weights must sum to 1.0, got {total:.6f}. Weights: {self._weights}")

        # Thresholds
        self._cert_threshold: float = self._settings.wdc_certification_threshold
        self._notes_threshold: float = self._settings.wdc_notes_threshold
        self._revision_threshold: float = self._settings.wdc_revision_threshold
        self._max_cycles: int = self._settings.wdc_max_revision_cycles

        logger.info(
            "WDC Engine initialized: cert=%.1f notes=%.1f rev=%.1f max_cycles=%d weights=%s",
            self._cert_threshold,
            self._notes_threshold,
            self._revision_threshold,
            self._max_cycles,
            self._weights,
        )

    # ── Public API ───────────────────────────────────────────────────

    def score(self, agent_scores: list[WDCScore]) -> WDCResult:
        """Synchronously score a list of agent evaluations.

        Parameters
        ----------
        agent_scores:
            One WDCScore from each of the 5 agents. Must include all
            required roles exactly once.

        Returns
        -------
        WDCResult with verdict, composite score, and optional feedback.

        Raises
        ------
        ValueError:
            If agent_scores does not contain exactly one score per
            required role.
        """
        self._validate_scores(agent_scores)

        # Step 1: Check for Compliance veto FIRST — absolute override
        vetoed, veto_reason = self._check_veto(agent_scores)

        # Step 2: Compute weighted composite
        composite, raw_scores, weighted_scores = self._compute_composite(agent_scores)

        # Step 3: Determine verdict (veto overrides composite)
        verdict = self._determine_verdict(composite, vetoed)

        # Step 4: Collect notes and revision feedback
        notes = self._collect_notes(agent_scores)
        revision_feedback = self._collect_revision_feedback(agent_scores, verdict)

        result = WDCResult(
            verdict=verdict,
            composite_score=round(composite, 4),
            agent_scores=raw_scores,
            weighted_scores={k: round(v, 4) for k, v in weighted_scores.items()},
            vetoed=vetoed,
            veto_reason=veto_reason,
            notes=notes,
            revision_feedback=revision_feedback,
        )

        logger.info(
            "WDC scored: verdict=%s composite=%.2f vetoed=%s",
            result.verdict.value,
            result.composite_score,
            result.vetoed,
        )

        return result

    async def run_debate(
        self,
        output: str,
        agents: list[Any],
        context: dict[str, Any] | None = None,
    ) -> WDCResult:
        """Run a full WDC debate cycle with all agents scoring in parallel.

        Parameters
        ----------
        output:
            The substantive text to be evaluated by all agents.
        agents:
            List of BaseAgent instances (must cover all 5 roles).
        context:
            Optional case context dict passed to each agent's score method.

        Returns
        -------
        WDCResult from the scoring round.
        """
        # Parallel scoring via asyncio.gather
        score_tasks = [agent.score(output, context) for agent in agents]
        agent_scores: list[WDCScore] = await asyncio.gather(*score_tasks)

        return self.score(agent_scores)

    # ── Internal Methods ─────────────────────────────────────────────

    def _validate_scores(self, agent_scores: list[WDCScore]) -> None:
        """Ensure exactly one score per required agent role."""
        received_roles = {s.scorer_role.value for s in agent_scores}
        missing = self.REQUIRED_ROLES - received_roles
        if missing:
            raise ValueError(
                f"Missing agent scores for roles: {sorted(missing)}. All 5 agents must participate in every WDC round."
            )
        if len(agent_scores) != len(self.REQUIRED_ROLES):
            raise ValueError(
                f"Expected exactly {len(self.REQUIRED_ROLES)} scores (one per role), got {len(agent_scores)}."
            )

    def _check_veto(self, agent_scores: list[WDCScore]) -> tuple[bool, str | None]:
        """Check if any agent with veto authority has exercised it.

        Only Compliance Counsel has veto power. A veto is absolute
        and overrides any composite score.

        Returns
        -------
        Tuple of (vetoed: bool, reason: str | None).
        """
        for s in agent_scores:
            if s.veto:
                reason = s.veto_reason or "Compliance veto exercised (no reason provided)"
                logger.warning(
                    "VETO exercised by %s: %s",
                    s.scorer_role.value,
                    reason,
                )
                return True, reason
        return False, None

    def _compute_composite(self, agent_scores: list[WDCScore]) -> tuple[float, dict[str, float], dict[str, float]]:
        """Compute the weighted composite score.

        Returns
        -------
        Tuple of (composite, raw_scores_dict, weighted_scores_dict).
        """
        raw_scores: dict[str, float] = {}
        weighted_scores: dict[str, float] = {}

        for s in agent_scores:
            role = s.scorer_role.value
            weight = self._weights[role]
            raw_scores[role] = s.score
            weighted_scores[role] = s.score * weight

        composite = sum(weighted_scores.values())
        return composite, raw_scores, weighted_scores

    def _determine_verdict(self, composite: float, vetoed: bool) -> WDCVerdict:
        """Map composite score to a verdict, with veto override.

        Parameters
        ----------
        composite:
            The weighted composite score (0-10 scale).
        vetoed:
            Whether the Compliance agent exercised a veto.

        Returns
        -------
        The appropriate WDCVerdict.
        """
        if vetoed:
            return WDCVerdict.VETOED

        if composite >= self._cert_threshold:
            return WDCVerdict.CERTIFIED
        elif composite >= self._notes_threshold:
            return WDCVerdict.CERTIFIED_WITH_NOTES
        elif composite >= self._revision_threshold:
            return WDCVerdict.REVISION_REQUIRED
        else:
            return WDCVerdict.REJECTED

    def _collect_notes(self, agent_scores: list[WDCScore]) -> list[str]:
        """Gather advisory notes from all agents' flags and reasoning.

        Returns notes from any agent that flagged issues, regardless
        of whether the overall verdict is positive.
        """
        notes: list[str] = []
        for s in agent_scores:
            if s.flags:
                notes.append(f"[{s.scorer_role.value}] flags: {', '.join(s.flags)}")
            # If an agent scored below the notes threshold, include their reasoning
            if s.score < self._notes_threshold:
                notes.append(f"[{s.scorer_role.value}] low score ({s.score:.1f}): {s.reasoning}")
        return notes

    def _collect_revision_feedback(
        self,
        agent_scores: list[WDCScore],
        verdict: WDCVerdict,
    ) -> list[str] | None:
        """Collect specific revision feedback when output needs improvement.

        Only populated when verdict is REVISION_REQUIRED or REJECTED.
        """
        if verdict not in (WDCVerdict.REVISION_REQUIRED, WDCVerdict.REJECTED):
            return None

        feedback: list[str] = []
        for s in agent_scores:
            if s.score < self._cert_threshold:
                feedback.append(f"[{s.scorer_role.value}] (score: {s.score:.1f}) {s.reasoning}")
            if s.flags:
                feedback.append(f"[{s.scorer_role.value}] issues: {', '.join(s.flags)}")
        return feedback if feedback else None
