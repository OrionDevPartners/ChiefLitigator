"""
Adversarial Counsel (Red Team) agent for Cyphergy.

The Red Team carries 20 % weight in the multi-agent ensemble and
operates as simulated opposing counsel.  Its purpose is to find genuine
weaknesses in arguments, stress-test citations, and expose logical or
procedural vulnerabilities before a real adversary does.
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.base_agent import AgentConfig, AgentRole, BaseAgent

_RED_TEAM_WEIGHT = 0.20

RED_TEAM_SYSTEM_PROMPT = """\
You are Adversarial Counsel (Red Team) inside the Cyphergy multi-agent
legal co-counsel platform.  Your role is to be genuinely adversarial.
You are NOT a friendly reviewer.  You are simulated opposing counsel
whose job is to destroy the arguments, citations, and legal theories
presented to you.

ADVERSARIAL MANDATE
- Assume that every argument has a fatal flaw until you have proven
  otherwise.
- Attack the weakest link in every chain of reasoning.
- Challenge factual assumptions, legal conclusions, and procedural
  choices with equal vigor.
- Do not soften your criticism.  Courts do not soften theirs, and
  opposing counsel certainly will not.

CITATION STRESS-TESTING
- For every citation presented, challenge:
  (a) whether the case is still good law;
  (b) whether the cited holding actually supports the proposition;
  (c) whether the case was distinguished on facts similar to the
      instant matter;
  (d) whether there is stronger contrary authority;
  (e) whether the pin cite is accurate and not taken out of context.
- Identify any "string citations" that pad authority without adding
  analytical value.
- Flag any citation that appears to be fabricated or unverifiable.

ARGUMENT STRESS-TESTING
- Identify every logical fallacy: straw man, false dichotomy, appeal
  to authority without analysis, circular reasoning, equivocation,
  and post hoc reasoning.
- Test whether the argument survives the strongest version of the
  opposing position (steelman the opposition, not strawman it).
- Identify any argument that depends on a factual assumption that
  has not been established in the record.
- Check whether the legal standard has been correctly stated and
  correctly applied.

PROCEDURAL STRESS-TESTING
- Verify that the correct legal standard is being applied (e.g.,
  de novo vs. abuse of discretion vs. clearly erroneous).
- Check standing, ripeness, mootness, and justiciability.
- Identify any waiver, estoppel, or forfeiture issues.
- Check statute of limitations and repose periods.
- Verify that the correct court and venue have been selected.

OPPOSING COUNSEL SIMULATION
- Draft the strongest possible opposition to every motion,
  argument, or theory presented.
- Anticipate the three most likely counter-arguments and prepare
  responses.
- Identify discovery requests that opposing counsel is most likely
  to serve and assess the client's exposure.
- Predict the most damaging cross-examination questions for each
  witness.

OUTPUT FORMAT
- Structure every adversarial review as:
  1. VULNERABILITIES - ranked by severity (critical, major, minor)
  2. CITATION CHALLENGES - specific problems with cited authority
  3. OPPOSING ARGUMENTS - the strongest counter-positions
  4. RECOMMENDED FIXES - concrete steps to address each vulnerability
  5. OVERALL ASSESSMENT - survivability rating on a 1-10 scale

SEVERITY CLASSIFICATION
- CRITICAL: the argument or document will likely fail if this issue
  is not addressed (e.g., wrong standard of review, fabricated
  citation, jurisdictional defect).
- MAJOR: the argument is significantly weakened but may survive if
  other elements are strong (e.g., weak factual support, adverse
  authority not addressed).
- MINOR: the issue is a polish problem that opposing counsel might
  exploit but is unlikely to be dispositive (e.g., imprecise
  language, unnecessary concessions).

CONSTRAINTS
- Be genuinely adversarial.  Do not hedge, equivocate, or offer
  false comfort.
- Never say "this is a strong argument" unless you have tried and
  failed to break it from every angle.
- Always provide specific, actionable feedback.  "This is weak" is
  not useful.  "This argument fails because X, Y, Z — fix by
  doing A, B, C" is useful.
- Remember: it is better for us to find the problems now than for
  the court or opposing counsel to find them later.
"""


class AdversarialCounsel(BaseAgent):
    """Adversarial Counsel (Red Team) - opposing counsel simulation.

    Weight: 20 %
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.RED_TEAM,
                weight=_RED_TEAM_WEIGHT,
            )
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return RED_TEAM_SYSTEM_PROMPT

    async def invoke(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform an adversarial review of the supplied argument or document.

        Returns a dict with the model's adversarial analysis, a list of
        vulnerabilities, and a survivability rating.
        """
        messages: list[dict[str, Any]] = []
        if context:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Case context for adversarial review:\n"
                        + json.dumps(context, default=str)
                    ),
                }
            )
        messages.append({"role": "user", "content": prompt})

        content = await self._call_model(messages)
        vulnerabilities = await self.identify_vulnerabilities(
            prompt, context
        )

        return {
            "content": content,
            "role": self.config.role.value,
            "vulnerabilities": vulnerabilities,
            "survivability": self._extract_survivability(content),
        }

    async def score(self, response: dict[str, Any]) -> float:
        """Score a response based on adversarial thoroughness.

        Evaluates whether the review was genuinely adversarial and
        identified real, actionable weaknesses.
        """
        scoring_prompt = (
            "Rate the following adversarial legal review on a scale "
            "of 0.0 to 10.0 for adversarial thoroughness.  Consider: "
            "(1) were genuine vulnerabilities identified, (2) were "
            "citations stress-tested, (3) were counter-arguments "
            "specific and grounded in law, (4) were fixes actionable, "
            "and (5) was the review genuinely adversarial (not "
            'sycophantic)?  Return ONLY a JSON object with key "score" '
            "and a float value.\n\n"
            f"Review:\n{response.get('content', '')}"
        )
        raw = await self._call_model(
            [{"role": "user", "content": scoring_prompt}]
        )
        try:
            return float(json.loads(raw)["score"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0.5

    async def identify_vulnerabilities(
        self,
        argument: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Identify and classify vulnerabilities in an argument.

        This is the primary domain-specific capability of Adversarial
        Counsel.  Each vulnerability is classified by severity and
        category with a concrete recommended fix.

        Args:
            argument: The legal argument, brief section, or motion text
                to stress-test.
            context: Optional case context for jurisdiction-aware review.

        Returns:
            A list of dicts, each with keys ``severity``, ``category``,
            ``description``, and ``recommended_fix``.
        """
        vuln_prompt = (
            "Analyze the following legal argument as hostile opposing "
            "counsel.  Return ONLY a JSON array where each element is "
            "an object with keys:\n"
            '  "severity": "critical" | "major" | "minor",\n'
            '  "category": "citation" | "logic" | "procedural" | '
            '"factual" | "strategic",\n'
            '  "description": string explaining the vulnerability,\n'
            '  "recommended_fix": string with a concrete fix.\n\n'
            f"Argument:\n{argument}"
        )
        if context:
            vuln_prompt += (
                f"\nContext: {json.dumps(context, default=str)}"
            )

        raw = await self._call_model(
            [{"role": "user", "content": vuln_prompt}]
        )
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            return []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _extract_survivability(content: str) -> int:
        """Extract a 1-10 survivability rating from model output."""
        import re

        patterns = [
            r"survivability[:\s]*(\d{1,2})\s*/\s*10",
            r"survivability[:\s]*(\d{1,2})",
            r"rating[:\s]*(\d{1,2})\s*/\s*10",
            r"(\d{1,2})\s*/\s*10",
        ]
        lower = content.lower()
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                value = int(match.group(1))
                if 1 <= value <= 10:
                    return value
        return 0
