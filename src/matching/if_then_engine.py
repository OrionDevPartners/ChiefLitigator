"""The If-Then Matching Engine.

This module translates raw user context into structured legal strategy by
querying the Aurora Knowledge Graph using semantic vector search.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.knowledge_models import CaseLaw, CourtRule, Statute
from src.providers.llm_provider import get_provider

logger = logging.getLogger("cyphergy.matching.if_then_engine")


class ExtractedFact(BaseModel):
    """A single fact extracted from user narrative."""
    entity: str = Field(description="The actor (e.g., Landlord, Employer)")
    action: str = Field(description="What they did (e.g., changed locks, fired me)")
    context: str = Field(description="Surrounding circumstances")


class LegalMatch(BaseModel):
    """A matched legal concept based on facts."""
    statute_id: str | None = None
    statute_citation: str | None = None
    cause_of_action: str
    confidence_score: float
    reasoning: str


class IfThenEngine:
    """Core engine for translating facts to law."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.llm = get_provider()

    async def extract_facts(self, user_narrative: str) -> List[ExtractedFact]:
        """Step 1: Extract structured facts from messy human narrative."""
        prompt = f"""
        Extract the core legal facts from the following user narrative.
        Identify the entities, their actions, and the context.
        
        Narrative:
        {user_narrative}
        """
        # In a real implementation, this would use structured output (JSON mode)
        # from the Bedrock LLM to return a list of ExtractedFact objects.
        response = await self.llm.create_message(
            system_prompt="You are an expert legal intake assessor.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        # Mocking the parsed response for now
        return [
            ExtractedFact(entity="Landlord", action="Changed locks", context="Tenant was at work")
        ]

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate a vector embedding for the text using AWS Bedrock Titan/Cohere."""
        # Mock embedding generation
        return [0.0] * 1536

    async def match_statutes(self, facts: List[ExtractedFact], jurisdiction: str) -> List[LegalMatch]:
        """Step 2: Semantic search against Aurora statutes table."""
        fact_text = " ".join([f"{f.entity} {f.action} {f.context}" for f in facts])
        vector = await self._get_embedding(fact_text)

        # Perform vector similarity search in PostgreSQL via pgvector
        # Using cosine distance (<=>)
        stmt = (
            select(Statute)
            .where(Statute.jurisdiction == jurisdiction)
            .order_by(Statute.embedding.cosine_distance(vector))
            .limit(5)
        )
        
        result = await self.db.execute(stmt)
        statutes = result.scalars().all()
        
        matches = []
        for stat in statutes:
            # Step 3: The "If-Then" evaluation
            # Here we would ask the LLM to evaluate if the specific facts trigger this statute
            matches.append(
                LegalMatch(
                    statute_id=str(stat.id),
                    statute_citation=f"{stat.title} § {stat.section}",
                    cause_of_action=stat.heading,
                    confidence_score=0.85, # Mock score
                    reasoning=f"The action '{facts[0].action}' directly implicates {stat.heading}."
                )
            )
            
        return matches

    async def infer_procedures(self, match: LegalMatch, jurisdiction: str) -> List[CourtRule]:
        """Step 4: Infer required procedures based on the matched cause of action."""
        # Query the court_rules table based on the cause of action
        stmt = (
            select(CourtRule)
            .where(CourtRule.jurisdiction == jurisdiction)
            # In reality, this would be another semantic search or a relational join
            # mapping causes of action to required procedural rules.
            .limit(3)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
