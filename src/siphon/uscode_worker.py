"""Auto-Siphon Worker for US Code (Office of Law Revision Counsel).

Downloads the full US Code XML bulk archive, parses each title/section,
generates semantic embeddings, and stores in Aurora.
"""

from __future__ import annotations

import io
import logging
import os
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.knowledge_models import Statute

logger = logging.getLogger("cyphergy.siphon.uscode")

# OLRC bulk download base URL
USCODE_DOWNLOAD_URL = "https://uscode.house.gov/download/releasepoints/us/pl/119/73/xml_usc{title}@119-73.zip"

# All 54 titles of the US Code
USC_TITLES = [str(i) for i in range(1, 55)]


class USCodeSiphon:
    """Worker to siphon the entire US Code from OLRC XML bulk downloads."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.client = httpx.AsyncClient(timeout=120.0)

    async def download_title(self, title_num: str) -> bytes | None:
        """Download the XML zip for a specific USC title."""
        url = USCODE_DOWNLOAD_URL.format(title=title_num.zfill(2))
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.warning(f"Failed to download USC Title {title_num}: {e}")
            return None

    def parse_title_xml(self, zip_bytes: bytes, title_num: str) -> List[Dict[str, Any]]:
        """Parse the XML inside the zip to extract sections."""
        sections = []
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    if name.endswith(".xml"):
                        xml_content = zf.read(name)
                        root = ET.fromstring(xml_content)
                        # Parse sections from USLM XML schema
                        for section in root.iter("{http://xml.house.gov/schemas/uslm/1.0}section"):
                            sec_id = section.get("identifier", "")
                            heading_el = section.find("{http://xml.house.gov/schemas/uslm/1.0}heading")
                            heading = heading_el.text if heading_el is not None else ""
                            # Extract all text content
                            text = " ".join(section.itertext()).strip()
                            if text:
                                sections.append({
                                    "title": f"Title {title_num}",
                                    "section": sec_id,
                                    "heading": heading,
                                    "text": text,
                                })
        except Exception as e:
            logger.error(f"Failed to parse USC Title {title_num}: {e}")
        return sections

    async def process_and_store(self, sections: List[Dict[str, Any]]) -> int:
        """Store parsed statute sections in Aurora."""
        count = 0
        for sec in sections:
            statute = Statute(
                jurisdiction="federal",
                title=sec["title"],
                section=sec["section"],
                heading=sec["heading"],
                text=sec["text"],
                # Embedding will be generated in a separate batch job
                embedding=None,
            )
            self.db.add(statute)
            count += 1

        await self.db.commit()
        return count

    async def run_full_ingest(self):
        """Download and ingest all 54 titles of the US Code."""
        logger.info("Starting full US Code ingest...")
        total = 0
        for title_num in USC_TITLES:
            logger.info(f"Processing USC Title {title_num}...")
            zip_bytes = await self.download_title(title_num)
            if zip_bytes:
                sections = self.parse_title_xml(zip_bytes, title_num)
                stored = await self.process_and_store(sections)
                total += stored
                logger.info(f"Title {title_num}: stored {stored} sections.")
        logger.info(f"US Code ingest complete. Total sections stored: {total}")
