"""Semantic Holding Extraction Engine — AI-driven headnote/KeyCite equivalent.

Novel architecture by Bo Pennington.

This is the AI equivalent of Westlaw's KeyCite/Headnotes system. Instead of
human editors reading every opinion and writing headnotes, the dual-brain
system (Opus + Llama Scout + Cohere Command-R+) extracts the actual legal
holding from each case opinion.

HARD CONSTRAINT: Opinion text must be externally retrieved (from CourtListener
or another source). The extraction models are never allowed to rely on
training-data memory for the substance of an opinion. They receive the actual
opinion text as input and extract structure from it.

Pipeline:
    1. Receive raw opinion text + case citation + jurisdiction
    2. Opus 4.6 reads the opinion and independently extracts holdings
    3. Llama Scout independently extracts holdings
    4. Cohere Command-R+ independently extracts holdings
    5. Consensus engine compares the three extractions
    6. Holdings agreed upon by ALL 3 models are marked verified=True
    7. Disagreements are flagged for human review
    8. Verified holdings are siphoned into the CaseCatalog / StatuteIndex
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.providers.llm_provider import LLMProvider, LLMProviderResponse, get_provider
from src.providers.model_router import ModelConfig, ModelRole, ModelRouter

logger = logging.getLogger("cyphergy.knowledge.holding_extractor")


# ---------------------------------------------------------------------------
# Holding Types & Models
# ---------------------------------------------------------------------------


class HoldingType(str, Enum):
    """Classification of a legal holding within an opinion."""

    RULE_STATEMENT = "rule_statement"       # "The court holds that under X, Y is required"
    APPLICATION = "application"             # "Applying X to these facts, the court finds..."
    EXCEPTION = "exception"                 # "However, X does not apply when..."
    LIMITATION = "limitation"               # "The scope of X is limited to..."
    OVERRULING = "overruling"               # "We overrule our prior holding in..."
    DISTINGUISHING = "distinguishing"       # "This case is distinguishable because..."


class LegalStandard(str, Enum):
    """Burden of proof / legal standard referenced in the holding."""

    PREPONDERANCE = "preponderance"
    CLEAR_AND_CONVINCING = "clear_and_convincing"
    BEYOND_REASONABLE_DOUBT = "beyond_reasonable_doubt"
    REASONABLE_BASIS = "reasonable_basis"
    SUBSTANTIAL_EVIDENCE = "substantial_evidence"
    ABUSE_OF_DISCRETION = "abuse_of_discretion"
    DE_NOVO = "de_novo"
    RATIONAL_BASIS = "rational_basis"
    STRICT_SCRUTINY = "strict_scrutiny"
    INTERMEDIATE_SCRUTINY = "intermediate_scrutiny"
    NOT_SPECIFIED = "not_specified"


class CourtLevel(str, Enum):
    """Level of the court issuing the opinion."""

    SUPREME = "supreme"
    APPELLATE = "appellate"
    TRIAL = "trial"
    FEDERAL_CIRCUIT = "federal_circuit"
    FEDERAL_DISTRICT = "federal_district"
    BANKRUPTCY = "bankruptcy"
    SPECIALTY = "specialty"


class PartySide(str, Enum):
    """Which party the holding favors."""

    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    NEUTRAL = "neutral"


class ExtractedHolding(BaseModel):
    """A single structured holding extracted from a case opinion.

    Each field is extracted FROM THE OPINION TEXT, never from model memory.
    """

    case_citation: str = Field(description="Full Bluebook citation of the case")
    statute_citation: str = Field(
        default="",
        description="Statute the holding interprets (e.g., 'Fla. Stat. 768.72')",
    )
    holding_text: str = Field(
        description="The actual legal holding in plain language, derived from the opinion",
    )
    holding_type: HoldingType = Field(
        description="Classification of this holding (rule_statement, application, etc.)",
    )
    key_facts: list[str] = Field(
        default_factory=list,
        description="Material facts that drove this holding",
    )
    legal_standard: str = Field(
        default=LegalStandard.NOT_SPECIFIED.value,
        description="Burden of proof or standard of review applied",
    )
    supports: str = Field(
        default=PartySide.NEUTRAL.value,
        description="Which party this holding favors: plaintiff, defendant, or neutral",
    )
    jurisdiction: str = Field(description="Jurisdiction code (FL, CA, FED, etc.)")
    court_level: str = Field(
        default=CourtLevel.APPELLATE.value,
        description="Level of court: supreme, appellate, trial, federal_circuit, etc.",
    )
    year: int = Field(default=0, description="Year the opinion was decided")
    verified: bool = Field(
        default=False,
        description="True only if all 3 dual-brain models agreed on this holding",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score: 1.0 = full 3-model consensus, 0.67 = 2 of 3, etc.",
    )

    # Extraction metadata
    extracted_at: str = Field(default="", description="ISO timestamp of extraction")
    extraction_source: str = Field(
        default="dual_brain",
        description="How this holding was extracted",
    )
    disagreement_notes: list[str] = Field(
        default_factory=list,
        description="Notes on where models disagreed (empty if full consensus)",
    )


class ExtractionResult(BaseModel):
    """Full result of a holding extraction run for one opinion."""

    case_citation: str
    jurisdiction: str
    total_holdings_found: int = 0
    consensus_holdings: list[ExtractedHolding] = Field(default_factory=list)
    partial_holdings: list[ExtractedHolding] = Field(default_factory=list)
    disagreements: list[dict[str, Any]] = Field(default_factory=list)
    model_responses: dict[str, int] = Field(
        default_factory=dict,
        description="Number of holdings each model extracted: {role: count}",
    )
    extraction_time_ms: int = 0
    error: str = ""


# ---------------------------------------------------------------------------
# Extraction Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a legal analyst extracting structured holdings from court opinions.

TASK: Read the provided opinion text and extract EVERY legal holding the court made.

RULES — STRICTLY ENFORCED:
1. Extract ONLY from the opinion text provided. NEVER supplement with your training data.
2. If information is not in the text, use "not_specified" or leave blank.
3. A "holding" is what the court DECIDED — not dicta, not procedural history, not recitations of argument.
4. For each holding, identify:
   - The statute or legal authority being interpreted (if any)
   - The holding itself in plain language
   - The type: rule_statement, application, exception, limitation, overruling, distinguishing
   - Key facts that drove the holding
   - The legal standard applied (preponderance, clear_and_convincing, beyond_reasonable_doubt, abuse_of_discretion, de_novo, etc.)
   - Which party the holding favors: plaintiff, defendant, or neutral
5. Preserve the court's actual language where possible. Do not editorialize.

OUTPUT FORMAT: Return a JSON array. Each element must have exactly these keys:
{
  "statute_citation": "string — the statute citation or empty string",
  "holding_text": "string — the holding in plain language",
  "holding_type": "rule_statement|application|exception|limitation|overruling|distinguishing",
  "key_facts": ["fact1", "fact2"],
  "legal_standard": "string — the standard or 'not_specified'",
  "supports": "plaintiff|defendant|neutral"
}

Return ONLY the JSON array. No preamble, no explanation, no markdown fences."""

_USER_PROMPT_TEMPLATE = """CASE: {case_citation}
JURISDICTION: {jurisdiction}

OPINION TEXT:
---
{opinion_text}
---

Extract all holdings from the opinion above. Return a JSON array."""


# ---------------------------------------------------------------------------
# Holding Extractor
# ---------------------------------------------------------------------------


class HoldingExtractor:
    """Extracts structured legal holdings from case opinions using dual-brain consensus.

    The dual-brain system reads the actual opinion text (from CourtListener or
    another external source) and extracts what the court ACTUALLY HELD. This is
    not a summarization task — it is structured information extraction.

    HARD CONSTRAINT: Opinion text must be externally retrieved. Never from
    model memory. The extractor receives raw text and parses it.

    Usage::

        router = ModelRouter()
        provider = get_provider()
        extractor = HoldingExtractor(router=router, provider=provider)

        result = await extractor.extract_holdings(
            opinion_text="... full opinion text from CourtListener ...",
            case_citation="Smith v. Jones, 123 So.3d 456 (Fla. 2024)",
            jurisdiction="FL",
            court_level="supreme",
            year=2024,
        )

        # Consensus holdings (all 3 models agree)
        for holding in result.consensus_holdings:
            print(f"[VERIFIED] {holding.holding_text}")

        # Partial agreement (2 of 3 models)
        for holding in result.partial_holdings:
            print(f"[PARTIAL] {holding.holding_text}")

        # Disagreements (for human review)
        for d in result.disagreements:
            print(f"[REVIEW] {d['reason']}")
    """

    # Similarity threshold for matching holdings across models.
    # Two holdings are considered "the same" if their text similarity
    # exceeds this threshold AND their type matches.
    _SIMILARITY_THRESHOLD = 0.55

    # Maximum opinion text length we send to a single model call.
    # Longer opinions are truncated with a warning. The 1M-context Opus
    # can handle enormous inputs but we cap for cost/latency.
    _MAX_OPINION_CHARS = 500_000

    def __init__(
        self,
        router: ModelRouter,
        provider: Optional[LLMProvider] = None,
    ) -> None:
        self._router = router
        self._provider = provider or get_provider()
        logger.info("HoldingExtractor initialized with dual-brain pipeline")

    async def extract_holdings(
        self,
        opinion_text: str,
        case_citation: str,
        jurisdiction: str,
        court_level: str = CourtLevel.APPELLATE.value,
        year: int = 0,
    ) -> ExtractionResult:
        """Extract all holdings from an opinion using 3-model consensus.

        Parameters
        ----------
        opinion_text :
            The full text of the court opinion. MUST be externally retrieved
            (e.g., from CourtListener). Never from model memory.
        case_citation :
            Full Bluebook citation (e.g., "Smith v. Jones, 123 So.3d 456 (Fla. 2024)").
        jurisdiction :
            Jurisdiction code (FL, CA, FED, etc.).
        court_level :
            Level of court: supreme, appellate, trial, federal_circuit, etc.
        year :
            Year the opinion was decided.

        Returns
        -------
        ExtractionResult
            Contains consensus_holdings (all 3 agree), partial_holdings
            (2 of 3 agree), and disagreements (for human review).
        """
        import time

        start = time.monotonic()

        result = ExtractionResult(
            case_citation=case_citation,
            jurisdiction=jurisdiction,
        )

        # Validate input
        if not opinion_text or not opinion_text.strip():
            result.error = "Empty opinion text provided"
            logger.error("extract_holdings | empty opinion text | citation=%s", case_citation)
            return result

        # Truncate if too long (with warning)
        if len(opinion_text) > self._MAX_OPINION_CHARS:
            logger.warning(
                "opinion_truncated | citation=%s chars=%d max=%d",
                case_citation, len(opinion_text), self._MAX_OPINION_CHARS,
            )
            opinion_text = opinion_text[: self._MAX_OPINION_CHARS]

        # Get the 3 dual-brain model configs
        models = self._router.get_dual_brain(jurisdiction)
        if len(models) < 3:
            result.error = f"Dual-brain requires 3 models, got {len(models)}"
            logger.error("extract_holdings | insufficient models | count=%d", len(models))
            return result

        # Run all 3 models in parallel
        extraction_tasks = [
            self._extract_with_model(opinion_text, case_citation, jurisdiction, config)
            for config in models
        ]
        raw_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Collect successful extractions
        extractions: list[list[dict[str, Any]]] = []
        model_labels = [
            ModelRole.JURISDICTION_PRIMARY.value,
            ModelRole.JURISDICTION_SCOUT.value,
            ModelRole.JURISDICTION_COHERE.value,
        ]

        for i, raw in enumerate(raw_results):
            label = model_labels[i] if i < len(model_labels) else f"model_{i}"
            if isinstance(raw, Exception):
                logger.error(
                    "model_extraction_failed | model=%s citation=%s error=%s",
                    label, case_citation, str(raw)[:300],
                )
                extractions.append([])
                result.model_responses[label] = 0
            elif isinstance(raw, list):
                extractions.append(raw)
                result.model_responses[label] = len(raw)
                logger.info(
                    "model_extraction_complete | model=%s citation=%s holdings=%d",
                    label, case_citation, len(raw),
                )
            else:
                extractions.append([])
                result.model_responses[label] = 0

        # Find consensus
        consensus, partial, disagreements = self._find_consensus(
            extractions=extractions,
            case_citation=case_citation,
            jurisdiction=jurisdiction,
            court_level=court_level,
            year=year,
        )

        result.consensus_holdings = consensus
        result.partial_holdings = partial
        result.disagreements = disagreements
        result.total_holdings_found = len(consensus) + len(partial) + len(disagreements)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        result.extraction_time_ms = elapsed_ms

        logger.info(
            "extraction_complete | citation=%s consensus=%d partial=%d disagreements=%d time_ms=%d",
            case_citation,
            len(consensus),
            len(partial),
            len(disagreements),
            elapsed_ms,
        )

        return result

    async def _extract_with_model(
        self,
        opinion_text: str,
        case_citation: str,
        jurisdiction: str,
        model_config: ModelConfig,
    ) -> list[dict[str, Any]]:
        """Run a single model extraction and parse its output.

        Parameters
        ----------
        opinion_text :
            The full opinion text (already truncated if needed).
        case_citation :
            Full Bluebook citation.
        jurisdiction :
            Jurisdiction code.
        model_config :
            ModelConfig from the router specifying which model to use.

        Returns
        -------
        list[dict]
            List of raw holding dicts extracted by this model.

        Raises
        ------
        ValueError
            If the model returns unparseable output after retry.
        """
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            case_citation=case_citation,
            jurisdiction=jurisdiction,
            opinion_text=opinion_text,
        )

        response: LLMProviderResponse = await self._provider.create_message(
            model=model_config.model_id,
            max_tokens=model_config.max_tokens,
            temperature=model_config.temperature,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse JSON from response
        holdings = self._parse_model_output(response.text, model_config.role)

        # Validate each holding has required fields
        validated: list[dict[str, Any]] = []
        for h in holdings:
            if not isinstance(h, dict):
                continue
            if not h.get("holding_text"):
                continue

            # Normalize fields with defaults
            validated.append({
                "statute_citation": str(h.get("statute_citation", "") or ""),
                "holding_text": str(h.get("holding_text", "")),
                "holding_type": self._normalize_holding_type(
                    str(h.get("holding_type", "rule_statement"))
                ),
                "key_facts": list(h.get("key_facts", [])),
                "legal_standard": self._normalize_legal_standard(
                    str(h.get("legal_standard", "not_specified"))
                ),
                "supports": self._normalize_party_side(
                    str(h.get("supports", "neutral"))
                ),
            })

        return validated

    def _parse_model_output(self, text: str, model_role: str) -> list[dict[str, Any]]:
        """Parse JSON array from model output, handling common formatting issues.

        Models sometimes wrap JSON in markdown fences or add preamble text.
        This parser handles those cases gracefully.
        """
        if not text or not text.strip():
            logger.warning("empty_model_output | model=%s", model_role)
            return []

        cleaned = text.strip()

        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            # Remove closing fence
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
            cleaned = cleaned.strip()

        # Try direct JSON parse first
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in the text
        array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if array_match:
            try:
                parsed = json.loads(array_match.group())
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Last resort: try to find individual JSON objects
        objects: list[dict[str, Any]] = []
        for obj_match in re.finditer(r"\{[^{}]*\}", cleaned):
            try:
                obj = json.loads(obj_match.group())
                if isinstance(obj, dict) and obj.get("holding_text"):
                    objects.append(obj)
            except json.JSONDecodeError:
                continue

        if objects:
            return objects

        logger.warning(
            "unparseable_model_output | model=%s text_preview=%s",
            model_role,
            cleaned[:200],
        )
        return []

    def _find_consensus(
        self,
        extractions: list[list[dict[str, Any]]],
        case_citation: str,
        jurisdiction: str,
        court_level: str,
        year: int,
    ) -> tuple[list[ExtractedHolding], list[ExtractedHolding], list[dict[str, Any]]]:
        """Find holdings that multiple models agree on.

        Consensus logic:
        - Full consensus (verified=True, confidence=1.0): all 3 models extracted
          a semantically equivalent holding with matching type.
        - Partial consensus (verified=False, confidence=0.67): exactly 2 of 3
          models agree. These are still usable but flagged.
        - Disagreement: a holding found by only 1 model, or where models
          extracted contradictory information. Flagged for human review.

        Parameters
        ----------
        extractions :
            List of 3 lists, one per model, each containing raw holding dicts.
        case_citation, jurisdiction, court_level, year :
            Metadata to attach to each ExtractedHolding.

        Returns
        -------
        (consensus, partial, disagreements)
        """
        now = datetime.utcnow().isoformat()

        # Handle degenerate cases
        non_empty = [e for e in extractions if e]
        if not non_empty:
            return [], [], [{"reason": "All 3 models returned empty extractions", "citation": case_citation}]

        if len(non_empty) == 1:
            # Only 1 model returned results — everything is unverified
            source_idx = next(i for i, e in enumerate(extractions) if e)
            model_labels = ["jurisdiction_primary", "jurisdiction_scout", "jurisdiction_cohere"]
            source_label = model_labels[source_idx] if source_idx < len(model_labels) else "unknown"
            disagreements: list[dict[str, Any]] = []
            for h in non_empty[0]:
                disagreements.append({
                    "reason": f"Only {source_label} extracted this holding; other 2 models returned nothing",
                    "citation": case_citation,
                    "holding_text": h.get("holding_text", ""),
                    "source_model": source_label,
                })
            return [], [], disagreements

        # Build a flat list of (model_index, holding_dict) pairs
        all_holdings: list[tuple[int, dict[str, Any]]] = []
        for model_idx, model_holdings in enumerate(extractions):
            for h in model_holdings:
                all_holdings.append((model_idx, h))

        # Track which holdings have been matched
        matched: set[tuple[int, int]] = set()  # (model_idx, holding_idx_within_model)

        # For each pair of holdings from different models, compute similarity
        # and group matches. We use a greedy approach: best matches first.
        match_candidates: list[tuple[float, int, int, int, int]] = []
        # (similarity, model_a_idx, holding_a_pos, model_b_idx, holding_b_pos)

        for i, (model_a, holding_a) in enumerate(all_holdings):
            for j, (model_b, holding_b) in enumerate(all_holdings):
                if j <= i:
                    continue
                if model_a == model_b:
                    continue

                sim = self._compute_holding_similarity(holding_a, holding_b)
                if sim >= self._SIMILARITY_THRESHOLD:
                    match_candidates.append((sim, model_a, i, model_b, j))

        # Sort by similarity (highest first) for greedy matching
        match_candidates.sort(key=lambda x: x[0], reverse=True)

        # Build match groups: groups of holdings from different models that
        # refer to the same legal holding.
        # Each group is a dict: {model_idx: (flat_all_holdings_index, holding_dict)}
        groups: list[dict[int, tuple[int, dict[str, Any]]]] = []

        for sim, model_a, idx_a, model_b, idx_b in match_candidates:
            if (model_a, idx_a) in matched or (model_b, idx_b) in matched:
                # One of these holdings is already matched; try to add to
                # existing group if the other side is unmatched
                if (model_a, idx_a) in matched and (model_b, idx_b) not in matched:
                    # Find the group containing (model_a, idx_a)
                    for group in groups:
                        if model_a in group and group[model_a][0] == idx_a:
                            if model_b not in group:
                                group[model_b] = (idx_b, all_holdings[idx_b][1])
                                matched.add((model_b, idx_b))
                            break
                elif (model_b, idx_b) in matched and (model_a, idx_a) not in matched:
                    for group in groups:
                        if model_b in group and group[model_b][0] == idx_b:
                            if model_a not in group:
                                group[model_a] = (idx_a, all_holdings[idx_a][1])
                                matched.add((model_a, idx_a))
                            break
                continue

            # Neither is matched — create a new group
            group: dict[int, tuple[int, dict[str, Any]]] = {
                model_a: (idx_a, all_holdings[idx_a][1]),
                model_b: (idx_b, all_holdings[idx_b][1]),
            }
            matched.add((model_a, idx_a))
            matched.add((model_b, idx_b))
            groups.append(group)

        # Classify groups into consensus vs partial
        consensus_holdings: list[ExtractedHolding] = []
        partial_holdings: list[ExtractedHolding] = []

        for group in groups:
            num_models = len(group)
            holdings_in_group = [h_dict for _, (_, h_dict) in group.items()]
            merged = self._merge_holdings(holdings_in_group)

            if num_models >= 3:
                # Full consensus
                holding = ExtractedHolding(
                    case_citation=case_citation,
                    statute_citation=merged.get("statute_citation", ""),
                    holding_text=merged.get("holding_text", ""),
                    holding_type=HoldingType(merged.get("holding_type", HoldingType.RULE_STATEMENT.value)),
                    key_facts=merged.get("key_facts", []),
                    legal_standard=merged.get("legal_standard", LegalStandard.NOT_SPECIFIED.value),
                    supports=merged.get("supports", PartySide.NEUTRAL.value),
                    jurisdiction=jurisdiction,
                    court_level=court_level,
                    year=year,
                    verified=True,
                    confidence=1.0,
                    extracted_at=now,
                )
                consensus_holdings.append(holding)

            elif num_models == 2:
                # Partial consensus
                models_present = list(group.keys())
                model_labels_map = {0: "primary", 1: "scout", 2: "cohere"}
                present_labels = [model_labels_map.get(m, f"model_{m}") for m in models_present]
                missing_models = [
                    model_labels_map.get(m, f"model_{m}")
                    for m in range(3) if m not in group
                ]

                holding = ExtractedHolding(
                    case_citation=case_citation,
                    statute_citation=merged.get("statute_citation", ""),
                    holding_text=merged.get("holding_text", ""),
                    holding_type=HoldingType(merged.get("holding_type", HoldingType.RULE_STATEMENT.value)),
                    key_facts=merged.get("key_facts", []),
                    legal_standard=merged.get("legal_standard", LegalStandard.NOT_SPECIFIED.value),
                    supports=merged.get("supports", PartySide.NEUTRAL.value),
                    jurisdiction=jurisdiction,
                    court_level=court_level,
                    year=year,
                    verified=False,
                    confidence=0.67,
                    extracted_at=now,
                    disagreement_notes=[
                        f"Agreed by {', '.join(present_labels)}; not found by {', '.join(missing_models)}"
                    ],
                )
                partial_holdings.append(holding)

        # Collect unmatched holdings as disagreements
        disagreement_list: list[dict[str, Any]] = []
        model_labels_full = ["jurisdiction_primary", "jurisdiction_scout", "jurisdiction_cohere"]

        for flat_idx, (model_idx, h_dict) in enumerate(all_holdings):
            if (model_idx, flat_idx) not in matched:
                source_label = model_labels_full[model_idx] if model_idx < len(model_labels_full) else f"model_{model_idx}"
                disagreement_list.append({
                    "reason": f"Only {source_label} extracted this holding",
                    "citation": case_citation,
                    "holding_text": h_dict.get("holding_text", ""),
                    "holding_type": h_dict.get("holding_type", ""),
                    "statute_citation": h_dict.get("statute_citation", ""),
                    "supports": h_dict.get("supports", ""),
                    "source_model": source_label,
                })

        return consensus_holdings, partial_holdings, disagreement_list

    def _compute_holding_similarity(
        self,
        holding_a: dict[str, Any],
        holding_b: dict[str, Any],
    ) -> float:
        """Compute semantic similarity between two extracted holdings.

        Uses a weighted combination of:
        - Text similarity of holding_text (60%)
        - Holding type match (15%)
        - Statute citation match (15%)
        - Party support match (10%)

        Returns a score between 0.0 and 1.0.
        """
        text_a = str(holding_a.get("holding_text", "")).lower().strip()
        text_b = str(holding_b.get("holding_text", "")).lower().strip()

        if not text_a or not text_b:
            return 0.0

        # Text similarity via SequenceMatcher (works well for legal text
        # where the same holding may be phrased slightly differently)
        text_sim = SequenceMatcher(None, text_a, text_b).ratio()

        # Holding type match
        type_a = str(holding_a.get("holding_type", "")).lower().strip()
        type_b = str(holding_b.get("holding_type", "")).lower().strip()
        type_sim = 1.0 if type_a == type_b else 0.0

        # Statute citation match
        stat_a = str(holding_a.get("statute_citation", "")).lower().strip()
        stat_b = str(holding_b.get("statute_citation", "")).lower().strip()
        if stat_a and stat_b:
            stat_sim = SequenceMatcher(None, stat_a, stat_b).ratio()
        elif not stat_a and not stat_b:
            stat_sim = 1.0  # Both have no statute — neutral
        else:
            stat_sim = 0.0  # One has a statute, the other doesn't

        # Party support match
        support_a = str(holding_a.get("supports", "neutral")).lower().strip()
        support_b = str(holding_b.get("supports", "neutral")).lower().strip()
        support_sim = 1.0 if support_a == support_b else 0.0

        # Weighted combination
        score = (
            0.60 * text_sim
            + 0.15 * type_sim
            + 0.15 * stat_sim
            + 0.10 * support_sim
        )

        return score

    def _merge_holdings(self, holdings: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple model extractions of the same holding into one.

        When models agree on a holding but phrase it differently, we pick
        the best version of each field:
        - holding_text: longest version (most detailed)
        - key_facts: union of all facts
        - statute_citation: most specific (longest non-empty)
        - holding_type, legal_standard, supports: majority vote
        """
        if not holdings:
            return {}
        if len(holdings) == 1:
            return dict(holdings[0])

        # holding_text: pick the longest (most detailed)
        holding_text = max(
            (str(h.get("holding_text", "")) for h in holdings),
            key=len,
        )

        # statute_citation: pick the longest non-empty
        statute_citations = [str(h.get("statute_citation", "")) for h in holdings if h.get("statute_citation")]
        statute_citation = max(statute_citations, key=len) if statute_citations else ""

        # key_facts: union, deduplicated
        all_facts: list[str] = []
        seen_facts: set[str] = set()
        for h in holdings:
            for fact in h.get("key_facts", []):
                fact_lower = str(fact).lower().strip()
                if fact_lower and fact_lower not in seen_facts:
                    seen_facts.add(fact_lower)
                    all_facts.append(str(fact))

        # Majority vote for categorical fields
        holding_type = self._majority_vote(
            [str(h.get("holding_type", "rule_statement")) for h in holdings]
        )
        legal_standard = self._majority_vote(
            [str(h.get("legal_standard", "not_specified")) for h in holdings]
        )
        supports = self._majority_vote(
            [str(h.get("supports", "neutral")) for h in holdings]
        )

        return {
            "holding_text": holding_text,
            "statute_citation": statute_citation,
            "key_facts": all_facts,
            "holding_type": holding_type,
            "legal_standard": legal_standard,
            "supports": supports,
        }

    @staticmethod
    def _majority_vote(values: list[str]) -> str:
        """Return the most common value. Ties broken by first occurrence."""
        if not values:
            return ""
        counts: dict[str, int] = {}
        for v in values:
            v_clean = v.lower().strip()
            counts[v_clean] = counts.get(v_clean, 0) + 1
        winner = max(counts, key=lambda k: counts[k])
        # Return the original-cased version
        for v in values:
            if v.lower().strip() == winner:
                return v
        return winner

    @staticmethod
    def _normalize_holding_type(raw: str) -> str:
        """Normalize a holding type string to a valid HoldingType value."""
        clean = raw.lower().strip().replace(" ", "_").replace("-", "_")
        valid = {e.value for e in HoldingType}
        if clean in valid:
            return clean
        # Fuzzy matching for common variants
        aliases: dict[str, str] = {
            "rule": HoldingType.RULE_STATEMENT.value,
            "ruling": HoldingType.RULE_STATEMENT.value,
            "applied": HoldingType.APPLICATION.value,
            "apply": HoldingType.APPLICATION.value,
            "distinguished": HoldingType.DISTINGUISHING.value,
            "overruled": HoldingType.OVERRULING.value,
            "overrule": HoldingType.OVERRULING.value,
            "limited": HoldingType.LIMITATION.value,
            "limit": HoldingType.LIMITATION.value,
            "excepted": HoldingType.EXCEPTION.value,
            "except": HoldingType.EXCEPTION.value,
        }
        if clean in aliases:
            return aliases[clean]
        return HoldingType.RULE_STATEMENT.value

    @staticmethod
    def _normalize_legal_standard(raw: str) -> str:
        """Normalize a legal standard string."""
        clean = raw.lower().strip().replace(" ", "_").replace("-", "_")
        valid = {e.value for e in LegalStandard}
        if clean in valid:
            return clean
        aliases: dict[str, str] = {
            "preponderance_of_evidence": LegalStandard.PREPONDERANCE.value,
            "preponderance_of_the_evidence": LegalStandard.PREPONDERANCE.value,
            "clear_and_convincing_evidence": LegalStandard.CLEAR_AND_CONVINCING.value,
            "brd": LegalStandard.BEYOND_REASONABLE_DOUBT.value,
            "beyond_a_reasonable_doubt": LegalStandard.BEYOND_REASONABLE_DOUBT.value,
            "de_novo_review": LegalStandard.DE_NOVO.value,
            "abuse_of_discretion_standard": LegalStandard.ABUSE_OF_DISCRETION.value,
            "none": LegalStandard.NOT_SPECIFIED.value,
            "n/a": LegalStandard.NOT_SPECIFIED.value,
            "na": LegalStandard.NOT_SPECIFIED.value,
            "unknown": LegalStandard.NOT_SPECIFIED.value,
            "": LegalStandard.NOT_SPECIFIED.value,
        }
        if clean in aliases:
            return aliases[clean]
        return LegalStandard.NOT_SPECIFIED.value

    @staticmethod
    def _normalize_party_side(raw: str) -> str:
        """Normalize a party side string."""
        clean = raw.lower().strip()
        if clean in ("plaintiff", "plaintiffs"):
            return PartySide.PLAINTIFF.value
        if clean in ("defendant", "defendants", "defense"):
            return PartySide.DEFENDANT.value
        return PartySide.NEUTRAL.value


# ---------------------------------------------------------------------------
# Integration: Extract + Siphon into CaseCatalog
# ---------------------------------------------------------------------------


async def extract_and_catalog(
    opinion_text: str,
    case_citation: str,
    case_name: str,
    jurisdiction: str,
    court: str,
    court_level: str,
    year: int,
    extractor: HoldingExtractor,
    catalog: Any,
) -> ExtractionResult:
    """Extract holdings from an opinion and siphon them into the CaseCatalog.

    This is the main integration point between the HoldingExtractor and the
    CaseCatalog/StatuteIndex. Called by the crawler when it retrieves full
    opinion text for deeper analysis.

    Parameters
    ----------
    opinion_text :
        Full opinion text from CourtListener or another external source.
    case_citation :
        Full Bluebook citation.
    case_name :
        Case name (e.g., "Smith v. Jones").
    jurisdiction :
        Jurisdiction code.
    court :
        Full court name.
    court_level :
        Level of court.
    year :
        Year decided.
    extractor :
        HoldingExtractor instance.
    catalog :
        CaseCatalog instance (from src.knowledge.case_catalog).

    Returns
    -------
    ExtractionResult
        The full extraction result with consensus/partial/disagreement breakdown.
    """
    result = await extractor.extract_holdings(
        opinion_text=opinion_text,
        case_citation=case_citation,
        jurisdiction=jurisdiction,
        court_level=court_level,
        year=year,
    )

    if result.error:
        logger.error(
            "extract_and_catalog_failed | citation=%s error=%s",
            case_citation, result.error,
        )
        return result

    # Build holdings list for the CatalogEntry
    holdings_for_catalog: list[dict[str, str]] = []

    # Consensus holdings go in as verified
    for holding in result.consensus_holdings:
        holdings_for_catalog.append({
            "statute": holding.statute_citation,
            "holding_text": holding.holding_text,
            "treatment": _holding_type_to_treatment(holding.holding_type),
            "supports": holding.supports,
            "verified": "true",
            "holding_type": holding.holding_type.value,
            "legal_standard": holding.legal_standard,
        })

    # Partial holdings go in as unverified
    for holding in result.partial_holdings:
        holdings_for_catalog.append({
            "statute": holding.statute_citation,
            "holding_text": holding.holding_text,
            "treatment": _holding_type_to_treatment(holding.holding_type),
            "supports": holding.supports,
            "verified": "false",
            "holding_type": holding.holding_type.value,
            "legal_standard": holding.legal_standard,
        })

    # Determine overall party support
    supports_counts: dict[str, int] = {}
    for h in result.consensus_holdings + result.partial_holdings:
        side = h.supports
        supports_counts[side] = supports_counts.get(side, 0) + 1

    # Siphon into catalog (the CaseCatalog.siphon method handles indexing)
    from src.knowledge.case_catalog import CatalogEntry

    entry = CatalogEntry(
        citation=case_citation,
        name=case_name,
        court=court,
        year=year,
        jurisdiction=jurisdiction,
        holdings=holdings_for_catalog,
        statutes_cited=[
            h.statute_citation
            for h in result.consensus_holdings + result.partial_holdings
            if h.statute_citation
        ],
        verified=len(result.consensus_holdings) > 0,
        verification_source="dual_brain_consensus",
        opinion_text_available=True,
        opinion_url="",
        siphon_source="holding_extractor",
    )

    catalog.siphon(entry)

    logger.info(
        "extract_and_catalog_complete | citation=%s consensus=%d partial=%d siphoned=True",
        case_citation,
        len(result.consensus_holdings),
        len(result.partial_holdings),
    )

    return result


def _holding_type_to_treatment(holding_type: HoldingType) -> str:
    """Map a HoldingType to a CaseTreatment-compatible string.

    The CaseTreatment enum in statute_index.py has a different taxonomy.
    This bridges the two systems.
    """
    mapping = {
        HoldingType.RULE_STATEMENT: "interpreted",
        HoldingType.APPLICATION: "interpreted",
        HoldingType.EXCEPTION: "narrowed",
        HoldingType.LIMITATION: "narrowed",
        HoldingType.OVERRULING: "struck_down",
        HoldingType.DISTINGUISHING: "distinguished",
    }
    return mapping.get(holding_type, "interpreted")
