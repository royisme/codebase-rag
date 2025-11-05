# MCP Tools - Modular Structure

This directory contains the modularized MCP Server v2 implementation. The code has been split from a single 1454-line file into logical, maintainable modules.

## Directory Structure

```
mcp_tools/
├── __init__.py                 # Package exports for all handlers and utilities
├── tool_definitions.py         # Tool definitions (495 lines)
├── utils.py                    # Utility functions (140 lines)
├── knowledge_handlers.py       # Knowledge base handlers (135 lines)
├── code_handlers.py           # Code graph handlers (173 lines)
├── memory_handlers.py         # Memory store handlers (168 lines)
├── task_handlers.py           # Task management handlers (245 lines)
├── system_handlers.py         # System handlers (73 lines)
├── resources.py               # Resource handlers (84 lines)
└── prompts.py                 # Prompt handlers (91 lines)
```

## Module Descriptions

### `__init__.py`
Central import point for the package. Exports all handlers, utilities, and definitions for use in the main server file.

### `tool_definitions.py`
Contains the `get_tool_definitions()` function that returns all 25 tool definitions organized by category:
- Knowledge Base (5 tools)
- Code Graph (4 tools)
- Memory Store (7 tools)
- Task Management (6 tools)
- System (3 tools)

### `utils.py`
Contains the `format_result()` function that formats handler results for display, with specialized formatting for:
- Query results with answers
- Search results
- Memory search results
- Code graph results
- Context packs
- Task lists
- Queue statistics

### `knowledge_handlers.py`
Handlers for knowledge base operations:
- `handle_query_knowledge()` - Query using GraphRAG
- `handle_search_similar_nodes()` - Vector similarity search
- `handle_add_document()` - Add document (sync/async based on size)
- `handle_add_file()` - Add single file
- `handle_add_directory()` - Add directory (async)

### `code_handlers.py`
Handlers for code graph operations:
- `handle_code_graph_ingest_repo()` - Ingest repository (full/incremental)
- `handle_code_graph_related()` - Find related files
- `handle_code_graph_impact()` - Analyze impact/dependencies
- `handle_context_pack()` - Build context pack for AI agents

### `memory_handlers.py`
Handlers for memory store operations:
- `handle_add_memory()` - Add new memory
- `handle_search_memories()` - Search with filters
- `handle_get_memory()` - Get by ID
- `handle_update_memory()` - Update existing
- `handle_delete_memory()` - Soft delete
- `handle_supersede_memory()` - Replace with history
- `handle_get_project_summary()` - Project overview

### `task_handlers.py`
Handlers for task queue operations:
- `handle_get_task_status()` - Get single task status
- `handle_watch_task()` - Monitor task until completion
- `handle_watch_tasks()` - Monitor multiple tasks
- `handle_list_tasks()` - List with filters
- `handle_cancel_task()` - Cancel task
- `handle_get_queue_stats()` - Queue statistics

### `system_handlers.py`
Handlers for system operations:
- `handle_get_graph_schema()` - Get Neo4j schema
- `handle_get_statistics()` - Get KB statistics
- `handle_clear_knowledge_base()` - Clear all data (dangerous)

### `resources.py`
MCP resource handlers:
- `get_resource_list()` - List available resources
- `read_resource_content()` - Read resource content (config, status)

### `prompts.py`
MCP prompt handlers:
- `get_prompt_list()` - List available prompts
- `get_prompt_content()` - Get prompt content (suggest_queries)

## Service Injection Pattern

All handlers use dependency injection for services. Services are passed as parameters from the main server file:

```python
# Example from knowledge_handlers.py
async def handle_query_knowledge(args: Dict, knowledge_service) -> Dict:
    result = await knowledge_service.query(
        question=args["question"],
        mode=args.get("mode", "hybrid")
    )
    return result

# Called from mcp_server_v2.py
result = await handle_query_knowledge(arguments, knowledge_service)
```

This pattern:
- Keeps handlers testable (easy to mock services)
- Makes dependencies explicit
- Allows handlers to be pure functions
- Enables better code organization

## Main Server File

The main `mcp_server_v2.py` (310 lines) is now much cleaner:
- Imports all handlers from `mcp_tools`
- Initializes services
- Routes tool calls to appropriate handlers
- Handles resources and prompts

## Benefits of Modularization

1. **Maintainability**: Each module has a single responsibility
2. **Readability**: Easier to find and understand code
3. **Testability**: Modules can be tested independently
4. **Scalability**: Easy to add new handlers without cluttering main file
5. **Reusability**: Handlers can potentially be reused in other contexts

## Usage

The modularization is transparent to users. The server is used exactly the same way:

```bash
python start_mcp_v2.py
```

All tools, resources, and prompts work identically to the previous implementation.
