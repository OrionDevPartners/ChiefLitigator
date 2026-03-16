"""
Model router for Ciphergy Pipeline.

Selects the optimal Bedrock model based on task type, with configurable
preferences and automatic fallback chains.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ciphergy.models.bedrock import SUPPORTED_MODELS, BedrockClient, BedrockResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task types
# ---------------------------------------------------------------------------


class TaskType(str, Enum):
    """Supported task classifications for model routing."""

    EXECUTION = "execution"
    STRATEGY = "strategy"
    RESEARCH = "research"
    REVIEW = "review"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Default routing table
# ---------------------------------------------------------------------------

DEFAULT_ROUTING: Dict[TaskType, str] = {
    TaskType.EXECUTION: "claude-sonnet-4-6",
    TaskType.STRATEGY: "claude-opus-4-6",
    TaskType.RESEARCH: "claude-sonnet-4-6",
    TaskType.REVIEW: "claude-opus-4-6",
    TaskType.GENERAL: "claude-sonnet-4-6",
}


# ---------------------------------------------------------------------------
# Model preference
# ---------------------------------------------------------------------------


@dataclass
class ModelPreference:
    """Routing preference for a single task type."""

    preferred: str
    fallback: str
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class RouterConfig:
    """Full router configuration, loadable from ciphergy.yaml."""

    preferences: Dict[TaskType, ModelPreference] = field(default_factory=dict)
    auto_upgrade: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouterConfig":
        """Build RouterConfig from a parsed YAML dict.

        Expected structure under ``model_router``::

            model_router:
              auto_upgrade: true
              preferences:
                execution:
                  preferred: claude-sonnet-4-6
                  fallback: claude-opus-4-6
                  max_tokens: 4096
                  temperature: 0.7
        """
        prefs: Dict[TaskType, ModelPreference] = {}
        router_section = data.get("model_router", data)

        for key, val in router_section.get("preferences", {}).items():
            try:
                task = TaskType(key)
            except ValueError:
                logger.warning("Unknown task type '%s' in config, skipping", key)
                continue
            prefs[task] = ModelPreference(
                preferred=val.get("preferred", DEFAULT_ROUTING.get(task, "claude-sonnet-4-6")),
                fallback=val.get("fallback", "claude-sonnet-4-6"),
                max_tokens=val.get("max_tokens", 4096),
                temperature=val.get("temperature", 0.7),
            )

        return cls(
            preferences=prefs,
            auto_upgrade=router_section.get("auto_upgrade", True),
        )

    @classmethod
    def defaults(cls) -> "RouterConfig":
        """Return a RouterConfig with sensible defaults for all task types."""
        prefs: Dict[TaskType, ModelPreference] = {}
        for task, model_key in DEFAULT_ROUTING.items():
            alt = "claude-opus-4-6" if model_key == "claude-sonnet-4-6" else "claude-sonnet-4-6"
            prefs[task] = ModelPreference(preferred=model_key, fallback=alt)
        return cls(preferences=prefs, auto_upgrade=True)


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------


class ModelRouter:
    """Routes tasks to the optimal Bedrock model.

    Parameters
    ----------
    client : BedrockClient
        Shared Bedrock client instance.
    config : RouterConfig, optional
        Routing configuration.  Defaults to ``RouterConfig.defaults()``.
    """

    def __init__(
        self,
        client: BedrockClient,
        config: Optional[RouterConfig] = None,
    ) -> None:
        self._client = client
        self._config = config or RouterConfig.defaults()
        self._available_cache: Optional[List[str]] = None
        logger.info(
            "ModelRouter initialized: auto_upgrade=%s, tasks=%s",
            self._config.auto_upgrade,
            list(self._config.preferences.keys()),
        )

    # ------------------------------------------------------------------
    # Model availability
    # ------------------------------------------------------------------

    def _refresh_available(self) -> List[str]:
        """Refresh the list of Anthropic model IDs on Bedrock."""
        try:
            models = self._client.get_available_models()
            self._available_cache = [m["modelId"] for m in models]
        except Exception:
            logger.warning("Could not refresh model list; using static catalog")
            self._available_cache = [v["model_id"] for v in SUPPORTED_MODELS.values()]
        return self._available_cache

    def _is_available(self, model_key: str) -> bool:
        """Check whether a model key maps to an available Bedrock model."""
        if model_key not in SUPPORTED_MODELS:
            return False
        if self._available_cache is None:
            self._refresh_available()
        model_id = SUPPORTED_MODELS[model_key]["model_id"]
        # Also accept inference profile prefix matches
        return any(
            model_id in avail or avail.startswith(model_id.split("-2025")[0])
            for avail in (self._available_cache or [])
        )

    def _check_for_upgrades(self, model_key: str) -> str:
        """If auto_upgrade is on, check for a newer version of the model.

        Returns the (potentially upgraded) model key.
        """
        if not self._config.auto_upgrade:
            return model_key

        if self._available_cache is None:
            self._refresh_available()

        # Look for any model in the catalog with higher version for the same family
        current = SUPPORTED_MODELS.get(model_key)
        if not current:
            return model_key

        family = "sonnet" if "sonnet" in model_key else "opus"
        candidates = [
            k for k, v in SUPPORTED_MODELS.items()
            if family in k and v["priority"] <= current["priority"]
        ]
        if candidates:
            best = sorted(candidates, key=lambda k: SUPPORTED_MODELS[k]["priority"])[0]
            if best != model_key:
                logger.info("Auto-upgrade: %s -> %s", model_key, best)
                return best

        return model_key

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def select_model(self, task_type: TaskType) -> str:
        """Select the best model key for the given task type.

        Follows the fallback chain: preferred -> alternate -> error.

        Returns
        -------
        str
            A key into ``SUPPORTED_MODELS``.

        Raises
        ------
        RuntimeError
            If no model is available for the task.
        """
        pref = self._config.preferences.get(task_type)
        if pref is None:
            pref = ModelPreference(
                preferred=DEFAULT_ROUTING.get(task_type, "claude-sonnet-4-6"),
                fallback="claude-opus-4-6",
            )

        # Check upgrade
        preferred = self._check_for_upgrades(pref.preferred)

        if self._is_available(preferred):
            logger.debug("Routing %s -> %s (preferred)", task_type.value, preferred)
            return preferred

        fallback = pref.fallback
        if self._is_available(fallback):
            logger.warning("Preferred model %s unavailable, falling back to %s", preferred, fallback)
            return fallback

        raise RuntimeError(
            f"No available model for task '{task_type.value}'. "
            f"Tried: {preferred}, {fallback}"
        )

    def get_preference(self, task_type: TaskType) -> ModelPreference:
        """Return the ModelPreference for a task type."""
        return self._config.preferences.get(
            task_type,
            ModelPreference(
                preferred=DEFAULT_ROUTING.get(task_type, "claude-sonnet-4-6"),
                fallback="claude-opus-4-6",
            ),
        )

    # ------------------------------------------------------------------
    # Convenience invoke
    # ------------------------------------------------------------------

    def invoke(
        self,
        task_type: TaskType,
        messages: List[Dict[str, Any]],
        *,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> BedrockResponse:
        """Route and invoke in one call.

        Selects the model for ``task_type`` and delegates to
        ``BedrockClient.invoke_model``.
        """
        model_key = self.select_model(task_type)
        pref = self.get_preference(task_type)
        return self._client.invoke_model(
            messages,
            model=model_key,
            system=system,
            max_tokens=max_tokens or pref.max_tokens,
            temperature=temperature if temperature is not None else pref.temperature,
        )

    def invoke_with_tools(
        self,
        task_type: TaskType,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> BedrockResponse:
        """Route and invoke with tools in one call."""
        model_key = self.select_model(task_type)
        pref = self.get_preference(task_type)
        return self._client.invoke_with_tools(
            messages,
            tools,
            model=model_key,
            system=system,
            max_tokens=max_tokens or pref.max_tokens,
        )
