"""
Memory Store Handler Functions for MCP Server v2

This module contains handlers for memory management operations:
- Add memory
- Search memories
- Get memory
- Update memory
- Delete memory
- Supersede memory
- Get project summary
"""

from typing import Dict, Any
from loguru import logger


async def handle_add_memory(args: Dict, memory_store) -> Dict:
    """
    Add new memory to project knowledge base.

    Args:
        args: Arguments containing project_id, memory_type, title, content, etc.
        memory_store: Memory store instance

    Returns:
        Result with memory_id
    """
    result = await memory_store.add_memory(
        project_id=args["project_id"],
        memory_type=args["memory_type"],
        title=args["title"],
        content=args["content"],
        reason=args.get("reason"),
        tags=args.get("tags"),
        importance=args.get("importance", 0.5),
        related_refs=args.get("related_refs")
    )
    if result.get("success"):
        logger.info(f"Memory added: {result['memory_id']}")
    return result


async def handle_search_memories(args: Dict, memory_store) -> Dict:
    """
    Search project memories with filters.

    Args:
        args: Arguments containing project_id, query, memory_type, tags, min_importance, limit
        memory_store: Memory store instance

    Returns:
        Search results with matching memories
    """
    result = await memory_store.search_memories(
        project_id=args["project_id"],
        query=args.get("query"),
        memory_type=args.get("memory_type"),
        tags=args.get("tags"),
        min_importance=args.get("min_importance", 0.0),
        limit=args.get("limit", 20)
    )
    if result.get("success"):
        logger.info(f"Memory search: found {result.get('total_count', 0)} results")
    return result


async def handle_get_memory(args: Dict, memory_store) -> Dict:
    """
    Get specific memory by ID.

    Args:
        args: Arguments containing memory_id
        memory_store: Memory store instance

    Returns:
        Memory details
    """
    result = await memory_store.get_memory(args["memory_id"])
    if result.get("success"):
        logger.info(f"Retrieved memory: {args['memory_id']}")
    return result


async def handle_update_memory(args: Dict, memory_store) -> Dict:
    """
    Update existing memory (partial update supported).

    Args:
        args: Arguments containing memory_id and fields to update
        memory_store: Memory store instance

    Returns:
        Update result
    """
    result = await memory_store.update_memory(
        memory_id=args["memory_id"],
        title=args.get("title"),
        content=args.get("content"),
        reason=args.get("reason"),
        tags=args.get("tags"),
        importance=args.get("importance")
    )
    if result.get("success"):
        logger.info(f"Memory updated: {args['memory_id']}")
    return result


async def handle_delete_memory(args: Dict, memory_store) -> Dict:
    """
    Delete memory (soft delete - data retained).

    Args:
        args: Arguments containing memory_id
        memory_store: Memory store instance

    Returns:
        Deletion result
    """
    result = await memory_store.delete_memory(args["memory_id"])
    if result.get("success"):
        logger.info(f"Memory deleted: {args['memory_id']}")
    return result


async def handle_supersede_memory(args: Dict, memory_store) -> Dict:
    """
    Create new memory that supersedes old one (preserves history).

    Args:
        args: Arguments containing old_memory_id and new memory data
        memory_store: Memory store instance

    Returns:
        Result with new_memory_id
    """
    result = await memory_store.supersede_memory(
        old_memory_id=args["old_memory_id"],
        new_memory_data={
            "memory_type": args["new_memory_type"],
            "title": args["new_title"],
            "content": args["new_content"],
            "reason": args.get("new_reason"),
            "tags": args.get("new_tags"),
            "importance": args.get("new_importance", 0.5)
        }
    )
    if result.get("success"):
        logger.info(f"Memory superseded: {args['old_memory_id']} -> {result.get('new_memory_id')}")
    return result


async def handle_get_project_summary(args: Dict, memory_store) -> Dict:
    """
    Get summary of all memories for a project.

    Args:
        args: Arguments containing project_id
        memory_store: Memory store instance

    Returns:
        Project summary organized by memory type
    """
    result = await memory_store.get_project_summary(args["project_id"])
    if result.get("success"):
        summary = result.get("summary", {})
        logger.info(f"Project summary: {summary.get('total_memories', 0)} memories")
    return result
