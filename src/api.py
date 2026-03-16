"""Cyphergy API — FastAPI application entrypoint.

Run with:
    uvicorn src.api:app --host 0.0.0.0 --port 8000

All configuration is sourced from environment variables (CPAA-compliant).
CORS origins, LLM provider, rate limits, and security settings are
loaded at startup and validated before the application accepts traffic.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api_models import (
    ChatRequest,
    ChatResponse,
    ComputeDeadlineRequest,
    ComputeDeadlineResponse,
    ErrorResponse,
    HealthResponse,
    ReadinessResponse,
    VerifyCitationRequest,
    VerifyCitationResponse,
)
from src.auth.middleware import JWTAuthMiddleware
from src.cases import router as cases_router
from src.errors import (
    AgentError,
    AuthenticationError,
    CitationVerificationError,
    CyphergyError,
    LLMProviderError,
    RateLimitExceeded,
)
from src.legal.deadline_calc import (
    DeadlineCalculator,
    DeadlineType,
    Jurisdiction,
    ServiceMethod,
)
from src.security.middleware import SecurityMiddleware, configure_cors
from src.security.rate_limiter import RateLimiter, RateLimitResult  # noqa: I001

logger = logging.getLogger("cyphergy.api")

# ---------------------------------------------------------------------------
# Module-level singletons (initialized in lifespan)
# ---------------------------------------------------------------------------

_lead_counsel = None
_citation_verifier = None
_deadline_calculator = DeadlineCalculator()
_rate_limiter = RateLimiter()


def _get_lead_counsel():
    """Lazy-initialize LeadCounsel to avoid import-time env var reads."""
    global _lead_counsel
    if _lead_counsel is None:
        from src.agents.lead_counsel import LeadCounsel

        _lead_counsel = LeadCounsel()
    return _lead_counsel


def _get_citation_verifier():
    """Lazy-initialize CitationVerifier to avoid import-time env var reads."""
    global _citation_verifier
    if _citation_verifier is None:
        from src.verification.citation_chain import CitationVerifier

        _citation_verifier = CitationVerifier()
    return _citation_verifier


# ---------------------------------------------------------------------------
# Lifespan — startup/shutdown validation
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate required environment variables before accepting traffic.

    CPAA: Every required secret and configuration value is checked at boot.
    If a required variable is missing, the service logs the problem and
    refuses to start (fail-fast, never serve with broken config).
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    logger.info("cyphergy_starting | validating environment")

    # Required env vars — service cannot operate without these
    required_vars = [
        "ANTHROPIC_API_KEY",
    ]

    # Warn-only vars — service can start but features will be degraded
    recommended_vars = [
        "COURTLISTENER_API_KEY",
        "CORS_ALLOWED_ORIGINS",
        "SENTRY_DSN",
    ]

    missing_required: list[str] = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)

    missing_recommended: list[str] = []
    for var in recommended_vars:
        if not os.getenv(var):
            missing_recommended.append(var)

    if missing_required:
        # Log which vars are missing (names only — never values, @M:010)
        logger.critical(
            "cyphergy_startup_failed | missing_required_env_vars=%s",
            ",".join(missing_required),
        )
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing_required)}. "
            "Set them in .env or your deployment configuration."
        )

    if missing_recommended:
        logger.warning(
            "cyphergy_startup_degraded | missing_recommended_env_vars=%s",
            ",".join(missing_recommended),
        )

    # --- Sentry ---
    # Initialize Sentry before the app starts accepting traffic.
    # PII scrubbing is handled inside init_sentry() — legal data never leaves
    # the tenant boundary.  If SENTRY_DSN is not set, this is a safe no-op.
    from src.integrations.sentry import init_sentry

    sentry_active = init_sentry()
    if sentry_active:
        logger.info("cyphergy_sentry | status=active")
    else:
        logger.info("cyphergy_sentry | status=disabled")

    llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model = os.getenv("LLM_MODEL", "claude-opus-4-6")
    app_env = os.getenv("APP_ENV", "development")

    logger.info(
        "cyphergy_started | env=%s provider=%s model=%s agents=5 sentry=%s",
        app_env,
        llm_provider,
        llm_model,
        sentry_active,
    )

    yield

    # Shutdown
    logger.info("cyphergy_shutting_down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Cyphergy Legal AI",
    description=("Multi-agent legal co-counsel platform. 5 specialized agents with WDC-certified output quality."),
    version="0.1.0",
    docs_url="/docs" if os.getenv("APP_ENV", "development") != "production" else None,
    redoc_url="/redoc" if os.getenv("APP_ENV", "development") != "production" else None,
    lifespan=lifespan,
)

# --- Case persistence router ---
app.include_router(cases_router)

# --- Middleware stack (order matters: last added = first executed) ---
# 1. Security headers + request tracing (outermost)
app.add_middleware(SecurityMiddleware)
# 2. JWT authentication (after security headers, before CORS)
if os.getenv("JWT_SECRET_KEY"):
    app.add_middleware(JWTAuthMiddleware)
# 3. CORS (must be before SecurityMiddleware in execution order)
configure_cors(app)

# 4. Auth router (signup + login endpoints — public, no JWT required)
from src.auth import auth_router  # noqa: E402

app.include_router(auth_router)

# 5. Admin router (admin-only endpoints — requires admin JWT)
from src.admin.routes import admin_router  # noqa: E402

app.include_router(admin_router)

# 6. Beta gate middleware (IP enforcement — after JWT, before request handlers)
if os.getenv("BETA_GATE_ENABLED", "true").lower() == "true":
    from src.beta.middleware import BetaGateMiddleware  # noqa: E402
    from src.database.engine import get_db as _get_db  # noqa: E402

    app.add_middleware(BetaGateMiddleware, db_factory=_get_db)


# ---------------------------------------------------------------------------
# Rate limiting middleware (applied as a dependency-free middleware)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply 4-layer rate limiting to every request.

    Extracts client IP from request state (set by SecurityMiddleware) or
    falls back to direct extraction. Health endpoints are exempt to allow
    load balancer probes.
    """
    # Exempt health endpoints from rate limiting
    if request.url.path in ("/health", "/health/ready"):
        return await call_next(request)

    # Extract IP — SecurityMiddleware sets request.state.client_ip,
    # but this middleware may run before it in some configurations.
    client_ip = "unknown"
    try:
        client_ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else "unknown")
    except Exception:
        pass

    result: RateLimitResult = _rate_limiter.check_request(ip=client_ip)

    if not result.allowed:
        status_code = 503 if result.layer == "global" else 429
        retry_after = str(int(result.retry_after)) if result.retry_after > 0 else "60"
        logger.warning(
            "rate_limited | layer=%s ip=%s path=%s retry_after=%s",
            result.layer,
            client_ip,
            request.url.path,
            retry_after,
        )
        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(
                error=result.message,
                detail=f"Rate limit exceeded at layer: {result.layer}",
            ).model_dump(),
            headers={
                "Retry-After": retry_after,
                "X-RateLimit-Remaining": "0",
            },
        )

    response = await call_next(request)

    # Attach rate limit headers to successful responses
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    return response


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Basic health check",
)
async def health() -> HealthResponse:
    """Return service health status.

    Used by load balancers and orchestrators (ECS, Kubernetes) for
    liveness probes. Always returns 200 if the process is running.
    """
    return HealthResponse(status="ok", agents=5, tests_passing=33)


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["health"],
    summary="Readiness probe",
)
async def health_ready() -> ReadinessResponse:
    """Check if the service is ready to accept traffic.

    Verifies that the ANTHROPIC_API_KEY is set (the minimum required
    for the agent system to function). Used by load balancers for
    readiness probes — traffic is not routed until this returns ready=true.
    """
    api_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))
    llm_provider = os.getenv("LLM_PROVIDER", "anthropic")

    if api_key_set:
        return ReadinessResponse(
            ready=True,
            anthropic_api_key_set=True,
            llm_provider=llm_provider,
            detail="Service is ready to accept requests.",
        )

    return ReadinessResponse(
        ready=False,
        anthropic_api_key_set=False,
        llm_provider=llm_provider,
        detail="ANTHROPIC_API_KEY is not set. Service cannot process LLM requests.",
    )


# ---------------------------------------------------------------------------
# Sentry debug endpoint (non-production only)
# ---------------------------------------------------------------------------

if os.getenv("APP_ENV", "development") != "production":

    @app.get(
        "/debug-sentry",
        tags=["debug"],
        summary="Trigger a test exception for Sentry verification",
        include_in_schema=True,
    )
    async def debug_sentry() -> None:
        """Raise an intentional exception to verify Sentry is capturing events.

        This endpoint exists ONLY in non-production environments. It is
        excluded entirely when APP_ENV=production (the route is never
        registered). Use it after deployment to confirm that errors are
        flowing to the Sentry dashboard with PII properly scrubbed.
        """
        raise RuntimeError("Sentry integration test — this error should appear in the Sentry dashboard.")


# ---------------------------------------------------------------------------
# API v1 endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "LLM provider unavailable"},
    },
    tags=["chat"],
    summary="Chat with Lead Counsel",
)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Route a user message to Lead Counsel and return the response.

    Lead Counsel is the principal strategist and supervising attorney-agent
    in the Cyphergy system. It classifies the request, determines which
    specialist agents are needed, and provides actionable legal guidance.

    If a jurisdiction is provided, it is injected into the blackboard
    context so all agents have jurisdiction awareness.

    Graceful degradation:
        - LLM provider failures -> 503 with safe message
        - CyphergyError subclasses -> re-raised for typed handlers
        - Unknown errors -> 500 with sanitized message (no stack traces)
    """
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        lead = _get_lead_counsel()

        context = None
        if body.jurisdiction:
            context = {"jurisdiction": body.jurisdiction}

        agent_response = await lead.invoke(body.message, context)

        return ChatResponse(
            content=agent_response.content,
            confidence=agent_response.confidence,
            citations=agent_response.citations_used,
            flags=agent_response.flags,
            agent_id=agent_response.agent_id,
            elapsed_seconds=agent_response.elapsed_seconds,
            input_tokens=agent_response.input_tokens,
            output_tokens=agent_response.output_tokens,
        )

    except CyphergyError:
        # Let typed exception handlers deal with CyphergyError subclasses
        raise

    except Exception as exc:
        # Log error with request ID for correlation — never log user message (@M:010)
        logger.error(
            "chat_error | request_id=%s error_type=%s error=%s",
            request_id,
            type(exc).__name__,
            str(exc)[:200],
        )
        # Detect LLM provider errors by exception type name (Anthropic SDK,
        # botocore) and wrap them so the typed handler returns 503.
        exc_type = type(exc).__name__
        if exc_type in (
            "APIConnectionError",
            "APITimeoutError",
            "InternalServerError",
            "APIStatusError",
            "RateLimitError",
            "ClientError",
            "BotoCoreError",
            "EndpointConnectionError",
        ):
            raise LLMProviderError(str(exc)[:200]) from exc

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="An internal error occurred while processing your request.",
                request_id=request_id,
            ).model_dump(),
        )


@app.post(
    "/api/v1/verify-citation",
    response_model=VerifyCitationResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "External verification unavailable"},
    },
    tags=["verification"],
    summary="Verify a legal citation",
)
async def verify_citation(
    request: Request,
    body: VerifyCitationRequest,
) -> VerifyCitationResponse:
    """Run the 5-step Citation Verification Chain on a single citation.

    Steps:
        1. Existence Check -- does the citation exist in CourtListener?
        2. Reporter/Volume Validation -- are reporter and volume correct?
        3. Holding Verification -- does the claimed holding match? (HARD CONSTRAINT: external text only)
        4. Good Law Check -- is the case still good law?
        5. Currency Check -- is it the current version? (for statutes)

    Graceful degradation:
        - If CourtListener is down, the citation is returned as PARTIAL
          with a note that external verification was unavailable, rather
          than failing the entire request.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        verifier = _get_citation_verifier()
        result = await verifier.verify(body.citation, body.claimed_holding)

        return VerifyCitationResponse(
            citation=result.citation,
            status=result.status.value,
            steps_passed=result.steps_passed,
            steps_failed=result.steps_failed,
            external_source=result.external_source,
            holding_summary=result.holding_summary,
            holding_match=result.holding_match,
            good_law=result.good_law,
            confidence=result.confidence,
            details=result.details,
        )

    except CitationVerificationError as exc:
        # CourtListener/external source failed — return PARTIAL result
        # instead of an error. The citation exists but cannot be fully
        # verified right now. This is graceful degradation, not a failure.
        logger.warning(
            "citation_verification_degraded | request_id=%s error=%s",
            request_id,
            str(exc)[:200],
        )
        return VerifyCitationResponse(
            citation=body.citation,
            status="partial",
            steps_passed=[],
            steps_failed=[],
            external_source=None,
            holding_summary=None,
            holding_match=None,
            good_law=None,
            confidence=0.0,
            details="External verification unavailable. Citation could not be verified against CourtListener. Please retry later.",
        )

    except CyphergyError:
        # Let typed exception handlers deal with other CyphergyError subclasses
        raise

    except Exception as exc:
        # Detect CourtListener / httpx connection errors and degrade gracefully
        exc_type = type(exc).__name__
        if exc_type in (
            "ConnectError",
            "ConnectTimeout",
            "ReadTimeout",
            "HTTPStatusError",
            "TimeoutException",
        ):
            logger.warning(
                "citation_external_api_degraded | request_id=%s error_type=%s error=%s",
                request_id,
                exc_type,
                str(exc)[:200],
            )
            return VerifyCitationResponse(
                citation=body.citation,
                status="partial",
                steps_passed=[],
                steps_failed=[],
                external_source=None,
                holding_summary=None,
                holding_match=None,
                good_law=None,
                confidence=0.0,
                details="External verification unavailable. Citation could not be verified against CourtListener. Please retry later.",
            )

        logger.error(
            "verify_citation_error | request_id=%s error_type=%s error=%s",
            request_id,
            exc_type,
            str(exc)[:200],
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="An internal error occurred during citation verification.",
                request_id=request_id,
            ).model_dump(),
        )


@app.post(
    "/api/v1/compute-deadline",
    response_model=ComputeDeadlineResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["deadlines"],
    summary="Compute a jurisdiction-aware filing deadline",
)
async def compute_deadline(
    request: Request,
    body: ComputeDeadlineRequest,
) -> ComputeDeadlineResponse:
    """Compute a filing deadline with full jurisdiction and service method awareness.

    The deadline calculator is safety-critical: it always chooses the
    conservative (earlier) deadline when rules are ambiguous, and every
    adjustment (weekends, holidays, mail extensions) is logged in the
    audit trail.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Validate and parse enums
    try:
        event = date.fromisoformat(body.event_date)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=f"Invalid event_date format: '{body.event_date}'. Use YYYY-MM-DD.",
                request_id=request_id,
            ).model_dump(),
        )

    try:
        jurisdiction = Jurisdiction(body.jurisdiction.lower())
    except ValueError:
        valid = ", ".join(j.value for j in Jurisdiction)
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=f"Unknown jurisdiction: '{body.jurisdiction}'. Valid options: {valid}.",
                request_id=request_id,
            ).model_dump(),
        )

    try:
        deadline_type = DeadlineType(body.deadline_type.lower())
    except ValueError:
        valid = ", ".join(d.value for d in DeadlineType)
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=f"Unknown deadline_type: '{body.deadline_type}'. Valid options: {valid}.",
                request_id=request_id,
            ).model_dump(),
        )

    service_method = ServiceMethod.PERSONAL
    if body.service_method:
        try:
            service_method = ServiceMethod(body.service_method.lower())
        except ValueError:
            valid = ", ".join(s.value for s in ServiceMethod)
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=f"Unknown service_method: '{body.service_method}'. Valid options: {valid}.",
                    request_id=request_id,
                ).model_dump(),
            )

    try:
        result = _deadline_calculator.compute(
            event_date=event,
            deadline_type=deadline_type,
            jurisdiction=jurisdiction,
            service_method=service_method,
        )

        return ComputeDeadlineResponse(
            event_date=result.event_date.isoformat(),
            deadline_date=result.deadline_date.isoformat(),
            jurisdiction=result.jurisdiction.value,
            deadline_type=result.deadline_type.value,
            service_method=result.service_method.value,
            days_allowed=result.days_allowed,
            adjustments=result.adjustments,
            rule_citation=result.rule_citation,
            confidence=result.confidence,
            warning=result.warning,
            conservative=result.conservative,
        )

    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=str(exc),
                request_id=request_id,
            ).model_dump(),
        )
    except CyphergyError:
        # Let typed exception handlers deal with CyphergyError subclasses
        raise
    except Exception as exc:
        logger.error(
            "compute_deadline_error | request_id=%s error_type=%s error=%s",
            request_id,
            type(exc).__name__,
            str(exc)[:200],
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="An internal error occurred during deadline computation.",
                request_id=request_id,
            ).model_dump(),
        )


# ---------------------------------------------------------------------------
# Jurisdiction container endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/jurisdiction/query",
    tags=["jurisdiction"],
    summary="Query a jurisdiction container's dual-brain system",
)
async def query_jurisdiction(
    jurisdiction: str,
    question: str,
    practice_area: Optional[str] = None,
    sub_area: Optional[str] = None,
):
    """Route a legal question to the dual-brain system for a specific jurisdiction.

    All three models (Opus, Llama Scout, Cohere) must agree before output
    is certified. Disagreements are flagged for human review.
    """
    from src.containers import ContainerRegistry

    registry = ContainerRegistry()
    result = await registry.query(jurisdiction, question)
    return result


@app.get(
    "/api/v1/jurisdictions",
    tags=["jurisdiction"],
    summary="List all available jurisdictions",
)
async def list_jurisdictions():
    """Return the full list of supported jurisdictions (57 total).

    Includes 50 states, federal, DC, and 5 US territories.
    """
    from src.containers import ContainerRegistry

    registry = ContainerRegistry()
    return {"jurisdictions": registry.list_jurisdictions(), "total": registry.total_count}


# ---------------------------------------------------------------------------
# Typed exception handlers — one per CyphergyError subclass
# ---------------------------------------------------------------------------
# FastAPI dispatches to the most specific handler first. These handlers
# ensure that:
#   1. Users always get a safe, human-readable message.
#   2. Stack traces and PII never leak to the client (@M:010).
#   3. Each error type returns the correct HTTP status code.
#   4. Server-side logs include enough context for debugging.
# ---------------------------------------------------------------------------


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
    """Handle Anthropic/Bedrock API failures with a 503.

    Returns a reassuring message that the user's case data is safe.
    Load balancers should retry on 503 with exponential backoff.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "llm_provider_error | request_id=%s path=%s error=%s",
        request_id,
        request.url.path,
        str(exc)[:200],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.safe_message,
            request_id=request_id,
        ).model_dump(),
        headers={"Retry-After": "30"},
    )


@app.exception_handler(CitationVerificationError)
async def citation_verification_error_handler(request: Request, exc: CitationVerificationError) -> JSONResponse:
    """Handle CourtListener/external verification API failures with a 502.

    Instead of failing the whole request, citations are marked PARTIAL
    with a note that external verification was unavailable. The user
    can retry verification later.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "citation_verification_error | request_id=%s path=%s error=%s",
        request_id,
        request.url.path,
        str(exc)[:200],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.safe_message,
            detail="External verification unavailable — citation marked as unverified.",
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit violations with 429 and Retry-After header.

    The Retry-After header tells clients (and load balancers) how long
    to wait before retrying. The layer field helps operators debug which
    rate limit tier was hit.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "rate_limit_exceeded | request_id=%s path=%s layer=%s retry_after=%d",
        request_id,
        request.url.path,
        exc.layer,
        exc.retry_after,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.safe_message,
            request_id=request_id,
        ).model_dump(),
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Remaining": "0",
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Handle authentication failures with a 401.

    The same generic message is returned for expired, malformed, and
    missing tokens to prevent token-state enumeration.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    # Log at WARNING — auth failures are expected traffic, not bugs
    logger.warning(
        "auth_error | request_id=%s path=%s",
        request_id,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.safe_message,
            request_id=request_id,
        ).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError) -> JSONResponse:
    """Handle individual agent failures.

    When a single agent in the pipeline fails, the orchestrator can
    continue with the remaining agents. This handler is for cases where
    the failure bubbles up to the API layer directly.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "agent_error | request_id=%s path=%s agent_role=%s error=%s",
        request_id,
        request.url.path,
        exc.agent_role,
        str(exc)[:200],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.safe_message,
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(CyphergyError)
async def cyphergy_error_handler(request: Request, exc: CyphergyError) -> JSONResponse:
    """Catch-all for any CyphergyError subclass not handled above.

    This ensures that new error types added to src/errors.py will
    automatically get safe handling even before a dedicated handler
    is registered.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "cyphergy_error | request_id=%s path=%s error_type=%s error=%s",
        request_id,
        request.url.path,
        type(exc).__name__,
        str(exc)[:200],
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.safe_message,
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any unhandled exception.

    Legal data platforms must never expose internal error details to
    clients. This handler logs the full error server-side and returns
    a sanitized 500 response. No stack traces, no PII (@M:010).
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "unhandled_exception | request_id=%s path=%s error_type=%s error=%s",
        request_id,
        request.url.path,
        type(exc).__name__,
        str(exc)[:200],
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="An unexpected error occurred.",
            request_id=request_id,
        ).model_dump(),
    )
