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

v0.7 Automatic Extraction:
- Extract from conversation
- Extract from git commit
- Extract from code comments
- Suggest memory from query
- Batch extract from repository
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


# ============================================================================
# v0.7 Automatic Extraction Handlers
# ============================================================================

async def handle_extract_from_conversation(args: Dict, memory_extractor) -> Dict:
    """
    Extract memories from conversation using LLM analysis.

    Args:
        args: Arguments containing project_id, conversation, auto_save
        memory_extractor: Memory extractor instance

    Returns:
        Extracted memories with confidence scores
    """
    result = await memory_extractor.extract_from_conversation(
        project_id=args["project_id"],
        conversation=args["conversation"],
        auto_save=args.get("auto_save", False)
    )
    if result.get("success"):
        logger.info(f"Extracted {result.get('total_extracted', 0)} memories from conversation")
    return result


async def handle_extract_from_git_commit(args: Dict, memory_extractor) -> Dict:
    """
    Extract memories from git commit using LLM analysis.

    Args:
        args: Arguments containing project_id, commit_sha, commit_message, changed_files, auto_save
        memory_extractor: Memory extractor instance

    Returns:
        Extracted memories from commit
    """
    result = await memory_extractor.extract_from_git_commit(
        project_id=args["project_id"],
        commit_sha=args["commit_sha"],
        commit_message=args["commit_message"],
        changed_files=args["changed_files"],
        auto_save=args.get("auto_save", False)
    )
    if result.get("success"):
        logger.info(f"Extracted {result.get('auto_saved_count', 0)} memories from commit {args['commit_sha'][:8]}")
    return result


async def handle_extract_from_code_comments(args: Dict, memory_extractor) -> Dict:
    """
    Extract memories from code comments in source file.

    Args:
        args: Arguments containing project_id, file_path
        memory_extractor: Memory extractor instance

    Returns:
        Extracted memories from code comments
    """
    result = await memory_extractor.extract_from_code_comments(
        project_id=args["project_id"],
        file_path=args["file_path"]
    )
    if result.get("success"):
        logger.info(f"Extracted {result.get('total_extracted', 0)} memories from {args['file_path']}")
    return result


async def handle_suggest_memory_from_query(args: Dict, memory_extractor) -> Dict:
    """
    Suggest creating memory based on knowledge query and answer.

    Args:
        args: Arguments containing project_id, query, answer
        memory_extractor: Memory extractor instance

    Returns:
        Memory suggestion with confidence (not auto-saved)
    """
    result = await memory_extractor.suggest_memory_from_query(
        project_id=args["project_id"],
        query=args["query"],
        answer=args["answer"]
    )
    if result.get("success") and result.get("should_save"):
        logger.info(f"Memory suggested from query: {result.get('suggested_memory', {}).get('title', 'N/A')}")
    return result


async def handle_batch_extract_from_repository(args: Dict, memory_extractor) -> Dict:
    """
    Batch extract memories from entire repository.

    Args:
        args: Arguments containing project_id, repo_path, max_commits, file_patterns
        memory_extractor: Memory extractor instance

    Returns:
        Summary of extracted memories by source
    """
    result = await memory_extractor.batch_extract_from_repository(
        project_id=args["project_id"],
        repo_path=args["repo_path"],
        max_commits=args.get("max_commits", 50),
        file_patterns=args.get("file_patterns")
    )
    if result.get("success"):
        logger.info(f"Batch extraction: {result.get('total_extracted', 0)} memories from {args['repo_path']}")
    return result
