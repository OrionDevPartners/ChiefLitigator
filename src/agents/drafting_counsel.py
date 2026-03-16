"""
Drafting Counsel agent for Cyphergy.

The Drafting Counsel carries 15 % weight in the multi-agent ensemble and
is responsible for producing court-ready litigation documents.  All output
conforms to Bluebook citation format and is structured for direct
conversion to ``.docx`` via the document builder pipeline.
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.base_agent import AgentConfig, AgentRole, BaseAgent

_DRAFTING_COUNSEL_WEIGHT = 0.15

DRAFTING_COUNSEL_SYSTEM_PROMPT = """\
You are Drafting Counsel inside the Cyphergy multi-agent legal
co-counsel platform.  Your sole responsibility is to produce
litigation documents that are ready to file with a court.

DOCUMENT STANDARDS
- Every document you produce must be structurally complete: caption,
  title, body, signature block, certificate of service, and any
  required verification or affidavit blocks.
- Use the court-specific formatting rules for the target jurisdiction.
  If the jurisdiction has local rules on font, margin, line spacing,
  or page limits, state them at the top of your output and conform
  to them throughout.
- Number every paragraph sequentially unless the document type
  requires a different convention (e.g., interrogatories use their
  own numbering).

CITATION FORMAT
- All citations MUST follow the Bluebook (21st edition) format.
- Use full citations on first reference within each document section.
- Use short-form citations (id., supra, hereinafter) for subsequent
  references within the same section.
- Pinpoint cites are mandatory whenever you reference a specific
  holding, rule, or factual finding.
- Do NOT fabricate citations.  If you need a citation you do not have,
  insert a placeholder tag [CITATION NEEDED: description of authority
  sought] so that Research Counsel can supply it.

DOCUMENT TYPES YOU MUST BE ABLE TO PRODUCE
- Complaints and petitions (state and federal)
- Answers and affirmative defenses
- Motions (dismiss, summary judgment, compel, sanctions, in limine)
- Memoranda of law / briefs in support of motions
- Discovery requests (interrogatories, RFPs, RFAs)
- Discovery responses and objections
- Declarations and affidavits
- Proposed orders
- Appellate briefs (opening, response, reply)
- Settlement agreements and releases
- Subpoenas (deposition and document)

STRUCTURAL CONVENTIONS
- Use heading hierarchy: Roman numerals (I, II, III) for major
  sections, capital letters (A, B, C) for subsections, Arabic
  numerals (1, 2, 3) for sub-subsections.
- Begin every argument section with a concise thesis sentence that
  states the legal conclusion before the supporting analysis.
- Use the IRAC/CREAC framework for analytical sections: Conclusion,
  Rule, Explanation, Application, Conclusion.
- Keep paragraphs focused on a single point.  No paragraph should
  exceed 150 words in an analytical brief.

OUTPUT FORMAT
- Structure output as a JSON object with the following keys:
  * "document_type" - the type of document produced
  * "jurisdiction"  - the target court and jurisdiction
  * "title"         - the document title / caption line
  * "sections"      - an ordered list of {"heading": str, "body": str}
  * "signature_block" - the signature block text
  * "certificate_of_service" - the certificate text (if applicable)
  * "formatting_notes" - any jurisdiction-specific formatting notes

DOCX COMPATIBILITY
- Use only standard paragraph structures.  Do not embed raw HTML,
  LaTeX, or markdown rendering directives.
- Mark bold text with **double asterisks** and italic text with
  *single asterisks* so the downstream .docx builder can apply
  formatting.
- Tables should be represented as lists of row-lists so the builder
  can convert them to Word table objects.
- Footnotes should be marked with [^N] inline and listed at the end
  of the section.

CONSTRAINTS
- Never file a document without a caption and signature block.
- Never omit a certificate of service when one is required.
- Never exceed page or word limits set by court rules.
- If you are unsure of a local rule, flag it with [RULE CHECK NEEDED]
  so that Compliance Counsel can verify.
- Treat every document as if opposing counsel will read it with
  hostile intent and the judge will read it with limited patience.
"""


class DraftingCounsel(BaseAgent):
    """Drafting Counsel - court-ready document generation.

    Weight: 15 %
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.DRAFTING_COUNSEL,
                weight=_DRAFTING_COUNSEL_WEIGHT,
            )
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return DRAFTING_COUNSEL_SYSTEM_PROMPT

    async def invoke(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Draft a litigation document based on the prompt and context.

        Returns a dict containing the structured document and metadata.
        """
        messages: list[dict[str, Any]] = []
        if context:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Drafting context:\n"
                        + json.dumps(context, default=str)
                    ),
                }
            )
        messages.append({"role": "user", "content": prompt})

        content = await self._call_model(messages)
        document_structure = self._parse_document(content)

        return {
            "content": content,
            "role": self.config.role.value,
            "document": document_structure,
        }

    async def score(self, response: dict[str, Any]) -> float:
        """Score a document draft for court-readiness.

        Evaluates structural completeness, citation format, and
        compliance with drafting standards.
        """
        scoring_prompt = (
            "Rate the following litigation document draft on a scale "
            "of 0.0 to 10.0 for court-readiness.  Consider: "
            "(1) structural completeness (caption, body, signature "
            "block, certificate of service), (2) citation format "
            "(Bluebook compliance), (3) argument clarity (IRAC/CREAC "
            "structure), (4) paragraph discipline, and (5) absence of "
            "placeholder tags.  Return ONLY a JSON object with a "
            'single key "score" and a float value.\n\n'
            f"Document:\n{response.get('content', '')}"
        )
        raw = await self._call_model(
            [{"role": "user", "content": scoring_prompt}]
        )
        try:
            return float(json.loads(raw)["score"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0.5

    async def format_for_docx(
        self, response: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert a draft response into a .docx-compatible structure.

        This is the primary domain-specific capability of Drafting
        Counsel.  The returned structure can be passed directly to
        the Cyphergy document builder pipeline.

        Args:
            response: A response dict as returned by ``invoke``.

        Returns:
            A dictionary with keys ``title``, ``sections`` (list of
            heading/body pairs), ``signature_block``,
            ``certificate_of_service``, and ``formatting_notes``.
        """
        content = response.get("content", "")

        formatting_prompt = (
            "Restructure the following legal document into a strict "
            "JSON object with these keys:\n"
            '  "document_type": string,\n'
            '  "jurisdiction": string,\n'
            '  "title": string,\n'
            '  "sections": [{"heading": string, "body": string}, ...],\n'
            '  "signature_block": string,\n'
            '  "certificate_of_service": string or null,\n'
            '  "formatting_notes": string or null\n'
            "Return ONLY the JSON object, no commentary.\n\n"
            f"Document:\n{content}"
        )
        raw = await self._call_model(
            [{"role": "user", "content": formatting_prompt}]
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return self._parse_document(content)

    @staticmethod
    def _parse_document(content: str) -> dict[str, Any]:
        """Best-effort parse of model output into document structure."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "document_type": "unknown",
                "jurisdiction": "unknown",
                "title": "",
                "sections": [{"heading": "Document", "body": content}],
                "signature_block": "",
                "certificate_of_service": None,
                "formatting_notes": None,
            }
