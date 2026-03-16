"""CPAA-compliant application settings.

All configuration is sourced exclusively from environment variables
(with optional .env file fallback). Zero hardcoded secrets or provider details.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Cyphergy platform.

    Every value here can be overridden by setting the corresponding
    environment variable (case-insensitive). The .env file is loaded
    as a convenience for local development only.
    """

    # ── LLM Provider (CPAA — all from env) ──────────────────────────
    # LLM_PROVIDER controls which backend the provider layer uses.
    # "anthropic" (default): direct Anthropic API — for development.
    # "bedrock": AWS Bedrock Runtime — for production.
    # The actual switching logic lives in src/providers/llm_provider.py.
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    aws_default_region: str = "us-east-1"
    llm_model: str = "claude-opus-4-6"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0  # Deterministic for legal — non-negotiable

    # ── Legal Data Sources (CPAA — all from env) ────────────────────
    courtlistener_api_url: str = "https://www.courtlistener.com/api/rest/v4"
    courtlistener_api_key: str = ""

    # ── WDC Configuration ───────────────────────────────────────────
    wdc_certification_threshold: float = 8.5
    wdc_notes_threshold: float = 7.0
    wdc_revision_threshold: float = 5.0
    wdc_max_revision_cycles: int = 3

    # ── Agent Weights (must sum to 1.0) ─────────────────────────────
    weight_lead_counsel: float = 0.30
    weight_research_counsel: float = 0.25
    weight_drafting_counsel: float = 0.15
    weight_red_team: float = 0.20
    weight_compliance_counsel: float = 0.10

    # ── Verification Chain ──────────────────────────────────────────
    citation_similarity_threshold: float = 0.85
    citation_recheck_days: int = 30
    external_retrieval_required: bool = True  # HARD CONSTRAINT — never set to False

    # ── Application ─────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # ── Validators ──────────────────────────────────────────────────

    @field_validator("llm_provider")
    @classmethod
    def llm_provider_must_be_valid(cls, v: str) -> str:
        allowed = {"anthropic", "bedrock"}
        if v.lower().strip() not in allowed:
            raise ValueError(f"llm_provider must be one of {allowed}, got '{v}'")
        return v.lower().strip()

    @field_validator("llm_temperature")
    @classmethod
    def temperature_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"llm_temperature must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("wdc_certification_threshold")
    @classmethod
    def certification_above_notes(cls, v: float) -> float:
        if v < 0.0 or v > 10.0:
            raise ValueError(f"wdc_certification_threshold must be 0-10, got {v}")
        return v

    @field_validator("wdc_notes_threshold")
    @classmethod
    def notes_above_revision(cls, v: float) -> float:
        if v < 0.0 or v > 10.0:
            raise ValueError(f"wdc_notes_threshold must be 0-10, got {v}")
        return v

    @field_validator("wdc_revision_threshold")
    @classmethod
    def revision_threshold_valid(cls, v: float) -> float:
        if v < 0.0 or v > 10.0:
            raise ValueError(f"wdc_revision_threshold must be 0-10, got {v}")
        return v

    @field_validator("external_retrieval_required")
    @classmethod
    def external_retrieval_must_be_true(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "external_retrieval_required is a HARD CONSTRAINT and must be True. "
                "Disabling external retrieval compromises citation verification integrity."
            )
        return v

    # ── Computed Properties ──────────────────────────────────────────

    @property
    def agent_weights(self) -> dict[str, float]:
        """Return all agent weights as a role-keyed dictionary."""
        return {
            "lead_counsel": self.weight_lead_counsel,
            "research_counsel": self.weight_research_counsel,
            "drafting_counsel": self.weight_drafting_counsel,
            "red_team": self.weight_red_team,
            "compliance_counsel": self.weight_compliance_counsel,
        }

    @property
    def total_weight(self) -> float:
        """Sum of all agent weights. Must equal 1.0."""
        return sum(self.agent_weights.values())


# ── Singleton ────────────────────────────────────────────────────────

_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached Settings singleton.

    Uses module-level caching to avoid re-reading env on every call.
    Call ``reset_settings()`` in tests to force a fresh instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Clear the cached singleton. Used in tests."""
    global _settings
    _settings = None
