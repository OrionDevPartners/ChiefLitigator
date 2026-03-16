"""
Ciphergy Pipeline — GitHub Connector

Full GitHub API integration for Ciphergy. Handles repos, issues, PRs,
Actions workflows, file read/write, and webhooks.
"""

import base64
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ciphergy.connectors.base import BaseConnector, ConnectorConfig

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    """
    GitHub connector for Ciphergy Pipeline.

    Provides repo management, issue/PR CRUD, Actions workflow triggers,
    file read/write via the GitHub API, and webhook support.
    """

    CONNECTOR_NAME = "github"
    BASE_URL = "https://api.github.com"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._token: Optional[str] = config.api_key or os.environ.get("GITHUB_TOKEN")
        self._owner: str = config.extra.get("owner", "")
        self._repo: str = config.extra.get("repo", "")
        self._default_branch: str = config.extra.get("default_branch", "main")

    @property
    def _repo_prefix(self) -> str:
        """URL prefix for the configured repo."""
        return f"repos/{self._owner}/{self._repo}"

    # ── Connection lifecycle ────────────────────────────────────────

    def connect(self) -> bool:
        """Verify GitHub token and establish connection."""
        if not self._token:
            self._logger.error("No GitHub token. Set GITHUB_TOKEN or pass api_key.")
            return False

        try:
            result = self._api_request("GET", "user")
            login = result.get("login", "Unknown")
            self._logger.info("Connected to GitHub as: %s", login)
            self._connected = True
            return True
        except Exception as exc:
            self._logger.error("Failed to connect to GitHub: %s", exc)
            return False

    def disconnect(self) -> None:
        """Mark the connector as disconnected."""
        self._connected = False
        self._logger.info("Disconnected from GitHub")

    def health_check(self) -> bool:
        """Verify GitHub API is reachable and token is valid."""
        try:
            result = self._api_request("GET", "rate_limit")
            return "rate" in result
        except Exception:
            return False

    # ── Core interface ──────────────────────────────────────────────

    def fetch(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Fetch data from GitHub.

        Args:
            query: API endpoint path (e.g., "repos/{owner}/{repo}/issues").
            **kwargs: Query parameters appended to the URL.

        Returns:
            Dict with "data", "status", and "connector" keys.
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        if params:
            query_string = urllib.parse.urlencode(params)
            query = f"{query}?{query_string}"

        result = self._with_retry(f"GitHub fetch {query}", self._api_request, "GET", query)
        return {
            "data": result if isinstance(result, list) else result,
            "status": "ok",
            "connector": "github",
        }

    def push(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        Push data to GitHub.

        Args:
            data: Must contain "endpoint" and "payload" keys.
            **kwargs: Additional parameters.

        Returns:
            True if successful.
        """
        endpoint = data.get("endpoint", "")
        payload = data.get("payload", {})
        method = data.get("method", "POST")

        if not endpoint:
            self._logger.error("Push requires 'endpoint' in data")
            return False

        self._with_retry(f"GitHub push {endpoint}", self._api_request, method, endpoint, payload)
        return True

    # ── Repo management ─────────────────────────────────────────────

    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        auto_init: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new GitHub repository.

        Args:
            name: Repository name.
            description: Repository description.
            private: Whether the repo is private.
            auto_init: Initialize with a README.

        Returns:
            The created repo data.
        """
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        result = self._with_retry("Create repo", self._api_request, "POST", "user/repos", payload)
        self._logger.info("Created repo: %s/%s", result.get("owner", {}).get("login"), name)
        return result

    def get_repo(self, owner: Optional[str] = None, repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Get repository information.

        Args:
            owner: Repo owner (uses default if None).
            repo: Repo name (uses default if None).

        Returns:
            Repository data dict.
        """
        o = owner or self._owner
        r = repo or self._repo
        return self._with_retry("Get repo", self._api_request, "GET", f"repos/{o}/{r}")

    def list_branches(self) -> List[Dict[str, Any]]:
        """
        List all branches in the configured repository.

        Returns:
            List of branch dicts.
        """
        result = self._with_retry("List branches", self._api_request, "GET", f"{self._repo_prefix}/branches")
        return result if isinstance(result, list) else []

    # ── Issue management ────────────────────────────────────────────

    def create_issue(
        self,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new issue.

        Args:
            title: Issue title.
            body: Issue body (Markdown).
            labels: List of label names.
            assignees: List of assignee usernames.
            milestone: Milestone number.

        Returns:
            The created issue data.
        """
        payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        if milestone:
            payload["milestone"] = milestone

        result = self._with_retry("Create issue", self._api_request, "POST", f"{self._repo_prefix}/issues", payload)
        self._logger.info("Created issue #%s: %s", result.get("number"), title)
        return result

    def list_issues(
        self, state: str = "open", labels: Optional[str] = None, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """
        List issues in the repository.

        Args:
            state: Filter by state ("open", "closed", "all").
            labels: Comma-separated label names to filter by.
            per_page: Number of results per page.

        Returns:
            List of issue dicts.
        """
        params = f"?state={state}&per_page={per_page}"
        if labels:
            params += f"&labels={urllib.parse.quote(labels)}"

        result = self._with_retry(
            "List issues",
            self._api_request,
            "GET",
            f"{self._repo_prefix}/issues{params}",
        )
        return result if isinstance(result, list) else []

    def update_issue(self, issue_number: int, **fields: Any) -> Dict[str, Any]:
        """
        Update an existing issue.

        Args:
            issue_number: The issue number.
            **fields: Fields to update (title, body, state, labels, assignees, etc.).

        Returns:
            The updated issue data.
        """
        result = self._with_retry(
            f"Update issue #{issue_number}",
            self._api_request,
            "PATCH",
            f"{self._repo_prefix}/issues/{issue_number}",
            fields,
        )
        return result

    # ── Pull request management ─────────────────────────────────────

    def create_pull_request(
        self,
        title: str,
        head: str,
        base: Optional[str] = None,
        body: str = "",
        draft: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a pull request.

        Args:
            title: PR title.
            head: Head branch.
            base: Base branch (uses default_branch if None).
            body: PR body (Markdown).
            draft: Create as draft PR.

        Returns:
            The created PR data.
        """
        payload = {
            "title": title,
            "head": head,
            "base": base or self._default_branch,
            "body": body,
            "draft": draft,
        }
        result = self._with_retry("Create PR", self._api_request, "POST", f"{self._repo_prefix}/pulls", payload)
        self._logger.info("Created PR #%s: %s", result.get("number"), title)
        return result

    def list_pull_requests(self, state: str = "open") -> List[Dict[str, Any]]:
        """
        List pull requests.

        Args:
            state: Filter by state ("open", "closed", "all").

        Returns:
            List of PR dicts.
        """
        result = self._with_retry(
            "List PRs",
            self._api_request,
            "GET",
            f"{self._repo_prefix}/pulls?state={state}",
        )
        return result if isinstance(result, list) else []

    def merge_pull_request(
        self, pr_number: int, merge_method: str = "squash", commit_title: str = ""
    ) -> Dict[str, Any]:
        """
        Merge a pull request.

        Args:
            pr_number: PR number.
            merge_method: Merge method ("merge", "squash", "rebase").
            commit_title: Optional custom commit title.

        Returns:
            Merge result data.
        """
        payload: Dict[str, Any] = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title

        result = self._with_retry(
            f"Merge PR #{pr_number}",
            self._api_request,
            "PUT",
            f"{self._repo_prefix}/pulls/{pr_number}/merge",
            payload,
        )
        return result

    # ── Actions workflow management ─────────────────────────────────

    def trigger_workflow(
        self, workflow_id: str, ref: Optional[str] = None, inputs: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Trigger a GitHub Actions workflow dispatch event.

        Args:
            workflow_id: Workflow file name or ID (e.g., "deploy.yml").
            ref: Git ref (branch/tag). Defaults to default_branch.
            inputs: Optional workflow inputs.

        Returns:
            True if the dispatch was accepted.
        """
        payload: Dict[str, Any] = {"ref": ref or self._default_branch}
        if inputs:
            payload["inputs"] = inputs

        self._with_retry(
            f"Trigger workflow {workflow_id}",
            self._api_request,
            "POST",
            f"{self._repo_prefix}/actions/workflows/{workflow_id}/dispatches",
            payload,
        )
        self._logger.info("Triggered workflow: %s on %s", workflow_id, payload["ref"])
        return True

    def list_workflow_runs(
        self, workflow_id: Optional[str] = None, status: Optional[str] = None, per_page: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List workflow runs.

        Args:
            workflow_id: Optional workflow file name to filter by.
            status: Optional status filter ("queued", "in_progress", "completed").
            per_page: Number of results.

        Returns:
            List of workflow run dicts.
        """
        if workflow_id:
            endpoint = f"{self._repo_prefix}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"{self._repo_prefix}/actions/runs"

        params = f"?per_page={per_page}"
        if status:
            params += f"&status={status}"

        result = self._with_retry("List workflow runs", self._api_request, "GET", f"{endpoint}{params}")
        return result.get("workflow_runs", [])

    # ── File operations via API ─────────────────────────────────────

    def read_file(self, path: str, ref: Optional[str] = None) -> Dict[str, Any]:
        """
        Read a file from the repository.

        Args:
            path: File path within the repository.
            ref: Git ref (branch/tag/sha). Defaults to default_branch.

        Returns:
            Dict with "content" (decoded), "sha", "path", and "size".
        """
        endpoint = f"{self._repo_prefix}/contents/{path}"
        if ref:
            endpoint += f"?ref={ref}"

        result = self._with_retry(f"Read file {path}", self._api_request, "GET", endpoint)

        content = ""
        if result.get("content"):
            content = base64.b64decode(result["content"]).decode("utf-8")

        return {
            "content": content,
            "sha": result.get("sha", ""),
            "path": result.get("path", path),
            "size": result.get("size", 0),
            "encoding": result.get("encoding", ""),
        }

    def write_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a file in the repository.

        Args:
            path: File path within the repository.
            content: File content (will be base64-encoded).
            message: Commit message.
            branch: Target branch (uses default_branch if None).
            sha: Current file SHA (required for updates, not for creates).

        Returns:
            The commit and content data.
        """
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        payload: Dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch or self._default_branch,
        }
        if sha:
            payload["sha"] = sha

        result = self._with_retry(
            f"Write file {path}",
            self._api_request,
            "PUT",
            f"{self._repo_prefix}/contents/{path}",
            payload,
        )
        self._logger.info("Wrote file: %s", path)
        return result

    def delete_file(self, path: str, message: str, sha: str, branch: Optional[str] = None) -> bool:
        """
        Delete a file from the repository.

        Args:
            path: File path within the repository.
            message: Commit message.
            sha: Current file SHA.
            branch: Target branch.

        Returns:
            True if deleted successfully.
        """
        payload: Dict[str, Any] = {
            "message": message,
            "sha": sha,
            "branch": branch or self._default_branch,
        }
        self._with_retry(
            f"Delete file {path}",
            self._api_request,
            "DELETE",
            f"{self._repo_prefix}/contents/{path}",
            payload,
        )
        return True

    # ── Webhook operations ──────────────────────────────────────────

    def register_webhook(
        self,
        target_url: str,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None,
        active: bool = True,
    ) -> Dict[str, Any]:
        """
        Register a webhook on the repository.

        Args:
            target_url: URL to receive webhook events.
            events: List of event types (e.g., ["push", "pull_request"]).
            secret: Webhook secret for payload signing.
            active: Whether the webhook is active.

        Returns:
            The created webhook data.
        """
        config: Dict[str, Any] = {
            "url": target_url,
            "content_type": "json",
        }
        if secret:
            config["secret"] = secret

        payload = {
            "config": config,
            "events": events or ["push"],
            "active": active,
        }

        result = self._with_retry(
            "Register webhook",
            self._api_request,
            "POST",
            f"{self._repo_prefix}/hooks",
            payload,
        )
        self._logger.info("Webhook registered: %s", target_url)
        return result

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all webhooks on the repository.

        Returns:
            List of webhook dicts.
        """
        result = self._with_retry("List webhooks", self._api_request, "GET", f"{self._repo_prefix}/hooks")
        return result if isinstance(result, list) else []

    def delete_webhook(self, hook_id: int) -> bool:
        """
        Delete a webhook.

        Args:
            hook_id: The webhook ID.

        Returns:
            True if deleted.
        """
        self._with_retry(
            f"Delete webhook {hook_id}",
            self._api_request,
            "DELETE",
            f"{self._repo_prefix}/hooks/{hook_id}",
        )
        return True

    # ── Private helpers ─────────────────────────────────────────────

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Make an authenticated GitHub API request."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if data and method != "GET":
            headers["Content-Type"] = "application/json"

        body = json.dumps(data).encode() if data and method != "GET" else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                response_body = resp.read().decode()
                if not response_body:
                    return {}
                return json.loads(response_body)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if hasattr(exc, "read") else ""
            raise RuntimeError(f"GitHub API {exc.code}: {error_body}") from exc
