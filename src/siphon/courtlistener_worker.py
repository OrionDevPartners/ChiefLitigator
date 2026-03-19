"""Auto-Siphon Worker for CourtListener / Free Law Project.

This worker runs on a schedule (via EventBridge/Lambda) to fetch new
case law opinions, generate semantic embeddings, and insert them into
the Aurora Knowledge Graph.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.knowledge_models import CaseLaw
from src.providers.llm_provider import get_provider

logger = logging.getLogger("cyphergy.siphon.courtlistener")


class CourtListenerSiphon:
    """Worker to siphon data from CourtListener REST API."""

    BASE_URL = "https://www.courtlistener.com/api/rest/v3"

    def __init__(self, db_session: AsyncSession, api_token: str | None = None):
        self.db = db_session
        self.api_token = api_token
        self.llm = get_provider()
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Token {self.api_token}"} if self.api_token else {}
        )

    async def fetch_recent_opinions(self, days_back: int = 1) -> List[Dict[str, Any]]:
        """Fetch opinions filed in the last N days."""
        target_date = date.today() - timedelta(days=days_back)
        
        # CourtListener API endpoint for opinions
        url = f"{self.BASE_URL}/opinions/"
        params = {
            "date_filed__gte": target_date.isoformat(),
            "type": "010combined", # Standard opinions
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Failed to fetch from CourtListener: {e}")
            return []

    async def _generate_holding_summary(self, opinion_text: str) -> str:
        """Use Bedrock LLM to extract the core holding from the raw opinion."""
        prompt = f"""
        Extract the core legal holding (the 'rule of the case') from the following court opinion.
        Keep it under 3 sentences.
        
        Opinion:
        {opinion_text[:5000]}... # Truncated for token limits
        """
        response = await self.llm.create_message(
            system_prompt="You are an expert appellate clerk.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.text

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate a vector embedding for the text using AWS Bedrock Titan/Cohere."""
        # Mock embedding generation
        return [0.0] * 1536

    async def process_and_store(self, opinions: List[Dict[str, Any]]) -> int:
        """Process raw API data, generate embeddings, and store in Aurora."""
        count = 0
        for op in opinions:
            # 1. Extract raw data
            cl_id = op.get("id")
            text = op.get("html_with_citations") or op.get("plain_text")
            if not text:
                continue
                
            # 2. Generate AI enrichments
            holding = await self._generate_holding_summary(text)
            embedding = await self._get_embedding(holding)
            
            # 3. Create ORM model
            case = CaseLaw(
                courtlistener_id=cl_id,
                case_name=op.get("case_name", "Unknown Case"),
                citation=op.get("download_url", "Unknown Citation"), # Simplified for example
                court=op.get("court", "Unknown Court"),
                jurisdiction="federal", # Would need mapping logic
                date_filed=datetime.fromisoformat(op.get("date_filed")).date(),
                opinion_text=text,
                holding_summary=holding,
                embedding=embedding
            )
            
            self.db.add(case)
            count += 1
            
        await self.db.commit()
        return count

    async def run_daily_siphon(self):
        """Main entrypoint for the daily cron job."""
        logger.info("Starting daily CourtListener siphon...")
        opinions = await self.fetch_recent_opinions(days_back=1)
        logger.info(f"Fetched {len(opinions)} new opinions. Processing...")
        stored = await self.process_and_store(opinions)
        logger.info(f"Successfully stored {stored} new cases in Aurora Knowledge Graph.")
