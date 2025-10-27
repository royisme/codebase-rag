"""Simple in-memory cache for GraphRAG query responses."""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Optional

from loguru import logger

from config import settings
from schemas import GraphRAGQueryResponse


class GraphQueryCache:
    """Store recent GraphRAG responses for lightweight multi-turn support."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._cache: dict[str, tuple[dt.datetime, dict]] = {}
        self._lock = asyncio.Lock()

    @property
    def ttl(self) -> int:
        return self._ttl

    def update_ttl(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds

    async def get(self, query_id: str) -> Optional[GraphRAGQueryResponse]:
        async with self._lock:
            self._purge_expired_locked()
            item = self._cache.get(query_id)
            if not item:
                return None

            _, payload = item
            try:
                return GraphRAGQueryResponse.model_validate(payload)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to deserialize cached GraphRAG response: {}", exc)
                self._cache.pop(query_id, None)
                return None

    async def set(self, query_id: str, response: GraphRAGQueryResponse) -> None:
        async with self._lock:
            self._purge_expired_locked()
            self._cache[query_id] = (
                dt.datetime.now(dt.timezone.utc),
                response.model_dump(mode="json"),
            )

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    def _purge_expired_locked(self) -> None:
        if not self._cache:
            return

        now = dt.datetime.now(dt.timezone.utc)
        ttl_delta = dt.timedelta(seconds=self._ttl)
        expired = [key for key, (ts, _) in self._cache.items() if now - ts > ttl_delta]
        for key in expired:
            self._cache.pop(key, None)


graph_query_cache = GraphQueryCache(settings.graphrag_query_cache_ttl_seconds)


async def refresh_cache_settings() -> None:
    """Synchronise cache TTL with settings (useful in tests)."""

    graph_query_cache.update_ttl(settings.graphrag_query_cache_ttl_seconds)
