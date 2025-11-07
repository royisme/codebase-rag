"""
Knowledge Base Handler Functions for MCP Server v2

This module contains handlers for knowledge base operations:
- Query knowledge base
- Search similar nodes
- Add documents
- Add files
- Add directories
"""

from typing import Dict, Any
from loguru import logger


async def handle_query_knowledge(args: Dict, knowledge_service) -> Dict:
    """
    Query knowledge base using Neo4j GraphRAG.

    Args:
        args: Arguments containing question and mode
        knowledge_service: Neo4jKnowledgeService instance

    Returns:
        Query result with answer and source nodes
    """
    result = await knowledge_service.query(
        question=args["question"],
        mode=args.get("mode", "hybrid")
    )
    logger.info(f"Query: {args['question'][:50]}... (mode: {args.get('mode', 'hybrid')})")
    return result


async def handle_search_similar_nodes(args: Dict, knowledge_service) -> Dict:
    """
    Search for similar nodes using vector similarity.

    Args:
        args: Arguments containing query and top_k
        knowledge_service: Neo4jKnowledgeService instance

    Returns:
        Search results with similar nodes
    """
    result = await knowledge_service.search_similar_nodes(
        query=args["query"],
        top_k=args.get("top_k", 10)
    )
    logger.info(f"Search: {args['query'][:50]}... (top_k: {args.get('top_k', 10)})")
    return result


async def handle_add_document(args: Dict, knowledge_service, submit_document_processing_task) -> Dict:
    """
    Add document to knowledge base.

    Small documents (<10KB) are processed synchronously.
    Large documents (>=10KB) are queued for async processing.

    Args:
        args: Arguments containing content, title, metadata
        knowledge_service: Neo4jKnowledgeService instance
        submit_document_processing_task: Task submission function

    Returns:
        Result with success status and task_id if async
    """
    content = args["content"]
    size = len(content)

    # Small documents: synchronous
    if size < 10 * 1024:
        result = await knowledge_service.add_document(
            content=content,
            title=args.get("title"),
            metadata=args.get("metadata")
        )
    else:
        # Large documents: async task
        task_id = await submit_document_processing_task(
            content=content,
            title=args.get("title"),
            metadata=args.get("metadata")
        )
        result = {
            "success": True,
            "async": True,
            "task_id": task_id,
            "message": f"Large document queued (size: {size} bytes)"
        }

    logger.info(f"Add document: {args.get('title', 'Untitled')} ({size} bytes)")
    return result


async def handle_add_file(args: Dict, knowledge_service) -> Dict:
    """
    Add file to knowledge base.

    Args:
        args: Arguments containing file_path
        knowledge_service: Neo4jKnowledgeService instance

    Returns:
        Result with success status
    """
    result = await knowledge_service.add_file(args["file_path"])
    logger.info(f"Add file: {args['file_path']}")
    return result


async def handle_add_directory(args: Dict, submit_directory_processing_task) -> Dict:
    """
    Add directory to knowledge base (async processing).

    Args:
        args: Arguments containing directory_path and recursive flag
        submit_directory_processing_task: Task submission function

    Returns:
        Result with task_id for tracking
    """
    task_id = await submit_directory_processing_task(
        directory_path=args["directory_path"],
        recursive=args.get("recursive", True)
    )
    result = {
        "success": True,
        "async": True,
        "task_id": task_id,
        "message": f"Directory processing queued: {args['directory_path']}"
    }
    logger.info(f"Add directory: {args['directory_path']}")
    return result
