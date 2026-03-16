"""Base agent class for the Cyphergy 5-agent legal AI architecture.

All agents inherit from BaseAgent, which handles:
- LLM provider configuration via environment variables (CPAA-compliant)
- Provider-agnostic LLM invocation (Anthropic or Bedrock) via the provider layer
- WDC scoring interface
- Message construction with blackboard context injection
- Private scratchpad management
"""

from __future__ import annotations

import logging
import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from src.providers.llm_provider import LLMProvider, LLMProviderResponse, get_provider

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    """LLM provider configuration loaded exclusively from environment variables.

    CPAA-compliant: no hardcoded API keys or provider details. The actual
    provider credentials are managed by the provider layer
    (``src.providers.llm_provider``), not by this settings class.
    """

    llm_model: str = Field(default="claude-opus-4-6", alias="LLM_MODEL")
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.4, alias="LLM_TEMPERATURE")

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


class AgentRole(str, Enum):
    """Role identifiers for the 5-agent Cyphergy architecture."""

    LEAD_COUNSEL = "lead_counsel"
    RESEARCH_COUNSEL = "research_counsel"
    DRAFTING_COUNSEL = "drafting_counsel"
    RED_TEAM = "red_team"
    COMPLIANCE_COUNSEL = "compliance_counsel"


class AgentResponse(BaseModel):
    """Structured response returned by any agent invocation."""

    content: str = Field(description="The agent's textual output")
    role: AgentRole = Field(description="Which agent produced this response")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-assessed confidence in the response (0.0-1.0)",
    )
    citations_used: list[str] = Field(
        default_factory=list,
        description="Legal citations referenced in the response",
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Flags raised during generation (e.g., 'needs_verification', 'deadline_critical')",
    )
    agent_id: str = Field(default="", description="Unique ID of the agent instance")
    elapsed_seconds: float = Field(
        default=0.0,
        description="Wall-clock time for the API call",
    )
    input_tokens: int = Field(default=0, description="Tokens consumed in the prompt")
    output_tokens: int = Field(default=0, description="Tokens generated in the response")

    def __str__(self) -> str:
        flag_str = f" | flags: {self.flags}" if self.flags else ""
        cite_str = f" | citations: {len(self.citations_used)}" if self.citations_used else ""
        return (
            f"[{self.role.value}] (confidence={self.confidence:.2f}{flag_str}{cite_str})\n"
            f"{self.content}"
        )


class WDCScore(BaseModel):
    """Weighted Debate Consensus score produced when one agent evaluates another's output."""

    score: float = Field(ge=0.0, le=10.0, description="Score from 0-10")
    reasoning: str = Field(description="Justification for the assigned score")
    flags: list[str] = Field(
        default_factory=list,
        description="Issues identified during scoring",
    )
    veto: bool = Field(
        default=False,
        description="Whether this score constitutes a veto (Compliance only)",
    )
    veto_reason: str | None = Field(
        default=None,
        description="Explanation if a veto is exercised",
    )
    scorer_role: AgentRole = Field(description="Role of the agent that produced this score")
    scorer_weight: float = Field(
        ge=0.0,
        le=1.0,
        description="WDC weight of the scoring agent",
    )

    @property
    def weighted_score(self) -> float:
        """Compute the contribution of this score to the WDC composite."""
        return self.score * self.scorer_weight


class AgentConfig(BaseModel):
    """Immutable configuration for an agent instance."""

    role: AgentRole
    weight: float = Field(ge=0.0, le=1.0, description="WDC weight (0.0-1.0)")
    has_veto: bool = Field(default=False, description="Only Compliance Counsel has veto power")
    system_prompt: str = Field(
        default="",
        description="System prompt defining the agent's behavior",
    )


class BaseAgent:
    """Abstract base for all 5 Cyphergy agents.

    Handles LLM provider initialization, message construction, API invocation,
    and WDC scoring. Subclasses must provide their own AgentConfig.

    The blackboard pattern: agents share a mutable ``blackboard`` dict for case
    state, but each agent also maintains a private ``scratchpad`` dict that is
    never shared with other agents.

    Provider switching (CPAA):
        The LLM provider is resolved once via ``get_provider()`` which reads
        the ``LLM_PROVIDER`` environment variable. All agent instances share
        the same singleton provider. Set ``LLM_PROVIDER=anthropic`` for dev,
        ``LLM_PROVIDER=bedrock`` for production. No code changes required.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.agent_id: str = str(uuid.uuid4())
        self.scratchpad: dict[str, Any] = {}
        self._message_history: list[dict[str, Any]] = []

        self._settings = LLMSettings()  # type: ignore[call-arg]
        self._provider: LLMProvider = get_provider()

        logger.info(
            "Agent initialized: role=%s weight=%.2f veto=%s model=%s id=%s provider=%s",
            config.role.value,
            config.weight,
            config.has_veto,
            self._settings.llm_model,
            self.agent_id[:8],
            type(self._provider).__name__,
        )

    # ------------------------------------------------------------------
    # Public API — invoke and score
    # ------------------------------------------------------------------

    async def invoke(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Make an LLM API call and return a structured AgentResponse.

        Parameters
        ----------
        user_message:
            The user's input or an internal routing prompt.
        context:
            Optional blackboard context dict to inject into the message.

        Returns
        -------
        AgentResponse with the LLM's output, confidence, citations, and flags.
        """
        messages = self._build_messages(user_message, context)
        start = time.monotonic()

        response = await self._provider.create_message(
            model=self._settings.llm_model,
            max_tokens=self._settings.llm_max_tokens,
            temperature=self._settings.llm_temperature,
            system=self.config.system_prompt,
            messages=messages,
        )

        elapsed = time.monotonic() - start
        content = response.text

        self._message_history.append({"role": "user", "content": user_message})
        self._message_history.append({"role": "assistant", "content": content})

        return AgentResponse(
            content=content,
            role=self.config.role,
            confidence=self._parse_confidence(content),
            citations_used=self._parse_citations(content),
            flags=self._parse_flags(content),
            agent_id=self.agent_id,
            elapsed_seconds=round(elapsed, 3),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    async def score(
        self,
        output: str,
        context: dict[str, Any] | None = None,
    ) -> WDCScore:
        """Score another agent's output for WDC debate consensus.

        Parameters
        ----------
        output:
            The text produced by another agent that needs evaluation.
        context:
            Optional context about the original task and case state.

        Returns
        -------
        WDCScore with a 0-10 score, reasoning, and optional veto.
        """
        scoring_prompt = (
            "You are evaluating another agent's legal output for quality, accuracy, "
            "and completeness. Score it from 0 to 10.\n\n"
            "Scoring criteria:\n"
            "- Legal accuracy and correct citation of statutes/rules (0-3 points)\n"
            "- Completeness of analysis — are all relevant issues addressed? (0-2 points)\n"
            "- Actionability — can a pro se litigant act on this? (0-2 points)\n"
            "- Risk awareness — are pitfalls and deadlines flagged? (0-2 points)\n"
            "- Clarity and plain-language explanation (0-1 point)\n\n"
            "Respond in EXACTLY this format (no other text):\n"
            "SCORE: <number 0-10>\n"
            "REASONING: <your detailed reasoning>\n"
            "FLAGS: <comma-separated list of issues, or NONE>\n"
            "VETO: <YES or NO>\n"
            "VETO_REASON: <reason if YES, or NONE>\n\n"
            "--- OUTPUT TO EVALUATE ---\n"
            f"{output}"
        )

        messages = self._build_messages(scoring_prompt, context)

        response = await self._provider.create_message(
            model=self._settings.llm_model,
            max_tokens=1024,
            temperature=0.2,
            system=self.config.system_prompt,
            messages=messages,
        )

        return self._parse_wdc_score(response.text)

    # ------------------------------------------------------------------
    # _call_model — convenience method for subclass agents
    # ------------------------------------------------------------------

    async def _call_model(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
    ) -> str:
        """Low-level LLM call that returns raw text content.

        This is the method that domain-specific agent subclasses
        (Research, Drafting, Red Team, Compliance) use for their
        specialized prompts. It provides a simpler interface than
        ``invoke()`` when structured ``AgentResponse`` wrapping is
        not needed.

        Parameters
        ----------
        messages:
            List of message dicts ({"role": str, "content": str}).
        max_tokens:
            Override for max tokens. Defaults to settings value.
        temperature:
            Override for temperature. Defaults to settings value.
        system:
            Override for system prompt. Defaults to the agent's
            configured system prompt. If the agent defines a
            ``system_prompt`` property (as Devin-built agents do),
            that property is used.

        Returns
        -------
        str
            The raw text content from the LLM response.
        """
        resolved_system = system
        if resolved_system is None:
            if hasattr(self, "system_prompt") and isinstance(
                getattr(type(self), "system_prompt", None), property
            ):
                resolved_system = self.system_prompt  # type: ignore[attr-defined]
            else:
                resolved_system = self.config.system_prompt

        # Inject LLM guardrails into EVERY agent's system prompt
        from src.security.llm_guardrails import GUARDRAIL_SYSTEM_PROMPT
        resolved_system = GUARDRAIL_SYSTEM_PROMPT + "\n\n" + resolved_system

        response = await self._provider.create_message(
            model=self._settings.llm_model,
            max_tokens=max_tokens if max_tokens is not None else self._settings.llm_max_tokens,
            temperature=temperature if temperature is not None else self._settings.llm_temperature,
            system=resolved_system,
            messages=messages,
        )

        return response.text

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Build the messages array for the API call.

        Injects blackboard context and conversation history into the
        user message so the LLM has full situational awareness.
        """
        messages: list[dict[str, Any]] = []

        for msg in self._message_history:
            messages.append(msg)

        content_parts: list[str] = []

        if context:
            ctx_lines = [f"- {k}: {v}" for k, v in context.items()]
            content_parts.append(
                "CASE CONTEXT (from shared blackboard):\n" + "\n".join(ctx_lines)
            )

        content_parts.append(user_message)

        messages.append({"role": "user", "content": "\n\n".join(content_parts)})
        return messages

    def reset_history(self) -> None:
        """Clear conversation history for a fresh interaction."""
        self._message_history.clear()

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_confidence(self, content: str) -> float:
        """Extract self-assessed confidence from the response content.

        Looks for patterns like 'Confidence: 0.85' or 'CONFIDENCE: HIGH'.
        Defaults to 0.5 if not found.
        """
        import re

        pattern = re.compile(r"(?:confidence|conf)\s*[:=]\s*([\d.]+)", re.IGNORECASE)
        match = pattern.search(content)
        if match:
            try:
                val = float(match.group(1))
                return min(max(val, 0.0), 1.0)
            except ValueError:
                pass

        qualitative = re.compile(
            r"(?:confidence|conf)\s*[:=]\s*(very\s+high|high|medium|low|very\s+low)",
            re.IGNORECASE,
        )
        qual_match = qualitative.search(content)
        if qual_match:
            level = qual_match.group(1).lower().strip()
            mapping = {
                "very high": 0.95,
                "high": 0.85,
                "medium": 0.65,
                "low": 0.35,
                "very low": 0.15,
            }
            return mapping.get(level, 0.5)

        return 0.5

    def _parse_citations(self, content: str) -> list[str]:
        """Extract legal citations from response content.

        Matches patterns for federal/state statutes, case law, rules of procedure, etc.
        """
        import re

        patterns = [
            r"\d+\s+U\.?S\.?C\.?\s*(?:§|sec\.?|section)?\s*\d+",
            r"\d+\s+C\.?F\.?R\.?\s*(?:§|sec\.?|part)?\s*[\d.]+",
            r"(?:Fed\.?\s*R\.?\s*Civ\.?\s*P\.?|FRCP)\s*(?:Rule\s*)?\d+",
            r"(?:La\.?\s*(?:C\.?C\.?P\.?|Code\s*Civ\.?\s*Proc\.?))\s*(?:art\.?\s*)?\d+",
            r"\d+\s+(?:So\.|S\.(?:Ct|W|E)\.|F\.\s*(?:Supp|2d|3d|4th)|N\.(?:E|W)\.|A\.)\s*(?:2d|3d)?\s*\d+",
            r"[A-Z][a-z]+\s+v\.?\s+[A-Z][a-z]+(?:,\s*\d+\s+\w)",
        ]

        citations: list[str] = []
        for pat in patterns:
            for match in re.finditer(pat, content):
                citation = match.group(0).strip()
                if citation not in citations:
                    citations.append(citation)

        return citations

    def _parse_flags(self, content: str) -> list[str]:
        """Extract operational flags from the response content."""
        import re

        flags: list[str] = []

        flag_keywords = {
            "deadline_critical": [r"deadline", r"time[-\s]?sensitive", r"statute\s+of\s+limitations"],
            "needs_verification": [r"verify", r"confirm\s+with", r"double[-\s]?check", r"unverified"],
            "disclaimer_required": [r"not\s+legal\s+advice", r"consult\s+(?:an?\s+)?attorney"],
            "high_stakes": [r"incarceration", r"felony", r"custody", r"constitutional\s+right"],
            "jurisdiction_sensitive": [r"varies\s+by\s+(?:state|jurisdiction)", r"local\s+rule"],
        }

        content_lower = content.lower()
        for flag_name, keyword_patterns in flag_keywords.items():
            for kp in keyword_patterns:
                if re.search(kp, content_lower):
                    flags.append(flag_name)
                    break

        return flags

    def _parse_wdc_score(self, raw: str) -> WDCScore:
        """Parse structured WDC scoring output from the LLM response."""
        import re

        score = 5.0
        reasoning = "Unable to parse detailed reasoning."
        flags: list[str] = []
        veto = False
        veto_reason: str | None = None

        score_match = re.search(r"SCORE\s*:\s*([\d.]+)", raw)
        if score_match:
            try:
                score = min(max(float(score_match.group(1)), 0.0), 10.0)
            except ValueError:
                pass

        reasoning_match = re.search(r"REASONING\s*:\s*(.+?)(?=\nFLAGS\s*:|\Z)", raw, re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()

        flags_match = re.search(r"FLAGS\s*:\s*(.+?)(?=\nVETO\s*:|\Z)", raw, re.DOTALL)
        if flags_match:
            raw_flags = flags_match.group(1).strip()
            if raw_flags.upper() != "NONE":
                flags = [f.strip() for f in raw_flags.split(",") if f.strip()]

        veto_match = re.search(r"VETO\s*:\s*(YES|NO)", raw, re.IGNORECASE)
        if veto_match and self.config.has_veto:
            veto = veto_match.group(1).upper() == "YES"

        if veto:
            veto_reason_match = re.search(r"VETO_REASON\s*:\s*(.+?)(?:\Z)", raw, re.DOTALL)
            if veto_reason_match:
                reason_text = veto_reason_match.group(1).strip()
                if reason_text.upper() != "NONE":
                    veto_reason = reason_text

        return WDCScore(
            score=score,
            reasoning=reasoning,
            flags=flags,
            veto=veto,
            veto_reason=veto_reason,
            scorer_role=self.config.role,
            scorer_weight=self.config.weight,
        )
