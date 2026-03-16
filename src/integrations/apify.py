"""Apify integration — web scraping for jurisdiction data pipeline.

CPAA: All config from env vars. Code is function only.

Apify feeds the jurisdiction containers by:
1. Crawling state legislature sites for current statutory text
2. Scraping court websites for local rules and standing orders
3. Building the legal corpus that lives inside each of the 57 jurisdiction containers
4. Feeding the perpetual crawler with structured legal data

Usage::

    client = ApifyClient()

    # Scrape a state legislature site
    results = await client.run_actor(
        actor_id="apify/web-scraper",
        input_data={"startUrls": [{"url": "https://legis.la.gov/legis/Laws_Toc.aspx"}]},
    )

    # Feed results into jurisdiction container
    for result in results:
        catalog.siphon(parse_statute(result))
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("cyphergy.integrations.apify")

# CPAA: all config from env
_APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
_APIFY_BASE_URL = os.getenv("APIFY_BASE_URL", "https://api.apify.com/v2")


class ApifyClient:
    """CPAA-compliant Apify client for web scraping."""

    def __init__(self) -> None:
        self._token = _APIFY_TOKEN
        self._base_url = _APIFY_BASE_URL
        if not self._token:
            logger.warning("APIFY_TOKEN not set — Apify integration disabled")

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    async def run_actor(
        self,
        actor_id: str,
        input_data: dict[str, Any],
        timeout_secs: int = 300,
    ) -> list[dict[str, Any]]:
        """Run an Apify actor and return results.

        Args:
            actor_id: The Apify actor to run (e.g., "apify/web-scraper")
            input_data: Input configuration for the actor
            timeout_secs: Max wait time for actor completion
        """
        if not self._token:
            raise RuntimeError("APIFY_TOKEN not configured")

        import httpx

        async with httpx.AsyncClient(timeout=timeout_secs) as client:
            # Start the actor run
            resp = await client.post(
                f"{self._base_url}/acts/{actor_id}/runs",
                headers={"Authorization": f"Bearer {self._token}"},
                json=input_data,
            )
            resp.raise_for_status()
            run_data = resp.json()["data"]
            run_id = run_data["id"]

            logger.info("apify_run_started | actor=%s run_id=%s", actor_id, run_id)

            # Wait for completion
            import asyncio
            for _ in range(timeout_secs // 5):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"{self._base_url}/actor-runs/{run_id}",
                    headers={"Authorization": f"Bearer {self._token}"},
                )
                status = status_resp.json()["data"]["status"]
                if status == "SUCCEEDED":
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    raise RuntimeError(f"Apify run {run_id} failed: {status}")

            # Get results
            results_resp = await client.get(
                f"{self._base_url}/actor-runs/{run_id}/dataset/items",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            results_resp.raise_for_status()
            items = results_resp.json()

            logger.info("apify_run_complete | run_id=%s items=%d", run_id, len(items))
            return items

    async def scrape_state_statutes(self, state_code: str, url: str) -> list[dict[str, Any]]:
        """Scrape a state legislature website for statutory text."""
        return await self.run_actor(
            actor_id="apify/web-scraper",
            input_data={
                "startUrls": [{"url": url}],
                "maxCrawledPages": 100,
                "proxyConfiguration": {"useApifyProxy": True},
            },
        )

    async def scrape_court_rules(self, court_url: str) -> list[dict[str, Any]]:
        """Scrape a court website for local rules and standing orders."""
        return await self.run_actor(
            actor_id="apify/web-scraper",
            input_data={
                "startUrls": [{"url": court_url}],
                "maxCrawledPages": 50,
                "proxyConfiguration": {"useApifyProxy": True},
            },
        )
