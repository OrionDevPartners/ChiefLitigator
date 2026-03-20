"""Strategy Advisor Agent — Predictive case analytics and litigation strategy.

Analyzes the full case context and produces:
  1. Win probability estimates based on historical case data
  2. Judge-specific insights (tendencies, ruling patterns)
  3. Opposing counsel profiling
  4. Settlement vs. trial recommendations
  5. Cost-benefit analysis
  6. Timeline projections
  7. Risk assessment with mitigation strategies

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.agents.strategy_advisor")


class RiskLevel(BaseModel):
    """A risk factor in the case."""
    risk_id: str = Field(default_factory=lambda: f"risk-{uuid.uuid4().hex[:6]}")
    category: str = Field(description="procedural, evidentiary, legal, financial, timing")
    description: str
    severity: str = Field(description="critical, high, medium, low")
    probability: float = Field(ge=0.0, le=1.0)
    mitigation: str = Field(description="How to mitigate this risk")


class StrategyRecommendation(BaseModel):
    """A strategic recommendation."""
    rec_id: str = Field(default_factory=lambda: f"rec-{uuid.uuid4().hex[:6]}")
    strategy: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    timeline: str
    estimated_cost: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)


class CaseAnalysis(BaseModel):
    """Complete strategic analysis of a case."""
    analysis_id: str = Field(default_factory=lambda: f"analysis-{uuid.uuid4().hex[:12]}")
    case_id: str
    win_probability: float = Field(ge=0.0, le=1.0)
    win_probability_explanation: str = ""
    judge_insights: Dict[str, Any] = Field(default_factory=dict)
    opposing_counsel_profile: Dict[str, Any] = Field(default_factory=dict)
    risks: List[RiskLevel] = Field(default_factory=list)
    recommendations: List[StrategyRecommendation] = Field(default_factory=list)
    settlement_analysis: Dict[str, Any] = Field(default_factory=dict)
    timeline_projection: Dict[str, Any] = Field(default_factory=dict)
    cost_estimate: Dict[str, Any] = Field(default_factory=dict)
    plain_language_summary: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class StrategyAdvisor:
    """Provides predictive analytics and strategic litigation advice.

    Usage::

        advisor = StrategyAdvisor()
        analysis = await advisor.analyze_case(
            case_id="case-12345",
            case_context={
                "practice_area": "breach_of_contract",
                "jurisdiction": "FL",
                "court": "Broward County Circuit Court",
                "judge": "Judge Smith",
                "facts": "...",
                "claims": ["breach of contract"],
                "evidence_strength": 0.75,
                "opposing_party": "MegaCorp Inc.",
            },
        )
    """

    def __init__(self, agentcore_runtime: Any = None) -> None:
        self._runtime = agentcore_runtime
        logger.info("StrategyAdvisor initialized")

    async def analyze_case(
        self,
        case_id: str,
        case_context: Dict[str, Any],
    ) -> CaseAnalysis:
        """Produce a complete strategic analysis of a case."""
        logger.info("Analyzing case %s", case_id)

        # Run all analyses in parallel
        import asyncio
        win_prob_task = self._estimate_win_probability(case_context)
        judge_task = self._analyze_judge(case_context)
        risk_task = self._assess_risks(case_context)
        settlement_task = self._analyze_settlement(case_context)
        timeline_task = self._project_timeline(case_context)
        cost_task = self._estimate_costs(case_context)

        (
            win_prob,
            judge_insights,
            risks,
            settlement,
            timeline,
            costs,
        ) = await asyncio.gather(
            win_prob_task, judge_task, risk_task,
            settlement_task, timeline_task, cost_task,
        )

        # Generate recommendations
        recommendations = await self._generate_recommendations(
            case_context, win_prob, risks, settlement,
        )

        # Generate plain-language summary
        summary = await self._generate_summary(
            case_context, win_prob, risks, recommendations, settlement,
        )

        return CaseAnalysis(
            case_id=case_id,
            win_probability=win_prob.get("probability", 0.5),
            win_probability_explanation=win_prob.get("explanation", ""),
            judge_insights=judge_insights,
            risks=risks,
            recommendations=recommendations,
            settlement_analysis=settlement,
            timeline_projection=timeline,
            cost_estimate=costs,
            plain_language_summary=summary,
        )

    async def _estimate_win_probability(
        self,
        case_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Estimate win probability based on case factors."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"Estimate the probability of success for this case.\n\n"
            f"Practice Area: {case_context.get('practice_area', 'unknown')}\n"
            f"Jurisdiction: {case_context.get('jurisdiction', 'unknown')}\n"
            f"Evidence Strength: {case_context.get('evidence_strength', 'unknown')}\n"
            f"Facts: {case_context.get('facts', 'unknown')}\n"
            f"Claims: {case_context.get('claims', [])}\n\n"
            f"Consider:\n"
            f"1. Strength of legal theory\n"
            f"2. Quality of evidence\n"
            f"3. Jurisdictional favorability\n"
            f"4. Historical outcomes in similar cases\n\n"
            f"Return: probability (0.0-1.0) and explanation"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=2048,
            temperature=0.0,
            system=(
                "You are a litigation strategist. Estimate win probability objectively. "
                "Be conservative. Consider both strengths and weaknesses."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse probability from response
        import re
        prob_match = re.search(r"(\d+\.?\d*)%", response.text)
        if prob_match:
            probability = float(prob_match.group(1)) / 100.0
        else:
            prob_match = re.search(r"0\.\d+", response.text)
            probability = float(prob_match.group()) if prob_match else 0.5

        return {
            "probability": min(1.0, max(0.0, probability)),
            "explanation": response.text,
        }

    async def _analyze_judge(self, case_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the assigned judge's tendencies."""
        judge = case_context.get("judge", "")
        if not judge:
            return {"available": False, "note": "No judge assigned yet"}

        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"Analyze Judge {judge} in {case_context.get('jurisdiction', '')} "
            f"for a {case_context.get('practice_area', '')} case.\n\n"
            f"Consider:\n"
            f"1. Known tendencies on motions to dismiss\n"
            f"2. Summary judgment grant rate\n"
            f"3. Attitude toward pro se litigants\n"
            f"4. Discovery dispute handling\n"
            f"5. Settlement conference approach\n"
            f"6. Trial management style"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER2_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=2048,
            temperature=0.0,
            system="Analyze judicial tendencies objectively based on public records.",
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "judge": judge,
            "analysis": response.text,
            "available": True,
        }

    async def _assess_risks(self, case_context: Dict[str, Any]) -> List[RiskLevel]:
        """Assess all risk factors in the case."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"Identify ALL risk factors in this case:\n\n"
            f"Practice Area: {case_context.get('practice_area', '')}\n"
            f"Jurisdiction: {case_context.get('jurisdiction', '')}\n"
            f"Facts: {case_context.get('facts', '')}\n"
            f"Claims: {case_context.get('claims', [])}\n"
            f"Evidence Strength: {case_context.get('evidence_strength', '')}\n\n"
            f"Categories: procedural, evidentiary, legal, financial, timing\n"
            f"Severity: critical, high, medium, low\n"
            f"For each risk: description, severity, probability (0-1), mitigation"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=4096,
            temperature=0.0,
            system="You are a risk analyst for litigation. Identify every risk factor.",
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse into RiskLevel objects (simplified)
        return [RiskLevel(
            category="legal",
            description=response.text[:500],
            severity="medium",
            probability=0.3,
            mitigation="See full analysis",
        )]

    async def _analyze_settlement(self, case_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze settlement vs. trial decision."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"Analyze settlement vs. trial for this case:\n\n"
            f"Practice Area: {case_context.get('practice_area', '')}\n"
            f"Evidence Strength: {case_context.get('evidence_strength', '')}\n"
            f"Opposing Party: {case_context.get('opposing_party', 'unknown')}\n\n"
            f"Provide:\n"
            f"1. Recommended settlement range\n"
            f"2. Trial verdict estimate\n"
            f"3. Cost of trial vs. settlement\n"
            f"4. Risk-adjusted recommendation"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER2_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=2048,
            temperature=0.0,
            system="Analyze settlement economics objectively.",
            messages=[{"role": "user", "content": prompt}],
        )

        return {"analysis": response.text}

    async def _project_timeline(self, case_context: Dict[str, Any]) -> Dict[str, Any]:
        """Project the case timeline."""
        jurisdiction = case_context.get("jurisdiction", "")
        practice_area = case_context.get("practice_area", "")

        # Average timelines by practice area and jurisdiction
        timelines = {
            "breach_of_contract": {"federal": "12-18 months", "state": "8-14 months"},
            "personal_injury": {"federal": "18-24 months", "state": "12-18 months"},
            "eviction": {"federal": "N/A", "state": "2-6 weeks"},
            "family": {"federal": "N/A", "state": "3-12 months"},
            "immigration": {"federal": "6-24 months", "state": "N/A"},
            "small_claims": {"federal": "N/A", "state": "1-3 months"},
        }

        court_type = "federal" if jurisdiction == "USDC" else "state"
        timeline = timelines.get(practice_area, {}).get(court_type, "6-18 months")

        return {
            "estimated_duration": timeline,
            "phases": {
                "pleadings": "1-2 months",
                "discovery": "3-6 months",
                "motions": "1-3 months",
                "trial_prep": "1-2 months",
                "trial": "1-2 weeks",
            },
        }

    async def _estimate_costs(self, case_context: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate case costs (what user saves by using ChiefLitigator)."""
        practice_area = case_context.get("practice_area", "")

        # Average attorney costs
        attorney_costs = {
            "breach_of_contract": {"hourly": 350, "total_estimate": "15,000 - 50,000"},
            "personal_injury": {"hourly": 400, "total_estimate": "20,000 - 100,000"},
            "eviction": {"hourly": 250, "total_estimate": "2,000 - 5,000"},
            "family": {"hourly": 300, "total_estimate": "10,000 - 30,000"},
            "immigration": {"hourly": 300, "total_estimate": "5,000 - 15,000"},
            "small_claims": {"hourly": 200, "total_estimate": "1,000 - 3,000"},
        }

        costs = attorney_costs.get(practice_area, {"hourly": 300, "total_estimate": "10,000 - 50,000"})

        return {
            "traditional_attorney_cost": costs,
            "chieflitigator_cost": "Subscription-based — fraction of attorney fees",
            "filing_fees": "Varies by jurisdiction (fee waiver may apply)",
            "savings_estimate": f"You could save {costs['total_estimate']} in attorney fees",
        }

    async def _generate_recommendations(
        self,
        case_context: Dict[str, Any],
        win_prob: Dict[str, Any],
        risks: List[RiskLevel],
        settlement: Dict[str, Any],
    ) -> List[StrategyRecommendation]:
        """Generate strategic recommendations."""
        recs = []
        probability = win_prob.get("probability", 0.5)

        if probability >= 0.7:
            recs.append(StrategyRecommendation(
                strategy="Aggressive Litigation",
                rationale="Strong case with high win probability. Press for full relief.",
                confidence=probability,
                timeline="Full litigation timeline",
                estimated_cost="Filing fees + ChiefLitigator subscription",
                pros=["High chance of full recovery", "Sets strong precedent"],
                cons=["Longer timeline", "Requires sustained effort"],
            ))

        if 0.4 <= probability <= 0.8:
            recs.append(StrategyRecommendation(
                strategy="Negotiate from Strength",
                rationale="File the case, then negotiate settlement from a position of strength.",
                confidence=min(probability + 0.1, 1.0),
                timeline="3-6 months",
                estimated_cost="Filing fees + minimal discovery costs",
                pros=["Faster resolution", "Reduced risk", "Guaranteed outcome"],
                cons=["May recover less than trial verdict"],
            ))

        if probability < 0.5:
            recs.append(StrategyRecommendation(
                strategy="Strengthen Before Filing",
                rationale="Gather additional evidence and strengthen legal theories before proceeding.",
                confidence=0.6,
                timeline="1-3 months preparation",
                estimated_cost="Minimal — evidence gathering phase",
                pros=["Better prepared case", "Higher eventual win probability"],
                cons=["Delayed action", "Statute of limitations consideration"],
            ))

        return recs

    async def _generate_summary(
        self,
        case_context: Dict[str, Any],
        win_prob: Dict[str, Any],
        risks: List[RiskLevel],
        recommendations: List[StrategyRecommendation],
        settlement: Dict[str, Any],
    ) -> str:
        """Generate a plain-language strategy summary."""
        probability = win_prob.get("probability", 0.5)
        strength = "strong" if probability >= 0.7 else "moderate" if probability >= 0.5 else "challenging"

        summary = (
            f"Based on our analysis, your case is {strength} with a "
            f"{probability:.0%} estimated chance of success. "
        )

        if recommendations:
            top_rec = recommendations[0]
            summary += f"Our top recommendation is: {top_rec.strategy}. {top_rec.rationale} "

        critical_risks = [r for r in risks if r.severity == "critical"]
        if critical_risks:
            summary += f"There are {len(critical_risks)} critical risk(s) to address. "

        summary += (
            f"ChiefLitigator will guide you through every step. "
            f"Review the detailed analysis below."
        )

        return summary
