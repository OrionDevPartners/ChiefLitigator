"""Lead Counsel agent — The Strategist.

Agent 1 in the Cyphergy 5-agent architecture.
Responsible for: strategy, case command, user interface, task classification,
agent routing, response aggregation, and final approval.

Weight: 30% in WDC scoring. No veto power.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base_agent import (
    AgentConfig,
    AgentResponse,
    AgentRole,
    BaseAgent,
    WDCScore,
)

logger = logging.getLogger(__name__)

LEAD_COUNSEL_SYSTEM_PROMPT = """\
You are Lead Counsel, the principal strategist and supervising attorney-agent \
in the Cyphergy Legal AI system. You carry 30% weight in the Weighted Debate \
Consensus (WDC) scoring process.

YOUR ROLE:
- You are the case commander. Every user interaction begins with you.
- You classify incoming requests, determine which specialist agents are needed, \
  and route tasks accordingly.
- You synthesize and present outputs from all agents into clear, actionable \
  guidance for pro se litigants (people representing themselves in court).
- You ensure every response is grounded in specific legal authority — statutes, \
  rules of procedure, case law — with proper citations.

CORE CAPABILITIES:
1. TASK CLASSIFICATION: Analyze user input and categorize it (case intake, \
   legal research, document drafting, motion practice, deadline management, \
   settlement analysis, strategy review).
2. AGENT ROUTING: Determine which of the 5 agents should handle each subtask: \
   Research Counsel (legal research, case law), Drafting Counsel (document \
   preparation), Red Team (adversarial review, counterarguments), Compliance \
   Counsel (ethical/procedural compliance, with VETO authority).
3. RESPONSE AGGREGATION: Merge multi-agent outputs into a coherent, \
   prioritized action plan.
4. CONFIDENCE FLAGGING: Every assertion must include a confidence level. \
   Use the format "Confidence: 0.XX" where XX represents your certainty.

OUTPUT STANDARDS:
- Write in clear, plain language accessible to non-lawyers.
- When using legal terminology, immediately follow with a plain-language \
  explanation in parentheses.
- Always structure responses with numbered action items when applicable.
- Flag all deadlines prominently with "DEADLINE:" prefix.
- Flag all risks prominently with "RISK:" prefix.
- Include jurisdiction-specific information when the jurisdiction is known.

CONFIDENCE CALIBRATION:
- 0.90-1.00: Black-letter law, well-settled procedure, statutory text
- 0.70-0.89: Strong authority but fact-dependent or jurisdiction-variant
- 0.50-0.69: Reasonable legal position but genuinely debatable
- 0.30-0.49: Weak position, significant contrary authority exists
- 0.00-0.29: Speculative, no clear legal basis, flag for attorney review

MANDATORY DISCLAIMER:
You must include this at the end of every user-facing response:
"IMPORTANT: Cyphergy is a legal research and document preparation tool, not a \
law firm or attorney. This output does not constitute legal advice. For matters \
involving liberty, significant financial exposure, or complex litigation, \
consult a licensed attorney in your jurisdiction."

VERIFICATION CHAINS:
No output you produce should advance to the user without verification by at \
least one other agent. When operating solo (before other agents are online), \
apply self-verification by re-examining your output against the scoring criteria \
and explicitly noting any gaps.

When asked to classify a task, respond in EXACTLY this JSON format:
{
    "task_type": "<CASE_INTAKE|LEGAL_RESEARCH|DOCUMENT_DRAFTING|MOTION_PRACTICE|DEADLINE_CHECK|SETTLEMENT_ANALYSIS|STRATEGY_REVIEW>",
    "agents_needed": ["<agent_role_1>", "<agent_role_2>"],
    "urgency": "<low|medium|high|critical>",
    "reasoning": "<why this classification>"
}
"""


class TaskType(str, Enum):
    """Classification categories for user input."""

    CASE_INTAKE = "CASE_INTAKE"
    LEGAL_RESEARCH = "LEGAL_RESEARCH"
    DOCUMENT_DRAFTING = "DOCUMENT_DRAFTING"
    MOTION_PRACTICE = "MOTION_PRACTICE"
    DEADLINE_CHECK = "DEADLINE_CHECK"
    SETTLEMENT_ANALYSIS = "SETTLEMENT_ANALYSIS"
    STRATEGY_REVIEW = "STRATEGY_REVIEW"


class Urgency(str, Enum):
    """Urgency levels for task classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskClassification(BaseModel):
    """Result of Lead Counsel classifying a user's request."""

    task_type: TaskType = Field(description="The classified task category")
    agents_needed: list[AgentRole] = Field(
        description="Which agents should be involved in handling this task",
    )
    urgency: Urgency = Field(description="How time-sensitive this task is")
    reasoning: str = Field(description="Why Lead Counsel chose this classification")


class LeadCounsel(BaseAgent):
    """Agent 1: Lead Counsel -- Strategy, case command, user interface, final approval.

    Weight: 30% in WDC scoring. No veto power.

    Lead Counsel is the orchestrator of the entire Cyphergy system. Every user
    interaction starts here. It classifies tasks, routes them to specialist
    agents, and aggregates multi-agent responses into actionable output.
    """

    def __init__(self) -> None:
        config = AgentConfig(
            role=AgentRole.LEAD_COUNSEL,
            weight=0.30,
            has_veto=False,
            system_prompt=LEAD_COUNSEL_SYSTEM_PROMPT,
        )
        super().__init__(config)

    async def classify_task(self, user_input: str) -> TaskClassification:
        """Classify user input into a task type and determine agent routing.

        Parameters
        ----------
        user_input:
            Raw text from the user describing their legal situation or request.

        Returns
        -------
        TaskClassification with the task type, required agents, urgency, and reasoning.
        """
        classification_prompt = (
            "Classify the following user request. Respond with ONLY the JSON object, "
            "no other text before or after it.\n\n"
            f"USER REQUEST:\n{user_input}"
        )

        messages = self._build_messages(classification_prompt, None)

        raw = await self._call_model(
            messages,
            max_tokens=512,
            temperature=0.1,
        )

        return self._parse_classification(raw)

    async def aggregate_responses(
        self,
        responses: list[AgentResponse],
        original_request: str = "",
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Aggregate multiple agent responses into a single coherent output.

        Lead Counsel reviews all specialist outputs, resolves conflicts,
        prioritizes action items, and produces a unified response for the user.

        Parameters
        ----------
        responses:
            List of AgentResponse objects from specialist agents.
        original_request:
            The user's original input that triggered the multi-agent workflow.
        context:
            Optional blackboard context for situational awareness.

        Returns
        -------
        A unified AgentResponse from Lead Counsel.
        """
        agent_summaries: list[str] = []
        all_citations: list[str] = []
        all_flags: list[str] = []

        for resp in responses:
            agent_summaries.append(
                f"--- {resp.role.value.upper()} (confidence: {resp.confidence:.2f}) ---\n"
                f"{resp.content}\n"
            )
            all_citations.extend(resp.citations_used)
            all_flags.extend(resp.flags)

        aggregation_prompt = (
            "You are aggregating outputs from multiple specialist agents into a single, "
            "coherent response for the user. Synthesize the information, resolve any "
            "conflicts between agents, prioritize action items by urgency, and present "
            "the result in clear, actionable language.\n\n"
            f"ORIGINAL USER REQUEST:\n{original_request}\n\n"
            "AGENT OUTPUTS:\n" + "\n".join(agent_summaries)
        )

        result = await self.invoke(aggregation_prompt, context)

        unique_citations = list(dict.fromkeys(all_citations + result.citations_used))
        unique_flags = list(dict.fromkeys(all_flags + result.flags))

        return AgentResponse(
            content=result.content,
            role=AgentRole.LEAD_COUNSEL,
            confidence=result.confidence,
            citations_used=unique_citations,
            flags=unique_flags,
            agent_id=self.agent_id,
            elapsed_seconds=result.elapsed_seconds,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    async def compute_wdc_composite(
        self,
        scores: list[WDCScore],
    ) -> dict[str, Any]:
        """Compute the Weighted Debate Consensus composite score.

        Parameters
        ----------
        scores:
            WDC scores from all participating agents.

        Returns
        -------
        Dict with composite_score, certification_level, veto_active, and breakdown.

        Certification thresholds:
        - 8.5+: CERTIFIED
        - 7.0-8.4: CERTIFIED_WITH_NOTES
        - 5.0-6.9: NEEDS_REVISION
        - <5.0: REJECTED
        """
        if not scores:
            return {
                "composite_score": 0.0,
                "certification_level": "NO_SCORES",
                "veto_active": False,
                "breakdown": [],
            }

        veto_active = any(s.veto for s in scores)
        total_weight = sum(s.scorer_weight for s in scores)

        if total_weight == 0:
            composite = 0.0
        else:
            composite = sum(s.weighted_score for s in scores) / total_weight

        composite = round(composite, 3)

        if veto_active:
            certification = "VETOED"
        elif composite >= 8.5:
            certification = "CERTIFIED"
        elif composite >= 7.0:
            certification = "CERTIFIED_WITH_NOTES"
        elif composite >= 5.0:
            certification = "NEEDS_REVISION"
        else:
            certification = "REJECTED"

        breakdown = [
            {
                "agent": s.scorer_role.value,
                "score": s.score,
                "weight": s.scorer_weight,
                "weighted_contribution": round(s.weighted_score, 3),
                "flags": s.flags,
                "veto": s.veto,
            }
            for s in scores
        ]

        return {
            "composite_score": composite,
            "certification_level": certification,
            "veto_active": veto_active,
            "breakdown": breakdown,
        }

    def _parse_classification(self, raw: str) -> TaskClassification:
        """Parse the LLM's JSON classification response into a TaskClassification."""
        json_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if not json_match:
            logger.warning("No JSON found in classification response, using defaults")
            return TaskClassification(
                task_type=TaskType.STRATEGY_REVIEW,
                agents_needed=[AgentRole.LEAD_COUNSEL, AgentRole.RESEARCH_COUNSEL],
                urgency=Urgency.MEDIUM,
                reasoning="Unable to parse classification; defaulting to strategy review.",
            )

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in classification response, using defaults")
            return TaskClassification(
                task_type=TaskType.STRATEGY_REVIEW,
                agents_needed=[AgentRole.LEAD_COUNSEL, AgentRole.RESEARCH_COUNSEL],
                urgency=Urgency.MEDIUM,
                reasoning="Unable to parse classification; defaulting to strategy review.",
            )

        task_type_str = data.get("task_type", "STRATEGY_REVIEW").upper()
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.STRATEGY_REVIEW

        raw_agents = data.get("agents_needed", [])
        agents_needed: list[AgentRole] = []
        for agent_str in raw_agents:
            try:
                agents_needed.append(AgentRole(agent_str))
            except ValueError:
                logger.debug("Unknown agent role in classification: %s", agent_str)

        if not agents_needed:
            agents_needed = [AgentRole.LEAD_COUNSEL]

        urgency_str = data.get("urgency", "medium").lower()
        try:
            urgency = Urgency(urgency_str)
        except ValueError:
            urgency = Urgency.MEDIUM

        reasoning = data.get("reasoning", "No reasoning provided.")

        return TaskClassification(
            task_type=task_type,
            agents_needed=agents_needed,
            urgency=urgency,
            reasoning=reasoning,
        )
