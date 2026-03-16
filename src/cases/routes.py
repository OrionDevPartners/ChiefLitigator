"""Case persistence API routes.

Endpoints:
    POST   /api/v1/cases              — create a new case
    GET    /api/v1/cases              — list the authenticated user's cases
    GET    /api/v1/cases/{case_id}    — get a single case with messages
    POST   /api/v1/cases/{case_id}/messages — add a message to a case
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.database.crud import add_message, create_case, get_case, list_cases

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CreateCaseRequest(BaseModel):
    """Payload for creating a new case."""

    title: str = Field(..., min_length=1, max_length=500, description="Case title.")
    description: str = Field(default="", max_length=10_000, description="Optional case description.")
    jurisdiction: Optional[str] = Field(default=None, max_length=100, description="Optional jurisdiction.")


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
    title: str
    description: str
    jurisdiction: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


class CaseDetailOut(CaseOut):
    """Serialized case with its messages."""

    messages: List[MessageOut] = Field(default_factory=list)


class AddMessageRequest(BaseModel):
    """Payload for adding a message to a case."""

    role: str = Field(..., min_length=1, max_length=50, description="Message role (e.g. 'user', 'assistant').")
    content: str = Field(..., min_length=1, max_length=100_000, description="Message content.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id(request: Request) -> str:
    """Extract user_id from the JWT payload attached by auth middleware."""
    payload = getattr(request.state, "jwt_payload", None)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")
    return user_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=CaseOut, status_code=201)
async def create_case_endpoint(
    body: CreateCaseRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> CaseOut:
    """Create a new case for the authenticated user."""
    user_id = _get_user_id(request)
    case = await create_case(
        session,
        user_id=user_id,
        title=body.title,
        description=body.description,
        jurisdiction=body.jurisdiction,
    )
    return CaseOut(
        id=case.id,
        user_id=case.user_id,
        title=case.title,
        description=case.description,
        jurisdiction=case.jurisdiction,
        status=case.status,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
    )


@router.get("", response_model=List[CaseOut])
async def list_cases_endpoint(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> List[CaseOut]:
    """List all cases belonging to the authenticated user."""
    user_id = _get_user_id(request)
    cases = await list_cases(session, user_id=user_id)
    return [
        CaseOut(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            description=c.description,
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
    session: AsyncSession = Depends(get_session),
) -> CaseDetailOut:
    """Get a single case with all its messages."""
    user_id = _get_user_id(request)
    case = await get_case(session, case_id=case_id, user_id=user_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return CaseDetailOut(
        id=case.id,
        user_id=case.user_id,
        title=case.title,
        description=case.description,
        jurisdiction=case.jurisdiction,
        status=case.status,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
        messages=[
            MessageOut(
                id=m.id,
                case_id=m.case_id,
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
    session: AsyncSession = Depends(get_session),
) -> MessageOut:
    """Add a message to an existing case."""
    user_id = _get_user_id(request)
    # Verify case exists and belongs to user
    case = await get_case(session, case_id=case_id, user_id=user_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    message = await add_message(
        session,
        case_id=case_id,
        role=body.role,
        content=body.content,
    )
    return MessageOut(
        id=message.id,
        case_id=message.case_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )
