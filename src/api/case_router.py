"""Case Management Router — CRUD operations for litigation cases.

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.api.case_router")

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

_cases_store: Dict[str, Dict[str, Any]] = {}


class CreateCaseRequest(BaseModel):
    narrative: Optional[str] = None
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    opposing_party: Optional[str] = None
    court: Optional[str] = None


class UpdateCaseRequest(BaseModel):
    status: Optional[str] = None
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    opposing_party: Optional[str] = None
    court: Optional[str] = None
    case_number: Optional[str] = None
    judge: Optional[str] = None


class CaseResponse(BaseModel):
    case_id: str
    status: str = "intake"
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    opposing_party: Optional[str] = None
    court: Optional[str] = None
    case_number: Optional[str] = None
    judge: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    galvanizer_score: Optional[float] = None


@router.post("/", response_model=CaseResponse)
async def create_case(request: CreateCaseRequest) -> CaseResponse:
    """Create a new litigation case."""
    case_id = f"case-{uuid.uuid4().hex[:12]}"
    case = {
        "case_id": case_id,
        "status": "intake",
        "jurisdiction": request.jurisdiction,
        "practice_area": request.practice_area,
        "opposing_party": request.opposing_party,
        "court": request.court,
        "narrative": request.narrative,
        "created_at": datetime.utcnow().isoformat(),
    }
    _cases_store[case_id] = case

    # Auto-trigger intake if narrative provided
    if request.narrative:
        try:
            from src.agents.intake_agent import IntakeAgent
            agent = IntakeAgent()
            result = await agent.process_narrative(
                narrative=request.narrative,
                jurisdiction=request.jurisdiction,
            )
            case["intake_result"] = result.model_dump() if hasattr(result, "model_dump") else {}
            case["status"] = "intake_complete"
        except Exception as exc:
            logger.warning("Auto-intake deferred: %s", str(exc)[:100])

    return CaseResponse(**{k: v for k, v in case.items() if k in CaseResponse.model_fields})


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str) -> CaseResponse:
    """Get a case by ID."""
    case = _cases_store.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(**{k: v for k, v in case.items() if k in CaseResponse.model_fields})


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(case_id: str, request: UpdateCaseRequest) -> CaseResponse:
    """Update a case."""
    case = _cases_store.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    updates = request.model_dump(exclude_none=True)
    case.update(updates)
    return CaseResponse(**{k: v for k, v in case.items() if k in CaseResponse.model_fields})


@router.get("/", response_model=List[CaseResponse])
async def list_cases() -> List[CaseResponse]:
    """List all cases."""
    return [
        CaseResponse(**{k: v for k, v in c.items() if k in CaseResponse.model_fields})
        for c in _cases_store.values()
    ]


@router.post("/{case_id}/analyze")
async def analyze_case(case_id: str) -> Dict[str, Any]:
    """Run full strategic analysis on a case."""
    case = _cases_store.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    from src.agents.strategy_advisor import StrategyAdvisor
    advisor = StrategyAdvisor()
    analysis = await advisor.analyze_case(
        case_id=case_id,
        case_context=case,
    )

    return analysis.model_dump()


@router.post("/{case_id}/galvanize")
async def galvanize_case(case_id: str, document_id: str) -> Dict[str, Any]:
    """Run a document through The Galvanizer for adversarial review."""
    case = _cases_store.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    from src.orchestrator.galvanizer import Galvanizer
    galvanizer = Galvanizer()

    result = await galvanizer.galvanize(
        case_id=case_id,
        document_id=document_id,
        document_text="",  # Would be resolved from document store
        case_context=case,
    )

    return result.model_dump()
