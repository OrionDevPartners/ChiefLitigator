"""Case persistence API routes.

Endpoints:
    POST   /api/v1/cases              -- create a new case
    GET    /api/v1/cases              -- list the authenticated user's cases
    GET    /api/v1/cases/{case_id}    -- get a single case with messages
    POST   /api/v1/cases/{case_id}/messages -- add a message to a case
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.crud import create_case, create_message, get_case_with_messages, get_cases_for_user

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateCaseRequest(BaseModel):
    """Payload for creating a new case."""

    name: str = Field(..., min_length=1, max_length=512, description="Case name.")
    jurisdiction: Optional[str] = Field(default=None, max_length=64, description="Optional jurisdiction.")


class MessageOut(BaseModel):
    """Serialized message."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    role: str
    content: str
    created_at: str


class CaseOut(BaseModel):
    """Serialized case (without messages)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    jurisdiction: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


class CaseDetailOut(CaseOut):
    """Serialized case with its messages."""

    messages: List[MessageOut] = Field(default_factory=list)


class AddMessageRequest(BaseModel):
    """Payload for adding a message to a case."""

    role: str = Field(..., min_length=1, max_length=16, description="Message role (e.g. 'user', 'assistant').")
    content: str = Field(..., min_length=1, max_length=100_000, description="Message content.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id(request: Request) -> uuid.UUID:
    """Extract user_id from the JWT payload attached by auth middleware."""
    payload = getattr(request.state, "jwt_payload", None)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    sub: Optional[str] = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")
    try:
        return uuid.UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid 'sub' claim in token.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=CaseOut, status_code=201)
async def create_case_endpoint(
    body: CreateCaseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CaseOut:
    """Create a new case for the authenticated user."""
    user_id = _get_user_id(request)
    case = await create_case(
        db,
        user_id=user_id,
        name=body.name,
        jurisdiction=body.jurisdiction,
    )
    return CaseOut(
        id=str(case.id),
        user_id=str(case.user_id),
        name=case.name,
        jurisdiction=case.jurisdiction,
        status=case.status,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
    )


@router.get("", response_model=List[CaseOut])
async def list_cases_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> List[CaseOut]:
    """List all cases belonging to the authenticated user."""
    user_id = _get_user_id(request)
    cases = await get_cases_for_user(db, user_id=user_id)
    return [
        CaseOut(
            id=str(c.id),
            user_id=str(c.user_id),
            name=c.name,
            jurisdiction=c.jurisdiction,
            status=c.status,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in cases
    ]


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case_endpoint(
    case_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CaseDetailOut:
    """Get a single case with all its messages."""
    user_id = _get_user_id(request)
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found.")
    case = await get_case_with_messages(db, case_id=cid, user_id=user_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return CaseDetailOut(
        id=str(case.id),
        user_id=str(case.user_id),
        name=case.name,
        jurisdiction=case.jurisdiction,
        status=case.status,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
        messages=[
            MessageOut(
                id=str(m.id),
                case_id=str(m.case_id),
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in case.messages
        ],
    )


@router.post("/{case_id}/messages", response_model=MessageOut, status_code=201)
async def add_message_endpoint(
    case_id: str,
    body: AddMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    """Add a message to an existing case."""
    user_id = _get_user_id(request)
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found.")
    # Verify case exists and belongs to user
    case = await get_case_with_messages(db, case_id=cid, user_id=user_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    message = await create_message(
        db,
        case_id=cid,
        role=body.role,
        content=body.content,
    )
    return MessageOut(
        id=str(message.id),
        case_id=str(message.case_id),
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )
