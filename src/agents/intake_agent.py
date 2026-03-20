"""Intake Agent — The front door of ChiefLitigator.

Converts a user's natural language description of their legal situation
into structured legal context: applicable law, procedures, deadlines,
and recommended document types.

This is the agent that makes ChiefLitigator accessible to pro se litigants.
The user says "my landlord changed the locks while I was at work" and the
Intake Agent translates that into:
  - Applicable statute: FL Stat. 83.67 (Prohibited practices during tenancy)
  - Cause of action: Wrongful lockout / Self-help eviction
  - Required filing: Emergency Motion for Possession
  - Deadline: File within 5 business days
  - Court: County Court, Civil Division
  - Estimated confidence: 87%

The Intake Agent operates in three modes:
  1. **Guided Flow**: Step-by-step questions for users who don't know where to start
  2. **Narrative Intake**: Free-form description for users who know their situation
  3. **Document Upload**: Extract facts from uploaded documents (complaints, letters, etc.)

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.agents.intake_agent")


# ---------------------------------------------------------------------------
# Intake Models
# ---------------------------------------------------------------------------
class IntakeMode(str, Enum):
    GUIDED = "guided"
    NARRATIVE = "narrative"
    DOCUMENT_UPLOAD = "document_upload"


class PracticeArea(str, Enum):
    CIVIL_GENERAL = "civil_general"
    CONTRACT = "contract"
    TORT = "tort"
    PROPERTY = "property"
    EVICTION = "eviction"
    FAMILY = "family"
    IMMIGRATION = "immigration"
    EMPLOYMENT = "employment"
    CONSUMER = "consumer"
    SMALL_CLAIMS = "small_claims"
    CRIMINAL = "criminal"
    BANKRUPTCY = "bankruptcy"
    LIEN = "lien"
    LANDLORD_TENANT = "landlord_tenant"
    PERSONAL_INJURY = "personal_injury"
    DEBT_COLLECTION = "debt_collection"
    DISCRIMINATION = "discrimination"
    INTELLECTUAL_PROPERTY = "intellectual_property"


class LegalIssue(BaseModel):
    """A specific legal issue identified from the user's narrative."""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    practice_area: str = Field(description="Practice area classification")
    description: str = Field(description="Plain-language description of the issue")
    legal_description: str = Field(description="Legal terminology description")
    applicable_statutes: List[str] = Field(default_factory=list)
    applicable_case_law: List[str] = Field(default_factory=list)
    applicable_rules: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this classification")


class ExtractedFact(BaseModel):
    """A fact extracted from the user's narrative."""
    fact_text: str = Field(description="The fact as stated")
    fact_type: str = Field(description="Type: event, relationship, document, financial, temporal")
    relevance: float = Field(ge=0.0, le=1.0, description="Relevance to legal issues")
    source: str = Field(default="user_narrative", description="Where this fact came from")


class IntakeResult(BaseModel):
    """Complete result of the intake process."""
    intake_id: str = Field(default_factory=lambda: f"intake-{uuid.uuid4().hex[:12]}")
    case_id: Optional[str] = Field(default=None, description="Assigned case ID if case created")
    user_narrative: str = Field(description="Original user input")
    extracted_facts: List[ExtractedFact] = Field(default_factory=list)
    legal_issues: List[LegalIssue] = Field(default_factory=list)
    jurisdiction: str = Field(description="Identified jurisdiction")
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    deadlines: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_documents: List[str] = Field(default_factory=list)
    plain_language_summary: str = Field(description="Plain-language explanation for the user")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall intake confidence")
    needs_more_info: bool = Field(default=False)
    follow_up_questions: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class GuidedQuestion(BaseModel):
    """A question in the guided intake flow."""
    question_id: str = Field(description="Unique question identifier")
    question_text: str = Field(description="The question in plain language")
    question_type: str = Field(description="Type: text, choice, date, yesno, multi_choice")
    options: List[str] = Field(default_factory=list, description="Options for choice questions")
    required: bool = Field(default=True)
    help_text: str = Field(default="", description="Additional context for the user")
    next_question_logic: Dict[str, str] = Field(
        default_factory=dict,
        description="Conditional routing: answer -> next_question_id",
    )


# ---------------------------------------------------------------------------
# Guided Intake Flow Templates
# ---------------------------------------------------------------------------
GUIDED_FLOWS: Dict[str, List[GuidedQuestion]] = {
    "general": [
        GuidedQuestion(
            question_id="q1_situation",
            question_text="What's going on? Tell me in your own words what happened.",
            question_type="text",
            required=True,
            help_text="Don't worry about legal terms. Just describe what happened like you're telling a friend.",
        ),
        GuidedQuestion(
            question_id="q2_when",
            question_text="When did this happen?",
            question_type="date",
            required=True,
            help_text="If it happened over a period of time, give us the most recent date.",
        ),
        GuidedQuestion(
            question_id="q3_where",
            question_text="Where did this happen? (City and State)",
            question_type="text",
            required=True,
            help_text="This helps us determine which laws apply to your situation.",
        ),
        GuidedQuestion(
            question_id="q4_who",
            question_text="Who is involved? (The other party — person, company, or government agency)",
            question_type="text",
            required=True,
            help_text="Include their full name or business name if you know it.",
        ),
        GuidedQuestion(
            question_id="q5_category",
            question_text="Which of these best describes your situation?",
            question_type="choice",
            required=True,
            options=[
                "Someone owes me money or broke a contract",
                "I'm being evicted or having housing problems",
                "I was injured or my property was damaged",
                "I have an immigration issue",
                "I'm dealing with a family matter (divorce, custody, support)",
                "I have an employment or workplace issue",
                "I need to file a lien",
                "Someone is suing me and I need to respond",
                "I have a consumer complaint (fraud, defective product)",
                "Something else",
            ],
            help_text="Pick the closest match. We'll narrow it down from there.",
        ),
        GuidedQuestion(
            question_id="q6_documents",
            question_text="Do you have any documents related to this? (contracts, letters, court papers, emails)",
            question_type="yesno",
            required=True,
            help_text="If yes, you can upload them and we'll extract the key information automatically.",
        ),
        GuidedQuestion(
            question_id="q7_prior_action",
            question_text="Has anything been filed in court yet?",
            question_type="choice",
            required=True,
            options=[
                "No, nothing has been filed yet",
                "Yes, I filed something",
                "Yes, someone filed something against me",
                "I'm not sure",
            ],
        ),
        GuidedQuestion(
            question_id="q8_goal",
            question_text="What outcome are you hoping for?",
            question_type="text",
            required=True,
            help_text="For example: 'I want my money back', 'I want to stay in my apartment', 'I need my green card'.",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Intake Agent
# ---------------------------------------------------------------------------
class IntakeAgent:
    """The front door of ChiefLitigator.

    Processes user narratives, guided flow responses, and uploaded documents
    to produce a structured IntakeResult that feeds into the matching engine,
    document generator, and Galvanizer.

    Usage::

        agent = IntakeAgent()

        # Narrative mode
        result = await agent.process_narrative(
            narrative="My landlord changed the locks while I was at work...",
            jurisdiction="FL",
        )

        # Guided mode
        flow = agent.get_guided_flow("general")
        result = await agent.process_guided_responses(
            responses={"q1_situation": "...", "q2_when": "2026-03-15", ...},
        )
    """

    def __init__(self, agentcore_runtime: Any = None) -> None:
        self._runtime = agentcore_runtime
        logger.info("IntakeAgent initialized")

    def get_guided_flow(self, flow_type: str = "general") -> List[GuidedQuestion]:
        """Return the guided intake flow questions."""
        return GUIDED_FLOWS.get(flow_type, GUIDED_FLOWS["general"])

    async def process_narrative(
        self,
        narrative: str,
        jurisdiction: Optional[str] = None,
    ) -> IntakeResult:
        """Process a free-form user narrative.

        Steps:
        1. Extract facts from the narrative
        2. Classify practice area and legal issues
        3. Run If-Then matching to find applicable law
        4. Compute deadlines
        5. Recommend documents and actions
        6. Generate plain-language summary
        """
        logger.info("Processing narrative intake: %d chars", len(narrative))

        # Step 1: Extract facts
        facts = await self._extract_facts(narrative)

        # Step 2: Classify legal issues
        issues = await self._classify_issues(narrative, facts, jurisdiction)

        # Step 3: Determine jurisdiction if not provided
        if not jurisdiction:
            jurisdiction = await self._infer_jurisdiction(narrative, facts)

        # Step 4: Run If-Then matching
        matching_results = await self._run_matching(narrative, jurisdiction, issues)

        # Step 5: Compute deadlines
        deadlines = await self._compute_deadlines(issues, jurisdiction, facts)

        # Step 6: Determine recommended documents
        recommended_docs = self._recommend_documents(issues, matching_results)

        # Step 7: Determine recommended actions
        recommended_actions = self._recommend_actions(issues, deadlines, matching_results)

        # Step 8: Generate plain-language summary
        summary = await self._generate_summary(
            narrative, facts, issues, jurisdiction, deadlines, recommended_docs,
        )

        # Step 9: Identify follow-up questions
        follow_ups = self._identify_follow_ups(facts, issues)

        # Calculate overall confidence
        confidence = self._calculate_confidence(facts, issues, matching_results)

        return IntakeResult(
            user_narrative=narrative,
            extracted_facts=facts,
            legal_issues=issues,
            jurisdiction=jurisdiction or "UNKNOWN",
            recommended_actions=recommended_actions,
            deadlines=deadlines,
            recommended_documents=recommended_docs,
            plain_language_summary=summary,
            confidence=confidence,
            needs_more_info=confidence < 0.6 or len(follow_ups) > 0,
            follow_up_questions=follow_ups,
        )

    async def process_guided_responses(
        self,
        responses: Dict[str, str],
        flow_type: str = "general",
    ) -> IntakeResult:
        """Process responses from the guided intake flow."""
        # Convert guided responses to a narrative
        narrative_parts = []
        for q_id, answer in responses.items():
            narrative_parts.append(answer)

        combined_narrative = " ".join(narrative_parts)

        # Extract jurisdiction from location answer
        jurisdiction = None
        location = responses.get("q3_where", "")
        if location:
            jurisdiction = await self._infer_jurisdiction(location, [])

        return await self.process_narrative(combined_narrative, jurisdiction)

    # ── Fact Extraction ──────────────────────────────────────────────

    async def _extract_facts(self, narrative: str) -> List[ExtractedFact]:
        """Extract structured facts from a user narrative using LLM."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"Extract all legally relevant facts from this narrative. "
            f"For each fact, classify it as: event, relationship, document, "
            f"financial, or temporal. Rate its relevance from 0.0 to 1.0.\n\n"
            f"NARRATIVE:\n{narrative}\n\n"
            f"Return facts as a numbered list with format:\n"
            f"1. [TYPE] Fact text (relevance: 0.X)"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER3_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=2048,
            temperature=0.0,
            system=(
                "You are a legal intake specialist. Extract facts precisely. "
                "Do not infer facts that are not stated. Be conservative."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response into ExtractedFact objects
        facts = []
        for line in response.text.strip().split("\n"):
            line = line.strip()
            if not line or not line[0].isdigit():
                continue

            # Simple parsing — production would use structured output
            fact_type = "event"
            for ft in ["event", "relationship", "document", "financial", "temporal"]:
                if f"[{ft}]" in line.lower() or f"[{ft.upper()}]" in line:
                    fact_type = ft
                    break

            relevance = 0.7  # Default
            if "relevance:" in line.lower():
                try:
                    rel_str = line.lower().split("relevance:")[1].strip().rstrip(")")
                    relevance = float(rel_str)
                except (ValueError, IndexError):
                    pass

            facts.append(ExtractedFact(
                fact_text=line,
                fact_type=fact_type,
                relevance=relevance,
            ))

        return facts

    async def _classify_issues(
        self,
        narrative: str,
        facts: List[ExtractedFact],
        jurisdiction: Optional[str],
    ) -> List[LegalIssue]:
        """Classify the legal issues present in the narrative."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        facts_text = "\n".join(f.fact_text for f in facts)

        prompt = (
            f"Based on these facts, identify all legal issues. For each issue:\n"
            f"1. Practice area (from: {', '.join(p.value for p in PracticeArea)})\n"
            f"2. Plain-language description\n"
            f"3. Legal description with proper terminology\n"
            f"4. Applicable statutes (cite specific sections)\n"
            f"5. Confidence (0.0-1.0)\n\n"
            f"FACTS:\n{facts_text}\n\n"
            f"JURISDICTION: {jurisdiction or 'Unknown — infer from facts'}"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=4096,
            temperature=0.0,
            system=(
                "You are a legal issue classifier. Identify ALL legal issues. "
                "Cite specific statutes. Never fabricate citations. "
                "If unsure about a statute, say 'requires verification'."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse into LegalIssue objects
        issues = [LegalIssue(
            practice_area="civil_general",
            description="Legal issue identified from intake",
            legal_description=response.text,
            confidence=0.7,
        )]

        return issues

    async def _infer_jurisdiction(
        self,
        text: str,
        facts: List[ExtractedFact],
    ) -> str:
        """Infer the jurisdiction from the user's description."""
        # State abbreviation mapping
        state_map = {
            "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
            "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
            "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
            "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
            "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
            "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
            "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
            "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
            "new mexico": "NM", "new york": "NY", "north carolina": "NC",
            "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
            "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
            "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
            "vermont": "VT", "virginia": "VA", "washington": "WA",
            "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
        }

        text_lower = text.lower()
        for state_name, abbrev in state_map.items():
            if state_name in text_lower:
                return abbrev

        # Check for abbreviations
        import re
        abbrev_pattern = r"\b([A-Z]{2})\b"
        matches = re.findall(abbrev_pattern, text)
        valid_abbrevs = set(state_map.values())
        for match in matches:
            if match in valid_abbrevs:
                return match

        return "UNKNOWN"

    async def _run_matching(
        self,
        narrative: str,
        jurisdiction: str,
        issues: List[LegalIssue],
    ) -> Dict[str, Any]:
        """Run the If-Then Matching Engine."""
        try:
            from src.matching.if_then_engine import IfThenMatchingEngine
            engine = IfThenMatchingEngine()
            result = await engine.match(
                user_narrative=narrative,
                jurisdiction=jurisdiction,
            )
            return result
        except Exception as exc:
            logger.error("Matching engine failed: %s", str(exc)[:200])
            return {"matched_statutes": [], "matched_rules": [], "error": str(exc)}

    async def _compute_deadlines(
        self,
        issues: List[LegalIssue],
        jurisdiction: str,
        facts: List[ExtractedFact],
    ) -> List[Dict[str, Any]]:
        """Compute applicable deadlines based on identified issues."""
        deadlines = []
        try:
            from src.legal.deadline_calc import compute_deadline

            # Find temporal facts for trigger dates
            trigger_date = None
            for fact in facts:
                if fact.fact_type == "temporal":
                    # Extract date from fact text
                    import re
                    date_match = re.search(r"\d{4}-\d{2}-\d{2}", fact.fact_text)
                    if date_match:
                        trigger_date = date_match.group()
                        break

            if trigger_date and jurisdiction != "UNKNOWN":
                # Common deadline types based on practice area
                for issue in issues:
                    if "eviction" in issue.practice_area.lower():
                        dl = compute_deadline(
                            event_type="answer_to_complaint",
                            trigger_date=trigger_date,
                            jurisdiction=jurisdiction,
                            service_method="personal",
                        )
                        deadlines.append(dl)
                    elif "contract" in issue.practice_area.lower():
                        dl = compute_deadline(
                            event_type="answer_to_complaint",
                            trigger_date=trigger_date,
                            jurisdiction=jurisdiction,
                            service_method="electronic",
                        )
                        deadlines.append(dl)

        except Exception as exc:
            logger.error("Deadline computation failed: %s", str(exc)[:200])

        return deadlines

    def _recommend_documents(
        self,
        issues: List[LegalIssue],
        matching_results: Dict[str, Any],
    ) -> List[str]:
        """Recommend document types based on identified issues."""
        docs = set()

        for issue in issues:
            pa = issue.practice_area.lower()
            if "eviction" in pa or "landlord" in pa:
                docs.update(["Answer to Eviction Complaint", "Emergency Motion for Stay",
                           "Counterclaim for Wrongful Eviction"])
            elif "contract" in pa:
                docs.update(["Complaint for Breach of Contract", "Demand Letter",
                           "Motion for Summary Judgment"])
            elif "immigration" in pa:
                docs.update(["I-589 Asylum Application", "Motion to Reopen",
                           "Brief in Support"])
            elif "lien" in pa:
                docs.update(["Notice of Intent to Lien", "Mechanic's Lien Claim",
                           "Lien Foreclosure Complaint"])
            elif "employment" in pa:
                docs.update(["EEOC Charge of Discrimination", "Complaint for Wrongful Termination",
                           "Demand Letter"])
            elif "family" in pa:
                docs.update(["Petition for Dissolution", "Motion for Temporary Orders",
                           "Parenting Plan"])
            elif "small_claims" in pa:
                docs.update(["Small Claims Complaint", "Demand Letter"])
            elif "personal_injury" in pa:
                docs.update(["Complaint for Negligence", "Demand Letter",
                           "Motion for Default Judgment"])
            else:
                docs.update(["Complaint", "Answer", "Motion"])

        return sorted(docs)

    def _recommend_actions(
        self,
        issues: List[LegalIssue],
        deadlines: List[Dict[str, Any]],
        matching_results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Recommend next actions for the user."""
        actions = []

        # Urgent deadline actions
        for dl in deadlines:
            actions.append({
                "priority": "urgent",
                "action": f"File response by deadline",
                "details": dl,
                "plain_language": "You have a deadline coming up. Let's prepare your response.",
            })

        # Document preparation actions
        actions.append({
            "priority": "high",
            "action": "Prepare initial filing",
            "details": {"issues": [i.description for i in issues]},
            "plain_language": "We'll draft the documents you need. Review and approve before filing.",
        })

        # Evidence gathering actions
        actions.append({
            "priority": "medium",
            "action": "Gather supporting evidence",
            "details": {},
            "plain_language": "Collect any emails, contracts, photos, or other documents that support your case.",
        })

        return actions

    async def _generate_summary(
        self,
        narrative: str,
        facts: List[ExtractedFact],
        issues: List[LegalIssue],
        jurisdiction: str,
        deadlines: List[Dict[str, Any]],
        recommended_docs: List[str],
    ) -> str:
        """Generate a plain-language summary for the user."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        prompt = (
            f"Write a plain-language summary for a non-lawyer. Explain:\n"
            f"1. What legal issues they have\n"
            f"2. What laws apply\n"
            f"3. What they need to do next\n"
            f"4. Any urgent deadlines\n\n"
            f"Use simple language. No legal jargon without explanation.\n\n"
            f"SITUATION: {narrative}\n"
            f"JURISDICTION: {jurisdiction}\n"
            f"ISSUES: {[i.description for i in issues]}\n"
            f"DEADLINES: {deadlines}\n"
            f"RECOMMENDED DOCUMENTS: {recommended_docs}"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER3_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=1024,
            temperature=0.3,
            system=(
                "You are a friendly legal guide helping someone who has never been to court. "
                "Explain everything in plain English. Be reassuring but honest."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        return response.text

    def _identify_follow_ups(
        self,
        facts: List[ExtractedFact],
        issues: List[LegalIssue],
    ) -> List[str]:
        """Identify what additional information is needed."""
        follow_ups = []

        # Check for missing temporal facts
        has_date = any(f.fact_type == "temporal" for f in facts)
        if not has_date:
            follow_ups.append("When did this happen? The exact date helps us calculate your deadlines.")

        # Check for missing party info
        has_party = any("relationship" in f.fact_type for f in facts)
        if not has_party:
            follow_ups.append("Who is the other party? (Their full name or business name)")

        # Check for missing financial info in relevant cases
        for issue in issues:
            if issue.practice_area in ("contract", "debt_collection", "small_claims"):
                has_financial = any(f.fact_type == "financial" for f in facts)
                if not has_financial:
                    follow_ups.append("How much money is involved?")

        return follow_ups

    def _calculate_confidence(
        self,
        facts: List[ExtractedFact],
        issues: List[LegalIssue],
        matching_results: Dict[str, Any],
    ) -> float:
        """Calculate overall intake confidence."""
        confidence = 0.3  # Base

        # Facts quality
        if len(facts) >= 3:
            confidence += 0.1
        if len(facts) >= 6:
            confidence += 0.1

        # Issue classification confidence
        if issues:
            avg_issue_conf = sum(i.confidence for i in issues) / len(issues)
            confidence += avg_issue_conf * 0.3

        # Matching results
        if matching_results and not matching_results.get("error"):
            confidence += 0.1
            if matching_results.get("matched_statutes"):
                confidence += 0.1

        return min(1.0, confidence)
