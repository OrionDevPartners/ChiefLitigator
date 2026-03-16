"""Cyphergy orchestration module.

Contains the Weighted Debate Consensus (WDC) v2.0 scoring engine
that all substantive outputs must pass through before reaching the user.
"""

from src.orchestrator.orchestrator import OrchestrationRequest, OrchestrationResult, Orchestrator
from src.orchestrator.wdc import WDCEngine, WDCResult, WDCVerdict

__all__ = [
    "WDCEngine",
    "WDCResult",
    "WDCVerdict",
    "Orchestrator",
    "OrchestrationRequest",
    "OrchestrationResult",
]
