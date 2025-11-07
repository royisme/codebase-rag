"""Declarative tool definitions exposed to the workflow agent."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List

from llama_index.core.tools import AsyncFunctionTool

from codebase_rag.services.knowledge.neo4j_knowledge_service import (
    neo4j_knowledge_service,
)
from codebase_rag.services.memory import memory_extractor, memory_store

_knowledge_lock = asyncio.Lock()
_memory_lock = asyncio.Lock()


async def _ensure_knowledge_ready() -> None:
    """Initialize the Neo4j knowledge service if required."""

    if not neo4j_knowledge_service._initialized:  # type: ignore[attr-defined]
        async with _knowledge_lock:
            if not neo4j_knowledge_service._initialized:  # type: ignore[attr-defined]
                await neo4j_knowledge_service.initialize()


async def _ensure_memory_ready() -> None:
    """Initialize the memory store when first accessed."""

    if not memory_store._initialized:  # type: ignore[attr-defined]
        async with _memory_lock:
            if not memory_store._initialized:  # type: ignore[attr-defined]
                await memory_store.initialize()


async def _agent_query_knowledge(question: str, mode: str = "hybrid") -> Dict[str, Any]:
    """Run a knowledge graph query through the Neo4j service."""

    await _ensure_knowledge_ready()
    return await neo4j_knowledge_service.query(question=question, mode=mode)


async def _agent_similar_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Retrieve nodes similar to the provided query text."""

    await _ensure_knowledge_ready()
    return await neo4j_knowledge_service.search_similar_nodes(query=query, top_k=top_k)


async def _agent_graph_summary() -> Dict[str, Any]:
    """Expose a lightweight schema/statistics view of the knowledge graph."""

    await _ensure_knowledge_ready()
    schema = await neo4j_knowledge_service.get_graph_schema()
    stats = await neo4j_knowledge_service.get_statistics()
    return {"schema": schema, "statistics": stats}


async def _agent_extract_memories(
    project_id: str,
    conversation: List[Dict[str, str]],
    auto_save: bool = False,
) -> Dict[str, Any]:
    """Use the MemoryExtractor to analyse a conversation."""

    await _ensure_memory_ready()
    return await memory_extractor.extract_from_conversation(
        project_id=project_id,
        conversation=conversation,
        auto_save=auto_save,
    )


async def _agent_save_memory(
    project_id: str,
    memory_type: str,
    title: str,
    content: str,
    reason: str | None = None,
    tags: Iterable[str] | None = None,
    importance: float = 0.5,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Persist a memory entry directly through the MemoryStore."""

    await _ensure_memory_ready()
    return await memory_store.add_memory(
        project_id=project_id,
        memory_type=memory_type,  # type: ignore[arg-type]
        title=title,
        content=content,
        reason=reason,
        tags=list(tags) if tags is not None else None,
        importance=importance,
        metadata=metadata,
    )


KNOWLEDGE_TOOLS = [
    AsyncFunctionTool.from_defaults(
        fn=_agent_query_knowledge,
        name="query_knowledge_graph",
        description=(
            "Query the Neo4j knowledge graph using hybrid retrieval. Use this when "
            "you need long-form answers backed by stored documents."
        ),
    ),
    AsyncFunctionTool.from_defaults(
        fn=_agent_similar_search,
        name="search_similar_nodes",
        description=(
            "Retrieve top related nodes using semantic similarity in the knowledge graph."
        ),
    ),
    AsyncFunctionTool.from_defaults(
        fn=_agent_graph_summary,
        name="describe_graph_state",
        description=(
            "Get schema and health information about the Neo4j knowledge graph "
            "to support planning or diagnostics."
        ),
    ),
]

MEMORY_TOOLS = [
    AsyncFunctionTool.from_defaults(
        fn=_agent_extract_memories,
        name="extract_conversation_memories",
        description=(
            "Analyse the current conversation and suggest project memories. "
            "Set auto_save to true to persist high-confidence results automatically."
        ),
    ),
    AsyncFunctionTool.from_defaults(
        fn=_agent_save_memory,
        name="save_project_memory",
        description=(
            "Persist an explicit memory entry for the current project into the "
            "long-term Neo4j store."
        ),
    ),
]

AGENT_TOOLS = [*KNOWLEDGE_TOOLS, *MEMORY_TOOLS]

