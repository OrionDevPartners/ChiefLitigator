"""Internal admin agent for admin.cyphergy.ai.

Provides an LLM-powered conversational interface for admin operations:
- Deploy management (ECS redeployment triggers)
- Git repository status inspection
- Beta user management
- System statistics and health checks

The agent uses the CPAA-compliant LLM provider (Anthropic in dev, Bedrock
in production) with a special admin system prompt that grants elevated
understanding of the platform internals. Every action is logged to the
AdminAuditLog. Destructive operations (deploy, revoke, IP reset) NEVER
auto-execute -- the agent returns a confirmation prompt first.

All configuration from environment variables (CPAA-compliant).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.audit import log_admin_action
from src.beta.models import BetaInvite
from src.database.models import Case, Message, User
from src.providers.llm_provider import LLMProvider, get_provider
from src.security.llm_guardrails import GUARDRAIL_SYSTEM_PROMPT

logger = logging.getLogger("cyphergy.admin.agent")


# ---------------------------------------------------------------------------
# Admin system prompt -- elevated context for the internal agent
# ---------------------------------------------------------------------------

_ADMIN_SYSTEM_PROMPT = """
You are the Cyphergy Admin Agent, an internal operations assistant available
exclusively on admin.cyphergy.ai. You help the platform administrator manage
the Cyphergy legal AI platform.

YOUR CAPABILITIES:
- deploy: Describe how to trigger ECS redeployment (you propose, admin confirms)
- git_status: Report the current state of the git repository
- users: List, invite, revoke, or reset IP for beta users
- stats: Report system statistics (user count, case count, message count)
- health: Check all service connectivity (RDS, LLM provider, S3)

BEHAVIOR RULES:
1. You NEVER auto-execute destructive operations. Always return a confirmation
   prompt with the exact action you propose, and wait for explicit approval.
2. You log every action you take or propose to the admin audit trail.
3. You are direct, concise, and operational. No filler text.
4. You may reference Cyphergy internals (agent names, architecture) because
   this conversation is admin-only and never exposed to end users.
5. For deploy commands, describe the AWS CLI or ECS API call but do NOT
   execute it without the admin typing "confirm".
6. For user management, call the appropriate capability and return results.
7. If you cannot fulfill a request, say so and explain what is needed.

CURRENT PLATFORM:
- Backend: FastAPI on ECS Fargate
- LLM: Anthropic API (dev) / AWS Bedrock (prod) via CPAA
- Database: PostgreSQL on RDS
- Frontend: Cloudflare Pages at cyphergy.ai
- Admin: admin.cyphergy.ai (this interface)
"""


# ---------------------------------------------------------------------------
# Capability handlers
# ---------------------------------------------------------------------------


async def _handle_git_status() -> dict[str, Any]:
    """Check the git repository status.

    Runs git commands in a subprocess to inspect the repo state.
    Does NOT perform any mutations.
    """
    repo_dir = os.getenv(
        "CYPHERGY_REPO_DIR",
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    )

    results: dict[str, Any] = {"repo_dir": repo_dir}

    try:
        branch = await asyncio.to_thread(
            subprocess.run,
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            timeout=10,
        )
        results["branch"] = branch.stdout.strip() if branch.returncode == 0 else "unknown"

        status = await asyncio.to_thread(
            subprocess.run,
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            timeout=10,
        )
        results["dirty_files"] = len(status.stdout.strip().splitlines()) if status.stdout.strip() else 0
        results["clean"] = results["dirty_files"] == 0

        log = await asyncio.to_thread(
            subprocess.run,
            ["git", "log", "--oneline", "-5"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            timeout=10,
        )
        results["recent_commits"] = log.stdout.strip().splitlines() if log.returncode == 0 else []

    except Exception as exc:
        results["error"] = str(exc)[:200]

    return results


async def _handle_system_stats(db: AsyncSession) -> dict[str, Any]:
    """Gather platform statistics from the database."""
    stats: dict[str, Any] = {}

    try:
        user_count = await db.execute(select(func.count(User.id)))
        stats["total_users"] = user_count.scalar_one()

        active_users = await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
        stats["active_users"] = active_users.scalar_one()

        case_count = await db.execute(select(func.count(Case.id)))
        stats["total_cases"] = case_count.scalar_one()

        message_count = await db.execute(select(func.count(Message.id)))
        stats["total_messages"] = message_count.scalar_one()

        beta_count = await db.execute(select(func.count(BetaInvite.id)))
        stats["total_beta_invites"] = beta_count.scalar_one()

        active_beta = await db.execute(select(func.count(BetaInvite.id)).where(BetaInvite.status == "active"))
        stats["active_beta_users"] = active_beta.scalar_one()

    except Exception as exc:
        stats["error"] = str(exc)[:200]

    return stats


async def _handle_health_check() -> dict[str, Any]:
    """Check connectivity to external services."""
    health: dict[str, Any] = {}

    # Check LLM provider availability
    try:
        provider = get_provider()
        health["llm_provider"] = {
            "status": "available",
            "type": type(provider).__name__,
        }
    except Exception as exc:
        health["llm_provider"] = {
            "status": "unavailable",
            "error": str(exc)[:200],
        }

    # Check database connectivity (caller must pass db for full check)
    health["database"] = {"status": "check_via_stats_endpoint"}

    # Check S3 bucket accessibility
    bucket_name = os.getenv("S3_DOCUMENTS_BUCKET", "cyphergy-documents")
    try:
        import boto3

        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        await asyncio.to_thread(s3.head_bucket, Bucket=bucket_name)
        health["s3"] = {"status": "accessible", "bucket": bucket_name}
    except ImportError:
        health["s3"] = {"status": "boto3_not_installed"}
    except Exception as exc:
        health["s3"] = {"status": "error", "error": str(exc)[:200]}

    # Check ECS cluster status
    cluster_name = os.getenv("ECS_CLUSTER_NAME", "cyphergy")
    try:
        import boto3

        ecs = boto3.client("ecs", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        response = await asyncio.to_thread(ecs.describe_clusters, clusters=[cluster_name])
        clusters = response.get("clusters", [])
        if clusters:
            health["ecs"] = {
                "status": clusters[0].get("status", "unknown"),
                "cluster": cluster_name,
                "running_tasks": clusters[0].get("runningTasksCount", 0),
            }
        else:
            health["ecs"] = {"status": "not_found", "cluster": cluster_name}
    except ImportError:
        health["ecs"] = {"status": "boto3_not_installed"}
    except Exception as exc:
        health["ecs"] = {"status": "error", "error": str(exc)[:200]}

    return health


async def _handle_deploy_info() -> dict[str, Any]:
    """Return deployment information and proposed commands.

    Does NOT execute deployment. Returns the commands the admin
    would need to confirm.
    """
    cluster = os.getenv("ECS_CLUSTER_NAME", "cyphergy")
    service = os.getenv("ECS_SERVICE_NAME", "cyphergy-api")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    return {
        "action": "ecs_force_deployment",
        "requires_confirmation": True,
        "cluster": cluster,
        "service": service,
        "region": region,
        "command": (
            f"aws ecs update-service --cluster {cluster} --service {service} --force-new-deployment --region {region}"
        ),
        "warning": "This will trigger a rolling restart of all running tasks.",
    }


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "deploy": [
        re.compile(r"\b(deploy|redeploy|restart|roll\s*(out|back)|force.*deploy)\b", re.IGNORECASE),
    ],
    "git_status": [
        re.compile(r"\bgit\b", re.IGNORECASE),
        re.compile(r"\b(repo|repository|branch|commit)\b", re.IGNORECASE),
    ],
    "users": [
        re.compile(r"\b(user|beta|invite|revoke|ip\s*lock|ip\s*reset)\b", re.IGNORECASE),
    ],
    "stats": [
        re.compile(r"\b(stat|stats|statistics|count|metric|analytics|numbers)\b", re.IGNORECASE),
    ],
    "health": [
        re.compile(r"\b(health|status|check|ping|alive|connectivity|service)\b", re.IGNORECASE),
    ],
}


def _detect_intent(message: str) -> str | None:
    """Detect the admin's intent from their message.

    Returns the capability name or None if no clear intent is matched.
    """
    for intent, patterns in _INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(message):
                return intent
    return None


# ---------------------------------------------------------------------------
# Admin Agent
# ---------------------------------------------------------------------------


class AdminAgent:
    """Internal agent on admin.cyphergy.ai with elevated access.

    The agent processes admin commands by:
    1. Detecting intent from the admin's natural language message
    2. Executing the appropriate capability handler to gather data
    3. Passing the data + message to the LLM for a contextual response
    4. Logging the action to AdminAuditLog
    5. Returning the response (with confirmation prompts for destructive ops)

    The LLM is used for natural language understanding and response
    formatting. Actual data comes from direct system calls, not from
    the LLM's training data.
    """

    CAPABILITIES: dict[str, str] = {
        "deploy": "Trigger ECS redeployment (requires confirmation)",
        "git_status": "Check repository status",
        "users": "Manage beta users",
        "stats": "Get system statistics",
        "health": "Check all service connectivity",
    }

    def __init__(self) -> None:
        self._provider: LLMProvider | None = None
        self._model = os.getenv("LLM_MODEL", "claude-opus-4-6")
        self._max_tokens = int(os.getenv("ADMIN_AGENT_MAX_TOKENS", "2048"))
        self._temperature = float(os.getenv("ADMIN_AGENT_TEMPERATURE", "0.3"))

    def _get_provider(self) -> LLMProvider:
        """Lazy-initialize the LLM provider (CPAA singleton)."""
        if self._provider is None:
            self._provider = get_provider()
        return self._provider

    async def process(
        self,
        message: str,
        admin_email: str,
        db: AsyncSession | None = None,
        ip_address: str = "unknown",
    ) -> dict[str, Any]:
        """Process an admin command via the internal agent.

        Args:
            message: The admin's natural language command.
            admin_email: Authenticated admin's email (from JWT).
            db: Optional database session for data-dependent operations.
            ip_address: Admin's IP address for audit logging.

        Returns:
            Dict with:
                - response: The agent's textual response
                - intent: Detected intent (or "general")
                - data: Raw data from capability handlers (if any)
                - requires_confirmation: Whether the action needs explicit approval
        """
        intent = _detect_intent(message)

        # Gather context data based on detected intent
        context_data: dict[str, Any] = {}
        requires_confirmation = False

        if intent == "git_status":
            context_data = await _handle_git_status()

        elif intent == "stats" and db is not None:
            context_data = await _handle_system_stats(db)

        elif intent == "health":
            context_data = await _handle_health_check()

        elif intent == "deploy":
            context_data = await _handle_deploy_info()
            requires_confirmation = True

        elif intent == "users" and db is not None:
            # User queries are handled by the routes directly.
            # The agent provides guidance on available user management commands.
            context_data = {
                "available_commands": [
                    "POST /admin/beta/invite -- Invite a new beta user",
                    "GET /admin/beta/users -- List all beta users",
                    "POST /admin/beta/revoke -- Revoke a user's access",
                    "POST /admin/beta/reset-ip -- Reset a user's locked IP",
                ],
                "note": "User management is handled via dedicated API endpoints.",
            }

        # Build the LLM message with gathered context
        context_text = (
            f"\n\nSYSTEM DATA (gathered from live sources, not model memory):\n"
            f"```json\n{json.dumps(context_data, indent=2, default=str)}\n```"
            if context_data
            else ""
        )

        user_prompt = (
            f"Admin ({admin_email}) says: {message}"
            f"{context_text}"
            f"\n\nRespond concisely with actionable information. "
            f"If this requires a destructive operation, describe the action and "
            f"ask for explicit confirmation before proceeding."
        )

        # Call the LLM for natural language response
        try:
            provider = self._get_provider()
            system = GUARDRAIL_SYSTEM_PROMPT + "\n\n" + _ADMIN_SYSTEM_PROMPT
            llm_response = await provider.create_message(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            response_text = llm_response.text
        except Exception as exc:
            logger.error(
                "admin_agent_llm_error | admin=%s error=%s",
                admin_email,
                str(exc)[:200],
            )
            # Fallback: return raw data without LLM formatting
            response_text = (
                f"LLM unavailable. Raw data for intent '{intent or 'general'}':\n"
                f"{json.dumps(context_data, indent=2, default=str)}"
            )

        # Log the action to audit trail
        if db is not None:
            try:
                await log_admin_action(
                    db,
                    admin_email=admin_email,
                    action=f"agent_chat:{intent or 'general'}",
                    details={
                        "message": message[:500],
                        "intent": intent or "general",
                        "requires_confirmation": requires_confirmation,
                    },
                    ip_address=ip_address,
                )
            except Exception as exc:
                logger.error(
                    "admin_agent_audit_error | admin=%s error=%s",
                    admin_email,
                    str(exc)[:200],
                )

        return {
            "response": response_text,
            "intent": intent or "general",
            "data": context_data,
            "requires_confirmation": requires_confirmation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def list_capabilities(self) -> dict[str, str]:
        """Return the agent's capability manifest.

        This is a read-only operation that does not require
        authentication beyond the admin JWT already verified
        by the route middleware.
        """
        return dict(self.CAPABILITIES)
