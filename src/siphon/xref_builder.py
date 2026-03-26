"""Cross-Reference Builder — Links statutes, case law, and court rules.

Runs after siphon workers to build the legal_cross_references table.
Uses citation extraction, semantic similarity, and explicit references
to create the knowledge graph edges that power the If-Then Matching Engine.

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("cyphergy.siphon.xref_builder")

# Citation patterns for cross-referencing
STATUTE_CITATION_PATTERNS = [
    # Federal: "42 U.S.C. § 1983"
    re.compile(r"(\d+)\s+U\.?S\.?C\.?\s*§\s*(\d+[a-z]?(?:\(\w+\))*)"),
    # State: "Fla. Stat. § 83.67" or "F.S. § 83.67"
    re.compile(r"(?:Fla\.?\s*Stat\.?|F\.S\.)\s*§\s*([\d.]+)"),
    re.compile(r"(?:Tex\.?\s*(?:Civ\.?\s*Prac\.?\s*&\s*Rem\.?\s*Code|Prop\.?\s*Code))\s*§\s*([\d.]+)"),
    re.compile(r"(?:Cal\.?\s*(?:Civ\.?\s*Code|Code\s*Civ\.?\s*Proc\.?))\s*§\s*([\d.]+)"),
    re.compile(r"(?:N\.?Y\.?\s*(?:C\.?P\.?L\.?R\.?|Gen\.?\s*Bus\.?\s*Law))\s*§\s*([\d.]+)"),
]

CASE_CITATION_PATTERNS = [
    # "123 U.S. 456"
    re.compile(r"(\d+)\s+U\.S\.\s+(\d+)"),
    # "123 S.Ct. 456"
    re.compile(r"(\d+)\s+S\.?\s*Ct\.?\s+(\d+)"),
    # "123 F.3d 456"
    re.compile(r"(\d+)\s+F\.(?:2d|3d|4th|Supp\.?\s*(?:2d|3d)?)\s+(\d+)"),
    # "123 So.3d 456"
    re.compile(r"(\d+)\s+(?:So|N\.?[EW]|S\.?[EW]|A|P)\.?(?:2d|3d)?\s+(\d+)"),
]

RULE_CITATION_PATTERNS = [
    # "Fed. R. Civ. P. 12(b)(6)"
    re.compile(r"Fed\.?\s*R\.?\s*Civ\.?\s*P\.?\s*(\d+(?:\(\w+\))*)"),
    # "FRCP Rule 56"
    re.compile(r"(?:FRCP|F\.R\.C\.P\.)\s*(?:Rule\s*)?(\d+(?:\(\w+\))*)"),
    # "Rule 12(b)(6)"
    re.compile(r"Rule\s+(\d+(?:\(\w+\))*)"),
]


@dataclass
class CrossReference:
    """A discovered cross-reference between legal authorities."""
    statute_section: Optional[str] = None
    case_citation: Optional[str] = None
    rule_number: Optional[str] = None
    relationship: str = "cites"
    confidence: float = 0.0
    source_type: str = ""
    source_id: int = 0


class XRefBuilder:
    """Builds cross-references between statutes, case law, and court rules.

    The cross-reference graph is the backbone of the If-Then Matching Engine.
    When a user describes a situation, the matching engine finds the relevant
    statute, then follows cross-references to find:
      - Cases that interpret that statute
      - Rules that govern the procedure
      - Other statutes that are related

    This creates the "if that then" chain that powers ChiefLitigator.
    """

    def __init__(self) -> None:
        self._stats = {
            "cases_scanned": 0,
            "statutes_scanned": 0,
            "rules_scanned": 0,
            "xrefs_created": 0,
            "errors": 0,
        }

    def extract_statute_citations(self, text: str) -> List[str]:
        """Extract statute citations from text."""
        citations = []
        for pattern in STATUTE_CITATION_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    citations.append(" ".join(match))
                else:
                    citations.append(match)
        return list(set(citations))

    def extract_case_citations(self, text: str) -> List[str]:
        """Extract case citations from text."""
        citations = []
        for pattern in CASE_CITATION_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    citations.append(f"{match[0]} _ {match[1]}")
                else:
                    citations.append(match)
        return list(set(citations))

    def extract_rule_citations(self, text: str) -> List[str]:
        """Extract procedural rule citations from text."""
        citations = []
        for pattern in RULE_CITATION_PATTERNS:
            matches = pattern.findall(text)
            citations.extend(matches)
        return list(set(citations))

    async def scan_case_law(self, db_connection) -> List[CrossReference]:
        """Scan all case law opinions for citations to statutes and rules."""
        xrefs = []

        # In production: paginated query against Aurora case_law table
        # SELECT id, opinion_text FROM case_law WHERE opinion_text IS NOT NULL
        # For each opinion, extract citations and create cross-references

        logger.info("Scanning case law for cross-references...")

        # Simulated query — in production this reads from Aurora
        # async for row in db_connection.fetch_all("SELECT id, opinion_text, jurisdiction FROM case_law"):
        #     opinion_text = row["opinion_text"]
        #     statute_cites = self.extract_statute_citations(opinion_text)
        #     rule_cites = self.extract_rule_citations(opinion_text)
        #     case_cites = self.extract_case_citations(opinion_text)
        #
        #     for cite in statute_cites:
        #         xrefs.append(CrossReference(
        #             case_citation=str(row["id"]),
        #             statute_section=cite,
        #             relationship="interprets",
        #             confidence=0.85,
        #             source_type="case_law",
        #             source_id=row["id"],
        #         ))
        #
        #     for cite in rule_cites:
        #         xrefs.append(CrossReference(
        #             case_citation=str(row["id"]),
        #             rule_number=cite,
        #             relationship="applies",
        #             confidence=0.80,
        #             source_type="case_law",
        #             source_id=row["id"],
        #         ))
        #
        #     self._stats["cases_scanned"] += 1

        return xrefs

    async def scan_statutes(self, db_connection) -> List[CrossReference]:
        """Scan statutes for cross-references to other statutes and rules."""
        xrefs = []
        logger.info("Scanning statutes for cross-references...")
        # Similar pattern: read from Aurora, extract citations, create xrefs
        return xrefs

    async def build_semantic_links(self, db_connection) -> List[CrossReference]:
        """Use vector similarity to find semantically related authorities.

        This catches relationships that aren't expressed through explicit citations.
        For example, a state statute about unlawful lockouts and a federal case
        about tenant rights may be semantically related even without citing each other.
        """
        xrefs = []
        logger.info("Building semantic cross-references via vector similarity...")

        # In production:
        # 1. For each statute, find the top-5 most similar case_law entries
        # 2. For each case, find the top-3 most similar court_rules
        # 3. Create xrefs with relationship="semantically_related"
        #
        # SQL: SELECT cl.id, cl.case_name,
        #        1 - (s.embedding <=> cl.embedding) as similarity
        #      FROM statutes s
        #      CROSS JOIN LATERAL (
        #        SELECT id, case_name, embedding
        #        FROM case_law
        #        WHERE jurisdiction = s.jurisdiction
        #        ORDER BY embedding <=> s.embedding
        #        LIMIT 5
        #      ) cl
        #      WHERE 1 - (s.embedding <=> cl.embedding) > 0.75

        return xrefs

    async def run_incremental(self, db_connection=None) -> Dict[str, Any]:
        """Run incremental cross-reference building."""
        logger.info("Cross-reference builder starting (incremental)")

        case_xrefs = await self.scan_case_law(db_connection)
        statute_xrefs = await self.scan_statutes(db_connection)
        semantic_xrefs = await self.build_semantic_links(db_connection)

        all_xrefs = case_xrefs + statute_xrefs + semantic_xrefs
        self._stats["xrefs_created"] = len(all_xrefs)

        # In production: batch INSERT into legal_cross_references table
        # INSERT INTO legal_cross_references (statute_id, case_law_id, court_rule_id, relationship, confidence)
        # VALUES ($1, $2, $3, $4, $5)
        # ON CONFLICT DO UPDATE SET confidence = GREATEST(confidence, EXCLUDED.confidence)

        logger.info("Cross-reference builder complete: %s", self._stats)
        return self._stats

    async def run_full(self, db_connection=None) -> Dict[str, Any]:
        """Run full cross-reference rebuild."""
        logger.info("Cross-reference builder starting (full rebuild)")
        # Truncate and rebuild
        return await self.run_incremental(db_connection)
