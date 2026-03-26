"""ChiefLitigator Auto-Siphon Pipeline.

Workers:
    - courtlistener_worker: Case law (8M+ opinions, all courts)
    - uscode_worker: Federal statutes (54 titles)
    - legiscan_worker: 50-state statutes
    - scotus_worker: Supreme Court opinions
    - rules_worker: Federal Rules (FRCP, FRAP, FRE, FRCrP)
    - immigration_worker: INA, BIA, USCIS, EOIR
    - xref_builder: Cross-reference linkage (statute ↔ case ↔ rule)

Orchestrator:
    - orchestrator: Master controller for all workers
"""

from .orchestrator import SiphonOrchestrator, SiphonSource

__all__ = ["SiphonOrchestrator", "SiphonSource"]
