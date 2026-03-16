"""
Compliance & Procedure Counsel agent for Cyphergy.

The Compliance Counsel carries 10 % weight in the multi-agent ensemble
but possesses **VETO POWER**: it can reject any output from the system
that contains a procedural defect, regardless of the scores assigned by
the other agents.  ``has_veto=True`` in its ``AgentConfig``.
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.base_agent import AgentConfig, AgentRole, BaseAgent

_COMPLIANCE_COUNSEL_WEIGHT = 0.10

COMPLIANCE_COUNSEL_SYSTEM_PROMPT = """\
You are Compliance & Procedure Counsel inside the Cyphergy multi-agent
legal co-counsel platform.  You are the final gatekeeper.  No document
or strategy leaves this platform without your procedural clearance.
You hold VETO POWER over all outputs -- a single procedural defect
identified by you will block delivery regardless of all other scores.

DEADLINE VERIFICATION
- For every matter, compute all applicable deadlines from the
  triggering event (filing date, service date, order date, etc.)
  using the correct computation method for the jurisdiction.
- Federal: FRCP 6(a) -- exclude the trigger day, include the last
  day, extend to the next business day if the last day falls on a
  weekend or federal holiday.
- State: apply the specific state's computation rules, which vary
  (some states count calendar days, some count business days, some
  have unique holiday schedules).
- Electronic filing deadlines: note the cutoff time (usually
  11:59 PM local time of the court, but some jurisdictions differ).
- Serve calendar reminders at 30, 14, 7, 3, and 1 day(s) before
  every deadline.

JURISDICTIONAL RULES
- Verify that the correct court has been identified (subject matter
  jurisdiction, personal jurisdiction, venue).
- Check removal and remand eligibility for state-filed cases with
  potential federal jurisdiction.
- Verify that service of process complies with the applicable rules
  (FRCP 4 for federal, state equivalent for state courts, Hague
  Convention for international defendants).
- Confirm that the applicable statute of limitations or repose has
  not expired and that any tolling doctrines apply.
- Identify any mandatory pre-suit requirements (demand letters,
  administrative exhaustion, notice of claim, mediation).

PROCEDURAL COMPLIANCE
- Verify that every filing conforms to the local rules of the
  target court, including:
  (a) page or word limits;
  (b) font and margin requirements;
  (c) required cover pages or tables;
  (d) electronic filing format requirements (.pdf, .docx, etc.);
  (e) proposed order requirements;
  (f) certificate of service format and method.
- Verify that discovery requests comply with numerical limits
  (e.g., 25 interrogatories under FRCP 33).
- Verify that all required meet-and-confer obligations have been
  satisfied before filing discovery motions.

DATA PRIVACY COMPLIANCE
- HIPAA: verify that no protected health information (PHI) appears
  in any filing unless a protective order or HIPAA-compliant
  authorization is in place.
- GDPR: if any party or witness is an EU data subject, verify that
  data processing complies with GDPR Articles 6 and 9, and that
  cross-border transfer mechanisms (SCCs, adequacy decisions) are
  addressed.
- CCPA/CPRA: if California consumer data is at issue, verify
  compliance with notice, opt-out, and data minimisation
  requirements.
- Redaction: ensure that Social Security numbers, financial account
  numbers, dates of birth of minors, and home addresses of minors
  are redacted per FRCP 5.2 or the state equivalent.

VETO PROTOCOL
- If you identify ANY of the following, you MUST issue a VETO:
  (a) a missed or miscalculated deadline;
  (b) a filing in the wrong court or jurisdiction;
  (c) improper or incomplete service of process;
  (d) a document that exceeds page/word limits;
  (e) unredacted PII in a public filing;
  (f) a filing that violates a standing order;
  (g) a discovery motion filed without meet-and-confer;
  (h) any HIPAA, GDPR, or CCPA violation.
- A VETO includes: the specific defect, the rule violated, and
  the exact corrective action required.
- The VETO is non-negotiable.  Other agents cannot override it.

OUTPUT FORMAT
- Structure every compliance review as:
  1. DEADLINES - all computed deadlines with computation method
  2. JURISDICTIONAL CHECKLIST - court, jurisdiction, venue, service
  3. PROCEDURAL CHECKLIST - local rules compliance item by item
  4. PRIVACY CHECKLIST - HIPAA, GDPR, CCPA compliance
  5. DEFECTS FOUND - list of defects with rule references
  6. VETO STATUS - "CLEAR" or "VETO" with specific defects

CONSTRAINTS
- Never approve a document you have not fully reviewed.
- Never waive a procedural requirement.  If a rule exists, enforce it.
- When in doubt, VETO.  It is always safer to delay a filing to fix
  a defect than to file a defective document.
- You are not here to be popular.  You are here to prevent
  malpractice.
"""


class ComplianceCounsel(BaseAgent):
    """Compliance & Procedure Counsel - procedural gatekeeper with veto power.

    Weight: 10 %
    Veto: YES - can block any output with procedural defects.
    """

    def __init__(self, config: AgentConfig | None = None) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.COMPLIANCE_COUNSEL,
                weight=_COMPLIANCE_COUNSEL_WEIGHT,
                has_veto=True,
            )
        super().__init__(config)

    @property
    def system_prompt(self) -> str:
        return COMPLIANCE_COUNSEL_SYSTEM_PROMPT

    async def invoke(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a compliance review of the supplied document or strategy.

        Returns a dict containing the full review, any defects found,
        and the veto status.
        """
        messages: list[dict[str, Any]] = []
        if context:
            messages.append(
                {
                    "role": "user",
                    "content": ("Compliance review context:\n" + json.dumps(context, default=str)),
                }
            )
        messages.append({"role": "user", "content": prompt})

        content = await self._call_model(messages)
        veto_result = await self.veto_check(prompt, context)

        return {
            "content": content,
            "role": self.config.role.value,
            "veto": veto_result["veto"],
            "defects": veto_result["defects"],
            "deadlines": veto_result.get("deadlines", []),
        }

    async def score(self, response: dict[str, Any]) -> float:
        """Score a response based on procedural compliance.

        A vetoed response automatically receives a score of 0.0.
        """
        if response.get("veto", False):
            return 0.0

        scoring_prompt = (
            "Rate the following legal compliance review on a scale "
            "of 0.0 to 10.0 for thoroughness.  Consider: "
            "(1) deadline verification, (2) jurisdictional accuracy, "
            "(3) local rules compliance, (4) data privacy checks, "
            "and (5) clarity of defect descriptions.  Return ONLY a "
            'JSON object with key "score" and a float value.\n\n'
            f"Review:\n{response.get('content', '')}"
        )
        raw = await self._call_model([{"role": "user", "content": scoring_prompt}])
        try:
            return float(json.loads(raw)["score"])
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0.5

    async def veto_check(
        self,
        document_or_strategy: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Determine whether a document or strategy triggers a veto.

        This is the primary domain-specific capability of Compliance
        Counsel and the mechanism through which it exercises its veto
        power.  A veto is issued when any procedural defect is found
        that cannot be waived.

        Args:
            document_or_strategy: The text to review for procedural
                compliance.
            context: Optional case context including jurisdiction,
                deadlines, and applicable local rules.

        Returns:
            A dict with keys:
                ``veto`` (bool): True if a veto is issued.
                ``defects`` (list[dict]): Each defect has ``rule``,
                    ``description``, and ``corrective_action`` keys.
                ``deadlines`` (list[dict]): Computed deadlines if
                    applicable.
        """
        veto_prompt = (
            "Review the following legal document or strategy for "
            "procedural compliance.  Return ONLY a JSON object with:\n"
            '  "veto": true/false,\n'
            '  "defects": [{"rule": str, "description": str, '
            '"corrective_action": str}, ...],\n'
            '  "deadlines": [{"event": str, "date": str, '
            '"computation": str}, ...]\n\n'
            "Apply the strictest standard.  If ANY procedural defect "
            "is found, set veto to true.\n\n"
            f"Document/Strategy:\n{document_or_strategy}"
        )
        if context:
            veto_prompt += f"\nContext: {json.dumps(context, default=str)}"

        raw = await self._call_model([{"role": "user", "content": veto_prompt}])
        try:
            parsed = json.loads(raw)
            return {
                "veto": bool(parsed.get("veto", False)),
                "defects": parsed.get("defects", []),
                "deadlines": parsed.get("deadlines", []),
            }
        except json.JSONDecodeError:
            has_veto_signal = any(
                keyword in raw.lower() for keyword in ["veto", "defect", "violation", "non-compliant"]
            )
            return {
                "veto": has_veto_signal,
                "defects": [
                    {
                        "rule": "parse_error",
                        "description": (
                            "Could not parse structured compliance review; raw output flagged for manual review."
                        ),
                        "corrective_action": ("Re-run compliance review or perform manual procedural check."),
                    }
                ]
                if has_veto_signal
                else [],
                "deadlines": [],
            }
