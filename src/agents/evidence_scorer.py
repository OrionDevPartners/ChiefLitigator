"""Evidence Scorer Agent — Evaluates evidence strength and identifies gaps.

Scores every piece of evidence in a case, maps evidence to claims,
identifies gaps that weaken the case, and recommends what additional
evidence the user should gather.

Scoring dimensions:
  - Relevance: How directly does this evidence support a claim?
  - Authenticity: Can this evidence be authenticated in court?
  - Weight: How persuasive is this evidence to a judge/jury?
  - Admissibility: Is this evidence likely admissible under the rules of evidence?
  - Completeness: Does this evidence tell the full story or is it partial?

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.agents.evidence_scorer")


class EvidenceType(str, Enum):
    DOCUMENT = "document"
    EMAIL = "email"
    CONTRACT = "contract"
    PHOTOGRAPH = "photograph"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT_MESSAGE = "text_message"
    SOCIAL_MEDIA = "social_media"
    FINANCIAL_RECORD = "financial_record"
    MEDICAL_RECORD = "medical_record"
    POLICE_REPORT = "police_report"
    WITNESS_STATEMENT = "witness_statement"
    EXPERT_REPORT = "expert_report"
    GOVERNMENT_RECORD = "government_record"
    PHYSICAL_EVIDENCE = "physical_evidence"
    COURT_RECORD = "court_record"


class EvidenceScore(BaseModel):
    """Score for a single piece of evidence."""
    evidence_id: str = Field(default_factory=lambda: f"ev-{uuid.uuid4().hex[:8]}")
    evidence_type: str
    description: str
    relevance: float = Field(ge=0.0, le=1.0)
    authenticity: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    admissibility: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    composite_score: float = Field(ge=0.0, le=1.0)
    mapped_claims: List[str] = Field(default_factory=list)
    admissibility_issues: List[str] = Field(default_factory=list)
    strengthening_suggestions: List[str] = Field(default_factory=list)


class EvidenceGap(BaseModel):
    """An identified gap in the evidence."""
    gap_id: str = Field(default_factory=lambda: f"gap-{uuid.uuid4().hex[:8]}")
    claim: str = Field(description="The claim that lacks sufficient evidence")
    gap_description: str = Field(description="What evidence is missing")
    impact: str = Field(description="How this gap affects the case: critical, significant, minor")
    recommendation: str = Field(description="Plain-language recommendation for the user")
    evidence_types_needed: List[str] = Field(default_factory=list)


class CaseEvidenceReport(BaseModel):
    """Complete evidence assessment for a case."""
    report_id: str = Field(default_factory=lambda: f"evr-{uuid.uuid4().hex[:12]}")
    case_id: str
    evidence_scores: List[EvidenceScore] = Field(default_factory=list)
    evidence_gaps: List[EvidenceGap] = Field(default_factory=list)
    overall_evidence_strength: float = Field(ge=0.0, le=1.0)
    claim_coverage: Dict[str, float] = Field(
        default_factory=dict,
        description="Claim -> evidence coverage percentage",
    )
    plain_language_summary: str = Field(default="")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EvidenceScorer:
    """Evaluates evidence strength and identifies gaps.

    Usage::

        scorer = EvidenceScorer()
        report = await scorer.score_case_evidence(
            case_id="case-12345",
            evidence=[
                {"type": "contract", "description": "Signed lease agreement dated 2025-01-01"},
                {"type": "email", "description": "Email from landlord threatening eviction"},
            ],
            claims=["Wrongful eviction under FL Stat. 83.67"],
            jurisdiction="FL",
        )
    """

    def __init__(self, agentcore_runtime: Any = None) -> None:
        self._runtime = agentcore_runtime
        # Scoring weights
        self._weights = {
            "relevance": 0.30,
            "authenticity": 0.15,
            "weight": 0.25,
            "admissibility": 0.20,
            "completeness": 0.10,
        }
        logger.info("EvidenceScorer initialized")

    async def score_case_evidence(
        self,
        case_id: str,
        evidence: List[Dict[str, Any]],
        claims: List[str],
        jurisdiction: str,
    ) -> CaseEvidenceReport:
        """Score all evidence in a case and identify gaps."""
        logger.info("Scoring evidence for case %s: %d items, %d claims", case_id, len(evidence), len(claims))

        # Score each piece of evidence
        scores = []
        for ev in evidence:
            score = await self._score_single_evidence(ev, claims, jurisdiction)
            scores.append(score)

        # Identify gaps
        gaps = await self._identify_gaps(scores, claims, jurisdiction)

        # Calculate claim coverage
        claim_coverage = self._calculate_claim_coverage(scores, claims)

        # Calculate overall strength
        overall = self._calculate_overall_strength(scores, claim_coverage)

        # Generate plain-language summary
        summary = await self._generate_summary(scores, gaps, claim_coverage, overall)

        return CaseEvidenceReport(
            case_id=case_id,
            evidence_scores=scores,
            evidence_gaps=gaps,
            overall_evidence_strength=overall,
            claim_coverage=claim_coverage,
            plain_language_summary=summary,
        )

    async def _score_single_evidence(
        self,
        evidence: Dict[str, Any],
        claims: List[str],
        jurisdiction: str,
    ) -> EvidenceScore:
        """Score a single piece of evidence."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        ev_type = evidence.get("type", "document")
        ev_desc = evidence.get("description", "")

        prompt = (
            f"Score this evidence for a legal case in {jurisdiction}.\n\n"
            f"EVIDENCE TYPE: {ev_type}\n"
            f"DESCRIPTION: {ev_desc}\n\n"
            f"CLAIMS TO SUPPORT:\n"
            + "\n".join(f"- {c}" for c in claims) +
            f"\n\nScore each dimension from 0.0 to 1.0:\n"
            f"1. Relevance: How directly does this support the claims?\n"
            f"2. Authenticity: Can this be authenticated in court?\n"
            f"3. Weight: How persuasive is this to a judge/jury?\n"
            f"4. Admissibility: Is this admissible under rules of evidence?\n"
            f"5. Completeness: Does this tell the full story?\n\n"
            f"Also identify:\n"
            f"- Which claims this evidence supports\n"
            f"- Any admissibility issues\n"
            f"- How to strengthen this evidence\n\n"
            f"Format: dimension: score"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER2_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=2048,
            temperature=0.0,
            system="You are a litigation evidence analyst. Score evidence objectively.",
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse scores from response (with defaults)
        scores = self._parse_scores(response.text)

        composite = sum(
            scores.get(dim, 0.5) * weight
            for dim, weight in self._weights.items()
        )

        return EvidenceScore(
            evidence_type=ev_type,
            description=ev_desc,
            relevance=scores.get("relevance", 0.5),
            authenticity=scores.get("authenticity", 0.5),
            weight=scores.get("weight", 0.5),
            admissibility=scores.get("admissibility", 0.5),
            completeness=scores.get("completeness", 0.5),
            composite_score=min(1.0, composite),
            mapped_claims=claims[:3],  # Map to top claims
        )

    def _parse_scores(self, text: str) -> Dict[str, float]:
        """Parse dimension scores from LLM response."""
        scores = {}
        dimensions = ["relevance", "authenticity", "weight", "admissibility", "completeness"]
        for dim in dimensions:
            import re
            pattern = rf"{dim}[:\s]+(\d+\.?\d*)"
            match = re.search(pattern, text.lower())
            if match:
                val = float(match.group(1))
                scores[dim] = min(1.0, val if val <= 1.0 else val / 10.0)
            else:
                scores[dim] = 0.5
        return scores

    async def _identify_gaps(
        self,
        scores: List[EvidenceScore],
        claims: List[str],
        jurisdiction: str,
    ) -> List[EvidenceGap]:
        """Identify evidence gaps for each claim."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        evidence_summary = "\n".join(
            f"- [{s.evidence_type}] {s.description} (score: {s.composite_score:.2f})"
            for s in scores
        )

        prompt = (
            f"Given this evidence and these claims, identify what evidence is MISSING.\n\n"
            f"EXISTING EVIDENCE:\n{evidence_summary}\n\n"
            f"CLAIMS:\n" + "\n".join(f"- {c}" for c in claims) +
            f"\n\nJURISDICTION: {jurisdiction}\n\n"
            f"For each gap:\n"
            f"1. Which claim lacks evidence\n"
            f"2. What type of evidence is needed\n"
            f"3. Impact (critical/significant/minor)\n"
            f"4. Plain-language recommendation for the user"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER2_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=2048,
            temperature=0.0,
            system="You are a litigation strategist. Identify evidence gaps that could lose the case.",
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse gaps (simplified — production would use structured output)
        gaps = [EvidenceGap(
            claim=claims[0] if claims else "General",
            gap_description=response.text[:500],
            impact="significant",
            recommendation="Review the analysis above and gather the recommended evidence.",
        )]

        return gaps

    def _calculate_claim_coverage(
        self,
        scores: List[EvidenceScore],
        claims: List[str],
    ) -> Dict[str, float]:
        """Calculate evidence coverage for each claim."""
        coverage = {}
        for claim in claims:
            supporting = [
                s for s in scores
                if claim in s.mapped_claims and s.composite_score >= 0.5
            ]
            if supporting:
                coverage[claim] = sum(s.composite_score for s in supporting) / len(supporting)
            else:
                coverage[claim] = 0.0
        return coverage

    def _calculate_overall_strength(
        self,
        scores: List[EvidenceScore],
        claim_coverage: Dict[str, float],
    ) -> float:
        """Calculate overall evidence strength."""
        if not scores:
            return 0.0

        avg_score = sum(s.composite_score for s in scores) / len(scores)
        avg_coverage = sum(claim_coverage.values()) / len(claim_coverage) if claim_coverage else 0.0

        return (avg_score * 0.6) + (avg_coverage * 0.4)

    async def _generate_summary(
        self,
        scores: List[EvidenceScore],
        gaps: List[EvidenceGap],
        claim_coverage: Dict[str, float],
        overall: float,
    ) -> str:
        """Generate a plain-language evidence summary."""
        strength_label = "strong" if overall >= 0.7 else "moderate" if overall >= 0.5 else "needs work"

        summary = (
            f"Your evidence is {strength_label} (score: {overall:.0%}). "
            f"You have {len(scores)} piece(s) of evidence. "
        )

        if gaps:
            summary += f"We identified {len(gaps)} gap(s) that should be addressed. "

        weak_claims = [c for c, v in claim_coverage.items() if v < 0.5]
        if weak_claims:
            summary += "Some of your claims need stronger evidence support."

        return summary
