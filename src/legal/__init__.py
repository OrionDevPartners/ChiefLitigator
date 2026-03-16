"""Cyphergy Legal Engine — jurisdiction-aware deadline computation.

This module provides the core legal deadline calculator used across all
Cyphergy agents. It is the most safety-critical component in the system:
a missed deadline can result in case dismissal.

Conservative computation: when ambiguous, ALWAYS choose the earlier deadline.
"""

from src.legal.deadline_calc import (
    DeadlineCalculator,
    DeadlineResult,
    DeadlineType,
    Jurisdiction,
    ServiceMethod,
)

__all__ = [
    "DeadlineCalculator",
    "DeadlineResult",
    "DeadlineType",
    "Jurisdiction",
    "ServiceMethod",
]
