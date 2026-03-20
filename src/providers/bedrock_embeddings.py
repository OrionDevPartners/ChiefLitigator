"""Bedrock Embeddings Service — Titan Embeddings V2 for pgvector semantic search.

Provides vector embedding generation for the ChiefLitigator knowledge graph:
  - Case law holdings → 1536-dim vectors stored in Aurora pgvector
  - Statute text → 1536-dim vectors for semantic statute matching
  - Court rules → 1536-dim vectors for procedural matching
  - User narratives → 1536-dim vectors for If-Then matching

Uses Amazon Titan Text Embeddings V2 (amazon.titan-embed-text-v2:0)
which produces 1024-dim vectors by default, configurable up to 1536.

All configuration via environment variables. No hardcoded secrets.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger("cyphergy.providers.bedrock_embeddings")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BEDROCK_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
EMBEDDING_MODEL = os.getenv(
    "BEDROCK_EMBEDDING_MODEL",
    "amazon.titan-embed-text-v2:0",
)
EMBEDDING_DIMENSIONS = int(os.getenv("BEDROCK_EMBEDDING_DIMENSIONS", "1536"))
EMBEDDING_NORMALIZE = os.getenv("BEDROCK_EMBEDDING_NORMALIZE", "true").lower() == "true"
BATCH_SIZE = int(os.getenv("BEDROCK_EMBEDDING_BATCH_SIZE", "25"))


class EmbeddingResult:
    """Result of an embedding operation."""

    __slots__ = ("text", "vector", "dimensions", "text_hash")

    def __init__(self, text: str, vector: List[float], dimensions: int) -> None:
        self.text = text
        self.vector = vector
        self.dimensions = dimensions
        self.text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]


class BedrockEmbeddingService:
    """Generates vector embeddings via Amazon Titan Text Embeddings V2.

    Designed for high-throughput ingestion (siphon pipeline) and
    low-latency query-time embedding (user search).

    Usage::

        service = BedrockEmbeddingService()

        # Single embedding
        result = await service.embed("landlord changed locks while tenant at work")

        # Batch embedding (for siphon pipeline)
        results = await service.embed_batch([
            "42 USC 1983 - Civil action for deprivation of rights",
            "FL Stat 83.67 - Prohibited practices during tenancy",
            ...
        ])
    """

    def __init__(self) -> None:
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
        )
        self._model_id = EMBEDDING_MODEL
        self._dimensions = EMBEDDING_DIMENSIONS
        self._normalize = EMBEDDING_NORMALIZE

        # In-memory LRU cache for repeated queries (query-time optimization)
        self._cache: Dict[str, List[float]] = {}
        self._cache_max = int(os.getenv("EMBEDDING_CACHE_MAX", "10000"))

        logger.info(
            "BedrockEmbeddingService initialized: model=%s dims=%d normalize=%s",
            self._model_id,
            self._dimensions,
            self._normalize,
        )

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate a vector embedding for a single text input.

        Args:
            text: The text to embed (max ~8,192 tokens for Titan V2).

        Returns:
            EmbeddingResult with the vector and metadata.
        """
        cache_key = hashlib.sha256(text.encode()).hexdigest()[:16]
        if cache_key in self._cache:
            return EmbeddingResult(
                text=text,
                vector=self._cache[cache_key],
                dimensions=self._dimensions,
            )

        body = json.dumps({
            "inputText": text,
            "dimensions": self._dimensions,
            "normalize": self._normalize,
        })

        response = await asyncio.to_thread(
            self._client.invoke_model,
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        vector = response_body.get("embedding", [])

        # Cache the result
        if len(self._cache) < self._cache_max:
            self._cache[cache_key] = vector

        return EmbeddingResult(
            text=text,
            vector=vector,
            dimensions=len(vector),
        )

    async def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False,
    ) -> List[EmbeddingResult]:
        """Generate embeddings for a batch of texts.

        Processes in chunks of BATCH_SIZE to respect API limits.
        Uses asyncio.gather for concurrent processing within each batch.

        Args:
            texts: List of texts to embed.
            show_progress: If True, log progress every batch.

        Returns:
            List of EmbeddingResult objects in the same order as input.
        """
        results: List[EmbeddingResult] = []
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(0, len(texts), BATCH_SIZE):
            batch = texts[batch_idx : batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1

            if show_progress:
                logger.info(
                    "Embedding batch %d/%d (%d texts)",
                    batch_num,
                    total_batches,
                    len(batch),
                )

            # Process batch concurrently
            tasks = [self.embed(text) for text in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(
                        "Embedding failed for text[%d]: %s",
                        batch_idx + i,
                        str(result)[:200],
                    )
                    # Return zero vector for failed embeddings
                    results.append(
                        EmbeddingResult(
                            text=batch[i],
                            vector=[0.0] * self._dimensions,
                            dimensions=self._dimensions,
                        )
                    )
                else:
                    results.append(result)

        return results

    async def similarity_search(
        self,
        query: str,
        table: str,
        vector_column: str = "embedding",
        limit: int = 10,
        db_session: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Perform a semantic similarity search against a pgvector table.

        Generates the query embedding, then executes a cosine similarity
        search against the specified Aurora PostgreSQL table.

        Args:
            query: Natural language query text.
            table: Database table name (e.g., 'case_law', 'statutes').
            vector_column: Name of the pgvector column.
            limit: Maximum results to return.
            db_session: SQLAlchemy async session (if None, creates one).

        Returns:
            List of matching records with similarity scores.
        """
        # Generate query embedding
        query_embedding = await self.embed(query)

        # Build pgvector cosine similarity query
        vector_str = "[" + ",".join(str(v) for v in query_embedding.vector) + "]"

        sql = f"""
            SELECT *,
                   1 - ({vector_column} <=> '{vector_str}'::vector) AS similarity
            FROM {table}
            ORDER BY {vector_column} <=> '{vector_str}'::vector
            LIMIT {limit}
        """

        if db_session:
            from sqlalchemy import text
            result = await db_session.execute(text(sql))
            rows = result.mappings().all()
            return [dict(row) for row in rows]

        # If no session provided, return the SQL for manual execution
        return [{"sql": sql, "query_vector_dimensions": query_embedding.dimensions}]

    def get_stats(self) -> Dict[str, Any]:
        """Return embedding service statistics."""
        return {
            "model": self._model_id,
            "dimensions": self._dimensions,
            "normalize": self._normalize,
            "cache_size": len(self._cache),
            "cache_max": self._cache_max,
            "batch_size": BATCH_SIZE,
        }

    def clear_cache(self) -> int:
        """Clear the embedding cache. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_embedding_service: Optional[BedrockEmbeddingService] = None


def get_embedding_service() -> BedrockEmbeddingService:
    """Return the singleton BedrockEmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = BedrockEmbeddingService()
    return _embedding_service
