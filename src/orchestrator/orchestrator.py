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
from src.errors import AgentError, LLMProviderError
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
    wdc_result: Optional[WDCResult] = Field(
        default=None,
        description=(
            "WDC scoring details. None if the WDC debate failed — in "
            "that case the draft is delivered uncertified and the "
            "degraded_agents list will contain relevant context."
        ),
    )
    agent_contributions: dict[str, str] = Field(
        default_factory=dict,
        description="Per-agent contribution summaries (role -> summary)",
    )
    degraded_agents: list[str] = Field(
        default_factory=list,
        description=(
            "Roles of agents that failed during this request. Their "
            "contributions are absent from the response. The pipeline "
            "continued with the remaining agents."
        ),
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
        """Execute the full orchestration pipeline with graceful degradation.

        Steps:
            1. Lead Counsel classifies the task
            2. Route to relevant agents based on classification
            3. Collect agent responses (failed agents are skipped, not fatal)
            4. Run WDC debate on the aggregated output
            5. If REVISION_REQUIRED, re-draft up to max_cycles
            6. Return certified result with degraded agent info

        Error handling:
            - If Lead Counsel classification fails, falls back to
              invoking all agents with task_type="general".
            - If individual agents fail during fan-out, they are
              recorded in ``degraded_agents`` and the pipeline continues.
            - If the aggregation step fails, re-raises as LLMProviderError.
            - If the WDC debate fails, delivers the draft without
              WDC certification and logs the failure.
            - Agent roles are logged on failure; user data is never
              included in error logs (@M:010).
        """
        start = time.monotonic()
        degraded_agents: list[str] = []

        # Step 0: LLM Guardrails — check for jailbreak before any agent sees the input
        from src.security.llm_guardrails import enforce_guardrails, check_input
        is_safe, deflection = check_input(request.message)
        if not is_safe:
            elapsed_ms = (time.monotonic() - start) * 1000
            return OrchestrationResult(
                content=deflection or "I'm Cyphergy, a legal analysis tool. How can I help with your legal matter?",
                wdc_result=None,  # type: ignore[arg-type]
                agent_contributions={},
                degraded_agents=[],
                revision_cycles=0,
                total_time_ms=round(elapsed_ms, 1),
                task_type="jailbreak_blocked",
            )

        # Build shared context (blackboard)
        context = self._build_context(request)

        # Step 1: Lead Counsel classifies the task
        # If classification fails, fall back to all agents with "general" type.
        task_type = "general"
        agents_needed = [r.value for r in AgentRole]

        try:
            classification = await self._lead.classify_task(
                request.message, context
            )
            task_type = classification.get("task_type", "general")
            agents_needed = classification.get(
                "agents_needed", [r.value for r in AgentRole]
            )
        except Exception as exc:
            logger.error(
                "classification_failed | role=lead_counsel error_type=%s error=%s | falling back to all agents",
                type(exc).__name__,
                str(exc)[:200],
            )
            degraded_agents.append(AgentRole.LEAD_COUNSEL.value)

        logger.info(
            "Task classified: type=%s agents=%s degraded=%s",
            task_type,
            agents_needed,
            degraded_agents,
        )

        # Step 2-3: Fan-out to relevant agents and collect responses.
        # Individual agent failures are handled inside _fan_out and
        # recorded in the returned dict (with agent_error flag).
        agent_responses, fan_out_failures = await self._fan_out(
            request.message, context, agents_needed
        )
        degraded_agents.extend(fan_out_failures)

        # If ALL agents failed, we cannot produce useful output.
        if not agent_responses:
            raise LLMProviderError(
                "All agents failed during fan-out — cannot produce a response"
            )

        # Step 4: Aggregate into a single response.
        # This is the critical step — if Lead Counsel cannot aggregate,
        # the request cannot succeed.
        try:
            aggregation_prompt = self._build_aggregation_prompt(
                request.message, agent_responses, degraded_agents
            )
            aggregated = await self._lead.invoke(aggregation_prompt, context)
            draft_content = aggregated.content
        except Exception as exc:
            logger.error(
                "aggregation_failed | role=lead_counsel error_type=%s error=%s",
                type(exc).__name__,
                str(exc)[:200],
            )
            raise LLMProviderError(
                "Lead Counsel aggregation failed — cannot produce a response"
            ) from exc

        # Step 5: WDC debate cycle (with revisions if needed).
        # If WDC debate fails, deliver the un-certified draft and log the failure.
        cycle = 1
        wdc_result: Optional[WDCResult] = None

        try:
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

                # Re-draft with feedback.  If drafting fails during a
                # revision cycle, break out and deliver the previous draft.
                try:
                    revision_prompt = self._build_revision_prompt(
                        draft_content, wdc_result.revision_feedback or []
                    )
                    revised = await self._drafting.invoke(revision_prompt, context)
                    draft_content = revised.content
                except Exception as rev_exc:
                    logger.error(
                        "revision_failed | role=drafting_counsel cycle=%d error_type=%s error=%s",
                        cycle,
                        type(rev_exc).__name__,
                        str(rev_exc)[:200],
                    )
                    degraded_agents.append(AgentRole.DRAFTING_COUNSEL.value)
                    break

                # Re-score
                try:
                    wdc_result = await self._wdc.run_debate(
                        draft_content, self._agents, context
                    )
                except Exception as wdc_exc:
                    logger.error(
                        "wdc_rescore_failed | cycle=%d error_type=%s error=%s",
                        cycle,
                        type(wdc_exc).__name__,
                        str(wdc_exc)[:200],
                    )
                    wdc_result = None
                    break

        except Exception as wdc_exc:
            logger.error(
                "wdc_debate_failed | error_type=%s error=%s | delivering uncertified draft",
                type(wdc_exc).__name__,
                str(wdc_exc)[:200],
            )
            wdc_result = None

        elapsed_ms = (time.monotonic() - start) * 1000

        # Step 6: LLM Guardrails — scrub output before it reaches the user
        from src.security.llm_guardrails import scrub_output
        draft_content = scrub_output(draft_content)

        # Build the result. If WDC failed, deliver with a None-safe fallback.
        result = OrchestrationResult(
            content=draft_content,
            wdc_result=wdc_result,  # type: ignore[arg-type]
            agent_contributions={
                role: resp.content[:200] for role, resp in agent_responses.items()
            },
            degraded_agents=degraded_agents,
            revision_cycles=cycle,
            total_time_ms=round(elapsed_ms, 1),
            task_type=task_type,
        )

        if degraded_agents:
            logger.warning(
                "orchestration_degraded | degraded_agents=%s total_agents=%d responding_agents=%d",
                ",".join(degraded_agents),
                len(agents_needed),
                len(agent_responses),
            )

        return result

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
    ) -> tuple[dict[str, AgentResponse], list[str]]:
        """Fan-out to multiple agents in parallel and collect responses.

        Only invokes agents listed in agents_needed. Lead Counsel is
        always included as the aggregator and is not invoked here.

        Returns
        -------
        tuple of (responses, failed_roles)
            responses: dict mapping role name to AgentResponse for
                agents that succeeded.
            failed_roles: list of role names for agents that raised
                exceptions. These agents are skipped (graceful
                degradation), and the pipeline continues with the
                remaining agents.

        Error handling:
            - Each agent.invoke() failure is caught individually.
            - Only the agent role is logged — never user data (@M:010).
            - Failed agents are excluded from the response dict so
              Lead Counsel does not aggregate garbage placeholder text.
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

        if not tasks:
            return {}, []

        # Run all agents in parallel — return_exceptions=True so one
        # failure does not cancel the others.
        results = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

        responses: dict[str, AgentResponse] = {}
        failed_roles: list[str] = []

        for role_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                # Log role only — no user data, no full stack trace (@M:010)
                logger.error(
                    "agent_invoke_failed | role=%s error_type=%s error=%s",
                    role_name,
                    type(result).__name__,
                    str(result)[:200],
                )
                failed_roles.append(role_name)
            else:
                responses[role_name] = result

        if failed_roles:
            logger.warning(
                "fan_out_degraded | failed=%s succeeded=%s total=%d",
                ",".join(failed_roles),
                ",".join(responses.keys()),
                len(tasks),
            )

        return responses, failed_roles

    def _build_aggregation_prompt(
        self,
        original_message: str,
        agent_responses: dict[str, AgentResponse],
        degraded_agents: list[str] | None = None,
    ) -> str:
        """Build a prompt for Lead Counsel to aggregate agent responses.

        Parameters
        ----------
        original_message:
            The user's original query.
        agent_responses:
            Successful agent responses to synthesize.
        degraded_agents:
            Roles of agents that failed. If non-empty, Lead Counsel is
            instructed to note that the analysis is partial.
        """
        parts = [
            f"ORIGINAL QUERY: {original_message}",
            "",
        ]

        # Inform Lead Counsel about degraded agents so it can
        # adjust confidence and flag coverage gaps.
        if degraded_agents:
            parts.append(
                "DEGRADED AGENTS (these agents were unavailable for this request):"
            )
            for role in degraded_agents:
                parts.append(f"  - {role}")
            parts.append(
                "Note: Adjust your confidence downward and flag any coverage "
                "gaps caused by the missing agents.\n"
            )

        parts.append(
            "AGENT RESPONSES (synthesize into a unified, certified response):"
        )
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
