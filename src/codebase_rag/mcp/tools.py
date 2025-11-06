"""
Tool Definitions for MCP Server v2

This module contains all tool definitions used by the MCP server.
Each tool defines its name, description, and input schema.
"""

from typing import List
from mcp.types import Tool


def get_tool_definitions() -> List[Tool]:
    """
    Get all 30 tool definitions for MCP server.

    Returns:
        List of Tool objects organized by category:
        - Knowledge Base (5 tools)
        - Code Graph (4 tools)
        - Memory Store (7 tools)
        - Memory Extraction v0.7 (5 tools)
        - Task Management (6 tools)
        - System (3 tools)
    """

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

        # ===== Memory Extraction Tools (v0.7) - 5 tools =====
        Tool(
            name="extract_from_conversation",
            description="""Extract memories from conversation using LLM analysis (v0.7).

Analyzes conversation messages to identify:
- Design decisions and rationale
- Problems encountered and solutions
- Preferences and conventions
- Important architectural choices

Can auto-save high-confidence memories or return suggestions for manual review.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "conversation": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        },
                        "description": "List of conversation messages"
                    },
                    "auto_save": {
                        "type": "boolean",
                        "default": False,
                        "description": "Auto-save high-confidence memories (>= 0.7)"
                    }
                },
                "required": ["project_id", "conversation"]
            }
        ),

        Tool(
            name="extract_from_git_commit",
            description="""Extract memories from git commit using LLM analysis (v0.7).

Analyzes commit message and changed files to identify:
- Feature additions (decisions)
- Bug fixes (experiences)
- Refactoring (experiences/conventions)
- Breaking changes (high importance decisions)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "commit_sha": {"type": "string", "description": "Git commit SHA"},
                    "commit_message": {"type": "string", "description": "Full commit message"},
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of changed file paths"
                    },
                    "auto_save": {
                        "type": "boolean",
                        "default": False,
                        "description": "Auto-save high-confidence memories"
                    }
                },
                "required": ["project_id", "commit_sha", "commit_message", "changed_files"]
            }
        ),

        Tool(
            name="extract_from_code_comments",
            description="""Extract memories from code comments in source file (v0.7).

Identifies special markers:
- TODO: → plan
- FIXME: / BUG: → experience
- NOTE: / IMPORTANT: → convention
- DECISION: → decision

Extracts and saves as structured memories with file references.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "file_path": {"type": "string", "description": "Path to source file"}
                },
                "required": ["project_id", "file_path"]
            }
        ),

        Tool(
            name="suggest_memory_from_query",
            description="""Suggest creating memory from knowledge base query (v0.7).

Uses LLM to determine if Q&A represents important knowledge worth saving.
Returns suggestion with confidence score (not auto-saved).

Useful for:
- Frequently asked questions
- Important architectural information
- Non-obvious solutions or workarounds""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "query": {"type": "string", "description": "User query"},
                    "answer": {"type": "string", "description": "LLM answer"}
                },
                "required": ["project_id", "query", "answer"]
            }
        ),

        Tool(
            name="batch_extract_from_repository",
            description="""Batch extract memories from entire repository (v0.7).

Comprehensive analysis of:
- Recent git commits (configurable count)
- Code comments in source files
- Documentation files (README, CHANGELOG, etc.)

This is a long-running operation that may take several minutes.
Returns summary of extracted memories by source type.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "repo_path": {"type": "string", "description": "Path to git repository"},
                    "max_commits": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 50,
                        "description": "Maximum commits to analyze"
                    },
                    "file_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File patterns to scan (e.g., ['*.py', '*.js'])"
                    }
                },
                "required": ["project_id", "repo_path"]
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
