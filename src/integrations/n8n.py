"""n8n integration — self-hosted workflow automation for Cyphergy.

CPAA: All config from env vars. Code is function only.

n8n replaces Zapier — self-hosted, no per-task fees, runs in Docker.

What n8n handles for Cyphergy:
1. PACER email routing — court notification triggers
2. Cross-service automation — when a case deadline approaches, trigger:
   - Email notification to user
   - Calendar event creation
   - Slack/Linear notification
3. Perpetual crawler scheduling — trigger crawl batches
4. Case intake automation — when user uploads docs, trigger OCR + classification
5. WDC result notifications — when a debate completes, notify admin

Usage::

    client = N8nClient()

    # Trigger a workflow
    result = await client.trigger_workflow(
        workflow_id="case-deadline-alert",
        data={"case_id": "xxx", "deadline_date": "2026-04-01", "days_left": 3},
    )

    # List active workflows
    workflows = await client.list_workflows()
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("cyphergy.integrations.n8n")

# CPAA: all config from env
_N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
_N8N_API_KEY = os.getenv("N8N_TOKEN", "")


class N8nClient:
    """CPAA-compliant n8n client for workflow automation."""

    def __init__(self) -> None:
        self._base_url = _N8N_BASE_URL
        self._api_key = _N8N_API_KEY
        if not self._api_key:
            logger.warning("N8N_TOKEN not set — n8n integration disabled")

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def trigger_workflow(
        self,
        workflow_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Trigger an n8n workflow by ID with input data.

        Args:
            workflow_id: The n8n workflow ID or webhook path
            data: Input data for the workflow
        """
        if not self._api_key:
            raise RuntimeError("N8N_TOKEN not configured")

        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/workflows/{workflow_id}/execute",
                headers={"X-N8N-API-KEY": self._api_key},
                json={"data": data},
            )
            resp.raise_for_status()
            result = resp.json()

            logger.info(
                "n8n_workflow_triggered | workflow=%s status=%s",
                workflow_id,
                result.get("status", "unknown"),
            )
            return result

    async def trigger_webhook(
        self,
        webhook_path: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Trigger an n8n workflow via webhook URL."""
        if not self._api_key:
            raise RuntimeError("N8N_TOKEN not configured")

        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/webhook/{webhook_path}",
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_workflows(self) -> list[dict[str, Any]]:
        """List all active n8n workflows."""
        if not self._api_key:
            return []

        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._base_url}/api/v1/workflows",
                headers={"X-N8N-API-KEY": self._api_key},
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def trigger_deadline_alert(
        self,
        case_id: str,
        deadline_date: str,
        days_left: int,
        user_email: str,
    ) -> dict[str, Any]:
        """Trigger the deadline alert workflow."""
        return await self.trigger_webhook(
            webhook_path="case-deadline-alert",
            data={
                "case_id": case_id,
                "deadline_date": deadline_date,
                "days_left": days_left,
                "user_email": user_email,
            },
        )

    async def trigger_crawl_batch(
        self,
        jurisdiction: str,
        batch_size: int = 20,
    ) -> dict[str, Any]:
        """Trigger a crawler batch for a specific jurisdiction."""
        return await self.trigger_webhook(
            webhook_path="crawler-batch",
            data={
                "jurisdiction": jurisdiction,
                "batch_size": batch_size,
            },
        )
