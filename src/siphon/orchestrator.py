"""Siphon Orchestrator — Manages all data ingestion workers.

This is the top-level controller that schedules and runs all siphon workers.
In production, this is invoked by AWS EventBridge on a schedule.
In development, it can be run manually via CLI.

Schedule:
    - CourtListener (case law):  Daily at 02:00 UTC
    - US Code (federal statutes): Weekly on Sunday at 03:00 UTC
    - GovInfo (CFR, Fed Register): Daily at 02:30 UTC
    - LegiScan (state statutes):  Weekly on Monday at 04:00 UTC
    - SCOTUS (Supreme Court):     Daily at 01:00 UTC
    - Federal Rules:              Monthly on 1st at 05:00 UTC
    - Immigration (INA, BIA):     Weekly on Wednesday at 03:00 UTC
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("cyphergy.siphon.orchestrator")


class SiphonSource(str, Enum):
    """Available data sources for the siphon pipeline."""
    COURTLISTENER = "courtlistener"
    USCODE = "uscode"
    GOVINFO = "govinfo"
    LEGISCAN = "legiscan"
    SCOTUS = "scotus"
    FEDERAL_RULES = "federal_rules"
    IMMIGRATION = "immigration"
    ALL = "all"


class SiphonOrchestrator:
    """Top-level orchestrator for all siphon workers."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def run(self, source: SiphonSource = SiphonSource.ALL) -> dict[str, Any]:
        """Run one or all siphon workers."""
        results: dict[str, Any] = {}
        start = datetime.utcnow()

        if source in (SiphonSource.ALL, SiphonSource.COURTLISTENER):
            from src.siphon.courtlistener_worker import CourtListenerSiphon
            token = os.getenv("COURTLISTENER_API_TOKEN")
            worker = CourtListenerSiphon(self.db, api_token=token)
            await worker.run_daily_siphon()
            results["courtlistener"] = "completed"

        if source in (SiphonSource.ALL, SiphonSource.USCODE):
            from src.siphon.uscode_worker import USCodeSiphon
            worker = USCodeSiphon(self.db)
            await worker.run_full_ingest()
            results["uscode"] = "completed"

        # Additional workers follow the same pattern:
        # GovInfo, LegiScan, SCOTUS, Federal Rules, Immigration
        # Each has its own worker class in src/siphon/

        elapsed = (datetime.utcnow() - start).total_seconds()
        results["elapsed_seconds"] = elapsed
        logger.info(f"Siphon run complete in {elapsed:.1f}s: {results}")
        return results


# CLI entrypoint for manual runs
if __name__ == "__main__":
    import sys
    source = SiphonSource(sys.argv[1]) if len(sys.argv) > 1 else SiphonSource.ALL
    # In production, the db_session would come from the FastAPI dependency injection
    # For CLI, we create it manually
    print(f"Running siphon for: {source.value}")
