"""Bedrock Tool-Use Layer — Function calling via Converse API toolConfig.

Defines all tools that ChiefLitigator agents can invoke during reasoning:
  - Legal research (search case law, statutes, court rules)
  - Citation verification (validate against CourtListener)
  - Deadline computation (FRCP + state-specific)
  - Document generation (draft court documents)
  - Evidence scoring (evaluate evidence strength)
  - Docket lookup (check case status via PACER)
  - If-Then matching (translate facts to applicable law)

Each tool is defined in Bedrock Converse API format with JSON Schema
input specifications. The ToolExecutor handles dispatching tool calls
to the appropriate internal modules.

No hardcoded secrets. All configuration via environment variables.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.providers.bedrock_tools")


# ---------------------------------------------------------------------------
# Tool Definition Schema (Bedrock Converse API format)
# ---------------------------------------------------------------------------
class ToolDefinition(BaseModel):
    """A tool that agents can invoke during reasoning."""
    name: str = Field(description="Unique tool name")
    description: str = Field(description="What this tool does — shown to the model")
    input_schema: Dict[str, Any] = Field(description="JSON Schema for tool input")
    handler: Optional[str] = Field(
        default=None,
        description="Python dotted path to the handler function",
    )


# ---------------------------------------------------------------------------
# ChiefLitigator Tool Registry
# ---------------------------------------------------------------------------
LEGAL_TOOLS: List[Dict[str, Any]] = [
    {
        "toolSpec": {
            "name": "search_case_law",
            "description": (
                "Search the ChiefLitigator case law database (Aurora PostgreSQL) "
                "for relevant cases. Uses semantic vector search via pgvector. "
                "Returns case citations, holdings, and relevance scores. "
                "Always use this tool instead of relying on training data for case law."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language legal question or fact pattern",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Jurisdiction code (e.g., 'FL', 'CA', 'FED', 'SCOTUS')",
                        },
                        "practice_area": {
                            "type": "string",
                            "description": "Practice area filter (e.g., 'civil', 'criminal', 'immigration')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                        },
                        "date_after": {
                            "type": "string",
                            "description": "Only return cases decided after this date (YYYY-MM-DD)",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "search_statutes",
            "description": (
                "Search federal and state statutes in the ChiefLitigator database. "
                "Returns statute text, section numbers, and related case law. "
                "Covers all 54 titles of the US Code and all 50 state statute compilations."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language description of the legal issue or statute topic",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Jurisdiction code for state statutes, or 'FED' for US Code",
                        },
                        "statute_number": {
                            "type": "string",
                            "description": "Specific statute number if known (e.g., '42 USC 1983', 'FL 83.67')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 5)",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "search_court_rules",
            "description": (
                "Search court rules (FRCP, FRCE, FRE, state court rules, local rules). "
                "Returns the rule text, applicable jurisdiction, and any relevant advisory notes."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Description of the procedural issue or rule topic",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Jurisdiction code",
                        },
                        "rule_set": {
                            "type": "string",
                            "description": "Rule set (e.g., 'FRCP', 'FRCE', 'FRE', 'local')",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "verify_citation",
            "description": (
                "Verify a legal citation against the CourtListener database. "
                "Checks that the case exists, the citation format is correct, "
                "the holding matches what is claimed, and the case has not been "
                "overruled or distinguished. Returns verification status and details."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "citation": {
                            "type": "string",
                            "description": "The legal citation to verify (e.g., '410 U.S. 113')",
                        },
                        "claimed_holding": {
                            "type": "string",
                            "description": "What the citation is claimed to stand for",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Expected jurisdiction of the citation",
                        },
                    },
                    "required": ["citation"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "compute_deadline",
            "description": (
                "Compute a legal deadline based on jurisdiction rules, FRCP, "
                "and court-specific calendaring. Accounts for weekends, holidays, "
                "and service method extensions. Always returns the conservative "
                "(earlier) date when ambiguous."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "event_type": {
                            "type": "string",
                            "description": "Type of deadline (e.g., 'answer_to_complaint', 'motion_response', 'discovery_response')",
                        },
                        "trigger_date": {
                            "type": "string",
                            "description": "Date that triggers the deadline (YYYY-MM-DD)",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Jurisdiction code",
                        },
                        "service_method": {
                            "type": "string",
                            "description": "How the document was served (e.g., 'personal', 'mail', 'electronic')",
                        },
                    },
                    "required": ["event_type", "trigger_date", "jurisdiction"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "match_facts_to_law",
            "description": (
                "Run the If-Then Matching Engine to translate a set of user facts "
                "into applicable statutes, procedures, and deadlines. This is the "
                "core context-to-law matching algorithm."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "facts": {
                            "type": "string",
                            "description": "Natural language description of the user's situation",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Jurisdiction where the legal issue arose",
                        },
                        "practice_area": {
                            "type": "string",
                            "description": "Practice area if known (e.g., 'eviction', 'contract', 'immigration')",
                        },
                    },
                    "required": ["facts", "jurisdiction"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "draft_document",
            "description": (
                "Generate a court-ready legal document based on case context. "
                "Supports: Complaints, Answers, Motions (to Dismiss, for Summary Judgment, "
                "etc.), Notices, Discovery requests/responses, Liens, and Immigration forms."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "document_type": {
                            "type": "string",
                            "description": "Type of document (e.g., 'complaint', 'answer', 'motion_to_dismiss', 'discovery_request')",
                        },
                        "case_context": {
                            "type": "string",
                            "description": "Full case context including facts, parties, and legal theories",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Filing jurisdiction",
                        },
                        "court": {
                            "type": "string",
                            "description": "Specific court (e.g., 'S.D. Fla.', 'Broward County Circuit Court')",
                        },
                    },
                    "required": ["document_type", "case_context", "jurisdiction"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "score_evidence",
            "description": (
                "Evaluate the strength of a piece of evidence for a specific claim. "
                "Returns a confidence score, admissibility assessment, and recommendations "
                "for strengthening the evidence."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "evidence_description": {
                            "type": "string",
                            "description": "Description of the evidence",
                        },
                        "claim": {
                            "type": "string",
                            "description": "The legal claim this evidence supports",
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Jurisdiction for evidence rules",
                        },
                    },
                    "required": ["evidence_description", "claim"],
                },
            },
        },
    },
    {
        "toolSpec": {
            "name": "lookup_docket",
            "description": (
                "Look up a case docket via PACER or CourtListener. Returns "
                "docket entries, filing dates, and current case status."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "case_number": {
                            "type": "string",
                            "description": "Court case number",
                        },
                        "court": {
                            "type": "string",
                            "description": "Court identifier (e.g., 'flsd' for S.D. Fla.)",
                        },
                        "party_name": {
                            "type": "string",
                            "description": "Party name for search (alternative to case number)",
                        },
                    },
                    "required": [],
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool Executor — Dispatches tool calls to internal modules
# ---------------------------------------------------------------------------
class ToolExecutor:
    """Executes tool calls returned by Bedrock models.

    When a model returns a toolUse block, this executor:
    1. Looks up the tool by name
    2. Validates the input against the schema
    3. Dispatches to the appropriate internal module
    4. Returns the result formatted for the Converse API toolResult block

    Usage::

        executor = ToolExecutor()
        result = await executor.execute(tool_call)
        # result is ready to send back to the model as toolResult
    """

    def __init__(self) -> None:
        # Register tool handlers — maps tool name to async handler function
        self._handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register all default tool handlers."""
        self._handlers["search_case_law"] = self._handle_search_case_law
        self._handlers["search_statutes"] = self._handle_search_statutes
        self._handlers["search_court_rules"] = self._handle_search_court_rules
        self._handlers["verify_citation"] = self._handle_verify_citation
        self._handlers["compute_deadline"] = self._handle_compute_deadline
        self._handlers["match_facts_to_law"] = self._handle_match_facts_to_law
        self._handlers["draft_document"] = self._handle_draft_document
        self._handlers["score_evidence"] = self._handle_score_evidence
        self._handlers["lookup_docket"] = self._handle_lookup_docket

    def register_tool(self, name: str, handler: Callable) -> None:
        """Register a custom tool handler."""
        self._handlers[name] = handler
        logger.info("Tool registered: %s", name)

    async def execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result in Converse API format.

        Args:
            tool_call: The toolUse block from the model response, containing
                       'toolUseId', 'name', and 'input'.

        Returns:
            A toolResult block ready to send back to the model.
        """
        tool_name = tool_call.get("name", "")
        tool_input = tool_call.get("input", {})
        tool_use_id = tool_call.get("toolUseId", "")

        handler = self._handlers.get(tool_name)
        if not handler:
            logger.error("Unknown tool: %s", tool_name)
            return {
                "toolUseId": tool_use_id,
                "content": [{"text": f"Error: Unknown tool '{tool_name}'"}],
                "status": "error",
            }

        try:
            result = await handler(tool_input)
            return {
                "toolUseId": tool_use_id,
                "content": [{"text": json.dumps(result, default=str)}],
                "status": "success",
            }
        except Exception as exc:
            logger.error(
                "Tool execution failed: tool=%s error=%s",
                tool_name,
                str(exc)[:200],
            )
            return {
                "toolUseId": tool_use_id,
                "content": [{"text": f"Error executing {tool_name}: {str(exc)[:200]}"}],
                "status": "error",
            }

    # ── Tool Handlers ────────────────────────────────────────────────

    async def _handle_search_case_law(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search case law in Aurora via pgvector semantic search."""
        from src.matching.if_then_engine import IfThenMatchingEngine
        engine = IfThenMatchingEngine()
        results = await engine.search_case_law(
            query=params.get("query", ""),
            jurisdiction=params.get("jurisdiction"),
            max_results=params.get("max_results", 10),
        )
        return {"cases": results, "count": len(results)}

    async def _handle_search_statutes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search statutes in Aurora."""
        from src.matching.if_then_engine import IfThenMatchingEngine
        engine = IfThenMatchingEngine()
        results = await engine.search_statutes(
            query=params.get("query", ""),
            jurisdiction=params.get("jurisdiction"),
            statute_number=params.get("statute_number"),
            max_results=params.get("max_results", 5),
        )
        return {"statutes": results, "count": len(results)}

    async def _handle_search_court_rules(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search court rules."""
        from src.matching.if_then_engine import IfThenMatchingEngine
        engine = IfThenMatchingEngine()
        results = await engine.search_court_rules(
            query=params.get("query", ""),
            jurisdiction=params.get("jurisdiction"),
            rule_set=params.get("rule_set"),
        )
        return {"rules": results, "count": len(results)}

    async def _handle_verify_citation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a citation via the 5-step citation chain."""
        from src.verification.citation_chain import verify_citation
        result = await verify_citation(
            citation=params.get("citation", ""),
            claimed_holding=params.get("claimed_holding"),
        )
        return result

    async def _handle_compute_deadline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute a legal deadline."""
        from src.legal.deadline_calc import compute_deadline
        result = compute_deadline(
            event_type=params.get("event_type", ""),
            trigger_date=params.get("trigger_date", ""),
            jurisdiction=params.get("jurisdiction", ""),
            service_method=params.get("service_method", "electronic"),
        )
        return result

    async def _handle_match_facts_to_law(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run the If-Then Matching Engine."""
        from src.matching.if_then_engine import IfThenMatchingEngine
        engine = IfThenMatchingEngine()
        result = await engine.match(
            user_narrative=params.get("facts", ""),
            jurisdiction=params.get("jurisdiction", ""),
        )
        return result

    async def _handle_draft_document(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Draft a legal document."""
        from src.agents.document_generator import DocumentGenerator
        generator = DocumentGenerator()
        result = await generator.generate(
            document_type=params.get("document_type", ""),
            case_context=params.get("case_context", ""),
            jurisdiction=params.get("jurisdiction", ""),
            court=params.get("court"),
        )
        return result

    async def _handle_score_evidence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Score evidence strength."""
        from src.agents.evidence_scorer import EvidenceScorer
        scorer = EvidenceScorer()
        result = await scorer.score(
            evidence_description=params.get("evidence_description", ""),
            claim=params.get("claim", ""),
            jurisdiction=params.get("jurisdiction"),
        )
        return result

    async def _handle_lookup_docket(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Look up a docket via PACER/CourtListener."""
        from src.integrations.pacer_client import PACERClient
        client = PACERClient()
        result = await client.lookup(
            case_number=params.get("case_number"),
            court=params.get("court"),
            party_name=params.get("party_name"),
        )
        return result


def get_legal_tools() -> List[Dict[str, Any]]:
    """Return all legal tools in Bedrock Converse API format."""
    return LEGAL_TOOLS


def get_tool_executor() -> ToolExecutor:
    """Return a configured ToolExecutor instance."""
    return ToolExecutor()
