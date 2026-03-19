"""
Cyphergy Legal — Linear Integration
Project tracking and issue creation for case management workflows.

CPAA: LINEAR_TOKEN loaded from environment at runtime.
This module provides a thin client around the Linear GraphQL API to:
  - Create issues from case intake
  - Track task status transitions
  - Sync case milestones with Linear project boards
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LINEAR_API_URL = "https://api.linear.app/graphql"

# Linear issue priority mapping (1 = Urgent, 4 = Low, 0 = None)
PRIORITY_MAP: dict[str, int] = {
    "urgent": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "none": 0,
}


@dataclass
class LinearIssue:
    """Represents a Linear issue created from Cyphergy case intake."""

    id: str
    identifier: str  # e.g. CYP-42
    title: str
    url: str
    state_name: str = ""
    priority: int = 0


@dataclass
class LinearClient:
    """Thin async client for the Linear GraphQL API.

    CPAA: Token is read from LINEAR_TOKEN env var at instantiation.
    Never stored on disk, never logged, never sent to any third party.
    """

    token: str = field(default="", repr=False)
    team_id: str = ""
    _http: httpx.AsyncClient | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.token:
            self.token = os.environ.get("LINEAR_TOKEN", "").strip()
        if not self.team_id:
            self.team_id = os.environ.get("LINEAR_TEAM_ID", "").strip()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=LINEAR_API_URL,
                headers=self._headers,
                timeout=30.0,
            )
        return self._http

    def is_configured(self) -> bool:
        """Return True if both LINEAR_TOKEN and LINEAR_TEAM_ID are set."""
        return bool(self.token) and bool(self.team_id)

    async def _query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query against the Linear API."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self.http.post("", json=payload)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            errors = result["errors"]
            logger.error("Linear API errors: %s", errors)
            raise LinearAPIError(f"Linear GraphQL errors: {errors}")

        return result.get("data", {})

    async def create_issue(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
    ) -> LinearIssue:
        """Create a Linear issue from case intake.

        Args:
            title: Issue title (typically case reference + short description).
            description: Markdown body. Do NOT include PII — only structural
                         metadata about the case type, jurisdiction, deadlines.
            priority: One of 'urgent', 'high', 'medium', 'low', 'none'.
            labels: Optional label IDs to attach.

        Returns:
            LinearIssue with the created issue details.
        """
        if not self.is_configured():
            raise LinearConfigError("LINEAR_TOKEN and LINEAR_TEAM_ID must be set in environment.")

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                    state { name }
                    priority
                }
            }
        }
        """
        variables: dict[str, Any] = {
            "input": {
                "teamId": self.team_id,
                "title": title,
                "description": description,
                "priority": PRIORITY_MAP.get(priority.lower(), 3),
            }
        }

        if labels:
            variables["input"]["labelIds"] = labels

        data = await self._query(mutation, variables)
        issue_data = data.get("issueCreate", {}).get("issue", {})

        if not issue_data:
            raise LinearAPIError("Issue creation returned no data.")

        issue = LinearIssue(
            id=issue_data["id"],
            identifier=issue_data["identifier"],
            title=issue_data["title"],
            url=issue_data["url"],
            state_name=issue_data.get("state", {}).get("name", ""),
            priority=issue_data.get("priority", 0),
        )
        logger.info("Created Linear issue %s: %s", issue.identifier, issue.title)
        return issue

    async def get_issue_status(self, issue_id: str) -> dict[str, Any]:
        """Fetch current status of a Linear issue.

        Args:
            issue_id: The Linear issue UUID.

        Returns:
            Dict with 'identifier', 'title', 'state', 'priority', 'assignee'.
        """
        query = """
        query GetIssue($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                state { name }
                priority
                assignee { name email }
                updatedAt
            }
        }
        """
        data = await self._query(query, {"id": issue_id})
        return data.get("issue", {})

    async def update_issue_status(
        self,
        issue_id: str,
        state_id: str | None = None,
        priority: str | None = None,
    ) -> dict[str, Any]:
        """Update issue state or priority.

        Args:
            issue_id: The Linear issue UUID.
            state_id: Target workflow state ID (e.g., 'In Progress', 'Done').
            priority: New priority level string.

        Returns:
            Updated issue data.
        """
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    identifier
                    state { name }
                    priority
                }
            }
        }
        """
        update_input: dict[str, Any] = {}
        if state_id:
            update_input["stateId"] = state_id
        if priority:
            update_input["priority"] = PRIORITY_MAP.get(priority.lower(), 3)

        if not update_input:
            raise ValueError("At least one of state_id or priority must be provided.")

        data = await self._query(mutation, {"id": issue_id, "input": update_input})
        return data.get("issueUpdate", {}).get("issue", {})

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None


class LinearAPIError(Exception):
    """Raised when the Linear API returns an error response."""


class LinearConfigError(Exception):
    """Raised when LINEAR_TOKEN or LINEAR_TEAM_ID is missing."""
