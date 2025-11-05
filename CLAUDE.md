# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Code Graph Knowledge System is a Neo4j-based intelligent knowledge management system that combines vector search, graph databases, and LLM integration for document processing and RAG (Retrieval Augmented Generation). The system processes documents into a knowledge graph and provides intelligent querying capabilities.

## Architecture

### Core Components
- **FastAPI Application** (`main.py`, `core/app.py`): Main web server with async request handling
- **Neo4j Knowledge Service** (`services/neo4j_knowledge_service.py`): Primary service handling LlamaIndex + Neo4j integration for knowledge graph operations
- **Memory Store** (`services/memory_store.py`): Project knowledge persistence for AI agents - stores decisions, preferences, experiences, and conventions (v0.6)
- **SQL Parsers** (`services/sql_parser.py`, `services/universal_sql_schema_parser.py`): Database schema analysis and parsing
- **Task Queue System** (`services/task_queue.py`, `monitoring/task_monitor.py`): Async background processing with web monitoring
- **MCP Server** (`mcp_server.py`, `start_mcp.py`): Model Context Protocol integration for AI assistants
  - **v1 (FastMCP)**: `mcp_server.py` - Full feature set with 25 tools (stable)
  - **v2 (Official SDK)**: `mcp_server_v2.py` - Official MCP SDK with advanced features (Memory Store, 7 tools)

### Multi-Provider LLM Support
The system supports multiple LLM and embedding providers:
- **Ollama**: Local LLM hosting (default)
- **OpenAI**: GPT models and embeddings
- **Google Gemini**: Gemini models and embeddings  
- **OpenRouter**: Access to multiple model providers
- **HuggingFace**: Local embedding models

Configuration is handled via environment variables in `.env` file (see `env.example`).

## Development Commands

### Running the Application
```bash
# Start main application
python start.py

# Start MCP server v1 (FastMCP - all 25 tools)
python start_mcp.py

# Start MCP server v2 (Official SDK - Memory Store only, 7 tools)
python start_mcp_v2.py

# Using script entry points (after uv sync)
uv run server
uv run mcp_client        # MCP v1
uv run mcp_client_v2     # MCP v2

# Direct FastAPI startup
python main.py
```

**MCP Server Versions**:
- **v1** (FastMCP): Stable, 25 tools, all features
- **v2** (Official SDK): New, 7 Memory tools, advanced features (session management, streaming)
- See `docs/MCP_MIGRATION_GUIDE.md` for detailed comparison

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov

# Run specific test file
pytest tests/test_specific.py
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
ruff check .
```

### Dependencies
```bash
# Install dependencies
pip install -e .

# Using uv (recommended)
uv pip install -e .
```

## Configuration

### Environment Setup
1. Copy `env.example` to `.env`
2. Configure Neo4j connection: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
3. Choose LLM provider: `LLM_PROVIDER` (ollama/openai/gemini/openrouter)
4. Set embedding provider: `EMBEDDING_PROVIDER`

### Neo4j Requirements
- Neo4j 5.0+ with APOC plugin
- Default connection: `bolt://localhost:7687`
- Database: `neo4j` (default)

### Service Dependencies
The application checks service health on startup via `start.py:check_dependencies()`. Required services:
- Neo4j database connection
- LLM provider (Ollama/OpenAI/etc.)

## Key Development Patterns

### Service Initialization
All services use async initialization patterns. The `Neo4jKnowledgeService` must be initialized before use:
```python
await knowledge_service.initialize()
```

### Error Handling
Services return structured responses with `success` field and error details:
```python
result = await service.operation()
if not result.get("success"):
    # Handle error from result["error"]
```

### Timeout Management
Operations use configurable timeouts from `config.py`:
- `connection_timeout`: Database connections
- `operation_timeout`: Standard operations
- `large_document_timeout`: Large document processing

### LlamaIndex Integration
The system uses LlamaIndex's `KnowledgeGraphIndex` with Neo4j backend. Global settings are configured in `services/neo4j_knowledge_service.py:initialize()`.

## API Structure

### Main Endpoints
- `/api/v1/health`: Service health check
- `/api/v1/knowledge/query`: Query knowledge base with RAG
- `/api/v1/knowledge/search`: Vector similarity search
- `/api/v1/documents/*`: Document management
- `/api/v1/sql/*`: SQL parsing and analysis
- `/api/v1/memory/*`: Memory management for AI agents (v0.6)
  - `POST /add`: Add new memory (decision/preference/experience/convention/plan/note)
  - `POST /search`: Search memories with filters
  - `GET /{memory_id}`: Get specific memory
  - `PUT /{memory_id}`: Update memory
  - `DELETE /{memory_id}`: Delete memory (soft delete)
  - `POST /supersede`: Create new memory that supersedes old one
  - `GET /project/{project_id}/summary`: Get project memory summary

### Real-time Task Monitoring
The system provides multiple approaches for real-time task monitoring:

#### Web UI Monitoring (`/ui/monitor`)
When `ENABLE_MONITORING=true`, NiceGUI monitoring interface is available with:
- Real-time task status updates via WebSocket
- File upload functionality (50KB size limit)
- Directory batch processing
- Task progress visualization

#### Server-Sent Events (SSE) API
SSE endpoints for streaming real-time updates:
- `/api/v1/sse/task/{task_id}`: Monitor single task progress
- `/api/v1/sse/tasks`: Monitor all tasks with optional status filtering
- `/api/v1/sse/stats`: Get active SSE connection statistics

#### MCP Real-time Tools
MCP server provides real-time monitoring tools:
- `watch_task`: Monitor single task with progress history
- `watch_tasks`: Monitor multiple tasks until completion
- Supports custom timeouts and update intervals
- **Note**: These are MCP protocol tools, not HTTP endpoints

#### Client Implementation Examples
- `examples/pure_mcp_client.py`: Pure MCP client using `watch_task` tools
- `examples/hybrid_http_sse_client.py`: HTTP + SSE hybrid approach

### Large File Handling Strategy
The system handles large documents through multiple approaches:
- **Small files (<10KB)**: Direct synchronous processing
- **Medium files (10-50KB)**: Temporary file strategy with background processing
- **Large files (>50KB)**: UI prompts for directory processing or MCP client usage
- **MCP client**: Automatic temporary file creation for large documents

## Testing Approach

Tests are located in `tests/` directory. The system includes comprehensive testing for SQL parsing functionality. Use `pytest` for running tests.

## Memory Management for AI Agents (v0.6)

The Memory Store provides long-term project knowledge persistence specifically designed for AI agents during continuous development. Unlike short-term conversation history, Memory Store preserves curated project knowledge.

### Core Concept

**Memory = Structured Project Knowledge**

When AI agents work on a project over time, they need to remember:
- **Decisions**: Architecture choices, technology selections, and their rationale
- **Preferences**: Coding styles, tools, and team conventions
- **Experiences**: Problems encountered and their solutions
- **Conventions**: Team rules, naming patterns, and best practices
- **Plans**: Future improvements and TODOs
- **Notes**: Other important project information

### Why Memory is Essential for AI Coding

1. **Cross-Session Continuity**: Remember decisions made in previous sessions
2. **Avoid Repeating Mistakes**: Recall past problems and solutions
3. **Maintain Consistency**: Follow established patterns and conventions
4. **Track Evolution**: Document how decisions change over time
5. **Preserve Rationale**: Remember *why* something was done, not just *what* was done

### Memory Types and Use Cases

```python
# Decision - Architecture and technical choices
{
    "type": "decision",
    "title": "Use JWT for authentication",
    "content": "Decided to use JWT tokens instead of session-based auth",
    "reason": "Need stateless authentication for mobile clients",
    "importance": 0.9,
    "tags": ["auth", "architecture"]
}

# Preference - Team coding style and tool choices
{
    "type": "preference",
    "title": "Use raw SQL instead of ORM",
    "content": "Team prefers writing raw SQL queries",
    "reason": "Better performance control and team familiarity",
    "importance": 0.6,
    "tags": ["database", "coding-style"]
}

# Experience - Problems and solutions
{
    "type": "experience",
    "title": "Redis connection timeout in Docker",
    "content": "Redis fails with localhost in Docker",
    "reason": "Docker requires service name instead of localhost",
    "importance": 0.7,
    "tags": ["docker", "redis", "networking"]
}

# Convention - Team rules and standards
{
    "type": "convention",
    "title": "API endpoints must use kebab-case",
    "content": "All REST API endpoints use kebab-case naming",
    "importance": 0.5,
    "tags": ["api", "naming"]
}

# Plan - Future work and improvements
{
    "type": "plan",
    "title": "Migrate to PostgreSQL 16",
    "content": "Plan to upgrade PostgreSQL for performance improvements",
    "importance": 0.4,
    "tags": ["database", "upgrade"]
}
```

### MCP Tools for AI Agents

The Memory Store provides 7 MCP tools (available in Claude Desktop, VSCode with MCP, etc.):

1. **add_memory**: Save new project knowledge
2. **search_memories**: Find relevant memories when starting tasks
3. **get_memory**: Retrieve specific memory by ID
4. **update_memory**: Modify existing memory
5. **delete_memory**: Remove memory (soft delete)
6. **supersede_memory**: Create new memory that replaces old one
7. **get_project_summary**: Get overview of all project memories

### Typical AI Agent Workflow

```
1. Start working on a feature
   ↓
2. search_memories(query="feature area", memory_type="decision")
   - Find related past decisions
   - Check team preferences
   - Review known issues
   ↓
3. Implement feature following established patterns
   ↓
4. add_memory() to save:
   - Implementation decisions
   - Problems encountered
   - Solutions discovered
   ↓
5. Next session: Agent remembers everything
```

### HTTP API

For web clients and custom integrations:

```bash
# Add a decision
POST /api/v1/memory/add
{
    "project_id": "myapp",
    "memory_type": "decision",
    "title": "Use PostgreSQL",
    "content": "Selected PostgreSQL for main database",
    "reason": "Need advanced JSON support",
    "importance": 0.9,
    "tags": ["database", "architecture"]
}

# Search memories
POST /api/v1/memory/search
{
    "project_id": "myapp",
    "query": "database",
    "memory_type": "decision",
    "min_importance": 0.7
}

# Get project summary
GET /api/v1/memory/project/myapp/summary
```

### Memory Evolution

When decisions change, use `supersede_memory` to maintain history:

```python
# Original decision
old_id = add_memory(
    title="Use MySQL",
    content="Selected MySQL for database",
    importance=0.7
)

# Later: Decision changes
supersede_memory(
    old_memory_id=old_id,
    new_title="Migrate to PostgreSQL",
    new_content="Migrating from MySQL to PostgreSQL",
    new_reason="Need advanced features",
    new_importance=0.9
)

# Result:
# - New memory becomes primary
# - Old memory marked as superseded
# - History preserved
```

### Implementation Details

**Storage**: Neo4j graph database
- Nodes: `Memory`, `Project`
- Relationships: `BELONGS_TO`, `RELATES_TO`, `SUPERSEDES`
- Indexes: Fulltext search on title, content, reason, tags

**Key Files**:
- `services/memory_store.py`: Core memory management service
- `api/memory_routes.py`: HTTP API endpoints
- `services/memory_extractor.py`: Future auto-extraction (placeholder)
- `mcp_server.py` (lines 1407-1885): MCP tool implementations
- `tests/test_memory_store.py`: Comprehensive tests
- `examples/memory_usage_example.py`: Usage examples

### Manual vs Automatic Memory Curation

**v0.6 (Current)**: Manual curation
- AI agent explicitly calls `add_memory` to save knowledge
- User can manually add memories via API
- Full control over what gets saved

**Future (v0.7+)**: Automatic extraction
- Extract from git commits
- Mine from code comments
- Analyze conversations
- Auto-suggest important memories

### Best Practices

1. **Importance Scoring**:
   - 0.9-1.0: Critical decisions, security findings
   - 0.7-0.8: Important architectural choices
   - 0.5-0.6: Preferences and conventions
   - 0.3-0.4: Plans and future work
   - 0.0-0.2: Minor notes

2. **Tagging Strategy**:
   - Use domain tags: `auth`, `database`, `api`
   - Use type tags: `security`, `performance`, `bug`
   - Use status tags: `critical`, `deprecated`

3. **When to Save Memory**:
   - After making architecture decisions
   - When solving a tricky bug
   - When establishing team conventions
   - When discovering important limitations

4. **Search Strategy**:
   - Search before starting work on a feature
   - Use tags to filter by domain
   - Use `min_importance` to focus on key decisions
   - Review project summary periodically

### Examples

See `examples/memory_usage_example.py` for complete working examples of:
- Direct service usage
- HTTP API usage
- AI agent workflow
- Memory evolution
- MCP tool invocations