"""Cyphergy Orchestrator — 5-agent legal co-counsel with WDC debate.

This is the core product: user input flows through Lead Counsel (classification),
fans out to relevant agents, collects responses, runs WDC debate for quality
certification, and returns the certified output to the user.

Flow:
    User Input → Lead Counsel (classify) → Fan-out to agents → Collect responses
    → WDC Debate (all 5 score) → If CERTIFIED: deliver → If REVISION: re-draft
    → Max 3 revision cycles → Deliver or flag for human review

Architecture:
    - Opus 4.6 (1M) orchestrates all agents in dev
    - Bedrock Core (best per agent class) in production
    - CPAA: provider swapped via LLM_PROVIDER env var
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.agents.base_agent import AgentRole, AgentResponse, WDCScore
from src.agents.lead_counsel import LeadCounsel
from src.agents.research_counsel import ResearchCounsel
from src.agents.drafting_counsel import DraftingCounsel
from src.agents.red_team import AdversarialCounsel
from src.agents.compliance_counsel import ComplianceCounsel
from src.orchestrator.wdc import WDCEngine, WDCResult, WDCVerdict
from src.config.settings import get_settings

logger = logging.getLogger("cyphergy.orchestrator")


# ── Models ────────────────────────────────────────────────────────────


class OrchestrationRequest(BaseModel):
    """Input to the orchestrator from the API layer."""

    message: str = Field(description="User's message or query")
    jurisdiction: Optional[str] = Field(
        default=None, description="Legal jurisdiction if known"
    )
    case_context: Optional[dict[str, Any]] = Field(
        default=None, description="Existing case data from the blackboard"
    )


class OrchestrationResult(BaseModel):
    """Complete output from the orchestration pipeline."""

    content: str = Field(description="The certified response text")
    wdc_result: WDCResult = Field(description="WDC scoring details")
    agent_contributions: dict[str, str] = Field(
        default_factory=dict,
        description="Per-agent contribution summaries (role -> summary)",
    )
    revision_cycles: int = Field(
        default=1, description="How many draft-review cycles occurred"
    )
    total_time_ms: float = Field(description="Total processing time in milliseconds")
    task_type: str = Field(description="Classified task type from Lead Counsel")


# ── Orchestrator ──────────────────────────────────────────────────────


class Orchestrator:
    """5-agent legal co-counsel orchestrator with WDC debate.

    Usage::

        orch = Orchestrator()
        result = await orch.run("I received a lawsuit in Louisiana")
    """

    def __init__(self) -> None:
        settings = get_settings()

        # Initialize all 5 agents
        self._lead = LeadCounsel()
        self._research = ResearchCounsel()
        self._drafting = DraftingCounsel()
        self._red_team = AdversarialCounsel()
        self._compliance = ComplianceCounsel()

        # Agent list for WDC debate
        self._agents = [
            self._lead,
            self._research,
            self._drafting,
            self._red_team,
            self._compliance,
        ]

        # WDC engine
        self._wdc = WDCEngine(settings)
        self._max_cycles = settings.wdc_max_revision_cycles

        logger.info(
            "Orchestrator initialized: 5 agents, WDC max_cycles=%d",
            self._max_cycles,
        )

    async def run(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Execute the full orchestration pipeline.

        Steps:
            1. Lead Counsel classifies the task
            2. Route to relevant agents based on classification
            3. Collect agent responses
            4. Run WDC debate on the aggregated output
            5. If REVISION_REQUIRED, re-draft up to max_cycles
            6. Return certified result
        """
        start = time.monotonic()

        # Build shared context (blackboard)
        context = self._build_context(request)

        # Step 1: Lead Counsel classifies the task
        classification = await self._lead.classify_task(
            request.message, context
        )
        task_type = classification.get("task_type", "general")
        agents_needed = classification.get("agents_needed", [r.value for r in AgentRole])

        logger.info(
            "Task classified: type=%s agents=%s",
            task_type,
            agents_needed,
        )

        # Step 2-3: Fan-out to relevant agents and collect responses
        agent_responses = await self._fan_out(
            request.message, context, agents_needed
        )

        # Step 4: Aggregate into a single response
        aggregated = await self._lead.invoke(
            self._build_aggregation_prompt(request.message, agent_responses),
            context,
        )
        draft_content = aggregated.content

        # Step 5: WDC debate cycle (with revisions if needed)
        cycle = 1
        wdc_result = await self._wdc.run_debate(
            draft_content, self._agents, context
        )

        while (
            wdc_result.verdict == WDCVerdict.REVISION_REQUIRED
            and cycle < self._max_cycles
        ):
            cycle += 1
            logger.info(
                "Revision cycle %d: score=%.2f feedback=%s",
                cycle,
                wdc_result.composite_score,
                wdc_result.revision_feedback,
            )

            # Re-draft with feedback
            revision_prompt = self._build_revision_prompt(
                draft_content, wdc_result.revision_feedback or []
            )
            revised = await self._drafting.invoke(revision_prompt, context)
            draft_content = revised.content

            # Re-score
            wdc_result = await self._wdc.run_debate(
                draft_content, self._agents, context
            )

        elapsed_ms = (time.monotonic() - start) * 1000

        return OrchestrationResult(
            content=draft_content,
            wdc_result=wdc_result,
            agent_contributions={
                role: resp.content[:200] for role, resp in agent_responses.items()
            },
            revision_cycles=cycle,
            total_time_ms=round(elapsed_ms, 1),
            task_type=task_type,
        )

    # ── Internal Methods ──────────────────────────────────────────────

    def _build_context(self, request: OrchestrationRequest) -> dict[str, Any]:
        """Build the shared blackboard context for all agents."""
        ctx: dict[str, Any] = {}
        if request.jurisdiction:
            ctx["jurisdiction"] = request.jurisdiction
        if request.case_context:
            ctx.update(request.case_context)
        return ctx

    async def _fan_out(
        self,
        message: str,
        context: dict[str, Any],
        agents_needed: list[str],
    ) -> dict[str, AgentResponse]:
        """Fan-out to multiple agents in parallel and collect responses.

        Only invokes agents listed in agents_needed. Lead Counsel is
        always included as the aggregator.
        """
        agent_map = {
            AgentRole.LEAD_COUNSEL.value: self._lead,
            AgentRole.RESEARCH_COUNSEL.value: self._research,
            AgentRole.DRAFTING_COUNSEL.value: self._drafting,
            AgentRole.RED_TEAM.value: self._red_team,
            AgentRole.COMPLIANCE_COUNSEL.value: self._compliance,
        }

        tasks = {}
        for role_name in agents_needed:
            agent = agent_map.get(role_name)
            if agent and role_name != AgentRole.LEAD_COUNSEL.value:
                tasks[role_name] = agent.invoke(message, context)

        # Run all agents in parallel
        if tasks:
            results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            responses = {}
            for role_name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(
                        "Agent %s failed: %s", role_name, str(result)[:200]
                    )
                    responses[role_name] = AgentResponse(
                        content=f"[Agent {role_name} encountered an error]",
                        role=AgentRole(role_name),
                        confidence=0.0,
                        citations_used=[],
                        flags=["agent_error"],
                    )
                else:
                    responses[role_name] = result
            return responses

        return {}

    def _build_aggregation_prompt(
        self,
        original_message: str,
        agent_responses: dict[str, AgentResponse],
    ) -> str:
        """Build a prompt for Lead Counsel to aggregate agent responses."""
        parts = [
            f"ORIGINAL QUERY: {original_message}",
            "",
            "AGENT RESPONSES (synthesize into a unified, certified response):",
        ]
        for role, resp in agent_responses.items():
            parts.append(f"\n--- {role.upper()} (confidence: {resp.confidence}) ---")
            parts.append(resp.content)
            if resp.citations_used:
                parts.append(f"Citations: {', '.join(resp.citations_used)}")
            if resp.flags:
                parts.append(f"Flags: {', '.join(resp.flags)}")

        parts.append(
            "\n\nSynthesize these into a single, clear response for the user. "
            "Preserve all citations with their verification status. "
            "Flag any disagreements between agents. "
            "Use plain language — the user is a pro se litigant."
        )
        return "\n".join(parts)

    def _build_revision_prompt(
        self,
        draft: str,
        feedback: list[str],
    ) -> str:
        """Build a prompt for Drafting Counsel to revise based on WDC feedback."""
        return (
            f"REVISE THIS DRAFT based on WDC feedback:\n\n"
            f"DRAFT:\n{draft}\n\n"
            f"FEEDBACK:\n" + "\n".join(f"- {f}" for f in feedback) + "\n\n"
            f"Produce an improved version addressing all feedback points. "
            f"Maintain all verified citations. Fix any flagged issues."
        )
