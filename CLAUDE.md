# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Code Graph Knowledge System is a Neo4j-based intelligent knowledge management system that combines vector search, graph databases, and LLM integration for document processing and RAG (Retrieval Augmented Generation). The system processes documents into a knowledge graph and provides intelligent querying capabilities.

## Architecture

### Core Components
- **FastAPI Application** (`main.py`, `core/app.py`): Main web server with async request handling
- **Neo4j Knowledge Service** (`services/neo4j_knowledge_service.py`): Primary service handling LlamaIndex + Neo4j integration for knowledge graph operations
- **SQL Parsers** (`services/sql_parser.py`, `services/universal_sql_schema_parser.py`): Database schema analysis and parsing
- **Task Queue System** (`services/task_queue.py`, `monitoring/task_monitor.py`): Async background processing with web monitoring
- **MCP Server** (`mcp_server.py`, `start_mcp.py`): Model Context Protocol integration for AI assistants

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

# Start MCP server (for AI assistant integration)
python start_mcp.py

# Using script entry points (after uv sync)
uv run server
uv run mcp_client

# Direct FastAPI startup
python main.py
```

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