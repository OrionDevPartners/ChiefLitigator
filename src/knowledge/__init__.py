"""Cyphergy Knowledge Engine — Auto-siphon case law catalog.

Novel architecture by Bo Pennington.

The knowledge engine automatically catalogs case law indexed by:
1. Statute (federal + state) — every case mapped to the statutes it interprets
2. Jurisdiction — federal case law tagged with applicable state implications
3. Practice area — civil, criminal, overlap classification
4. Holding type — what the case actually decided
5. Case context — filtered and suggested in sandbox with user's case facts

Auto-siphon: As cases flow through the system (via CourtListener,
user uploads, WDC debates), they are automatically cataloged and
indexed. The catalog grows with every interaction.
"""

from src.knowledge.argument_graph import (
    ArgumentChain,
    ArgumentGraph,
    CaseRelationship,
    GraphEdge,
)
from src.knowledge.case_catalog import CaseCatalog, CatalogEntry
from src.knowledge.crawler import CaseLawCrawler, CaseLawEntry, CrawlState
from src.knowledge.holding_extractor import (
    ExtractedHolding,
    ExtractionResult,
    HoldingExtractor,
    HoldingType,
    extract_and_catalog,
)
from src.knowledge.statute_index import StatuteEntry, StatuteIndex

__all__ = [
    "CaseCatalog",
    "CatalogEntry",
    "StatuteIndex",
    "StatuteEntry",
    "CaseLawCrawler",
    "CaseLawEntry",
    "CrawlState",
    "HoldingExtractor",
    "ExtractedHolding",
    "ExtractionResult",
    "HoldingType",
    "extract_and_catalog",
    "ArgumentGraph",
    "ArgumentChain",
    "GraphEdge",
    "CaseRelationship",
]
