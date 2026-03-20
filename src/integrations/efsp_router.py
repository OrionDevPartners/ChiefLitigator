"""EFSP Router — Electronic Filing Service Provider routing for state courts.

Routes e-filing requests to the appropriate state EFSP based on jurisdiction:
  - Tyler Odyssey (30+ states)
  - eFileTexas
  - eFileIL
  - NYSCEF (New York)
  - TrueFiling (California appellate)
  - File & ServeXpress

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger("cyphergy.integrations.efsp_router")


class EFSPConfig(BaseModel):
    """Configuration for an EFSP."""
    name: str
    base_url: str
    api_key_env: str
    supports_pro_se: bool = True
    accepted_formats: list = ["PDF"]
    max_file_size_mb: int = 35


# EFSP configurations per state
EFSP_REGISTRY: Dict[str, EFSPConfig] = {
    "TX": EFSPConfig(
        name="eFileTexas",
        base_url=os.getenv("EFILE_TEXAS_URL", "https://efile.txcourts.gov/api"),
        api_key_env="EFILE_TEXAS_KEY",
        supports_pro_se=True,
    ),
    "IL": EFSPConfig(
        name="eFileIL",
        base_url=os.getenv("EFILE_IL_URL", "https://efile.illinoiscourts.gov/api"),
        api_key_env="EFILE_IL_KEY",
        supports_pro_se=True,
    ),
    "NY": EFSPConfig(
        name="NYSCEF",
        base_url=os.getenv("NYSCEF_URL", "https://iapps.courts.state.ny.us/nyscef/api"),
        api_key_env="NYSCEF_KEY",
        supports_pro_se=True,
    ),
    "CA": EFSPConfig(
        name="TrueFiling",
        base_url=os.getenv("TRUEFILING_URL", "https://tf3.truefiling.com/api"),
        api_key_env="TRUEFILING_KEY",
        supports_pro_se=True,
    ),
    "FL": EFSPConfig(
        name="Tyler Odyssey (FL)",
        base_url=os.getenv("TYLER_FL_URL", "https://florida.tylerhost.net/api"),
        api_key_env="TYLER_FL_KEY",
        supports_pro_se=True,
    ),
    "GA": EFSPConfig(
        name="Tyler Odyssey (GA)",
        base_url=os.getenv("TYLER_GA_URL", "https://georgia.tylerhost.net/api"),
        api_key_env="TYLER_GA_KEY",
        supports_pro_se=True,
    ),
    "IN": EFSPConfig(
        name="Tyler Odyssey (IN)",
        base_url=os.getenv("TYLER_IN_URL", "https://indiana.tylerhost.net/api"),
        api_key_env="TYLER_IN_KEY",
        supports_pro_se=True,
    ),
    "MN": EFSPConfig(
        name="Tyler Odyssey (MN)",
        base_url=os.getenv("TYLER_MN_URL", "https://minnesota.tylerhost.net/api"),
        api_key_env="TYLER_MN_KEY",
        supports_pro_se=True,
    ),
}


class EFSPRouter:
    """Routes e-filing requests to the appropriate state EFSP.

    Usage::

        router = EFSPRouter()
        config = router.get_efsp("TX")
        result = await router.submit_filing("TX", filing_envelope)
    """

    def __init__(self) -> None:
        logger.info("EFSPRouter initialized with %d state configurations", len(EFSP_REGISTRY))

    def get_efsp(self, state: str) -> Optional[EFSPConfig]:
        """Get the EFSP configuration for a state."""
        return EFSP_REGISTRY.get(state.upper())

    def supports_efiling(self, state: str) -> bool:
        """Check if a state supports electronic filing."""
        return state.upper() in EFSP_REGISTRY

    def supports_pro_se(self, state: str) -> bool:
        """Check if a state's EFSP supports pro se filers."""
        config = EFSP_REGISTRY.get(state.upper())
        return config.supports_pro_se if config else False

    async def submit_filing(
        self,
        state: str,
        filing_envelope: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Submit a filing to the appropriate state EFSP."""
        config = EFSP_REGISTRY.get(state.upper())
        if not config:
            return {
                "status": "error",
                "message": f"No EFSP configured for state: {state}",
                "manual_filing_required": True,
            }

        api_key = os.getenv(config.api_key_env, "")
        if not api_key:
            return {
                "status": "error",
                "message": f"API key not configured for {config.name}",
            }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                async with session.post(
                    f"{config.base_url}/filings",
                    json=filing_envelope,
                    headers=headers,
                ) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        return {
                            "status": "submitted",
                            "efsp": config.name,
                            "confirmation": data.get("filingId", ""),
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "status": "rejected",
                            "efsp": config.name,
                            "error": error_text[:500],
                        }
        except Exception as exc:
            return {
                "status": "error",
                "efsp": config.name,
                "error": str(exc)[:200],
            }

    def get_all_supported_states(self) -> Dict[str, str]:
        """Get all states with EFSP support."""
        return {state: config.name for state, config in EFSP_REGISTRY.items()}
