"""
Ciphergy Pipeline — Connector Registry

Central registry for all available connectors. Supports manual registration,
auto-discovery from the connectors package, and use-case-based recommendations.
"""

import importlib
import inspect
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from ciphergy.connectors.base import BaseConnector, ConnectorConfig

logger = logging.getLogger(__name__)


@dataclass
class ConnectorCatalogEntry:
    """Metadata about a registered connector."""

    name: str
    connector_class: Type[BaseConnector]
    description: str = ""
    use_cases: List[str] = field(default_factory=list)
    required_credentials: List[str] = field(default_factory=list)
    setup_steps: List[str] = field(default_factory=list)


# ── Built-in connector catalog ──────────────────────────────────────

BUILTIN_CATALOG: Dict[str, Dict[str, Any]] = {
    "asana": {
        "description": "Asana project management — tasks, comments, webhooks, inter-agent messaging",
        "use_cases": ["legal", "startup_dd", "software", "medical", "project_management"],
        "required_credentials": ["ASANA_PAT"],
        "setup_steps": [
            "Create an Asana Personal Access Token at https://app.asana.com/0/developer-console",
            "Set ASANA_PAT environment variable",
            "Configure project GID in ciphergy.yaml under asana.project_gid",
        ],
    },
    "github": {
        "description": "GitHub repos, issues, PRs, Actions, file read/write, webhooks",
        "use_cases": ["software", "startup_dd", "legal", "open_source"],
        "required_credentials": ["GITHUB_TOKEN"],
        "setup_steps": [
            "Create a GitHub Personal Access Token with repo scope",
            "Set GITHUB_TOKEN environment variable",
            "Configure owner/repo in ciphergy.yaml under github section",
        ],
    },
    "aws": {
        "description": "AWS services — S3, DynamoDB, SES, CloudWatch, Bedrock delegation",
        "use_cases": ["software", "startup_dd", "legal", "medical", "infrastructure"],
        "required_credentials": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
        "setup_steps": [
            "Configure AWS credentials via environment or ~/.aws/credentials",
            "Set AWS_DEFAULT_REGION (default: us-east-1)",
            "Ensure IAM permissions for S3, DynamoDB, SES, CloudWatch, Bedrock",
        ],
    },
    "cloudflare": {
        "description": "Cloudflare Workers, Pages, DNS, KV storage, R2 object storage",
        "use_cases": ["software", "infrastructure", "deployment"],
        "required_credentials": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
        "setup_steps": [
            "Create API token at https://dash.cloudflare.com/profile/api-tokens",
            "Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID environment variables",
            "Configure zone_id in ciphergy.yaml under cloudflare section",
        ],
    },
}

# ── Use case to connector mappings ──────────────────────────────────

USE_CASE_MAP: Dict[str, List[str]] = {
    "legal": ["asana", "github", "aws"],
    "startup_dd": ["asana", "github", "aws"],
    "medical": ["asana", "aws"],
    "software": ["asana", "github", "aws", "cloudflare"],
    "infrastructure": ["aws", "cloudflare"],
    "deployment": ["aws", "cloudflare", "github"],
    "project_management": ["asana"],
    "open_source": ["github"],
}


class ConnectorRegistry:
    """
    Central registry for Ciphergy connectors.

    Manages connector class registration, instance creation,
    auto-discovery, and use-case-based recommendations.
    """

    def __init__(self) -> None:
        self._catalog: Dict[str, ConnectorCatalogEntry] = {}
        self._instances: Dict[str, BaseConnector] = {}

    def register(
        self,
        name: str,
        connector_class: Type[BaseConnector],
        description: str = "",
        use_cases: Optional[List[str]] = None,
        required_credentials: Optional[List[str]] = None,
        setup_steps: Optional[List[str]] = None,
    ) -> None:
        """
        Register a connector class with the registry.

        Args:
            name: Unique connector name (e.g., "asana").
            connector_class: The connector class (must subclass BaseConnector).
            description: Human-readable description.
            use_cases: List of use case tags this connector supports.
            required_credentials: Environment variable names needed.
            setup_steps: Setup instructions for the user.

        Raises:
            TypeError: If connector_class does not subclass BaseConnector.
        """
        if not (isinstance(connector_class, type) and issubclass(connector_class, BaseConnector)):
            raise TypeError(
                f"Connector class must subclass BaseConnector, got {connector_class}"
            )

        # Merge with built-in catalog metadata if available
        builtin = BUILTIN_CATALOG.get(name, {})

        entry = ConnectorCatalogEntry(
            name=name,
            connector_class=connector_class,
            description=description or builtin.get("description", ""),
            use_cases=use_cases or builtin.get("use_cases", []),
            required_credentials=required_credentials or builtin.get("required_credentials", []),
            setup_steps=setup_steps or builtin.get("setup_steps", []),
        )

        self._catalog[name] = entry
        logger.info("Registered connector: %s (%s)", name, connector_class.__name__)

    def get(self, name: str, **config_kwargs: Any) -> BaseConnector:
        """
        Get a connector instance by name.

        Creates a new instance if one doesn't exist or if config_kwargs
        are provided. Reuses cached instances otherwise.

        Args:
            name: Registered connector name.
            **config_kwargs: Overrides for ConnectorConfig fields.

        Returns:
            A configured BaseConnector instance.

        Raises:
            KeyError: If the connector name is not registered.
        """
        if name not in self._catalog:
            raise KeyError(
                f"Connector '{name}' not registered. "
                f"Available: {', '.join(self._catalog.keys())}"
            )

        if config_kwargs or name not in self._instances:
            entry = self._catalog[name]
            config = ConnectorConfig(name=name, **config_kwargs)
            instance = entry.connector_class(config)
            self._instances[name] = instance

        return self._instances[name]

    def list_available(self) -> List[str]:
        """
        List all registered connector names.

        Returns:
            Sorted list of connector names.
        """
        return sorted(self._catalog.keys())

    def get_catalog(self) -> Dict[str, ConnectorCatalogEntry]:
        """
        Get the full connector catalog.

        Returns:
            Dict mapping connector names to their catalog entries.
        """
        return dict(self._catalog)

    def get_info(self, name: str) -> Optional[ConnectorCatalogEntry]:
        """
        Get catalog info for a specific connector.

        Args:
            name: Connector name.

        Returns:
            ConnectorCatalogEntry or None if not found.
        """
        return self._catalog.get(name)

    def get_recommended(self, use_case: str) -> List[ConnectorCatalogEntry]:
        """
        Get recommended connectors for a given use case.

        Args:
            use_case: Use case identifier (e.g., "legal", "software").

        Returns:
            List of ConnectorCatalogEntry objects recommended for the use case,
            ordered by relevance. Falls back to all registered connectors
            whose use_cases list includes the query.
        """
        results: List[ConnectorCatalogEntry] = []

        # First check the static map
        mapped_names = USE_CASE_MAP.get(use_case.lower(), [])
        for name in mapped_names:
            if name in self._catalog:
                results.append(self._catalog[name])

        # Then check all registered connectors for matching use_cases
        for name, entry in self._catalog.items():
            if name not in mapped_names and use_case.lower() in [
                uc.lower() for uc in entry.use_cases
            ]:
                results.append(entry)

        if not results:
            # Return all connectors if no specific match
            logger.info(
                "No specific recommendations for use case '%s'. Returning all connectors.",
                use_case,
            )
            results = list(self._catalog.values())

        return results

    def auto_discover(self) -> int:
        """
        Auto-discover connector classes in the ciphergy.connectors package.

        Scans all modules in the connectors package for classes that
        subclass BaseConnector. Each discovered class is registered
        using its CONNECTOR_NAME class attribute or a name derived
        from the module name.

        Returns:
            Number of connectors discovered and registered.
        """
        import ciphergy.connectors as connectors_pkg

        discovered = 0
        package_path = connectors_pkg.__path__
        skip_modules = {"__init__", "base", "registry"}

        for importer, module_name, is_pkg in pkgutil.iter_modules(package_path):
            if module_name in skip_modules:
                continue

            try:
                module = importlib.import_module(f"ciphergy.connectors.{module_name}")
            except ImportError as exc:
                logger.warning("Failed to import connector module '%s': %s", module_name, exc)
                continue

            for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseConnector)
                    and obj is not BaseConnector
                    and obj.__module__ == module.__name__
                ):
                    # Use CONNECTOR_NAME class attribute or derive from module name
                    connector_name = getattr(
                        obj, "CONNECTOR_NAME", module_name.replace("_connector", "")
                    )
                    if connector_name not in self._catalog:
                        self.register(connector_name, obj)
                        discovered += 1

        logger.info("Auto-discovery complete: %d connector(s) found", discovered)
        return discovered

    def disconnect_all(self) -> None:
        """Disconnect all active connector instances."""
        for name, instance in self._instances.items():
            try:
                if instance.is_connected:
                    instance.disconnect()
                    logger.info("Disconnected: %s", name)
            except Exception as exc:
                logger.warning("Error disconnecting %s: %s", name, exc)
        self._instances.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._catalog

    def __len__(self) -> int:
        return len(self._catalog)

    def __repr__(self) -> str:
        return f"<ConnectorRegistry connectors={len(self._catalog)} active={len(self._instances)}>"
