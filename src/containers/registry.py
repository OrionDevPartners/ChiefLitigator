"""Container Registry — Manages all jurisdiction containers.

Novel architecture by Bo Pennington.

The registry is the orchestrator's map of all active jurisdiction containers.
It handles container lifecycle, inter-container routing, and context aggregation.

Architecture:
  Registry
  ├── Federal Container (FRCP, USC, CFR, federal case law)
  ├── Louisiana Container (La. CCP, La. CC, LA case law, bar rules)
  ├── California Container (CCP, CRC, CA case law, bar rules)
  ├── Texas Container (TRCP, TX case law, bar rules)
  ├── ... (50 states + territories)
  └── Cross-Jurisdiction Router (conflicts of law, federal preemption)

Each container is lazy-loaded on first query for that jurisdiction.
No container runs unless needed — Fargate serverless scaling.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.containers.jurisdiction import (
    JurisdictionConfig,
    JurisdictionContainer,
    JurisdictionType,
)

logger = logging.getLogger("cyphergy.containers.registry")


# ---------------------------------------------------------------------------
# Pre-configured Jurisdictions
# ---------------------------------------------------------------------------

_JURISDICTIONS: list[JurisdictionConfig] = [
    # Federal
    JurisdictionConfig(
        code="FED", name="Federal", type=JurisdictionType.FEDERAL,
        statute_source="uscode.house.gov",
        case_law_source="courtlistener",
        court_rules_source="uscourts.gov",
    ),
    # States (alphabetical — top 10 first, rest added as needed)
    JurisdictionConfig(
        code="CA", name="California", type=JurisdictionType.STATE,
        statute_source="leginfo.legislature.ca.gov",
        court_rules_source="courts.ca.gov",
    ),
    JurisdictionConfig(
        code="FL", name="Florida", type=JurisdictionType.STATE,
        statute_source="flsenate.gov",
        court_rules_source="flcourts.org",
    ),
    JurisdictionConfig(
        code="GA", name="Georgia", type=JurisdictionType.STATE,
    ),
    JurisdictionConfig(
        code="IL", name="Illinois", type=JurisdictionType.STATE,
    ),
    JurisdictionConfig(
        code="LA", name="Louisiana", type=JurisdictionType.STATE,
        statute_source="legis.la.gov",
        court_rules_source="lasc.org",
    ),
    JurisdictionConfig(
        code="NY", name="New York", type=JurisdictionType.STATE,
        statute_source="nysenate.gov",
        court_rules_source="nycourts.gov",
    ),
    JurisdictionConfig(
        code="OH", name="Ohio", type=JurisdictionType.STATE,
    ),
    JurisdictionConfig(
        code="PA", name="Pennsylvania", type=JurisdictionType.STATE,
    ),
    JurisdictionConfig(
        code="TX", name="Texas", type=JurisdictionType.STATE,
        statute_source="statutes.capitol.texas.gov",
        court_rules_source="txcourts.gov",
    ),
    JurisdictionConfig(
        code="VA", name="Virginia", type=JurisdictionType.STATE,
    ),
]


# ---------------------------------------------------------------------------
# Container Registry
# ---------------------------------------------------------------------------


class ContainerRegistry:
    """Manages all jurisdiction containers with lazy loading.

    Containers are created on first access and cached for the
    lifetime of the process. In production (ECS Fargate), each
    container could be its own ECS task for true isolation.

    Usage::

        registry = ContainerRegistry()

        # Query a specific jurisdiction
        result = await registry.query("LA", "What is the prescriptive period for breach of contract?")

        # Get container status for admin dashboard
        status = registry.get_all_status()

        # Ingest training data
        await registry.ingest_wdc_debate("LA", debate_data)
    """

    def __init__(self) -> None:
        self._configs: dict[str, JurisdictionConfig] = {
            j.code: j for j in _JURISDICTIONS
        }
        self._containers: dict[str, JurisdictionContainer] = {}

        logger.info(
            "ContainerRegistry initialized: %d jurisdictions configured",
            len(self._configs),
        )

    def _get_or_create(self, code: str) -> JurisdictionContainer:
        """Lazy-load a jurisdiction container."""
        code = code.upper()
        if code not in self._containers:
            config = self._configs.get(code)
            if not config:
                raise ValueError(
                    f"Unknown jurisdiction: {code}. "
                    f"Available: {sorted(self._configs.keys())}"
                )
            self._containers[code] = JurisdictionContainer(config)
        return self._containers[code]

    async def query(self, jurisdiction_code: str, question: str) -> dict[str, Any]:
        """Query a jurisdiction container's dual-brain system.

        Returns the DualBrainResult as a dict.
        """
        container = self._get_or_create(jurisdiction_code)
        result = await container.query(question)
        return result.model_dump()

    async def ingest_wdc_debate(
        self, jurisdiction_code: str, debate_data: dict[str, Any]
    ) -> None:
        """Route WDC debate training data to the correct container."""
        container = self._get_or_create(jurisdiction_code)
        await container.ingest_wdc_debate(debate_data)

    async def ingest_case_outcome(
        self, jurisdiction_code: str, outcome: dict[str, Any]
    ) -> None:
        """Route case outcome data to the correct container."""
        container = self._get_or_create(jurisdiction_code)
        await container.ingest_case_outcome(outcome)

    def get_container_status(self, code: str) -> dict[str, Any]:
        """Get status of a specific container."""
        container = self._get_or_create(code)
        return container.get_status()

    def get_all_status(self) -> list[dict[str, Any]]:
        """Get status of all configured jurisdictions (admin dashboard)."""
        statuses = []
        for code, config in sorted(self._configs.items()):
            if code in self._containers:
                statuses.append(self._containers[code].get_status())
            else:
                statuses.append({
                    "code": config.code,
                    "name": config.name,
                    "type": config.type.value,
                    "status": "not_loaded",
                    "wdc_debates_ingested": 0,
                    "case_outcomes_ingested": 0,
                })
        return statuses

    def list_jurisdictions(self) -> list[dict[str, str]]:
        """List all available jurisdictions."""
        return [
            {"code": c.code, "name": c.name, "type": c.type.value}
            for c in sorted(self._configs.values(), key=lambda x: x.code)
        ]

    @property
    def active_count(self) -> int:
        """Number of currently loaded containers."""
        return len(self._containers)

    @property
    def total_count(self) -> int:
        """Total configured jurisdictions."""
        return len(self._configs)
