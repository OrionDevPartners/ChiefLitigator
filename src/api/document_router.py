"""Document Management Router — Document lifecycle operations.

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.api.document_router")

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    document_id: str
    case_id: str
    filename: str
    document_type: str = ""
    status: str = "uploaded"
    galvanizer_score: Optional[float] = None
    privilege_flags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


_documents_store: Dict[str, Dict[str, Any]] = {}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
) -> DocumentResponse:
    """Upload a document for a case."""
    doc_id = f"doc-{uuid.uuid4().hex[:12]}"

    upload_dir = os.getenv("UPLOAD_DIR", "/tmp/chieflitigator/uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{doc_id}_{file.filename}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    doc = {
        "document_id": doc_id,
        "case_id": case_id,
        "filename": file.filename or "unknown",
        "file_path": file_path,
        "status": "uploaded",
        "created_at": datetime.utcnow().isoformat(),
    }

    # Process through Discovery Manager
    try:
        from src.agents.discovery_manager import DiscoveryManager
        manager = DiscoveryManager()
        result = await manager.ingest_document(
            case_id=case_id,
            file_path=file_path,
            filename=file.filename or "unknown",
        )
        doc["status"] = result.status
        doc["document_type"] = result.classification
        doc["privilege_flags"] = result.privilege_flags
    except Exception as exc:
        logger.warning("Discovery processing deferred: %s", str(exc)[:100])

    _documents_store[doc_id] = doc
    return DocumentResponse(**{k: v for k, v in doc.items() if k in DocumentResponse.model_fields})


@router.get("/{case_id}", response_model=List[DocumentResponse])
async def list_documents(case_id: str) -> List[DocumentResponse]:
    """List all documents for a case."""
    docs = [d for d in _documents_store.values() if d.get("case_id") == case_id]
    return [
        DocumentResponse(**{k: v for k, v in d.items() if k in DocumentResponse.model_fields})
        for d in docs
    ]


@router.get("/{case_id}/{document_id}", response_model=DocumentResponse)
async def get_document(case_id: str, document_id: str) -> DocumentResponse:
    """Get a specific document."""
    doc = _documents_store.get(document_id)
    if not doc or doc.get("case_id") != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**{k: v for k, v in doc.items() if k in DocumentResponse.model_fields})


@router.post("/{case_id}/generate")
async def generate_document(
    case_id: str,
    document_type: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a court document for a case."""
    from src.agents.document_generator import DocumentGenerator
    generator = DocumentGenerator()

    result = await generator.generate(
        case_id=case_id,
        document_type=document_type,
        case_context=context or {},
    )

    return result.model_dump() if hasattr(result, "model_dump") else {"status": "generated"}


@router.post("/{case_id}/{document_id}/galvanize")
async def galvanize_document(case_id: str, document_id: str) -> Dict[str, Any]:
    """Run a document through The Galvanizer."""
    doc = _documents_store.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from src.orchestrator.galvanizer import Galvanizer
    galvanizer = Galvanizer()

    result = await galvanizer.galvanize(
        case_id=case_id,
        document_id=document_id,
        document_text="",  # Would be resolved from document store
        case_context={},
    )

    doc["galvanizer_score"] = result.final_confidence
    doc["status"] = "galvanized" if result.passed else "needs_revision"

    return result.model_dump()
