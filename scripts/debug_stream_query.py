"""Quick script to inspect GraphRAG streaming events."""

from __future__ import annotations

import asyncio
import json

from services.graph_rag_service import GraphRAGService


async def main() -> None:
    service = GraphRAGService()
    async for event in service.stream_query(
        "测试知识图谱如何构建?",
        timeout_seconds=30,
        include_evidence=True,
        max_results=5,
    ):
        print(json.dumps(event, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
