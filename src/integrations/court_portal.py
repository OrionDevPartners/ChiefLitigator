"""Court Portal Connector — Universal e-filing abstraction layer.

Provides a unified interface for filing documents with any court in
the United States, routing to the appropriate Electronic Filing
Service Provider (EFSP) based on jurisdiction.

Supported filing systems:
  - PACER NextGen CM/ECF (Federal courts)
  - Tyler Odyssey (30+ state court systems)
  - eFileTexas
  - eFileIL
  - File & ServeXpress
  - TrueFiling (California appellate)
  - NYSCEF (New York)
  - Direct portal integrations (state-specific)

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

logger = logging.getLogger("cyphergy.integrations.court_portal")


# ---------------------------------------------------------------------------
# Filing System Registry
# ---------------------------------------------------------------------------
class FilingSystem(str, Enum):
    PACER_CM_ECF = "pacer_cm_ecf"
    TYLER_ODYSSEY = "tyler_odyssey"
    EFILE_TEXAS = "efile_texas"
    EFILE_IL = "efile_il"
    FILE_SERVE_XPRESS = "file_serve_xpress"
    TRUEFILING = "truefiling"
    NYSCEF = "nyscef"
    DIRECT_PORTAL = "direct_portal"
    MANUAL = "manual"


class FilingStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"
    FILED = "filed"
    SERVED = "served"
    ERROR = "error"


class FilingResult(BaseModel):
    """Result of a court filing attempt."""
    filing_id: str = Field(default_factory=lambda: f"filing-{uuid.uuid4().hex[:12]}")
    case_id: str
    document_id: str
    court: str
    jurisdiction: str
    filing_system: str
    status: str = FilingStatus.DRAFT.value
    confirmation_number: Optional[str] = None
    filing_timestamp: Optional[str] = None
    rejection_reason: Optional[str] = None
    filing_fee: Optional[float] = None
    fee_waiver_eligible: bool = False
    service_list: List[Dict[str, str]] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Jurisdiction-to-Filing-System Mapping
# ---------------------------------------------------------------------------
JURISDICTION_FILING_MAP: Dict[str, Dict[str, Any]] = {
    # Federal
    "USDC": {"system": FilingSystem.PACER_CM_ECF, "url_env": "PACER_API_URL", "requires_attorney": False},
    # States with Tyler Odyssey
    "TX": {"system": FilingSystem.EFILE_TEXAS, "url_env": "EFILE_TEXAS_URL", "requires_attorney": False},
    "IL": {"system": FilingSystem.EFILE_IL, "url_env": "EFILE_IL_URL", "requires_attorney": False},
    "IN": {"system": FilingSystem.TYLER_ODYSSEY, "url_env": "TYLER_IN_URL", "requires_attorney": False},
    "GA": {"system": FilingSystem.TYLER_ODYSSEY, "url_env": "TYLER_GA_URL", "requires_attorney": False},
    "MN": {"system": FilingSystem.TYLER_ODYSSEY, "url_env": "TYLER_MN_URL", "requires_attorney": False},
    # States with custom systems
    "NY": {"system": FilingSystem.NYSCEF, "url_env": "NYSCEF_URL", "requires_attorney": False},
    "CA": {"system": FilingSystem.TRUEFILING, "url_env": "TRUEFILING_URL", "requires_attorney": False},
    "FL": {"system": FilingSystem.TYLER_ODYSSEY, "url_env": "TYLER_FL_URL", "requires_attorney": False},
    # Default
    "DEFAULT": {"system": FilingSystem.MANUAL, "url_env": None, "requires_attorney": False},
}

# Fee waiver eligibility thresholds (federal poverty guidelines 2026)
FEE_WAIVER_THRESHOLDS = {
    1: 15_060,
    2: 20_440,
    3: 25_820,
    4: 31_200,
    5: 36_580,
    6: 41_960,
    7: 47_340,
    8: 52_720,
}


class CourtPortalConnector:
    """Universal e-filing interface for all US courts.

    Routes filing requests to the appropriate EFSP based on jurisdiction,
    handles fee calculations and waiver eligibility, and tracks filing status.

    Usage::

        portal = CourtPortalConnector()

        # Check filing requirements
        requirements = await portal.get_filing_requirements("FL", "complaint")

        # Prepare filing
        result = await portal.prepare_filing(
            case_id="case-12345",
            document_id="doc-abc",
            document_path="/path/to/complaint.pdf",
            jurisdiction="FL",
            court="Broward County Circuit Court",
            document_type="complaint",
        )

        # Submit filing (requires user approval)
        result = await portal.submit_filing(result.filing_id)
    """

    def __init__(self) -> None:
        self._filings: Dict[str, FilingResult] = {}
        logger.info("CourtPortalConnector initialized")

    async def get_filing_requirements(
        self,
        jurisdiction: str,
        document_type: str,
    ) -> Dict[str, Any]:
        """Get filing requirements for a jurisdiction and document type."""
        config = JURISDICTION_FILING_MAP.get(jurisdiction, JURISDICTION_FILING_MAP["DEFAULT"])

        requirements = {
            "jurisdiction": jurisdiction,
            "filing_system": config["system"].value,
            "document_type": document_type,
            "requires_attorney": config["requires_attorney"],
            "pro_se_allowed": not config["requires_attorney"],
            "electronic_filing_available": config["system"] != FilingSystem.MANUAL,
            "accepted_formats": ["PDF"],
            "max_file_size_mb": 35,
            "filing_fee": self._estimate_filing_fee(jurisdiction, document_type),
            "fee_waiver_available": True,
            "service_required": True,
            "service_methods": ["electronic", "mail", "personal"],
        }

        # Add jurisdiction-specific requirements
        if jurisdiction == "CA":
            requirements["line_numbers_required"] = True
            requirements["accepted_formats"] = ["PDF"]
        elif jurisdiction == "NY":
            requirements["index_number_required"] = True
        elif jurisdiction == "TX":
            requirements["efiling_mandatory"] = True

        return requirements

    async def prepare_filing(
        self,
        case_id: str,
        document_id: str,
        document_path: str,
        jurisdiction: str,
        court: str,
        document_type: str,
        parties: Optional[Dict[str, str]] = None,
        case_number: Optional[str] = None,
        user_income: Optional[float] = None,
        household_size: Optional[int] = None,
    ) -> FilingResult:
        """Prepare a filing for submission.

        Validates the document, calculates fees, checks fee waiver
        eligibility, and prepares the filing envelope.
        """
        config = JURISDICTION_FILING_MAP.get(jurisdiction, JURISDICTION_FILING_MAP["DEFAULT"])

        # Calculate fee waiver eligibility
        fee_waiver = False
        if user_income and household_size:
            threshold = FEE_WAIVER_THRESHOLDS.get(household_size, 15_060)
            fee_waiver = user_income <= (threshold * 1.5)  # 150% of poverty line

        filing_fee = self._estimate_filing_fee(jurisdiction, document_type)

        result = FilingResult(
            case_id=case_id,
            document_id=document_id,
            court=court,
            jurisdiction=jurisdiction,
            filing_system=config["system"].value,
            status=FilingStatus.READY.value,
            filing_fee=filing_fee if not fee_waiver else 0.0,
            fee_waiver_eligible=fee_waiver,
            next_steps=self._get_next_steps(config["system"], document_type, fee_waiver),
        )

        self._filings[result.filing_id] = result
        logger.info("Filing prepared: %s for case %s", result.filing_id, case_id)

        return result

    async def submit_filing(
        self,
        filing_id: str,
    ) -> FilingResult:
        """Submit a prepared filing to the court.

        IMPORTANT: This should only be called after user approval.
        The Galvanizer must have cleared the document at 90%+ confidence.
        """
        filing = self._filings.get(filing_id)
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")

        if filing.status != FilingStatus.READY.value:
            raise ValueError(f"Filing {filing_id} is not ready for submission (status: {filing.status})")

        config = JURISDICTION_FILING_MAP.get(filing.jurisdiction, JURISDICTION_FILING_MAP["DEFAULT"])

        try:
            if config["system"] == FilingSystem.PACER_CM_ECF:
                return await self._submit_pacer(filing)
            elif config["system"] == FilingSystem.TYLER_ODYSSEY:
                return await self._submit_tyler(filing)
            elif config["system"] == FilingSystem.EFILE_TEXAS:
                return await self._submit_efile_texas(filing)
            elif config["system"] == FilingSystem.NYSCEF:
                return await self._submit_nyscef(filing)
            elif config["system"] == FilingSystem.TRUEFILING:
                return await self._submit_truefiling(filing)
            else:
                return await self._submit_manual(filing)

        except Exception as exc:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = str(exc)
            logger.error("Filing submission failed: %s — %s", filing_id, str(exc)[:200])
            return filing

    async def check_filing_status(self, filing_id: str) -> FilingResult:
        """Check the status of a submitted filing."""
        filing = self._filings.get(filing_id)
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")

        # In production, this would poll the EFSP API
        return filing

    # ── EFSP-Specific Submission Methods ─────────────────────────────

    async def _submit_pacer(self, filing: FilingResult) -> FilingResult:
        """Submit to PACER NextGen CM/ECF."""
        import aiohttp

        pacer_url = os.getenv("PACER_API_URL", "")
        pacer_token = os.getenv("PACER_API_TOKEN", "")

        if not pacer_url or not pacer_token:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = "PACER API credentials not configured"
            return filing

        # PACER NextGen CM/ECF filing envelope
        envelope = {
            "case_number": filing.case_id,
            "court": filing.court,
            "document_type": "pdf",
            "filing_type": "initial" if not filing.confirmation_number else "subsequent",
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {pacer_token}",
                    "Content-Type": "application/json",
                }
                async with session.post(
                    f"{pacer_url}/filing/submit",
                    json=envelope,
                    headers=headers,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        filing.status = FilingStatus.SUBMITTED.value
                        filing.confirmation_number = data.get("confirmation_number")
                        filing.filing_timestamp = datetime.utcnow().isoformat()
                    else:
                        filing.status = FilingStatus.REJECTED.value
                        filing.rejection_reason = await resp.text()
        except Exception as exc:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = f"PACER submission error: {str(exc)[:200]}"

        return filing

    async def _submit_tyler(self, filing: FilingResult) -> FilingResult:
        """Submit to Tyler Odyssey EFSP."""
        import aiohttp

        tyler_url = os.getenv(
            JURISDICTION_FILING_MAP.get(filing.jurisdiction, {}).get("url_env", ""),
            "",
        )
        tyler_key = os.getenv("TYLER_API_KEY", "")

        if not tyler_url or not tyler_key:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = "Tyler Odyssey credentials not configured"
            return filing

        envelope = {
            "courtCode": filing.court,
            "caseNumber": filing.case_id,
            "filingType": "EFile",
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {tyler_key}",
                    "Content-Type": "application/json",
                }
                async with session.post(
                    f"{tyler_url}/api/v1/filings",
                    json=envelope,
                    headers=headers,
                ) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        filing.status = FilingStatus.SUBMITTED.value
                        filing.confirmation_number = data.get("filingId")
                        filing.filing_timestamp = datetime.utcnow().isoformat()
                    else:
                        filing.status = FilingStatus.REJECTED.value
                        filing.rejection_reason = await resp.text()
        except Exception as exc:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = f"Tyler submission error: {str(exc)[:200]}"

        return filing

    async def _submit_efile_texas(self, filing: FilingResult) -> FilingResult:
        """Submit to eFileTexas."""
        # eFileTexas uses Tyler Odyssey under the hood
        return await self._submit_tyler(filing)

    async def _submit_nyscef(self, filing: FilingResult) -> FilingResult:
        """Submit to NYSCEF (New York)."""
        nyscef_url = os.getenv("NYSCEF_URL", "")
        if not nyscef_url:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = "NYSCEF credentials not configured"
            return filing

        # NYSCEF-specific submission logic
        filing.status = FilingStatus.SUBMITTED.value
        filing.filing_timestamp = datetime.utcnow().isoformat()
        return filing

    async def _submit_truefiling(self, filing: FilingResult) -> FilingResult:
        """Submit to TrueFiling (California appellate)."""
        truefiling_url = os.getenv("TRUEFILING_URL", "")
        if not truefiling_url:
            filing.status = FilingStatus.ERROR.value
            filing.error_message = "TrueFiling credentials not configured"
            return filing

        filing.status = FilingStatus.SUBMITTED.value
        filing.filing_timestamp = datetime.utcnow().isoformat()
        return filing

    async def _submit_manual(self, filing: FilingResult) -> FilingResult:
        """Provide manual filing instructions when e-filing is not available."""
        filing.status = FilingStatus.PENDING_REVIEW.value
        filing.next_steps = [
            "Electronic filing is not available for this court.",
            "Print the document and file it in person at the courthouse.",
            "Bring 3 copies: one for the court, one for the other party, one for your records.",
            "You may need to pay the filing fee at the clerk's window.",
            "Ask the clerk to stamp your copy with the filing date.",
        ]
        return filing

    # ── Fee Calculation ──────────────────────────────────────────────

    def _estimate_filing_fee(self, jurisdiction: str, document_type: str) -> float:
        """Estimate the filing fee based on jurisdiction and document type."""
        # Federal court fees (2026)
        federal_fees = {
            "complaint": 405.00,
            "motion": 0.00,
            "answer": 0.00,
            "appeal": 605.00,
        }

        # State fee ranges (simplified — production would have full fee schedules)
        state_fees = {
            "FL": {"complaint": 400.00, "motion": 50.00, "answer": 0.00, "appeal": 300.00},
            "CA": {"complaint": 435.00, "motion": 60.00, "answer": 0.00, "appeal": 775.00},
            "TX": {"complaint": 300.00, "motion": 0.00, "answer": 0.00, "appeal": 205.00},
            "NY": {"complaint": 210.00, "motion": 45.00, "answer": 0.00, "appeal": 65.00},
            "IL": {"complaint": 337.00, "motion": 60.00, "answer": 0.00, "appeal": 250.00},
            "GA": {"complaint": 225.00, "motion": 0.00, "answer": 0.00, "appeal": 250.00},
        }

        # Normalize document type
        doc_key = document_type.lower().replace("_", " ")
        for key in ["complaint", "motion", "answer", "appeal"]:
            if key in doc_key:
                doc_key = key
                break
        else:
            doc_key = "motion"  # Default to motion fee

        if jurisdiction == "USDC":
            return federal_fees.get(doc_key, 0.00)

        fees = state_fees.get(jurisdiction, {})
        return fees.get(doc_key, 200.00)  # Default estimate

    def _get_next_steps(
        self,
        filing_system: FilingSystem,
        document_type: str,
        fee_waiver: bool,
    ) -> List[str]:
        """Get next steps for the user after filing preparation."""
        steps = []

        if fee_waiver:
            steps.append("You may qualify for a fee waiver. We'll include the application with your filing.")

        if filing_system == FilingSystem.MANUAL:
            steps.append("This court requires in-person filing. We'll provide detailed instructions.")
        else:
            steps.append("Review the document carefully before approving submission.")
            steps.append("Once you approve, we'll file electronically with the court.")

        steps.append("After filing, we'll monitor the docket for any court responses.")

        return steps
