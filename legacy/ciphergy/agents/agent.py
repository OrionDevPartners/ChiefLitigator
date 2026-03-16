"""
Individual agent implementation for Ciphergy Pipeline.

Each Agent wraps a Bedrock session with a specific role, model, tools,
and context.  The ``run()`` method executes the agent's task and returns
a structured ``AgentResult``.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ciphergy.models.bedrock import BedrockClient, TokenUsage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent types and status
# ---------------------------------------------------------------------------


class AgentType(str, Enum):
    """Supported agent role classifications."""

    GENERAL = "general"
    RESEARCH = "research"
    EXECUTION = "execution"
    REVIEW = "review"
    RED_TEAM = "red_team"


class AgentStatus(str, Enum):
    """Lifecycle states for an agent."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Structured result returned by an agent after execution."""

    agent_id: str
    agent_name: str
    agent_type: str
    status: str
    output: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool execution helper
# ---------------------------------------------------------------------------


def _execute_tool(tool_name: str, tool_input: Dict[str, Any], tools_map: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call using the registered tools map.

    Parameters
    ----------
    tool_name : str
        Name of the tool to invoke.
    tool_input : dict
        Input arguments for the tool.
    tools_map : dict
        Mapping of tool name -> callable.

    Returns
    -------
    dict
        Tool result with ``type``, ``tool_use_id``, and ``content``.
    """
    handler = tools_map.get(tool_name)
    if handler is None:
        return {
            "type": "tool_result",
            "content": f"Error: tool '{tool_name}' not found in registered tools",
            "is_error": True,
        }

    try:
        result = handler(**tool_input) if callable(handler) else str(handler)
        return {
            "type": "tool_result",
            "content": str(result) if not isinstance(result, str) else result,
            "is_error": False,
        }
    except Exception as exc:
        logger.error("Tool '%s' failed: %s", tool_name, exc)
        return {
            "type": "tool_result",
            "content": f"Error executing tool '{tool_name}': {exc}",
            "is_error": True,
        }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class Agent:
    """A single AI agent backed by AWS Bedrock.

    Parameters
    ----------
    name : str
        Human-readable agent name.
    task : str
        The task / prompt for this agent.
    client : BedrockClient
        Bedrock client instance (each agent should get its own for isolation).
    model : str, optional
        Model key (e.g. ``claude-sonnet-4-6``).  Uses client default if omitted.
    agent_type : AgentType
        Role classification.
    tools : list, optional
        Tool definitions (Anthropic tool-use schema) the agent may call.
    tools_map : dict, optional
        Mapping of tool name -> callable for executing tool calls.
    context : str, optional
        Additional system-level context prepended to the system prompt.
    system_prompt : str, optional
        Full system prompt override.
    max_tokens : int
        Max output tokens per invocation.
    temperature : float
        Sampling temperature.
    max_tool_rounds : int
        Maximum number of tool-use round-trips before forcing completion.
    timeout : float, optional
        Timeout in seconds.  None = no timeout.
    """

    def __init__(
        self,
        name: str,
        task: str,
        client: BedrockClient,
        *,
        model: Optional[str] = None,
        agent_type: AgentType = AgentType.GENERAL,
        tools: Optional[List[Dict[str, Any]]] = None,
        tools_map: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        max_tool_rounds: int = 10,
        timeout: Optional[float] = None,
    ) -> None:
        self.agent_id: str = str(uuid.uuid4())
        self.name = name
        self.task = task
        self.client = client
        self.model = model
        self.agent_type = agent_type
        self.tools = tools or []
        self.tools_map = tools_map or {}
        self.context = context
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_tool_rounds = max_tool_rounds
        self.timeout = timeout
        self.status = AgentStatus.PENDING

        # Build system prompt
        parts: List[str] = []
        if system_prompt:
            parts.append(system_prompt)
        else:
            parts.append(f"You are a {agent_type.value} agent named '{name}'.")
            if context:
                parts.append(context)
        self._system = "\n\n".join(parts)

        logger.debug(
            "Agent created: id=%s name=%s type=%s model=%s",
            self.agent_id[:8],
            self.name,
            self.agent_type.value,
            self.model,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self) -> AgentResult:
        """Execute the agent's task.

        Handles multi-turn tool use: if the model returns tool_use blocks,
        the agent executes them and feeds results back until the model
        produces a final text response or the round limit is reached.

        Returns
        -------
        AgentResult
        """
        self.status = AgentStatus.RUNNING
        start = time.monotonic()
        total_usage = TokenUsage()
        all_tool_calls: List[Dict[str, Any]] = []
        all_tool_results: List[Dict[str, Any]] = []

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": self.task},
        ]

        try:
            for round_num in range(self.max_tool_rounds + 1):
                # Check timeout
                if self.timeout and (time.monotonic() - start) > self.timeout:
                    self.status = AgentStatus.TIMED_OUT
                    return AgentResult(
                        agent_id=self.agent_id,
                        agent_name=self.name,
                        agent_type=self.agent_type.value,
                        status=AgentStatus.TIMED_OUT.value,
                        output="",
                        tool_calls=all_tool_calls,
                        tool_results=all_tool_results,
                        usage=total_usage,
                        duration_seconds=time.monotonic() - start,
                        error=f"Timed out after {self.timeout}s",
                    )

                # Invoke model
                if self.tools and round_num < self.max_tool_rounds:
                    response = self.client.invoke_with_tools(
                        messages,
                        self.tools,
                        model=self.model,
                        system=self._system,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                else:
                    response = self.client.invoke_model(
                        messages,
                        model=self.model,
                        system=self._system,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )

                # Accumulate usage
                total_usage.input_tokens += response.usage.input_tokens
                total_usage.output_tokens += response.usage.output_tokens

                # If no tool calls, we're done
                if not response.tool_calls:
                    self.status = AgentStatus.COMPLETED
                    return AgentResult(
                        agent_id=self.agent_id,
                        agent_name=self.name,
                        agent_type=self.agent_type.value,
                        status=AgentStatus.COMPLETED.value,
                        output=response.content,
                        tool_calls=all_tool_calls,
                        tool_results=all_tool_results,
                        usage=total_usage,
                        duration_seconds=time.monotonic() - start,
                    )

                # Process tool calls
                # Build the assistant message with all content blocks from raw response
                assistant_content: List[Dict[str, Any]] = []
                if response.content:
                    assistant_content.append({"type": "text", "text": response.content})
                for tc in response.tool_calls:
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["input"],
                        }
                    )
                    all_tool_calls.append(tc)

                messages.append({"role": "assistant", "content": assistant_content})

                # Execute tools and build user response
                tool_results_content: List[Dict[str, Any]] = []
                for tc in response.tool_calls:
                    logger.info(
                        "Agent %s calling tool: %s",
                        self.name,
                        tc["name"],
                    )
                    result = _execute_tool(tc["name"], tc["input"], self.tools_map)
                    result["tool_use_id"] = tc["id"]
                    tool_results_content.append(result)
                    all_tool_results.append(
                        {
                            "tool_name": tc["name"],
                            "tool_input": tc["input"],
                            "result": result["content"],
                            "is_error": result.get("is_error", False),
                        }
                    )

                messages.append({"role": "user", "content": tool_results_content})

            # Exhausted tool rounds
            self.status = AgentStatus.COMPLETED
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                agent_type=self.agent_type.value,
                status=AgentStatus.COMPLETED.value,
                output=response.content,  # type: ignore[possibly-undefined]
                tool_calls=all_tool_calls,
                tool_results=all_tool_results,
                usage=total_usage,
                duration_seconds=time.monotonic() - start,
                metadata={"max_tool_rounds_reached": True},
            )

        except Exception as exc:
            self.status = AgentStatus.FAILED
            logger.error("Agent '%s' failed: %s", self.name, exc, exc_info=True)
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                agent_type=self.agent_type.value,
                status=AgentStatus.FAILED.value,
                output="",
                tool_calls=all_tool_calls,
                tool_results=all_tool_results,
                usage=total_usage,
                duration_seconds=time.monotonic() - start,
                error=str(exc),
            )
