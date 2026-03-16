#!/usr/bin/env python3
"""
Ciphergy Pipeline — Asana API Bridge
Provides structured communication with Asana for inter-agent messaging.

Usage as module:
    from asana_bridge import AsanaBridge
    bridge = AsanaBridge(config_path="config/ciphergy.yaml")
    messages = bridge.read_messages(task_gid)
    bridge.post_message(task_gid, "Hello from Ciphergy")

Usage as CLI:
    python scripts/asana_bridge.py read --task-gid 123456
    python scripts/asana_bridge.py post --task-gid 123456 --message "Update complete"
    python scripts/asana_bridge.py pending --task-gid 123456
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Message Types and Priorities
# ---------------------------------------------------------------------------

MESSAGE_TYPES = {
    "STATUS": "[STATUS]",
    "ALERT": "[ALERT]",
    "QUESTION": "[QUESTION]",
    "ANSWER": "[ANSWER]",
    "DIRECTIVE": "[DIRECTIVE]",
    "CASCADE": "[CASCADE]",
    "SYNC": "[SYNC]",
    "INFO": "[INFO]",
}

PRIORITIES = {
    "CRITICAL": "P0",
    "HIGH": "P1",
    "MEDIUM": "P2",
    "LOW": "P3",
}


# ---------------------------------------------------------------------------
# AsanaBridge Class
# ---------------------------------------------------------------------------


class AsanaBridge:
    """Asana API wrapper for Ciphergy Pipeline communication."""

    BASE_URL = "https://app.asana.com/api/1.0"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self, config_path=None, pat=None):
        """
        Initialize the Asana bridge.

        Args:
            config_path: Path to ciphergy.yaml config file
            pat: Asana Personal Access Token (overrides config)
        """
        self.config = {}
        self.pat = pat

        if config_path and os.path.isfile(config_path):
            if yaml is None:
                raise ImportError("PyYAML required. Install with: pip install pyyaml")
            with open(config_path) as f:
                full_config = yaml.safe_load(f)
            self.config = full_config.get("asana", {})

        if not self.pat:
            pat_var = self.config.get("pat_env_var", "ASANA_PAT")
            self.pat = os.environ.get(pat_var)

        if not self.pat:
            raise ValueError(
                f"Asana PAT not found. Set environment variable "
                f"'{self.config.get('pat_env_var', 'ASANA_PAT')}' or pass pat= argument."
            )

    def _request(self, method, endpoint, data=None):
        """
        Make an authenticated API request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint path
            data: Request body (dict, will be JSON-encoded)

        Returns:
            dict: Parsed JSON response

        Raises:
            RuntimeError: After all retries exhausted
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body = json.dumps(data).encode() if data else None

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    response_data = json.loads(resp.read().decode())
                    return response_data
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429:
                    # Rate limited — respect Retry-After header
                    retry_after = int(e.headers.get("Retry-After", self.RETRY_DELAY * attempt))
                    print(f"  [WARN] Rate limited. Retrying in {retry_after}s (attempt {attempt}/{self.MAX_RETRIES})")
                    time.sleep(retry_after)
                elif e.code >= 500:
                    # Server error — retry
                    print(f"  [WARN] Server error {e.code}. Retrying in {self.RETRY_DELAY * attempt}s")
                    time.sleep(self.RETRY_DELAY * attempt)
                else:
                    # Client error — don't retry
                    error_body = e.read().decode() if hasattr(e, "read") else ""
                    raise RuntimeError(f"Asana API error {e.code}: {error_body}")
            except urllib.error.URLError as e:
                last_error = e
                print(f"  [WARN] Connection error. Retrying in {self.RETRY_DELAY * attempt}s")
                time.sleep(self.RETRY_DELAY * attempt)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                else:
                    break

        raise RuntimeError(f"Asana API request failed after {self.MAX_RETRIES} retries: {last_error}")

    def read_messages(self, task_gid):
        """
        Get all comments (stories) from an Asana task.

        Args:
            task_gid: The Asana task GID

        Returns:
            list[dict]: List of message dicts with keys: id, author, text, created_at, type
        """
        response = self._request("GET", f"tasks/{task_gid}/stories")
        stories = response.get("data", [])

        messages = []
        for story in stories:
            if story.get("resource_subtype") != "comment_added":
                continue
            messages.append(
                {
                    "id": story.get("gid"),
                    "author": story.get("created_by", {}).get("name", "Unknown"),
                    "text": story.get("text", ""),
                    "created_at": story.get("created_at", ""),
                    "type": self._detect_message_type(story.get("text", "")),
                }
            )

        return messages

    def post_message(self, task_gid, message):
        """
        Post a formatted comment to an Asana task.

        Args:
            task_gid: The Asana task GID
            message: Message text to post

        Returns:
            dict: The created story data
        """
        response = self._request("POST", f"tasks/{task_gid}/stories", {"data": {"text": message}})
        return response.get("data", {})

    def get_pending(self, task_gid):
        """
        Get OPEN/unresolved messages from a task.
        Messages are considered "open" if they contain [OPEN], [QUESTION], or [ALERT]
        and have not been followed by a corresponding [ANSWER] or [RESOLVED].

        Args:
            task_gid: The Asana task GID

        Returns:
            list[dict]: List of pending message dicts
        """
        all_messages = self.read_messages(task_gid)

        # Track which messages have been resolved
        resolved_ids = set()
        for msg in all_messages:
            text = msg.get("text", "")
            if "[RESOLVED]" in text or "[ANSWER]" in text:
                # Look for reference to original message
                for other in all_messages:
                    if other["id"] in text:
                        resolved_ids.add(other["id"])

        pending = []
        for msg in all_messages:
            if msg["id"] in resolved_ids:
                continue
            msg_type = msg.get("type", "")
            if msg_type in ("QUESTION", "ALERT", "DIRECTIVE"):
                pending.append(msg)

        return pending

    @staticmethod
    def format_message(msg_type="INFO", priority="MEDIUM", subject="", body="", status=""):
        """
        Build a formatted Ciphergy message string.

        Args:
            msg_type: Message type (STATUS, ALERT, QUESTION, etc.)
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
            subject: Message subject line
            body: Message body text
            status: Optional status tag

        Returns:
            str: Formatted message string
        """
        type_tag = MESSAGE_TYPES.get(msg_type.upper(), f"[{msg_type.upper()}]")
        priority_tag = PRIORITIES.get(priority.upper(), priority)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        parts = [
            f"{type_tag} {priority_tag} | {subject}",
            f"Time: {timestamp}",
        ]

        if body:
            parts.append(f"\n{body}")

        if status:
            parts.append(f"\nStatus: {status}")

        parts.append("\n--- Ciphergy Pipeline")

        return "\n".join(parts)

    @staticmethod
    def _detect_message_type(text):
        """Detect message type from text content."""
        text_upper = text.upper()
        for type_name, tag in MESSAGE_TYPES.items():
            if tag in text_upper:
                return type_name
        return "INFO"


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------


def find_config():
    """Find the ciphergy.yaml config file."""
    candidates = [
        os.path.join(os.getcwd(), "config", "ciphergy.yaml"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "ciphergy.yaml"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def cli_read(args, bridge):
    """CLI: Read messages from a task."""
    messages = bridge.read_messages(args.task_gid)
    if not messages:
        print("No messages found.")
        return

    for msg in messages:
        print(f"\n{'=' * 60}")
        print(f"  From: {msg['author']}")
        print(f"  Date: {msg['created_at']}")
        print(f"  Type: {msg['type']}")
        print(f"  {'=' * 56}")
        print(f"  {msg['text']}")

    print(f"\n  Total: {len(messages)} message(s)")


def cli_post(args, bridge):
    """CLI: Post a message to a task."""
    if args.formatted:
        message = AsanaBridge.format_message(
            msg_type=args.type or "INFO",
            priority=args.priority or "MEDIUM",
            subject=args.subject or "",
            body=args.message,
            status=args.status or "",
        )
    else:
        message = args.message

    result = bridge.post_message(args.task_gid, message)
    print(f"  Message posted. Story GID: {result.get('gid', 'unknown')}")


def cli_pending(args, bridge):
    """CLI: Show pending messages."""
    pending = bridge.get_pending(args.task_gid)
    if not pending:
        print("  No pending messages.")
        return

    for msg in pending:
        print(f"\n  [{msg['type']}] {msg['created_at']}")
        print(f"  {msg['text'][:200]}...")

    print(f"\n  Total pending: {len(pending)}")


def main():
    parser = argparse.ArgumentParser(description="Ciphergy Pipeline — Asana Bridge")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Read
    read_parser = subparsers.add_parser("read", help="Read messages from a task")
    read_parser.add_argument("--task-gid", required=True, help="Asana task GID")

    # Post
    post_parser = subparsers.add_parser("post", help="Post a message to a task")
    post_parser.add_argument("--task-gid", required=True, help="Asana task GID")
    post_parser.add_argument("--message", required=True, help="Message text")
    post_parser.add_argument("--formatted", action="store_true", help="Use Ciphergy formatting")
    post_parser.add_argument("--type", default="INFO", help="Message type")
    post_parser.add_argument("--priority", default="MEDIUM", help="Priority level")
    post_parser.add_argument("--subject", default="", help="Subject line")
    post_parser.add_argument("--status", default="", help="Status tag")

    # Pending
    pending_parser = subparsers.add_parser("pending", help="Show pending messages")
    pending_parser.add_argument("--task-gid", required=True, help="Asana task GID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config_path = find_config()
    try:
        bridge = AsanaBridge(config_path=config_path)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    dispatch = {
        "read": cli_read,
        "post": cli_post,
        "pending": cli_pending,
    }

    dispatch[args.command](args, bridge)


if __name__ == "__main__":
    main()
