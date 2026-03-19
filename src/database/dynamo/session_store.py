"""DynamoDB Session Store — Fast key-value access for user sessions and case state.

Aurora holds the massive legal knowledge graph.
DynamoDB holds the lightweight, highly transactional user data:
  - Active user sessions
  - Case metadata and current state
  - Galvanizer debate logs (intermediate WDC rounds)
  - Document draft metadata (actual files in S3)

All configuration via environment variables per CPAA mandate.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("cyphergy.database.dynamo.session_store")

# Table names from environment
SESSIONS_TABLE = os.getenv("DYNAMO_SESSIONS_TABLE", "chieflitigator-sessions")
CASES_TABLE = os.getenv("DYNAMO_CASES_TABLE", "chieflitigator-cases")
GALVANIZER_TABLE = os.getenv("DYNAMO_GALVANIZER_TABLE", "chieflitigator-galvanizer-logs")


def _get_dynamo_resource():
    """Get DynamoDB resource with region from environment."""
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


class SessionStore:
    """Manages user sessions in DynamoDB."""

    def __init__(self):
        self.dynamo = _get_dynamo_resource()
        self.table = self.dynamo.Table(SESSIONS_TABLE)

    async def create_session(self, user_id: str) -> Dict[str, Any]:
        """Create a new user session."""
        session_id = str(uuid.uuid4())
        item = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "active_case_id": None,
        }
        self.table.put_item(Item=item)
        return item

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by ID."""
        try:
            response = self.table.get_item(Key={"session_id": session_id})
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None


class CaseStateStore:
    """Manages active case state in DynamoDB."""

    def __init__(self):
        self.dynamo = _get_dynamo_resource()
        self.table = self.dynamo.Table(CASES_TABLE)

    async def save_case_state(self, case_id: str, state: Dict[str, Any]) -> None:
        """Save or update the current state of a case."""
        item = {
            "case_id": case_id,
            "updated_at": datetime.utcnow().isoformat(),
            **state,
        }
        self.table.put_item(Item=item)

    async def get_case_state(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the current state of a case."""
        try:
            response = self.table.get_item(Key={"case_id": case_id})
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get case state {case_id}: {e}")
            return None


class GalvanizerLogStore:
    """Stores intermediate Galvanizer (WDC) debate rounds in DynamoDB."""

    def __init__(self):
        self.dynamo = _get_dynamo_resource()
        self.table = self.dynamo.Table(GALVANIZER_TABLE)

    async def log_round(
        self,
        case_id: str,
        round_number: int,
        advocacy_score: float,
        stress_test_score: float,
        composite_score: float,
        debate_transcript: str,
    ) -> None:
        """Log a single Galvanizer debate round."""
        item = {
            "case_id": case_id,
            "round_number": round_number,
            "timestamp": datetime.utcnow().isoformat(),
            "advocacy_score": str(advocacy_score),
            "stress_test_score": str(stress_test_score),
            "composite_score": str(composite_score),
            "debate_transcript": debate_transcript,
        }
        self.table.put_item(Item=item)
