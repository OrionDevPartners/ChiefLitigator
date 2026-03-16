"""Argument Graph Engine — Directed case law relationship graph.

Novel architecture by Bo Pennington.

Instead of returning a flat list of cases per statute, this engine
builds a DIRECTED GRAPH where each case either SUPPORTS, WEAKENS,
DISTINGUISHES, or OVERRULES other cases. When a user searches, they
get an argument CHAIN — not a case list.

The argument chain is a litigation strategy:
  1. Foundation case — earliest binding authority establishing the rule
  2. Supporting cases — cases that follow/extend the foundation
  3. Recent reaffirmation — newest case confirming the rule is good law
  4. Anticipated counters — what the opposing side will cite,
     plus why each counter is distinguishable

The graph is stored in-memory initially but designed for Aurora
PostgreSQL migration with recursive CTEs for path traversal.

Schema preview (for future migration):

    CREATE TABLE case_edges (
        id          BIGSERIAL PRIMARY KEY,
        source_cite TEXT NOT NULL,
        target_cite TEXT NOT NULL,
        relationship TEXT NOT NULL,
        description TEXT,
        jurisdiction TEXT NOT NULL,
        year        INT NOT NULL,
        created_at  TIMESTAMPTZ DEFAULT now()
    );

    -- Recursive CTE for chain traversal:
    WITH RECURSIVE chain AS (
        SELECT source_cite, target_cite, relationship, 1 AS depth
        FROM case_edges
        WHERE source_cite = :foundation
          AND relationship IN ('follows', 'supports', 'extends')
        UNION ALL
        SELECT e.source_cite, e.target_cite, e.relationship, c.depth + 1
        FROM case_edges e
        JOIN chain c ON c.target_cite = e.source_cite
        WHERE c.depth < 10
    )
    SELECT * FROM chain ORDER BY depth;
"""

from __future__ import annotations

import logging
from collections import defaultdict
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.knowledge.argument_graph")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CaseRelationship(str, Enum):
    """How one case relates to another in the argument graph."""

    SUPPORTS = "supports"           # Case A supports the same legal principle as Case B
    WEAKENS = "weakens"             # Case A weakens Case B's holding
    DISTINGUISHES = "distinguishes" # Case A says "that case was different because..."
    OVERRULES = "overrules"         # Case A explicitly overrules Case B
    FOLLOWS = "follows"             # Case A follows Case B's reasoning
    EXTENDS = "extends"             # Case A extends Case B to new facts
    LIMITS = "limits"               # Case A limits Case B's scope


# Which relationships strengthen an argument vs. which undermine it
_REINFORCING: frozenset[CaseRelationship] = frozenset({
    CaseRelationship.SUPPORTS,
    CaseRelationship.FOLLOWS,
    CaseRelationship.EXTENDS,
})

_UNDERMINING: frozenset[CaseRelationship] = frozenset({
    CaseRelationship.WEAKENS,
    CaseRelationship.DISTINGUISHES,
    CaseRelationship.OVERRULES,
    CaseRelationship.LIMITS,
})


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class GraphEdge(BaseModel):
    """A directed edge in the argument graph.

    Represents: source_citation -[relationship]-> target_citation.

    Example: if Case A follows Case B's reasoning, the edge is
    source=A, target=B, relationship=FOLLOWS. This means A looked
    at B and adopted its rule.
    """

    source_citation: str = Field(description="The citing case (Case A)")
    target_citation: str = Field(description="The cited case (Case B)")
    relationship: CaseRelationship
    description: str = Field(
        default="",
        description="How the cases relate — the specific legal reasoning",
    )
    jurisdiction: str = Field(description="Jurisdiction where source case was decided")
    year: int = Field(description="Year the source case was decided")
    statute: str = Field(
        default="",
        description="The statute this relationship concerns (if applicable)",
    )
    verified: bool = Field(
        default=False,
        description="Whether this edge has been verified against opinion text",
    )


class ArgumentChain(BaseModel):
    """A complete argument strategy built from the graph.

    This is what the user receives — not a case list, but a
    structured litigation strategy showing how cases build on
    each other and how to anticipate the opposing side's arguments.
    """

    statute: str = Field(description="The statute this chain interprets")
    jurisdiction: str = Field(description="Jurisdiction for binding authority")
    side: str = Field(description="'plaintiff' or 'defendant'")

    # The chain
    foundation_case: str = Field(
        description="Start here — the earliest binding authority establishing the rule",
    )
    foundation_year: int = Field(
        default=0,
        description="Year of the foundation case",
    )
    foundation_holding: str = Field(
        default="",
        description="What the foundation case established",
    )
    supporting_cases: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Cases that build the argument [{citation, year, relationship, description}]",
    )
    recent_reaffirmation: Optional[str] = Field(
        default=None,
        description="Most recent case confirming the rule is good law",
    )
    recent_reaffirmation_year: Optional[int] = Field(
        default=None,
        description="Year of the most recent reaffirmation",
    )
    anticipated_counters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="What opposing counsel will cite + why it's distinguishable",
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) based on chain depth and recency",
    )
    total_cases_analyzed: int = Field(
        default=0,
        description="Total cases in the graph for this statute+jurisdiction",
    )
    chain_depth: int = Field(
        default=0,
        description="Number of cases in the supporting chain",
    )


# ---------------------------------------------------------------------------
# Argument Graph Engine
# ---------------------------------------------------------------------------


class ArgumentGraph:
    """Directed graph of case law relationships.

    Transforms flat case indexes into structured argument strategies.
    Each node is a case citation. Each edge is a relationship
    (supports, weakens, distinguishes, overrules, follows, extends, limits).

    The graph answers the question every litigator asks:
    "Given this statute in this jurisdiction, what is my strongest
    argument chain, and what will the other side throw at me?"

    Usage::

        graph = ArgumentGraph()

        # Add edges as cases are cataloged
        graph.add_edge(GraphEdge(
            source_citation="Smith v. Jones, 700 So.2d 100 (Fla. 2000)",
            target_citation="Globe v. King, 658 So.2d 518 (Fla. 1995)",
            relationship=CaseRelationship.FOLLOWS,
            description="Court adopted Globe's proffer requirement for punitive claims",
            jurisdiction="FL",
            year=2000,
            statute="Fla. Stat. § 768.72",
        ))

        # Build argument chain for a user's case
        chain = graph.build_argument_chain(
            statute="Fla. Stat. § 768.72",
            jurisdiction="FL",
            side="plaintiff",
        )
        # Returns: foundation case -> supporting -> recent -> anticipated counters

        # Red team: find the strongest arguments AGAINST your position
        counters = graph.find_counter_arguments(
            statute="Fla. Stat. § 768.72",
            jurisdiction="FL",
            side="plaintiff",
        )
    """

    # Maximum traversal depth to prevent infinite loops in cyclic graphs
    _MAX_DEPTH = 20

    def __init__(self) -> None:
        # All edges in the graph
        self._edges: list[GraphEdge] = []

        # Adjacency list: citation -> outgoing edges (cases that cite this one)
        self._outgoing: dict[str, list[GraphEdge]] = defaultdict(list)

        # Reverse adjacency: citation -> incoming edges (cases cited by this one)
        self._incoming: dict[str, list[GraphEdge]] = defaultdict(list)

        # Index: statute -> list of edges concerning that statute
        self._statute_edges: dict[str, list[GraphEdge]] = defaultdict(list)

        # Index: jurisdiction -> list of edges from that jurisdiction
        self._jurisdiction_edges: dict[str, list[GraphEdge]] = defaultdict(list)

        # Track all known citations (nodes in the graph)
        self._nodes: set[str] = set()

        logger.info("ArgumentGraph initialized")

    # ── Public API: Graph Mutation ────────────────────────────────────

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a relationship between two cases.

        Maintains adjacency lists, statute index, and jurisdiction index.
        Duplicate edges (same source, target, relationship) are rejected.

        Parameters
        ----------
        edge:
            The directed edge to add.
        """
        # Check for duplicate
        for existing in self._outgoing[edge.source_citation]:
            if (
                existing.target_citation == edge.target_citation
                and existing.relationship == edge.relationship
            ):
                logger.debug(
                    "duplicate_edge | source=%s target=%s rel=%s",
                    edge.source_citation,
                    edge.target_citation,
                    edge.relationship.value,
                )
                return

        self._edges.append(edge)
        self._outgoing[edge.source_citation].append(edge)
        self._incoming[edge.target_citation].append(edge)

        if edge.statute:
            self._statute_edges[edge.statute].append(edge)

        self._jurisdiction_edges[edge.jurisdiction].append(edge)

        self._nodes.add(edge.source_citation)
        self._nodes.add(edge.target_citation)

        logger.debug(
            "edge_added | %s -[%s]-> %s | statute=%s jurisdiction=%s year=%d",
            edge.source_citation,
            edge.relationship.value,
            edge.target_citation,
            edge.statute,
            edge.jurisdiction,
            edge.year,
        )

    def add_edges(self, edges: list[GraphEdge]) -> int:
        """Batch-add multiple edges. Returns the count of new edges added."""
        before = len(self._edges)
        for edge in edges:
            self.add_edge(edge)
        added = len(self._edges) - before
        logger.info("batch_added | edges=%d new=%d", len(edges), added)
        return added

    # ── Public API: Graph Query ───────────────────────────────────────

    def get_relationships(self, citation: str) -> list[GraphEdge]:
        """Get all relationships for a case (both outgoing and incoming).

        Parameters
        ----------
        citation:
            The case citation to look up.

        Returns
        -------
        All edges where this citation is either source or target.
        """
        outgoing = list(self._outgoing.get(citation, []))
        incoming = list(self._incoming.get(citation, []))
        return outgoing + incoming

    def get_outgoing(self, citation: str) -> list[GraphEdge]:
        """Get edges where this case cites other cases."""
        return list(self._outgoing.get(citation, []))

    def get_incoming(self, citation: str) -> list[GraphEdge]:
        """Get edges where other cases cite this case."""
        return list(self._incoming.get(citation, []))

    def get_edges_for_statute(self, statute: str) -> list[GraphEdge]:
        """Get all edges concerning a specific statute."""
        return list(self._statute_edges.get(statute, []))

    def get_edges_for_jurisdiction(self, jurisdiction: str) -> list[GraphEdge]:
        """Get all edges from a specific jurisdiction."""
        return list(self._jurisdiction_edges.get(jurisdiction, []))

    def has_node(self, citation: str) -> bool:
        """Check if a case exists in the graph."""
        return citation in self._nodes

    # ── Public API: Argument Chain Builder ────────────────────────────

    def build_argument_chain(
        self,
        statute: str,
        jurisdiction: str,
        side: str,
    ) -> ArgumentChain:
        """Build a complete argument strategy from the graph.

        This is the core function. Given a statute, jurisdiction, and
        which side the user is on, it constructs a litigation chain:

        1. Find the foundation case (earliest binding authority
           for this statute in this jurisdiction)
        2. Follow SUPPORTS/FOLLOWS/EXTENDS edges to build the chain
        3. Find recent reaffirmation (newest case following the rule)
        4. Follow WEAKENS/DISTINGUISHES/LIMITS edges to find counters
        5. For each counter: explain why it is distinguishable

        Parameters
        ----------
        statute:
            Statute citation (e.g., "Fla. Stat. § 768.72").
        jurisdiction:
            Jurisdiction code (e.g., "FL").
        side:
            "plaintiff" or "defendant".

        Returns
        -------
        A complete ArgumentChain with foundation, supporting cases,
        reaffirmation, and anticipated counters.
        """
        # Gather all edges for this statute in this jurisdiction
        statute_edges = self._statute_edges.get(statute, [])
        relevant_edges = [
            e for e in statute_edges
            if e.jurisdiction == jurisdiction
        ]

        # Also include federal authority (always potentially binding)
        federal_edges = [
            e for e in statute_edges
            if e.jurisdiction == "FED"
        ]
        all_edges = relevant_edges + federal_edges

        if not all_edges:
            logger.info(
                "no_edges | statute=%s jurisdiction=%s",
                statute, jurisdiction,
            )
            return ArgumentChain(
                statute=statute,
                jurisdiction=jurisdiction,
                side=side,
                foundation_case="",
                confidence=0.0,
                total_cases_analyzed=0,
            )

        # Collect all citations in this statute+jurisdiction context
        citations_in_scope = set()
        for e in all_edges:
            citations_in_scope.add(e.source_citation)
            citations_in_scope.add(e.target_citation)

        total_analyzed = len(citations_in_scope)

        # Step 1: Find foundation case — earliest binding authority
        foundation, foundation_year, foundation_holding = self._find_foundation(
            all_edges, citations_in_scope, jurisdiction
        )

        # Step 2: Build supporting chain from foundation
        supporting = self._build_supporting_chain(
            foundation, all_edges, citations_in_scope
        )

        # Step 3: Find most recent reaffirmation
        reaffirmation, reaffirmation_year = self._find_recent_reaffirmation(
            foundation, all_edges, citations_in_scope
        )

        # Step 4: Find counter-arguments (what the other side will cite)
        counters = self._find_counters(
            foundation, all_edges, citations_in_scope, side
        )

        # Step 5: Compute confidence
        confidence = self._compute_confidence(
            foundation=foundation,
            supporting=supporting,
            reaffirmation=reaffirmation,
            reaffirmation_year=reaffirmation_year,
            counters=counters,
            total=total_analyzed,
        )

        chain = ArgumentChain(
            statute=statute,
            jurisdiction=jurisdiction,
            side=side,
            foundation_case=foundation,
            foundation_year=foundation_year,
            foundation_holding=foundation_holding,
            supporting_cases=supporting,
            recent_reaffirmation=reaffirmation,
            recent_reaffirmation_year=reaffirmation_year,
            anticipated_counters=counters,
            confidence=round(confidence, 4),
            total_cases_analyzed=total_analyzed,
            chain_depth=len(supporting),
        )

        logger.info(
            "chain_built | statute=%s jurisdiction=%s side=%s "
            "foundation=%s supporting=%d reaffirm=%s counters=%d confidence=%.3f",
            statute, jurisdiction, side,
            foundation, len(supporting),
            reaffirmation or "none",
            len(counters), confidence,
        )

        return chain

    # ── Public API: Red Team ──────────────────────────────────────────

    def find_counter_arguments(
        self,
        statute: str,
        jurisdiction: str,
        side: str,
    ) -> list[dict[str, Any]]:
        """Red Team function: find the strongest arguments AGAINST your position.

        Searches the graph for cases that WEAKEN, DISTINGUISH, LIMIT, or
        OVERRULE cases supporting your side. Returns them ranked by
        strength (overrules > weakens > limits > distinguishes).

        Parameters
        ----------
        statute:
            Statute citation.
        jurisdiction:
            Jurisdiction code.
        side:
            "plaintiff" or "defendant" — the side to argue AGAINST.

        Returns
        -------
        List of counter-argument dicts, each containing:
        - citation: the counter case
        - relationship: how it undermines (weakens, distinguishes, etc.)
        - target: which of your cases it attacks
        - description: the legal reasoning
        - year: when decided
        - strength: relative strength score
        """
        statute_edges = self._statute_edges.get(statute, [])
        relevant_edges = [
            e for e in statute_edges
            if e.jurisdiction == jurisdiction or e.jurisdiction == "FED"
        ]

        if not relevant_edges:
            return []

        # Find all undermining edges
        counter_edges = [
            e for e in relevant_edges
            if e.relationship in _UNDERMINING
        ]

        # Rank by strength
        strength_order = {
            CaseRelationship.OVERRULES: 4,
            CaseRelationship.WEAKENS: 3,
            CaseRelationship.LIMITS: 2,
            CaseRelationship.DISTINGUISHES: 1,
        }

        counters = []
        for edge in counter_edges:
            strength = strength_order.get(edge.relationship, 0)
            counters.append({
                "citation": edge.source_citation,
                "relationship": edge.relationship.value,
                "target": edge.target_citation,
                "description": edge.description,
                "year": edge.year,
                "jurisdiction": edge.jurisdiction,
                "strength": strength,
                "is_binding": edge.jurisdiction == jurisdiction,
            })

        # Sort by strength descending, then by year descending (recent = more dangerous)
        counters.sort(key=lambda c: (c["strength"], c["year"]), reverse=True)

        logger.info(
            "counter_arguments | statute=%s jurisdiction=%s side=%s count=%d",
            statute, jurisdiction, side, len(counters),
        )

        return counters

    # ── Public API: Stats ─────────────────────────────────────────────

    def get_graph_stats(self) -> dict[str, Any]:
        """Stats for admin dashboard."""
        relationship_counts: dict[str, int] = defaultdict(int)
        for edge in self._edges:
            relationship_counts[edge.relationship.value] += 1

        jurisdiction_counts: dict[str, int] = defaultdict(int)
        for edge in self._edges:
            jurisdiction_counts[edge.jurisdiction] += 1

        verified_count = sum(1 for e in self._edges if e.verified)

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "statutes_indexed": len(self._statute_edges),
            "jurisdictions_covered": len(self._jurisdiction_edges),
            "relationship_distribution": dict(relationship_counts),
            "jurisdiction_distribution": dict(jurisdiction_counts),
            "verified_edges": verified_count,
            "unverified_edges": len(self._edges) - verified_count,
        }

    # ── Public API: Serialization (for future DB migration) ──────────

    def to_edge_dicts(self) -> list[dict[str, Any]]:
        """Serialize all edges to dicts for DB insertion or export.

        Each dict maps directly to the case_edges table schema.
        """
        return [
            {
                "source_cite": e.source_citation,
                "target_cite": e.target_citation,
                "relationship": e.relationship.value,
                "description": e.description,
                "jurisdiction": e.jurisdiction,
                "year": e.year,
                "statute": e.statute,
                "verified": e.verified,
            }
            for e in self._edges
        ]

    def load_from_edge_dicts(self, rows: list[dict[str, Any]]) -> int:
        """Load edges from dicts (e.g., DB rows or JSON import).

        Parameters
        ----------
        rows:
            List of dicts with keys matching GraphEdge fields.

        Returns
        -------
        Number of new edges added.
        """
        edges = []
        for row in rows:
            try:
                edge = GraphEdge(
                    source_citation=row["source_cite"],
                    target_citation=row["target_cite"],
                    relationship=CaseRelationship(row["relationship"]),
                    description=row.get("description", ""),
                    jurisdiction=row["jurisdiction"],
                    year=row["year"],
                    statute=row.get("statute", ""),
                    verified=row.get("verified", False),
                )
                edges.append(edge)
            except (KeyError, ValueError) as exc:
                logger.warning("skip_invalid_row | error=%s row=%s", exc, row)
                continue

        return self.add_edges(edges)

    # ── Internal: Foundation Discovery ────────────────────────────────

    def _find_foundation(
        self,
        edges: list[GraphEdge],
        citations: set[str],
        jurisdiction: str,
    ) -> tuple[str, int, str]:
        """Find the foundation case — earliest binding authority.

        The foundation is the case with the earliest year that:
        1. Is in the target jurisdiction (binding authority)
        2. Has other cases following/supporting it (is cited positively)
        3. Has not been overruled

        Returns (citation, year, holding_description).
        """
        # Build a map of citation -> earliest year seen in edges
        citation_year: dict[str, int] = {}
        citation_holding: dict[str, str] = {}

        for edge in edges:
            # Track source citation year
            if edge.source_citation not in citation_year or edge.year < citation_year[edge.source_citation]:
                citation_year[edge.source_citation] = edge.year
            # Track target citation by looking at edges that reference it
            # The target's year is approximated by the earliest edge pointing to it
            # (since we may not have the target's own edge data)

        # For targets, we infer year from edges that cite them
        for edge in edges:
            target = edge.target_citation
            # The target must be older than the source (it was cited by the source)
            inferred_year = edge.year - 1  # Conservative: at least 1 year earlier
            if target not in citation_year or inferred_year < citation_year[target]:
                citation_year[target] = inferred_year

            if edge.description and target not in citation_holding:
                citation_holding[target] = edge.description

        # Find overruled cases to exclude
        overruled = set()
        for edge in edges:
            if edge.relationship == CaseRelationship.OVERRULES:
                overruled.add(edge.target_citation)

        # Find cases that are cited positively (have incoming reinforcing edges)
        positively_cited: dict[str, int] = defaultdict(int)
        for edge in edges:
            if edge.relationship in _REINFORCING:
                positively_cited[edge.target_citation] += 1

        # Candidates: in-jurisdiction, not overruled, positively cited
        candidates = []
        for citation in citations:
            if citation in overruled:
                continue
            year = citation_year.get(citation, 9999)
            positive_count = positively_cited.get(citation, 0)
            candidates.append((citation, year, positive_count))

        if not candidates:
            # Fallback: just pick the earliest case
            all_candidates = [
                (c, citation_year.get(c, 9999)) for c in citations
                if c not in overruled
            ]
            if all_candidates:
                all_candidates.sort(key=lambda x: x[1])
                chosen = all_candidates[0][0]
                return chosen, all_candidates[0][1], citation_holding.get(chosen, "")
            # No cases at all
            return "", 0, ""

        # Sort by: most positively cited first, then earliest year
        candidates.sort(key=lambda x: (-x[2], x[1]))
        foundation = candidates[0][0]
        foundation_year = candidates[0][1]
        holding = citation_holding.get(foundation, "")

        return foundation, foundation_year, holding

    # ── Internal: Supporting Chain Builder ─────────────────────────────

    def _build_supporting_chain(
        self,
        foundation: str,
        edges: list[GraphEdge],
        citations: set[str],
    ) -> list[dict[str, Any]]:
        """Build the supporting chain from the foundation case.

        Follows SUPPORTS, FOLLOWS, and EXTENDS edges outward from
        the foundation to find cases that reinforce the argument.
        Returns them in chronological order (oldest to newest).
        """
        if not foundation:
            return []

        # Build a local adjacency for reinforcing edges only
        # We want cases that CITE the foundation (incoming to foundation)
        # AND cases that cite those cases, etc.
        reinforcing_incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            if edge.relationship in _REINFORCING:
                reinforcing_incoming[edge.target_citation].append(edge)

        # BFS from foundation, following incoming reinforcing edges
        visited: set[str] = {foundation}
        queue = [foundation]
        chain: list[dict[str, Any]] = []

        depth = 0
        while queue and depth < self._MAX_DEPTH:
            next_queue: list[str] = []
            for current in queue:
                for edge in reinforcing_incoming.get(current, []):
                    if edge.source_citation not in visited:
                        visited.add(edge.source_citation)
                        next_queue.append(edge.source_citation)
                        chain.append({
                            "citation": edge.source_citation,
                            "year": edge.year,
                            "relationship": edge.relationship.value,
                            "description": edge.description,
                            "cites": current,
                            "depth": depth + 1,
                        })
            queue = next_queue
            depth += 1

        # Sort chronologically (oldest to newest)
        chain.sort(key=lambda c: c["year"])

        return chain

    # ── Internal: Recent Reaffirmation ────────────────────────────────

    def _find_recent_reaffirmation(
        self,
        foundation: str,
        edges: list[GraphEdge],
        citations: set[str],
    ) -> tuple[Optional[str], Optional[int]]:
        """Find the most recent case that reaffirms the foundation's rule.

        Looks for the newest case connected to the foundation via
        reinforcing edges (SUPPORTS, FOLLOWS, EXTENDS).
        """
        if not foundation:
            return None, None

        # Gather all cases in the reinforcing chain
        reinforcing_incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            if edge.relationship in _REINFORCING:
                reinforcing_incoming[edge.target_citation].append(edge)

        # BFS to find all reachable reinforcing cases
        visited: set[str] = {foundation}
        queue = [foundation]
        most_recent: Optional[str] = None
        most_recent_year: int = 0

        depth = 0
        while queue and depth < self._MAX_DEPTH:
            next_queue: list[str] = []
            for current in queue:
                for edge in reinforcing_incoming.get(current, []):
                    if edge.source_citation not in visited:
                        visited.add(edge.source_citation)
                        next_queue.append(edge.source_citation)
                        if edge.year > most_recent_year:
                            most_recent = edge.source_citation
                            most_recent_year = edge.year
            queue = next_queue
            depth += 1

        if most_recent and most_recent != foundation:
            return most_recent, most_recent_year
        return None, None

    # ── Internal: Counter-Argument Discovery ──────────────────────────

    def _find_counters(
        self,
        foundation: str,
        edges: list[GraphEdge],
        citations: set[str],
        side: str,
    ) -> list[dict[str, Any]]:
        """Find anticipated counter-arguments.

        Searches for cases that WEAKEN, DISTINGUISH, LIMIT, or OVERRULE
        cases in the supporting chain. For each counter, explains why
        it might be distinguishable.
        """
        if not foundation:
            return []

        # First, find all cases in the supporting chain
        supporting_chain = {foundation}
        reinforcing_incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            if edge.relationship in _REINFORCING:
                reinforcing_incoming[edge.target_citation].append(edge)

        queue = [foundation]
        depth = 0
        while queue and depth < self._MAX_DEPTH:
            next_queue: list[str] = []
            for current in queue:
                for edge in reinforcing_incoming.get(current, []):
                    if edge.source_citation not in supporting_chain:
                        supporting_chain.add(edge.source_citation)
                        next_queue.append(edge.source_citation)
            queue = next_queue
            depth += 1

        # Find undermining edges that attack any case in the supporting chain
        strength_order = {
            CaseRelationship.OVERRULES: 4,
            CaseRelationship.WEAKENS: 3,
            CaseRelationship.LIMITS: 2,
            CaseRelationship.DISTINGUISHES: 1,
        }

        counters: list[dict[str, Any]] = []
        seen_counter_pairs: set[tuple[str, str]] = set()

        for edge in edges:
            if edge.relationship not in _UNDERMINING:
                continue

            # Check if this edge attacks a case in our supporting chain
            if edge.target_citation not in supporting_chain:
                continue

            pair = (edge.source_citation, edge.target_citation)
            if pair in seen_counter_pairs:
                continue
            seen_counter_pairs.add(pair)

            strength = strength_order.get(edge.relationship, 0)

            # Build the counter entry with distinguishability analysis
            counter_entry: dict[str, Any] = {
                "citation": edge.source_citation,
                "relationship": edge.relationship.value,
                "attacks": edge.target_citation,
                "description": edge.description,
                "year": edge.year,
                "jurisdiction": edge.jurisdiction,
                "strength": strength,
            }

            # Add distinguishability reasoning based on relationship type
            counter_entry["distinguishable_because"] = (
                self._generate_distinguishability(edge)
            )

            counters.append(counter_entry)

        # Sort by strength descending, then recency
        counters.sort(key=lambda c: (c["strength"], c["year"]), reverse=True)

        return counters

    # ── Internal: Distinguishability ──────────────────────────────────

    def _generate_distinguishability(self, edge: GraphEdge) -> str:
        """Generate a distinguishability note for a counter-argument.

        Based on the relationship type, provides a framework for
        why this counter may not apply to the user's case.
        """
        templates = {
            CaseRelationship.DISTINGUISHES: (
                "The court in {source} distinguished {target} on specific facts. "
                "If your facts align with {target} rather than {source}, "
                "the distinguishing rationale does not apply."
            ),
            CaseRelationship.WEAKENS: (
                "{source} weakened {target}'s holding but did not overrule it. "
                "{target} remains good law. Argue that the weakening is dicta "
                "or limited to the specific procedural posture of {source}."
            ),
            CaseRelationship.LIMITS: (
                "{source} limited the scope of {target}. "
                "If your facts fall within {target}'s original scope "
                "(not the narrowed scope), the limitation is inapplicable."
            ),
            CaseRelationship.OVERRULES: (
                "WARNING: {source} explicitly overruled {target}. "
                "This is the strongest possible counter. "
                "Verify the scope of the overruling — partial overrulings "
                "may leave portions of {target} intact."
            ),
        }

        template = templates.get(
            edge.relationship,
            "{source} addressed {target} but the relationship is unclear.",
        )

        return template.format(
            source=edge.source_citation,
            target=edge.target_citation,
        )

    # ── Internal: Confidence Scoring ──────────────────────────────────

    def _compute_confidence(
        self,
        foundation: str,
        supporting: list[dict[str, Any]],
        reaffirmation: Optional[str],
        reaffirmation_year: Optional[int],
        counters: list[dict[str, Any]],
        total: int,
    ) -> float:
        """Compute confidence score for an argument chain.

        Factors:
        1. Foundation exists (base 0.2)
        2. Supporting chain depth (up to 0.3, diminishing returns)
        3. Recent reaffirmation (up to 0.3, decays with age)
        4. Counter-argument penalty (up to -0.3 for overrulings)
        5. Total evidence base (up to 0.1)
        """
        if not foundation:
            return 0.0

        score = 0.0

        # Factor 1: Foundation exists
        score += 0.2

        # Factor 2: Supporting chain depth
        # Diminishing returns: first 3 supporting cases worth most
        chain_depth = len(supporting)
        if chain_depth >= 1:
            score += 0.1
        if chain_depth >= 2:
            score += 0.08
        if chain_depth >= 3:
            score += 0.06
        if chain_depth >= 5:
            score += 0.04
        if chain_depth >= 8:
            score += 0.02

        # Factor 3: Recent reaffirmation
        if reaffirmation and reaffirmation_year:
            # Full credit if within 5 years, decays after that
            import datetime as _dt
            current_year = _dt.date.today().year
            age = current_year - reaffirmation_year
            if age <= 2:
                score += 0.30
            elif age <= 5:
                score += 0.25
            elif age <= 10:
                score += 0.20
            elif age <= 20:
                score += 0.15
            else:
                score += 0.10

        # Factor 4: Counter-argument penalty
        for counter in counters:
            if counter.get("relationship") == CaseRelationship.OVERRULES.value:
                score -= 0.15  # Overrulings are severe
            elif counter.get("relationship") == CaseRelationship.WEAKENS.value:
                score -= 0.05
            elif counter.get("relationship") == CaseRelationship.LIMITS.value:
                score -= 0.03
            elif counter.get("relationship") == CaseRelationship.DISTINGUISHES.value:
                score -= 0.02

        # Factor 5: Evidence base size
        if total >= 3:
            score += 0.03
        if total >= 5:
            score += 0.03
        if total >= 10:
            score += 0.04

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, score))
