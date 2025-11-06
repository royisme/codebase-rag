# MCP Tools Reference

Complete reference for all 30 Model Context Protocol (MCP) tools available in the Code Graph Knowledge System.

**MCP Server Version**: 2.0.0
**MCP Protocol Version**: 1.1.0
**Total Tools**: 30

## Overview

The MCP server provides AI assistants (like Claude Desktop, VS Code with MCP, etc.) with direct access to the Code Graph Knowledge System through the official Model Context Protocol SDK.

**Key Features**:
- 30 specialized tools across 6 categories
- Session management for tracking context
- Streaming support for long-running operations
- Multi-transport capability (stdio, SSE, WebSocket)
- Standard MCP protocol compliance

**Architecture**:
- Main server: `mcp_server.py` (310 lines - modular design)
- Tool handlers: `mcp_tools/` package (organized by category)
- Official SDK: `mcp>=1.1.0`

---

## Installation & Setup

### Start MCP Server

```bash
# Using start script
python start_mcp.py

# Using uv (recommended)
uv run mcp_client
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["/path/to/codebase-rag/start_mcp.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password"
      }
    }
  }
}
```

### VS Code MCP Extension

Configure in `.vscode/mcp.json`:

```json
{
  "servers": {
    "code-graph": {
      "command": "python /path/to/codebase-rag/start_mcp.py"
    }
  }
}
```

---

## Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **Knowledge Base** | 5 | Query and manage knowledge graph |
| **Code Graph** | 4 | Repository analysis and context |
| **Memory Store** | 7 | Project knowledge persistence |
| **Memory Extraction** | 5 | Automatic memory extraction (v0.7) |
| **Task Management** | 6 | Async task monitoring |
| **System** | 3 | Schema and statistics |

---

## Knowledge Base Tools (5)

Tools for querying and managing the knowledge graph.

### 1. query_knowledge

Query the knowledge base using Neo4j GraphRAG.

**Input Parameters**:
```typescript
{
  question: string;        // Required: Question to ask
  mode?: "hybrid" | "graph_only" | "vector_only";  // Default: "hybrid"
}
```

**Query Modes**:
- `hybrid` (recommended): Graph traversal + vector search
- `graph_only`: Use only graph relationships
- `vector_only`: Use only vector similarity

**Example**:
```json
{
  "question": "How does authentication work in this system?",
  "mode": "hybrid"
}
```

**Response**:
```json
{
  "success": true,
  "answer": "The system uses JWT-based authentication with refresh tokens...",
  "source_nodes": [
    {
      "text": "JWT implementation details...",
      "score": 0.92,
      "metadata": {"title": "Auth Guide"}
    }
  ],
  "mode": "hybrid"
}
```

---

### 2. search_similar_nodes

Search for similar nodes using vector similarity.

**Input Parameters**:
```typescript
{
  query: string;     // Required: Search query
  top_k?: number;    // Default: 10, Range: 1-50
}
```

**Example**:
```json
{
  "query": "database configuration",
  "top_k": 10
}
```

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "text": "Database connection settings...",
      "score": 0.89,
      "metadata": {"title": "Config Guide"}
    }
  ]
}
```

---

### 3. add_document

Add a document to the knowledge base.

**Input Parameters**:
```typescript
{
  content: string;       // Required: Document content
  title?: string;        // Optional: Document title
  metadata?: object;     // Optional: Additional metadata
}
```

**Size Handling**:
- **Small documents (<10KB)**: Processed synchronously
- **Large documents (>=10KB)**: Processed asynchronously with task_id

**Example**:
```json
{
  "content": "This is the document content with important information...",
  "title": "Architecture Guide",
  "metadata": {
    "author": "Team",
    "tags": ["architecture", "design"]
  }
}
```

**Response (Small)**:
```json
{
  "success": true,
  "message": "Document added successfully",
  "document_id": "doc-abc123",
  "chunks_created": 5
}
```

**Response (Large)**:
```json
{
  "success": true,
  "task_id": "task-xyz789",
  "message": "Document processing queued",
  "processing_async": true
}
```

---

### 4. add_file

Add a file to the knowledge base.

**Input Parameters**:
```typescript
{
  file_path: string;  // Required: Absolute path to file
}
```

**Supported file types**: Text files, code files, markdown, etc.

**Example**:
```json
{
  "file_path": "/absolute/path/to/document.md"
}
```

**Response**:
```json
{
  "success": true,
  "message": "File added successfully",
  "file_path": "/absolute/path/to/document.md",
  "chunks_created": 8
}
```

---

### 5. add_directory

Add all files from a directory to the knowledge base.

**Input Parameters**:
```typescript
{
  directory_path: string;   // Required: Absolute directory path
  recursive?: boolean;      // Default: true
}
```

**Example**:
```json
{
  "directory_path": "/absolute/path/to/docs",
  "recursive": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "Directory processed",
  "files_processed": 23,
  "total_chunks": 156
}
```

---

## Code Graph Tools (4)

Tools for repository analysis and code understanding.

### 1. code_graph_ingest_repo

Ingest a code repository into the graph database.

**Input Parameters**:
```typescript
{
  local_path: string;              // Required: Local repository path
  repo_url?: string;               // Optional: Repository URL
  mode?: "full" | "incremental";  // Default: "incremental"
}
```

**Ingestion Modes**:
- `full`: Complete re-ingestion (slow but thorough)
- `incremental`: Only changed files (60x faster)

**Extracts**:
- File nodes
- Symbol nodes (functions, classes)
- IMPORTS relationships
- Code structure

**Example**:
```json
{
  "local_path": "/path/to/repository",
  "mode": "incremental"
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "ing-20250115-103045-abc12345",
  "status": "done",
  "message": "Successfully ingested 125 files",
  "files_processed": 125,
  "mode": "incremental"
}
```

---

### 2. code_graph_related

Find files related to a query using fulltext search.

**Input Parameters**:
```typescript
{
  query: string;      // Required: Search query
  repo_id: string;    // Required: Repository identifier
  limit?: number;     // Default: 30, Range: 1-100
}
```

**Example**:
```json
{
  "query": "authentication jwt token",
  "repo_id": "myproject",
  "limit": 30
}
```

**Response**:
```json
{
  "nodes": [
    {
      "type": "file",
      "ref": "ref://file/src/auth/jwt.py",
      "path": "src/auth/jwt.py",
      "lang": "python",
      "score": 0.92,
      "summary": "JWT authentication implementation with token generation"
    }
  ],
  "query": "authentication jwt token",
  "repo_id": "myproject"
}
```

---

### 3. code_graph_impact

Analyze impact of changes to a file (reverse dependencies).

**Input Parameters**:
```typescript
{
  repo_id: string;      // Required: Repository identifier
  file_path: string;    // Required: File path to analyze
  depth?: number;       // Default: 2, Range: 1-5
}
```

**Use Cases**:
- Understanding blast radius of changes
- Finding code that needs updating
- Identifying critical files with many dependents

**Example**:
```json
{
  "repo_id": "myproject",
  "file_path": "src/auth/jwt.py",
  "depth": 2
}
```

**Response**:
```json
{
  "nodes": [
    {
      "type": "file",
      "path": "src/api/auth_routes.py",
      "lang": "python",
      "repoId": "myproject",
      "relationship": "IMPORTS",
      "depth": 1,
      "score": 0.85,
      "ref": "ref://file/src/api/auth_routes.py",
      "summary": "Auth API routes (imports jwt.py)"
    }
  ],
  "file": "src/auth/jwt.py",
  "repo_id": "myproject",
  "depth": 2
}
```

---

### 4. context_pack

Build a context pack for AI agents within token budget.

**Input Parameters**:
```typescript
{
  repo_id: string;                             // Required: Repository ID
  stage?: "plan" | "review" | "implement";    // Default: "implement"
  budget?: number;                             // Default: 1500, Range: 500-10000
  keywords?: string;                           // Optional: Focus keywords
  focus?: string;                              // Optional: Focus file paths
}
```

**Stages**:
- `plan`: Project overview and high-level architecture
- `review`: Code review focus with detailed analysis
- `implement`: Implementation details and code snippets

**Example**:
```json
{
  "repo_id": "myproject",
  "stage": "implement",
  "budget": 2000,
  "keywords": "authentication, jwt, middleware"
}
```

**Response**:
```json
{
  "items": [
    {
      "kind": "file",
      "title": "src/auth/jwt.py",
      "summary": "JWT authentication with token generation and validation",
      "ref": "ref://file/src/auth/jwt.py",
      "extra": {"lang": "python", "score": 0.92}
    }
  ],
  "budget_used": 1850,
  "budget_limit": 2000,
  "stage": "implement",
  "repo_id": "myproject"
}
```

---

## Memory Store Tools (7)

Tools for project knowledge persistence and management.

### 1. add_memory

Add a new memory to project knowledge base.

**Input Parameters**:
```typescript
{
  project_id: string;                          // Required
  memory_type: MemoryType;                     // Required
  title: string;                               // Required (max 200 chars)
  content: string;                             // Required
  reason?: string;                             // Optional: Rationale
  tags?: string[];                             // Optional: Tags
  importance?: number;                         // Default: 0.5, Range: 0-1
  related_refs?: string[];                     // Optional: ref:// handles
}

type MemoryType = "decision" | "preference" | "experience" | "convention" | "plan" | "note";
```

**Memory Types**:
- `decision`: Architecture choices, tech stack selection
- `preference`: Coding style, tool preferences
- `experience`: Problems encountered and solutions
- `convention`: Team rules, naming conventions
- `plan`: Future improvements, TODOs
- `note`: Other important information

**Example**:
```json
{
  "project_id": "myapp",
  "memory_type": "decision",
  "title": "Use JWT for authentication",
  "content": "Decided to use JWT tokens instead of session-based auth",
  "reason": "Need stateless authentication for mobile clients",
  "tags": ["auth", "architecture"],
  "importance": 0.9,
  "related_refs": ["ref://file/src/auth/jwt.py"]
}
```

**Response**:
```json
{
  "success": true,
  "memory_id": "mem-abc123-def456",
  "project_id": "myapp",
  "message": "Memory added successfully"
}
```

---

### 2. search_memories

Search project memories with filters.

**Input Parameters**:
```typescript
{
  project_id: string;           // Required
  query?: string;               // Optional: Search text
  memory_type?: MemoryType;     // Optional: Filter by type
  tags?: string[];              // Optional: Filter by tags
  min_importance?: number;      // Default: 0.0, Range: 0-1
  limit?: number;               // Default: 20, Range: 1-100
}
```

**Example**:
```json
{
  "project_id": "myapp",
  "query": "authentication security",
  "memory_type": "decision",
  "min_importance": 0.7,
  "limit": 20
}
```

**Response**:
```json
{
  "success": true,
  "memories": [
    {
      "memory_id": "mem-abc123",
      "memory_type": "decision",
      "title": "Use JWT for authentication",
      "content": "Decided to use JWT tokens...",
      "importance": 0.9,
      "tags": ["auth", "architecture"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

### 3. get_memory

Get a specific memory by ID with full details.

**Input Parameters**:
```typescript
{
  memory_id: string;  // Required
}
```

**Example**:
```json
{
  "memory_id": "mem-abc123-def456"
}
```

**Response**:
```json
{
  "success": true,
  "memory": {
    "memory_id": "mem-abc123",
    "project_id": "myapp",
    "memory_type": "decision",
    "title": "Use JWT for authentication",
    "content": "Decided to use JWT tokens...",
    "reason": "Need stateless authentication...",
    "tags": ["auth", "architecture"],
    "importance": 0.9,
    "related_refs": ["ref://file/src/auth/jwt.py"],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z",
    "is_superseded": false
  }
}
```

---

### 4. update_memory

Update an existing memory (partial update supported).

**Input Parameters**:
```typescript
{
  memory_id: string;        // Required
  title?: string;           // Optional
  content?: string;         // Optional
  reason?: string;          // Optional
  tags?: string[];          // Optional
  importance?: number;      // Optional: Range: 0-1
}
```

**Example**:
```json
{
  "memory_id": "mem-abc123",
  "importance": 0.95,
  "tags": ["auth", "security", "critical"]
}
```

**Response**:
```json
{
  "success": true,
  "message": "Memory updated successfully",
  "memory_id": "mem-abc123"
}
```

---

### 5. delete_memory

Delete a memory (soft delete - data retained).

**Input Parameters**:
```typescript
{
  memory_id: string;  // Required
}
```

**Example**:
```json
{
  "memory_id": "mem-abc123"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Memory deleted successfully",
  "memory_id": "mem-abc123"
}
```

---

### 6. supersede_memory

Create a new memory that supersedes an old one (preserves history).

**Input Parameters**:
```typescript
{
  old_memory_id: string;        // Required
  new_memory_type: MemoryType;  // Required
  new_title: string;            // Required
  new_content: string;          // Required
  new_reason?: string;          // Optional
  new_tags?: string[];          // Optional
  new_importance?: number;      // Default: 0.5, Range: 0-1
}
```

**Use Case**: When decisions change or better solutions are found.

**Example**:
```json
{
  "old_memory_id": "mem-abc123",
  "new_memory_type": "decision",
  "new_title": "Use PostgreSQL instead of MySQL",
  "new_content": "Switched to PostgreSQL for better JSON support",
  "new_reason": "Need advanced JSON querying capabilities",
  "new_importance": 0.8
}
```

**Response**:
```json
{
  "success": true,
  "old_memory_id": "mem-abc123",
  "new_memory_id": "mem-xyz789",
  "message": "Memory superseded successfully"
}
```

---

### 7. get_project_summary

Get summary of all memories for a project, organized by type.

**Input Parameters**:
```typescript
{
  project_id: string;  // Required
}
```

**Example**:
```json
{
  "project_id": "myapp"
}
```

**Response**:
```json
{
  "success": true,
  "project_id": "myapp",
  "total_memories": 42,
  "by_type": {
    "decision": {
      "count": 12,
      "top_memories": [
        {
          "memory_id": "mem-abc123",
          "title": "Use JWT for authentication",
          "importance": 0.9
        }
      ]
    },
    "preference": {"count": 8},
    "experience": {"count": 15},
    "convention": {"count": 5},
    "plan": {"count": 2}
  }
}
```

---

## Memory Extraction Tools (5)

Automatic memory extraction from various sources (v0.7).

### 1. extract_from_conversation

Extract memories from conversation using LLM analysis.

**Input Parameters**:
```typescript
{
  project_id: string;                 // Required
  conversation: Array<{               // Required
    role: string;
    content: string;
  }>;
  auto_save?: boolean;                // Default: false
}
```

**Auto-save**: If true, automatically saves memories with confidence >= 0.7

**Example**:
```json
{
  "project_id": "myapp",
  "conversation": [
    {"role": "user", "content": "Should we use Redis or Memcached?"},
    {"role": "assistant", "content": "Let's use Redis because it supports data persistence"}
  ],
  "auto_save": false
}
```

**Response**:
```json
{
  "success": true,
  "extracted_memories": [
    {
      "memory_type": "decision",
      "title": "Use Redis for caching",
      "content": "Decided to use Redis instead of Memcached",
      "reason": "Redis supports data persistence",
      "confidence": 0.85,
      "auto_saved": false,
      "memory_id": null
    }
  ],
  "total_extracted": 1,
  "auto_saved_count": 0
}
```

---

### 2. extract_from_git_commit

Extract memories from git commit using LLM analysis.

**Input Parameters**:
```typescript
{
  project_id: string;           // Required
  commit_sha: string;           // Required
  commit_message: string;       // Required
  changed_files: string[];      // Required
  auto_save?: boolean;          // Default: false
}
```

**Identifies**:
- Feature additions → `decision`
- Bug fixes → `experience`
- Refactoring → `experience`/`convention`
- Breaking changes → high importance `decision`

**Example**:
```json
{
  "project_id": "myapp",
  "commit_sha": "abc123def456",
  "commit_message": "feat: add JWT authentication\n\nImplemented JWT-based auth",
  "changed_files": ["src/auth/jwt.py", "src/middleware/auth.py"],
  "auto_save": true
}
```

**Response**:
```json
{
  "success": true,
  "extracted_memories": [
    {
      "memory_type": "decision",
      "title": "Implement JWT authentication",
      "content": "Added JWT-based authentication system",
      "confidence": 0.92,
      "auto_saved": true,
      "memory_id": "mem-xyz789"
    }
  ]
}
```

---

### 3. extract_from_code_comments

Extract memories from code comments in source file.

**Input Parameters**:
```typescript
{
  project_id: string;    // Required
  file_path: string;     // Required: Path to source file
}
```

**Marker Mappings**:
- `TODO:` → `plan`
- `FIXME:` / `BUG:` → `experience`
- `NOTE:` / `IMPORTANT:` → `convention`
- `DECISION:` → `decision`

**Example**:
```json
{
  "project_id": "myapp",
  "file_path": "/path/to/project/src/service.py"
}
```

**Response**:
```json
{
  "success": true,
  "extracted_memories": [
    {
      "memory_type": "plan",
      "title": "TODO: Add rate limiting",
      "content": "Need to implement rate limiting for API endpoints",
      "line_number": 45,
      "auto_saved": true,
      "memory_id": "mem-plan123"
    }
  ],
  "total_extracted": 1
}
```

---

### 4. suggest_memory_from_query

Suggest creating memory from knowledge base query.

**Input Parameters**:
```typescript
{
  project_id: string;    // Required
  query: string;         // Required: User query
  answer: string;        // Required: LLM answer
}
```

**Use Cases**:
- Frequently asked questions
- Important architectural information
- Non-obvious solutions or workarounds

**Example**:
```json
{
  "project_id": "myapp",
  "query": "How does the authentication work?",
  "answer": "The system uses JWT tokens with refresh token rotation..."
}
```

**Response**:
```json
{
  "success": true,
  "should_save": true,
  "confidence": 0.88,
  "suggested_memory": {
    "memory_type": "note",
    "title": "Authentication mechanism",
    "content": "System uses JWT with refresh token rotation",
    "importance": 0.7
  }
}
```

---

### 5. batch_extract_from_repository

Batch extract memories from entire repository.

**Input Parameters**:
```typescript
{
  project_id: string;           // Required
  repo_path: string;            // Required: Path to git repo
  max_commits?: number;         // Default: 50, Range: 1-200
  file_patterns?: string[];     // Optional: e.g., ["*.py", "*.js"]
}
```

**Analyzes**:
- Recent git commits (configurable count)
- Code comments in source files
- Documentation files (README, CHANGELOG, etc.)

**Note**: Long-running operation (may take several minutes).

**Example**:
```json
{
  "project_id": "myapp",
  "repo_path": "/path/to/repository",
  "max_commits": 50,
  "file_patterns": ["*.py", "*.js"]
}
```

**Response**:
```json
{
  "success": true,
  "summary": {
    "commits_analyzed": 50,
    "files_scanned": 125,
    "total_extracted": 23,
    "by_source": {
      "git_commits": 12,
      "code_comments": 11
    },
    "by_type": {
      "decision": 5,
      "experience": 8,
      "plan": 10
    }
  },
  "execution_time_seconds": 45.2
}
```

---

## Task Management Tools (6)

Tools for monitoring asynchronous task execution.

### 1. get_task_status

Get status of a specific task.

**Input Parameters**:
```typescript
{
  task_id: string;  // Required
}
```

**Example**:
```json
{
  "task_id": "task-abc123"
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "task-abc123",
  "status": "SUCCESS",
  "progress": 100.0,
  "message": "Task completed successfully",
  "result": {
    "chunks_created": 15
  }
}
```

**Status Values**: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`, `CANCELLED`

---

### 2. watch_task

Monitor a task in real-time until completion (with timeout).

**Input Parameters**:
```typescript
{
  task_id: string;           // Required
  timeout?: number;          // Default: 300, Range: 10-600 (seconds)
  poll_interval?: number;    // Default: 2, Range: 1-10 (seconds)
}
```

**Example**:
```json
{
  "task_id": "task-abc123",
  "timeout": 300,
  "poll_interval": 2
}
```

**Response** (Streaming):
```json
{
  "success": true,
  "task_id": "task-abc123",
  "final_status": "SUCCESS",
  "progress_history": [
    {"timestamp": "2025-01-15T10:30:00Z", "progress": 0.0, "status": "PENDING"},
    {"timestamp": "2025-01-15T10:30:05Z", "progress": 25.0, "status": "PROCESSING"},
    {"timestamp": "2025-01-15T10:30:10Z", "progress": 100.0, "status": "SUCCESS"}
  ],
  "result": {"chunks_created": 15}
}
```

---

### 3. watch_tasks

Monitor multiple tasks until all complete.

**Input Parameters**:
```typescript
{
  task_ids: string[];        // Required
  timeout?: number;          // Default: 300, Range: 10-600
  poll_interval?: number;    // Default: 2, Range: 1-10
}
```

**Example**:
```json
{
  "task_ids": ["task-abc123", "task-xyz789"],
  "timeout": 300,
  "poll_interval": 2
}
```

**Response**:
```json
{
  "success": true,
  "tasks": {
    "task-abc123": {
      "status": "SUCCESS",
      "progress": 100.0,
      "result": {"chunks_created": 15}
    },
    "task-xyz789": {
      "status": "SUCCESS",
      "progress": 100.0,
      "result": {"chunks_created": 22}
    }
  },
  "all_completed": true
}
```

---

### 4. list_tasks

List tasks with optional status filter.

**Input Parameters**:
```typescript
{
  status_filter?: "pending" | "running" | "completed" | "failed";
  limit?: number;  // Default: 20, Range: 1-100
}
```

**Example**:
```json
{
  "status_filter": "running",
  "limit": 20
}
```

**Response**:
```json
{
  "success": true,
  "tasks": [
    {
      "task_id": "task-abc123",
      "status": "PROCESSING",
      "progress": 45.0,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 2
}
```

---

### 5. cancel_task

Cancel a pending or running task.

**Input Parameters**:
```typescript
{
  task_id: string;  // Required
}
```

**Example**:
```json
{
  "task_id": "task-abc123"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Task cancelled successfully",
  "task_id": "task-abc123"
}
```

---

### 6. get_queue_stats

Get task queue statistics.

**Input Parameters**: None

**Example**:
```json
{}
```

**Response**:
```json
{
  "success": true,
  "pending": 5,
  "running": 2,
  "completed": 142,
  "failed": 6,
  "total": 155,
  "queue_active": true
}
```

---

## System Tools (3)

System information and management tools.

### 1. get_graph_schema

Get Neo4j graph schema (node labels, relationship types, statistics).

**Input Parameters**: None

**Example**:
```json
{}
```

**Response**:
```json
{
  "success": true,
  "node_labels": ["Document", "Chunk", "Entity", "Memory", "Project", "File", "Repo"],
  "relationship_types": ["HAS_CHUNK", "MENTIONS", "RELATES_TO", "BELONGS_TO"],
  "statistics": {
    "node_count": 1523,
    "relationship_count": 4567
  }
}
```

---

### 2. get_statistics

Get knowledge base statistics.

**Input Parameters**: None

**Example**:
```json
{}
```

**Response**:
```json
{
  "success": true,
  "total_nodes": 1523,
  "total_relationships": 4567,
  "document_count": 45,
  "chunk_count": 892,
  "entity_count": 586,
  "memory_count": 42,
  "file_count": 125
}
```

---

### 3. clear_knowledge_base

**⚠️ DANGEROUS**: Clear all data from knowledge base.

**Input Parameters**:
```typescript
{
  confirmation: string;  // Required: Must be "yes"
}
```

**Example**:
```json
{
  "confirmation": "yes"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Knowledge base cleared",
  "nodes_deleted": 1523,
  "relationships_deleted": 4567
}
```

---

## Resources

MCP resources provide dynamic data access.

### Available Resources

1. **knowledge://config** - System configuration and settings
2. **knowledge://status** - Current system status and health

**Access via MCP**: Resources are accessed through the MCP protocol, not as tools.

---

## Prompts

MCP prompts provide query suggestions.

### suggest_queries

Generate suggested queries for the knowledge graph.

**Arguments**:
- `domain`: Domain to focus on (general, code, documentation, sql, architecture)

**Example Domains**:
- `general`: General system questions
- `code`: Code-specific queries
- `documentation`: Documentation queries
- `sql`: Database schema queries
- `architecture`: Architecture questions

---

## Error Handling

All tools follow consistent error response format.

### Success Response

```json
{
  "success": true,
  "...": "tool-specific data"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Detailed error message",
  "error_type": "ValidationError | NotFoundError | ServiceError"
}
```

### Common Error Types

**Validation Error**:
```json
{
  "success": false,
  "error": "Invalid memory_type. Must be one of: decision, preference, experience, convention, plan, note"
}
```

**Not Found Error**:
```json
{
  "success": false,
  "error": "Memory not found: mem-abc123"
}
```

**Service Error**:
```json
{
  "success": false,
  "error": "Failed to connect to Neo4j database"
}
```

---

## Best Practices

### Memory Management

1. **Importance Scoring**:
   - 0.9-1.0: Critical decisions, security findings
   - 0.7-0.8: Important architectural choices
   - 0.5-0.6: Preferences and conventions
   - 0.3-0.4: Plans and future work

2. **Tagging Strategy**:
   - Use domain tags: `auth`, `database`, `api`
   - Use type tags: `security`, `performance`, `bug`
   - Use status tags: `critical`, `deprecated`

3. **When to Use Extraction**:
   - Use `extract_from_conversation` for Q&A sessions
   - Use `extract_from_git_commit` for commit hooks
   - Use `extract_from_code_comments` for code reviews
   - Use `batch_extract_from_repository` for initial setup

### Task Monitoring

1. Use `watch_task` for single long-running operations
2. Use `watch_tasks` for batch operations
3. Set appropriate timeouts based on operation size
4. Use `cancel_task` to stop unnecessary work

### Code Graph

1. Use `incremental` mode for regular updates (60x faster)
2. Use `full` mode for initial ingestion or major changes
3. Use `context_pack` to stay within token limits
4. Use `impact` analysis before making changes

---

**Last Updated**: 2025-01-15
**MCP Server Version**: 2.0.0
**Total Tools**: 30
