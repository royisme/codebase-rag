"""
MCP Tools Package

This package contains modularized handlers for MCP Server v2.
All tool handlers, utilities, and definitions are organized into logical modules.
"""

# Knowledge base handlers
from .knowledge_handlers import (
    handle_query_knowledge,
    handle_search_similar_nodes,
    handle_add_document,
    handle_add_file,
    handle_add_directory,
)

# Code graph handlers
from .code_handlers import (
    handle_code_graph_ingest_repo,
    handle_code_graph_related,
    handle_code_graph_impact,
    handle_context_pack,
)

# Memory store handlers
from .memory_handlers import (
    handle_add_memory,
    handle_search_memories,
    handle_get_memory,
    handle_update_memory,
    handle_delete_memory,
    handle_supersede_memory,
    handle_get_project_summary,
    # v0.7 Automatic extraction
    handle_extract_from_conversation,
    handle_extract_from_git_commit,
    handle_extract_from_code_comments,
    handle_suggest_memory_from_query,
    handle_batch_extract_from_repository,
)

# Task management handlers
from .task_handlers import (
    handle_get_task_status,
    handle_watch_task,
    handle_watch_tasks,
    handle_list_tasks,
    handle_cancel_task,
    handle_get_queue_stats,
)

# System handlers
from .system_handlers import (
    handle_get_graph_schema,
    handle_get_statistics,
    handle_clear_knowledge_base,
)

# Tool definitions
from .tool_definitions import get_tool_definitions

# Utilities
from .utils import format_result

# Resources
from .resources import get_resource_list, read_resource_content

# Prompts
from .prompts import get_prompt_list, get_prompt_content


__all__ = [
    # Knowledge handlers
    "handle_query_knowledge",
    "handle_search_similar_nodes",
    "handle_add_document",
    "handle_add_file",
    "handle_add_directory",
    # Code handlers
    "handle_code_graph_ingest_repo",
    "handle_code_graph_related",
    "handle_code_graph_impact",
    "handle_context_pack",
    # Memory handlers
    "handle_add_memory",
    "handle_search_memories",
    "handle_get_memory",
    "handle_update_memory",
    "handle_delete_memory",
    "handle_supersede_memory",
    "handle_get_project_summary",
    # v0.7 Extraction handlers
    "handle_extract_from_conversation",
    "handle_extract_from_git_commit",
    "handle_extract_from_code_comments",
    "handle_suggest_memory_from_query",
    "handle_batch_extract_from_repository",
    # Task handlers
    "handle_get_task_status",
    "handle_watch_task",
    "handle_watch_tasks",
    "handle_list_tasks",
    "handle_cancel_task",
    "handle_get_queue_stats",
    # System handlers
    "handle_get_graph_schema",
    "handle_get_statistics",
    "handle_clear_knowledge_base",
    # Tool definitions
    "get_tool_definitions",
    # Utilities
    "format_result",
    # Resources
    "get_resource_list",
    "read_resource_content",
    # Prompts
    "get_prompt_list",
    "get_prompt_content",
]
