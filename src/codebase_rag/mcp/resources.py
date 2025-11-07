"""
Resource Handlers for MCP Server v2

This module contains handlers for MCP resources:
- List resources
- Read resource content
"""

import json
from typing import List
from mcp.types import Resource


def get_resource_list() -> List[Resource]:
    """
    Get list of available resources.

    Returns:
        List of Resource objects
    """
    return [
        Resource(
            uri="knowledge://config",
            name="System Configuration",
            mimeType="application/json",
            description="Current system configuration and model info"
        ),
        Resource(
            uri="knowledge://status",
            name="System Status",
            mimeType="application/json",
            description="Current system status and service health"
        ),
    ]


async def read_resource_content(
    uri: str,
    knowledge_service,
    task_queue,
    settings,
    get_current_model_info,
    service_initialized: bool
) -> str:
    """
    Read content of a specific resource.

    Args:
        uri: Resource URI
        knowledge_service: Neo4jKnowledgeService instance
        task_queue: Task queue instance
        settings: Settings instance
        get_current_model_info: Function to get model info
        service_initialized: Service initialization flag

    Returns:
        Resource content as JSON string

    Raises:
        ValueError: If resource URI is unknown
    """
    if uri == "knowledge://config":
        model_info = get_current_model_info()
        config = {
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "neo4j_uri": settings.neo4j_uri,
            "model_info": model_info
        }
        return json.dumps(config, indent=2)

    elif uri == "knowledge://status":
        stats = await knowledge_service.get_statistics()
        queue_stats = await task_queue.get_stats()

        status = {
            "knowledge_base": stats,
            "task_queue": queue_stats,
            "services_initialized": service_initialized
        }
        return json.dumps(status, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")
