"""
Cyphergy Verification Module — Citation Verification Chain.

Exports:
    CitationVerifier: The 5-step citation verification pipeline.
    VerificationResult: Pydantic model for verification outcomes.
    VerificationStatus: Enum for verification status codes.
"""

from src.verification.citation_chain import (
    CitationVerifier,
    VerificationResult,
    VerificationStatus,
)

__all__ = [
    "CitationVerifier",
    "VerificationResult",
    "VerificationStatus",
]
