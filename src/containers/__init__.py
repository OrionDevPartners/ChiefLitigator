"""Cyphergy Jurisdiction Containers — Data-Resident AI Agents.

Novel architecture by Bo Pennington.

Each jurisdiction (state, federal, territory) is a self-contained
container with its own AI agents, embedded data, and context memory.
Agents live WITH the data — no external API calls for legal lookups.

Container Structure:
  ├── AI Agent (Bedrock: Opus 4.6 primary)
  ├── Local Data (Aurora pgvector: statutes, case law, rules)
  ├── Dual-Brain Consensus (Opus + Llama Scout + Cohere)
  ├── Context Memory (persistent agent state)
  └── MCP Interface (inter-container communication)
"""

from src.containers.jurisdiction import JurisdictionContainer
from src.containers.registry import ContainerRegistry

__all__ = ["JurisdictionContainer", "ContainerRegistry"]
