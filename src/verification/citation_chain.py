"""
Citation Verification Chain — 5-Step External Verification Pipeline.

The single most critical safety component in the Cyphergy system.
Verifies legal citations against external data sources (CourtListener, Google Scholar)
to break correlated model failure across all 5 debate agents.

HARD CONSTRAINT (Red Team review — non-negotiable):
    Step 3 (holding verification) MUST read externally-retrieved opinion text.
    Model memory alone is NEVER sufficient for holding verification.
    If external text cannot be retrieved, the citation is marked UNVERIFIED.

CPAA: All external API URLs are loaded from environment variables, never hardcoded.

Usage:
    import asyncio
    from src.verification.citation_chain import CitationVerifier

    cv = CitationVerifier()
    result = asyncio.run(cv.verify(
        "Brown v. Board of Education, 347 U.S. 483 (1954)",
        "Separate educational facilities are inherently unequal"
    ))
    print(result)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.verification.citation_chain")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class VerificationStatus(str, Enum):
    """Outcome status for a citation verification run."""

    VERIFIED = "verified"       # Passed all 5 steps
    UNVERIFIED = "unverified"   # Failed one or more steps
    PARTIAL = "partial"         # Some steps passed, external source unavailable
    ERROR = "error"             # External API error


class VerificationResult(BaseModel):
    """Complete result of running the 5-step verification chain on a citation."""

    citation: str = Field(description="The citation being verified")
    status: VerificationStatus
    steps_passed: list[str] = Field(default_factory=list, description="Steps that passed")
    steps_failed: list[str] = Field(default_factory=list, description="Steps that failed")
    external_source: str | None = Field(default=None, description="Where opinion text was retrieved from")
    holding_summary: str | None = Field(default=None, description="What the case actually holds (from external text)")
    holding_match: bool | None = Field(default=None, description="Does the claimed holding match?")
    good_law: bool | None = Field(default=None, description="Is it still good law?")
    current_version: bool | None = Field(default=None, description="Is it the current version? (for statutes)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score 0.0–1.0")
    details: str = Field(default="", description="Human-readable explanation")


# ---------------------------------------------------------------------------
# Bluebook Citation Patterns
# ---------------------------------------------------------------------------

# Federal reporters
_FEDERAL_REPORTERS: list[str] = [
    r"U\.S\.",
    r"S\.\s*Ct\.",
    r"L\.\s*Ed\.\s*2d",
    r"L\.\s*Ed\.",
    r"F\.\s*4th",
    r"F\.\s*3d",
    r"F\.\s*2d",
    r"F\.",
    r"F\.\s*Supp\.\s*3d",
    r"F\.\s*Supp\.\s*2d",
    r"F\.\s*Supp\.",
    r"F\.\s*App(?:'|')x",
    r"B\.R\.",
]

# Common state reporters
_STATE_REPORTERS: list[str] = [
    r"N\.E\.\s*3d", r"N\.E\.\s*2d", r"N\.E\.",
    r"N\.W\.\s*2d", r"N\.W\.",
    r"S\.E\.\s*2d", r"S\.E\.",
    r"S\.W\.\s*3d", r"S\.W\.\s*2d", r"S\.W\.",
    r"So\.\s*3d", r"So\.\s*2d", r"So\.",
    r"P\.\s*3d", r"P\.\s*2d", r"P\.",
    r"A\.\s*3d", r"A\.\s*2d", r"A\.",
    r"Cal\.\s*Rptr\.\s*3d", r"Cal\.\s*Rptr\.\s*2d", r"Cal\.\s*Rptr\.",
    r"N\.Y\.S\.\s*3d", r"N\.Y\.S\.\s*2d", r"N\.Y\.S\.",
    r"Ill\.\s*Dec\.",
]

# Statutory citation patterns (U.S.C., C.F.R.)
_STATUTE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\d+\s+U\.S\.C\.?\s*§?\s*\d+", re.IGNORECASE),
    re.compile(r"\d+\s+C\.F\.R\.?\s*§?\s*\d+", re.IGNORECASE),
    re.compile(r"\d+\s+U\.S\.C\.A\.?\s*§?\s*\d+", re.IGNORECASE),
    re.compile(r"Pub\.\s*L\.\s*No\.\s*\d+-\d+", re.IGNORECASE),
]

# Combined case citation pattern: <volume> <reporter> <page>
_ALL_REPORTERS = "|".join(_FEDERAL_REPORTERS + _STATE_REPORTERS)
_CASE_CITATION_RE = re.compile(
    rf"\d+\s+(?:{_ALL_REPORTERS})\s+\d+",
    re.IGNORECASE,
)

# Year extraction
_YEAR_RE = re.compile(r"\(.*?(\d{4})\)")


# ---------------------------------------------------------------------------
# CitationVerifier
# ---------------------------------------------------------------------------

class CitationVerifier:
    """
    5-step Citation Verification Chain.

    Steps:
        1. Existence Check — does the citation exist in CourtListener?
        2. Format Verification — does it follow Bluebook citation format?
        3. Holding Verification — does the claimed holding match the external text?
           (HARD CONSTRAINT: external text only, never model memory)
        4. Good Law Check — has the case been overruled or negatively treated?
        5. Currency Check — for statutes, is the version current?
    """

    STEP_NAMES: list[str] = [
        "existence_check",
        "format_verification",
        "holding_verification",
        "good_law_check",
        "currency_check",
    ]

    def __init__(self) -> None:
        self._courtlistener_api_url: str = os.environ.get(
            "COURTLISTENER_API_URL", ""
        ).rstrip("/")
        self._courtlistener_api_key: str | None = os.environ.get(
            "COURTLISTENER_API_KEY"
        )
        self._us_code_api_url: str = os.environ.get(
            "US_CODE_API_URL", ""
        ).rstrip("/")

        if not self._courtlistener_api_url:
            logger.warning(
                "COURTLISTENER_API_URL not set — defaulting to "
                "https://www.courtlistener.com/api/rest/v4. "
                "Set the env var for CPAA compliance."
            )
            self._courtlistener_api_url = "https://www.courtlistener.com/api/rest/v4"

        # Build default headers
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "Cyphergy-Legal-Verification/0.1",
        }
        if self._courtlistener_api_key:
            headers["Authorization"] = f"Token {self._courtlistener_api_key}"

        self._client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=headers,
            follow_redirects=True,
        )

        logger.info(
            "CitationVerifier initialized — CourtListener API: %s",
            self._courtlistener_api_url,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def verify(
        self,
        citation: str,
        claimed_holding: str | None = None,
    ) -> VerificationResult:
        """
        Run the full 5-step verification chain on a single citation.

        Args:
            citation: The legal citation string (e.g. "347 U.S. 483").
            claimed_holding: What the citing document claims the case holds.

        Returns:
            A VerificationResult with step-by-step outcomes.
        """
        logger.info("BEGIN verification for: %s", citation)

        steps_passed: list[str] = []
        steps_failed: list[str] = []
        detail_parts: list[str] = []
        external_source: str | None = None
        holding_summary: str | None = None
        holding_match: bool | None = None
        good_law: bool | None = None
        current_version: bool | None = None
        is_statute = self._is_statute(citation)

        # -- STEP 1: Existence -------------------------------------------
        try:
            exists, opinion_data = await self._step1_exists(citation)
        except Exception as exc:
            logger.error("Step 1 (existence) raised: %s", exc, exc_info=True)
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.ERROR,
                steps_passed=steps_passed,
                steps_failed=["existence_check"],
                confidence=0.0,
                details=f"External API error during existence check: {exc}",
            )

        if exists:
            steps_passed.append("existence_check")
            if opinion_data:
                source_url = opinion_data.get("absolute_url", "")
                if source_url and not source_url.startswith("http"):
                    source_url = f"https://www.courtlistener.com{source_url}"
                external_source = source_url or "CourtListener"
            detail_parts.append("Step 1 PASSED: Citation found in external database.")
            logger.info("Step 1 PASSED — citation exists in CourtListener")
        else:
            steps_failed.append("existence_check")
            detail_parts.append(
                "Step 1 FAILED: Citation not found in CourtListener. "
                "This may indicate a hallucinated or incorrect citation."
            )
            logger.warning("Step 1 FAILED — citation not found externally")
            # Short-circuit: if the citation does not exist, we cannot verify
            # anything else meaningfully.
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.UNVERIFIED,
                steps_passed=steps_passed,
                steps_failed=steps_failed + [
                    s for s in self.STEP_NAMES[1:] if s not in steps_passed
                ],
                external_source=external_source,
                confidence=0.0,
                details=" | ".join(detail_parts) + (
                    " | Steps 2–5 skipped: citation not found."
                ),
            )

        # -- STEP 2: Format Verification ---------------------------------
        fmt_valid, fmt_note = self._step2_format(citation)
        if fmt_valid:
            steps_passed.append("format_verification")
            detail_parts.append(f"Step 2 PASSED: {fmt_note}")
            logger.info("Step 2 PASSED — citation format valid")
        else:
            steps_failed.append("format_verification")
            detail_parts.append(f"Step 2 FAILED: {fmt_note}")
            logger.warning("Step 2 FAILED — citation format issue: %s", fmt_note)

        # -- STEP 3: Holding Verification (HARD CONSTRAINT) ---------------
        if claimed_holding and opinion_data and not is_statute:
            try:
                h_match, h_summary = await self._step3_holding(
                    citation, claimed_holding, opinion_data
                )
                holding_summary = h_summary
                holding_match = h_match
                if h_match:
                    steps_passed.append("holding_verification")
                    detail_parts.append(
                        f"Step 3 PASSED: Claimed holding matches external text. "
                        f"Summary: {h_summary}"
                    )
                    logger.info("Step 3 PASSED — holding verified against external text")
                else:
                    steps_failed.append("holding_verification")
                    detail_parts.append(
                        f"Step 3 FAILED: Claimed holding does NOT match external text. "
                        f"Actual: {h_summary}"
                    )
                    logger.warning(
                        "Step 3 FAILED — holding mismatch. Claimed: %s, Actual: %s",
                        claimed_holding,
                        h_summary,
                    )
            except _ExternalTextUnavailable as exc:
                steps_failed.append("holding_verification")
                holding_match = None
                detail_parts.append(
                    f"Step 3 FAILED (HARD CONSTRAINT): {exc}. "
                    "External opinion text could not be retrieved. "
                    "Model memory is NEVER used for holding verification."
                )
                logger.error(
                    "Step 3 FAILED — external text unavailable, "
                    "hard constraint prevents model-memory fallback: %s",
                    exc,
                )
            except Exception as exc:
                steps_failed.append("holding_verification")
                detail_parts.append(
                    f"Step 3 ERROR: Unexpected error during holding verification: {exc}"
                )
                logger.error("Step 3 ERROR: %s", exc, exc_info=True)
        elif is_statute:
            # Holding verification does not apply to statutes
            steps_passed.append("holding_verification")
            detail_parts.append(
                "Step 3 SKIPPED (statute): Holding verification applies to case law only."
            )
            logger.info("Step 3 SKIPPED — statute citation, not case law")
        elif not claimed_holding:
            steps_failed.append("holding_verification")
            holding_match = None
            detail_parts.append(
                "Step 3 SKIPPED: No claimed holding provided for comparison."
            )
            logger.info("Step 3 SKIPPED — no claimed holding to verify")
        else:
            steps_failed.append("holding_verification")
            detail_parts.append(
                "Step 3 FAILED: Opinion data unavailable for holding comparison."
            )
            logger.warning("Step 3 FAILED — no opinion data")

        # -- STEP 4: Good Law Check --------------------------------------
        if opinion_data and not is_statute:
            try:
                still_good, treatment = await self._step4_good_law(
                    citation, opinion_data
                )
                good_law = still_good
                if still_good:
                    steps_passed.append("good_law_check")
                    detail_parts.append(f"Step 4 PASSED: {treatment}")
                    logger.info("Step 4 PASSED — case is still good law")
                else:
                    steps_failed.append("good_law_check")
                    detail_parts.append(f"Step 4 FAILED: {treatment}")
                    logger.warning("Step 4 FAILED — %s", treatment)
            except Exception as exc:
                steps_failed.append("good_law_check")
                detail_parts.append(f"Step 4 ERROR: {exc}")
                logger.error("Step 4 ERROR: %s", exc, exc_info=True)
        elif is_statute:
            steps_passed.append("good_law_check")
            detail_parts.append(
                "Step 4 SKIPPED (statute): Good-law check applies to case law only."
            )
            logger.info("Step 4 SKIPPED — statute citation")
        else:
            steps_failed.append("good_law_check")
            detail_parts.append("Step 4 SKIPPED: No opinion data for good-law analysis.")
            logger.warning("Step 4 SKIPPED — no opinion data")

        # -- STEP 5: Currency Check (statutes) ----------------------------
        if is_statute:
            try:
                is_current, currency_note = await self._step5_current(citation)
                current_version = is_current
                if is_current:
                    steps_passed.append("currency_check")
                    detail_parts.append(f"Step 5 PASSED: {currency_note}")
                    logger.info("Step 5 PASSED — statute is current")
                else:
                    steps_failed.append("currency_check")
                    detail_parts.append(f"Step 5 FAILED: {currency_note}")
                    logger.warning("Step 5 FAILED — %s", currency_note)
            except Exception as exc:
                steps_failed.append("currency_check")
                detail_parts.append(f"Step 5 ERROR: {exc}")
                logger.error("Step 5 ERROR: %s", exc, exc_info=True)
        else:
            # Currency check applies only to statutes; for case law it auto-passes.
            steps_passed.append("currency_check")
            detail_parts.append(
                "Step 5 SKIPPED (case law): Currency check applies to statutes only."
            )
            logger.info("Step 5 SKIPPED — case law, not a statute")

        # -- Compute final status & confidence ----------------------------
        total_steps = len(self.STEP_NAMES)
        passed_count = len(steps_passed)

        if passed_count == total_steps:
            status = VerificationStatus.VERIFIED
            confidence = 1.0
        elif passed_count == 0:
            status = VerificationStatus.UNVERIFIED
            confidence = 0.0
        else:
            # Check if any critical step failed
            critical_failures = {"existence_check", "holding_verification"} & set(
                steps_failed
            )
            if critical_failures:
                status = VerificationStatus.UNVERIFIED
                confidence = max(0.0, (passed_count / total_steps) * 0.5)
            else:
                status = VerificationStatus.PARTIAL
                confidence = passed_count / total_steps

        result = VerificationResult(
            citation=citation,
            status=status,
            steps_passed=steps_passed,
            steps_failed=steps_failed,
            external_source=external_source,
            holding_summary=holding_summary,
            holding_match=holding_match,
            good_law=good_law,
            current_version=current_version,
            confidence=round(confidence, 3),
            details=" | ".join(detail_parts),
        )

        logger.info(
            "END verification for %s — status=%s, confidence=%.3f, passed=%d/%d",
            citation,
            result.status.value,
            result.confidence,
            passed_count,
            total_steps,
        )

        return result

    async def verify_batch(
        self,
        citations: list[tuple[str, str | None]],
    ) -> list[VerificationResult]:
        """
        Verify multiple citations concurrently.

        Args:
            citations: List of (citation_string, claimed_holding_or_None) tuples.

        Returns:
            List of VerificationResult in the same order as input.
        """
        logger.info("BEGIN batch verification for %d citations", len(citations))
        tasks = [
            self.verify(citation, claimed_holding)
            for citation, claimed_holding in citations
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final: list[VerificationResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Batch item %d (%s) raised: %s",
                    i,
                    citations[i][0],
                    result,
                    exc_info=result,
                )
                final.append(
                    VerificationResult(
                        citation=citations[i][0],
                        status=VerificationStatus.ERROR,
                        confidence=0.0,
                        details=f"Unexpected error: {result}",
                    )
                )
            else:
                final.append(result)

        logger.info("END batch verification — %d results", len(final))
        return final

    async def close(self) -> None:
        """Close the underlying HTTP client. Call when done verifying."""
        await self._client.aclose()
        logger.info("HTTP client closed")

    # ------------------------------------------------------------------
    # STEP 1: Existence Check
    # ------------------------------------------------------------------

    async def _step1_exists(
        self, citation: str
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Search CourtListener for the citation.

        Returns:
            (exists, opinion_data) — opinion_data is the first matching result
            dict from CourtListener, or None if not found.
        """
        opinion_data = await self._search_courtlistener(citation)
        if opinion_data is not None:
            return True, opinion_data

        # Fallback: try a broader search by extracting volume/reporter/page
        simplified = self._extract_volume_reporter_page(citation)
        if simplified and simplified != citation:
            logger.info(
                "Retrying CourtListener with simplified query: %s", simplified
            )
            opinion_data = await self._search_courtlistener(simplified)
            if opinion_data is not None:
                return True, opinion_data

        logger.warning("Citation not found in CourtListener: %s", citation)
        return False, None

    # ------------------------------------------------------------------
    # STEP 2: Format Verification
    # ------------------------------------------------------------------

    def _step2_format(self, citation: str) -> tuple[bool, str]:
        """
        Verify the citation follows Bluebook format.

        Checks for the standard volume-reporter-page pattern for case law,
        or title-code-section pattern for statutes.

        Returns:
            (valid, note)
        """
        stripped = citation.strip()

        # Check statute patterns first
        for pattern in _STATUTE_PATTERNS:
            if pattern.search(stripped):
                return True, f"Valid statutory citation format: {stripped}"

        # Check case citation pattern
        if _CASE_CITATION_RE.search(stripped):
            return True, f"Valid Bluebook case citation format detected."

        # If it has a year in parens and some recognizable structure,
        # give it a partial pass with a note
        if _YEAR_RE.search(stripped) and re.search(r"\d+\s+\S+\s+\d+", stripped):
            return True, (
                "Citation has recognizable structure (volume/reporter/page with year) "
                "but reporter may not be in standard Bluebook list."
            )

        return False, (
            f"Citation does not match standard Bluebook format. "
            f"Expected patterns like '123 F.3d 456 (9th Cir. 2020)' for cases "
            f"or '42 U.S.C. § 1983' for statutes."
        )

    # ------------------------------------------------------------------
    # STEP 3: Holding Verification (HARD CONSTRAINT: external text only)
    # ------------------------------------------------------------------

    async def _step3_holding(
        self,
        citation: str,
        claimed_holding: str | None,
        opinion_data: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Compare the claimed holding against the ACTUAL opinion text retrieved
        from CourtListener.

        HARD CONSTRAINT (Red Team — non-negotiable):
            This method MUST use externally-retrieved opinion text.
            It NEVER falls back to model memory.
            If the opinion text cannot be retrieved from CourtListener,
            it raises _ExternalTextUnavailable.

        Args:
            citation: The citation string.
            claimed_holding: What the citing document claims the case holds.
            opinion_data: The opinion metadata from CourtListener search.

        Returns:
            (matches, actual_holding_summary)

        Raises:
            _ExternalTextUnavailable: If the opinion text cannot be fetched.
        """
        if not claimed_holding:
            raise _ExternalTextUnavailable(
                "No claimed holding provided for comparison."
            )

        # Retrieve the opinion ID from CourtListener data
        opinion_id = self._extract_opinion_id(opinion_data)
        if not opinion_id:
            raise _ExternalTextUnavailable(
                "Could not extract opinion ID from CourtListener search results. "
                "Cannot retrieve opinion text for holding verification."
            )

        # Fetch external opinion text — this is the critical external call
        opinion_text = await self._fetch_opinion_text(opinion_id)

        if not opinion_text or len(opinion_text.strip()) < 100:
            raise _ExternalTextUnavailable(
                f"Opinion text for ID {opinion_id} is empty or too short "
                f"({len(opinion_text.strip()) if opinion_text else 0} chars). "
                "Cannot verify holding without substantive external text. "
                "Model memory will NOT be used as fallback."
            )

        logger.info(
            "Step 3: Retrieved %d chars of external opinion text for %s",
            len(opinion_text),
            citation,
        )

        # Compare the claimed holding against the external text using
        # keyword and semantic overlap analysis.
        # We do NOT use an LLM here to avoid model-memory contamination.
        # Instead we check if key phrases from the claimed holding appear
        # in the actual opinion text.
        matches, summary = self._compare_holding_to_text(
            claimed_holding, opinion_text, citation
        )

        return matches, summary

    def _compare_holding_to_text(
        self,
        claimed_holding: str,
        opinion_text: str,
        citation: str,
    ) -> tuple[bool, str]:
        """
        Compare a claimed holding against externally-retrieved opinion text
        using keyword overlap analysis.

        This method deliberately avoids using an LLM for the comparison
        to prevent model-memory contamination. It uses text-matching heuristics
        on the EXTERNAL opinion text.

        Args:
            claimed_holding: The holding claimed by the citing document.
            opinion_text: Full text of the opinion from CourtListener.
            citation: The citation string (for logging).

        Returns:
            (matches, summary_of_actual_holding)
        """
        # Normalize texts
        claimed_lower = claimed_holding.lower().strip()
        opinion_lower = opinion_text.lower()

        # Extract meaningful phrases from the claimed holding
        # Remove common legal filler words for better signal
        filler_words = {
            "the", "a", "an", "of", "in", "to", "for", "and", "or", "that",
            "this", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can", "must",
            "not", "no", "its", "it", "with", "by", "from", "as", "at",
            "on", "but", "if", "into", "through", "during", "before",
            "after", "above", "below", "between", "under", "upon",
            "court", "held", "holding", "case", "opinion", "v.",
        }

        claimed_words = [
            w for w in re.findall(r"[a-z]+", claimed_lower)
            if w not in filler_words and len(w) > 2
        ]

        if not claimed_words:
            return False, "Could not extract meaningful terms from claimed holding."

        # Check what fraction of meaningful claimed-holding words appear
        # in the opinion text
        found_words: list[str] = []
        missing_words: list[str] = []

        for word in claimed_words:
            if word in opinion_lower:
                found_words.append(word)
            else:
                missing_words.append(word)

        word_match_ratio = len(found_words) / len(claimed_words) if claimed_words else 0

        # Also look for multi-word phrase matches (2-grams and 3-grams)
        # from the claimed holding in the opinion
        claimed_clean = re.sub(r"[^\w\s]", "", claimed_lower)
        claimed_tokens = claimed_clean.split()
        bigrams = [
            " ".join(claimed_tokens[i : i + 2])
            for i in range(len(claimed_tokens) - 1)
        ]
        trigrams = [
            " ".join(claimed_tokens[i : i + 3])
            for i in range(len(claimed_tokens) - 2)
        ]

        opinion_clean = re.sub(r"[^\w\s]", "", opinion_lower)
        bigram_matches = sum(1 for bg in bigrams if bg in opinion_clean)
        trigram_matches = sum(1 for tg in trigrams if tg in opinion_clean)

        bigram_ratio = bigram_matches / len(bigrams) if bigrams else 0
        trigram_ratio = trigram_matches / len(trigrams) if trigrams else 0

        # Weighted score: trigrams matter more than bigrams which matter
        # more than individual words
        composite_score = (
            word_match_ratio * 0.3
            + bigram_ratio * 0.35
            + trigram_ratio * 0.35
        )

        # Extract a summary from the opinion text (first ~500 chars that
        # contain the most matches)
        summary = self._extract_relevant_passage(opinion_text, claimed_words)

        # Threshold: 0.40 composite score indicates the holding is
        # substantively present in the opinion
        threshold = 0.40
        matches = composite_score >= threshold

        logger.info(
            "Step 3 comparison for %s — word_ratio=%.2f, bigram_ratio=%.2f, "
            "trigram_ratio=%.2f, composite=%.2f, threshold=%.2f, match=%s",
            citation,
            word_match_ratio,
            bigram_ratio,
            trigram_ratio,
            composite_score,
            threshold,
            matches,
        )

        detail_prefix = "MATCH" if matches else "MISMATCH"
        full_summary = (
            f"{detail_prefix} (score={composite_score:.2f}, "
            f"threshold={threshold}). "
            f"Key terms found: {found_words[:10]}. "
            f"Key terms missing: {missing_words[:10]}. "
            f"Relevant passage: {summary}"
        )

        return matches, full_summary

    @staticmethod
    def _extract_relevant_passage(
        opinion_text: str, keywords: list[str], max_length: int = 500
    ) -> str:
        """
        Extract the most relevant passage from the opinion text based on
        keyword density. Returns up to max_length characters.
        """
        if len(opinion_text) <= max_length:
            return opinion_text.strip()

        # Sliding window approach: find the window with the most keyword hits
        window_size = max_length
        text_lower = opinion_text.lower()
        best_start = 0
        best_count = 0

        # Sample at intervals to avoid O(n*k) complexity on very long texts
        step = max(1, len(text_lower) // 200)

        for start in range(0, len(text_lower) - window_size, step):
            window = text_lower[start : start + window_size]
            count = sum(1 for kw in keywords if kw in window)
            if count > best_count:
                best_count = count
                best_start = start

        passage = opinion_text[best_start : best_start + window_size].strip()

        # Try to start at a sentence boundary
        first_period = passage.find(". ")
        if 0 < first_period < 80:
            passage = passage[first_period + 2 :]

        # Try to end at a sentence boundary
        last_period = passage.rfind(". ")
        if last_period > len(passage) - 80:
            passage = passage[: last_period + 1]

        return passage

    # ------------------------------------------------------------------
    # STEP 4: Good Law Check
    # ------------------------------------------------------------------

    async def _step4_good_law(
        self, citation: str, opinion_data: dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Check whether the case has been overruled, reversed, or received
        significant negative treatment by looking at citing opinions.

        Uses CourtListener's citing-opinions data.

        Returns:
            (still_good_law, treatment_summary)
        """
        cluster_id = self._extract_cluster_id(opinion_data)
        if not cluster_id:
            return True, (
                "Good-law check inconclusive: could not extract cluster ID. "
                "No negative treatment detected in available data."
            )

        # Fetch citing opinions from CourtListener
        url = f"{self._courtlistener_api_url}/opinions/"
        params: dict[str, Any] = {
            "cites": cluster_id,
            "fields": "plain_text,download_url,case_name",
            "page_size": 20,
            "order_by": "-date_created",
        }

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            # API may return 4xx for various reasons — do not crash
            logger.warning(
                "Step 4: CourtListener citing-opinions returned %d: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return True, (
                f"Good-law check inconclusive: CourtListener returned "
                f"HTTP {exc.response.status_code}. "
                "No negative treatment confirmed."
            )
        except httpx.HTTPError as exc:
            logger.warning("Step 4: HTTP error fetching citing opinions: %s", exc)
            return True, (
                "Good-law check inconclusive due to API error. "
                "No negative treatment confirmed."
            )

        results = data.get("results", [])
        if not results:
            return True, (
                "No citing opinions found in CourtListener. "
                "Case has not been negatively treated (or citing data is unavailable)."
            )

        # Look for negative treatment signals in citing opinion text
        negative_signals = [
            "overruled", "overrule", "reversed", "reverse",
            "abrogated", "abrogate", "vacated", "vacate",
            "no longer good law", "no longer controlling",
            "expressly overruled", "implicitly overruled",
            "superseded by statute",
        ]

        negative_hits: list[str] = []
        total_checked = 0

        for citing in results:
            citing_text = (
                citing.get("plain_text", "") or ""
            ).lower()
            citing_case = citing.get("case_name", "Unknown")

            if not citing_text:
                continue

            total_checked += 1
            for signal in negative_signals:
                if signal in citing_text:
                    negative_hits.append(
                        f"{citing_case} contains '{signal}'"
                    )
                    break  # One signal per citing case is enough

        if negative_hits:
            summary = (
                f"POTENTIAL NEGATIVE TREATMENT detected in {len(negative_hits)} "
                f"of {total_checked} citing opinions: "
                + "; ".join(negative_hits[:5])
            )
            logger.warning("Step 4: %s", summary)
            return False, summary

        return True, (
            f"No negative treatment detected across {total_checked} citing "
            f"opinions checked."
        )

    # ------------------------------------------------------------------
    # STEP 5: Currency Check (statutes)
    # ------------------------------------------------------------------

    async def _step5_current(self, citation: str) -> tuple[bool, str]:
        """
        For statutory citations, check if the statute version is current.

        Queries the US Code API (if configured) or performs a basic
        CourtListener search for recent amendments.

        Returns:
            (is_current, notes)
        """
        if not self._is_statute(citation):
            return True, "Not a statutory citation — currency check not applicable."

        # Extract title and section for US Code lookup
        usc_match = re.search(
            r"(\d+)\s+U\.S\.C\.?\s*§?\s*(\d+[a-z]*(?:-\d+)?)",
            citation,
            re.IGNORECASE,
        )

        if usc_match and self._us_code_api_url:
            title = usc_match.group(1)
            section = usc_match.group(2)

            url = f"{self._us_code_api_url}/title/{title}/section/{section}"
            try:
                response = await self._client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    # Check for amendment/repeal indicators
                    status = data.get("status", "unknown")
                    if status in ("current", "active"):
                        return True, (
                            f"Statute {title} U.S.C. § {section} is current "
                            f"per US Code API."
                        )
                    elif status in ("repealed", "superseded"):
                        return False, (
                            f"Statute {title} U.S.C. § {section} has been "
                            f"{status} per US Code API."
                        )
                    else:
                        return True, (
                            f"US Code API returned status '{status}' for "
                            f"{title} U.S.C. § {section}. "
                            "Treating as current (verify manually)."
                        )
                else:
                    logger.warning(
                        "US Code API returned %d for %s",
                        response.status_code,
                        citation,
                    )
            except httpx.HTTPError as exc:
                logger.warning("US Code API error: %s", exc)

        # Fallback: search CourtListener for recent cases mentioning the
        # statute being repealed or amended
        try:
            query = f'"{citation}" (repealed OR amended OR superseded)'
            params: dict[str, Any] = {
                "q": query,
                "type": "o",
                "order_by": "score desc",
                "stat_Precedential": "on",
            }
            response = await self._client.get(
                f"{self._courtlistener_api_url}/search/",
                params=params,
            )
            if response.status_code == 200:
                data = response.json()
                count = data.get("count", 0)
                if count > 0:
                    return True, (
                        f"Statute appears in {count} CourtListener result(s) "
                        f"mentioning repeal/amendment. Manual review recommended."
                    )
                else:
                    return True, (
                        "No CourtListener results indicate repeal or amendment. "
                        "Statute presumed current."
                    )
        except httpx.HTTPError as exc:
            logger.warning("Step 5 fallback search error: %s", exc)

        return True, (
            "Currency check inconclusive — no US Code API configured and "
            "CourtListener fallback unavailable. Statute presumed current "
            "pending manual verification."
        )

    # ------------------------------------------------------------------
    # CourtListener API Helpers
    # ------------------------------------------------------------------

    async def _search_courtlistener(
        self, query: str
    ) -> dict[str, Any] | None:
        """
        Search CourtListener for the given citation query.

        Makes a real HTTP GET to the CourtListener search API.
        Handles rate limiting, errors, and timeouts gracefully.

        Args:
            query: The search string (citation or simplified citation).

        Returns:
            The first matching opinion result dict, or None.
        """
        url = f"{self._courtlistener_api_url}/search/"
        params: dict[str, Any] = {
            "q": query,
            "type": "o",
            "order_by": "score desc",
            "stat_Precedential": "on",
        }

        logger.debug("CourtListener search: GET %s params=%s", url, params)

        try:
            response = await self._client.get(url, params=params)
        except httpx.TimeoutException:
            logger.error(
                "CourtListener search timed out for query: %s", query
            )
            return None
        except httpx.HTTPError as exc:
            logger.error(
                "CourtListener search HTTP error for query '%s': %s",
                query,
                exc,
            )
            return None

        if response.status_code == 429:
            logger.warning(
                "CourtListener rate limit hit — consider adding "
                "COURTLISTENER_API_KEY for higher limits."
            )
            return None

        if response.status_code != 200:
            logger.warning(
                "CourtListener returned HTTP %d for query '%s': %s",
                response.status_code,
                query,
                response.text[:200],
            )
            return None

        try:
            data = response.json()
        except Exception as exc:
            logger.error("Failed to parse CourtListener JSON: %s", exc)
            return None

        results = data.get("results", [])
        if not results:
            logger.debug("CourtListener returned 0 results for: %s", query)
            return None

        # Return the top-scoring result
        top = results[0]
        logger.info(
            "CourtListener found: %s (score=%s)",
            top.get("caseName", top.get("case_name", "Unknown")),
            top.get("score", "N/A"),
        )
        return top

    async def _fetch_opinion_text(self, opinion_id: str) -> str | None:
        """
        Fetch the full opinion text from CourtListener by opinion ID.

        This is the critical external data retrieval that Step 3 depends on.
        The returned text is EXTERNAL — not from model memory.

        Args:
            opinion_id: The CourtListener opinion ID (numeric string).

        Returns:
            The plain text of the opinion, or None if unavailable.
        """
        url = f"{self._courtlistener_api_url}/opinions/{opinion_id}/"

        logger.debug("Fetching opinion text: GET %s", url)

        try:
            response = await self._client.get(url)
        except httpx.TimeoutException:
            logger.error(
                "Timeout fetching opinion text for ID %s", opinion_id
            )
            return None
        except httpx.HTTPError as exc:
            logger.error(
                "HTTP error fetching opinion text for ID %s: %s",
                opinion_id,
                exc,
            )
            return None

        if response.status_code != 200:
            logger.warning(
                "CourtListener opinion endpoint returned %d for ID %s: %s",
                response.status_code,
                opinion_id,
                response.text[:200],
            )
            return None

        try:
            data = response.json()
        except Exception as exc:
            logger.error(
                "Failed to parse opinion JSON for ID %s: %s",
                opinion_id,
                exc,
            )
            return None

        # Try plain_text first, then html_with_citations, then html
        plain_text = data.get("plain_text", "")
        if plain_text and len(plain_text.strip()) > 100:
            logger.info(
                "Retrieved %d chars of plain_text for opinion %s",
                len(plain_text),
                opinion_id,
            )
            return plain_text

        # Fall back to HTML — strip tags for text comparison
        html_text = data.get("html_with_citations", "") or data.get("html", "")
        if html_text:
            stripped = self._strip_html(html_text)
            if len(stripped.strip()) > 100:
                logger.info(
                    "Retrieved %d chars of HTML text (stripped) for opinion %s",
                    len(stripped),
                    opinion_id,
                )
                return stripped

        # Try the cluster's opinions if this opinion object is sparse
        cluster_url = data.get("cluster", "")
        if cluster_url:
            cluster_text = await self._fetch_cluster_text(cluster_url)
            if cluster_text:
                return cluster_text

        logger.warning(
            "No substantive text found for opinion %s. "
            "Available fields: %s",
            opinion_id,
            list(data.keys()),
        )
        return None

    async def _fetch_cluster_text(self, cluster_url: str) -> str | None:
        """
        Fetch opinion text from the cluster endpoint as a fallback.

        Sometimes the individual opinion has sparse text but the cluster
        has other sub-opinions with content.
        """
        try:
            if not cluster_url.startswith("http"):
                cluster_url = f"{self._courtlistener_api_url}{cluster_url}"

            response = await self._client.get(cluster_url)
            if response.status_code != 200:
                return None

            data = response.json()

            # Check sub_opinions
            sub_opinions = data.get("sub_opinions", [])
            for sub_url in sub_opinions:
                if isinstance(sub_url, str):
                    if not sub_url.startswith("http"):
                        sub_url = f"https://www.courtlistener.com{sub_url}"
                    try:
                        sub_resp = await self._client.get(sub_url)
                        if sub_resp.status_code == 200:
                            sub_data = sub_resp.json()
                            text = sub_data.get("plain_text", "")
                            if text and len(text.strip()) > 100:
                                return text
                            html = sub_data.get("html_with_citations", "") or sub_data.get("html", "")
                            if html:
                                stripped = self._strip_html(html)
                                if len(stripped.strip()) > 100:
                                    return stripped
                    except httpx.HTTPError:
                        continue
        except Exception as exc:
            logger.debug("Cluster text fetch failed: %s", exc)

        return None

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def _extract_opinion_id(self, opinion_data: dict[str, Any]) -> str | None:
        """
        Extract a usable opinion ID from CourtListener search result data.

        CourtListener search results may have different structures depending
        on the API version. This method tries several extraction strategies.
        """
        # Direct ID field
        for key in ("id", "pk", "opinion_id"):
            val = opinion_data.get(key)
            if val is not None:
                return str(val)

        # From absolute_url like /opinion/123456/case-name/
        abs_url = opinion_data.get("absolute_url", "")
        if abs_url:
            match = re.search(r"/opinion/(\d+)/", abs_url)
            if match:
                return match.group(1)

        # From cluster_id — use it to find opinions
        cluster_id = opinion_data.get("cluster_id") or opinion_data.get("cluster")
        if cluster_id:
            # We can use the cluster ID to look up opinions
            return str(cluster_id)

        # CourtListener v3 search API returns 'citeCount', 'cluster_id', etc.
        # in its search results. The 'id' is usually the cluster ID.
        for key in ("sibling_ids", "sub_opinions"):
            ids = opinion_data.get(key)
            if isinstance(ids, list) and ids:
                return str(ids[0])

        logger.warning(
            "Could not extract opinion ID. Available keys: %s",
            list(opinion_data.keys()),
        )
        return None

    def _extract_cluster_id(self, opinion_data: dict[str, Any]) -> str | None:
        """Extract the cluster ID from opinion data for citing-opinions lookup."""
        for key in ("cluster_id", "cluster", "id", "pk"):
            val = opinion_data.get(key)
            if val is not None:
                return str(val)

        abs_url = opinion_data.get("absolute_url", "")
        if abs_url:
            match = re.search(r"/opinion/(\d+)/", abs_url)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _extract_volume_reporter_page(citation: str) -> str | None:
        """
        Extract the volume-reporter-page core from a full citation string.

        Example: "Brown v. Board of Education, 347 U.S. 483 (1954)"
                 -> "347 U.S. 483"
        """
        match = _CASE_CITATION_RE.search(citation)
        if match:
            return match.group(0)
        return None

    @staticmethod
    def _is_statute(citation: str) -> bool:
        """Check if the citation is a statutory citation (U.S.C., C.F.R., etc.)."""
        return any(p.search(citation) for p in _STATUTE_PATTERNS)

    @staticmethod
    def _strip_html(html: str) -> str:
        """Remove HTML tags from a string, keeping text content."""
        # Remove script and style blocks entirely
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove all tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode common HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        text = text.replace("&nbsp;", " ")
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# ---------------------------------------------------------------------------
# Internal Exceptions
# ---------------------------------------------------------------------------

class _ExternalTextUnavailable(Exception):
    """
    Raised when external opinion text cannot be retrieved for Step 3.

    This is a SAFETY exception — it enforces the hard constraint that
    holding verification NEVER falls back to model memory.
    """

    pass
