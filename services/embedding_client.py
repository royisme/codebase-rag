"""Unified embedding client leveraging configured LlamaIndex providers."""

from __future__ import annotations

import asyncio
import hashlib
import math
from typing import Iterable, List, Optional

from loguru import logger
from llama_index.core import Settings

from services.neo4j_knowledge_service import neo4j_knowledge_service


class EmbeddingClient:
    """Adapter around LlamaIndex embedding models with graceful fallback."""

    def __init__(self, *, dimension: int = 32) -> None:
        self.dimension = dimension

    async def _ensure_model(self):
        if not neo4j_knowledge_service._initialized:  # noqa: SLF001
            try:
                await neo4j_knowledge_service.initialize()
            except Exception as exc:  # pragma: no cover - initialization failure
                logger.warning("Failed to initialize knowledge service for embeddings: {}", exc)
                return None
        return Settings.embed_model

    async def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        texts = list(texts)
        if not texts:
            return []

        model = await self._ensure_model()
        if model is None:
            return [self._fallback_embedding(text) for text in texts]

        try:
            return await asyncio.to_thread(model.get_text_embedding_batch, texts)
        except Exception as exc:  # pragma: no cover - provider failure
            logger.error("Embedding provider failed, falling back to deterministic vectors: {}", exc)
            return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector: List[float] = []
        for index in range(self.dimension):
            start = (index * 2) % len(digest)
            value = int.from_bytes(digest[start : start + 2], "big", signed=False)
            vector.append((value % 2000) / 1000.0 - 1.0)
        return vector

    @staticmethod
    def average_magnitude(vectors: List[List[float]]) -> float:
        if not vectors:
            return 0.0
        magnitudes = [math.sqrt(sum(component ** 2 for component in vec)) for vec in vectors]
        return sum(magnitudes) / len(magnitudes)


__all__ = ["EmbeddingClient"]
