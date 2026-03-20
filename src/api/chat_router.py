"""Chat Router — Consumer-facing API for the ChiefLitigator chat interface.

This is the primary API that pro se litigants and small businesses interact
with. It provides a conversational interface that routes user messages to
the appropriate agents and returns plain-language responses.

The chat is persistent and visible on ALL screens (consumer UI mandate).

Endpoints:
  POST /api/v1/chat/message       — Send a message and get a response
  POST /api/v1/chat/intake        — Start a new case intake
  GET  /api/v1/chat/history       — Get chat history for a case
  POST /api/v1/chat/upload        — Upload documents for a case
  GET  /api/v1/chat/status        — Get case status and next steps
  POST /api/v1/chat/approve       — Approve a document for filing
  GET  /api/v1/chat/guided-flow   — Get guided intake questions

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.api.chat_router")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class ChatMessageRequest(BaseModel):
    """User sends a chat message."""
    case_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=10000)
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Response to a chat message."""
    message_id: str
    case_id: str
    response_text: str
    plain_language: bool = True
    suggested_actions: List[Dict[str, str]] = Field(default_factory=list)
    documents_ready: List[Dict[str, str]] = Field(default_factory=list)
    deadlines: List[Dict[str, str]] = Field(default_factory=list)
    confidence: float = 0.0
    needs_more_info: bool = False
    follow_up_questions: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class IntakeRequest(BaseModel):
    """Start a new case intake."""
    narrative: Optional[str] = None
    guided_responses: Optional[Dict[str, str]] = None
    jurisdiction: Optional[str] = None


class IntakeResponse(BaseModel):
    """Response to case intake."""
    case_id: str
    intake_id: str
    legal_issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_documents: List[str] = Field(default_factory=list)
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    plain_language_summary: str
    confidence: float
    needs_more_info: bool = False
    follow_up_questions: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class CaseStatusResponse(BaseModel):
    """Current status of a case."""
    case_id: str
    status: str
    phase: str
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    galvanizer_scores: Dict[str, float] = Field(default_factory=dict)
    next_actions: List[str] = Field(default_factory=list)
    plain_language_summary: str = ""


class DocumentApprovalRequest(BaseModel):
    """User approves a document for filing."""
    case_id: str
    document_id: str
    approved: bool = True
    user_notes: Optional[str] = None


class DocumentApprovalResponse(BaseModel):
    """Response to document approval."""
    document_id: str
    status: str
    filing_id: Optional[str] = None
    next_steps: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chat Message History (in-memory for now, DynamoDB in production)
# ---------------------------------------------------------------------------
_chat_history: Dict[str, List[Dict[str, Any]]] = {}
_cases: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """Send a chat message and get a response.

    This is the primary interaction endpoint. The system:
    1. Identifies the user's intent
    2. Routes to the appropriate agent(s)
    3. Returns a plain-language response with suggested actions
    """
    case_id = request.case_id or f"case-{uuid.uuid4().hex[:12]}"
    message_id = f"msg-{uuid.uuid4().hex[:8]}"

    # Store user message
    if case_id not in _chat_history:
        _chat_history[case_id] = []
    _chat_history[case_id].append({
        "role": "user",
        "message": request.message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Route to appropriate agent based on intent
    intent = _classify_intent(request.message)
    response_text = ""
    suggested_actions = []
    follow_ups = []
    confidence = 0.0

    try:
        if intent == "new_case":
            # Route to Intake Agent
            from src.agents.intake_agent import IntakeAgent
            agent = IntakeAgent()
            result = await agent.process_narrative(request.message)
            response_text = result.plain_language_summary
            confidence = result.confidence
            follow_ups = result.follow_up_questions
            suggested_actions = [
                {"action": "start_intake", "label": "Start your case"},
                {"action": "upload_documents", "label": "Upload documents"},
            ]

        elif intent == "document_request":
            # Route to Document Generator
            response_text = (
                "I can draft that document for you. Let me gather the details "
                "I need to create a court-ready version. "
            )
            suggested_actions = [
                {"action": "generate_document", "label": "Draft the document"},
            ]

        elif intent == "status_check":
            # Return case status
            case = _cases.get(case_id, {})
            response_text = (
                f"Here's where your case stands: {case.get('status', 'Getting started')}. "
                f"Your next step is: {case.get('next_action', 'Tell me about your situation')}."
            )

        elif intent == "evidence_question":
            # Route to Evidence Scorer
            response_text = (
                "Let me analyze the evidence you have. Upload your documents "
                "and I'll score their strength and identify any gaps."
            )
            suggested_actions = [
                {"action": "upload_evidence", "label": "Upload evidence"},
                {"action": "score_evidence", "label": "Score my evidence"},
            ]

        elif intent == "deadline_question":
            # Route to Deadline Calculator
            response_text = (
                "I'll check your deadlines. Let me review your case details "
                "and calculate all applicable filing deadlines."
            )

        elif intent == "strategy_question":
            # Route to Strategy Advisor
            from src.agents.strategy_advisor import StrategyAdvisor
            advisor = StrategyAdvisor()
            analysis = await advisor.analyze_case(
                case_id=case_id,
                case_context={"facts": request.message},
            )
            response_text = analysis.plain_language_summary
            confidence = analysis.win_probability

        else:
            # General legal question — route through dual-brain
            response_text = await _handle_general_question(request.message, case_id)
            confidence = 0.7

    except Exception as exc:
        logger.error("Chat processing error: %s", str(exc)[:200])
        response_text = (
            "I encountered an issue processing your request. "
            "Let me try a different approach. Could you rephrase your question?"
        )

    # Store assistant response
    _chat_history[case_id].append({
        "role": "assistant",
        "message": response_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return ChatMessageResponse(
        message_id=message_id,
        case_id=case_id,
        response_text=response_text,
        suggested_actions=suggested_actions,
        confidence=confidence,
        needs_more_info=len(follow_ups) > 0,
        follow_up_questions=follow_ups,
    )


@router.post("/intake", response_model=IntakeResponse)
async def start_intake(request: IntakeRequest) -> IntakeResponse:
    """Start a new case intake process."""
    from src.agents.intake_agent import IntakeAgent

    agent = IntakeAgent()
    case_id = f"case-{uuid.uuid4().hex[:12]}"

    if request.narrative:
        result = await agent.process_narrative(
            narrative=request.narrative,
            jurisdiction=request.jurisdiction,
        )
    elif request.guided_responses:
        result = await agent.process_guided_responses(
            responses=request.guided_responses,
        )
    else:
        raise HTTPException(status_code=400, detail="Provide either narrative or guided_responses")

    # Store case
    _cases[case_id] = {
        "case_id": case_id,
        "intake_id": result.intake_id,
        "status": "intake_complete",
        "jurisdiction": result.jurisdiction,
        "created_at": datetime.utcnow().isoformat(),
    }

    return IntakeResponse(
        case_id=case_id,
        intake_id=result.intake_id,
        legal_issues=[{"description": i.description, "confidence": i.confidence} for i in result.legal_issues],
        recommended_documents=result.recommended_documents,
        deadlines=result.deadlines,
        plain_language_summary=result.plain_language_summary,
        confidence=result.confidence,
        needs_more_info=result.needs_more_info,
        follow_up_questions=result.follow_up_questions,
        next_steps=[
            "Review the legal issues identified above",
            "Upload any documents you have",
            "We'll draft the documents you need",
        ],
    )


@router.get("/history")
async def get_chat_history(case_id: str) -> Dict[str, Any]:
    """Get chat history for a case."""
    history = _chat_history.get(case_id, [])
    return {
        "case_id": case_id,
        "messages": history,
        "total": len(history),
    }


@router.post("/upload")
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Upload a document for a case."""
    from src.agents.discovery_manager import DiscoveryManager

    # Save uploaded file
    upload_dir = os.getenv("UPLOAD_DIR", "/tmp/chieflitigator/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{file.filename}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Process through Discovery Manager
    manager = DiscoveryManager()
    doc = await manager.ingest_document(
        case_id=case_id,
        file_path=file_path,
        filename=file.filename or "unknown",
    )

    return {
        "document_id": doc.doc_id,
        "filename": file.filename,
        "status": doc.status,
        "classification": doc.classification,
        "privilege_flags": doc.privilege_flags,
        "message": f"Document '{file.filename}' uploaded and processed successfully.",
    }


@router.get("/status", response_model=CaseStatusResponse)
async def get_case_status(case_id: str) -> CaseStatusResponse:
    """Get the current status of a case."""
    case = _cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return CaseStatusResponse(
        case_id=case_id,
        status=case.get("status", "unknown"),
        phase=case.get("phase", "intake"),
        plain_language_summary=case.get("summary", "Your case is being processed."),
    )


@router.post("/approve", response_model=DocumentApprovalResponse)
async def approve_document(request: DocumentApprovalRequest) -> DocumentApprovalResponse:
    """Approve a document for filing with the court."""
    if not request.approved:
        return DocumentApprovalResponse(
            document_id=request.document_id,
            status="revision_requested",
            next_steps=["Tell us what changes you'd like and we'll revise the document."],
        )

    # Route to Court Portal for filing
    from src.integrations.court_portal import CourtPortalConnector

    portal = CourtPortalConnector()
    case = _cases.get(request.case_id, {})

    filing = await portal.prepare_filing(
        case_id=request.case_id,
        document_id=request.document_id,
        document_path="",  # Would be resolved from document store
        jurisdiction=case.get("jurisdiction", ""),
        court=case.get("court", ""),
        document_type=case.get("document_type", ""),
    )

    return DocumentApprovalResponse(
        document_id=request.document_id,
        status="ready_for_filing",
        filing_id=filing.filing_id,
        next_steps=filing.next_steps,
    )


@router.get("/guided-flow")
async def get_guided_flow(flow_type: str = "general") -> Dict[str, Any]:
    """Get guided intake flow questions."""
    from src.agents.intake_agent import IntakeAgent

    agent = IntakeAgent()
    questions = agent.get_guided_flow(flow_type)

    return {
        "flow_type": flow_type,
        "questions": [q.model_dump() for q in questions],
        "total_questions": len(questions),
    }


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------
def _classify_intent(message: str) -> str:
    """Classify user message intent for routing."""
    msg_lower = message.lower()

    # New case indicators
    new_case_terms = [
        "i was", "i got", "someone", "my landlord", "my employer",
        "i need help", "i'm being", "they", "sued", "evicted",
        "i want to file", "i need to file",
    ]
    if any(term in msg_lower for term in new_case_terms):
        return "new_case"

    # Document request indicators
    doc_terms = [
        "draft", "write", "prepare", "create", "generate",
        "complaint", "motion", "answer", "letter", "lien",
    ]
    if any(term in msg_lower for term in doc_terms):
        return "document_request"

    # Status check indicators
    status_terms = ["status", "where", "update", "progress", "what's next"]
    if any(term in msg_lower for term in status_terms):
        return "status_check"

    # Evidence indicators
    evidence_terms = ["evidence", "proof", "document", "upload", "exhibit"]
    if any(term in msg_lower for term in evidence_terms):
        return "evidence_question"

    # Deadline indicators
    deadline_terms = ["deadline", "when", "how long", "time limit", "statute of limitations"]
    if any(term in msg_lower for term in deadline_terms):
        return "deadline_question"

    # Strategy indicators
    strategy_terms = ["chance", "win", "settle", "strategy", "should i", "what are my options"]
    if any(term in msg_lower for term in strategy_terms):
        return "strategy_question"

    return "general"


async def _handle_general_question(message: str, case_id: str) -> str:
    """Handle general legal questions through the dual-brain system."""
    from src.providers.llm_provider import get_provider

    provider = get_provider()
    response = await provider.create_message(
        model=os.getenv("BEDROCK_TIER2_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
        max_tokens=2048,
        temperature=0.3,
        system=(
            "You are ChiefLitigator, an AI legal assistant helping pro se litigants "
            "and small businesses. Explain everything in plain English. Be helpful, "
            "accurate, and reassuring. Never fabricate legal citations. Always clarify "
            "that you provide legal information, not legal advice."
        ),
        messages=[{"role": "user", "content": message}],
    )

    return response.text
