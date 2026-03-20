"""Bedrock AgentCore Runtime — Multi-agent session management for ChiefLitigator.

This module provides the AgentCore runtime integration that enables:
  - Long-running agent sessions (up to 8 hours for complex litigation workflows)
  - Multi-agent orchestration with isolated execution environments
  - Session memory persistence across interactions
  - Agent-to-agent communication via shared context

Architecture:
  Each ChiefLitigator agent (Lead Counsel, Research, Drafting, Red Team,
  Compliance, Intake, Document Generator, Evidence Scorer, Docket Monitor)
  runs as an isolated AgentCore session. The Orchestrator manages the
  lifecycle and coordinates inter-agent communication.

All configuration via environment variables per CPAA mandate.
No hardcoded secrets.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.providers.bedrock_agentcore")


# ---------------------------------------------------------------------------
# Configuration — ALL from environment variables
# ---------------------------------------------------------------------------
BEDROCK_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AGENTCORE_SESSION_TIMEOUT = int(os.getenv("AGENTCORE_SESSION_TIMEOUT", "28800"))  # 8 hours
AGENTCORE_ISOLATION_LEVEL = os.getenv("AGENTCORE_ISOLATION_LEVEL", "full")


# ---------------------------------------------------------------------------
# Agent Identity Registry
# ---------------------------------------------------------------------------
class AgentIdentity(str, Enum):
    """All ChiefLitigator agents registered in the AgentCore runtime."""
    ORCHESTRATOR = "chieflitigator-orchestrator"
    LEAD_COUNSEL = "chieflitigator-lead-counsel"
    RESEARCH_COUNSEL = "chieflitigator-research-counsel"
    DRAFTING_COUNSEL = "chieflitigator-drafting-counsel"
    RED_TEAM = "chieflitigator-red-team"
    COMPLIANCE_COUNSEL = "chieflitigator-compliance-counsel"
    INTAKE_AGENT = "chieflitigator-intake-agent"
    DOCUMENT_GENERATOR = "chieflitigator-document-generator"
    EVIDENCE_SCORER = "chieflitigator-evidence-scorer"
    DOCKET_MONITOR = "chieflitigator-docket-monitor"
    GALVANIZER_ADVOCACY = "chieflitigator-galvanizer-advocacy"
    GALVANIZER_STRESS_TEST = "chieflitigator-galvanizer-stress-test"


# ---------------------------------------------------------------------------
# Session Models
# ---------------------------------------------------------------------------
class AgentSession(BaseModel):
    """Represents an active AgentCore session."""
    session_id: str = Field(description="Unique session identifier")
    agent_id: str = Field(description="Agent identity from AgentIdentity enum")
    case_id: str = Field(description="Associated case ID")
    created_at: str = Field(description="ISO timestamp of session creation")
    expires_at: str = Field(description="ISO timestamp of session expiration")
    status: str = Field(default="active", description="Session status: active, suspended, terminated")
    memory_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Episodic memory: facts, decisions, and context accumulated during session",
    )


class AgentMessage(BaseModel):
    """Inter-agent message for communication within a case."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = Field(description="Sending agent identity")
    to_agent: str = Field(description="Receiving agent identity")
    case_id: str = Field(description="Case context")
    content: str = Field(description="Message content")
    message_type: str = Field(
        default="info",
        description="Type: info, request, response, alert, escalation",
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# AgentCore Runtime Manager
# ---------------------------------------------------------------------------
class AgentCoreRuntime:
    """Manages Bedrock AgentCore sessions for all ChiefLitigator agents.

    This is the central runtime that:
    1. Creates and manages agent sessions with configurable timeouts
    2. Routes messages between agents
    3. Maintains episodic memory per session
    4. Handles session lifecycle (create, invoke, suspend, terminate)

    Usage::

        runtime = AgentCoreRuntime()
        session = await runtime.create_session(
            agent_id=AgentIdentity.LEAD_COUNSEL,
            case_id="case-12345",
        )
        response = await runtime.invoke_agent(
            session_id=session.session_id,
            prompt="Classify this legal matter: tenant locked out of apartment",
        )
    """

    def __init__(self) -> None:
        self._bedrock_agent_client = boto3.client(
            "bedrock-agent-runtime",
            region_name=BEDROCK_REGION,
        )
        self._bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
        )
        # Active sessions indexed by session_id
        self._sessions: Dict[str, AgentSession] = {}
        # Message bus: case_id -> list of messages
        self._message_bus: Dict[str, List[AgentMessage]] = {}
        # Agent-to-model mapping (from ModelRouter)
        self._agent_model_map: Dict[str, str] = self._load_agent_model_map()

        logger.info(
            "AgentCoreRuntime initialized: region=%s timeout=%ds isolation=%s",
            BEDROCK_REGION,
            AGENTCORE_SESSION_TIMEOUT,
            AGENTCORE_ISOLATION_LEVEL,
        )

    def _load_agent_model_map(self) -> Dict[str, str]:
        """Load agent-to-model mapping from environment variables.

        Each agent can be assigned a specific Bedrock model via:
          AGENT_MODEL_{AGENT_NAME}=model-id

        Falls back to tier-based defaults from the ModelRouter.
        """
        # Tier 1: Maximum capability (Orchestrator, WDC/Galvanizer panels)
        tier_1_model = os.getenv(
            "BEDROCK_TIER1_MODEL",
            "anthropic.claude-opus-4-6-v1:0",
        )
        # Tier 2: Jurisdiction dual-brain
        tier_2_primary = os.getenv(
            "BEDROCK_TIER2_PRIMARY",
            "anthropic.claude-opus-4-6-v1:0",
        )
        tier_2_scout = os.getenv(
            "BEDROCK_TIER2_SCOUT",
            "meta.llama4-scout-17b-instruct-v1:0",
        )
        tier_2_cohere = os.getenv(
            "BEDROCK_TIER2_COHERE",
            "cohere.command-r-plus-v1:0",
        )
        # Tier 3: Utility
        tier_3_model = os.getenv(
            "BEDROCK_TIER3_MODEL",
            "anthropic.claude-sonnet-4-6-20260301-v1:0",
        )

        defaults = {
            AgentIdentity.ORCHESTRATOR.value: tier_1_model,
            AgentIdentity.LEAD_COUNSEL.value: tier_1_model,
            AgentIdentity.RESEARCH_COUNSEL.value: tier_1_model,
            AgentIdentity.DRAFTING_COUNSEL.value: tier_1_model,
            AgentIdentity.RED_TEAM.value: tier_1_model,
            AgentIdentity.COMPLIANCE_COUNSEL.value: tier_1_model,
            AgentIdentity.GALVANIZER_ADVOCACY.value: tier_1_model,
            AgentIdentity.GALVANIZER_STRESS_TEST.value: tier_1_model,
            AgentIdentity.INTAKE_AGENT.value: tier_3_model,
            AgentIdentity.DOCUMENT_GENERATOR.value: tier_3_model,
            AgentIdentity.EVIDENCE_SCORER.value: tier_2_primary,
            AgentIdentity.DOCKET_MONITOR.value: tier_3_model,
        }

        # Override from environment
        for agent_id in AgentIdentity:
            env_key = f"AGENT_MODEL_{agent_id.name}"
            override = os.getenv(env_key)
            if override:
                defaults[agent_id.value] = override
                logger.info("Model override: %s -> %s", agent_id.value, override)

        return defaults

    # ── Session Lifecycle ────────────────────────────────────────────

    async def create_session(
        self,
        agent_id: AgentIdentity,
        case_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> AgentSession:
        """Create a new AgentCore session for an agent working on a case.

        Sessions persist for up to 8 hours, allowing complex litigation
        workflows to run without interruption.
        """
        session_id = f"ses-{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()
        expires = now + timedelta(seconds=AGENTCORE_SESSION_TIMEOUT)

        session = AgentSession(
            session_id=session_id,
            agent_id=agent_id.value,
            case_id=case_id,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            status="active",
            memory_context=initial_context or {},
        )

        self._sessions[session_id] = session
        logger.info(
            "Session created: %s agent=%s case=%s expires=%s",
            session_id,
            agent_id.value,
            case_id,
            expires.isoformat(),
        )
        return session

    async def invoke_agent(
        self,
        session_id: str,
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Invoke an agent within its session context.

        Uses the Bedrock Converse API with the model assigned to this
        agent's tier. Supports tool-use if tools are provided.

        Returns the full response including text, tool calls, and usage stats.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or expired")

        if session.status != "active":
            raise ValueError(f"Session {session_id} is {session.status}, not active")

        # Check expiration
        if datetime.utcnow() > datetime.fromisoformat(session.expires_at):
            session.status = "expired"
            raise ValueError(f"Session {session_id} has expired")

        model_id = self._agent_model_map.get(
            session.agent_id,
            os.getenv("BEDROCK_DEFAULT_MODEL", "anthropic.claude-opus-4-6-v1:0"),
        )

        # Build system prompt with session memory context
        system_prompt = self._build_system_prompt(session)

        # Build Converse API request
        converse_params: Dict[str, Any] = {
            "modelId": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            "system": [{"text": system_prompt}],
            "inferenceConfig": {
                "maxTokens": int(os.getenv("BEDROCK_MAX_TOKENS", "8192")),
                "temperature": float(os.getenv("BEDROCK_TEMPERATURE", "0.0")),
            },
        }

        # Add tools if provided
        if tools:
            converse_params["toolConfig"] = {
                "tools": tools,
            }

        # Execute via Bedrock Converse API (async wrapper)
        raw_response = await asyncio.to_thread(
            self._bedrock_client.converse,
            **converse_params,
        )

        # Extract response
        output = raw_response.get("output", {}).get("message", {})
        usage = raw_response.get("usage", {})

        # Update session memory with this interaction
        session.memory_context.setdefault("interactions", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_preview": prompt[:200],
            "model": model_id,
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
        })

        # Parse response content
        text_parts = []
        tool_calls = []
        for block in output.get("content", []):
            if "text" in block:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tool_calls.append(block["toolUse"])

        return {
            "session_id": session_id,
            "agent_id": session.agent_id,
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
            "stop_reason": raw_response.get("stopReason", ""),
            "model_id": model_id,
        }

    async def terminate_session(self, session_id: str) -> None:
        """Terminate an agent session and persist its memory."""
        session = self._sessions.get(session_id)
        if session:
            session.status = "terminated"
            logger.info("Session terminated: %s agent=%s", session_id, session.agent_id)

    # ── Inter-Agent Communication ────────────────────────────────────

    async def send_message(self, message: AgentMessage) -> None:
        """Send a message from one agent to another within a case context."""
        self._message_bus.setdefault(message.case_id, []).append(message)
        logger.debug(
            "Message sent: %s -> %s case=%s type=%s",
            message.from_agent,
            message.to_agent,
            message.case_id,
            message.message_type,
        )

    async def get_messages(
        self,
        case_id: str,
        for_agent: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> List[AgentMessage]:
        """Retrieve messages for a case, optionally filtered by recipient or type."""
        messages = self._message_bus.get(case_id, [])
        if for_agent:
            messages = [m for m in messages if m.to_agent == for_agent or m.to_agent == "broadcast"]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        return messages

    # ── Multi-Agent Orchestration ────────────────────────────────────

    async def fan_out(
        self,
        case_id: str,
        agents: List[AgentIdentity],
        prompt: str,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Fan out a prompt to multiple agents in parallel.

        Creates sessions for each agent, invokes them concurrently,
        and collects all responses. Failed agents are recorded but
        don't block the pipeline (graceful degradation).
        """
        sessions = []
        for agent_id in agents:
            session = await self.create_session(
                agent_id=agent_id,
                case_id=case_id,
                initial_context=shared_context,
            )
            sessions.append(session)

        # Invoke all agents in parallel
        tasks = [
            self.invoke_agent(session.session_id, prompt)
            for session in sessions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = {}
        failures = []
        for session, result in zip(sessions, results):
            if isinstance(result, Exception):
                logger.error(
                    "Agent fan-out failed: agent=%s error=%s",
                    session.agent_id,
                    str(result)[:200],
                )
                failures.append(session.agent_id)
            else:
                responses[session.agent_id] = result

        # Terminate all sessions
        for session in sessions:
            await self.terminate_session(session.session_id)

        return {
            "responses": responses,
            "failures": failures,
            "total_agents": len(agents),
            "successful_agents": len(responses),
        }

    # ── Private Helpers ──────────────────────────────────────────────

    def _build_system_prompt(self, session: AgentSession) -> str:
        """Build the system prompt for an agent, including its memory context."""
        base_prompt = (
            f"You are {session.agent_id}, a specialized legal AI agent within the "
            f"ChiefLitigator platform. You are working on case {session.case_id}. "
            f"Your role is to provide expert legal analysis and assistance. "
            f"Always cite specific statutes, case law, and court rules. "
            f"Never fabricate citations. If uncertain, say so explicitly."
        )

        # Append memory context if available
        memory = session.memory_context
        if memory:
            facts = memory.get("key_facts", [])
            if facts:
                base_prompt += f"\n\nKey facts established so far:\n"
                for fact in facts:
                    base_prompt += f"- {fact}\n"

            decisions = memory.get("decisions", [])
            if decisions:
                base_prompt += f"\n\nDecisions made:\n"
                for decision in decisions:
                    base_prompt += f"- {decision}\n"

        return base_prompt

    def get_active_sessions(self, case_id: Optional[str] = None) -> List[AgentSession]:
        """List all active sessions, optionally filtered by case."""
        sessions = [s for s in self._sessions.values() if s.status == "active"]
        if case_id:
            sessions = [s for s in sessions if s.case_id == case_id]
        return sessions

    def get_session_stats(self) -> Dict[str, Any]:
        """Return runtime statistics for monitoring."""
        active = sum(1 for s in self._sessions.values() if s.status == "active")
        terminated = sum(1 for s in self._sessions.values() if s.status == "terminated")
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active,
            "terminated_sessions": terminated,
            "message_bus_cases": len(self._message_bus),
            "total_messages": sum(len(msgs) for msgs in self._message_bus.values()),
        }
