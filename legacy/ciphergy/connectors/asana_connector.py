"""
Ciphergy Pipeline — Asana Connector

Full Asana API integration for Ciphergy. Handles tasks, comments, projects,
sections, and webhooks. Implements the Ciphergy message bus protocol over
Asana task comments.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ciphergy.connectors.base import BaseConnector, ConnectorConfig, MessageBusMessage

logger = logging.getLogger(__name__)


class AsanaConnector(BaseConnector):
    """
    Asana connector for Ciphergy Pipeline.

    Provides full CRUD operations on tasks, comments, projects, and sections.
    Supports webhook registration and the Ciphergy message bus protocol
    via task comment threads.
    """

    CONNECTOR_NAME = "asana"
    BASE_URL = "https://app.asana.com/api/1.0"

    # Ciphergy message bus markers
    BUS_PREFIX = "[CIPHERGY-BUS]"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._pat: Optional[str] = config.api_key or os.environ.get("ASANA_PAT")
        self._workspace_gid: Optional[str] = config.extra.get("workspace_gid")
        self._project_gid: Optional[str] = config.extra.get("project_gid")
        self._comm_task_gid: Optional[str] = config.extra.get("comm_task_gid")

    # ── Connection lifecycle ────────────────────────────────────────

    def connect(self) -> bool:
        """Verify Asana PAT and establish connection."""
        if not self._pat:
            self._logger.error("No Asana PAT provided. Set ASANA_PAT or pass api_key in config.")
            return False

        try:
            result = self._api_request("GET", "users/me")
            user_name = result.get("data", {}).get("name", "Unknown")
            self._logger.info("Connected to Asana as: %s", user_name)
            self._connected = True
            return True
        except Exception as exc:
            self._logger.error("Failed to connect to Asana: %s", exc)
            return False

    def disconnect(self) -> None:
        """Mark the connector as disconnected."""
        self._connected = False
        self._logger.info("Disconnected from Asana")

    def health_check(self) -> bool:
        """Verify Asana API is reachable and PAT is valid."""
        try:
            result = self._api_request("GET", "users/me")
            return "data" in result
        except Exception:
            return False

    # ── Core CRUD ───────────────────────────────────────────────────

    def fetch(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Fetch data from Asana.

        Args:
            query: Resource path — e.g., "tasks/{gid}", "projects/{gid}/tasks",
                   or "__ciphergy_bus__" for message bus polling.
            **kwargs: Additional query parameters.

        Returns:
            Dict with "data", "status", and "connector" keys.
        """
        if query == "__ciphergy_bus__":
            return self._fetch_bus_messages(**kwargs)

        result = self._with_retry(f"Asana fetch {query}", self._api_request, "GET", query)
        return {
            "data": result.get("data", []),
            "status": "ok",
            "connector": "asana",
        }

    def push(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        Push data to Asana (create or update resources).

        Args:
            data: Must contain "endpoint" and "payload" keys,
                  or be a message bus payload (with "ciphergy_message" key).
            **kwargs: If message_bus=True, routes to bus handler.

        Returns:
            True if successful.
        """
        if kwargs.get("message_bus") or data.get("ciphergy_message"):
            return self._push_bus_message(data)

        endpoint = data.get("endpoint", "")
        payload = data.get("payload", {})
        method = data.get("method", "POST")

        if not endpoint:
            self._logger.error("Push requires 'endpoint' in data")
            return False

        self._with_retry(f"Asana push {endpoint}", self._api_request, method, endpoint, payload)
        return True

    # ── Task operations ─────────────────────────────────────────────

    def create_task(
        self,
        name: str,
        project_gid: Optional[str] = None,
        section_gid: Optional[str] = None,
        notes: str = "",
        assignee: Optional[str] = None,
        due_on: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Asana task.

        Args:
            name: Task name.
            project_gid: Project to add the task to (uses default if None).
            section_gid: Optional section within the project.
            notes: Task description/notes.
            assignee: Assignee GID or "me".
            due_on: Due date in YYYY-MM-DD format.
            tags: List of tag GIDs.

        Returns:
            The created task data.
        """
        task_data: Dict[str, Any] = {"name": name, "notes": notes}

        proj = project_gid or self._project_gid
        if proj:
            task_data["projects"] = [proj]
        if section_gid:
            task_data["memberships"] = [{"project": proj, "section": section_gid}]
        if assignee:
            task_data["assignee"] = assignee
        if due_on:
            task_data["due_on"] = due_on
        if tags:
            task_data["tags"] = tags

        result = self._with_retry(
            "Create task", self._api_request, "POST", "tasks", {"data": task_data}
        )
        task = result.get("data", {})
        self._logger.info("Created task: %s (GID: %s)", name, task.get("gid"))
        return task

    def update_task(self, task_gid: str, **fields: Any) -> Dict[str, Any]:
        """
        Update an existing Asana task.

        Args:
            task_gid: The task GID to update.
            **fields: Task fields to update (name, notes, completed, due_on, etc.).

        Returns:
            The updated task data.
        """
        result = self._with_retry(
            f"Update task {task_gid}",
            self._api_request,
            "PUT",
            f"tasks/{task_gid}",
            {"data": fields},
        )
        return result.get("data", {})

    def get_task(self, task_gid: str) -> Dict[str, Any]:
        """
        Get a single task by GID.

        Args:
            task_gid: The task GID.

        Returns:
            Task data dict.
        """
        result = self._with_retry(
            f"Get task {task_gid}", self._api_request, "GET", f"tasks/{task_gid}"
        )
        return result.get("data", {})

    # ── Comment operations ──────────────────────────────────────────

    def read_task_comments(self, task_gid: str) -> List[Dict[str, Any]]:
        """
        Read all comments from a task.

        Args:
            task_gid: The task GID.

        Returns:
            List of comment dicts with id, author, text, created_at, type.
        """
        result = self._with_retry(
            f"Read comments {task_gid}",
            self._api_request,
            "GET",
            f"tasks/{task_gid}/stories",
        )
        stories = result.get("data", [])

        comments: List[Dict[str, Any]] = []
        for story in stories:
            if story.get("resource_subtype") != "comment_added":
                continue
            comments.append({
                "id": story.get("gid", ""),
                "author": story.get("created_by", {}).get("name", "Unknown"),
                "text": story.get("text", ""),
                "created_at": story.get("created_at", ""),
                "type": self._detect_message_type(story.get("text", "")),
            })

        return comments

    def post_comment(
        self, task_gid: str, text: str, is_rich_text: bool = False
    ) -> Dict[str, Any]:
        """
        Post a comment to a task.

        Args:
            task_gid: The task GID.
            text: Comment text.
            is_rich_text: If True, treat text as HTML body.

        Returns:
            The created story data.
        """
        payload: Dict[str, Any] = {"data": {}}
        if is_rich_text:
            payload["data"]["html_text"] = text
        else:
            payload["data"]["text"] = text

        result = self._with_retry(
            f"Post comment {task_gid}",
            self._api_request,
            "POST",
            f"tasks/{task_gid}/stories",
            payload,
        )
        return result.get("data", {})

    # ── Project & section operations ────────────────────────────────

    def list_projects(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all projects in a workspace.

        Args:
            workspace_gid: Workspace GID (uses default if None).

        Returns:
            List of project dicts.
        """
        ws = workspace_gid or self._workspace_gid
        endpoint = f"workspaces/{ws}/projects" if ws else "projects"
        result = self._with_retry("List projects", self._api_request, "GET", endpoint)
        return result.get("data", [])

    def list_sections(self, project_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all sections in a project.

        Args:
            project_gid: Project GID (uses default if None).

        Returns:
            List of section dicts.
        """
        proj = project_gid or self._project_gid
        if not proj:
            self._logger.error("No project GID provided")
            return []

        result = self._with_retry(
            f"List sections {proj}", self._api_request, "GET", f"projects/{proj}/sections"
        )
        return result.get("data", [])

    def list_tasks(
        self, project_gid: Optional[str] = None, section_gid: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List tasks in a project or section.

        Args:
            project_gid: Project GID.
            section_gid: Section GID (takes precedence over project_gid).

        Returns:
            List of task dicts.
        """
        if section_gid:
            endpoint = f"sections/{section_gid}/tasks"
        else:
            proj = project_gid or self._project_gid
            if not proj:
                self._logger.error("No project or section GID provided")
                return []
            endpoint = f"projects/{proj}/tasks"

        result = self._with_retry("List tasks", self._api_request, "GET", endpoint)
        return result.get("data", [])

    # ── Webhook operations ──────────────────────────────────────────

    def register_webhook(
        self, resource_gid: str, target_url: str, filters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Register a webhook for an Asana resource.

        Args:
            resource_gid: The resource GID to watch.
            target_url: URL to receive webhook events.
            filters: Optional list of filter dicts (e.g., [{"resource_type": "task", "action": "changed"}]).

        Returns:
            The created webhook data.
        """
        payload: Dict[str, Any] = {
            "data": {
                "resource": resource_gid,
                "target": target_url,
            }
        }
        if filters:
            payload["data"]["filters"] = filters

        result = self._with_retry(
            "Register webhook", self._api_request, "POST", "webhooks", payload
        )
        webhook = result.get("data", {})
        self._logger.info("Webhook registered: %s -> %s", resource_gid, target_url)
        return webhook

    def list_webhooks(self, workspace_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all webhooks in a workspace.

        Args:
            workspace_gid: Workspace GID (uses default if None).

        Returns:
            List of webhook dicts.
        """
        ws = workspace_gid or self._workspace_gid
        if not ws:
            self._logger.error("No workspace GID for webhook listing")
            return []

        result = self._with_retry(
            "List webhooks",
            self._api_request,
            "GET",
            f"webhooks?workspace={ws}",
        )
        return result.get("data", [])

    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming webhook event.

        Args:
            event_data: The raw webhook event payload.

        Returns:
            Processed event dict with action, resource_gid, resource_type, and change data.
        """
        events = event_data.get("events", [])
        processed: List[Dict[str, Any]] = []

        for event in events:
            processed.append({
                "action": event.get("action", ""),
                "resource_gid": event.get("resource", {}).get("gid", ""),
                "resource_type": event.get("resource", {}).get("resource_type", ""),
                "parent_gid": event.get("parent", {}).get("gid", ""),
                "change": event.get("change", {}),
                "user_gid": event.get("user", {}).get("gid", ""),
                "created_at": event.get("created_at", ""),
            })

        return {"events": processed, "count": len(processed)}

    # ── Message bus implementation ──────────────────────────────────

    def send_message(self, message: MessageBusMessage) -> bool:
        """
        Send a Ciphergy bus message via Asana task comments.

        Args:
            message: The message to send.

        Returns:
            True if posted successfully.
        """
        task_gid = self._comm_task_gid
        if not task_gid:
            self._logger.error("No comm_task_gid configured for message bus")
            return False

        formatted = (
            f"{self.BUS_PREFIX}\n"
            f"Source: {message.source}\n"
            f"Destination: {message.destination}\n"
            f"Type: {message.msg_type}\n"
            f"Priority: {message.priority}\n"
            f"Timestamp: {message.timestamp}\n"
            f"Correlation-ID: {message.correlation_id}\n"
            f"---\n"
            f"{json.dumps(message.payload, indent=2)}"
        )

        self.post_comment(task_gid, formatted)
        return True

    def receive_messages(self, **kwargs: Any) -> List[MessageBusMessage]:
        """
        Receive Ciphergy bus messages from the comm task.

        Args:
            **kwargs: Optional "since" key for filtering by timestamp.

        Returns:
            List of pending MessageBusMessage objects.
        """
        task_gid = self._comm_task_gid
        if not task_gid:
            return []

        comments = self.read_task_comments(task_gid)
        messages: List[MessageBusMessage] = []

        since = kwargs.get("since", "")

        for comment in comments:
            text = comment.get("text", "")
            if not text.startswith(self.BUS_PREFIX):
                continue
            if since and comment.get("created_at", "") < since:
                continue

            try:
                msg = self._parse_bus_message(text)
                if msg:
                    messages.append(msg)
            except Exception as exc:
                self._logger.warning("Failed to parse bus message: %s", exc)

        return messages

    # ── Private helpers ─────────────────────────────────────────────

    def _api_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an authenticated Asana API request."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._pat}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if hasattr(exc, "read") else ""
            raise RuntimeError(f"Asana API {exc.code}: {error_body}") from exc

    def _fetch_bus_messages(self, **kwargs: Any) -> Dict[str, Any]:
        """Fetch bus messages and return in standard format."""
        messages = self.receive_messages(**kwargs)
        return {
            "data": [
                {
                    "ciphergy_message": True,
                    "source": m.source,
                    "destination": m.destination,
                    "type": m.msg_type,
                    "priority": m.priority,
                    "timestamp": m.timestamp,
                    "correlation_id": m.correlation_id,
                    "payload": m.payload,
                }
                for m in messages
            ],
            "status": "ok",
            "connector": "asana",
        }

    def _push_bus_message(self, data: Dict[str, Any]) -> bool:
        """Push a message bus payload as an Asana comment."""
        msg = MessageBusMessage(
            source=data.get("source", ""),
            destination=data.get("destination", ""),
            msg_type=data.get("type", "INFO"),
            payload=data.get("payload", {}),
            priority=data.get("priority", "MEDIUM"),
            correlation_id=data.get("correlation_id", ""),
        )
        return self.send_message(msg)

    @staticmethod
    def _parse_bus_message(text: str) -> Optional[MessageBusMessage]:
        """Parse a Ciphergy bus message from comment text."""
        lines = text.split("\n")
        if not lines or not lines[0].startswith("[CIPHERGY-BUS]"):
            return None

        fields: Dict[str, str] = {}
        payload_lines: List[str] = []
        in_payload = False

        for line in lines[1:]:
            if line.strip() == "---":
                in_payload = True
                continue
            if in_payload:
                payload_lines.append(line)
            elif ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().lower().replace("-", "_")] = value.strip()

        try:
            payload = json.loads("\n".join(payload_lines)) if payload_lines else {}
        except json.JSONDecodeError:
            payload = {"raw": "\n".join(payload_lines)}

        return MessageBusMessage(
            source=fields.get("source", ""),
            destination=fields.get("destination", ""),
            msg_type=fields.get("type", "INFO"),
            priority=fields.get("priority", "MEDIUM"),
            timestamp=fields.get("timestamp", ""),
            correlation_id=fields.get("correlation_id", ""),
            payload=payload,
        )

    @staticmethod
    def _detect_message_type(text: str) -> str:
        """Detect Ciphergy message type from comment text."""
        type_markers = {
            "[STATUS]": "STATUS",
            "[ALERT]": "ALERT",
            "[QUESTION]": "QUESTION",
            "[ANSWER]": "ANSWER",
            "[DIRECTIVE]": "DIRECTIVE",
            "[CASCADE]": "CASCADE",
            "[SYNC]": "SYNC",
            "[CIPHERGY-BUS]": "BUS",
        }
        text_upper = text.upper()
        for marker, msg_type in type_markers.items():
            if marker in text_upper:
                return msg_type
        return "INFO"
