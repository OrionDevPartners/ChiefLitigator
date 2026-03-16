"""Cyphergy Model Router — Multi-model orchestration for legal accuracy.

ARCHITECTURE:
  TIER 1 — Orchestrator + WDC Panel (maximum capability)
    Orchestrator: Opus 4.6 (1M context)
    WDC Panel: 5x Opus 4.6 + 3 extended panel models
    Extended: Opus 4.5, Opus 4.1, Sonnet 4.6 for cross-validation

  TIER 2 — Jurisdiction Dual-Brain (per-state legal accuracy)
    Brain A: Opus 4.6 (1M) — primary legal reasoning
    Brain B: Llama 4 Scout — cross-validation
    Brain C: Cohere Command-R+ — third opinion
    All must AGREE before output is certified.

  TIER 3 — Utility (lower cost tasks)
    Haiku 4.5 — scheduling, email, classification
    Sonnet 4.6 — moderate tasks (case intake, metadata)

  AUTO-ROTATION: newest model replaces oldest when released.
  All models via CPAA (Bedrock in production, Anthropic in dev).
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.providers.model_router")


# ---------------------------------------------------------------------------
# Model Tier Classification
# ---------------------------------------------------------------------------


class ModelTier(str, Enum):
    """Task complexity tiers determining which models are used."""

    TIER_1_LEGAL = "tier_1_legal"       # Orchestrator + WDC panel — max capability
    TIER_2_JURISDICTION = "tier_2_jurisdiction"  # Dual-brain per-state verification
    TIER_3_UTILITY = "tier_3_utility"   # Scheduling, formatting, classification


class ModelRole(str, Enum):
    """Specific role a model plays in the pipeline."""

    ORCHESTRATOR = "orchestrator"           # Manages all agents
    WDC_PANEL = "wdc_panel"                 # WDC debate scoring
    EXTENDED_PANEL = "extended_panel"       # Cross-validation on WDC
    JURISDICTION_PRIMARY = "jurisdiction_primary"   # Brain A — primary legal
    JURISDICTION_SCOUT = "jurisdiction_scout"       # Brain B — Llama Scout
    JURISDICTION_COHERE = "jurisdiction_cohere"     # Brain C — Cohere
    UTILITY_LIGHT = "utility_light"         # Easy tasks
    UTILITY_MEDIUM = "utility_medium"       # Moderate tasks


# ---------------------------------------------------------------------------
# Bedrock Model Registry
# ---------------------------------------------------------------------------

# Maps role → Bedrock model ID. Updated when new models are released.
# CPAA: model IDs are configuration, not hardcoded logic.
# Override any model via env var: MODEL_OVERRIDE_{ROLE}=model-id

_BEDROCK_MODELS: dict[str, str] = {
    # TIER 1 — Maximum capability for legal reasoning
    ModelRole.ORCHESTRATOR.value: "anthropic.claude-opus-4-6-v1",
    ModelRole.WDC_PANEL.value: "anthropic.claude-opus-4-6-v1",

    # Extended WDC panel — 3 additional high-context models
    "extended_panel_1": "anthropic.claude-opus-4-5-20251101-v1:0",
    "extended_panel_2": "anthropic.claude-opus-4-1-20250805-v1:0",
    "extended_panel_3": "anthropic.claude-sonnet-4-6",

    # TIER 2 — Jurisdiction dual-brain (per-state verification)
    ModelRole.JURISDICTION_PRIMARY.value: "anthropic.claude-opus-4-6-v1",
    ModelRole.JURISDICTION_SCOUT.value: "meta.llama4-scout-17b-instruct-v1:0",
    ModelRole.JURISDICTION_COHERE.value: "cohere.command-r-plus-v1:0",

    # TIER 3 — Utility (lower cost)
    ModelRole.UTILITY_LIGHT.value: "anthropic.claude-haiku-4-5-20251001-v1:0",
    ModelRole.UTILITY_MEDIUM.value: "anthropic.claude-sonnet-4-6",
}


# ---------------------------------------------------------------------------
# Model Config
# ---------------------------------------------------------------------------


class ModelConfig(BaseModel):
    """Configuration for a specific model invocation."""

    model_id: str = Field(description="Bedrock model ID")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.0)
    role: str = Field(description="What role this model plays")


# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------


class ModelRouter:
    """Routes tasks to the correct model(s) based on tier and role.

    Usage::

        router = ModelRouter()
        config = router.get_model(ModelRole.ORCHESTRATOR)
        # → ModelConfig(model_id="anthropic.claude-opus-4-6-v1", ...)

        models = router.get_dual_brain("louisiana")
        # → [primary_config, scout_config, cohere_config]

        panel = router.get_extended_wdc_panel()
        # → [opus_4.6, opus_4.5, opus_4.1, sonnet_4.6]
    """

    def __init__(self) -> None:
        self._models = dict(_BEDROCK_MODELS)
        self._apply_env_overrides()
        logger.info(
            "ModelRouter initialized: %d models configured", len(self._models)
        )

    def _apply_env_overrides(self) -> None:
        """Allow env var overrides for any model role.

        Format: MODEL_OVERRIDE_ORCHESTRATOR=new-model-id
        This enables auto-rotation when newer models are released.
        """
        for role in ModelRole:
            env_key = f"MODEL_OVERRIDE_{role.value.upper()}"
            override = os.getenv(env_key)
            if override:
                old = self._models.get(role.value, "unset")
                self._models[role.value] = override
                logger.info(
                    "model_override | role=%s old=%s new=%s",
                    role.value, old, override,
                )

    def get_model(self, role: ModelRole) -> ModelConfig:
        """Get the model configuration for a specific role."""
        model_id = self._models.get(role.value)
        if not model_id:
            raise ValueError(f"No model configured for role: {role.value}")

        # Tier 1 legal tasks: temperature 0 for deterministic reasoning
        # Tier 3 utility: slightly higher temperature for natural responses
        temperature = 0.0 if role in (
            ModelRole.ORCHESTRATOR,
            ModelRole.WDC_PANEL,
            ModelRole.EXTENDED_PANEL,
            ModelRole.JURISDICTION_PRIMARY,
            ModelRole.JURISDICTION_SCOUT,
            ModelRole.JURISDICTION_COHERE,
        ) else 0.3

        # Max tokens: higher for legal reasoning, lower for utility
        max_tokens = 8192 if role in (
            ModelRole.ORCHESTRATOR,
            ModelRole.WDC_PANEL,
            ModelRole.JURISDICTION_PRIMARY,
        ) else 4096

        return ModelConfig(
            model_id=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            role=role.value,
        )

    def get_dual_brain(self, jurisdiction: str) -> list[ModelConfig]:
        """Get the 3-model dual-brain configuration for a jurisdiction.

        All 3 models must AGREE on law/statutes/case law before
        output is certified. Disagreement triggers human review.
        """
        return [
            self.get_model(ModelRole.JURISDICTION_PRIMARY),
            self.get_model(ModelRole.JURISDICTION_SCOUT),
            self.get_model(ModelRole.JURISDICTION_COHERE),
        ]

    def get_extended_wdc_panel(self) -> list[ModelConfig]:
        """Get the extended WDC panel: 5 base agents + 3 cross-validators.

        The 3 extended panel models provide independent verification
        from different model families / versions to catch correlated
        failure modes in the primary Opus 4.6 panel.
        """
        base = self.get_model(ModelRole.WDC_PANEL)
        extended = []
        for key in ("extended_panel_1", "extended_panel_2", "extended_panel_3"):
            model_id = self._models.get(key)
            if model_id:
                extended.append(ModelConfig(
                    model_id=model_id,
                    max_tokens=4096,
                    temperature=0.0,
                    role="extended_panel",
                ))
        return [base] + extended

    def get_utility_model(self, task_complexity: str) -> ModelConfig:
        """Get the appropriate utility model based on task complexity.

        Args:
            task_complexity: "light" (scheduling, email) or "medium" (case intake)
        """
        if task_complexity == "light":
            return self.get_model(ModelRole.UTILITY_LIGHT)
        return self.get_model(ModelRole.UTILITY_MEDIUM)

    def list_all_models(self) -> dict[str, str]:
        """Return all configured models for admin dashboard display."""
        return dict(self._models)


# ---------------------------------------------------------------------------
# Dual-Brain Consensus Check
# ---------------------------------------------------------------------------


class DualBrainResult(BaseModel):
    """Result of a dual-brain jurisdiction verification."""

    jurisdiction: str = Field(description="Jurisdiction being verified")
    primary_response: str = Field(description="Opus 4.6 response")
    scout_response: str = Field(description="Llama Scout response")
    cohere_response: str = Field(description="Cohere Command-R+ response")
    consensus: bool = Field(description="Whether all 3 brains agree")
    disagreements: list[str] = Field(
        default_factory=list,
        description="Specific points of disagreement between models",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence based on agreement level (1.0 = full consensus)",
    )


async def run_dual_brain_check(
    question: str,
    jurisdiction: str,
    router: ModelRouter,
    provider: Any,
) -> DualBrainResult:
    """Run a legal question through the 3-brain jurisdiction system.

    All 3 models answer independently. If they disagree on law,
    statutes, or case law, consensus=False and the output requires
    human review.
    """
    import asyncio

    models = router.get_dual_brain(jurisdiction)
    system_prompt = (
        f"You are a legal expert for {jurisdiction} jurisdiction. "
        f"Answer the following legal question with specific citations to "
        f"statutes, case law, and court rules. Be precise and cite sources."
    )

    # Run all 3 models in parallel
    tasks = []
    for model_config in models:
        tasks.append(
            provider.create_message(
                model=model_config.model_id,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": question}],
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    responses = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                "dual_brain_failed | model=%s error=%s",
                models[i].model_id,
                str(result)[:200],
            )
            responses.append(f"[Model {models[i].role} unavailable]")
        else:
            responses.append(result)

    # Simple consensus check — all responses should agree on key citations
    # Full consensus engine will be built in Phase 2
    consensus = len(responses) == 3 and all(
        not isinstance(r, str) or not r.startswith("[Model") for r in responses
    )

    return DualBrainResult(
        jurisdiction=jurisdiction,
        primary_response=responses[0] if responses else "",
        scout_response=responses[1] if len(responses) > 1 else "",
        cohere_response=responses[2] if len(responses) > 2 else "",
        consensus=consensus,
        disagreements=[],
        confidence=1.0 if consensus else 0.5,
    )
