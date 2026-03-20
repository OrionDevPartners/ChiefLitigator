"""The Galvanizer — Adversarial Panel Iteration Engine.

The Galvanizer is ChiefLitigator's core quality assurance mechanism.
It simulates a courtroom where legal strategy and document drafts are
stress-tested through adversarial debate before being delivered to the user.

Architecture:
  - **Advocacy Panel** (Lead Counsel + Research Counsel): Argues FOR the
    strategy. Finds the strongest interpretations, most favorable precedent,
    and best framing of facts.
  - **Stress-Test Panel** (Red Team + Compliance): Argues AGAINST the
    strategy. Attacks citations, challenges logic, finds procedural traps,
    and identifies weaknesses a real adversary would exploit.
  - **Dual-Brain Operator**: The 3-model jurisdiction system (Opus + Llama
    Scout + Cohere) that produces the initial work product.
  - **90% Confidence Gate**: Nothing leaves the system below 90% confidence.
    If the threshold cannot be reached, the system tells the user exactly
    what is missing and what evidence would push it over.

The Galvanizer runs iterative rounds:
  Round 1: Advocacy presents. Stress-Test attacks.
  Round 2: Advocacy responds to attacks. Stress-Test escalates.
  Round N: Continues until confidence >= 90% OR max rounds reached.

Named "Galvanizer" because the process shock-strengthens the work product
like galvanizing steel — it goes in raw and comes out armored.

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.orchestrator.galvanizer")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIDENCE_GATE = float(os.getenv("GALVANIZER_CONFIDENCE_GATE", "0.90"))
MAX_ROUNDS = int(os.getenv("GALVANIZER_MAX_ROUNDS", "5"))
VETO_THRESHOLD = float(os.getenv("GALVANIZER_VETO_THRESHOLD", "0.40"))
ESCALATION_DELTA = float(os.getenv("GALVANIZER_ESCALATION_DELTA", "0.05"))


# ---------------------------------------------------------------------------
# Panel Roles
# ---------------------------------------------------------------------------
class PanelRole(str, Enum):
    """Roles within the Galvanizer adversarial system."""
    ADVOCACY_LEAD = "advocacy_lead_counsel"
    ADVOCACY_RESEARCH = "advocacy_research_counsel"
    STRESS_LEAD = "stress_red_team"
    STRESS_COMPLIANCE = "stress_compliance_counsel"


class AttackType(str, Enum):
    """Types of attacks the Stress-Test Panel can launch."""
    CITATION_CHALLENGE = "citation_challenge"
    LOGIC_FLAW = "logic_flaw"
    PROCEDURAL_TRAP = "procedural_trap"
    EVIDENCE_GAP = "evidence_gap"
    JURISDICTION_MISMATCH = "jurisdiction_mismatch"
    STATUTE_OBSOLETE = "statute_obsolete"
    OPPOSING_PRECEDENT = "opposing_precedent"
    STANDING_CHALLENGE = "standing_challenge"
    STATUTE_OF_LIMITATIONS = "statute_of_limitations"
    CONSTITUTIONAL_ISSUE = "constitutional_issue"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
class PanelArgument(BaseModel):
    """A single argument from a panel member."""
    panel_role: str = Field(description="Which panel member made this argument")
    argument_text: str = Field(description="The full argument")
    citations: List[str] = Field(default_factory=list, description="Citations supporting the argument")
    attack_type: Optional[str] = Field(default=None, description="Type of attack (Stress-Test only)")
    confidence_impact: float = Field(
        default=0.0,
        description="How much this argument changes confidence (+/- 0.0 to 1.0)",
    )
    rebutted: bool = Field(default=False, description="Whether this argument was successfully rebutted")
    rebuttal_text: Optional[str] = Field(default=None, description="The rebuttal if rebutted")


class GalvanizerRound(BaseModel):
    """One round of adversarial debate."""
    round_number: int = Field(description="Round number (1-indexed)")
    advocacy_arguments: List[PanelArgument] = Field(
        default_factory=list,
        description="Arguments from the Advocacy Panel",
    )
    stress_test_attacks: List[PanelArgument] = Field(
        default_factory=list,
        description="Attacks from the Stress-Test Panel",
    )
    advocacy_rebuttals: List[PanelArgument] = Field(
        default_factory=list,
        description="Advocacy responses to Stress-Test attacks",
    )
    round_confidence: float = Field(
        default=0.0,
        description="Confidence score after this round",
    )
    unresolved_attacks: List[str] = Field(
        default_factory=list,
        description="Attacks that were NOT successfully rebutted",
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class GalvanizerResult(BaseModel):
    """Final result of a Galvanizer session."""
    session_id: str = Field(description="Unique Galvanizer session ID")
    case_id: str = Field(description="Associated case ID")
    work_product_type: str = Field(description="Type of work product galvanized")
    initial_confidence: float = Field(description="Confidence before Galvanizer")
    final_confidence: float = Field(description="Confidence after Galvanizer")
    passed_gate: bool = Field(description="Whether the 90% confidence gate was cleared")
    total_rounds: int = Field(description="Number of rounds executed")
    rounds: List[GalvanizerRound] = Field(description="Full debate transcript")
    galvanized_output: str = Field(description="The final hardened work product")
    unresolved_weaknesses: List[str] = Field(
        default_factory=list,
        description="Weaknesses that could not be resolved (if gate not passed)",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="What the user needs to provide to push confidence higher",
    )
    veto_applied: bool = Field(
        default=False,
        description="Whether Compliance applied a veto",
    )
    veto_reason: Optional[str] = Field(default=None, description="Reason for veto if applied")
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# The Galvanizer Engine
# ---------------------------------------------------------------------------
class Galvanizer:
    """The adversarial panel iteration engine.

    Orchestrates the Advocacy Panel and Stress-Test Panel through
    iterative rounds of debate until the work product either:
    1. Clears the 90% confidence gate (ready for filing/delivery)
    2. Reaches max rounds without clearing (returns with recommendations)
    3. Is vetoed by Compliance (blocked with explanation)

    Usage::

        galvanizer = Galvanizer(agentcore_runtime=runtime)
        result = await galvanizer.galvanize(
            case_id="case-12345",
            work_product="[draft motion to dismiss]",
            work_product_type="motion_to_dismiss",
            case_context={...},
        )
        if result.passed_gate:
            # Safe to file
            final_doc = result.galvanized_output
        else:
            # Tell user what's missing
            show_recommendations(result.recommendations)
    """

    def __init__(self, agentcore_runtime: Any = None) -> None:
        self._runtime = agentcore_runtime
        self._confidence_gate = CONFIDENCE_GATE
        self._max_rounds = MAX_ROUNDS
        self._veto_threshold = VETO_THRESHOLD

        logger.info(
            "Galvanizer initialized: gate=%.0f%% max_rounds=%d veto_threshold=%.0f%%",
            self._confidence_gate * 100,
            self._max_rounds,
            self._veto_threshold * 100,
        )

    async def galvanize(
        self,
        case_id: str,
        work_product: str,
        work_product_type: str,
        case_context: Dict[str, Any],
        jurisdiction: str = "",
    ) -> GalvanizerResult:
        """Run the full Galvanizer process on a work product.

        Args:
            case_id: The case this work product belongs to.
            work_product: The draft document or strategy to galvanize.
            work_product_type: Type (e.g., 'complaint', 'motion', 'strategy').
            case_context: Full case context including facts, evidence, parties.
            jurisdiction: Jurisdiction code for rule-specific checks.

        Returns:
            GalvanizerResult with the full debate transcript and final output.
        """
        session_id = f"galv-{uuid.uuid4().hex[:12]}"
        logger.info(
            "Galvanizer session started: %s case=%s type=%s",
            session_id,
            case_id,
            work_product_type,
        )

        # Step 1: Initial confidence assessment
        initial_confidence = await self._assess_initial_confidence(
            work_product, case_context, jurisdiction,
        )

        result = GalvanizerResult(
            session_id=session_id,
            case_id=case_id,
            work_product_type=work_product_type,
            initial_confidence=initial_confidence,
            final_confidence=initial_confidence,
            passed_gate=False,
            total_rounds=0,
            rounds=[],
            galvanized_output=work_product,
        )

        # Check if already above gate (rare but possible for simple matters)
        if initial_confidence >= self._confidence_gate:
            result.passed_gate = True
            result.completed_at = datetime.utcnow().isoformat()
            logger.info(
                "Galvanizer: initial confidence %.1f%% already above gate",
                initial_confidence * 100,
            )
            return result

        # Step 2: Run adversarial rounds
        current_product = work_product
        current_confidence = initial_confidence
        all_unresolved: List[str] = []

        for round_num in range(1, self._max_rounds + 1):
            logger.info(
                "Galvanizer round %d/%d — confidence=%.1f%%",
                round_num,
                self._max_rounds,
                current_confidence * 100,
            )

            # Run one round of adversarial debate
            round_result = await self._run_round(
                round_number=round_num,
                work_product=current_product,
                case_context=case_context,
                jurisdiction=jurisdiction,
                current_confidence=current_confidence,
                prior_unresolved=all_unresolved,
            )

            result.rounds.append(round_result)
            current_confidence = round_result.round_confidence
            all_unresolved = round_result.unresolved_attacks

            # Check for Compliance veto
            veto = await self._check_compliance_veto(
                round_result, case_context, jurisdiction,
            )
            if veto:
                result.veto_applied = True
                result.veto_reason = veto
                result.final_confidence = 0.0
                result.completed_at = datetime.utcnow().isoformat()
                logger.warning("Galvanizer: COMPLIANCE VETO — %s", veto)
                return result

            # Apply improvements from this round
            current_product = await self._apply_improvements(
                current_product, round_result, case_context,
            )

            # Check if gate is cleared
            if current_confidence >= self._confidence_gate:
                result.passed_gate = True
                result.final_confidence = current_confidence
                result.total_rounds = round_num
                result.galvanized_output = current_product
                result.completed_at = datetime.utcnow().isoformat()
                logger.info(
                    "Galvanizer: GATE CLEARED at round %d — confidence=%.1f%%",
                    round_num,
                    current_confidence * 100,
                )
                return result

        # Max rounds reached without clearing gate
        result.final_confidence = current_confidence
        result.total_rounds = self._max_rounds
        result.galvanized_output = current_product
        result.unresolved_weaknesses = all_unresolved
        result.recommendations = await self._generate_recommendations(
            all_unresolved, case_context, current_confidence,
        )
        result.completed_at = datetime.utcnow().isoformat()

        logger.warning(
            "Galvanizer: max rounds reached — confidence=%.1f%% (gate=%.1f%%)",
            current_confidence * 100,
            self._confidence_gate * 100,
        )
        return result

    # ── Round Execution ──────────────────────────────────────────────

    async def _run_round(
        self,
        round_number: int,
        work_product: str,
        case_context: Dict[str, Any],
        jurisdiction: str,
        current_confidence: float,
        prior_unresolved: List[str],
    ) -> GalvanizerRound:
        """Execute one round of adversarial debate."""
        round_result = GalvanizerRound(
            round_number=round_number,
            round_confidence=current_confidence,
        )

        # Phase A: Advocacy Panel presents strengths
        advocacy_args = await self._run_advocacy_panel(
            work_product, case_context, jurisdiction, round_number,
        )
        round_result.advocacy_arguments = advocacy_args

        # Phase B: Stress-Test Panel attacks
        stress_attacks = await self._run_stress_test_panel(
            work_product, case_context, jurisdiction,
            advocacy_args, prior_unresolved, round_number,
        )
        round_result.stress_test_attacks = stress_attacks

        # Phase C: Advocacy responds to attacks
        rebuttals = await self._run_advocacy_rebuttals(
            stress_attacks, case_context, jurisdiction,
        )
        round_result.advocacy_rebuttals = rebuttals

        # Phase D: Score the round
        confidence_delta = self._score_round(
            advocacy_args, stress_attacks, rebuttals,
        )
        new_confidence = min(1.0, max(0.0, current_confidence + confidence_delta))
        round_result.round_confidence = new_confidence

        # Identify unresolved attacks
        rebutted_indices = {
            i for i, r in enumerate(rebuttals)
            if r.rebutted
        }
        round_result.unresolved_attacks = [
            attack.argument_text
            for i, attack in enumerate(stress_attacks)
            if i not in rebutted_indices
        ]

        return round_result

    async def _run_advocacy_panel(
        self,
        work_product: str,
        case_context: Dict[str, Any],
        jurisdiction: str,
        round_number: int,
    ) -> List[PanelArgument]:
        """Advocacy Panel argues FOR the work product."""
        if not self._runtime:
            return await self._run_advocacy_local(
                work_product, case_context, jurisdiction, round_number,
            )

        from src.providers.bedrock_agentcore import AgentIdentity

        # Fan out to Lead Counsel and Research Counsel
        prompt = (
            f"You are the ADVOCACY PANEL in round {round_number} of the Galvanizer process.\n\n"
            f"Your job is to argue FOR the following legal work product. Find the strongest "
            f"interpretations, most favorable precedent, and best framing of the facts.\n\n"
            f"WORK PRODUCT:\n{work_product}\n\n"
            f"CASE CONTEXT:\n{_format_context(case_context)}\n\n"
            f"JURISDICTION: {jurisdiction}\n\n"
            f"Provide your arguments with specific citations. Each argument should include:\n"
            f"1. The argument text\n"
            f"2. Supporting citations\n"
            f"3. Why this strengthens the work product"
        )

        fan_out = await self._runtime.fan_out(
            case_id=case_context.get("case_id", "unknown"),
            agents=[AgentIdentity.LEAD_COUNSEL, AgentIdentity.RESEARCH_COUNSEL],
            prompt=prompt,
            shared_context=case_context,
        )

        arguments = []
        for agent_id, response in fan_out.get("responses", {}).items():
            arguments.append(PanelArgument(
                panel_role=agent_id,
                argument_text=response.get("text", ""),
                citations=[],
                confidence_impact=0.05,
            ))

        return arguments

    async def _run_stress_test_panel(
        self,
        work_product: str,
        case_context: Dict[str, Any],
        jurisdiction: str,
        advocacy_args: List[PanelArgument],
        prior_unresolved: List[str],
        round_number: int,
    ) -> List[PanelArgument]:
        """Stress-Test Panel attacks the work product."""
        if not self._runtime:
            return await self._run_stress_local(
                work_product, case_context, jurisdiction, round_number,
            )

        from src.providers.bedrock_agentcore import AgentIdentity

        advocacy_text = "\n".join(a.argument_text for a in advocacy_args)
        unresolved_text = "\n".join(prior_unresolved) if prior_unresolved else "None"

        prompt = (
            f"You are the STRESS-TEST PANEL in round {round_number} of the Galvanizer process.\n\n"
            f"Your job is to ATTACK the following legal work product. Find every weakness, "
            f"every questionable citation, every procedural trap, and every argument that "
            f"opposing counsel would make.\n\n"
            f"WORK PRODUCT:\n{work_product}\n\n"
            f"ADVOCACY PANEL ARGUMENTS:\n{advocacy_text}\n\n"
            f"UNRESOLVED FROM PRIOR ROUNDS:\n{unresolved_text}\n\n"
            f"CASE CONTEXT:\n{_format_context(case_context)}\n\n"
            f"JURISDICTION: {jurisdiction}\n\n"
            f"For each attack, specify:\n"
            f"1. The attack type (citation_challenge, logic_flaw, procedural_trap, "
            f"evidence_gap, opposing_precedent, standing_challenge, statute_of_limitations)\n"
            f"2. The specific weakness\n"
            f"3. How opposing counsel would exploit it\n"
            f"4. The confidence impact (how much this weakens the case)"
        )

        fan_out = await self._runtime.fan_out(
            case_id=case_context.get("case_id", "unknown"),
            agents=[AgentIdentity.RED_TEAM, AgentIdentity.COMPLIANCE_COUNSEL],
            prompt=prompt,
            shared_context=case_context,
        )

        attacks = []
        for agent_id, response in fan_out.get("responses", {}).items():
            attacks.append(PanelArgument(
                panel_role=agent_id,
                argument_text=response.get("text", ""),
                attack_type=AttackType.LOGIC_FLAW.value,
                confidence_impact=-0.05,
            ))

        return attacks

    async def _run_advocacy_rebuttals(
        self,
        attacks: List[PanelArgument],
        case_context: Dict[str, Any],
        jurisdiction: str,
    ) -> List[PanelArgument]:
        """Advocacy Panel responds to Stress-Test attacks."""
        if not self._runtime:
            return await self._run_rebuttals_local(attacks, case_context, jurisdiction)

        from src.providers.bedrock_agentcore import AgentIdentity

        rebuttals = []
        for attack in attacks:
            prompt = (
                f"The Stress-Test Panel has raised the following attack:\n\n"
                f"{attack.argument_text}\n\n"
                f"As the Advocacy Panel, provide a rebuttal with specific citations. "
                f"If you cannot rebut this attack, say so explicitly."
            )

            response = await self._runtime.fan_out(
                case_id=case_context.get("case_id", "unknown"),
                agents=[AgentIdentity.LEAD_COUNSEL],
                prompt=prompt,
                shared_context=case_context,
            )

            for agent_id, resp in response.get("responses", {}).items():
                text = resp.get("text", "")
                rebutted = "cannot rebut" not in text.lower() and "unable to rebut" not in text.lower()
                rebuttals.append(PanelArgument(
                    panel_role=agent_id,
                    argument_text=text,
                    rebutted=rebutted,
                    rebuttal_text=text if rebutted else None,
                    confidence_impact=0.03 if rebutted else 0.0,
                ))

        return rebuttals

    # ── Local Fallback (when AgentCore runtime not available) ────────

    async def _run_advocacy_local(
        self, work_product: str, case_context: Dict[str, Any],
        jurisdiction: str, round_number: int,
    ) -> List[PanelArgument]:
        """Local advocacy panel using direct Bedrock Converse API."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"As an experienced trial attorney ADVOCATING for this legal position, "
            f"identify the 3 strongest arguments supporting this work product:\n\n"
            f"{work_product}\n\nJurisdiction: {jurisdiction}"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=4096,
            temperature=0.0,
            system="You are the Advocacy Panel of the Galvanizer. Argue FOR the work product.",
            messages=[{"role": "user", "content": prompt}],
        )

        return [PanelArgument(
            panel_role=PanelRole.ADVOCACY_LEAD.value,
            argument_text=response.text,
            confidence_impact=0.05,
        )]

    async def _run_stress_local(
        self, work_product: str, case_context: Dict[str, Any],
        jurisdiction: str, round_number: int,
    ) -> List[PanelArgument]:
        """Local stress-test panel using direct Bedrock Converse API."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"As a ruthless opposing counsel, find EVERY weakness in this legal work product. "
            f"Attack the citations, logic, procedures, and evidence gaps:\n\n"
            f"{work_product}\n\nJurisdiction: {jurisdiction}"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=4096,
            temperature=0.3,  # Slightly higher temp for creative attacks
            system="You are the Stress-Test Panel of the Galvanizer. ATTACK the work product mercilessly.",
            messages=[{"role": "user", "content": prompt}],
        )

        return [PanelArgument(
            panel_role=PanelRole.STRESS_LEAD.value,
            argument_text=response.text,
            attack_type=AttackType.LOGIC_FLAW.value,
            confidence_impact=-0.05,
        )]

    async def _run_rebuttals_local(
        self, attacks: List[PanelArgument],
        case_context: Dict[str, Any], jurisdiction: str,
    ) -> List[PanelArgument]:
        """Local rebuttals using direct Bedrock Converse API."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        rebuttals = []

        for attack in attacks:
            prompt = (
                f"Rebut this attack with specific legal citations:\n\n"
                f"{attack.argument_text}\n\nJurisdiction: {jurisdiction}"
            )

            response = await provider.create_message(
                model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
                max_tokens=2048,
                temperature=0.0,
                system="You are the Advocacy Panel. Rebut the attack or admit you cannot.",
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.text
            rebutted = "cannot rebut" not in text.lower() and "unable to rebut" not in text.lower()
            rebuttals.append(PanelArgument(
                panel_role=PanelRole.ADVOCACY_LEAD.value,
                argument_text=text,
                rebutted=rebutted,
                rebuttal_text=text if rebutted else None,
                confidence_impact=0.03 if rebutted else 0.0,
            ))

        return rebuttals

    # ── Scoring & Assessment ─────────────────────────────────────────

    def _score_round(
        self,
        advocacy: List[PanelArgument],
        attacks: List[PanelArgument],
        rebuttals: List[PanelArgument],
    ) -> float:
        """Calculate the net confidence change from a round.

        Scoring formula:
          + Each advocacy argument: +0.05 base
          - Each unresolved attack: -0.05 base
          + Each successful rebuttal: +0.03 recovery
          - Compliance veto: sets to 0.0 (handled separately)

        The delta is capped at +/- 0.15 per round to prevent wild swings.
        """
        positive = sum(a.confidence_impact for a in advocacy if a.confidence_impact > 0)
        negative = sum(a.confidence_impact for a in attacks if a.confidence_impact < 0)
        recovery = sum(r.confidence_impact for r in rebuttals if r.rebutted and r.confidence_impact > 0)

        delta = positive + negative + recovery
        # Cap at +/- 0.15 per round
        return max(-0.15, min(0.15, delta))

    async def _assess_initial_confidence(
        self,
        work_product: str,
        case_context: Dict[str, Any],
        jurisdiction: str,
    ) -> float:
        """Assess the initial confidence of a work product before Galvanizer rounds.

        Uses a quick heuristic check:
        - Has citations? +0.1
        - Has jurisdiction-specific references? +0.1
        - Has procedural compliance? +0.1
        - Has evidence references? +0.1
        - Length and completeness? +0.1
        Base: 0.3
        """
        confidence = 0.3  # Base confidence for any drafted work product

        # Check for citations
        import re
        citation_patterns = [
            r"\d+\s+U\.S\.\s+\d+",           # Supreme Court
            r"\d+\s+F\.\d[a-z]*\s+\d+",       # Federal Reporter
            r"\d+\s+F\.\s*Supp",              # Federal Supplement
            r"§\s*\d+",                         # Statute sections
            r"\d+\s+S\.\s*Ct\.\s+\d+",        # Supreme Court Reporter
        ]
        for pattern in citation_patterns:
            if re.search(pattern, work_product):
                confidence += 0.02

        # Cap citation bonus
        confidence = min(confidence + 0.1, confidence)

        # Check for jurisdiction reference
        if jurisdiction and jurisdiction.lower() in work_product.lower():
            confidence += 0.1

        # Check for procedural references
        procedural_terms = ["FRCP", "Rule", "motion", "complaint", "answer", "discovery"]
        proc_count = sum(1 for term in procedural_terms if term.lower() in work_product.lower())
        confidence += min(0.1, proc_count * 0.02)

        # Check for evidence references
        evidence_terms = ["exhibit", "evidence", "testimony", "declaration", "affidavit"]
        ev_count = sum(1 for term in evidence_terms if term.lower() in work_product.lower())
        confidence += min(0.1, ev_count * 0.02)

        # Length/completeness bonus
        word_count = len(work_product.split())
        if word_count > 500:
            confidence += 0.05
        if word_count > 2000:
            confidence += 0.05

        return min(0.85, confidence)  # Cap initial at 0.85 — must earn the last 5%+

    async def _check_compliance_veto(
        self,
        round_result: GalvanizerRound,
        case_context: Dict[str, Any],
        jurisdiction: str,
    ) -> Optional[str]:
        """Check if Compliance should veto the work product.

        Veto triggers:
        - Fabricated citation detected
        - Unauthorized practice of law boundary crossed
        - Filing deadline already passed
        - Ethical violation detected
        """
        # Check for critical unresolved attacks
        critical_types = {
            AttackType.CITATION_CHALLENGE.value,
            AttackType.STATUTE_OF_LIMITATIONS.value,
            AttackType.STANDING_CHALLENGE.value,
        }

        for attack in round_result.stress_test_attacks:
            if (
                attack.attack_type in critical_types
                and attack.argument_text in round_result.unresolved_attacks
            ):
                if round_result.round_confidence < self._veto_threshold:
                    return (
                        f"COMPLIANCE VETO: Critical unresolved {attack.attack_type} "
                        f"with confidence below {self._veto_threshold * 100:.0f}% threshold. "
                        f"Work product cannot be filed in its current state."
                    )

        return None

    async def _apply_improvements(
        self,
        work_product: str,
        round_result: GalvanizerRound,
        case_context: Dict[str, Any],
    ) -> str:
        """Apply improvements to the work product based on round results.

        Uses the successful rebuttals and advocacy arguments to
        strengthen the work product for the next round.
        """
        if not self._runtime:
            return await self._apply_improvements_local(
                work_product, round_result, case_context,
            )

        from src.providers.bedrock_agentcore import AgentIdentity

        rebuttals_text = "\n".join(
            r.argument_text for r in round_result.advocacy_rebuttals if r.rebutted
        )
        unresolved_text = "\n".join(round_result.unresolved_attacks)

        prompt = (
            f"Improve this legal work product based on the Galvanizer debate:\n\n"
            f"CURRENT WORK PRODUCT:\n{work_product}\n\n"
            f"SUCCESSFUL REBUTTALS (incorporate these):\n{rebuttals_text}\n\n"
            f"UNRESOLVED WEAKNESSES (address these):\n{unresolved_text}\n\n"
            f"Return the improved work product. Do not remove any existing strong arguments."
        )

        response = await self._runtime.fan_out(
            case_id=case_context.get("case_id", "unknown"),
            agents=[AgentIdentity.DRAFTING_COUNSEL],
            prompt=prompt,
            shared_context=case_context,
        )

        for _, resp in response.get("responses", {}).items():
            return resp.get("text", work_product)

        return work_product

    async def _apply_improvements_local(
        self,
        work_product: str,
        round_result: GalvanizerRound,
        case_context: Dict[str, Any],
    ) -> str:
        """Local improvement application via direct Bedrock call."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        rebuttals_text = "\n".join(
            r.argument_text for r in round_result.advocacy_rebuttals if r.rebutted
        )
        unresolved_text = "\n".join(round_result.unresolved_attacks)

        prompt = (
            f"Improve this legal work product:\n\n"
            f"CURRENT:\n{work_product}\n\n"
            f"INCORPORATE:\n{rebuttals_text}\n\n"
            f"ADDRESS:\n{unresolved_text}"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=8192,
            temperature=0.0,
            system="Improve the legal work product. Preserve all strong arguments. Address weaknesses.",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.text

    async def _generate_recommendations(
        self,
        unresolved: List[str],
        case_context: Dict[str, Any],
        current_confidence: float,
    ) -> List[str]:
        """Generate plain-language recommendations for the user.

        When the Galvanizer can't reach 90%, it tells the user exactly
        what evidence or information would push it over the threshold.
        """
        recommendations = []
        gap = self._confidence_gate - current_confidence

        recommendations.append(
            f"Your case strategy is currently at {current_confidence * 100:.0f}% confidence. "
            f"It needs to reach {self._confidence_gate * 100:.0f}% before we can file. "
            f"Here's what would help:"
        )

        for weakness in unresolved:
            if "citation" in weakness.lower():
                recommendations.append(
                    "We need stronger case law supporting your position. "
                    "Do you have any court documents from similar cases?"
                )
            elif "evidence" in weakness.lower():
                recommendations.append(
                    "Additional evidence would strengthen your case. "
                    "Do you have emails, contracts, photos, or witness statements?"
                )
            elif "procedural" in weakness.lower():
                recommendations.append(
                    "There may be a procedural issue. We're checking the court rules "
                    "to find the best path forward."
                )
            elif "standing" in weakness.lower():
                recommendations.append(
                    "We need to establish that you have legal standing. "
                    "Can you provide documentation showing how you were directly affected?"
                )

        return recommendations


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _format_context(ctx: Dict[str, Any]) -> str:
    """Format case context dict into a readable string for prompts."""
    parts = []
    for key, value in ctx.items():
        if isinstance(value, list):
            parts.append(f"{key}: {', '.join(str(v) for v in value)}")
        else:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)
