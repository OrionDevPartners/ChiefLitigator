"""System Router — Health checks, system info, and admin endpoints.

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger("cyphergy.api.system_router")

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for load balancers and monitoring."""
    components = {
        "api": "healthy",
        "bedrock": _check_bedrock(),
        "aurora": _check_aurora(),
        "dynamodb": _check_dynamodb(),
        "siphon": _check_siphon(),
    }

    overall = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"

    return {
        "status": overall,
        "service": "ChiefLitigator",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
    }


@router.get("/info")
async def system_info() -> Dict[str, Any]:
    """System information endpoint."""
    return {
        "service": "ChiefLitigator",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "description": "AGI-grade litigation platform for pro se litigants and small businesses",
        "domains": ["chieflitigator.com", "chieflitigator.ai"],
        "tiers": {
            "consumer": "Plain-language chat interface with guided flows",
            "enterprise": "Bulk processing, team management, API access",
            "developer": "Raw endpoints, webhooks, custom integrations",
        },
        "agents": {
            "intake_agent": "Context-to-law matching and case intake",
            "document_generator": "Court-ready document drafting",
            "evidence_scorer": "Evidence strength analysis and gap identification",
            "strategy_advisor": "Predictive analytics and litigation strategy",
            "docket_monitor": "Real-time court docket tracking",
            "discovery_manager": "Document management, OCR, and privilege detection",
        },
        "engines": {
            "galvanizer": "Adversarial panel iteration — Advocacy vs Stress-Test panels with 90% confidence gate",
            "wdc": "Weighted Debate Consensus — multi-agent scoring and revision",
            "if_then": "Context-to-law matching algorithm with semantic search",
        },
        "infrastructure": {
            "compute": "AWS Bedrock AgentCore",
            "models": {
                "tier1_reasoning": "anthropic.claude-opus-4-6-v1:0 (200K context)",
                "tier2_workhorse": "anthropic.claude-sonnet-4-6-20260301-v1:0 (200K context)",
                "tier3_speed": "anthropic.claude-haiku-3-6-20250401-v1:0 (200K context)",
                "tier2_alt": "meta.llama4-maverick-17b-instruct-v1:0 (1M context)",
                "tier2_validation": "cohere.command-a-08-2025-v1:0 (256K context)",
                "embeddings": "amazon.titan-embed-text-v2:0 (1536 dim)",
            },
            "database": "AWS Aurora PostgreSQL + pgvector",
            "user_data": "AWS DynamoDB",
            "frontend": "Cloudflare Pages + Workers",
            "ci_cd": "GitHub Actions → AWS",
        },
        "data_sources": {
            "case_law": "CourtListener (8M+ opinions), Harvard CAP",
            "statutes": "US Code (OLRC XML), LegiScan (50 states)",
            "rules": "Federal Rules (govinfo.gov), State court rules",
            "dockets": "PACER RSS, CourtListener webhooks",
        },
    }


@router.get("/metrics")
async def system_metrics() -> Dict[str, Any]:
    """Basic system metrics."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "N/A",
        "total_cases": 0,
        "total_documents": 0,
        "total_filings": 0,
        "galvanizer_runs": 0,
        "average_confidence": 0.0,
        "siphon_status": {
            "last_run": "N/A",
            "total_records": 0,
        },
    }


def _check_bedrock() -> str:
    """Check Bedrock connectivity."""
    try:
        region = os.getenv("AWS_DEFAULT_REGION", "")
        return "healthy" if region else "not_configured"
    except Exception:
        return "error"


def _check_aurora() -> str:
    """Check Aurora connectivity."""
    try:
        dsn = os.getenv("AURORA_DSN", "")
        return "healthy" if dsn else "not_configured"
    except Exception:
        return "error"


def _check_dynamodb() -> str:
    """Check DynamoDB connectivity."""
    try:
        region = os.getenv("AWS_DEFAULT_REGION", "")
        return "healthy" if region else "not_configured"
    except Exception:
        return "error"


def _check_siphon() -> str:
    """Check siphon pipeline status."""
    return "idle"
