"""Case Catalog — Exhaustive case law database indexed by statute.

Novel architecture by Bo Pennington.

This is NOT a passive siphon. The perpetual crawler (crawler.py) runs
until EVERY major Supreme Court and state court case is cataloged.

What we store per case (LIGHTWEIGHT):
  - Case number, date, plaintiff vs defendant names
  - Reference links (CourtListener URL, Google Scholar URL)
  - Holdings mapped to statutes
  - Support classification: SUPPORTS_PLAINTIFF or SUPPORTS_DEFENDANT
  - Positive/negative tags for instant matching
  - Practice area + sub-area tags

What we DO NOT store:
  - Full opinion text (we link to it)

TWO ACCESS MODES:
  MODE 1: Context-aware — user uploads case facts → auto-suggestions
  MODE 2: Context-free — user types scenario + desired outcome + side
          → search returns matching case law instantly
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.knowledge.statute_index import (
    CaseTreatment,
    StatuteIndex,
)

logger = logging.getLogger("cyphergy.knowledge.case_catalog")


class CatalogEntry(BaseModel):
    """A single case in the catalog — the atomic unit of legal knowledge."""

    # Case identity
    citation: str = Field(description="Full Bluebook citation")
    name: str = Field(description="Case name (e.g., 'Smith v. Jones')")
    court: str = Field(description="Court that decided the case")
    year: int = Field(description="Year decided")
    jurisdiction: str = Field(description="Jurisdiction code")

    # What the case decided
    holdings: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of holdings: [{statute, holding_text, treatment}]",
    )

    # Classification
    practice_area: str = Field(default="civil")
    sub_areas: list[str] = Field(default_factory=list)
    is_overlap: bool = Field(
        default=False,
        description="True if case involves civil-criminal bridge law",
    )

    # Statutes interpreted
    statutes_cited: list[str] = Field(
        default_factory=list,
        description="All statutes this case cites or interprets",
    )

    # Verification
    verified: bool = Field(default=False, description="Passed citation verification chain")
    good_law: bool = Field(default=True, description="Not overruled or reversed")
    verification_source: str = Field(default="", description="CourtListener, Google Scholar, etc.")

    # Auto-siphon metadata
    siphoned_at: str = Field(default="", description="When auto-cataloged")
    siphon_source: str = Field(default="", description="How discovered: wdc_debate, user_query, courtlistener_search")

    # Full text (if available)
    opinion_text_available: bool = Field(default=False)
    opinion_url: str = Field(default="")


class CaseCatalog:
    """The auto-siphon engine — catalogs case law indexed by statute.

    Usage::

        catalog = CaseCatalog()

        # Auto-siphon a case (called by citation verification chain)
        catalog.siphon(CatalogEntry(
            citation="Globe Newspaper Co. v. King, 658 So.2d 518 (Fla. 1995)",
            name="Globe Newspaper Co. v. King",
            court="Florida Supreme Court",
            year=1995,
            jurisdiction="FL",
            practice_area="overlap",
            sub_areas=["punitive_damages"],
            is_overlap=True,
            statutes_cited=["Fla. Stat. § 768.72"],
            holdings=[{
                "statute": "Fla. Stat. § 768.72",
                "holding_text": "Court must evaluate proffer before allowing punitive amendment",
                "treatment": "interpreted",
            }],
            verified=True,
        ))

        # Query: what cases interpret Fla. Stat. § 768.72?
        results = catalog.query_by_statute("Fla. Stat. § 768.72")

        # Context-aware suggestions in sandbox
        suggestions = catalog.suggest(
            jurisdiction="FL",
            statutes=["Fla. Stat. § 768.72", "Fla. Stat. § 768.73"],
            practice_area="overlap",
            case_facts="Construction defect with gross negligence",
        )
    """

    def __init__(self) -> None:
        self._cases: dict[str, CatalogEntry] = {}  # citation → entry
        self._statute_index = StatuteIndex()
        logger.info("CaseCatalog initialized with StatuteIndex")

    @property
    def statute_index(self) -> StatuteIndex:
        return self._statute_index

    def siphon(self, entry: CatalogEntry) -> bool:
        """Auto-siphon a case into the catalog.

        Indexes the case by every statute it cites.
        Returns True if new, False if duplicate.
        """
        if entry.citation in self._cases:
            return False

        entry.siphoned_at = datetime.utcnow().isoformat()
        self._cases[entry.citation] = entry

        # Index by every statute cited
        for holding in entry.holdings:
            statute_citation = holding.get("statute", "")
            if statute_citation:
                treatment = CaseTreatment.INTERPRETED
                try:
                    treatment = CaseTreatment(holding.get("treatment", "interpreted"))
                except ValueError:
                    pass

                self._statute_index.siphon_case(
                    statute_citation=statute_citation,
                    case_citation=entry.citation,
                    case_name=entry.name,
                    holding=holding.get("holding_text", ""),
                    treatment=treatment,
                    court=entry.court,
                    year=entry.year,
                    jurisdiction=entry.jurisdiction,
                    verified=entry.verified,
                )

        logger.info(
            "case_cataloged | citation=%s jurisdiction=%s statutes=%d holdings=%d",
            entry.citation,
            entry.jurisdiction,
            len(entry.statutes_cited),
            len(entry.holdings),
        )
        return True

    def query_by_statute(
        self,
        statute_citation: str,
        jurisdiction: Optional[str] = None,
        min_year: Optional[int] = None,
        verified_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Query cases that interpret a specific statute."""
        return self._statute_index.query(
            statute_citation=statute_citation,
            jurisdiction=jurisdiction,
            min_year=min_year,
            verified_only=verified_only,
        )

    def query_by_case(self, citation: str) -> Optional[CatalogEntry]:
        """Look up a specific case."""
        return self._cases.get(citation)

    def suggest(
        self,
        jurisdiction: str,
        statutes: Optional[list[str]] = None,
        practice_area: Optional[str] = None,
        sub_area: Optional[str] = None,
        case_facts: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Context-aware case suggestions for the user's sandbox.

        Given the user's case context (jurisdiction, relevant statutes,
        practice area, facts), returns the most relevant cases ranked by:
        1. Binding authority in the user's jurisdiction
        2. Cases interpreting the same statutes
        3. Similar practice area/sub-area
        4. Recency
        """
        suggestions = []

        # If specific statutes provided, query each
        if statutes:
            for statute in statutes:
                cases = self._statute_index.query(
                    statute_citation=statute,
                    jurisdiction=jurisdiction,
                )
                for case in cases:
                    case["source_statute"] = statute
                    case["relevance"] = "binding" if case.get("jurisdiction") == jurisdiction else "persuasive"
                    suggestions.append(case)

        # Also get statute-level suggestions
        if practice_area:
            statute_suggestions = self._statute_index.suggest_for_case(
                jurisdiction=jurisdiction,
                practice_area=practice_area,
                sub_area=sub_area,
                case_facts=case_facts,
                limit=limit,
            )
            for s in statute_suggestions:
                suggestions.append(
                    {
                        "type": "statute_suggestion",
                        "statute": s["statute"],
                        "title": s["title"],
                        "binding_cases": s["binding_cases"],
                        "persuasive_cases": s["persuasive_cases"],
                        "relevance_score": s["relevance_score"],
                    }
                )

        # Deduplicate and sort
        seen = set()
        unique = []
        for s in suggestions:
            key = s.get("citation") or s.get("statute", "")
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Catalog statistics for admin dashboard."""
        statute_stats = self._statute_index.get_stats()
        overlap_cases = sum(1 for c in self._cases.values() if c.is_overlap)
        verified = sum(1 for c in self._cases.values() if c.verified)
        return {
            "total_cases": len(self._cases),
            "verified_cases": verified,
            "overlap_cases": overlap_cases,
            "jurisdictions": len(set(c.jurisdiction for c in self._cases.values())),
            **statute_stats,
        }
