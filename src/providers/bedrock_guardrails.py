"""Bedrock Guardrails — Content filtering and PII redaction for ChiefLitigator.

Integrates AWS Bedrock Guardrails to enforce:
  - PII detection and redaction in user inputs and model outputs
  - Content filtering for harmful, misleading, or unethical legal advice
  - Topic denial for unauthorized practice of law boundaries
  - Word/phrase filtering for legal compliance
  - Contextual grounding checks to prevent hallucinated citations

The guardrail is created once via AWS Console or CDK, then referenced
by ID in all Converse API calls.

No hardcoded secrets. All configuration via environment variables.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger("cyphergy.providers.bedrock_guardrails")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BEDROCK_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
GUARDRAIL_ID = os.getenv("BEDROCK_GUARDRAIL_ID", "")
GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
PII_REDACTION_ENABLED = os.getenv("PII_REDACTION_ENABLED", "true").lower() == "true"


class PIIEntityType(str, Enum):
    """PII entity types detected and redacted by the guardrail."""
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    ADDRESS = "ADDRESS"
    DOB = "DATE_OF_BIRTH"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    PASSPORT = "PASSPORT"
    IP_ADDRESS = "IP_ADDRESS"


class GuardrailAction(str, Enum):
    """Actions the guardrail can take."""
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ANONYMIZE = "ANONYMIZE"


class GuardrailResult:
    """Result of a guardrail evaluation."""

    def __init__(
        self,
        action: GuardrailAction,
        original_text: str,
        processed_text: str,
        pii_detected: List[Dict[str, str]],
        blocked_topics: List[str],
        grounding_score: float,
    ) -> None:
        self.action = action
        self.original_text = original_text
        self.processed_text = processed_text
        self.pii_detected = pii_detected
        self.blocked_topics = blocked_topics
        self.grounding_score = grounding_score

    @property
    def is_allowed(self) -> bool:
        return self.action == GuardrailAction.ALLOW

    @property
    def is_blocked(self) -> bool:
        return self.action == GuardrailAction.BLOCK

    @property
    def has_pii(self) -> bool:
        return len(self.pii_detected) > 0


class BedrockGuardrailService:
    """Enforces content safety and PII protection for all ChiefLitigator interactions.

    Two modes of operation:
    1. **Inline with Converse API**: Pass guardrailConfig to converse() calls.
       Bedrock applies the guardrail automatically.
    2. **Standalone ApplyGuardrail**: Evaluate text independently before/after
       processing. Used for pre-screening user input and post-screening output.

    Usage::

        guardrails = BedrockGuardrailService()

        # Pre-screen user input
        result = await guardrails.evaluate_input("My SSN is 123-45-6789")
        if result.has_pii:
            # Use redacted version
            safe_text = result.processed_text

        # Get guardrail config for Converse API
        config = guardrails.get_converse_config()
        # Pass to converse() call: guardrailConfig=config
    """

    def __init__(self) -> None:
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
        )
        self._guardrail_id = GUARDRAIL_ID
        self._guardrail_version = GUARDRAIL_VERSION
        self._pii_enabled = PII_REDACTION_ENABLED

        # Local PII patterns as fallback when Bedrock guardrail is not configured
        self._local_pii_patterns = {
            PIIEntityType.SSN: re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            PIIEntityType.CREDIT_CARD: re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
            PIIEntityType.PHONE: re.compile(r"\b(?:\+1[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"),
            PIIEntityType.EMAIL: re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        }

        if self._guardrail_id:
            logger.info(
                "BedrockGuardrailService initialized: id=%s version=%s",
                self._guardrail_id,
                self._guardrail_version,
            )
        else:
            logger.warning(
                "BEDROCK_GUARDRAIL_ID not set — using local PII patterns only. "
                "Set BEDROCK_GUARDRAIL_ID for full guardrail protection."
            )

    def get_converse_config(self) -> Optional[Dict[str, Any]]:
        """Return guardrail configuration for Bedrock Converse API calls.

        Returns None if no guardrail is configured, so callers can
        conditionally include it.
        """
        if not self._guardrail_id:
            return None

        return {
            "guardrailIdentifier": self._guardrail_id,
            "guardrailVersion": self._guardrail_version,
            "trace": "enabled",
        }

    async def evaluate_input(self, text: str) -> GuardrailResult:
        """Evaluate user input text through the guardrail.

        Detects PII, blocked topics, and harmful content.
        Returns the processed (redacted) text if PII is found.
        """
        if self._guardrail_id:
            return await self._evaluate_via_bedrock(text, source="INPUT")
        return self._evaluate_locally(text)

    async def evaluate_output(self, text: str) -> GuardrailResult:
        """Evaluate model output text through the guardrail.

        Checks for hallucinated citations, harmful advice, and PII leakage.
        """
        if self._guardrail_id:
            return await self._evaluate_via_bedrock(text, source="OUTPUT")
        return self._evaluate_locally(text)

    async def _evaluate_via_bedrock(
        self,
        text: str,
        source: str = "INPUT",
    ) -> GuardrailResult:
        """Evaluate text using the Bedrock ApplyGuardrail API."""
        try:
            response = await asyncio.to_thread(
                self._client.apply_guardrail,
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion=self._guardrail_version,
                source=source,
                content=[{"text": {"text": text}}],
            )

            action_str = response.get("action", "NONE")
            outputs = response.get("outputs", [])
            assessments = response.get("assessments", [])

            # Extract processed text
            processed_text = text
            if outputs:
                processed_text = outputs[0].get("text", text)

            # Extract PII detections
            pii_detected = []
            blocked_topics = []
            grounding_score = 1.0

            for assessment in assessments:
                # PII assessment
                pii_policy = assessment.get("sensitiveInformationPolicy", {})
                for pii_finding in pii_policy.get("piiEntities", []):
                    pii_detected.append({
                        "type": pii_finding.get("type", "UNKNOWN"),
                        "action": pii_finding.get("action", "ANONYMIZED"),
                    })

                # Topic policy
                topic_policy = assessment.get("topicPolicy", {})
                for topic in topic_policy.get("topics", []):
                    if topic.get("action") == "BLOCKED":
                        blocked_topics.append(topic.get("name", "unknown"))

                # Contextual grounding
                grounding = assessment.get("contextualGroundingPolicy", {})
                filters = grounding.get("filters", [])
                if filters:
                    grounding_score = min(
                        f.get("score", 1.0) for f in filters
                    )

            action = GuardrailAction.ALLOW
            if action_str == "GUARDRAIL_INTERVENED":
                action = GuardrailAction.BLOCK if blocked_topics else GuardrailAction.ANONYMIZE

            return GuardrailResult(
                action=action,
                original_text=text,
                processed_text=processed_text,
                pii_detected=pii_detected,
                blocked_topics=blocked_topics,
                grounding_score=grounding_score,
            )

        except Exception as exc:
            logger.error("Bedrock guardrail evaluation failed: %s", str(exc)[:200])
            # Fall back to local evaluation
            return self._evaluate_locally(text)

    def _evaluate_locally(self, text: str) -> GuardrailResult:
        """Local PII detection fallback when Bedrock guardrail is not configured."""
        pii_detected = []
        processed_text = text

        if self._pii_enabled:
            for pii_type, pattern in self._local_pii_patterns.items():
                matches = pattern.findall(text)
                for match in matches:
                    pii_detected.append({
                        "type": pii_type.value,
                        "action": "ANONYMIZED",
                        "match": match,
                    })
                    # Redact the match
                    redacted = f"[{pii_type.value}_REDACTED]"
                    processed_text = processed_text.replace(match, redacted)

        action = GuardrailAction.ANONYMIZE if pii_detected else GuardrailAction.ALLOW

        return GuardrailResult(
            action=action,
            original_text=text,
            processed_text=processed_text,
            pii_detected=pii_detected,
            blocked_topics=[],
            grounding_score=1.0,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_guardrail_service: Optional[BedrockGuardrailService] = None


def get_guardrail_service() -> BedrockGuardrailService:
    """Return the singleton BedrockGuardrailService instance."""
    global _guardrail_service
    if _guardrail_service is None:
        _guardrail_service = BedrockGuardrailService()
    return _guardrail_service
