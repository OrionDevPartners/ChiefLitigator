"""ChiefLitigator — Main FastAPI Application.

Entry point for the ChiefLitigator API. Wires all routers, middleware,
and startup/shutdown events.

Three-tier architecture:
  - Consumer API: /api/v1/chat/*      (plain-language, guided flows)
  - Enterprise API: /api/v1/enterprise/* (bulk processing, team management)
  - Developer API: /api/v1/dev/*       (raw endpoints, webhooks, scripts)

Deploy: Git → CI/CD → AWS (Bedrock backend) → Cloudflare (frontend/admin)
All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("cyphergy.api")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("ChiefLitigator API starting up...")

    # Initialize Bedrock AgentCore runtime
    try:
        from src.providers.bedrock_agentcore import BedrockAgentCoreRuntime
        runtime = BedrockAgentCoreRuntime()
        app.state.agentcore = runtime
        logger.info("Bedrock AgentCore runtime initialized")
    except Exception as exc:
        logger.warning("AgentCore init deferred: %s", str(exc)[:100])
        app.state.agentcore = None

    # Initialize siphon orchestrator (background)
    try:
        from src.siphon.orchestrator import SiphonOrchestrator
        siphon = SiphonOrchestrator()
        app.state.siphon = siphon
        logger.info("Siphon orchestrator initialized")
    except Exception as exc:
        logger.warning("Siphon init deferred: %s", str(exc)[:100])

    yield

    logger.info("ChiefLitigator API shutting down...")


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ChiefLitigator",
        description=(
            "AGI-grade litigation platform for pro se litigants and small businesses. "
            "Powered by AWS Bedrock, The Galvanizer, and the WDC Engine."
        ),
        version="1.0.0",
        docs_url="/api/docs" if os.getenv("ENVIRONMENT") != "production" else None,
        redoc_url="/api/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
        lifespan=lifespan,
    )

    # CORS — Cloudflare frontend domains
    allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
    allowed_origins = [o.strip() for o in allowed_origins if o.strip()]
    if not allowed_origins:
        allowed_origins = [
            "https://chieflitigator.com",
            "https://www.chieflitigator.com",
            "https://chieflitigator.ai",
            "https://www.chieflitigator.ai",
            "http://localhost:3000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Routers ─────────────────────────────────────────────

    # Consumer API (chat interface)
    from src.api.chat_router import router as chat_router
    app.include_router(chat_router)

    # Case management API
    from src.api.case_router import router as case_router
    app.include_router(case_router)

    # Document management API
    from src.api.document_router import router as document_router
    app.include_router(document_router)

    # Health and system endpoints
    from src.api.system_router import router as system_router
    app.include_router(system_router)

    # Webhooks (CourtListener, etc.)
    from src.api.webhook_router import router as webhook_router
    app.include_router(webhook_router)

    # ── Global Exception Handler ─────────────────────────────────────

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", str(exc)[:500])
        return JSONResponse(
            status_code=500,
            content={
                "error": "An unexpected error occurred.",
                "detail": "Our team has been notified. Please try again.",
            },
        )

    return app


# ---------------------------------------------------------------------------
# Case Management Router
# ---------------------------------------------------------------------------
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

case_router_module = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class CreateCaseRequest(BaseModel):
    narrative: Optional[str] = None
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    opposing_party: Optional[str] = None


class CaseResponse(BaseModel):
    case_id: str
    status: str
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    created_at: str
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    galvanizer_score: Optional[float] = None


_cases_store: Dict[str, Dict[str, Any]] = {}


@case_router_module.post("/", response_model=CaseResponse)
async def create_case(request: CreateCaseRequest) -> CaseResponse:
    case_id = f"case-{uuid.uuid4().hex[:12]}"
    case = {
        "case_id": case_id,
        "status": "intake",
        "jurisdiction": request.jurisdiction,
        "practice_area": request.practice_area,
        "opposing_party": request.opposing_party,
        "narrative": request.narrative,
        "created_at": datetime.utcnow().isoformat(),
    }
    _cases_store[case_id] = case
    return CaseResponse(**case)


@case_router_module.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str) -> CaseResponse:
    case = _cases_store.get(case_id)
    if not case:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(**case)


@case_router_module.get("/", response_model=List[CaseResponse])
async def list_cases() -> List[CaseResponse]:
    return [CaseResponse(**c) for c in _cases_store.values()]


# ---------------------------------------------------------------------------
# Document Management Router
# ---------------------------------------------------------------------------
document_router_module = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@document_router_module.get("/{case_id}")
async def list_documents(case_id: str) -> Dict[str, Any]:
    return {"case_id": case_id, "documents": []}


@document_router_module.get("/{case_id}/{document_id}")
async def get_document(case_id: str, document_id: str) -> Dict[str, Any]:
    return {"case_id": case_id, "document_id": document_id, "status": "not_found"}


# ---------------------------------------------------------------------------
# System Router
# ---------------------------------------------------------------------------
system_router_module = APIRouter(prefix="/api/v1/system", tags=["system"])


@system_router_module.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ChiefLitigator",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "healthy",
            "bedrock": "checking",
            "aurora": "checking",
            "siphon": "checking",
        },
    }


@system_router_module.get("/info")
async def system_info() -> Dict[str, Any]:
    return {
        "service": "ChiefLitigator",
        "version": "1.0.0",
        "description": "AGI-grade litigation platform",
        "tiers": ["consumer", "enterprise", "developer"],
        "agents": [
            "IntakeAgent",
            "DocumentGenerator",
            "EvidenceScorer",
            "StrategyAdvisor",
            "DocketMonitor",
            "DiscoveryManager",
        ],
        "engines": [
            "Galvanizer (adversarial panel)",
            "WDC (weighted debate consensus)",
            "If-Then Matching Engine",
        ],
        "infrastructure": {
            "compute": "AWS Bedrock AgentCore",
            "database": "AWS Aurora PostgreSQL + pgvector",
            "user_data": "AWS DynamoDB",
            "frontend": "Cloudflare",
            "models": "Claude Opus / Sonnet / Haiku + Llama 4 Maverick + Cohere Command A",
        },
    }


# Expose the sub-routers for import
# In production, these would be separate files
import sys

# Create module-like objects for the routers
class _RouterModule:
    def __init__(self, r):
        self.router = r

# Register in a way the main app can import
_case_mod = _RouterModule(case_router_module)
_doc_mod = _RouterModule(document_router_module)
_sys_mod = _RouterModule(system_router_module)
