# MCP Integration Overview

The Model Context Protocol (MCP) is an open standard that enables AI assistants like Claude Desktop and VS Code extensions to connect to external tools and data sources. The Code Graph Knowledge System provides a complete MCP server implementation with 30 specialized tools.

## What is MCP?

MCP (Model Context Protocol) is an open protocol developed by Anthropic that allows AI assistants to:

- **Access External Tools**: Call functions in external applications
- **Retrieve Context**: Fetch data from databases, APIs, and services
- **Execute Actions**: Perform operations on behalf of users
- **Stream Responses**: Receive real-time updates

Think of MCP as a standardized way for AI assistants to "talk to" your applications.

## Architecture

```
┌─────────────────┐
│  AI Assistant   │  (Claude Desktop, VS Code, etc.)
│  (MCP Client)   │
└────────┬────────┘
         │ MCP Protocol
         │ (stdio, SSE, WebSocket)
         ↓
┌─────────────────┐
│   MCP Server    │  (This Application)
│  (start_mcp.py) │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│  Backend Services                        │
│  ┌────────────────────────────────────┐ │
│  │ Knowledge RAG  │  Code Graph       │ │
│  │ Memory Store   │  Task Queue       │ │
│  │ Neo4j Database │  Git Integration  │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## System Components

### 1. MCP Server (`start_mcp.py`)

The main server that:
- Implements MCP protocol using official SDK
- Exposes 30 tools across 6 categories
- Manages connections from AI clients
- Routes requests to backend services

**Key Features**:
- ✅ Official MCP SDK (`mcp>=1.1.0`)
- ✅ Modular architecture (310-line main file)
- ✅ Session management
- ✅ Streaming support
- ✅ Multi-transport (stdio, SSE, WebSocket)

### 2. MCP Clients

AI assistants that connect to the server:

**Supported Clients**:
- **Claude Desktop**: Official Anthropic desktop app
- **VS Code**: Via MCP extension
- **Custom Clients**: Using MCP SDK

### 3. Backend Services

The actual functionality exposed via MCP:
- Knowledge RAG for document Q&A
- Code Graph for repository analysis
- Memory Store for project knowledge
- Task Queue for async operations
- Git utilities for repository operations

## Available Tools (30 Total)

### Knowledge Base Tools (5)

Process and query documents using RAG:

1. **query_knowledge**: Ask questions, get LLM-generated answers
2. **search_similar_nodes**: Find similar documents via vector search
3. **add_document**: Add document content to knowledge base
4. **add_file**: Process single file
5. **add_directory**: Batch process directory

**Availability**: Full mode only (requires LLM + embeddings)

### Code Graph Tools (4)

Analyze code repositories:

1. **code_graph_ingest_repo**: Index repository structure
2. **code_graph_fulltext_search**: Search code by text
3. **code_graph_impact_analysis**: Analyze change impact
4. **code_graph_pack_context**: Build context for LLM

**Availability**: All modes

### Memory Management Tools (7)

Store project knowledge for AI agents:

1. **add_memory**: Save decisions, preferences, experiences
2. **search_memories**: Find relevant memories
3. **get_memory**: Retrieve by ID
4. **update_memory**: Modify existing memory
5. **delete_memory**: Remove memory (soft delete)
6. **supersede_memory**: Replace with history preservation
7. **get_project_summary**: Get overview

**Availability**: All modes

### Memory Extraction Tools (5)

Automatically extract memories (v0.7):

1. **extract_from_conversation**: Analyze AI conversations
2. **extract_from_git_commit**: Mine git commits
3. **extract_from_code_comments**: Extract TODOs, FIXMEs
4. **suggest_memory_from_query**: Suggest from Q&A
5. **batch_extract_from_repository**: Comprehensive extraction

**Availability**: Full mode only (requires LLM)

### Task Management Tools (6)

Monitor async operations:

1. **get_task_status**: Check task status
2. **watch_task**: Monitor single task
3. **watch_tasks**: Monitor multiple tasks
4. **list_tasks**: List all tasks
5. **cancel_task**: Cancel running task
6. **get_queue_stats**: Get queue statistics

**Availability**: All modes

### System Tools (3)

System information and management:

1. **get_graph_schema**: Get Neo4j schema
2. **get_statistics**: Get system statistics
3. **clear_knowledge_base**: Clear all data

**Availability**: All modes

## Tool Usage Pattern

### Example: Query Knowledge Base

```json
{
  "tool": "query_knowledge",
  "input": {
    "question": "How do I configure Docker deployment?",
    "mode": "hybrid"
  }
}
```

**Response**:
```json
{
  "answer": "To configure Docker deployment, you need to...",
  "sources": [
    {"title": "Docker Guide", "score": 0.92, "content": "..."}
  ],
  "mode": "hybrid",
  "retrieval_time_ms": 150,
  "generation_time_ms": 2300
}
```

### Example: Add Memory

```json
{
  "tool": "add_memory",
  "input": {
    "project_id": "myapp",
    "memory_type": "decision",
    "title": "Use PostgreSQL for main database",
    "content": "Selected PostgreSQL over MySQL",
    "reason": "Need advanced JSON support and better performance",
    "importance": 0.9,
    "tags": ["database", "architecture"]
  }
}
```

### Example: Code Graph Analysis

```json
{
  "tool": "code_graph_ingest_repo",
  "input": {
    "repo_path": "/path/to/repo",
    "mode": "incremental"
  }
}
```

## MCP Protocol Details

### Transport Methods

MCP supports multiple transport protocols:

1. **stdio** (Standard Input/Output)
   - Used by Claude Desktop
   - Process-based communication
   - Most common for desktop apps

2. **SSE** (Server-Sent Events)
   - HTTP-based streaming
   - Used by web applications
   - Good for browser-based clients

3. **WebSocket**
   - Bidirectional streaming
   - Real-time updates
   - Low latency

**Our Implementation**: Supports all three via official MCP SDK

### Message Types

MCP uses JSON-RPC 2.0 protocol:

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tools/call",
  "params": {
    "name": "query_knowledge",
    "arguments": {
      "question": "What is RAG?"
    }
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "RAG (Retrieval-Augmented Generation) is..."
      }
    ]
  }
}
```

### Session Management

MCP maintains sessions for:
- User context preservation
- State management
- Resource tracking
- Connection lifecycle

## Deployment Modes

MCP server adapts to your deployment mode:

### Full Mode (All Features)

```bash
DEPLOYMENT_MODE=full
ENABLE_KNOWLEDGE_RAG=true
ENABLE_AUTO_EXTRACTION=true
```

**Tools Available**: 30 tools (all features)

### Standard Mode (No RAG)

```bash
DEPLOYMENT_MODE=standard
ENABLE_KNOWLEDGE_RAG=false
ENABLE_AUTO_EXTRACTION=false
```

**Tools Available**: 20 tools (no Knowledge RAG, no auto-extraction)

### Minimal Mode (Graph + Memory Only)

```bash
DEPLOYMENT_MODE=minimal
```

**Tools Available**: 17 tools (Code Graph + Memory + Tasks + System)

## Configuration

### Server Configuration

Configure MCP server in `.env`:

```bash
# MCP Server Settings
MCP_SERVER_NAME="Code Graph Knowledge System"
MCP_SERVER_VERSION="2.0"
MCP_LOG_LEVEL=INFO

# Feature Flags
ENABLE_KNOWLEDGE_RAG=true
ENABLE_AUTO_EXTRACTION=true
ENABLE_CODE_GRAPH=true
ENABLE_MEMORY_STORE=true
```

### Starting the Server

```bash
# Direct execution
python start_mcp.py

# Using uv
uv run mcp_server

# With custom config
MCP_LOG_LEVEL=DEBUG python start_mcp.py
```

### Client Configuration

Configure in Claude Desktop or VS Code settings:

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["/path/to/start_mcp.py"],
      "env": {
        "PYTHONPATH": "/path/to/codebase-rag"
      }
    }
  }
}
```

**VS Code** (settings.json):
```json
{
  "mcp.servers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["/path/to/start_mcp.py"]
    }
  }
}
```

## Use Cases

### 1. AI-Powered Code Assistant

**Tools Used**:
- `code_graph_ingest_repo`: Index codebase
- `code_graph_fulltext_search`: Find code
- `code_graph_impact_analysis`: Analyze changes
- `memory_store`: Remember decisions

**Workflow**:
1. Ingest repository
2. Ask questions about code
3. Analyze impact of changes
4. Save architectural decisions

### 2. Documentation Assistant

**Tools Used**:
- `add_directory`: Index documentation
- `query_knowledge`: Answer questions
- `search_similar_nodes`: Find related docs
- `suggest_memory_from_query`: Extract insights

**Workflow**:
1. Index documentation
2. Query for information
3. Get AI-generated answers
4. Save important findings

### 3. Development Memory

**Tools Used**:
- `add_memory`: Save knowledge
- `search_memories`: Find past decisions
- `extract_from_git_commit`: Mine commits
- `batch_extract_from_repository`: Auto-extract

**Workflow**:
1. Extract from git history
2. Mine code comments
3. Store decisions manually
4. Query when needed

### 4. Code Review Assistant

**Tools Used**:
- `code_graph_impact_analysis`: Analyze changes
- `query_knowledge`: Check documentation
- `search_memories`: Find conventions
- `extract_from_conversation`: Save findings

**Workflow**:
1. Analyze code changes
2. Check against documentation
3. Verify conventions
4. Save review insights

## Benefits of MCP Integration

### For Users

1. **Natural Language Interface**: Ask questions in plain English
2. **Context Awareness**: AI remembers project knowledge
3. **Automated Tasks**: Background processing of large operations
4. **Unified Experience**: Same tools across different AI assistants

### For Developers

1. **Standardized Protocol**: No custom API clients needed
2. **Tool Discovery**: AI automatically discovers available tools
3. **Type Safety**: JSON schemas for all tool inputs
4. **Error Handling**: Structured error responses

### For Organizations

1. **Vendor Independence**: Works with any MCP-compatible client
2. **Security**: Local execution, no data sent to external services
3. **Customization**: Easy to add new tools
4. **Integration**: Connects to existing infrastructure

## Security Considerations

### Data Privacy

- **Local Execution**: MCP server runs on your infrastructure
- **No External Calls**: Data stays in your network (with local LLM)
- **Access Control**: Implement authentication at proxy level

### Tool Permissions

Tools have different permission levels:

**Read-only tools**:
- `query_knowledge`
- `search_memories`
- `code_graph_fulltext_search`

**Write tools**:
- `add_document`
- `add_memory`
- `code_graph_ingest_repo`

**Destructive tools**:
- `delete_memory`
- `clear_knowledge_base`

**Best Practice**: Implement tool-level access control in production

### Network Security

```bash
# Run MCP server in isolated environment
docker run --network isolated-net mcp-server

# Use authentication proxy
nginx → (auth) → MCP server

# Restrict tool access by user
ALLOWED_TOOLS=query_knowledge,search_memories
```

## Performance Considerations

### Tool Execution Time

| Tool Category | Typical Time | Notes |
|--------------|--------------|-------|
| Query | 1-5s | Depends on LLM |
| Search | 100-500ms | Vector search |
| Memory | 50-200ms | Graph queries |
| Code Graph | 200ms-2s | Varies by size |
| Ingestion | 10s-5min | Background task |

### Concurrent Requests

The server handles concurrent requests:

```python
# Configure in server
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30  # seconds
```

### Caching Strategy

**Client-side caching**:
- Cache frequent queries
- Store tool schemas
- Cache project summaries

**Server-side caching**:
- Embedding cache
- Query result cache
- Graph query cache

## Monitoring and Debugging

### Server Logs

```bash
# View MCP server logs
tail -f mcp_server.log

# Enable debug logging
MCP_LOG_LEVEL=DEBUG python start_mcp.py
```

### Tool Call Tracing

Monitor tool calls:

```python
# Each tool call is logged
[INFO] Query: "How does auth work?" (mode: hybrid)
[INFO] Add memory: "Use JWT authentication" (project: myapp)
[INFO] Code ingest: /path/to/repo (mode: incremental)
```

### Health Monitoring

```bash
# Check MCP server health
python -c "from mcp_server import server; print(server.health_check())"

# Check backend services
curl http://localhost:8000/api/v1/health
```

## Limitations

### Current Limitations

1. **Single User**: No built-in multi-user support
2. **No Authentication**: Implement at proxy level
3. **Tool Discovery**: Static tool list (no runtime addition)
4. **Session Persistence**: In-memory only (no database)

### Planned Features

1. **Multi-user support**: User-specific contexts
2. **Tool marketplace**: Dynamically load tools
3. **Enhanced streaming**: Progress updates for long operations
4. **Webhook support**: External event notifications

## Comparison with Alternatives

### MCP vs REST API

| Feature | MCP | REST API |
|---------|-----|----------|
| Tool Discovery | Automatic | Manual |
| Type Safety | Built-in | Manual |
| Streaming | Native | SSE/WebSocket |
| AI Integration | Optimized | Generic |
| Learning Curve | Low | Medium |

### MCP vs Function Calling

| Feature | MCP | Function Calling |
|---------|-----|-----------------|
| Protocol | Standardized | Provider-specific |
| Transport | Multiple | HTTP only |
| Session Mgmt | Built-in | Manual |
| Tool Composability | High | Medium |

## Next Steps

- **[Claude Desktop Setup](claude-desktop.md)**: Configure Claude Desktop
- **[VS Code Setup](vscode.md)**: Configure VS Code extension
- **[Deployment Guide](../../deployment/full.md)**: Deploy MCP server
- **[Contributing Guide](../../development/contributing.md)**: Extend with custom tools

## Additional Resources

- **MCP Documentation**: https://modelcontextprotocol.io/
- **MCP SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop**: https://claude.ai/download
- **MCP Specification**: https://spec.modelcontextprotocol.io/
