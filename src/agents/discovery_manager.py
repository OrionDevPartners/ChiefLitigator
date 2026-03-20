"""Discovery Manager Agent — Document ingestion, OCR, privilege detection, and production.

Handles the full discovery lifecycle:
  1. Ingestion: Upload documents (PDF, images, emails, spreadsheets)
  2. OCR: Extract text from scanned documents and images
  3. Classification: Auto-classify document types and relevance
  4. Privilege Detection: Flag attorney-client privilege, work product, and other protections
  5. Evidence Mapping: Map documents to claims and legal issues
  6. Production: Generate privilege logs and production sets
  7. Review: Coordinate document review workflows

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

logger = logging.getLogger("cyphergy.agents.discovery_manager")


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    CLASSIFIED = "classified"
    PRIVILEGE_REVIEWED = "privilege_reviewed"
    READY_FOR_PRODUCTION = "ready_for_production"
    PRODUCED = "produced"
    WITHHELD = "withheld"


class PrivilegeType(str, Enum):
    NONE = "none"
    ATTORNEY_CLIENT = "attorney_client"
    WORK_PRODUCT = "work_product"
    JOINT_DEFENSE = "joint_defense"
    SPOUSAL = "spousal"
    MEDICAL = "medical"
    TRADE_SECRET = "trade_secret"
    FIFTH_AMENDMENT = "fifth_amendment"


class DiscoveryDocument(BaseModel):
    """A document in the discovery process."""
    doc_id: str = Field(default_factory=lambda: f"disc-{uuid.uuid4().hex[:12]}")
    case_id: str
    filename: str
    file_path: str
    file_type: str
    file_size_bytes: int = 0
    status: str = DocumentStatus.UPLOADED.value
    extracted_text: str = ""
    ocr_confidence: float = 0.0
    classification: str = ""
    relevance_score: float = 0.0
    privilege_flags: List[str] = Field(default_factory=list)
    privilege_basis: str = ""
    mapped_claims: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    bates_number: Optional[str] = None
    produced: bool = False
    withheld: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PrivilegeLogEntry(BaseModel):
    """An entry in the privilege log."""
    doc_id: str
    bates_range: str
    date: str
    author: str
    recipients: List[str] = Field(default_factory=list)
    document_type: str
    privilege_type: str
    privilege_basis: str


class ProductionSet(BaseModel):
    """A set of documents ready for production."""
    production_id: str = Field(default_factory=lambda: f"prod-{uuid.uuid4().hex[:12]}")
    case_id: str
    documents: List[str] = Field(default_factory=list, description="Document IDs")
    privilege_log: List[PrivilegeLogEntry] = Field(default_factory=list)
    total_documents: int = 0
    total_pages: int = 0
    produced_count: int = 0
    withheld_count: int = 0
    bates_start: str = ""
    bates_end: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# Privilege Detection Patterns
# ---------------------------------------------------------------------------
PRIVILEGE_PATTERNS = {
    PrivilegeType.ATTORNEY_CLIENT: [
        r"attorney[\s-]client",
        r"privileged\s+and\s+confidential",
        r"legal\s+advice",
        r"attorney\s+work\s+product",
        r"prepared\s+in\s+anticipation\s+of\s+litigation",
        r"confidential\s+communication",
        r"seeking\s+legal\s+counsel",
    ],
    PrivilegeType.WORK_PRODUCT: [
        r"work\s+product",
        r"litigation\s+strategy",
        r"case\s+analysis",
        r"trial\s+preparation",
        r"mental\s+impressions",
    ],
    PrivilegeType.MEDICAL: [
        r"hipaa",
        r"medical\s+record",
        r"patient\s+information",
        r"protected\s+health\s+information",
        r"phi",
    ],
    PrivilegeType.TRADE_SECRET: [
        r"trade\s+secret",
        r"proprietary",
        r"confidential\s+business",
        r"competitive\s+advantage",
    ],
}


class DiscoveryManager:
    """Manages the full discovery lifecycle.

    Usage::

        manager = DiscoveryManager()

        # Ingest documents
        doc = await manager.ingest_document(
            case_id="case-12345",
            file_path="/uploads/contract.pdf",
            filename="contract.pdf",
        )

        # Process all documents
        await manager.process_all(case_id="case-12345")

        # Generate production set
        production = await manager.generate_production(
            case_id="case-12345",
            claims=["breach of contract"],
        )
    """

    def __init__(self, agentcore_runtime: Any = None) -> None:
        self._runtime = agentcore_runtime
        self._documents: Dict[str, DiscoveryDocument] = {}
        self._bates_counter = 1
        logger.info("DiscoveryManager initialized")

    async def ingest_document(
        self,
        case_id: str,
        file_path: str,
        filename: str,
    ) -> DiscoveryDocument:
        """Ingest a document into the discovery system."""
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        file_size = 0
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            pass

        doc = DiscoveryDocument(
            case_id=case_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size,
        )

        self._documents[doc.doc_id] = doc
        logger.info("Ingested document: %s (%s, %d bytes)", filename, file_type, file_size)

        # Auto-process
        await self._process_document(doc)

        return doc

    async def _process_document(self, doc: DiscoveryDocument) -> None:
        """Process a document through the full pipeline."""
        doc.status = DocumentStatus.PROCESSING.value

        # Step 1: OCR / Text extraction
        doc.extracted_text = await self._extract_text(doc)
        doc.status = DocumentStatus.OCR_COMPLETE.value

        # Step 2: Classification
        doc.classification = await self._classify_document(doc)
        doc.status = DocumentStatus.CLASSIFIED.value

        # Step 3: Privilege detection
        doc.privilege_flags = self._detect_privilege(doc.extracted_text)
        if doc.privilege_flags:
            doc.privilege_basis = await self._analyze_privilege(doc)
        doc.status = DocumentStatus.PRIVILEGE_REVIEWED.value

        # Step 4: Assign Bates number
        doc.bates_number = f"CL-{self._bates_counter:06d}"
        self._bates_counter += 1

        # Step 5: Determine production status
        if doc.privilege_flags and any(
            p in (PrivilegeType.ATTORNEY_CLIENT.value, PrivilegeType.WORK_PRODUCT.value)
            for p in doc.privilege_flags
        ):
            doc.withheld = True
            doc.status = DocumentStatus.WITHHELD.value
        else:
            doc.status = DocumentStatus.READY_FOR_PRODUCTION.value

    async def _extract_text(self, doc: DiscoveryDocument) -> str:
        """Extract text from a document using OCR or direct parsing."""
        if doc.file_type == "pdf":
            return await self._extract_pdf(doc.file_path)
        elif doc.file_type in ("jpg", "jpeg", "png", "tiff", "bmp"):
            return await self._ocr_image(doc.file_path)
        elif doc.file_type in ("doc", "docx"):
            return await self._extract_docx(doc.file_path)
        elif doc.file_type in ("txt", "csv"):
            return await self._read_text(doc.file_path)
        elif doc.file_type in ("eml", "msg"):
            return await self._extract_email(doc.file_path)
        else:
            return ""

    async def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF."""
        try:
            import subprocess
            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout

            # Fallback to OCR if pdftotext returns empty (scanned PDF)
            return await self._ocr_image(file_path)
        except Exception as exc:
            logger.error("PDF extraction failed: %s", str(exc)[:200])
            return ""

    async def _ocr_image(self, file_path: str) -> str:
        """OCR an image or scanned document using AWS Textract."""
        import boto3

        try:
            client = boto3.client(
                "textract",
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            )

            with open(file_path, "rb") as f:
                image_bytes = f.read()

            response = client.detect_document_text(
                Document={"Bytes": image_bytes}
            )

            text_blocks = []
            for block in response.get("Blocks", []):
                if block["BlockType"] == "LINE":
                    text_blocks.append(block.get("Text", ""))

            return "\n".join(text_blocks)

        except Exception as exc:
            logger.error("OCR failed: %s", str(exc)[:200])
            # Fallback to local Tesseract
            try:
                import subprocess
                result = subprocess.run(
                    ["tesseract", file_path, "stdout"],
                    capture_output=True, text=True, timeout=60,
                )
                return result.stdout
            except Exception:
                return ""

    async def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX."""
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            with zipfile.ZipFile(file_path) as z:
                with z.open("word/document.xml") as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    paragraphs = root.findall(".//w:p", ns)
                    text = "\n".join(
                        "".join(r.text or "" for r in p.findall(".//w:r/w:t", ns))
                        for p in paragraphs
                    )
                    return text
        except Exception as exc:
            logger.error("DOCX extraction failed: %s", str(exc)[:200])
            return ""

    async def _read_text(self, file_path: str) -> str:
        """Read plain text files."""
        try:
            with open(file_path, "r", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    async def _extract_email(self, file_path: str) -> str:
        """Extract text from email files."""
        try:
            import email
            with open(file_path, "r", errors="replace") as f:
                msg = email.message_from_file(f)

            parts = [
                f"From: {msg.get('From', '')}",
                f"To: {msg.get('To', '')}",
                f"Date: {msg.get('Date', '')}",
                f"Subject: {msg.get('Subject', '')}",
                "",
            ]

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        parts.append(part.get_payload(decode=True).decode("utf-8", errors="replace"))
            else:
                parts.append(msg.get_payload(decode=True).decode("utf-8", errors="replace"))

            return "\n".join(parts)
        except Exception as exc:
            logger.error("Email extraction failed: %s", str(exc)[:200])
            return ""

    async def _classify_document(self, doc: DiscoveryDocument) -> str:
        """Classify the document type using LLM."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        text_preview = doc.extracted_text[:2000]

        prompt = (
            f"Classify this document into one category:\n"
            f"contract, correspondence, financial_record, legal_filing, "
            f"medical_record, employment_record, government_document, "
            f"personal_communication, business_record, other\n\n"
            f"FILENAME: {doc.filename}\n"
            f"TEXT PREVIEW:\n{text_preview}\n\n"
            f"Return only the category name."
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER3_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=50,
            temperature=0.0,
            system="Classify documents. Return only the category name.",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.text.strip().lower()

    def _detect_privilege(self, text: str) -> List[str]:
        """Detect potential privilege in document text."""
        import re
        detected = []
        text_lower = text.lower()

        for priv_type, patterns in PRIVILEGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected.append(priv_type.value)
                    break

        return detected

    async def _analyze_privilege(self, doc: DiscoveryDocument) -> str:
        """Analyze the privilege basis in detail."""
        from src.providers.llm_provider import get_provider

        provider = get_provider()
        text_preview = doc.extracted_text[:3000]

        prompt = (
            f"Analyze this document for privilege. Detected flags: {doc.privilege_flags}\n\n"
            f"TEXT:\n{text_preview}\n\n"
            f"Provide a brief privilege basis statement suitable for a privilege log."
        )

        response = await provider.create_message(
            model=os.getenv("BEDROCK_TIER2_MODEL", "anthropic.claude-sonnet-4-6-20260301-v1:0"),
            max_tokens=256,
            temperature=0.0,
            system="You are a privilege review attorney. Provide concise privilege log entries.",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.text.strip()

    async def process_all(self, case_id: str) -> Dict[str, Any]:
        """Process all unprocessed documents for a case."""
        docs = [d for d in self._documents.values() if d.case_id == case_id and d.status == DocumentStatus.UPLOADED.value]
        for doc in docs:
            await self._process_document(doc)

        total = len([d for d in self._documents.values() if d.case_id == case_id])
        withheld = len([d for d in self._documents.values() if d.case_id == case_id and d.withheld])
        ready = len([d for d in self._documents.values() if d.case_id == case_id and d.status == DocumentStatus.READY_FOR_PRODUCTION.value])

        return {
            "case_id": case_id,
            "total_documents": total,
            "withheld": withheld,
            "ready_for_production": ready,
        }

    async def generate_production(
        self,
        case_id: str,
        claims: Optional[List[str]] = None,
    ) -> ProductionSet:
        """Generate a production set with privilege log."""
        case_docs = [d for d in self._documents.values() if d.case_id == case_id]

        production_docs = [d for d in case_docs if not d.withheld]
        withheld_docs = [d for d in case_docs if d.withheld]

        # Build privilege log
        privilege_log = []
        for doc in withheld_docs:
            privilege_log.append(PrivilegeLogEntry(
                doc_id=doc.doc_id,
                bates_range=doc.bates_number or "",
                date=doc.created_at[:10],
                author="",
                document_type=doc.classification,
                privilege_type=", ".join(doc.privilege_flags),
                privilege_basis=doc.privilege_basis,
            ))

        production = ProductionSet(
            case_id=case_id,
            documents=[d.doc_id for d in production_docs],
            privilege_log=privilege_log,
            total_documents=len(case_docs),
            produced_count=len(production_docs),
            withheld_count=len(withheld_docs),
            bates_start=production_docs[0].bates_number if production_docs else "",
            bates_end=production_docs[-1].bates_number if production_docs else "",
        )

        return production
