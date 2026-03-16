"""
Agent orchestrator for Ciphergy Pipeline.

Manages up to 20 parallel AI agents, each with its own Bedrock session.
Uses asyncio + concurrent.futures for true parallel execution with
timeout management, progress tracking, and lifecycle control.
"""

import asyncio
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ciphergy.agents.agent import Agent, AgentResult, AgentStatus, AgentType
from ciphergy.models.bedrock import BedrockClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Orchestrator status
# ---------------------------------------------------------------------------


class OrchestratorStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"


# ---------------------------------------------------------------------------
# Agent tracking
# ---------------------------------------------------------------------------


@dataclass
class AgentHandle:
    """Internal tracking for a spawned agent."""

    agent: Agent
    future: Optional[Future] = None
    result: Optional[AgentResult] = None
    spawn_time: float = 0.0
    timeout: Optional[float] = None


# ---------------------------------------------------------------------------
# AgentOrchestrator
# ---------------------------------------------------------------------------


class AgentOrchestrator:
    """Orchestrates parallel AI agents on AWS Bedrock.

    Parameters
    ----------
    max_agents : int
        Maximum concurrent agents (default: 20).
    default_timeout : float
        Default per-agent timeout in seconds (default: 300).
    aws_region : str, optional
        AWS region for Bedrock clients.
    aws_profile : str, optional
        AWS profile name.
    on_agent_complete : callable, optional
        Callback ``(agent_id: str, result: AgentResult) -> None`` fired
        when any agent finishes.
    """

    def __init__(
        self,
        max_agents: int = 20,
        default_timeout: float = 300.0,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        on_agent_complete: Optional[Callable[[str, AgentResult], None]] = None,
    ) -> None:
        self._max_agents = max_agents
        self._default_timeout = default_timeout
        self._aws_region = aws_region
        self._aws_profile = aws_profile
        self._on_agent_complete = on_agent_complete

        self._agents: Dict[str, AgentHandle] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_agents, thread_name_prefix="ciphergy-agent")
        self._status = OrchestratorStatus.IDLE

        logger.info(
            "AgentOrchestrator initialized: max_agents=%d, default_timeout=%.0fs",
            max_agents,
            default_timeout,
        )

    # ------------------------------------------------------------------
    # Bedrock client factory
    # ------------------------------------------------------------------

    def _create_client(self, model: Optional[str] = None) -> BedrockClient:
        """Create an isolated BedrockClient for an agent."""
        return BedrockClient(
            region=self._aws_region,
            profile=self._aws_profile,
            preferred_model=model or "claude-sonnet-4-6",
        )

    # ------------------------------------------------------------------
    # Spawn
    # ------------------------------------------------------------------

    def spawn_agent(
        self,
        name: str,
        task: str,
        *,
        model: Optional[str] = None,
        agent_type: AgentType = AgentType.GENERAL,
        tools: Optional[List[Dict[str, Any]]] = None,
        tools_map: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: Optional[float] = None,
    ) -> str:
        """Spawn a new agent and begin execution.

        Parameters
        ----------
        name : str
            Human-readable agent name.
        task : str
            The task / prompt to give the agent.
        model : str, optional
            Model key (e.g. ``claude-opus-4-6``).
        agent_type : AgentType
            Role classification.
        tools : list, optional
            Tool definitions for tool-use.
        tools_map : dict, optional
            Name -> callable mapping for tool execution.
        context : str, optional
            Additional system context.
        system_prompt : str, optional
            Full system prompt override.
        max_tokens : int
            Max output tokens.
        temperature : float
            Sampling temperature.
        timeout : float, optional
            Per-agent timeout (overrides default).

        Returns
        -------
        str
            The spawned agent's unique ID.

        Raises
        ------
        RuntimeError
            If the maximum agent count is reached.
        """
        active = self._active_count()
        if active >= self._max_agents:
            raise RuntimeError(
                f"Cannot spawn agent: {active}/{self._max_agents} agents running. "
                f"Wait for completion or increase max_agents."
            )

        client = self._create_client(model)
        agent = Agent(
            name=name,
            task=task,
            client=client,
            model=model,
            agent_type=agent_type,
            tools=tools,
            tools_map=tools_map,
            context=context,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout or self._default_timeout,
        )

        handle = AgentHandle(
            agent=agent,
            spawn_time=time.monotonic(),
            timeout=timeout or self._default_timeout,
        )

        # Submit to thread pool
        future = self._executor.submit(self._run_agent, agent)
        future.add_done_callback(lambda f: self._on_done(agent.agent_id, f))
        handle.future = future

        self._agents[agent.agent_id] = handle
        self._status = OrchestratorStatus.RUNNING

        logger.info(
            "Spawned agent: id=%s name='%s' type=%s model=%s",
            agent.agent_id[:8],
            name,
            agent_type.value,
            model,
        )
        return agent.agent_id

    @staticmethod
    def _run_agent(agent: Agent) -> AgentResult:
        """Execute an agent (runs in thread pool)."""
        return agent.run()

    def _on_done(self, agent_id: str, future: Future) -> None:
        """Callback when an agent's future completes."""
        handle = self._agents.get(agent_id)
        if handle is None:
            return

        try:
            result = future.result()
        except Exception as exc:
            logger.error("Agent %s raised: %s", agent_id[:8], exc)
            result = AgentResult(
                agent_id=agent_id,
                agent_name=handle.agent.name,
                agent_type=handle.agent.agent_type.value,
                status=AgentStatus.FAILED.value,
                error=str(exc),
                duration_seconds=time.monotonic() - handle.spawn_time,
            )

        handle.result = result

        if self._on_agent_complete:
            try:
                self._on_agent_complete(agent_id, result)
            except Exception as exc:
                logger.error("on_agent_complete callback failed: %s", exc)

        logger.info(
            "Agent done: id=%s name='%s' status=%s duration=%.1fs",
            agent_id[:8],
            handle.agent.name,
            result.status,
            result.duration_seconds,
        )

    # ------------------------------------------------------------------
    # Wait
    # ------------------------------------------------------------------

    def wait_for_agent(self, agent_id: str, timeout: Optional[float] = None) -> AgentResult:
        """Block until a specific agent completes.

        Parameters
        ----------
        agent_id : str
            The agent ID returned by ``spawn_agent``.
        timeout : float, optional
            Max seconds to wait.  ``None`` = wait indefinitely.

        Returns
        -------
        AgentResult

        Raises
        ------
        KeyError
            If the agent_id is unknown.
        TimeoutError
            If the wait exceeds the timeout.
        """
        handle = self._agents.get(agent_id)
        if handle is None:
            raise KeyError(f"Unknown agent: {agent_id}")

        if handle.result is not None:
            return handle.result

        if handle.future is None:
            raise RuntimeError(f"Agent {agent_id} was never submitted")

        try:
            result = handle.future.result(timeout=timeout)
            handle.result = result
            return result
        except TimeoutError:
            raise TimeoutError(f"Agent {agent_id} did not complete within {timeout}s")
        except Exception as exc:
            return AgentResult(
                agent_id=agent_id,
                agent_name=handle.agent.name,
                agent_type=handle.agent.agent_type.value,
                status=AgentStatus.FAILED.value,
                error=str(exc),
                duration_seconds=time.monotonic() - handle.spawn_time,
            )

    def wait_for_all(self, timeout: Optional[float] = None) -> Dict[str, AgentResult]:
        """Block until all spawned agents complete.

        Parameters
        ----------
        timeout : float, optional
            Max seconds to wait for all agents combined.

        Returns
        -------
        dict
            Mapping of ``agent_id -> AgentResult``.
        """
        results: Dict[str, AgentResult] = {}
        start = time.monotonic()

        pending_futures: Dict[Future, str] = {}
        for aid, handle in self._agents.items():
            if handle.result is not None:
                results[aid] = handle.result
            elif handle.future is not None:
                pending_futures[handle.future] = aid

        if not pending_futures:
            return results

        remaining = timeout
        for future in as_completed(pending_futures, timeout=timeout):
            aid = pending_futures[future]
            handle = self._agents[aid]
            try:
                result = future.result(timeout=0)
            except Exception as exc:
                result = AgentResult(
                    agent_id=aid,
                    agent_name=handle.agent.name,
                    agent_type=handle.agent.agent_type.value,
                    status=AgentStatus.FAILED.value,
                    error=str(exc),
                    duration_seconds=time.monotonic() - handle.spawn_time,
                )
            handle.result = result
            results[aid] = result

        self._status = OrchestratorStatus.IDLE
        return results

    # ------------------------------------------------------------------
    # Kill / cancel
    # ------------------------------------------------------------------

    def kill_agent(self, agent_id: str) -> bool:
        """Attempt to cancel a running agent.

        Parameters
        ----------
        agent_id : str
            The agent to cancel.

        Returns
        -------
        bool
            True if cancellation was requested successfully.
        """
        handle = self._agents.get(agent_id)
        if handle is None:
            logger.warning("Cannot kill unknown agent: %s", agent_id)
            return False

        if handle.future and not handle.future.done():
            cancelled = handle.future.cancel()
            if cancelled:
                handle.agent.status = AgentStatus.CANCELLED
                handle.result = AgentResult(
                    agent_id=agent_id,
                    agent_name=handle.agent.name,
                    agent_type=handle.agent.agent_type.value,
                    status=AgentStatus.CANCELLED.value,
                    duration_seconds=time.monotonic() - handle.spawn_time,
                )
                logger.info("Agent cancelled: %s", agent_id[:8])
                return True
            else:
                logger.warning("Could not cancel agent %s (already running)", agent_id[:8])
                return False

        return False

    # ------------------------------------------------------------------
    # Status / reporting
    # ------------------------------------------------------------------

    def _active_count(self) -> int:
        """Count agents whose futures are not yet done."""
        return sum(1 for h in self._agents.values() if h.future is not None and not h.future.done())

    @property
    def status(self) -> OrchestratorStatus:
        """Current orchestrator status."""
        if self._active_count() > 0:
            return OrchestratorStatus.RUNNING
        return self._status

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Return status info for a specific agent.

        Returns
        -------
        dict
            Keys: agent_id, name, type, status, duration, has_result.
        """
        handle = self._agents.get(agent_id)
        if handle is None:
            raise KeyError(f"Unknown agent: {agent_id}")

        elapsed = time.monotonic() - handle.spawn_time if handle.spawn_time else 0
        return {
            "agent_id": agent_id,
            "name": handle.agent.name,
            "type": handle.agent.agent_type.value,
            "status": handle.agent.status.value,
            "duration_seconds": round(elapsed, 2),
            "has_result": handle.result is not None,
            "model": handle.agent.model,
        }

    def get_all_status(self) -> List[Dict[str, Any]]:
        """Return status for all agents."""
        return [self.get_agent_status(aid) for aid in self._agents]

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of orchestrator state."""
        statuses = [h.agent.status.value for h in self._agents.values()]
        return {
            "orchestrator_status": self.status.value,
            "total_agents": len(self._agents),
            "active": self._active_count(),
            "completed": statuses.count(AgentStatus.COMPLETED.value),
            "failed": statuses.count(AgentStatus.FAILED.value),
            "cancelled": statuses.count(AgentStatus.CANCELLED.value),
            "timed_out": statuses.count(AgentStatus.TIMED_OUT.value),
            "pending": statuses.count(AgentStatus.PENDING.value),
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def shutdown(self, wait: bool = True, cancel_pending: bool = False) -> None:
        """Shut down the orchestrator's thread pool.

        Parameters
        ----------
        wait : bool
            If True, wait for running agents to finish.
        cancel_pending : bool
            If True, cancel agents that haven't started yet.
        """
        self._status = OrchestratorStatus.SHUTTING_DOWN
        logger.info("Orchestrator shutting down (wait=%s, cancel_pending=%s)", wait, cancel_pending)

        if cancel_pending:
            for aid, handle in self._agents.items():
                if handle.future and not handle.future.done():
                    handle.future.cancel()

        self._executor.shutdown(wait=wait)
        self._status = OrchestratorStatus.IDLE
        logger.info("Orchestrator shutdown complete")

    def __enter__(self) -> "AgentOrchestrator":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.shutdown(wait=True)


# ---------------------------------------------------------------------------
# Async wrapper (for use in async contexts)
# ---------------------------------------------------------------------------


async def async_spawn_and_wait(
    orchestrator: AgentOrchestrator,
    agents_config: List[Dict[str, Any]],
) -> Dict[str, AgentResult]:
    """Spawn multiple agents and wait for all results asynchronously.

    This runs the synchronous orchestrator in a thread pool so it can
    be used from async code without blocking the event loop.

    Parameters
    ----------
    orchestrator : AgentOrchestrator
        The orchestrator instance.
    agents_config : list of dict
        Each dict is kwargs for ``spawn_agent``.

    Returns
    -------
    dict
        Mapping of agent_id -> AgentResult.
    """
    loop = asyncio.get_event_loop()

    # Spawn all agents
    agent_ids: List[str] = []
    for cfg in agents_config:
        aid = await loop.run_in_executor(
            None,
            lambda c=cfg: orchestrator.spawn_agent(**c),
        )
        agent_ids.append(aid)

    # Wait for all
    results = await loop.run_in_executor(None, orchestrator.wait_for_all)
    return results
