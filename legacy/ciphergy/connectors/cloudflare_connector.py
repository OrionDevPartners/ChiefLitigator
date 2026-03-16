"""
Ciphergy Pipeline — Cloudflare Connector

Provides integration with Cloudflare services: Workers deployment,
Pages deployment, DNS management, KV storage, and R2 object storage.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ciphergy.connectors.base import BaseConnector, ConnectorConfig

logger = logging.getLogger(__name__)


class CloudflareConnector(BaseConnector):
    """
    Cloudflare connector for Ciphergy Pipeline.

    Provides Workers deployment, Pages deployment, DNS management,
    KV namespace operations, and R2 object storage via the Cloudflare API v4.
    """

    CONNECTOR_NAME = "cloudflare"
    BASE_URL = "https://api.cloudflare.com/client/v4"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._token: Optional[str] = config.api_key or os.environ.get("CLOUDFLARE_API_TOKEN")
        self._account_id: str = config.extra.get("account_id", os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""))
        self._zone_id: str = config.extra.get("zone_id", os.environ.get("CLOUDFLARE_ZONE_ID", ""))

    # ── Connection lifecycle ────────────────────────────────────────

    def connect(self) -> bool:
        """Verify Cloudflare API token and establish connection."""
        if not self._token:
            self._logger.error("No Cloudflare API token. Set CLOUDFLARE_API_TOKEN or pass api_key.")
            return False

        try:
            result = self._api_request("GET", "user/tokens/verify")
            status = result.get("result", {}).get("status", "")
            if status == "active":
                self._logger.info("Connected to Cloudflare (token active)")
                self._connected = True
                return True
            else:
                self._logger.error("Cloudflare token status: %s", status)
                return False
        except Exception as exc:
            self._logger.error("Failed to connect to Cloudflare: %s", exc)
            return False

    def disconnect(self) -> None:
        """Mark the connector as disconnected."""
        self._connected = False
        self._logger.info("Disconnected from Cloudflare")

    def health_check(self) -> bool:
        """Verify Cloudflare API is reachable and token is valid."""
        try:
            result = self._api_request("GET", "user/tokens/verify")
            return result.get("result", {}).get("status") == "active"
        except Exception:
            return False

    # ── Core interface ──────────────────────────────────────────────

    def fetch(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Fetch data from Cloudflare.

        Args:
            query: API endpoint path relative to base URL.
            **kwargs: Query parameters.

        Returns:
            Dict with "data", "status", and "connector" keys.
        """
        result = self._with_retry(f"CF fetch {query}", self._api_request, "GET", query)
        return {
            "data": result.get("result", result),
            "status": "ok",
            "connector": "cloudflare",
        }

    def push(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        Push data to Cloudflare.

        Args:
            data: Must contain "endpoint" key. Optional "payload" and "method" keys.
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

        self._with_retry(f"CF push {endpoint}", self._api_request, method, endpoint, payload)
        return True

    # ── Workers deployment ──────────────────────────────────────────

    def deploy_worker(self, name: str, script: str, bindings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Deploy a Cloudflare Worker script.

        Args:
            name: Worker script name.
            script: JavaScript/TypeScript source code.
            bindings: Optional list of binding configurations (KV, R2, etc.).

        Returns:
            Deployment result data.
        """
        # Workers API uses multipart form data for script upload
        metadata: Dict[str, Any] = {"main_module": "worker.js"}
        if bindings:
            metadata["bindings"] = bindings

        # For simplicity, use the single-script upload endpoint
        endpoint = f"accounts/{self._account_id}/workers/scripts/{name}"

        result = self._with_retry(
            f"Deploy worker {name}",
            self._api_request,
            "PUT",
            endpoint,
            None,
            content_type="application/javascript",
            raw_body=script.encode("utf-8"),
        )
        self._logger.info("Deployed worker: %s", name)
        return result.get("result", {})

    def delete_worker(self, name: str) -> bool:
        """
        Delete a Cloudflare Worker script.

        Args:
            name: Worker script name.

        Returns:
            True if deleted.
        """
        endpoint = f"accounts/{self._account_id}/workers/scripts/{name}"
        self._with_retry(f"Delete worker {name}", self._api_request, "DELETE", endpoint)
        return True

    def list_workers(self) -> List[Dict[str, Any]]:
        """
        List all Workers in the account.

        Returns:
            List of worker script metadata dicts.
        """
        endpoint = f"accounts/{self._account_id}/workers/scripts"
        result = self._with_retry("List workers", self._api_request, "GET", endpoint)
        return result.get("result", [])

    # ── Pages deployment ────────────────────────────────────────────

    def create_pages_project(
        self,
        name: str,
        production_branch: str = "main",
        build_command: str = "",
        destination_dir: str = "",
    ) -> Dict[str, Any]:
        """
        Create a Cloudflare Pages project.

        Args:
            name: Project name.
            production_branch: Git branch for production builds.
            build_command: Build command (e.g., "npm run build").
            destination_dir: Build output directory.

        Returns:
            The created project data.
        """
        payload: Dict[str, Any] = {
            "name": name,
            "production_branch": production_branch,
        }
        if build_command or destination_dir:
            payload["build_config"] = {}
            if build_command:
                payload["build_config"]["build_command"] = build_command
            if destination_dir:
                payload["build_config"]["destination_dir"] = destination_dir

        endpoint = f"accounts/{self._account_id}/pages/projects"
        result = self._with_retry("Create Pages project", self._api_request, "POST", endpoint, payload)
        self._logger.info("Created Pages project: %s", name)
        return result.get("result", {})

    def list_pages_projects(self) -> List[Dict[str, Any]]:
        """
        List all Pages projects in the account.

        Returns:
            List of project metadata dicts.
        """
        endpoint = f"accounts/{self._account_id}/pages/projects"
        result = self._with_retry("List Pages projects", self._api_request, "GET", endpoint)
        return result.get("result", [])

    def get_pages_deployments(self, project_name: str) -> List[Dict[str, Any]]:
        """
        List deployments for a Pages project.

        Args:
            project_name: The project name.

        Returns:
            List of deployment dicts.
        """
        endpoint = f"accounts/{self._account_id}/pages/projects/{project_name}/deployments"
        result = self._with_retry(f"Get Pages deployments {project_name}", self._api_request, "GET", endpoint)
        return result.get("result", [])

    # ── DNS management ──────────────────────────────────────────────

    def list_dns_records(self, zone_id: Optional[str] = None, record_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List DNS records for a zone.

        Args:
            zone_id: Zone ID (uses default if None).
            record_type: Optional filter by record type (A, AAAA, CNAME, etc.).

        Returns:
            List of DNS record dicts.
        """
        zid = zone_id or self._zone_id
        if not zid:
            self._logger.error("No zone_id configured for DNS operations")
            return []

        endpoint = f"zones/{zid}/dns_records"
        if record_type:
            endpoint += f"?type={record_type}"

        result = self._with_retry("List DNS records", self._api_request, "GET", endpoint)
        return result.get("result", [])

    def create_dns_record(
        self,
        record_type: str,
        name: str,
        content: str,
        ttl: int = 1,
        proxied: bool = True,
        zone_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a DNS record.

        Args:
            record_type: Record type (A, AAAA, CNAME, TXT, MX, etc.).
            name: Record name (e.g., "api.example.com").
            content: Record value.
            ttl: TTL in seconds (1 = automatic).
            proxied: Whether to proxy through Cloudflare.
            zone_id: Zone ID (uses default if None).

        Returns:
            The created DNS record data.
        """
        zid = zone_id or self._zone_id
        payload = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied,
        }

        endpoint = f"zones/{zid}/dns_records"
        result = self._with_retry("Create DNS record", self._api_request, "POST", endpoint, payload)
        self._logger.info("Created DNS record: %s %s -> %s", record_type, name, content)
        return result.get("result", {})

    def update_dns_record(
        self, record_id: str, record_type: str, name: str, content: str, zone_id: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Update a DNS record.

        Args:
            record_id: The DNS record ID.
            record_type: Record type.
            name: Record name.
            content: New record value.
            zone_id: Zone ID (uses default if None).
            **kwargs: Additional fields (ttl, proxied, etc.).

        Returns:
            The updated DNS record data.
        """
        zid = zone_id or self._zone_id
        payload: Dict[str, Any] = {"type": record_type, "name": name, "content": content}
        payload.update(kwargs)

        endpoint = f"zones/{zid}/dns_records/{record_id}"
        result = self._with_retry("Update DNS record", self._api_request, "PUT", endpoint, payload)
        return result.get("result", {})

    def delete_dns_record(self, record_id: str, zone_id: Optional[str] = None) -> bool:
        """
        Delete a DNS record.

        Args:
            record_id: The DNS record ID.
            zone_id: Zone ID (uses default if None).

        Returns:
            True if deleted.
        """
        zid = zone_id or self._zone_id
        endpoint = f"zones/{zid}/dns_records/{record_id}"
        self._with_retry("Delete DNS record", self._api_request, "DELETE", endpoint)
        return True

    # ── KV storage ──────────────────────────────────────────────────

    def kv_list_namespaces(self) -> List[Dict[str, Any]]:
        """
        List all KV namespaces in the account.

        Returns:
            List of namespace dicts.
        """
        endpoint = f"accounts/{self._account_id}/storage/kv/namespaces"
        result = self._with_retry("List KV namespaces", self._api_request, "GET", endpoint)
        return result.get("result", [])

    def kv_create_namespace(self, title: str) -> Dict[str, Any]:
        """
        Create a KV namespace.

        Args:
            title: Namespace title.

        Returns:
            The created namespace data (contains id).
        """
        endpoint = f"accounts/{self._account_id}/storage/kv/namespaces"
        result = self._with_retry(
            "Create KV namespace", self._api_request, "POST", endpoint, {"title": title}
        )
        return result.get("result", {})

    def kv_write(self, namespace_id: str, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> bool:
        """
        Write a key-value pair to a KV namespace.

        Args:
            namespace_id: The KV namespace ID.
            key: The key.
            value: The value (string).
            metadata: Optional metadata dict.

        Returns:
            True if written.
        """
        endpoint = f"accounts/{self._account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
        self._with_retry(
            f"KV write {key}",
            self._api_request,
            "PUT",
            endpoint,
            None,
            content_type="text/plain",
            raw_body=value.encode("utf-8"),
        )
        return True

    def kv_read(self, namespace_id: str, key: str) -> Optional[str]:
        """
        Read a value from a KV namespace.

        Args:
            namespace_id: The KV namespace ID.
            key: The key to read.

        Returns:
            The value as a string, or None if not found.
        """
        endpoint = f"accounts/{self._account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
        try:
            result = self._with_retry(f"KV read {key}", self._api_request, "GET", endpoint, raw_response=True)
            return result
        except Exception:
            return None

    def kv_delete(self, namespace_id: str, key: str) -> bool:
        """
        Delete a key from a KV namespace.

        Args:
            namespace_id: The KV namespace ID.
            key: The key to delete.

        Returns:
            True if deleted.
        """
        endpoint = f"accounts/{self._account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
        self._with_retry(f"KV delete {key}", self._api_request, "DELETE", endpoint)
        return True

    def kv_list_keys(self, namespace_id: str, prefix: str = "", limit: int = 1000) -> List[Dict[str, Any]]:
        """
        List keys in a KV namespace.

        Args:
            namespace_id: The KV namespace ID.
            prefix: Optional key prefix filter.
            limit: Maximum keys to return.

        Returns:
            List of key metadata dicts.
        """
        endpoint = f"accounts/{self._account_id}/storage/kv/namespaces/{namespace_id}/keys"
        params = f"?limit={limit}"
        if prefix:
            params += f"&prefix={prefix}"

        result = self._with_retry("KV list keys", self._api_request, "GET", f"{endpoint}{params}")
        return result.get("result", [])

    # ── R2 storage ──────────────────────────────────────────────────

    def r2_list_buckets(self) -> List[Dict[str, Any]]:
        """
        List all R2 buckets in the account.

        Returns:
            List of bucket dicts.
        """
        endpoint = f"accounts/{self._account_id}/r2/buckets"
        result = self._with_retry("R2 list buckets", self._api_request, "GET", endpoint)
        return result.get("result", {}).get("buckets", [])

    def r2_create_bucket(self, name: str, location_hint: str = "enam") -> Dict[str, Any]:
        """
        Create an R2 bucket.

        Args:
            name: Bucket name.
            location_hint: Location hint (enam, wnam, apac, weur, eeur).

        Returns:
            The created bucket data.
        """
        endpoint = f"accounts/{self._account_id}/r2/buckets"
        result = self._with_retry(
            "R2 create bucket",
            self._api_request,
            "POST",
            endpoint,
            {"name": name, "locationHint": location_hint},
        )
        self._logger.info("Created R2 bucket: %s", name)
        return result.get("result", {})

    def r2_delete_bucket(self, name: str) -> bool:
        """
        Delete an R2 bucket.

        Args:
            name: Bucket name.

        Returns:
            True if deleted.
        """
        endpoint = f"accounts/{self._account_id}/r2/buckets/{name}"
        self._with_retry(f"R2 delete bucket {name}", self._api_request, "DELETE", endpoint)
        return True

    # ── Private helpers ─────────────────────────────────────────────

    def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        content_type: str = "application/json",
        raw_body: Optional[bytes] = None,
        raw_response: bool = False,
    ) -> Any:
        """Make an authenticated Cloudflare API request."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": content_type,
        }

        if raw_body is not None:
            body = raw_body
        elif data is not None:
            body = json.dumps(data).encode()
        else:
            body = None

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                response_bytes = resp.read()
                if raw_response:
                    return response_bytes.decode("utf-8")
                response_text = response_bytes.decode()
                if not response_text:
                    return {"result": {}, "success": True}
                return json.loads(response_text)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode() if hasattr(exc, "read") else ""
            raise RuntimeError(f"Cloudflare API {exc.code}: {error_body}") from exc
