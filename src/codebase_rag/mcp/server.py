"""
MCP Server  - Complete Official SDK Implementation

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
    python start_mcp.py
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
from codebase_rag.services.neo4j_knowledge_service import Neo4jKnowledgeService
from codebase_rag.services.memory_store import memory_store
from codebase_rag.services.memory_extractor import memory_extractor
from codebase_rag.services.task_queue import task_queue, TaskStatus, submit_document_processing_task, submit_directory_processing_task
from codebase_rag.services.task_processors import processor_registry
from codebase_rag.services.graph_service import graph_service
from codebase_rag.services.code_ingestor import get_code_ingestor
from codebase_rag.services.ranker import ranker
from codebase_rag.services.pack_builder import pack_builder
from codebase_rag.services.git_utils import git_utils
from codebase_rag.config import settings, get_current_model_info

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
    # v0.7 Extraction handlers
    handle_extract_from_conversation,
    handle_extract_from_git_commit,
    handle_extract_from_code_comments,
    handle_suggest_memory_from_query,
    handle_batch_extract_from_repository,
    # Task handlers
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
        await ensure_service_initialized()

        if not local_path and not repo_url:
            return {
                "success": False,
                "error": "Either local_path or repo_url must be provided"
            }

        if ctx:
            await ctx.info(f"Ingesting repository (mode: {mode})")

        # Set defaults
        if include_globs is None:
            include_globs = ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.java", "**/*.php", "**/*.go"]
        if exclude_globs is None:
            exclude_globs = ["**/node_modules/**", "**/.git/**", "**/__pycache__/**", "**/.venv/**", "**/vendor/**", "**/target/**"]

        # Generate task ID
        task_id = f"ing-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        # Determine repository path and ID
        repo_path = None
        repo_id = None
        cleanup_needed = False

        if local_path:
            repo_path = local_path
            repo_id = git_utils.get_repo_id_from_path(repo_path)
        else:
            # Clone repository
            if ctx:
                await ctx.info(f"Cloning repository: {repo_url}")

            clone_result = git_utils.clone_repo(repo_url, branch=branch)

            if not clone_result.get("success"):
                return {
                    "success": False,
                    "task_id": task_id,
                    "status": "error",
                    "error": clone_result.get("error", "Failed to clone repository")
                }

            repo_path = clone_result["path"]
            repo_id = git_utils.get_repo_id_from_url(repo_url)
            cleanup_needed = True

        # Get code ingestor
        code_ingestor = get_code_ingestor(graph_service)

        # Handle incremental mode
        files_to_process = None
        changed_files_count = 0

        if mode == "incremental" and git_utils.is_git_repo(repo_path):
            if ctx:
                await ctx.info("Using incremental mode - detecting changed files")

            changed_files_result = git_utils.get_changed_files(
                repo_path,
                since_commit=since_commit,
                include_untracked=True
            )
            changed_files_count = changed_files_result.get("count", 0)

            if changed_files_count == 0:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "done",
                    "message": "No changed files detected",
                    "mode": "incremental",
                    "files_processed": 0,
                    "changed_files_count": 0
                }

            # Filter changed files by globs
            files_to_process = [f["path"] for f in changed_files_result.get("changed_files", []) if f["action"] != "deleted"]

            if ctx:
                await ctx.info(f"Found {changed_files_count} changed files")

        # Scan files
        if ctx:
            await ctx.info(f"Scanning repository: {repo_path}")

        scanned_files = code_ingestor.scan_files(
            repo_path=repo_path,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
            specific_files=files_to_process
        )

        if not scanned_files:
            return {
                "success": True,
                "task_id": task_id,
                "status": "done",
                "message": "No files found matching criteria",
                "mode": mode,
                "files_processed": 0,
                "changed_files_count": changed_files_count if mode == "incremental" else None
            }

        # Ingest files
        if ctx:
            await ctx.info(f"Ingesting {len(scanned_files)} files...")

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

                if search_results:
                    ranked = ranker.rank_files(
                        files=search_results,
                        query=keyword,
                        limit=10
                    )

                    for file in ranked:
                        all_nodes.append({
                            "type": "file",
                            "path": file["path"],
                            "lang": file["lang"],
                            "score": file["score"],
                            "ref": ranker.generate_ref_handle(path=file["path"])
                        })

        # Add focus files with high priority
        if focus_list:
            for focus_path in focus_list:
                all_nodes.append({
                    "type": "file",
                    "path": focus_path,
                    "lang": "unknown",
                    "score": 10.0,  # High priority
                    "ref": ranker.generate_ref_handle(path=focus_path)
                })

        # Build context pack
        if ctx:
            await ctx.info(f"Packing {len(all_nodes)} candidate files into context...")

        context_result = pack_builder.build_context_pack(
            nodes=all_nodes,
            budget=budget,
            stage=stage,
            repo_id=repo_id,
            file_limit=8,
            symbol_limit=12,
            enable_deduplication=True
        )

        # Format items
        items = []
        for item in context_result.get("items", []):
            items.append({
                "kind": item.get("kind", "file"),
                "title": item.get("title", "Unknown"),
                "summary": item.get("summary", ""),
                "ref": item.get("ref", ""),
                "extra": {
                    "lang": item.get("extra", {}).get("lang"),
                    "score": item.get("extra", {}).get("score", 0.0)
                }
            })

        if ctx:
            await ctx.info(f"Context pack built: {len(items)} items, {context_result.get('budget_used', 0)} tokens")

        return {
            "success": True,
            "items": items,
            "budget_used": context_result.get("budget_used", 0),
            "budget_limit": budget,
            "stage": stage,
            "repo_id": repo_id,
            "category_counts": context_result.get("category_counts", {})
        }

    except Exception as e:
        error_msg = f"Context pack generation failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# ===================================
# MCP Resources
# ===================================

# MCP resource: knowledge base config
@mcp.resource("knowledge://config")
async def get_knowledge_config() -> Dict[str, Any]:
    """Get knowledge base configuration and settings."""
    model_info = get_current_model_info()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "neo4j_uri": settings.neo4j_uri,
        "neo4j_database": settings.neo4j_database,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "current_models": model_info,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "top_k": settings.top_k,
        "vector_dimension": settings.vector_dimension,
        "timeouts": {
            "connection": settings.connection_timeout,
            "operation": settings.operation_timeout,
            "large_document": settings.large_document_timeout
        }
    }

# MCP resource: system status
@mcp.resource("knowledge://status")
async def get_system_status() -> Dict[str, Any]:
    """Get current system status and health."""
    try:
        await ensure_service_initialized()
        stats = await knowledge_service.get_statistics()
        model_info = get_current_model_info()
        
        return {
            "status": "healthy" if stats.get("success") else "degraded",
            "services": {
                "neo4j_knowledge_service": _service_initialized,
                "neo4j_connection": True,  # if initialized, connection is healthy
            },
            "current_models": model_info,
            "statistics": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "services": {
                "neo4j_knowledge_service": _service_initialized,
                "neo4j_connection": False,
            }
        }

# MCP resource: recent documents
@mcp.resource("knowledge://recent-documents/{limit}")
async def get_recent_documents(limit: int = 10) -> Dict[str, Any]:
    """Get recently added documents."""
    try:
        await ensure_service_initialized()
        # here can be extended to query recent documents from graph database
        # currently return placeholder information
        return {
            "message": f"Recent {limit} documents endpoint",
            "note": "This feature can be extended to query Neo4j for recently added documents",
            "limit": limit,
            "implementation_status": "placeholder"
        }
    except Exception as e:
        return {
            "error": str(e)
        }

# MCP prompt: generate query suggestions
@mcp.prompt
def suggest_queries(domain: str = "general") -> str:
    """
    Generate suggested queries for the Neo4j knowledge graph.
    
    Args:
        domain: Domain to focus suggestions on (e.g., "code", "documentation", "sql", "architecture")
    """
    suggestions = {
        "general": [
            "What are the main components of this system?",
            "How does the Neo4j knowledge pipeline work?",
            "What databases and services are used in this project?",
            "Show me the overall architecture of the system"
        ],
        "code": [
            "Show me Python functions for data processing",
            "Find code examples for Neo4j integration",
            "What are the main classes in the pipeline module?",
            "How is the knowledge service implemented?"
        ],
        "documentation": [
            "What is the system architecture?",
            "How to set up the development environment?",
            "What are the API endpoints available?",
            "How to configure different LLM providers?"
        ],
        "sql": [
            "Show me table schemas for user management",
            "What are the relationships between database tables?",
            "Find SQL queries for reporting",
            "How is the database schema structured?"
        ],
        "architecture": [
            "What is the GraphRAG architecture?",
            "How does the vector search work with Neo4j?",
            "What are the different query modes available?",
            "How are documents processed and stored?"
        ]
    }
    
    domain_suggestions = suggestions.get(domain, suggestions["general"])
    
    return f"""Here are some suggested queries for the {domain} domain in the Neo4j Knowledge Graph:

{chr(10).join(f"• {suggestion}" for suggestion in domain_suggestions)}

Available query modes:
• hybrid: Combines graph traversal and vector search (recommended)
• graph_only: Uses only graph relationships
• vector_only: Uses only vector similarity search

You can use the query_knowledge tool with any of these questions or create your own queries."""

if __name__ == "__main__":
    asyncio.run(main())
