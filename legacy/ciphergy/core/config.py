"""
Configuration manager for Ciphergy Pipeline.

Loads settings from ``ciphergy.yaml``, with environment variable overrides
for any key prefixed with ``CIPHERGY_`` or ``AWS_``.  Implements a
thread-safe singleton so all modules share one config instance.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import PyYAML; fall back to a stub if not installed
try:
    import yaml  # type: ignore[import-untyped]

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False
    logger.debug("PyYAML not installed; config will rely on env vars and defaults")


# ---------------------------------------------------------------------------
# Typed config sections
# ---------------------------------------------------------------------------


@dataclass
class AWSConfig:
    """AWS-specific settings."""

    region: str = "us-east-1"
    profile: Optional[str] = None
    account_id: Optional[str] = None


@dataclass
class BedrockConfig:
    """Bedrock invocation defaults."""

    preferred_model: str = "claude-sonnet-4-6"
    max_retries: int = 5
    default_max_tokens: int = 4096
    default_temperature: float = 0.7


@dataclass
class AgentConfig:
    """Agent orchestration defaults."""

    max_parallel: int = 20
    default_timeout: int = 300  # seconds
    agent_types: List[str] = field(default_factory=lambda: ["general", "research", "execution", "review", "red_team"])


@dataclass
class ModelRouterSection:
    """Raw model-router preferences, passed to ``RouterConfig.from_dict``."""

    auto_upgrade: bool = True
    preferences: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CiphergyConfig (singleton)
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()
_INSTANCE: Optional["CiphergyConfig"] = None


class CiphergyConfig:
    """Central configuration for the Ciphergy Pipeline.

    Usage::

        cfg = CiphergyConfig.get()          # singleton
        print(cfg.aws.region)
        print(cfg.bedrock.preferred_model)

    Config is loaded once from:
      1. ``ciphergy.yaml`` (searched upward from cwd, or via CIPHERGY_CONFIG env var)
      2. Environment variable overrides: ``CIPHERGY_AWS_REGION``, ``AWS_DEFAULT_REGION``, etc.
    """

    def __init__(self, config_path: Optional[str] = None, _raw: Optional[Dict[str, Any]] = None) -> None:
        self._raw: Dict[str, Any] = _raw or {}
        self._config_path: Optional[Path] = None

        if _raw is None:
            self._config_path = self._find_config(config_path)
            if self._config_path:
                self._raw = self._load_yaml(self._config_path)
                logger.info("Config loaded from %s", self._config_path)
            else:
                logger.info("No ciphergy.yaml found; using defaults + env vars")

        self._apply_env_overrides()

        # Build typed sections
        self.aws = self._build_aws()
        self.bedrock = self._build_bedrock()
        self.agents = self._build_agents()
        self.model_router = self._build_model_router()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get(cls, config_path: Optional[str] = None, force_reload: bool = False) -> "CiphergyConfig":
        """Return the singleton CiphergyConfig instance.

        Parameters
        ----------
        config_path : str, optional
            Explicit path to ``ciphergy.yaml``.
        force_reload : bool
            If True, discard any cached instance and reload.
        """
        global _INSTANCE
        with _LOCK:
            if _INSTANCE is None or force_reload:
                _INSTANCE = cls(config_path=config_path)
            return _INSTANCE

    @classmethod
    def reset(cls) -> None:
        """Clear the singleton (mainly for tests)."""
        global _INSTANCE
        with _LOCK:
            _INSTANCE = None

    # ------------------------------------------------------------------
    # YAML discovery + loading
    # ------------------------------------------------------------------

    @staticmethod
    def _find_config(explicit: Optional[str] = None) -> Optional[Path]:
        """Locate ``ciphergy.yaml``.

        Search order:
          1. Explicit path argument
          2. CIPHERGY_CONFIG environment variable
          3. Walk upward from cwd
        """
        if explicit:
            p = Path(explicit)
            if p.is_file():
                return p.resolve()

        env = os.environ.get("CIPHERGY_CONFIG")
        if env:
            p = Path(env)
            if p.is_file():
                return p.resolve()

        cwd = Path.cwd()
        for directory in [cwd, *cwd.parents]:
            candidate = directory / "ciphergy.yaml"
            if candidate.is_file():
                return candidate.resolve()
            candidate = directory / "ciphergy.yml"
            if candidate.is_file():
                return candidate.resolve()

        return None

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not _HAS_YAML:
            logger.warning("PyYAML not installed; cannot parse %s", path)
            return {}
        try:
            with open(path, "r") as fh:
                data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.error("Failed to parse %s: %s", path, exc)
            return {}

    # ------------------------------------------------------------------
    # Environment overrides
    # ------------------------------------------------------------------

    def _apply_env_overrides(self) -> None:
        """Override YAML values with CIPHERGY_* and AWS_* environment variables."""
        mapping = {
            "CIPHERGY_AWS_REGION": ("aws", "region"),
            "AWS_DEFAULT_REGION": ("aws", "region"),
            "AWS_REGION": ("aws", "region"),
            "AWS_PROFILE": ("aws", "profile"),
            "CIPHERGY_AWS_ACCOUNT_ID": ("aws", "account_id"),
            "CIPHERGY_PREFERRED_MODEL": ("bedrock", "preferred_model"),
            "CIPHERGY_MAX_RETRIES": ("bedrock", "max_retries"),
            "CIPHERGY_DEFAULT_MAX_TOKENS": ("bedrock", "default_max_tokens"),
            "CIPHERGY_DEFAULT_TEMPERATURE": ("bedrock", "default_temperature"),
            "CIPHERGY_MAX_PARALLEL_AGENTS": ("agents", "max_parallel"),
            "CIPHERGY_AGENT_TIMEOUT": ("agents", "default_timeout"),
        }
        for env_key, (section, key) in mapping.items():
            val = os.environ.get(env_key)
            if val is not None:
                self._raw.setdefault(section, {})[key] = val
                logger.debug("Env override: %s -> %s.%s = %s", env_key, section, key, val)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_aws(self) -> AWSConfig:
        s = self._raw.get("aws", {})
        return AWSConfig(
            region=str(s.get("region", "us-east-1")),
            profile=s.get("profile"),
            account_id=s.get("account_id"),
        )

    def _build_bedrock(self) -> BedrockConfig:
        s = self._raw.get("bedrock", {})
        return BedrockConfig(
            preferred_model=str(s.get("preferred_model", "claude-sonnet-4-6")),
            max_retries=int(s.get("max_retries", 5)),
            default_max_tokens=int(s.get("default_max_tokens", 4096)),
            default_temperature=float(s.get("default_temperature", 0.7)),
        )

    def _build_agents(self) -> AgentConfig:
        s = self._raw.get("agents", {})
        return AgentConfig(
            max_parallel=int(s.get("max_parallel", 20)),
            default_timeout=int(s.get("default_timeout", 300)),
            agent_types=s.get("agent_types", ["general", "research", "execution", "review", "red_team"]),
        )

    def _build_model_router(self) -> ModelRouterSection:
        s = self._raw.get("model_router", {})
        return ModelRouterSection(
            auto_upgrade=bool(s.get("auto_upgrade", True)),
            preferences=s.get("preferences", {}),
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def raw(self) -> Dict[str, Any]:
        """Return the raw parsed config dict."""
        return self._raw

    @property
    def config_path(self) -> Optional[Path]:
        """Return the path to the loaded config file, if any."""
        return self._config_path

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Retrieve a nested value from the raw config.

        Example::

            cfg.get_nested("bedrock", "preferred_model", default="claude-sonnet-4-6")
        """
        node: Any = self._raw
        for key in keys:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                return default
            if node is None:
                return default
        return node

    def validate(self) -> List[str]:
        """Validate the config and return a list of warnings (empty = OK)."""
        warnings: List[str] = []
        if not self.aws.region:
            warnings.append("aws.region is empty")
        if self.bedrock.max_retries < 0:
            warnings.append("bedrock.max_retries must be >= 0")
        if self.agents.max_parallel < 1:
            warnings.append("agents.max_parallel must be >= 1")
        if self.bedrock.default_temperature < 0.0 or self.bedrock.default_temperature > 1.0:
            warnings.append("bedrock.default_temperature should be between 0.0 and 1.0")
        return warnings
