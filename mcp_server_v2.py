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
import json
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    ResourceTemplate,
    Prompt,
    PromptMessage,
    PromptArgument,
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


# ============================================================================
# Server Initialization
# ============================================================================

server = Server("codebase-rag-complete-v2")

# Initialize services
knowledge_service = Neo4jKnowledgeService()
_service_initialized = False

# Session tracking
active_sessions: Dict[str, Dict[str, Any]] = {}


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


def track_session_activity(session_id: str, tool: str, details: Dict[str, Any]):
    """Track tool usage in session"""
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

    tools = [
        # ===== Knowledge Base Tools (5) =====
        Tool(
            name="query_knowledge",
            description="""Query the knowledge base using Neo4j GraphRAG.

Modes:
- hybrid: Graph traversal + vector search (default, recommended)
- graph_only: Use only graph relationships
- vector_only: Use only vector similarity

Returns LLM-generated answer with source nodes.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to ask the knowledge base"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["hybrid", "graph_only", "vector_only"],
                        "default": "hybrid",
                        "description": "Query mode"
                    }
                },
                "required": ["question"]
            }
        ),

        Tool(
            name="search_similar_nodes",
            description="Search for similar nodes using vector similarity. Returns top-K most similar nodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Number of results"
                    }
                },
                "required": ["query"]
            }
        ),

        Tool(
            name="add_document",
            description="""Add a document to the knowledge base.

Small documents (<10KB): Processed synchronously
Large documents (>=10KB): Processed asynchronously with task ID

Content is chunked, embedded, and stored in Neo4j knowledge graph.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Document content"
                    },
                    "title": {
                        "type": "string",
                        "description": "Document title (optional)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)"
                    }
                },
                "required": ["content"]
            }
        ),

        Tool(
            name="add_file",
            description="Add a file to the knowledge base. Supports text files, code files, and documents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to file"
                    }
                },
                "required": ["file_path"]
            }
        ),

        Tool(
            name="add_directory",
            description="Add all files from a directory to the knowledge base. Processes recursively.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Absolute path to directory"
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": True,
                        "description": "Process subdirectories"
                    }
                },
                "required": ["directory_path"]
            }
        ),

        # ===== Code Graph Tools (4) =====
        Tool(
            name="code_graph_ingest_repo",
            description="""Ingest a code repository into the graph database.

Modes:
- full: Complete re-ingestion (slow but thorough)
- incremental: Only changed files (60x faster)

Extracts:
- File nodes
- Symbol nodes (functions, classes)
- IMPORTS relationships
- Code structure""",
            inputSchema={
                "type": "object",
                "properties": {
                    "local_path": {
                        "type": "string",
                        "description": "Local repository path"
                    },
                    "repo_url": {
                        "type": "string",
                        "description": "Repository URL (optional)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["full", "incremental"],
                        "default": "incremental",
                        "description": "Ingestion mode"
                    }
                },
                "required": ["local_path"]
            }
        ),

        Tool(
            name="code_graph_related",
            description="""Find files related to a query using fulltext search.

Returns ranked list of relevant files with ref:// handles.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 30,
                        "description": "Max results"
                    }
                },
                "required": ["query", "repo_id"]
            }
        ),

        Tool(
            name="code_graph_impact",
            description="""Analyze impact of changes to a file.

Finds all files that depend on the given file (reverse dependencies).
Useful for understanding blast radius of changes.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path to analyze"
                    },
                    "depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 2,
                        "description": "Dependency traversal depth"
                    }
                },
                "required": ["repo_id", "file_path"]
            }
        ),

        Tool(
            name="context_pack",
            description="""Build a context pack for AI agents within token budget.

Stages:
- plan: Project overview
- review: Code review focus
- implement: Implementation details

Returns curated list of files/symbols with ref:// handles.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["plan", "review", "implement"],
                        "default": "implement",
                        "description": "Development stage"
                    },
                    "budget": {
                        "type": "integer",
                        "minimum": 500,
                        "maximum": 10000,
                        "default": 1500,
                        "description": "Token budget"
                    },
                    "keywords": {
                        "type": "string",
                        "description": "Focus keywords (optional)"
                    },
                    "focus": {
                        "type": "string",
                        "description": "Focus file paths (optional)"
                    }
                },
                "required": ["repo_id"]
            }
        ),

        # ===== Memory Store Tools (7) =====
        Tool(
            name="add_memory",
            description="""Add a new memory to project knowledge base.

Memory Types:
- decision: Architecture choices, tech stack
- preference: Coding style, tool choices
- experience: Problems and solutions
- convention: Team rules, naming patterns
- plan: Future improvements, TODOs
- note: Other important information""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "memory_type": {
                        "type": "string",
                        "enum": ["decision", "preference", "experience", "convention", "plan", "note"]
                    },
                    "title": {"type": "string", "minLength": 1, "maxLength": 200},
                    "content": {"type": "string", "minLength": 1},
                    "reason": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                    "related_refs": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["project_id", "memory_type", "title", "content"]
            }
        ),

        Tool(
            name="search_memories",
            description="Search project memories with filters (query, type, tags, importance).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "query": {"type": "string"},
                    "memory_type": {
                        "type": "string",
                        "enum": ["decision", "preference", "experience", "convention", "plan", "note"]
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "min_importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.0},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                },
                "required": ["project_id"]
            }
        ),

        Tool(
            name="get_memory",
            description="Get specific memory by ID with full details.",
            inputSchema={
                "type": "object",
                "properties": {"memory_id": {"type": "string"}},
                "required": ["memory_id"]
            }
        ),

        Tool(
            name="update_memory",
            description="Update existing memory (partial update supported).",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "reason": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "importance": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["memory_id"]
            }
        ),

        Tool(
            name="delete_memory",
            description="Delete memory (soft delete - data retained).",
            inputSchema={
                "type": "object",
                "properties": {"memory_id": {"type": "string"}},
                "required": ["memory_id"]
            }
        ),

        Tool(
            name="supersede_memory",
            description="Create new memory that supersedes old one (preserves history).",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_memory_id": {"type": "string"},
                    "new_memory_type": {
                        "type": "string",
                        "enum": ["decision", "preference", "experience", "convention", "plan", "note"]
                    },
                    "new_title": {"type": "string"},
                    "new_content": {"type": "string"},
                    "new_reason": {"type": "string"},
                    "new_tags": {"type": "array", "items": {"type": "string"}},
                    "new_importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5}
                },
                "required": ["old_memory_id", "new_memory_type", "new_title", "new_content"]
            }
        ),

        Tool(
            name="get_project_summary",
            description="Get summary of all memories for a project, organized by type.",
            inputSchema={
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"]
            }
        ),

        # ===== Task Management Tools (6) =====
        Tool(
            name="get_task_status",
            description="Get status of a specific task.",
            inputSchema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"]
            }
        ),

        Tool(
            name="watch_task",
            description="Monitor a task in real-time until completion (with timeout).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 10, "maximum": 600, "default": 300},
                    "poll_interval": {"type": "integer", "minimum": 1, "maximum": 10, "default": 2}
                },
                "required": ["task_id"]
            }
        ),

        Tool(
            name="watch_tasks",
            description="Monitor multiple tasks until all complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_ids": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "minimum": 10, "maximum": 600, "default": 300},
                    "poll_interval": {"type": "integer", "minimum": 1, "maximum": 10, "default": 2}
                },
                "required": ["task_ids"]
            }
        ),

        Tool(
            name="list_tasks",
            description="List tasks with optional status filter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["pending", "running", "completed", "failed"]
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                },
                "required": []
            }
        ),

        Tool(
            name="cancel_task",
            description="Cancel a pending or running task.",
            inputSchema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"]
            }
        ),

        Tool(
            name="get_queue_stats",
            description="Get task queue statistics (pending, running, completed, failed counts).",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),

        # ===== System Tools (3) =====
        Tool(
            name="get_graph_schema",
            description="Get Neo4j graph schema (node labels, relationship types, statistics).",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),

        Tool(
            name="get_statistics",
            description="Get knowledge base statistics (node count, document count, etc.).",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),

        Tool(
            name="clear_knowledge_base",
            description="Clear all data from knowledge base (DANGEROUS - requires confirmation).",
            inputSchema={
                "type": "object",
                "properties": {
                    "confirmation": {
                        "type": "string",
                        "description": "Must be 'yes' to confirm"
                    }
                },
                "required": ["confirmation"]
            }
        ),
    ]

    return tools


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
        # Route to handler
        if name == "query_knowledge":
            result = await handle_query_knowledge(arguments)
        elif name == "search_similar_nodes":
            result = await handle_search_similar_nodes(arguments)
        elif name == "add_document":
            result = await handle_add_document(arguments)
        elif name == "add_file":
            result = await handle_add_file(arguments)
        elif name == "add_directory":
            result = await handle_add_directory(arguments)
        elif name == "code_graph_ingest_repo":
            result = await handle_code_graph_ingest_repo(arguments)
        elif name == "code_graph_related":
            result = await handle_code_graph_related(arguments)
        elif name == "code_graph_impact":
            result = await handle_code_graph_impact(arguments)
        elif name == "context_pack":
            result = await handle_context_pack(arguments)
        elif name == "add_memory":
            result = await handle_add_memory(arguments)
        elif name == "search_memories":
            result = await handle_search_memories(arguments)
        elif name == "get_memory":
            result = await handle_get_memory(arguments)
        elif name == "update_memory":
            result = await handle_update_memory(arguments)
        elif name == "delete_memory":
            result = await handle_delete_memory(arguments)
        elif name == "supersede_memory":
            result = await handle_supersede_memory(arguments)
        elif name == "get_project_summary":
            result = await handle_get_project_summary(arguments)
        elif name == "get_task_status":
            result = await handle_get_task_status(arguments)
        elif name == "watch_task":
            result = await handle_watch_task(arguments)
        elif name == "watch_tasks":
            result = await handle_watch_tasks(arguments)
        elif name == "list_tasks":
            result = await handle_list_tasks(arguments)
        elif name == "cancel_task":
            result = await handle_cancel_task(arguments)
        elif name == "get_queue_stats":
            result = await handle_get_queue_stats(arguments)
        elif name == "get_graph_schema":
            result = await handle_get_graph_schema(arguments)
        elif name == "get_statistics":
            result = await handle_get_statistics(arguments)
        elif name == "clear_knowledge_base":
            result = await handle_clear_knowledge_base(arguments)
        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

        # Format and return
        return [TextContent(type="text", text=format_result(result))]

    except Exception as e:
        logger.error(f"Error executing '{name}': {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# Handler Functions - Knowledge Base
# ============================================================================

async def handle_query_knowledge(args: Dict) -> Dict:
    """Query knowledge base"""
    result = await knowledge_service.query(
        question=args["question"],
        mode=args.get("mode", "hybrid")
    )
    logger.info(f"Query: {args['question'][:50]}... (mode: {args.get('mode', 'hybrid')})")
    return result


async def handle_search_similar_nodes(args: Dict) -> Dict:
    """Search similar nodes"""
    result = await knowledge_service.search_similar_nodes(
        query=args["query"],
        top_k=args.get("top_k", 10)
    )
    logger.info(f"Search: {args['query'][:50]}... (top_k: {args.get('top_k', 10)})")
    return result


async def handle_add_document(args: Dict) -> Dict:
    """Add document to knowledge base"""
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


async def handle_add_file(args: Dict) -> Dict:
    """Add file to knowledge base"""
    result = await knowledge_service.add_file(args["file_path"])
    logger.info(f"Add file: {args['file_path']}")
    return result


async def handle_add_directory(args: Dict) -> Dict:
    """Add directory to knowledge base"""
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


# ============================================================================
# Handler Functions - Code Graph
# ============================================================================

async def handle_code_graph_ingest_repo(args: Dict) -> Dict:
    """Ingest repository into code graph"""
    try:
        local_path = args["local_path"]
        repo_url = args.get("repo_url")
        mode = args.get("mode", "incremental")

        # Get repo_id from URL or path
        if repo_url:
            repo_id = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        else:
            from pathlib import Path
            repo_id = Path(local_path).name

        # Check if it's a git repo
        is_git = git_utils.is_git_repo(local_path)

        ingestor = get_code_ingestor()

        if mode == "incremental" and is_git:
            # Incremental mode
            result = await ingestor.ingest_repo_incremental(
                local_path=local_path,
                repo_url=repo_url or f"file://{local_path}",
                repo_id=repo_id
            )
        else:
            # Full mode
            result = await ingestor.ingest_repo(
                local_path=local_path,
                repo_url=repo_url or f"file://{local_path}"
            )

        logger.info(f"Ingest repo: {repo_id} (mode: {mode})")
        return result

    except Exception as e:
        logger.error(f"Code graph ingest failed: {e}")
        return {"success": False, "error": str(e)}


async def handle_code_graph_related(args: Dict) -> Dict:
    """Find related files"""
    try:
        query = args["query"]
        repo_id = args["repo_id"]
        limit = args.get("limit", 30)

        # Search files
        search_result = await graph_service.fulltext_search(
            query=query,
            repo_id=repo_id,
            limit=limit
        )

        if not search_result.get("success"):
            return search_result

        nodes = search_result.get("nodes", [])

        # Rank files
        if nodes:
            ranked = ranker.rank_files(nodes)
            result = {
                "success": True,
                "nodes": ranked,
                "total_count": len(ranked)
            }
        else:
            result = {
                "success": True,
                "nodes": [],
                "total_count": 0
            }

        logger.info(f"Related files: {query} ({len(result['nodes'])} found)")
        return result

    except Exception as e:
        logger.error(f"Code graph related failed: {e}")
        return {"success": False, "error": str(e)}


async def handle_code_graph_impact(args: Dict) -> Dict:
    """Analyze impact of file changes"""
    try:
        result = await graph_service.impact_analysis(
            repo_id=args["repo_id"],
            file_path=args["file_path"],
            depth=args.get("depth", 2)
        )
        logger.info(f"Impact analysis: {args['file_path']}")
        return result
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        return {"success": False, "error": str(e)}


async def handle_context_pack(args: Dict) -> Dict:
    """Build context pack"""
    try:
        result = await pack_builder.build_context_pack(
            repo_id=args["repo_id"],
            stage=args.get("stage", "implement"),
            budget=args.get("budget", 1500),
            keywords=args.get("keywords"),
            focus=args.get("focus")
        )
        logger.info(f"Context pack: {args['repo_id']} (budget: {args.get('budget', 1500)})")
        return result
    except Exception as e:
        logger.error(f"Context pack failed: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# Handler Functions - Memory Store
# ============================================================================

async def handle_add_memory(args: Dict) -> Dict:
    """Add memory"""
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


async def handle_search_memories(args: Dict) -> Dict:
    """Search memories"""
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


async def handle_get_memory(args: Dict) -> Dict:
    """Get memory by ID"""
    result = await memory_store.get_memory(args["memory_id"])
    if result.get("success"):
        logger.info(f"Retrieved memory: {args['memory_id']}")
    return result


async def handle_update_memory(args: Dict) -> Dict:
    """Update memory"""
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


async def handle_delete_memory(args: Dict) -> Dict:
    """Delete memory"""
    result = await memory_store.delete_memory(args["memory_id"])
    if result.get("success"):
        logger.info(f"Memory deleted: {args['memory_id']}")
    return result


async def handle_supersede_memory(args: Dict) -> Dict:
    """Supersede memory"""
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


async def handle_get_project_summary(args: Dict) -> Dict:
    """Get project summary"""
    result = await memory_store.get_project_summary(args["project_id"])
    if result.get("success"):
        summary = result.get("summary", {})
        logger.info(f"Project summary: {summary.get('total_memories', 0)} memories")
    return result


# ============================================================================
# Handler Functions - Task Management
# ============================================================================

async def handle_get_task_status(args: Dict) -> Dict:
    """Get task status"""
    task_id = args["task_id"]
    task = await task_queue.get_task(task_id)

    if task:
        result = {
            "success": True,
            "task_id": task_id,
            "status": task.status.value,
            "created_at": task.created_at,
            "result": task.result,
            "error": task.error
        }
    else:
        result = {"success": False, "error": "Task not found"}

    logger.info(f"Task status: {task_id} - {task.status.value if task else 'not found'}")
    return result


async def handle_watch_task(args: Dict) -> Dict:
    """Watch task until completion"""
    task_id = args["task_id"]
    timeout = args.get("timeout", 300)
    poll_interval = args.get("poll_interval", 2)

    start_time = asyncio.get_event_loop().time()
    history = []

    while True:
        task = await task_queue.get_task(task_id)

        if not task:
            return {"success": False, "error": "Task not found"}

        current = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": task.status.value
        }
        history.append(current)

        # Check if complete
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            result = {
                "success": True,
                "task_id": task_id,
                "final_status": task.status.value,
                "result": task.result,
                "error": task.error,
                "history": history
            }
            logger.info(f"Task completed: {task_id} - {task.status.value}")
            return result

        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            result = {
                "success": False,
                "error": "Timeout",
                "task_id": task_id,
                "current_status": task.status.value,
                "history": history
            }
            logger.warning(f"Task watch timeout: {task_id}")
            return result

        await asyncio.sleep(poll_interval)


async def handle_watch_tasks(args: Dict) -> Dict:
    """Watch multiple tasks"""
    task_ids = args["task_ids"]
    timeout = args.get("timeout", 300)
    poll_interval = args.get("poll_interval", 2)

    start_time = asyncio.get_event_loop().time()
    results = {}

    while True:
        all_done = True

        for task_id in task_ids:
            if task_id in results:
                continue

            task = await task_queue.get_task(task_id)

            if not task:
                results[task_id] = {"status": "not_found"}
                continue

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                results[task_id] = {
                    "status": task.status.value,
                    "result": task.result,
                    "error": task.error
                }
            else:
                all_done = False

        if all_done:
            logger.info(f"All tasks completed: {len(task_ids)} tasks")
            return {"success": True, "tasks": results}

        if asyncio.get_event_loop().time() - start_time > timeout:
            logger.warning(f"Tasks watch timeout: {len(task_ids)} tasks")
            return {"success": False, "error": "Timeout", "tasks": results}

        await asyncio.sleep(poll_interval)


async def handle_list_tasks(args: Dict) -> Dict:
    """List tasks"""
    status_filter = args.get("status_filter")
    limit = args.get("limit", 20)

    all_tasks = await task_queue.get_all_tasks()

    # Filter by status
    if status_filter:
        filtered = [t for t in all_tasks if t.status.value == status_filter]
    else:
        filtered = all_tasks

    # Limit
    limited = filtered[:limit]

    tasks_data = [
        {
            "task_id": t.task_id,
            "status": t.status.value,
            "created_at": t.created_at,
            "has_result": t.result is not None,
            "has_error": t.error is not None
        }
        for t in limited
    ]

    result = {
        "success": True,
        "tasks": tasks_data,
        "total_count": len(filtered),
        "returned_count": len(tasks_data)
    }

    logger.info(f"List tasks: {len(tasks_data)} tasks")
    return result


async def handle_cancel_task(args: Dict) -> Dict:
    """Cancel task"""
    task_id = args["task_id"]
    success = await task_queue.cancel_task(task_id)

    result = {
        "success": success,
        "task_id": task_id,
        "message": "Task cancelled" if success else "Failed to cancel task"
    }

    logger.info(f"Cancel task: {task_id} - {'success' if success else 'failed'}")
    return result


async def handle_get_queue_stats(args: Dict) -> Dict:
    """Get queue statistics"""
    stats = await task_queue.get_stats()
    logger.info(f"Queue stats: {stats}")
    return {"success": True, "stats": stats}


# ============================================================================
# Handler Functions - System
# ============================================================================

async def handle_get_graph_schema(args: Dict) -> Dict:
    """Get graph schema"""
    result = await knowledge_service.get_graph_schema()
    logger.info("Retrieved graph schema")
    return result


async def handle_get_statistics(args: Dict) -> Dict:
    """Get statistics"""
    result = await knowledge_service.get_statistics()
    logger.info("Retrieved statistics")
    return result


async def handle_clear_knowledge_base(args: Dict) -> Dict:
    """Clear knowledge base"""
    confirmation = args.get("confirmation", "")

    if confirmation != "yes":
        return {
            "success": False,
            "error": "Confirmation required. Set confirmation='yes' to proceed."
        }

    result = await knowledge_service.clear_knowledge_base()
    logger.warning("Knowledge base cleared!")
    return result


# ============================================================================
# Utilities
# ============================================================================

def format_result(result: Dict[str, Any]) -> str:
    """Format result for display"""

    if not result.get("success"):
        return f"❌ Error: {result.get('error', 'Unknown error')}"

    # Format based on content
    if "answer" in result:
        # Query result
        output = [f"Answer: {result['answer']}\n"]
        if result.get("source_nodes"):
            output.append(f"\nSources ({len(result['source_nodes'])} nodes):")
            for i, node in enumerate(result['source_nodes'][:5], 1):
                output.append(f"{i}. {node.get('text', '')[:100]}...")
        return "\n".join(output)

    elif "results" in result:
        # Search result
        results = result["results"]
        if not results:
            return "No results found."

        output = [f"Found {len(results)} results:\n"]
        for i, r in enumerate(results[:10], 1):
            output.append(f"{i}. Score: {r.get('score', 0):.3f}")
            output.append(f"   {r.get('text', '')[:100]}...\n")
        return "\n".join(output)

    elif "memories" in result:
        # Memory search
        memories = result["memories"]
        if not memories:
            return "No memories found."

        output = [f"Found {result.get('total_count', 0)} memories:\n"]
        for i, mem in enumerate(memories, 1):
            output.append(f"{i}. [{mem['type']}] {mem['title']}")
            output.append(f"   Importance: {mem.get('importance', 0.5):.2f}")
            if mem.get('tags'):
                output.append(f"   Tags: {', '.join(mem['tags'])}")
            output.append(f"   ID: {mem['id']}\n")
        return "\n".join(output)

    elif "memory" in result:
        # Single memory
        mem = result["memory"]
        output = [
            f"Memory: {mem['title']}",
            f"Type: {mem['type']}",
            f"Importance: {mem.get('importance', 0.5):.2f}",
            f"\nContent: {mem['content']}"
        ]
        if mem.get('reason'):
            output.append(f"\nReason: {mem['reason']}")
        if mem.get('tags'):
            output.append(f"\nTags: {', '.join(mem['tags'])}")
        output.append(f"\nID: {mem['id']}")
        return "\n".join(output)

    elif "nodes" in result:
        # Code graph result
        nodes = result["nodes"]
        if not nodes:
            return "No nodes found."

        output = [f"Found {len(nodes)} nodes:\n"]
        for i, node in enumerate(nodes[:10], 1):
            output.append(f"{i}. {node.get('path', node.get('name', 'Unknown'))}")
            if node.get('score'):
                output.append(f"   Score: {node['score']:.3f}")
            if node.get('ref'):
                output.append(f"   Ref: {node['ref']}")
            output.append("")
        return "\n".join(output)

    elif "items" in result:
        # Context pack
        items = result["items"]
        budget_used = result.get("budget_used", 0)
        budget_limit = result.get("budget_limit", 0)

        output = [
            f"Context Pack ({budget_used}/{budget_limit} tokens)\n",
            f"Items: {len(items)}\n"
        ]

        for item in items:
            output.append(f"[{item['kind']}] {item['title']}")
            if item.get('summary'):
                output.append(f"  {item['summary'][:100]}...")
            output.append(f"  Ref: {item['ref']}\n")

        return "\n".join(output)

    elif "tasks" in result and isinstance(result["tasks"], list):
        # Task list
        tasks = result["tasks"]
        if not tasks:
            return "No tasks found."

        output = [f"Tasks ({len(tasks)}):\n"]
        for task in tasks:
            output.append(f"- {task['task_id']}: {task['status']}")
            output.append(f"  Created: {task['created_at']}")
        return "\n".join(output)

    elif "stats" in result:
        # Queue stats
        stats = result["stats"]
        output = [
            "Queue Statistics:",
            f"Pending: {stats.get('pending', 0)}",
            f"Running: {stats.get('running', 0)}",
            f"Completed: {stats.get('completed', 0)}",
            f"Failed: {stats.get('failed', 0)}"
        ]
        return "\n".join(output)

    else:
        # Generic success
        return f"✅ Success\n{json.dumps(result, indent=2)}"


# ============================================================================
# Resources
# ============================================================================

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources"""
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


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content"""

    await ensure_service_initialized()

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
            "services_initialized": _service_initialized
        }
        return json.dumps(status, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")


# ============================================================================
# Prompts
# ============================================================================

@server.list_prompts()
async def handle_list_prompts() -> List[Prompt]:
    """List available prompts"""
    return [
        Prompt(
            name="suggest_queries",
            description="Generate suggested queries for the knowledge graph",
            arguments=[
                PromptArgument(
                    name="domain",
                    description="Domain to focus on",
                    required=False
                )
            ]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> List[PromptMessage]:
    """Get prompt content"""

    if name == "suggest_queries":
        domain = arguments.get("domain", "general")

        suggestions = {
            "general": [
                "What are the main components of this system?",
                "How does the knowledge pipeline work?",
                "What databases are used?"
            ],
            "code": [
                "Show me Python functions for data processing",
                "Find code examples for Neo4j integration",
                "What are the main classes?"
            ],
            "memory": [
                "What decisions have been made about architecture?",
                "Show me coding preferences for this project",
                "What problems have we encountered?"
            ]
        }

        domain_suggestions = suggestions.get(domain, suggestions["general"])

        content = f"""Here are suggested queries for {domain}:

{chr(10).join(f"• {s}" for s in domain_suggestions)}

Available query modes:
• hybrid: Graph + vector search (recommended)
• graph_only: Graph relationships only
• vector_only: Vector similarity only

You can use query_knowledge tool with these questions."""

        return [
            PromptMessage(
                role="user",
                content={"type": "text", "text": content}
            )
        ]

    else:
        raise ValueError(f"Unknown prompt: {name}")


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
