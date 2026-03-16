"""Perpetual Case Law Crawler — Exhaustive cataloging of ALL case law.

Novel architecture by Bo Pennington.

THIS IS NOT A PASSIVE SIPHON. This is a perpetual crawler that runs
until every single major Supreme Court and state court case is cataloged.

What we store per case (LIGHTWEIGHT — no full opinions):
  - Case number / docket number
  - Date decided
  - Plaintiff vs Defendant names
  - Court (which court decided it)
  - Reference links (CourtListener URL, Google Scholar URL)
  - Statutes interpreted (mapped to statute index)
  - Holdings summary (what the court decided)
  - Support classification: SUPPORTS_PLAINTIFF or SUPPORTS_DEFENDANT
  - Positive/negative treatment tags
  - Practice area + sub-area tags
  - Jurisdiction

What we DO NOT store:
  - Full opinion text (too expensive, not needed — we link to it)
  - Briefs, motions, or other filings
  - Judge biographical data (separate system)

The crawler runs perpetually via:
  1. CourtListener API — 12M+ opinions, paginated crawl
  2. Google Scholar Legal — backup source
  3. State court APIs — where available

Two access modes:
  MODE 1: Context-aware suggestions
    User uploads case context → Cyphergy auto-suggests matching case law
    filtered by jurisdiction, statute, practice area, plaintiff/defendant position

  MODE 2: Search without context
    User types a scenario + desired outcome + plaintiff or defendant
    → Cyphergy returns matching case law from the catalog
    No case context needed — pure search engine
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.knowledge.crawler")


# ---------------------------------------------------------------------------
# Catalog Entry — what we store per case (lightweight)
# ---------------------------------------------------------------------------


class PartyRole(str, Enum):
    """Which party does this case support?"""

    SUPPORTS_PLAINTIFF = "supports_plaintiff"
    SUPPORTS_DEFENDANT = "supports_defendant"
    NEUTRAL = "neutral"  # Procedural ruling, doesn't favor either side
    MIXED = "mixed"      # Different holdings favor different parties


class CaseLawEntry(BaseModel):
    """Lightweight catalog entry for a single case.

    No full opinion text — only metadata, links, and indexed holdings.
    """

    # Identity
    case_number: str = Field(description="Docket/case number")
    citation: str = Field(description="Bluebook citation")
    name: str = Field(description="Plaintiff v. Defendant")
    plaintiff: str = Field(description="Plaintiff name(s)")
    defendant: str = Field(description="Defendant name(s)")

    # Court + Date
    court: str = Field(description="Court name")
    date_decided: str = Field(description="Date decided (YYYY-MM-DD)")
    year: int = Field(description="Year decided")
    jurisdiction: str = Field(description="Jurisdiction code")

    # Reference links (we link, not store)
    courtlistener_url: str = Field(default="", description="CourtListener opinion URL")
    google_scholar_url: str = Field(default="", description="Google Scholar URL")
    other_urls: list[str] = Field(default_factory=list, description="Other reference URLs")

    # What the case decided
    holdings: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of holdings: [{statute, holding_text, supports (plaintiff/defendant)}]",
    )

    # Classification
    party_support: PartyRole = Field(
        default=PartyRole.NEUTRAL,
        description="Overall: which party does this case favor?",
    )
    practice_area: str = Field(default="civil")
    sub_areas: list[str] = Field(default_factory=list)
    is_overlap: bool = Field(default=False, description="Civil-criminal bridge case")

    # Statutes this case interprets
    statutes_cited: list[str] = Field(default_factory=list)

    # Treatment tags
    positive_tags: list[str] = Field(
        default_factory=list,
        description="What this case is GOOD for: ['breach_of_contract_damages', 'discovery_compel', ...]",
    )
    negative_tags: list[str] = Field(
        default_factory=list,
        description="What this case is BAD for (negative precedent): ['punitive_cap', 'arbitration_required', ...]",
    )

    # Status
    good_law: bool = Field(default=True, description="Not overruled")
    subsequent_history: str = Field(default="", description="Affirmed, reversed, vacated, etc.")

    # Crawler metadata
    crawled_at: str = Field(default="")
    crawl_source: str = Field(default="courtlistener")
    verified: bool = Field(default=False)


# ---------------------------------------------------------------------------
# Crawler State
# ---------------------------------------------------------------------------


class CrawlState(BaseModel):
    """Persistent state for the perpetual crawler."""

    # Progress tracking
    total_cases_crawled: int = 0
    total_cases_cataloged: int = 0
    total_cases_skipped: int = 0

    # Per-source progress
    courtlistener_offset: int = 0
    courtlistener_total: int = 0

    # Per-jurisdiction progress
    jurisdiction_progress: dict[str, int] = Field(
        default_factory=dict,
        description="Cases cataloged per jurisdiction",
    )

    # Timing
    started_at: str = Field(default="")
    last_crawl_at: str = Field(default="")
    is_running: bool = Field(default=False)


# ---------------------------------------------------------------------------
# Perpetual Crawler
# ---------------------------------------------------------------------------


class CaseLawCrawler:
    """Perpetual crawler that catalogs ALL case law.

    Runs until every major Supreme Court and state court case is indexed.
    Uses CourtListener API (12M+ opinions) as primary source.

    Usage::

        crawler = CaseLawCrawler(catalog=catalog)

        # Start perpetual crawl (runs in background)
        await crawler.start()

        # Check progress
        state = crawler.get_state()
        print(f"Crawled: {state.total_cases_crawled}, Cataloged: {state.total_cases_cataloged}")

        # Stop crawler
        await crawler.stop()
    """

    # CourtListener API base (from env — CPAA compliant)
    _API_BASE = os.getenv("COURTLISTENER_API_URL", "https://www.courtlistener.com/api/rest/v4")
    _API_KEY = os.getenv("COURTLISTENER_API_KEY", "")
    _BATCH_SIZE = 20  # Cases per API request
    _SLEEP_BETWEEN = 1.0  # Seconds between requests (rate limiting)

    def __init__(self, catalog: Any) -> None:
        self._catalog = catalog
        self._state = CrawlState()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the perpetual crawl in the background."""
        if self._running:
            logger.warning("Crawler already running")
            return

        self._running = True
        self._state.started_at = datetime.utcnow().isoformat()
        self._state.is_running = True
        self._task = asyncio.create_task(self._crawl_loop())
        logger.info("Perpetual crawler started")

    async def stop(self) -> None:
        """Stop the crawler gracefully."""
        self._running = False
        self._state.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(
            "Crawler stopped | crawled=%d cataloged=%d",
            self._state.total_cases_crawled,
            self._state.total_cases_cataloged,
        )

    def get_state(self) -> CrawlState:
        """Get current crawler state for admin dashboard."""
        return self._state

    async def _crawl_loop(self) -> None:
        """Main crawl loop — runs perpetually until stopped or complete."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {}
            if self._API_KEY:
                headers["Authorization"] = f"Token {self._API_KEY}"

            while self._running:
                try:
                    # Fetch a batch of opinions from CourtListener
                    url = f"{self._API_BASE}/opinions/"
                    params = {
                        "order_by": "-date_created",
                        "offset": self._state.courtlistener_offset,
                        "limit": self._BATCH_SIZE,
                    }

                    response = await client.get(url, headers=headers, params=params)

                    if response.status_code == 429:
                        # Rate limited — back off
                        logger.warning("CourtListener rate limited, sleeping 60s")
                        await asyncio.sleep(60)
                        continue

                    if response.status_code != 200:
                        logger.error(
                            "CourtListener API error: %d", response.status_code
                        )
                        await asyncio.sleep(10)
                        continue

                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        # No more results — crawl complete (or wrapped around)
                        logger.info("CourtListener crawl complete at offset %d", self._state.courtlistener_offset)
                        # Reset to catch new cases
                        self._state.courtlistener_offset = 0
                        await asyncio.sleep(3600)  # Wait 1 hour before re-crawling
                        continue

                    # Process each opinion
                    for opinion in results:
                        self._state.total_cases_crawled += 1
                        try:
                            entry = self._parse_opinion(opinion)
                            if entry:
                                added = self._catalog.siphon(entry)
                                if added:
                                    self._state.total_cases_cataloged += 1
                                    jur = entry.jurisdiction
                                    self._state.jurisdiction_progress[jur] = (
                                        self._state.jurisdiction_progress.get(jur, 0) + 1
                                    )
                                else:
                                    self._state.total_cases_skipped += 1
                        except Exception as e:
                            logger.error("parse_failed | error=%s", str(e)[:200])
                            self._state.total_cases_skipped += 1

                    # Advance offset
                    self._state.courtlistener_offset += self._BATCH_SIZE
                    self._state.last_crawl_at = datetime.utcnow().isoformat()

                    # Log progress periodically
                    if self._state.total_cases_crawled % 100 == 0:
                        logger.info(
                            "crawl_progress | crawled=%d cataloged=%d skipped=%d offset=%d",
                            self._state.total_cases_crawled,
                            self._state.total_cases_cataloged,
                            self._state.total_cases_skipped,
                            self._state.courtlistener_offset,
                        )

                    # Rate limiting — respect CourtListener
                    await asyncio.sleep(self._SLEEP_BETWEEN)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("crawl_error | error=%s", str(e)[:200])
                    await asyncio.sleep(10)

    def _parse_opinion(self, opinion: dict[str, Any]) -> Optional[CaseLawEntry]:
        """Parse a CourtListener opinion into a CaseLawEntry.

        Extracts only the lightweight metadata we need — no full text.
        """
        # Extract case name
        case_name = opinion.get("case_name", "")
        if not case_name:
            return None

        # Parse plaintiff vs defendant from case name
        parties = case_name.split(" v. ", 1) if " v. " in case_name else case_name.split(" v ", 1)
        plaintiff = parties[0].strip() if len(parties) > 1 else ""
        defendant = parties[1].strip() if len(parties) > 1 else ""

        # Extract citation
        citations = opinion.get("citations", [])
        citation = citations[0].get("cite", "") if citations else ""

        # Build entry
        entry = CaseLawEntry(
            case_number=str(opinion.get("id", "")),
            citation=citation or f"{case_name} (CourtListener ID: {opinion.get('id', '')})",
            name=case_name,
            plaintiff=plaintiff,
            defendant=defendant,
            court=opinion.get("court", {}).get("full_name", "") if isinstance(opinion.get("court"), dict) else str(opinion.get("court", "")),
            date_decided=opinion.get("date_created", "")[:10],
            year=int(opinion.get("date_created", "0000")[:4]) if opinion.get("date_created") else 0,
            jurisdiction=self._infer_jurisdiction(opinion),
            courtlistener_url=f"https://www.courtlistener.com/opinion/{opinion.get('id', '')}/",
            crawled_at=datetime.utcnow().isoformat(),
            crawl_source="courtlistener",
        )

        return entry

    def _infer_jurisdiction(self, opinion: dict[str, Any]) -> str:
        """Infer jurisdiction from CourtListener court data."""
        court = opinion.get("court", {})
        court_id = court.get("id", "") if isinstance(court, dict) else str(court)

        # Federal courts
        if any(x in court_id for x in ["scotus", "ca1", "ca2", "ca3", "ca4", "ca5",
                                         "ca6", "ca7", "ca8", "ca9", "ca10", "ca11", "cadc", "cafc"]):
            return "FED"

        # State courts — map court ID to state code
        state_map = {
            "fla": "FL", "cal": "CA", "tex": "TX", "la": "LA", "ny": "NY",
            "ill": "IL", "ga": "GA", "ohio": "OH", "pa": "PA", "va": "VA",
            "nj": "NJ", "nc": "NC", "mi": "MI", "ma": "MA", "wa": "WA",
            "az": "AZ", "co": "CO", "mn": "MN", "wi": "WI", "mo": "MO",
            "md": "MD", "in": "IN", "tn": "TN", "sc": "SC", "al": "AL",
            "or": "OR", "ky": "KY", "ct": "CT", "ok": "OK", "ia": "IA",
            "ms": "MS", "ar": "AR", "ks": "KS", "nv": "NV", "ut": "UT",
            "ne": "NE", "nm": "NM", "wv": "WV", "id": "ID", "hi": "HI",
            "me": "ME", "nh": "NH", "ri": "RI", "mt": "MT", "de": "DE",
            "sd": "SD", "nd": "ND", "ak": "AK", "vt": "VT", "wy": "WY",
            "dc": "DC",
        }

        for key, code in state_map.items():
            if key in court_id.lower():
                return code

        return "FED"  # Default to federal if unknown
