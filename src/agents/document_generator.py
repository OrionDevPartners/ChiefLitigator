"""Document Generator Agent — Court-ready legal document production.

Generates properly formatted legal documents for any jurisdiction and
court. Each document passes through the Galvanizer before delivery.

Supported document types:
  - Complaints (civil, breach of contract, negligence, etc.)
  - Answers (to complaints, counterclaims)
  - Motions (to dismiss, for summary judgment, for default, etc.)
  - Discovery (interrogatories, requests for production, admissions)
  - Notices (of appearance, of hearing, of deposition)
  - Liens (mechanic's lien, judgment lien, UCC filings)
  - Immigration (I-589, motions to reopen, briefs)
  - Family (petitions, parenting plans, support calculations)
  - Letters (demand letters, cease and desist)

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.agents.document_generator")


# ---------------------------------------------------------------------------
# Document Types
# ---------------------------------------------------------------------------
class DocumentType(str, Enum):
    COMPLAINT = "complaint"
    ANSWER = "answer"
    COUNTERCLAIM = "counterclaim"
    MOTION_TO_DISMISS = "motion_to_dismiss"
    MOTION_FOR_SUMMARY_JUDGMENT = "motion_for_summary_judgment"
    MOTION_FOR_DEFAULT = "motion_for_default"
    MOTION_FOR_STAY = "motion_for_stay"
    MOTION_TO_COMPEL = "motion_to_compel"
    MOTION_IN_LIMINE = "motion_in_limine"
    EMERGENCY_MOTION = "emergency_motion"
    INTERROGATORIES = "interrogatories"
    REQUEST_FOR_PRODUCTION = "request_for_production"
    REQUEST_FOR_ADMISSIONS = "request_for_admissions"
    NOTICE_OF_APPEARANCE = "notice_of_appearance"
    NOTICE_OF_HEARING = "notice_of_hearing"
    SUBPOENA = "subpoena"
    DEMAND_LETTER = "demand_letter"
    CEASE_AND_DESIST = "cease_and_desist"
    MECHANICS_LIEN = "mechanics_lien"
    JUDGMENT_LIEN = "judgment_lien"
    UCC_FILING = "ucc_filing"
    ASYLUM_APPLICATION = "asylum_application"
    IMMIGRATION_BRIEF = "immigration_brief"
    PETITION_FOR_DISSOLUTION = "petition_for_dissolution"
    PARENTING_PLAN = "parenting_plan"
    APPELLATE_BRIEF = "appellate_brief"
    MEMORANDUM_OF_LAW = "memorandum_of_law"
    DECLARATION = "declaration"
    AFFIDAVIT = "affidavit"
    STIPULATION = "stipulation"
    SETTLEMENT_AGREEMENT = "settlement_agreement"


class DocumentSection(BaseModel):
    """A section of a legal document."""
    section_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = Field(description="Section heading")
    content: str = Field(description="Section content")
    citations: List[str] = Field(default_factory=list)
    order: int = Field(description="Section order in the document")


class GeneratedDocument(BaseModel):
    """A complete generated legal document."""
    document_id: str = Field(default_factory=lambda: f"doc-{uuid.uuid4().hex[:12]}")
    case_id: str = Field(description="Associated case ID")
    document_type: str = Field(description="Type of document")
    title: str = Field(description="Document title")
    jurisdiction: str = Field(description="Filing jurisdiction")
    court: str = Field(description="Specific court")
    caption: str = Field(description="Case caption block")
    sections: List[DocumentSection] = Field(default_factory=list)
    full_text: str = Field(description="Complete document text")
    citations_used: List[str] = Field(default_factory=list)
    galvanizer_confidence: float = Field(
        default=0.0,
        description="Confidence score from the Galvanizer",
    )
    galvanizer_session_id: Optional[str] = Field(default=None)
    version: int = Field(default=1)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = Field(default="draft", description="draft, galvanized, approved, filed")


# ---------------------------------------------------------------------------
# Court Formatting Rules
# ---------------------------------------------------------------------------
COURT_FORMAT_RULES: Dict[str, Dict[str, Any]] = {
    "federal": {
        "margin_top": "1in",
        "margin_bottom": "1in",
        "margin_left": "1in",
        "margin_right": "1in",
        "font": "Times New Roman",
        "font_size": "12pt",
        "line_spacing": "double",
        "page_numbers": "bottom_center",
        "caption_style": "centered",
        "max_pages": None,
    },
    "FL": {
        "margin_top": "1in",
        "margin_bottom": "1in",
        "margin_left": "1in",
        "margin_right": "1in",
        "font": "Times New Roman",
        "font_size": "12pt",
        "line_spacing": "double",
        "page_numbers": "bottom_center",
        "caption_style": "left_aligned",
        "max_pages": None,
    },
    "CA": {
        "margin_top": "1in",
        "margin_bottom": "0.5in",
        "margin_left": "1in",
        "margin_right": "0.5in",
        "font": "Courier",
        "font_size": "12pt",
        "line_spacing": "double",
        "page_numbers": "bottom_center",
        "caption_style": "numbered_lines",
        "max_pages": None,
        "line_numbers": True,
    },
    "NY": {
        "margin_top": "1in",
        "margin_bottom": "1in",
        "margin_left": "1in",
        "margin_right": "1in",
        "font": "Times New Roman",
        "font_size": "12pt",
        "line_spacing": "double",
        "page_numbers": "bottom_center",
        "caption_style": "left_aligned",
        "max_pages": None,
    },
    "TX": {
        "margin_top": "1in",
        "margin_bottom": "1in",
        "margin_left": "1in",
        "margin_right": "1in",
        "font": "Times New Roman",
        "font_size": "12pt",
        "line_spacing": "double",
        "page_numbers": "bottom_right",
        "caption_style": "centered",
        "max_pages": None,
    },
}


# ---------------------------------------------------------------------------
# Document Generator
# ---------------------------------------------------------------------------
class DocumentGenerator:
    """Generates court-ready legal documents.

    Usage::

        generator = DocumentGenerator()
        doc = await generator.generate(
            document_type="complaint",
            case_context="Breach of contract. Defendant failed to pay...",
            jurisdiction="FL",
            court="Broward County Circuit Court",
        )
    """

    def __init__(self, agentcore_runtime: Any = None) -> None:
        self._runtime = agentcore_runtime
        logger.info("DocumentGenerator initialized")

    async def generate(
        self,
        document_type: str,
        case_context: str,
        jurisdiction: str,
        court: Optional[str] = None,
        case_id: Optional[str] = None,
        parties: Optional[Dict[str, str]] = None,
        case_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a complete legal document.

        Args:
            document_type: Type of document to generate.
            case_context: Full case context including facts, legal theories, evidence.
            jurisdiction: Filing jurisdiction code.
            court: Specific court name.
            case_id: Associated case ID.
            parties: Dict with 'plaintiff' and 'defendant' names.
            case_number: Court case number if assigned.

        Returns:
            Dict with the generated document and metadata.
        """
        logger.info(
            "Generating document: type=%s jurisdiction=%s court=%s",
            document_type, jurisdiction, court,
        )

        # Step 1: Get court formatting rules
        format_rules = self._get_format_rules(jurisdiction)

        # Step 2: Generate the caption block
        caption = self._generate_caption(
            jurisdiction=jurisdiction,
            court=court or f"{jurisdiction} Court",
            parties=parties or {"plaintiff": "[PLAINTIFF]", "defendant": "[DEFENDANT]"},
            case_number=case_number or "[CASE NUMBER]",
            document_type=document_type,
        )

        # Step 3: Generate document content via LLM
        sections = await self._generate_content(
            document_type=document_type,
            case_context=case_context,
            jurisdiction=jurisdiction,
            court=court,
            format_rules=format_rules,
        )

        # Step 4: Assemble full document
        full_text = self._assemble_document(caption, sections, format_rules)

        # Step 5: Extract citations used
        citations = self._extract_citations(full_text)

        doc = GeneratedDocument(
            case_id=case_id or f"case-{uuid.uuid4().hex[:8]}",
            document_type=document_type,
            title=self._get_document_title(document_type),
            jurisdiction=jurisdiction,
            court=court or f"{jurisdiction} Court",
            caption=caption,
            sections=sections,
            full_text=full_text,
            citations_used=citations,
        )

        return doc.model_dump()

    def _get_format_rules(self, jurisdiction: str) -> Dict[str, Any]:
        """Get court-specific formatting rules."""
        # Check for state-specific rules first, then fall back to federal
        rules = COURT_FORMAT_RULES.get(jurisdiction, COURT_FORMAT_RULES.get("federal", {}))
        return rules

    def _generate_caption(
        self,
        jurisdiction: str,
        court: str,
        parties: Dict[str, str],
        case_number: str,
        document_type: str,
    ) -> str:
        """Generate the case caption block."""
        plaintiff = parties.get("plaintiff", "[PLAINTIFF]")
        defendant = parties.get("defendant", "[DEFENDANT]")
        doc_title = self._get_document_title(document_type).upper()

        caption = (
            f"IN THE {court.upper()}\n"
            f"\n"
            f"{plaintiff},\n"
            f"    Plaintiff,\n"
            f"\n"
            f"v.                                          Case No. {case_number}\n"
            f"\n"
            f"{defendant},\n"
            f"    Defendant.\n"
            f"{'_' * 50}\n"
            f"\n"
            f"{doc_title}\n"
            f"{'_' * 50}\n"
        )
        return caption

    async def _generate_content(
        self,
        document_type: str,
        case_context: str,
        jurisdiction: str,
        court: Optional[str],
        format_rules: Dict[str, Any],
    ) -> List[DocumentSection]:
        """Generate document content sections via LLM."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()

        # Get the document structure template
        structure = self._get_document_structure(document_type)

        prompt = (
            f"Draft a {self._get_document_title(document_type)} for filing in "
            f"{court or jurisdiction}.\n\n"
            f"CASE CONTEXT:\n{case_context}\n\n"
            f"JURISDICTION: {jurisdiction}\n\n"
            f"REQUIRED SECTIONS:\n{structure}\n\n"
            f"RULES:\n"
            f"1. Cite specific statutes and case law for {jurisdiction}\n"
            f"2. Use proper legal formatting\n"
            f"3. Include all required elements for this document type\n"
            f"4. Be thorough but concise\n"
            f"5. Every legal claim must be supported by at least one citation\n"
            f"6. Never fabricate citations — use only verified law"
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER1_MODEL", "anthropic.claude-opus-4-6-v1:0"),
            max_tokens=8192,
            temperature=0.0,
            system=(
                f"You are an expert legal document drafter for {jurisdiction} jurisdiction. "
                f"Draft court-ready documents with proper formatting, citations, and legal arguments. "
                f"Every citation must be real and verifiable."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response into sections
        sections = [DocumentSection(
            title=self._get_document_title(document_type),
            content=response.text,
            order=1,
        )]

        return sections

    def _get_document_structure(self, document_type: str) -> str:
        """Return the required structure for a document type."""
        structures = {
            "complaint": (
                "I. PARTIES\n"
                "II. JURISDICTION AND VENUE\n"
                "III. FACTUAL ALLEGATIONS\n"
                "IV. CAUSES OF ACTION\n"
                "V. PRAYER FOR RELIEF\n"
                "VI. JURY DEMAND (if applicable)\n"
                "VERIFICATION\n"
                "CERTIFICATE OF SERVICE"
            ),
            "answer": (
                "I. PRELIMINARY STATEMENT\n"
                "II. RESPONSES TO ALLEGATIONS (paragraph by paragraph)\n"
                "III. AFFIRMATIVE DEFENSES\n"
                "IV. COUNTERCLAIMS (if any)\n"
                "CERTIFICATE OF SERVICE"
            ),
            "motion_to_dismiss": (
                "I. INTRODUCTION\n"
                "II. STATEMENT OF FACTS\n"
                "III. LEGAL STANDARD\n"
                "IV. ARGUMENT\n"
                "  A. Failure to State a Claim (Rule 12(b)(6))\n"
                "  B. Lack of Subject Matter Jurisdiction (Rule 12(b)(1))\n"
                "  C. Other Grounds\n"
                "V. CONCLUSION\n"
                "CERTIFICATE OF SERVICE"
            ),
            "motion_for_summary_judgment": (
                "I. INTRODUCTION\n"
                "II. STATEMENT OF UNDISPUTED MATERIAL FACTS\n"
                "III. LEGAL STANDARD\n"
                "IV. ARGUMENT\n"
                "V. CONCLUSION\n"
                "CERTIFICATE OF SERVICE"
            ),
            "demand_letter": (
                "I. IDENTIFICATION OF PARTIES\n"
                "II. STATEMENT OF FACTS\n"
                "III. LEGAL BASIS\n"
                "IV. DEMAND\n"
                "V. DEADLINE FOR RESPONSE\n"
                "VI. CONSEQUENCES OF NON-COMPLIANCE"
            ),
            "interrogatories": (
                "DEFINITIONS\n"
                "INSTRUCTIONS\n"
                "INTERROGATORIES (numbered)\n"
                "CERTIFICATE OF SERVICE"
            ),
            "request_for_production": (
                "DEFINITIONS\n"
                "INSTRUCTIONS\n"
                "REQUESTS FOR PRODUCTION (numbered)\n"
                "CERTIFICATE OF SERVICE"
            ),
            "mechanics_lien": (
                "I. CLAIMANT INFORMATION\n"
                "II. PROPERTY DESCRIPTION\n"
                "III. PROPERTY OWNER\n"
                "IV. DESCRIPTION OF WORK/MATERIALS\n"
                "V. AMOUNT OF LIEN\n"
                "VI. DATES OF WORK\n"
                "VERIFICATION\n"
                "NOTARIZATION"
            ),
        }
        return structures.get(document_type, (
            "I. INTRODUCTION\n"
            "II. STATEMENT OF FACTS\n"
            "III. LEGAL ARGUMENT\n"
            "IV. CONCLUSION\n"
            "CERTIFICATE OF SERVICE"
        ))

    def _get_document_title(self, document_type: str) -> str:
        """Get the proper title for a document type."""
        titles = {
            "complaint": "Complaint",
            "answer": "Answer and Affirmative Defenses",
            "counterclaim": "Counterclaim",
            "motion_to_dismiss": "Motion to Dismiss",
            "motion_for_summary_judgment": "Motion for Summary Judgment",
            "motion_for_default": "Motion for Default Judgment",
            "motion_for_stay": "Motion for Stay",
            "motion_to_compel": "Motion to Compel Discovery",
            "motion_in_limine": "Motion in Limine",
            "emergency_motion": "Emergency Motion",
            "interrogatories": "Interrogatories",
            "request_for_production": "Request for Production of Documents",
            "request_for_admissions": "Request for Admissions",
            "notice_of_appearance": "Notice of Appearance",
            "demand_letter": "Demand Letter",
            "cease_and_desist": "Cease and Desist Letter",
            "mechanics_lien": "Claim of Lien",
            "memorandum_of_law": "Memorandum of Law",
            "declaration": "Declaration",
            "affidavit": "Affidavit",
            "appellate_brief": "Appellate Brief",
        }
        return titles.get(document_type, document_type.replace("_", " ").title())

    def _assemble_document(
        self,
        caption: str,
        sections: List[DocumentSection],
        format_rules: Dict[str, Any],
    ) -> str:
        """Assemble the full document from caption and sections."""
        parts = [caption, ""]
        for section in sorted(sections, key=lambda s: s.order):
            parts.append(section.content)
            parts.append("")
        return "\n".join(parts)

    def _extract_citations(self, text: str) -> List[str]:
        """Extract all legal citations from the document text."""
        import re
        patterns = [
            r"\d+\s+U\.S\.\s+\d+",
            r"\d+\s+F\.\d[a-z]*\s+\d+",
            r"\d+\s+F\.\s*Supp\.\s*\d*[a-z]*\s+\d+",
            r"\d+\s+S\.\s*Ct\.\s+\d+",
            r"\d+\s+So\.\s*\d*[a-z]*\s+\d+",
            r"\d+\s+N\.E\.\d*[a-z]*\s+\d+",
            r"\d+\s+P\.\d*[a-z]*\s+\d+",
            r"\d+\s+Cal\.\s*\d*[a-z]*\s+\d+",
            r"\d+\s+N\.Y\.\s*\d*[a-z]*\s+\d+",
            r"§\s*[\d.]+(?:\([a-z0-9]+\))*",
        ]
        citations = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            citations.update(matches)
        return sorted(citations)
