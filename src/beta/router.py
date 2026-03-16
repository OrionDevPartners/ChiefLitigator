"""Admin-facing API endpoints for beta gate management.

POST /api/v1/admin/beta/approve  -- Approve a beta user
POST /api/v1/admin/beta/revoke   -- Revoke beta access
GET  /api/v1/admin/beta/invites  -- List all beta invites

These endpoints are intended for admin use only. Authentication and
admin role verification should be enforced by upstream middleware.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.beta.email import send_beta_invite
from src.beta.gate import BetaGate
from src.beta.models import BetaInvite
from src.database.engine import get_db

logger = logging.getLogger("cyphergy.beta.router")

beta_router = APIRouter(prefix="/api/v1/admin/beta", tags=["beta-admin"])

_gate = BetaGate()

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ApproveRequest(BaseModel):
    """Request body for approving a beta user."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=256)
    invited_by: str = Field(
        default="admin@cyphergy.ai",
        description="Admin email performing the approval.",
    )


class ApproveResponse(BaseModel):
    """Response after approving a beta user."""

    email: str
    invite_id: str
    user_id: str
    email_sent: bool


class RevokeRequest(BaseModel):
    """Request body for revoking beta access."""

    user_id: str = Field(..., description="UUID of the user to revoke.")


class RevokeResponse(BaseModel):
    """Response after revoking beta access."""

    user_id: str
    status: str


class InviteListItem(BaseModel):
    """Single invite in the list response."""

    invite_id: str
    user_id: str
    invited_by: str
    status: str
    locked_ip: str | None
    created_at: str
    activated_at: str | None
    revoked_at: str | None


class InviteListResponse(BaseModel):
    """Response listing all beta invites."""

    invites: list[InviteListItem]
    count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@beta_router.post(
    "/approve",
    response_model=ApproveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Approve a beta user",
)
async def approve_beta_user(
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> ApproveResponse:
    """Approve a new beta user and send invite credentials.

    Creates the user account with a random password, creates the
    BetaInvite record, and sends the credentials via email.
    """
    try:
        result = await _gate.approve_user(
            email=body.email,
            name=body.name,
            db=db,
            invited_by=body.invited_by,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # Send invite email (password is in result but NEVER logged)
    email_sent = await send_beta_invite(
        email=result["email"],
        name=body.name,
        password=result["password"],
    )

    logger.info(
        "beta_approve_endpoint | user_id=%s email_sent=%s",
        result["user_id"],
        email_sent,
    )

    return ApproveResponse(
        email=result["email"],
        invite_id=result["invite_id"],
        user_id=result["user_id"],
        email_sent=email_sent,
    )


@beta_router.post(
    "/revoke",
    response_model=RevokeResponse,
    summary="Revoke beta access",
)
async def revoke_beta_user(
    body: RevokeRequest,
    db: AsyncSession = Depends(get_db),
) -> RevokeResponse:
    """Revoke a beta user's access and deactivate their account."""
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

    await _gate.revoke_user(user_id, db)

    logger.info("beta_revoke_endpoint | user_id=%s", user_id)

    return RevokeResponse(
        user_id=body.user_id,
        status="revoked",
    )


@beta_router.get(
    "/invites",
    response_model=InviteListResponse,
    summary="List all beta invites",
)
async def list_beta_invites(
    db: AsyncSession = Depends(get_db),
) -> InviteListResponse:
    """List all beta invites with their current status."""
    stmt = select(BetaInvite).order_by(BetaInvite.created_at.desc())
    result = await db.execute(stmt)
    invites = list(result.scalars().all())

    items = [
        InviteListItem(
            invite_id=str(inv.id),
            user_id=str(inv.user_id),
            invited_by=inv.invited_by,
            status=inv.status,
            locked_ip=inv.locked_ip,
            created_at=inv.created_at.isoformat() if inv.created_at else "",
            activated_at=inv.activated_at.isoformat() if inv.activated_at else None,
            revoked_at=inv.revoked_at.isoformat() if inv.revoked_at else None,
        )
        for inv in invites
    ]

    return InviteListResponse(invites=items, count=len(items))
