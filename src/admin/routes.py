"""Admin API routes for admin.cyphergy.ai.

All endpoints require admin JWT authentication via the ``require_admin``
dependency from ``src.admin.auth``. The admin JWT uses a DIFFERENT signing
secret (ADMIN_JWT_SECRET) than user JWTs (JWT_SECRET_KEY), so user tokens
cannot access admin endpoints.

Endpoints:
    POST /admin/login         -- Admin login (returns admin JWT)
    POST /admin/beta/invite   -- Invite a beta user
    GET  /admin/beta/users    -- List all beta users
    POST /admin/beta/revoke   -- Revoke beta access
    POST /admin/beta/reset-ip -- Reset a user's locked IP
    GET  /admin/system/health -- Check all service connectivity
    GET  /admin/system/stats  -- Platform statistics
    POST /admin/agent/chat    -- Internal admin agent chat

All configuration from environment variables (CPAA-compliant).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.agent import AdminAgent
from src.admin.audit import AdminAuditLog, BetaUser, log_admin_action
from src.admin.auth import (
    AdminJWTHandler,
    get_client_ip,
    require_admin,
    verify_admin_credentials,
)
from src.beta.email import send_beta_invite
from src.beta.gate import BetaGate
from src.beta.models import BetaInvite
from src.database.crud import get_user_by_email
from src.database.engine import get_db
from src.database.models import Case, Message, User

logger = logging.getLogger("cyphergy.admin.routes")

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# Shared instances
_gate = BetaGate()
_agent = AdminAgent()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AdminLoginRequest(BaseModel):
    """Admin login request body."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    """Admin login response with admin JWT."""

    token: str
    token_type: str = "bearer"
    email: str


class InviteRequest(BaseModel):
    """Beta user invite request body."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=256)


class InviteResponse(BaseModel):
    """Beta user invite response."""

    email: str
    user_id: str
    invite_id: str
    email_sent: bool


class BetaUserItem(BaseModel):
    """Single beta user in the list response."""

    user_id: str
    email: str
    name: str
    status: str
    locked_ip: str | None
    invited_by: str
    created_at: str
    activated_at: str | None
    revoked_at: str | None


class BetaUserListResponse(BaseModel):
    """Response listing all beta users."""

    users: list[BetaUserItem]
    count: int


class RevokeRequest(BaseModel):
    """Beta user revoke request body."""

    user_id: str = Field(..., description="UUID of the user to revoke.")


class RevokeResponse(BaseModel):
    """Beta user revoke response."""

    user_id: str
    status: str


class ResetIPRequest(BaseModel):
    """IP reset request body."""

    user_id: str = Field(..., description="UUID of the user whose IP to reset.")


class ResetIPResponse(BaseModel):
    """IP reset response."""

    user_id: str
    previous_ip: str | None
    status: str


class HealthResponse(BaseModel):
    """System health check response."""

    overall: str
    services: dict[str, Any]
    checked_at: str


class StatsResponse(BaseModel):
    """Platform statistics response."""

    total_users: int
    active_users: int
    total_cases: int
    total_messages: int
    total_beta_invites: int
    active_beta_users: int
    checked_at: str


class AgentChatRequest(BaseModel):
    """Admin agent chat request body."""

    message: str = Field(..., min_length=1, max_length=2000)


class AgentChatResponse(BaseModel):
    """Admin agent chat response."""

    response: str
    intent: str
    requires_confirmation: bool
    timestamp: str


# ---------------------------------------------------------------------------
# Admin Login
# ---------------------------------------------------------------------------


@admin_router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="Admin login",
)
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    """Authenticate as admin and receive an admin JWT.

    Uses ADMIN_EMAIL and ADMIN_PASSWORD_HASH from the environment.
    The returned JWT is signed with ADMIN_JWT_SECRET (separate from
    user JWT_SECRET_KEY) and carries a role=admin claim.
    """
    ip = get_client_ip(request)

    if not verify_admin_credentials(body.email, body.password):
        logger.warning("admin_login_failed | email=%s ip=%s", body.email, ip)
        await log_admin_action(
            db,
            admin_email=body.email,
            action="admin_login_failed",
            details={"reason": "invalid_credentials"},
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )

    handler = AdminJWTHandler()
    token = handler.create_token(
        payload={
            "sub": body.email,
            "email": body.email,
        }
    )

    await log_admin_action(
        db,
        admin_email=body.email,
        action="admin_login",
        details={"ip": ip},
        ip_address=ip,
    )

    logger.info("admin_login_success | email=%s ip=%s", body.email, ip)

    return AdminLoginResponse(
        token=token,
        email=body.email,
    )


# ---------------------------------------------------------------------------
# Beta User Management
# ---------------------------------------------------------------------------


@admin_router.post(
    "/beta/invite",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a beta user",
    dependencies=[Depends(require_admin)],
)
async def invite_beta_user(
    body: InviteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_admin),
) -> InviteResponse:
    """Approve a beta user, generate credentials, and send invite email.

    Creates the user account with a random 16-character password,
    creates the BetaInvite record, and sends credentials via email
    (SES in production, console log in development).

    The plaintext password is included in the email but is NEVER logged
    or stored anywhere except the bcrypt hash in the users table.
    """
    admin_email = admin.get("email", "unknown")
    ip = get_client_ip(request)

    try:
        result = await _gate.approve_user(
            email=body.email,
            name=body.name,
            db=db,
            invited_by=admin_email,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # Send invite email (password in result but NEVER logged)
    email_sent = await send_beta_invite(
        email=result["email"],
        name=body.name,
        password=result["password"],
    )

    await log_admin_action(
        db,
        admin_email=admin_email,
        action="beta_invite",
        details={
            "invited_email": body.email,
            "invited_name": body.name,
            "user_id": result["user_id"],
            "email_sent": email_sent,
        },
        ip_address=ip,
    )

    logger.info(
        "admin_beta_invite | admin=%s invited=%s email_sent=%s",
        admin_email,
        body.email,
        email_sent,
    )

    return InviteResponse(
        email=result["email"],
        user_id=result["user_id"],
        invite_id=result["invite_id"],
        email_sent=email_sent,
    )


@admin_router.get(
    "/beta/users",
    response_model=BetaUserListResponse,
    summary="List all beta users",
    dependencies=[Depends(require_admin)],
)
async def list_beta_users(
    db: AsyncSession = Depends(get_db),
) -> BetaUserListResponse:
    """List all beta users with status, locked IP, and join date.

    Returns beta invite records joined with user data, ordered by
    creation date descending (newest first).
    """
    stmt = select(BetaInvite).order_by(BetaInvite.created_at.desc())
    result = await db.execute(stmt)
    invites = list(result.scalars().all())

    items: list[BetaUserItem] = []
    for inv in invites:
        # Resolve user details via the relationship
        user = inv.user
        items.append(
            BetaUserItem(
                user_id=str(inv.user_id),
                email=user.email if user else "unknown",
                name=user.name if user else "unknown",
                status=inv.status,
                locked_ip=inv.locked_ip,
                invited_by=inv.invited_by,
                created_at=inv.created_at.isoformat() if inv.created_at else "",
                activated_at=inv.activated_at.isoformat() if inv.activated_at else None,
                revoked_at=inv.revoked_at.isoformat() if inv.revoked_at else None,
            )
        )

    return BetaUserListResponse(users=items, count=len(items))


@admin_router.post(
    "/beta/revoke",
    response_model=RevokeResponse,
    summary="Revoke beta access",
    dependencies=[Depends(require_admin)],
)
async def revoke_beta_user(
    body: RevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_admin),
) -> RevokeResponse:
    """Revoke beta access for a user.

    Sets the BetaInvite status to 'revoked' and deactivates the
    user account (is_active=False). The user will no longer be able
    to authenticate.
    """
    admin_email = admin.get("email", "unknown")
    ip = get_client_ip(request)

    try:
        user_id = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user_id format. Expected UUID.",
        )

    invite = await _gate.get_invite_by_user_id(user_id, db)
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No beta invite found for this user.",
        )

    if invite.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User access is already revoked.",
        )

    await _gate.revoke_user(user_id, db)

    await log_admin_action(
        db,
        admin_email=admin_email,
        action="beta_revoke",
        details={"user_id": body.user_id},
        ip_address=ip,
    )

    logger.info("admin_beta_revoke | admin=%s user_id=%s", admin_email, body.user_id)

    return RevokeResponse(
        user_id=body.user_id,
        status="revoked",
    )


@admin_router.post(
    "/beta/reset-ip",
    response_model=ResetIPResponse,
    summary="Reset a user's locked IP",
    dependencies=[Depends(require_admin)],
)
async def reset_user_ip(
    body: ResetIPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_admin),
) -> ResetIPResponse:
    """Clear a beta user's locked IP so they can re-login from a new location.

    Resets the locked_ip field on the BetaInvite record to NULL and
    sets the status back to 'pending'. The user's next login will
    lock to their new IP address.
    """
    admin_email = admin.get("email", "unknown")
    ip = get_client_ip(request)

    try:
        user_id = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user_id format. Expected UUID.",
        )

    invite = await _gate.get_invite_by_user_id(user_id, db)
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No beta invite found for this user.",
        )

    if invite.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reset IP for a revoked user. Reinvite instead.",
        )

    previous_ip = invite.locked_ip

    # Clear the locked IP and reset to pending status
    stmt = (
        update(BetaInvite)
        .where(BetaInvite.user_id == user_id)
        .values(
            locked_ip=None,
            status="pending",
            activated_at=None,
        )
    )
    await db.execute(stmt)
    await db.flush()

    await log_admin_action(
        db,
        admin_email=admin_email,
        action="beta_reset_ip",
        details={
            "user_id": body.user_id,
            "previous_ip": previous_ip,
        },
        ip_address=ip,
    )

    logger.info(
        "admin_beta_reset_ip | admin=%s user_id=%s previous_ip=%s",
        admin_email,
        body.user_id,
        previous_ip or "none",
    )

    return ResetIPResponse(
        user_id=body.user_id,
        previous_ip=previous_ip,
        status="ip_reset",
    )


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


@admin_router.get(
    "/system/health",
    response_model=HealthResponse,
    summary="Check all service connectivity",
    dependencies=[Depends(require_admin)],
)
async def system_health() -> HealthResponse:
    """Check connectivity to all external services.

    Verifies:
    - LLM provider (Anthropic API or AWS Bedrock)
    - S3 document storage
    - ECS cluster status
    - Database (via the session factory)
    """
    from src.admin.agent import _handle_health_check

    services = await _handle_health_check()

    # Determine overall status
    statuses = []
    for svc_name, svc_data in services.items():
        if isinstance(svc_data, dict):
            svc_status = svc_data.get("status", "unknown")
            statuses.append(svc_status)

    if all(s in ("available", "accessible", "ACTIVE") for s in statuses):
        overall = "healthy"
    elif any(s in ("error", "unavailable") for s in statuses):
        overall = "degraded"
    else:
        overall = "partial"

    return HealthResponse(
        overall=overall,
        services=services,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


@admin_router.get(
    "/system/stats",
    response_model=StatsResponse,
    summary="Platform statistics",
    dependencies=[Depends(require_admin)],
)
async def system_stats(
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """Get platform statistics: user count, case count, message count.

    Queries the database for aggregate counts across all platform
    entities. These are live counts, not cached.
    """
    from src.admin.agent import _handle_system_stats

    stats = await _handle_system_stats(db)

    if "error" in stats:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {stats['error']}",
        )

    return StatsResponse(
        total_users=stats.get("total_users", 0),
        active_users=stats.get("active_users", 0),
        total_cases=stats.get("total_cases", 0),
        total_messages=stats.get("total_messages", 0),
        total_beta_invites=stats.get("total_beta_invites", 0),
        active_beta_users=stats.get("active_beta_users", 0),
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Internal Chat Agent
# ---------------------------------------------------------------------------


@admin_router.post(
    "/agent/chat",
    response_model=AgentChatResponse,
    summary="Admin agent chat",
    dependencies=[Depends(require_admin)],
)
async def admin_agent_chat(
    body: AgentChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: dict[str, Any] = Depends(require_admin),
) -> AgentChatResponse:
    """Process an admin command via the internal agent.

    The agent uses the LLM provider (CPAA) with a special admin system
    prompt to understand the admin's intent. It gathers live data from
    the system (git, database, AWS) and formats a contextual response.

    Destructive operations (deploy, revoke) are NEVER auto-executed.
    The agent returns a confirmation prompt and the admin must call
    the dedicated endpoint to execute.

    Every interaction is logged to AdminAuditLog.
    """
    admin_email = admin.get("email", "unknown")
    ip = get_client_ip(request)

    result = await _agent.process(
        message=body.message,
        admin_email=admin_email,
        db=db,
        ip_address=ip,
    )

    return AgentChatResponse(
        response=result["response"],
        intent=result["intent"],
        requires_confirmation=result["requires_confirmation"],
        timestamp=result["timestamp"],
    )


@admin_router.get(
    "/agent/capabilities",
    summary="List agent capabilities",
    dependencies=[Depends(require_admin)],
)
async def agent_capabilities() -> dict[str, str]:
    """List the admin agent's available capabilities."""
    return await _agent.list_capabilities()
