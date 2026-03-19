"""
Ciphergy Pipeline — Connector Framework

Provides a pluggable connector architecture for integrating external services
into the Ciphergy cascade pipeline. All connectors extend BaseConnector and
register themselves via the ConnectorRegistry.

Usage:
    from ciphergy.connectors import ConnectorRegistry, get_connector

    registry = ConnectorRegistry()
    registry.auto_discover()

    asana = registry.get("asana", config={"api_key": "..."})
    asana.connect()
    data = asana.fetch("project tasks")
"""

from ciphergy.connectors.base import BaseConnector, ConnectorConfig
from ciphergy.connectors.registry import ConnectorRegistry

# Module-level singleton registry
_registry: ConnectorRegistry | None = None


def get_registry() -> ConnectorRegistry:
    """Get or create the global connector registry."""
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
        _registry.auto_discover()
    return _registry


def get_connector(name: str, **config_kwargs) -> BaseConnector:
    """
    Convenience function to get a configured connector instance.

    Args:
        name: Registered connector name (e.g., "asana", "github", "aws").
        **config_kwargs: Configuration overrides passed to ConnectorConfig.

    Returns:
        A configured BaseConnector instance.
    """
    registry = get_registry()
    return registry.get(name, **config_kwargs)


def list_connectors() -> list[str]:
    """List all available connector names."""
    registry = get_registry()
    return registry.list_available()


__all__ = [
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorRegistry",
    "get_registry",
    "get_connector",
    "list_connectors",
]
