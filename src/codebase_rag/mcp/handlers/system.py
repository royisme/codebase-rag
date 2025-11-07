"""
System Handler Functions for MCP Server v2

This module contains handlers for system operations:
- Get graph schema
- Get statistics
- Clear knowledge base
"""

from typing import Dict, Any
from loguru import logger


async def handle_get_graph_schema(args: Dict, knowledge_service) -> Dict:
    """
    Get Neo4j graph schema.

    Returns node labels, relationship types, and schema statistics.

    Args:
        args: Arguments (none required)
        knowledge_service: Neo4jKnowledgeService instance

    Returns:
        Graph schema information
    """
    result = await knowledge_service.get_graph_schema()
    logger.info("Retrieved graph schema")
    return result


async def handle_get_statistics(args: Dict, knowledge_service) -> Dict:
    """
    Get knowledge base statistics.

    Returns node count, document count, and other statistics.

    Args:
        args: Arguments (none required)
        knowledge_service: Neo4jKnowledgeService instance

    Returns:
        Knowledge base statistics
    """
    result = await knowledge_service.get_statistics()
    logger.info("Retrieved statistics")
    return result


async def handle_clear_knowledge_base(args: Dict, knowledge_service) -> Dict:
    """
    Clear all data from knowledge base.

    DANGEROUS operation - requires confirmation='yes'.

    Args:
        args: Arguments containing confirmation
        knowledge_service: Neo4jKnowledgeService instance

    Returns:
        Clearing result
    """
    confirmation = args.get("confirmation", "")

    if confirmation != "yes":
        return {
            "success": False,
            "error": "Confirmation required. Set confirmation='yes' to proceed."
        }

    result = await knowledge_service.clear_knowledge_base()
    logger.warning("Knowledge base cleared!")
    return result
