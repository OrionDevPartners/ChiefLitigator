"""
Research & Citation Counsel agent for Cyphergy.

The Research Counsel carries 25 % weight in the multi-agent ensemble and
is the only agent authorised to assert that a legal citation is valid.
All citation work MUST pass through the ``CitationVerifier`` from
``src/verification/citation_chain`` -- the model's parametric memory is
never treated as a reliable source for case names, reporters, or pin
cites.
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.base_agent import AgentConfig, AgentRole, BaseAgent
from src.verification.citation_chain import CitationVerifier

_RESEARCH_COUNSEL_WEIGHT = 0.25

RESEARCH_COUNSEL_SYSTEM_PROMPT = """\
You are Research & Citation Counsel inside the Cyphergy multi-agent
legal co-counsel platform.  Your sole mission is to find, verify, and
deliver authoritative legal authority that supports (or undermines) a
given legal proposition.

ANTI-HALLUCINATION PROTOCOL
- You MUST NOT cite any case, statute, regulation, or rule from memory.
  Every citation you produce will be verified against external sources
  (CourtListener API) before it is accepted.
- If you cannot locate authority through verified sources, state that
  no authority was found rather than inventing a citation.
- When referencing a case, always include: full case name, volume,
  reporter, page, pin cite (if applicable), court, and year.
- When referencing a statute, include title, section, and the current
  version year.
- When referencing a regulation, include title, part, section, and
  the Federal Register date if relevant.

RESEARCH METHODOLOGY
- Begin every research task by identifying the precise legal question
  presented.
- Identify the controlling jurisdiction and any secondary jurisdictions
  whose authority may be persuasive.
- Search for binding authority first (same jurisdiction, same court
  level or higher).  Only cite persuasive authority when binding
  authority is absent or when a split exists.
- Organise authority hierarchically: constitutional provisions, then
  statutes, then regulations, then binding case law, then persuasive
  case law, then secondary sources.
- For each authority, provide a relevance summary explaining how it
  applies to the legal question.

CITATION FORMAT
- All citations MUST follow the Bluebook (21st edition) format.
- Use full citations on first reference and short-form citations
  thereafter within the same document section.
- Include subsequent history (affirmed, reversed, vacated, etc.)
  when material to the argument.
- Parallel citations are required only when the applicable court
  rules mandate them.

VERIFICATION REQUIREMENTS
- Every case citation must be checked for:
  (a) existence -- the case actually exists in the reporter;
  (b) accuracy  -- volume, reporter, and page are correct;
  (c) status    -- the case has not been overruled, vacated, or
      otherwise rendered non-authoritative on the point cited;
  (d) relevance -- the cited holding actually supports the
      proposition for which it is offered.
- If a citation fails any of these checks, flag it with a
  [CITATION WARNING] tag and explain the deficiency.

SHEPARDIZING / KEYCITE EQUIVALENT
- For every primary authority, note whether it has been:
  (a) followed, (b) distinguished, (c) criticized, (d) overruled.
- Present negative treatment prominently so that Lead Counsel and
  Adversarial Counsel can assess risk.

OUTPUT FORMAT
- Return research memos with the following sections:
  1. Question Presented
  2. Short Answer
  3. Controlling Authority (with verification status)
  4. Persuasive Authority (with verification status)
  5. Adverse Authority (with verification status)
  6. Analysis
  7. Gaps and Recommendations

CONSTRAINTS
- Never fabricate or embellish authority.
- Never present unverified citations as verified.
- Always disclose when the research is incomplete and state what
  additional sources should be consulted.
- Express confidence levels for each cited authority.
"""


class ResearchCounsel(BaseAgent):
    """Research & Citation Counsel - legal research and citation verification.

    Weight: 25 %
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.RESEARCH_COUNSEL,
                weight=_RESEARCH_COUNSEL_WEIGHT,
            )
        super().__init__(config)
        self._verifier = CitationVerifier()

    @property
    def system_prompt(self) -> str:
        return RESEARCH_COUNSEL_SYSTEM_PROMPT

    async def invoke(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform legal research and return a verified research memo.

        Every citation in the model output is extracted and verified
        through the ``CitationVerifier`` before the response is returned.
        """
        messages: list[dict[str, Any]] = []
        if context:
            messages.append(
                {
                    "role": "user",
                    "content": ("Research context:\n" + json.dumps(context, default=str)),
                }
            )
        messages.append({"role": "user", "content": prompt})

        content = await self._call_model(messages)

        citations = self._verifier.extract_citations(content)
        verification_results = await self._verifier.verify_batch(citations)

        verified_citations: list[dict[str, Any]] = []
        for result in verification_results:
            verified_citations.append(
                {
                    "citation": result.raw,
                    "valid": result.valid,
                    "status": result.status.value,
                    "source_url": result.source_url,
                    "errors": result.errors,
                }
            )

        return {
            "content": content,
            "role": self.config.role.value,
            "citations": verified_citations,
            "citation_count": len(citations),
            "verified_count": sum(1 for r in verification_results if r.valid),
        }

    async def score(self, response: dict[str, Any]) -> float:
        """Score a response based on citation accuracy and completeness.

        The score is a weighted combination of citation verification
        rate and the model's self-assessed research thoroughness.
        """
        citation_count = response.get("citation_count", 0)
        verified_count = response.get("verified_count", 0)

        if citation_count > 0:
            verification_ratio = verified_count / citation_count
        else:
            verification_ratio = 0.0

        scoring_prompt = (
            "Rate the following legal research memo on a scale of 0.0 "
            "to 1.0 for thoroughness.  Consider whether it addresses: "
            "(1) the precise question presented, (2) binding authority, "
            "(3) persuasive authority, (4) adverse authority, and "
            "(5) gaps in the research.  Return ONLY a JSON object with "
            'a single key "score" and a float value.\n\n'
            f"Memo:\n{response.get('content', '')}"
        )
        raw = await self._call_model([{"role": "user", "content": scoring_prompt}])
        try:
            thoroughness = float(json.loads(raw)["score"])
        except (json.JSONDecodeError, KeyError, ValueError):
            thoroughness = 0.5

        return 0.6 * verification_ratio + 0.4 * thoroughness

    async def verify_citations(self, text: str) -> list[dict[str, Any]]:
        """Extract and verify all citations found in *text*.

        This is the primary domain-specific capability of Research
        Counsel.  Other agents should delegate citation verification
        to this method.

        Args:
            text: Free-form legal text containing inline citations.

        Returns:
            A list of dicts, each containing ``citation``, ``valid``,
            ``status``, ``source_url``, and ``errors`` keys.
        """
        citations = self._verifier.extract_citations(text)
        results = await self._verifier.verify_batch(citations)
        return [
            {
                "citation": r.raw,
                "valid": r.valid,
                "status": r.status.value,
                "source_url": r.source_url,
                "errors": r.errors,
            }
            for r in results
        ]
