"""Beta invite model — re-exported from src.database.models.

The canonical BetaInvite model lives in src/database/models.py to avoid
SQLAlchemy metadata conflicts (duplicate table definitions).
"""

from __future__ import annotations

from src.database.models import BetaInvite

__all__ = ["BetaInvite"]
