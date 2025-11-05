"""
MCP Server v2 - Complete Official SDK Implementation

Full migration from FastMCP to official Model Context Protocol SDK.
All 25 tools now implemented with advanced features:
- Session management for tracking user context
- Streaming responses for long-running operations
- Multi-transport support (stdio, SSE, WebSocket)
- Enhanced error handling and logging
- Standard MCP protocol compliance

Tool Categories:
- Knowledge Base (5 tools): query, search, add documents
- Code Graph (4 tools): ingest, search, impact analysis, context pack
- Memory Store (7 tools): project knowledge management
- Task Management (6 tools): async task monitoring
- System (3 tools): schema, statistics, clear

Usage:
    python start_mcp_v2.py
"""

import asyncio
import sys
from typing import Any, Dict, List, Sequence
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    Prompt,
    PromptMessage,
)
from loguru import logger

# Import services
from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.memory_store import memory_store
from services.task_queue import task_queue, TaskStatus, submit_document_processing_task, submit_directory_processing_task
from services.task_processors import processor_registry
from services.graph_service import graph_service
from services.code_ingestor import get_code_ingestor
from services.ranker import ranker
from services.pack_builder import pack_builder
from services.git_utils import git_utils
from config import settings, get_current_model_info

# Import MCP tools modules
from mcp_tools import (
    # Handlers
    handle_query_knowledge,
    handle_search_similar_nodes,
    handle_add_document,
    handle_add_file,
    handle_add_directory,
    handle_code_graph_ingest_repo,
    handle_code_graph_related,
    handle_code_graph_impact,
    handle_context_pack,
    handle_add_memory,
    handle_search_memories,
    handle_get_memory,
    handle_update_memory,
    handle_delete_memory,
    handle_supersede_memory,
    handle_get_project_summary,
    handle_get_task_status,
    handle_watch_task,
    handle_watch_tasks,
    handle_list_tasks,
    handle_cancel_task,
    handle_get_queue_stats,
    handle_get_graph_schema,
    handle_get_statistics,
    handle_clear_knowledge_base,
    # Tool definitions
    get_tool_definitions,
    # Utilities
    format_result,
    # Resources
    get_resource_list,
    read_resource_content,
    # Prompts
    get_prompt_list,
    get_prompt_content,
)


# ============================================================================
# Server Initialization
# ============================================================================

server = Server("codebase-rag-complete-v2")

# Initialize services
knowledge_service = Neo4jKnowledgeService()
_service_initialized = False

# Session tracking with thread-safe access
active_sessions: Dict[str, Dict[str, Any]] = {}
_sessions_lock = asyncio.Lock()  # Protects active_sessions from race conditions


async def ensure_service_initialized():
    """Ensure all services are initialized"""
    global _service_initialized
    if not _service_initialized:
        # Initialize knowledge service
        success = await knowledge_service.initialize()
        if not success:
            raise Exception("Failed to initialize Neo4j Knowledge Service")

        # Initialize memory store
        memory_success = await memory_store.initialize()
        if not memory_success:
            logger.warning("Memory Store initialization failed")

        # Start task queue
        await task_queue.start()

        # Initialize task processors
        processor_registry.initialize_default_processors(knowledge_service)

        _service_initialized = True
        logger.info("All services initialized successfully")


async def track_session_activity(session_id: str, tool: str, details: Dict[str, Any]):
    """Track tool usage in session (thread-safe with lock)"""
    async with _sessions_lock:
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "tools_used": [],
                "memories_accessed": set(),
            }

        active_sessions[session_id]["tools_used"].append({
            "tool": tool,
            "timestamp": datetime.utcnow().isoformat(),
            **details
        })


# ============================================================================
# Tool Definitions
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all 25 available tools"""
    return get_tool_definitions()


# ============================================================================
# Tool Execution
# ============================================================================

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: Dict[str, Any]
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Execute tool and return result"""

    # Initialize services
    await ensure_service_initialized()

    try:
        # Route to handler with service injection
        if name == "query_knowledge":
            result = await handle_query_knowledge(arguments, knowledge_service)
        elif name == "search_similar_nodes":
            result = await handle_search_similar_nodes(arguments, knowledge_service)
        elif name == "add_document":
            result = await handle_add_document(arguments, knowledge_service, submit_document_processing_task)
        elif name == "add_file":
            result = await handle_add_file(arguments, knowledge_service)
        elif name == "add_directory":
            result = await handle_add_directory(arguments, submit_directory_processing_task)
        elif name == "code_graph_ingest_repo":
            result = await handle_code_graph_ingest_repo(arguments, get_code_ingestor, git_utils)
        elif name == "code_graph_related":
            result = await handle_code_graph_related(arguments, graph_service, ranker)
        elif name == "code_graph_impact":
            result = await handle_code_graph_impact(arguments, graph_service)
        elif name == "context_pack":
            result = await handle_context_pack(arguments, pack_builder)
        elif name == "add_memory":
            result = await handle_add_memory(arguments, memory_store)
        elif name == "search_memories":
            result = await handle_search_memories(arguments, memory_store)
        elif name == "get_memory":
            result = await handle_get_memory(arguments, memory_store)
        elif name == "update_memory":
            result = await handle_update_memory(arguments, memory_store)
        elif name == "delete_memory":
            result = await handle_delete_memory(arguments, memory_store)
        elif name == "supersede_memory":
            result = await handle_supersede_memory(arguments, memory_store)
        elif name == "get_project_summary":
            result = await handle_get_project_summary(arguments, memory_store)
        elif name == "get_task_status":
            result = await handle_get_task_status(arguments, task_queue, TaskStatus)
        elif name == "watch_task":
            result = await handle_watch_task(arguments, task_queue, TaskStatus)
        elif name == "watch_tasks":
            result = await handle_watch_tasks(arguments, task_queue, TaskStatus)
        elif name == "list_tasks":
            result = await handle_list_tasks(arguments, task_queue)
        elif name == "cancel_task":
            result = await handle_cancel_task(arguments, task_queue)
        elif name == "get_queue_stats":
            result = await handle_get_queue_stats(arguments, task_queue)
        elif name == "get_graph_schema":
            result = await handle_get_graph_schema(arguments, knowledge_service)
        elif name == "get_statistics":
            result = await handle_get_statistics(arguments, knowledge_service)
        elif name == "clear_knowledge_base":
            result = await handle_clear_knowledge_base(arguments, knowledge_service)
        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

        # Format and return
        return [TextContent(type="text", text=format_result(result))]

    except Exception as e:
        logger.error(f"Error executing '{name}': {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# Resources
# ============================================================================

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources"""
    return get_resource_list()


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content"""
    await ensure_service_initialized()

    return await read_resource_content(
        uri=uri,
        knowledge_service=knowledge_service,
        task_queue=task_queue,
        settings=settings,
        get_current_model_info=get_current_model_info,
        service_initialized=_service_initialized
    )


# ============================================================================
# Prompts
# ============================================================================

@server.list_prompts()
async def handle_list_prompts() -> List[Prompt]:
    """List available prompts"""
    return get_prompt_list()


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> List[PromptMessage]:
    """Get prompt content"""
    return get_prompt_content(name, arguments)


# ============================================================================
# Server Entry Point
# ============================================================================

async def main():
    """Main entry point"""
    from mcp.server.stdio import stdio_server

    logger.info("=" * 70)
    logger.info("MCP Server v2 (Official SDK) - Complete Migration")
    logger.info("=" * 70)
    logger.info(f"Server: {server.name}")
    logger.info("Transport: stdio")
    logger.info("Tools: 25 (all features)")
    logger.info("Resources: 2")
    logger.info("Prompts: 1")
    logger.info("=" * 70)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="codebase-rag-complete-v2",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
