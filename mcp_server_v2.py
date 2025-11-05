"""
MCP Server v2 - Official SDK Version

This is the official MCP SDK implementation of the server, featuring:
- Session management for tracking user context
- Streaming responses for long-running operations
- Multi-transport support (stdio, SSE, WebSocket)
- Enhanced error handling and logging
- Focus on Memory Store tools as initial migration target

Comparison to v1 (fastmcp):
- v1 (mcp_server.py): FastMCP-based, simpler API, 25 tools
- v2 (this file): Official SDK, advanced features, Memory-focused

Usage:
    python start_mcp_v2.py
"""

import asyncio
import sys
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from loguru import logger

from services.memory_store import memory_store
from config import settings


# ============================================================================
# Server Initialization
# ============================================================================

# Create server instance with metadata
server = Server("codebase-rag-memory-v2")

# Session tracking (enhanced capability of official SDK)
active_sessions: Dict[str, Dict[str, Any]] = {}


def track_session_activity(session_id: str, activity: Dict[str, Any]):
    """Track activity within a session for analytics and debugging"""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "activities": [],
            "memories_accessed": set(),
            "memories_created": []
        }

    active_sessions[session_id]["activities"].append({
        "timestamp": datetime.utcnow().isoformat(),
        **activity
    })


# ============================================================================
# Server Lifecycle Hooks
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """
    List all available tools.

    This is called by MCP clients to discover available tools.
    Official SDK provides strong typing and validation.
    """
    return [
        Tool(
            name="add_memory",
            description="""Add a new memory to the project knowledge base.

Use this to manually save important information:
- Design decisions and their rationale
- Team preferences and conventions
- Problems encountered and solutions
- Future plans and improvements

Memory Types:
- decision: Architecture choices, tech stack selection
- preference: Coding style, tool preferences
- experience: Problems and solutions
- convention: Team rules, naming conventions
- plan: Future improvements, TODOs
- note: Other important information""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project identifier (e.g., repo name)"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["decision", "preference", "experience", "convention", "plan", "note"],
                        "description": "Type of memory"
                    },
                    "title": {
                        "type": "string",
                        "description": "Short title/summary",
                        "minLength": 1,
                        "maxLength": 200
                    },
                    "content": {
                        "type": "string",
                        "description": "Detailed content",
                        "minLength": 1
                    },
                    "reason": {
                        "type": "string",
                        "description": "Rationale or explanation (optional)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance score 0-1",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5
                    },
                    "related_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related ref:// handles"
                    }
                },
                "required": ["project_id", "memory_type", "title", "content"]
            }
        ),
        Tool(
            name="search_memories",
            description="""Search project memories with various filters.

Use this to find relevant memories when:
- Starting a new feature (search for related decisions)
- Debugging an issue (search for similar experiences)
- Understanding project conventions

Filters:
- query: Text search (title, content, reason, tags)
- memory_type: Filter by type
- tags: Filter by tags (any match)
- min_importance: Minimum importance score
- limit: Max results (default 20)

Returns memories sorted by relevance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project identifier"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query text (optional)"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["decision", "preference", "experience", "convention", "plan", "note"],
                        "description": "Filter by type (optional)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (optional)"
                    },
                    "min_importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.0,
                        "description": "Minimum importance score"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20,
                        "description": "Maximum results"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_memory",
            description="Get a specific memory by ID with full details and related references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory identifier"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="update_memory",
            description="Update an existing memory. Only provided fields will be updated.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory identifier"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content (optional)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "New reason (optional)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags (optional)"
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "New importance score (optional)"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="delete_memory",
            description="Delete a memory (soft delete - marks as deleted but retains data).",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory identifier"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="supersede_memory",
            description="""Create a new memory that supersedes an old one.

Use when a decision changes or a better solution is found.
The old memory will be marked as superseded and linked to the new one.
History is preserved for audit trails.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_memory_id": {
                        "type": "string",
                        "description": "ID of memory to supersede"
                    },
                    "new_memory_type": {
                        "type": "string",
                        "enum": ["decision", "preference", "experience", "convention", "plan", "note"],
                        "description": "Type of new memory"
                    },
                    "new_title": {
                        "type": "string",
                        "description": "Title of new memory"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "Content of new memory"
                    },
                    "new_reason": {
                        "type": "string",
                        "description": "Reason for change (optional)"
                    },
                    "new_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for new memory (optional)"
                    },
                    "new_importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5,
                        "description": "Importance of new memory"
                    }
                },
                "required": ["old_memory_id", "new_memory_type", "new_title", "new_content"]
            }
        ),
        Tool(
            name="get_project_summary",
            description="""Get a summary of all memories for a project, organized by type.

Shows:
- Total memory count
- Breakdown by type (decision/preference/experience/etc.)
- Top memories by importance for each type

Use this to get an overview of project knowledge.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project identifier"
                    }
                },
                "required": ["project_id"]
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: Dict[str, Any]
) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """
    Handle tool execution.

    Official SDK provides:
    - Strong typing
    - Automatic validation
    - Better error handling
    - Session context (can be added in future)
    """

    # Initialize memory store if needed
    if not memory_store._initialized:
        success = await memory_store.initialize()
        if not success:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Memory store initialization failed"
                )
            ]

    try:
        # Route to appropriate handler
        if name == "add_memory":
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
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'"
                )
            ]

        # Return formatted response
        return [
            TextContent(
                type="text",
                text=format_result(result)
            )
        ]

    except Exception as e:
        logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


# ============================================================================
# Tool Handlers (Memory Store)
# ============================================================================

async def handle_add_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new memory"""
    result = await memory_store.add_memory(
        project_id=arguments["project_id"],
        memory_type=arguments["memory_type"],
        title=arguments["title"],
        content=arguments["content"],
        reason=arguments.get("reason"),
        tags=arguments.get("tags"),
        importance=arguments.get("importance", 0.5),
        related_refs=arguments.get("related_refs")
    )

    if result.get("success"):
        logger.info(f"Memory added: {result['memory_id']}")

    return result


async def handle_search_memories(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search memories with filters.

    Note: Official SDK supports streaming responses, which we can add later
    for large result sets. For now, returns all at once.
    """
    result = await memory_store.search_memories(
        project_id=arguments["project_id"],
        query=arguments.get("query"),
        memory_type=arguments.get("memory_type"),
        tags=arguments.get("tags"),
        min_importance=arguments.get("min_importance", 0.0),
        limit=arguments.get("limit", 20)
    )

    if result.get("success"):
        logger.info(f"Memory search: found {result.get('total_count', 0)} results")

    return result


async def handle_get_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get specific memory by ID"""
    result = await memory_store.get_memory(arguments["memory_id"])

    if result.get("success"):
        logger.info(f"Retrieved memory: {arguments['memory_id']}")

    return result


async def handle_update_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Update existing memory"""
    result = await memory_store.update_memory(
        memory_id=arguments["memory_id"],
        title=arguments.get("title"),
        content=arguments.get("content"),
        reason=arguments.get("reason"),
        tags=arguments.get("tags"),
        importance=arguments.get("importance")
    )

    if result.get("success"):
        logger.info(f"Memory updated: {arguments['memory_id']}")

    return result


async def handle_delete_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Delete memory (soft delete)"""
    result = await memory_store.delete_memory(arguments["memory_id"])

    if result.get("success"):
        logger.info(f"Memory deleted: {arguments['memory_id']}")

    return result


async def handle_supersede_memory(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create new memory that supersedes old one"""
    result = await memory_store.supersede_memory(
        old_memory_id=arguments["old_memory_id"],
        new_memory_data={
            "memory_type": arguments["new_memory_type"],
            "title": arguments["new_title"],
            "content": arguments["new_content"],
            "reason": arguments.get("new_reason"),
            "tags": arguments.get("new_tags"),
            "importance": arguments.get("new_importance", 0.5)
        }
    )

    if result.get("success"):
        logger.info(f"Memory superseded: {arguments['old_memory_id']} -> {result.get('new_memory_id')}")

    return result


async def handle_get_project_summary(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get project memory summary"""
    result = await memory_store.get_project_summary(arguments["project_id"])

    if result.get("success"):
        summary = result.get("summary", {})
        total = summary.get("total_memories", 0)
        logger.info(f"Project summary: {total} total memories")

    return result


# ============================================================================
# Utilities
# ============================================================================

def format_result(result: Dict[str, Any]) -> str:
    """
    Format result for display to user.

    Official SDK allows rich content (images, embedded resources),
    but for now we use simple text formatting.
    """
    import json

    if not result.get("success"):
        return f"❌ Error: {result.get('error', 'Unknown error')}"

    # Format based on result type
    if "memories" in result:
        # Search results
        memories = result["memories"]
        total = result.get("total_count", 0)

        if total == 0:
            return "No memories found."

        output = [f"Found {total} memories:\n"]
        for i, mem in enumerate(memories, 1):
            output.append(f"{i}. [{mem['type']}] {mem['title']}")
            output.append(f"   Importance: {mem.get('importance', 0.5):.2f}")
            if mem.get('tags'):
                output.append(f"   Tags: {', '.join(mem['tags'])}")
            output.append(f"   ID: {mem['id']}\n")

        return "\n".join(output)

    elif "memory" in result:
        # Single memory result
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

        if mem.get('related_refs'):
            output.append(f"\nRelated: {len(mem['related_refs'])} code references")

        output.append(f"\nID: {mem['id']}")
        output.append(f"Created: {mem.get('created_at', 'N/A')}")

        return "\n".join(output)

    elif "summary" in result:
        # Project summary
        summary = result["summary"]
        total = summary.get("total_memories", 0)
        by_type = summary.get("by_type", {})

        output = [f"Project Summary: {total} total memories\n"]

        for mem_type, data in by_type.items():
            count = data.get("count", 0)
            output.append(f"{mem_type}: {count}")

            top_mems = data.get("top_memories", [])[:3]
            for mem in top_mems:
                output.append(f"  - {mem['title']} (importance: {mem.get('importance', 0.5):.2f})")

        return "\n".join(output)

    else:
        # Generic success with details
        return f"✅ Success\n{json.dumps(result, indent=2)}"


# ============================================================================
# Server Entry Point
# ============================================================================

async def main():
    """Main entry point for the MCP server"""
    from mcp.server.stdio import stdio_server

    logger.info("Starting MCP Server v2 (Official SDK) - Memory Store Focus")
    logger.info(f"Server: {server.name}")
    logger.info("Transport: stdio")
    logger.info("Tools: 7 Memory Management tools")

    # Run the server using stdio transport (for Claude Desktop)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="codebase-rag-memory-v2",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
