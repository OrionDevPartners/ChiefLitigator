"""Siphon Orchestrator — Master controller for all data ingestion workers.

Manages the lifecycle of all siphon workers, coordinates execution order,
tracks run statistics, and reports to the EXECUTION_JOURNAL.

Schedule (EventBridge):
    - CourtListener (case law):  Daily at 02:00 UTC
    - US Code (federal statutes): Weekly on Sunday at 03:00 UTC
    - LegiScan (state statutes):  Weekly on Monday at 04:00 UTC
    - SCOTUS (Supreme Court):     Daily at 01:00 UTC
    - Federal Rules:              Monthly on 1st at 05:00 UTC
    - Immigration (INA, BIA):     Weekly on Wednesday at 03:00 UTC
    - XRef Builder:               Weekly on Saturday at 06:00 UTC

Triggered by:
    - AWS EventBridge (scheduled runs)
    - Manual invocation (initial bulk load)
    - API endpoint (admin-triggered refresh)

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cyphergy.siphon.orchestrator")


class SiphonSource(str, Enum):
    """Available data sources for the siphon pipeline."""
    COURTLISTENER = "courtlistener"
    USCODE = "uscode"
    LEGISCAN = "legiscan"
    SCOTUS = "scotus"
    FEDERAL_RULES = "federal_rules"
    IMMIGRATION = "immigration"
    XREF_BUILDER = "xref_builder"
    ALL = "all"


class SiphonOrchestrator:
    """Master orchestrator for the auto-siphon pipeline.

    Manages all workers and coordinates the ingestion of legal data
    from 10+ sources into Aurora PostgreSQL (pgvector).

    The orchestrator runs in two modes:
      1. **Full**: Initial bulk load of all data (run once at deployment)
      2. **Incremental**: Daily/weekly updates (run on EventBridge schedule)

    Worker execution order:
      Phase 1 (parallel): CourtListener, US Code, LegiScan, SCOTUS, Rules, Immigration
      Phase 2 (sequential): XRef Builder (depends on Phase 1 data)
    """

    WORKER_REGISTRY = {
        "courtlistener": {
            "module": "src.siphon.courtlistener_worker",
            "class_name": "CourtListenerSiphon",
            "schedule": "daily",
            "phase": 1,
            "description": "Case law from all federal and state courts (8M+ opinions)",
        },
        "uscode": {
            "module": "src.siphon.uscode_worker",
            "class_name": "USCodeSiphon",
            "schedule": "weekly",
            "phase": 1,
            "description": "Federal statutes — all 54 titles from OLRC",
        },
        "legiscan": {
            "module": "src.siphon.legiscan_worker",
            "class_name": "LegiScanWorker",
            "schedule": "weekly",
            "phase": 1,
            "description": "50-state statutes via LegiScan API",
        },
        "scotus": {
            "module": "src.siphon.scotus_worker",
            "class_name": "SCOTUSWorker",
            "schedule": "daily",
            "phase": 1,
            "description": "Supreme Court opinions and slip opinions",
        },
        "federal_rules": {
            "module": "src.siphon.rules_worker",
            "class_name": "RulesWorker",
            "schedule": "monthly",
            "phase": 1,
            "description": "Federal Rules (FRCP, FRAP, FRE, FRCrP)",
        },
        "immigration": {
            "module": "src.siphon.immigration_worker",
            "class_name": "ImmigrationWorker",
            "schedule": "weekly",
            "phase": 1,
            "description": "INA, BIA decisions, USCIS policy, EOIR practice manual",
        },
        "xref_builder": {
            "module": "src.siphon.xref_builder",
            "class_name": "XRefBuilder",
            "schedule": "weekly",
            "phase": 2,
            "description": "Cross-reference builder (statute ↔ case ↔ rule linkage)",
        },
    }

    def __init__(self, db_session=None) -> None:
        self.db = db_session
        self._run_id: Optional[str] = None
        self._results: Dict[str, Dict[str, Any]] = {}
        self._started_at: Optional[datetime] = None

    def _load_worker(self, name: str):
        """Dynamically load a worker class by name."""
        config = self.WORKER_REGISTRY.get(name)
        if not config:
            raise ValueError(f"Unknown worker: {name}")

        import importlib
        module = importlib.import_module(config["module"])
        worker_class = getattr(module, config["class_name"])
        return worker_class

    async def run_worker(self, name: str, mode: str = "incremental") -> Dict[str, Any]:
        """Run a single worker by name."""
        config = self.WORKER_REGISTRY.get(name)
        if not config:
            logger.error("Unknown worker: %s", name)
            return {"error": f"Unknown worker: {name}"}

        try:
            worker_class = self._load_worker(name)

            # Workers that need db_session
            if name in ("courtlistener", "uscode"):
                worker = worker_class(self.db, api_token=os.getenv("COURTLISTENER_API_TOKEN", ""))
                if name == "uscode":
                    worker = worker_class(self.db)
            else:
                worker = worker_class()

            logger.info("Starting worker: %s (mode=%s)", name, mode)

            if mode == "full":
                result = await worker.run_full()
            else:
                result = await worker.run_incremental()

            self._results[name] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            return result

        except Exception as exc:
            error_msg = str(exc)[:500]
            logger.error("Worker %s failed: %s", name, error_msg)
            self._results[name] = {
                "status": "failed",
                "error": error_msg,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            return {"error": error_msg}

    async def run_phase(self, phase: int, mode: str = "incremental") -> None:
        """Run all workers in a given phase concurrently."""
        phase_workers = [
            name for name, config in self.WORKER_REGISTRY.items()
            if config["phase"] == phase
        ]

        if not phase_workers:
            return

        logger.info("Running Phase %d workers: %s", phase, phase_workers)
        tasks = [self.run_worker(name, mode) for name in phase_workers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run(self, source: SiphonSource = SiphonSource.ALL, mode: str = "incremental") -> Dict[str, Any]:
        """Run one or all siphon workers.

        This is the main entry point called by EventBridge or the API.
        """
        self._started_at = datetime.now(timezone.utc)
        self._run_id = f"{mode}_{self._started_at.strftime('%Y%m%d_%H%M%S')}"
        logger.info("=== SIPHON RUN STARTING: %s (source=%s, mode=%s) ===", self._run_id, source.value, mode)

        if source == SiphonSource.ALL:
            # Phase 1: All data ingestion workers (parallel)
            await self.run_phase(1, mode=mode)
            # Phase 2: Cross-reference builder (depends on Phase 1)
            await self.run_phase(2, mode=mode)
        else:
            # Run single worker
            await self.run_worker(source.value, mode=mode)

        summary = self._build_summary()
        logger.info("=== SIPHON RUN COMPLETE: %s ===", self._run_id)
        return summary

    async def run_full(self) -> Dict[str, Any]:
        """Run full bulk ingestion of all data sources."""
        return await self.run(SiphonSource.ALL, mode="full")

    async def run_incremental(self, workers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run incremental update for specified workers (or all)."""
        if workers:
            self._started_at = datetime.now(timezone.utc)
            self._run_id = f"incr_{self._started_at.strftime('%Y%m%d_%H%M%S')}"
            for name in workers:
                await self.run_worker(name, mode="incremental")
            return self._build_summary()
        return await self.run(SiphonSource.ALL, mode="incremental")

    def _build_summary(self) -> Dict[str, Any]:
        """Build a summary of the siphon run."""
        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - self._started_at).total_seconds() if self._started_at else 0

        total_fetched = 0
        total_stored = 0
        total_errors = 0
        failed_workers = []

        for name, result in self._results.items():
            if result.get("status") == "failed":
                failed_workers.append(name)
                total_errors += 1
            elif result.get("result"):
                stats = result["result"]
                if isinstance(stats, dict):
                    total_fetched += stats.get("fetched", 0)
                    total_stored += stats.get("stored", 0)
                    total_errors += stats.get("errors", 0)

        return {
            "run_id": self._run_id,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "completed_at": completed_at.isoformat(),
            "duration_seconds": duration,
            "workers_run": len(self._results),
            "workers_failed": len(failed_workers),
            "failed_workers": failed_workers,
            "total_records_fetched": total_fetched,
            "total_records_stored": total_stored,
            "total_errors": total_errors,
            "worker_results": self._results,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "run_id": self._run_id,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "workers_registered": list(self.WORKER_REGISTRY.keys()),
            "results": self._results,
        }


# CLI entrypoint for manual runs
if __name__ == "__main__":
    import sys
    source_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    mode_arg = sys.argv[2] if len(sys.argv) > 2 else "incremental"
    source = SiphonSource(source_arg)
    print(f"Running siphon for: {source.value} (mode={mode_arg})")
    # In production, db_session comes from FastAPI DI
    # For CLI: asyncio.run(SiphonOrchestrator(db).run(source, mode_arg))
