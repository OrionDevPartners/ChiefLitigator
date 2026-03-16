"""Statute Index — Maps every statute to the case law that interprets it.

Novel architecture by Bo Pennington.

The statute index is the backbone of the auto-siphon system.
Every statute (federal and state) is indexed with:
- Full text reference
- Cases that have interpreted it
- Holdings per case (what the court decided about this statute)
- Jurisdiction applicability (federal statutes apply in all states,
  state statutes apply in their jurisdiction + persuasive elsewhere)
- Practice area classification
- Amendment history (when the statute changed)

When a user's case involves a statute, the system automatically
surfaces ALL case law interpreting that statute, filtered by:
1. Jurisdiction match (binding first, then persuasive)
2. Recency (newer cases preferred)
3. Relevance to the user's specific facts
4. Good law status (overruled cases flagged, not hidden)
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.knowledge.statute_index")


class StatuteType(str, Enum):
    """Classification of statutory authority."""

    FEDERAL_STATUTE = "federal_statute"  # USC
    FEDERAL_REGULATION = "federal_regulation"  # CFR
    FEDERAL_RULE = "federal_rule"  # FRCP, FRE, FRAP
    STATE_STATUTE = "state_statute"
    STATE_REGULATION = "state_regulation"
    STATE_RULE = "state_rule"  # State procedural rules
    LOCAL_RULE = "local_rule"  # Court-specific rules
    CONSTITUTIONAL = "constitutional"  # US or state constitution


class StatuteStatus(str, Enum):
    """Current status of a statute."""

    CURRENT = "current"
    AMENDED = "amended"  # Still valid but text changed
    REPEALED = "repealed"  # No longer in effect
    SUPERSEDED = "superseded"  # Replaced by another statute


class CaseTreatment(str, Enum):
    """How a case treats the statute it interprets."""

    INTERPRETED = "interpreted"  # Applied the statute to facts
    UPHELD = "upheld"  # Found statute constitutional/valid
    STRUCK_DOWN = "struck_down"  # Found statute unconstitutional
    NARROWED = "narrowed"  # Limited the statute's scope
    EXPANDED = "expanded"  # Broadened the statute's scope
    DISTINGUISHED = "distinguished"  # Applied differently than prior cases


class StatuteEntry(BaseModel):
    """A single statute in the index."""

    # Identity
    citation: str = Field(description="Full citation (e.g., '42 U.S.C. § 1983' or 'Fla. Stat. § 768.72')")
    title: str = Field(description="Short title or description")
    type: StatuteType
    jurisdiction: str = Field(description="Jurisdiction code (FED, FL, CA, etc.)")
    status: StatuteStatus = Field(default=StatuteStatus.CURRENT)

    # Practice area
    practice_area: str = Field(default="civil", description="Primary practice area")
    sub_areas: list[str] = Field(default_factory=list, description="Sub-areas this statute touches")

    # Versioning
    effective_date: Optional[str] = Field(default=None, description="When this version became effective")
    amendment_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="History of amendments: [{date, description, old_text_summary}]",
    )

    # Case law index — the core of the auto-siphon
    interpreting_cases: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Cases that interpret this statute, with holdings and treatment",
    )

    # Metadata
    source: str = Field(default="", description="Where this statute was sourced from")
    last_verified: Optional[str] = Field(default=None, description="Last verification date")
    auto_siphoned: bool = Field(default=False, description="Whether this was auto-cataloged")

    def add_case(
        self,
        case_citation: str,
        case_name: str,
        holding: str,
        treatment: CaseTreatment,
        court: str,
        year: int,
        jurisdiction: str,
        verified: bool = False,
        source: str = "auto_siphon",
    ) -> None:
        """Add a case to this statute's interpretation index."""
        self.interpreting_cases.append(
            {
                "citation": case_citation,
                "name": case_name,
                "holding": holding,
                "treatment": treatment.value,
                "court": court,
                "year": year,
                "jurisdiction": jurisdiction,
                "verified": verified,
                "source": source,
                "cataloged_at": datetime.utcnow().isoformat(),
            }
        )

    def get_cases_by_jurisdiction(self, jurisdiction: str) -> list[dict[str, Any]]:
        """Get cases from a specific jurisdiction interpreting this statute."""
        return [c for c in self.interpreting_cases if c["jurisdiction"] == jurisdiction]

    def get_binding_authority(self, jurisdiction: str) -> list[dict[str, Any]]:
        """Get binding cases (same jurisdiction) ordered by recency."""
        binding = self.get_cases_by_jurisdiction(jurisdiction)
        return sorted(binding, key=lambda c: c.get("year", 0), reverse=True)

    def get_persuasive_authority(self, exclude_jurisdiction: str) -> list[dict[str, Any]]:
        """Get persuasive cases (other jurisdictions) ordered by recency."""
        persuasive = [c for c in self.interpreting_cases if c["jurisdiction"] != exclude_jurisdiction]
        return sorted(persuasive, key=lambda c: c.get("year", 0), reverse=True)


class StatuteIndex:
    """Master index of all statutes with their interpreting case law.

    Usage::

        index = StatuteIndex()

        # Add a statute
        index.add_statute(StatuteEntry(
            citation="Fla. Stat. § 768.72",
            title="Punitive damages — leave of court required",
            type=StatuteType.STATE_STATUTE,
            jurisdiction="FL",
            practice_area="overlap",
            sub_areas=["punitive_damages"],
        ))

        # Auto-siphon a case into the index
        index.siphon_case(
            statute_citation="Fla. Stat. § 768.72",
            case_citation="Globe Newspaper Co. v. King, 658 So.2d 518 (Fla. 1995)",
            case_name="Globe Newspaper Co. v. King",
            holding="Court must evaluate proffer of evidence before allowing punitive amendment",
            treatment=CaseTreatment.INTERPRETED,
            court="Florida Supreme Court",
            year=1995,
            jurisdiction="FL",
        )

        # Query: what cases interpret this statute in Florida?
        cases = index.query("Fla. Stat. § 768.72", jurisdiction="FL")

        # Context-aware suggestion in sandbox
        suggestions = index.suggest_for_case(
            jurisdiction="FL",
            practice_area="overlap",
            sub_area="punitive_damages",
            case_facts="Defendant acted with gross negligence in construction defect case",
        )
    """

    def __init__(self) -> None:
        self._statutes: dict[str, StatuteEntry] = {}
        logger.info("StatuteIndex initialized")

    def add_statute(self, entry: StatuteEntry) -> None:
        """Add or update a statute in the index."""
        self._statutes[entry.citation] = entry
        logger.info("statute_indexed | citation=%s jurisdiction=%s", entry.citation, entry.jurisdiction)

    def get_statute(self, citation: str) -> Optional[StatuteEntry]:
        """Look up a statute by citation."""
        return self._statutes.get(citation)

    def siphon_case(
        self,
        statute_citation: str,
        case_citation: str,
        case_name: str,
        holding: str,
        treatment: CaseTreatment,
        court: str,
        year: int,
        jurisdiction: str,
        verified: bool = False,
    ) -> bool:
        """Auto-siphon a case into the statute index.

        If the statute doesn't exist yet, creates a placeholder entry.
        Returns True if the case was added, False if it was a duplicate.
        """
        # Auto-create statute entry if it doesn't exist
        if statute_citation not in self._statutes:
            self._statutes[statute_citation] = StatuteEntry(
                citation=statute_citation,
                title=f"Auto-cataloged from {case_name}",
                type=self._infer_statute_type(statute_citation),
                jurisdiction=self._infer_jurisdiction(statute_citation),
                auto_siphoned=True,
            )

        statute = self._statutes[statute_citation]

        # Check for duplicate
        existing = [c["citation"] for c in statute.interpreting_cases]
        if case_citation in existing:
            return False

        statute.add_case(
            case_citation=case_citation,
            case_name=case_name,
            holding=holding,
            treatment=treatment,
            court=court,
            year=year,
            jurisdiction=jurisdiction,
            verified=verified,
            source="auto_siphon",
        )

        logger.info(
            "case_siphoned | statute=%s case=%s jurisdiction=%s",
            statute_citation,
            case_citation,
            jurisdiction,
        )
        return True

    def query(
        self,
        statute_citation: str,
        jurisdiction: Optional[str] = None,
        treatment: Optional[CaseTreatment] = None,
        min_year: Optional[int] = None,
        verified_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Query cases interpreting a statute with filters."""
        statute = self._statutes.get(statute_citation)
        if not statute:
            return []

        cases = list(statute.interpreting_cases)

        if jurisdiction:
            cases = [c for c in cases if c["jurisdiction"] == jurisdiction]
        if treatment:
            cases = [c for c in cases if c["treatment"] == treatment.value]
        if min_year:
            cases = [c for c in cases if c.get("year", 0) >= min_year]
        if verified_only:
            cases = [c for c in cases if c.get("verified", False)]

        return sorted(cases, key=lambda c: c.get("year", 0), reverse=True)

    def suggest_for_case(
        self,
        jurisdiction: str,
        practice_area: str,
        sub_area: Optional[str] = None,
        case_facts: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Context-aware suggestions based on case facts and jurisdiction.

        This is the sandbox suggestion engine — given a user's case context,
        it finds the most relevant statutes and their interpreting cases.

        Ranking:
        1. Same jurisdiction + same sub-area (most relevant)
        2. Same jurisdiction + same practice area
        3. Federal (always relevant as potential preemption/authority)
        4. Other state (persuasive only)
        """
        suggestions = []

        for citation, statute in self._statutes.items():
            relevance = 0

            # Jurisdiction match
            if statute.jurisdiction == jurisdiction:
                relevance += 100
            elif statute.jurisdiction == "FED":
                relevance += 50  # Federal always somewhat relevant

            # Practice area match
            if statute.practice_area == practice_area:
                relevance += 30

            # Sub-area match
            if sub_area and sub_area in statute.sub_areas:
                relevance += 50

            # Has interpreting cases (more useful than bare statutes)
            relevance += min(len(statute.interpreting_cases) * 5, 50)

            if relevance > 0:
                binding = statute.get_binding_authority(jurisdiction)
                persuasive = statute.get_persuasive_authority(jurisdiction)
                suggestions.append(
                    {
                        "statute": citation,
                        "title": statute.title,
                        "jurisdiction": statute.jurisdiction,
                        "practice_area": statute.practice_area,
                        "relevance_score": relevance,
                        "binding_cases": len(binding),
                        "persuasive_cases": len(persuasive),
                        "most_recent_case": binding[0] if binding else (persuasive[0] if persuasive else None),
                        "total_cases": len(statute.interpreting_cases),
                    }
                )

        # Sort by relevance, return top N
        suggestions.sort(key=lambda s: s["relevance_score"], reverse=True)
        return suggestions[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Return catalog statistics for admin dashboard."""
        total_cases = sum(len(s.interpreting_cases) for s in self._statutes.values())
        auto_siphoned = sum(1 for s in self._statutes.values() if s.auto_siphoned)
        return {
            "total_statutes": len(self._statutes),
            "total_cases_cataloged": total_cases,
            "auto_siphoned_statutes": auto_siphoned,
            "jurisdictions_covered": len(set(s.jurisdiction for s in self._statutes.values())),
        }

    def _infer_statute_type(self, citation: str) -> StatuteType:
        """Infer statute type from citation format."""
        c = citation.lower()
        if "u.s.c." in c or "usc" in c:
            return StatuteType.FEDERAL_STATUTE
        if "c.f.r." in c or "cfr" in c:
            return StatuteType.FEDERAL_REGULATION
        if "frcp" in c or "fre " in c or "frap" in c:
            return StatuteType.FEDERAL_RULE
        if "const." in c or "amend." in c:
            return StatuteType.CONSTITUTIONAL
        return StatuteType.STATE_STATUTE

    def _infer_jurisdiction(self, citation: str) -> str:
        """Infer jurisdiction from citation format."""
        c = citation.lower()
        if "u.s.c." in c or "usc" in c or "frcp" in c or "c.f.r." in c:
            return "FED"
        if "fla." in c:
            return "FL"
        if "cal." in c:
            return "CA"
        if "tex." in c:
            return "TX"
        if "la. " in c:
            return "LA"
        if "n.y." in c:
            return "NY"
        return "UNKNOWN"
