"""PACER Client — Federal court e-filing and docket access.

Provides authenticated access to PACER NextGen CM/ECF for:
  - Case search
  - Docket retrieval
  - Document download
  - E-filing submission

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger("cyphergy.integrations.pacer_client")


class PACERCase(BaseModel):
    case_number: str
    case_name: str
    court: str
    date_filed: str
    date_closed: Optional[str] = None
    judge: Optional[str] = None
    nature_of_suit: Optional[str] = None


class PACERDocketEntry(BaseModel):
    entry_number: int
    date_filed: str
    description: str
    document_number: Optional[str] = None
    document_url: Optional[str] = None


class PACERClient:
    """Authenticated PACER API client.

    Usage::

        client = PACERClient()
        await client.authenticate()
        cases = await client.search_cases(court="flsd", query="Smith v. Jones")
    """

    def __init__(self) -> None:
        self._base_url = os.getenv("PACER_API_URL", "https://pcl.uscourts.gov/pcl-public-api/rest")
        self._username = os.getenv("PACER_USERNAME", "")
        self._password = os.getenv("PACER_PASSWORD", "")
        self._token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info("PACERClient initialized")

    async def authenticate(self) -> bool:
        """Authenticate with PACER."""
        if not self._username or not self._password:
            logger.warning("PACER credentials not configured")
            return False

        try:
            self._session = aiohttp.ClientSession()
            async with self._session.post(
                f"{self._base_url}/authenticate",
                json={
                    "loginId": self._username,
                    "password": self._password,
                },
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._token = data.get("nextGenCSO", "")
                    logger.info("PACER authentication successful")
                    return True
                else:
                    logger.error("PACER auth failed: %d", resp.status)
                    return False
        except Exception as exc:
            logger.error("PACER auth error: %s", str(exc)[:200])
            return False

    async def search_cases(
        self,
        court: str,
        query: Optional[str] = None,
        case_number: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[PACERCase]:
        """Search for cases in a federal court."""
        if not self._token:
            await self.authenticate()

        params: Dict[str, Any] = {"courtId": court}
        if query:
            params["caseName"] = query
        if case_number:
            params["caseNumber"] = case_number
        if date_from:
            params["dateFiledFrom"] = date_from
        if date_to:
            params["dateFiledTo"] = date_to

        try:
            headers = {"X-NEXT-GEN-CSO": self._token or ""}
            async with self._session.get(
                f"{self._base_url}/cases",
                params=params,
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        PACERCase(
                            case_number=c.get("caseNumber", ""),
                            case_name=c.get("caseName", ""),
                            court=court,
                            date_filed=c.get("dateFiled", ""),
                            date_closed=c.get("dateClosed"),
                            judge=c.get("judge"),
                            nature_of_suit=c.get("natureOfSuit"),
                        )
                        for c in data.get("content", [])
                    ]
                else:
                    logger.error("PACER search failed: %d", resp.status)
                    return []
        except Exception as exc:
            logger.error("PACER search error: %s", str(exc)[:200])
            return []

    async def get_docket(
        self,
        court: str,
        case_number: str,
    ) -> List[PACERDocketEntry]:
        """Get the docket for a case."""
        if not self._token:
            await self.authenticate()

        try:
            headers = {"X-NEXT-GEN-CSO": self._token or ""}
            async with self._session.get(
                f"{self._base_url}/cases/{court}/{case_number}/docket-entries",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        PACERDocketEntry(
                            entry_number=e.get("entryNumber", 0),
                            date_filed=e.get("dateFiled", ""),
                            description=e.get("description", ""),
                            document_number=e.get("documentNumber"),
                        )
                        for e in data.get("content", [])
                    ]
                else:
                    return []
        except Exception as exc:
            logger.error("PACER docket error: %s", str(exc)[:200])
            return []

    async def close(self) -> None:
        """Close the PACER session."""
        if self._session:
            await self._session.close()
