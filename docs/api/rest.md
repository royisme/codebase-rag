# REST API Reference

Complete reference for Code Graph Knowledge System REST API endpoints.

**Base URL**: `http://localhost:8000/api/v1`

**Version**: 1.0.0

## Authentication

Currently, the API does not require authentication. This may be added in future versions.

---

## Health & System

### Get Health Status

Get system health and service status.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "neo4j_knowledge_service": true,
    "graph_service": true,
    "task_queue": true
  },
  "version": "0.1.0"
}
```

### Get System Configuration

Get current system configuration.

**Endpoint**: `GET /config`

**Response**:
```json
{
  "app_name": "Code Graph Knowledge System",
  "version": "0.1.0",
  "debug": false,
  "llm_provider": "ollama",
  "embedding_provider": "ollama",
  "monitoring_enabled": true
}
```

### Get Graph Schema

Get Neo4j graph schema information.

**Endpoint**: `GET /schema`

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

### Get Statistics

Get knowledge base statistics.

**Endpoint**: `GET /statistics`

**Response**:
```json
{
  "success": true,
  "total_nodes": 1523,
  "total_relationships": 4567,
  "document_count": 45,
  "chunk_count": 892,
  "entity_count": 586
}
```

### Get Prometheus Metrics

Get system metrics in Prometheus format.

**Endpoint**: `GET /metrics`

**Response**: Plain text Prometheus metrics
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health"} 1234

# HELP neo4j_nodes_total Total nodes in Neo4j
# TYPE neo4j_nodes_total gauge
neo4j_nodes_total 1523
```

### Clear Knowledge Base

**⚠️ DANGEROUS**: Clear all data from knowledge base.

**Endpoint**: `DELETE /clear`

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

## Knowledge Base

### Query Knowledge Base

Query the knowledge base using GraphRAG.

**Endpoint**: `POST /knowledge/query`

**Request Body**:
```json
{
  "question": "How does authentication work in this system?",
  "mode": "hybrid"
}
```

**Parameters**:
- `question` (string, required): Question to ask
- `mode` (string, optional): Query mode
  - `hybrid` (default): Graph traversal + vector search
  - `graph_only`: Only graph relationships
  - `vector_only`: Only vector similarity

**Response**:
```json
{
  "success": true,
  "answer": "The system uses JWT-based authentication...",
  "source_nodes": [
    {
      "text": "JWT implementation details...",
      "score": 0.92,
      "metadata": {
        "title": "Authentication Guide",
        "source": "docs/auth.md"
      }
    }
  ],
  "mode": "hybrid"
}
```

### Search Similar Nodes

Search for similar nodes using vector similarity.

**Endpoint**: `POST /knowledge/search`

**Request Body**:
```json
{
  "query": "database configuration",
  "top_k": 10
}
```

**Parameters**:
- `query` (string, required): Search query
- `top_k` (integer, optional): Number of results (default: 10, max: 50)

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "text": "Database connection settings...",
      "score": 0.89,
      "metadata": {
        "title": "Configuration Guide",
        "type": "document"
      }
    }
  ],
  "query": "database configuration",
  "top_k": 10
}
```

### Add Document

Add a document to knowledge base.

**Endpoint**: `POST /documents`

**Request Body**:
```json
{
  "content": "This is the document content...",
  "title": "My Document",
  "metadata": {
    "author": "John Doe",
    "tags": ["tutorial", "api"]
  }
}
```

**Parameters**:
- `content` (string, required): Document content
- `title` (string, optional): Document title
- `metadata` (object, optional): Additional metadata

**Response**:
```json
{
  "success": true,
  "message": "Document added successfully",
  "document_id": "doc-abc123",
  "chunks_created": 5
}
```

**Note**: Large documents (>10KB) are processed asynchronously and return a task_id.

### Add File

Add a file to knowledge base.

**Endpoint**: `POST /documents/file`

**Request Body**:
```json
{
  "file_path": "/absolute/path/to/file.txt"
}
```

**Parameters**:
- `file_path` (string, required): Absolute path to file

**Response**:
```json
{
  "success": true,
  "message": "File added successfully",
  "file_path": "/absolute/path/to/file.txt",
  "chunks_created": 8
}
```

### Add Directory

Add all files from directory to knowledge base.

**Endpoint**: `POST /documents/directory`

**Request Body**:
```json
{
  "directory_path": "/absolute/path/to/directory",
  "recursive": true,
  "file_patterns": ["*.md", "*.txt"]
}
```

**Parameters**:
- `directory_path` (string, required): Absolute directory path
- `recursive` (boolean, optional): Process subdirectories (default: true)
- `file_patterns` (array, optional): File patterns to include

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

## Memory Management

Memory Store provides project knowledge persistence for AI agents.

### Add Memory

Add a new memory to project knowledge base.

**Endpoint**: `POST /memory/add`

**Request Body**:
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

**Parameters**:
- `project_id` (string, required): Project identifier
- `memory_type` (string, required): Type of memory
  - `decision`: Architecture choices, tech stack
  - `preference`: Coding style, tool preferences
  - `experience`: Problems and solutions
  - `convention`: Team rules, naming patterns
  - `plan`: Future improvements, TODOs
  - `note`: Other important information
- `title` (string, required): Short title (max 200 chars)
- `content` (string, required): Detailed content
- `reason` (string, optional): Rationale or explanation
- `tags` (array, optional): Tags for categorization
- `importance` (number, optional): Importance score 0-1 (default: 0.5)
- `related_refs` (array, optional): Related ref:// handles

**Response**:
```json
{
  "success": true,
  "memory_id": "mem-abc123-def456",
  "project_id": "myapp",
  "message": "Memory added successfully"
}
```

### Search Memories

Search project memories with filters.

**Endpoint**: `POST /memory/search`

**Request Body**:
```json
{
  "project_id": "myapp",
  "query": "authentication",
  "memory_type": "decision",
  "tags": ["auth"],
  "min_importance": 0.7,
  "limit": 20
}
```

**Parameters**:
- `project_id` (string, required): Project identifier
- `query` (string, optional): Search query text
- `memory_type` (string, optional): Filter by memory type
- `tags` (array, optional): Filter by tags
- `min_importance` (number, optional): Minimum importance (default: 0.0)
- `limit` (integer, optional): Max results (default: 20, max: 100)

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
      "reason": "Need stateless authentication...",
      "tags": ["auth", "architecture"],
      "importance": 0.9,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "query": "authentication"
}
```

### Get Memory

Get a specific memory by ID.

**Endpoint**: `GET /memory/{memory_id}`

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
    "is_superseded": false,
    "superseded_by": null
  }
}
```

### Update Memory

Update an existing memory.

**Endpoint**: `PUT /memory/{memory_id}`

**Request Body**:
```json
{
  "title": "Updated title",
  "importance": 0.95,
  "tags": ["auth", "security", "critical"]
}
```

**Parameters**: All fields are optional, only provided fields will be updated
- `title` (string): Update title
- `content` (string): Update content
- `reason` (string): Update reason
- `tags` (array): Update tags
- `importance` (number): Update importance

**Response**:
```json
{
  "success": true,
  "message": "Memory updated successfully",
  "memory_id": "mem-abc123"
}
```

### Delete Memory

Delete a memory (soft delete).

**Endpoint**: `DELETE /memory/{memory_id}`

**Response**:
```json
{
  "success": true,
  "message": "Memory deleted successfully",
  "memory_id": "mem-abc123"
}
```

### Supersede Memory

Create a new memory that supersedes an old one.

**Endpoint**: `POST /memory/supersede`

**Request Body**:
```json
{
  "old_memory_id": "mem-abc123",
  "new_memory_type": "decision",
  "new_title": "Use PostgreSQL instead of MySQL",
  "new_content": "Switched to PostgreSQL for better JSON support",
  "new_reason": "Need advanced JSON querying capabilities",
  "new_tags": ["database", "architecture"],
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

### Get Project Summary

Get summary of all memories for a project.

**Endpoint**: `GET /memory/project/{project_id}/summary`

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
          "importance": 0.9,
          "created_at": "2025-01-15T10:30:00Z"
        }
      ]
    },
    "preference": {"count": 8, "top_memories": []},
    "experience": {"count": 15, "top_memories": []},
    "convention": {"count": 5, "top_memories": []},
    "plan": {"count": 2, "top_memories": []}
  }
}
```

### Memory Health Check

Check memory store health.

**Endpoint**: `GET /memory/health`

**Response**:
```json
{
  "service": "memory_store",
  "status": "healthy",
  "initialized": true,
  "extraction_enabled": true
}
```

---

## Memory Extraction (v0.7)

Automatic memory extraction from various sources.

### Extract from Conversation

Extract memories from conversation using LLM analysis.

**Endpoint**: `POST /memory/extract/conversation`

**Request Body**:
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

**Parameters**:
- `project_id` (string, required): Project identifier
- `conversation` (array, required): Conversation messages
- `auto_save` (boolean, optional): Auto-save high-confidence memories (default: false)

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

### Extract from Git Commit

Extract memories from git commit using LLM analysis.

**Endpoint**: `POST /memory/extract/commit`

**Request Body**:
```json
{
  "project_id": "myapp",
  "commit_sha": "abc123def456",
  "commit_message": "feat: add JWT authentication\n\nImplemented JWT-based auth for stateless API",
  "changed_files": ["src/auth/jwt.py", "src/middleware/auth.py"],
  "auto_save": true
}
```

**Parameters**:
- `project_id` (string, required): Project identifier
- `commit_sha` (string, required): Git commit SHA
- `commit_message` (string, required): Full commit message
- `changed_files` (array, required): List of changed file paths
- `auto_save` (boolean, optional): Auto-save high-confidence memories

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

### Extract from Code Comments

Extract memories from code comments in source file.

**Endpoint**: `POST /memory/extract/comments`

**Request Body**:
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

### Suggest Memory from Query

Suggest creating memory from knowledge base query.

**Endpoint**: `POST /memory/suggest`

**Request Body**:
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

### Batch Extract from Repository

Batch extract memories from entire repository.

**Endpoint**: `POST /memory/extract/batch`

**Request Body**:
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

## Code Graph

Code graph analysis endpoints for repository understanding.

### Ingest Repository

Ingest a code repository into the graph database.

**Endpoint**: `POST /ingest/repo`

**Request Body**:
```json
{
  "local_path": "/path/to/repository",
  "repo_url": null,
  "branch": "main",
  "mode": "incremental",
  "include_globs": ["**/*.py", "**/*.ts", "**/*.tsx"],
  "exclude_globs": ["**/node_modules/**", "**/.git/**"],
  "since_commit": null
}
```

**Parameters**:
- `local_path` (string, optional): Local repository path
- `repo_url` (string, optional): Repository URL to clone
- `branch` (string, optional): Branch name (default: "main")
- `mode` (string, optional): Ingestion mode
  - `full`: Complete re-ingestion
  - `incremental`: Only changed files (60x faster)
- `include_globs` (array, optional): File patterns to include
- `exclude_globs` (array, optional): File patterns to exclude
- `since_commit` (string, optional): For incremental mode

**Response**:
```json
{
  "task_id": "ing-20250115-103045-abc12345",
  "status": "done",
  "message": "Successfully ingested 125 files",
  "files_processed": 125,
  "mode": "incremental",
  "changed_files_count": 8
}
```

### Get Related Files

Find files related to a query using fulltext search.

**Endpoint**: `GET /graph/related?query={query}&repoId={repoId}&limit={limit}`

**Parameters**:
- `query` (string, required): Search query
- `repoId` (string, required): Repository identifier
- `limit` (integer, optional): Max results (default: 30, max: 100)

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
      "summary": "JWT authentication implementation"
    }
  ],
  "query": "authentication",
  "repo_id": "myproject"
}
```

### Impact Analysis

Analyze impact of changes to a file (reverse dependencies).

**Endpoint**: `GET /graph/impact?repoId={repoId}&file={file}&depth={depth}&limit={limit}`

**Parameters**:
- `repoId` (string, required): Repository identifier
- `file` (string, required): File path to analyze
- `depth` (integer, optional): Traversal depth (default: 2, max: 5)
- `limit` (integer, optional): Max results (default: 50, max: 100)

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

### Context Pack

Build a context pack within token budget.

**Endpoint**: `GET /context/pack?repoId={repoId}&stage={stage}&budget={budget}&keywords={keywords}&focus={focus}`

**Parameters**:
- `repoId` (string, required): Repository identifier
- `stage` (string, optional): Development stage (default: "plan")
  - `plan`: Project overview
  - `review`: Code review focus
  - `implement`: Implementation details
- `budget` (integer, optional): Token budget (default: 1500, max: 10000)
- `keywords` (string, optional): Comma-separated keywords
- `focus` (string, optional): Comma-separated focus paths

**Response**:
```json
{
  "items": [
    {
      "kind": "file",
      "title": "src/auth/jwt.py",
      "summary": "JWT authentication implementation with token generation and validation",
      "ref": "ref://file/src/auth/jwt.py",
      "extra": {
        "lang": "python",
        "score": 0.92
      }
    }
  ],
  "budget_used": 1450,
  "budget_limit": 1500,
  "stage": "implement",
  "repo_id": "myproject",
  "category_counts": {
    "file": 8,
    "symbol": 12
  }
}
```

---

## Task Management

Asynchronous task queue management.

### Create Task

Create a new task.

**Endpoint**: `POST /tasks/`

**Request Body**:
```json
{
  "task_type": "document_processing",
  "task_name": "Process large document",
  "payload": {
    "document_content": "...",
    "title": "Large Doc"
  },
  "priority": 0,
  "metadata": {
    "source": "api"
  }
}
```

**Valid task types**:
- `document_processing`
- `schema_parsing`
- `knowledge_graph_construction`
- `batch_processing`

**Response**:
```json
{
  "task_id": "task-abc123",
  "status": "created"
}
```

### Get Task Status

Get status of a specific task.

**Endpoint**: `GET /tasks/{task_id}`

**Response**:
```json
{
  "task_id": "task-abc123",
  "status": "SUCCESS",
  "progress": 100.0,
  "message": "Task completed successfully",
  "result": {
    "chunks_created": 15,
    "document_id": "doc-xyz789"
  },
  "error": null,
  "created_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:30:05Z",
  "completed_at": "2025-01-15T10:30:45Z",
  "metadata": {
    "source": "api"
  }
}
```

**Status values**:
- `PENDING`: Waiting in queue
- `PROCESSING`: Currently running
- `SUCCESS`: Completed successfully
- `FAILED`: Failed with error
- `CANCELLED`: Cancelled by user

### List Tasks

List tasks with optional filtering.

**Endpoint**: `GET /tasks/?status={status}&page={page}&page_size={page_size}&task_type={task_type}`

**Parameters**:
- `status` (string, optional): Filter by status
- `page` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Page size (default: 20, max: 100)
- `task_type` (string, optional): Filter by task type

**Response**:
```json
{
  "tasks": [
    {
      "task_id": "task-abc123",
      "status": "SUCCESS",
      "progress": 100.0,
      "message": "Completed",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### Cancel Task

Cancel a pending or running task.

**Endpoint**: `DELETE /tasks/{task_id}`

**Response**:
```json
{
  "message": "Task cancelled successfully",
  "task_id": "task-abc123"
}
```

### Get Task Statistics

Get task queue statistics.

**Endpoint**: `GET /tasks/stats/overview`

**Response**:
```json
{
  "total_tasks": 156,
  "pending_tasks": 5,
  "processing_tasks": 2,
  "completed_tasks": 142,
  "failed_tasks": 6,
  "cancelled_tasks": 1
}
```

### Retry Task

Retry a failed or cancelled task.

**Endpoint**: `POST /tasks/{task_id}/retry`

**Response**:
```json
{
  "message": "Task retried successfully",
  "original_task_id": "task-abc123",
  "new_task_id": "task-xyz789"
}
```

### Get Queue Status

Get current queue status.

**Endpoint**: `GET /tasks/queue/status`

**Response**:
```json
{
  "running_tasks": 2,
  "max_concurrent_tasks": 5,
  "available_slots": 3,
  "queue_active": true
}
```

---

## SQL Parsing

SQL parsing and analysis endpoints.

### Parse SQL Statement

Parse and analyze SQL statement.

**Endpoint**: `POST /sql/parse`

**Request Body**:
```json
{
  "sql": "SELECT * FROM users WHERE id = 1",
  "dialect": "mysql"
}
```

**Supported dialects**: `mysql`, `postgresql`, `oracle`, `sqlserver`

**Response**:
```json
{
  "success": true,
  "parsed": {
    "statement_type": "SELECT",
    "tables": ["users"],
    "columns": ["*"],
    "where_conditions": ["id = 1"]
  }
}
```

### Validate SQL Syntax

Validate SQL syntax.

**Endpoint**: `POST /sql/validate`

**Request Body**:
```json
{
  "sql": "SELECT * FROM users",
  "dialect": "mysql"
}
```

**Response**:
```json
{
  "valid": true,
  "errors": []
}
```

### Convert SQL Dialect

Convert SQL between dialects.

**Endpoint**: `POST /sql/convert?sql={sql}&from_dialect={from}&to_dialect={to}`

**Response**:
```json
{
  "success": true,
  "original_sql": "SELECT * FROM users LIMIT 10",
  "converted_sql": "SELECT TOP 10 * FROM users",
  "from_dialect": "mysql",
  "to_dialect": "sqlserver"
}
```

### Parse SQL Schema

Parse SQL schema with auto-detection.

**Endpoint**: `POST /sql/parse-schema`

**Request Body**:
```json
{
  "schema_content": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));",
  "file_path": null
}
```

**Response**:
```json
{
  "success": true,
  "dialect": "mysql",
  "tables": [
    {
      "name": "users",
      "columns": [
        {"name": "id", "type": "INT", "primary_key": true},
        {"name": "name", "type": "VARCHAR(100)", "primary_key": false}
      ]
    }
  ],
  "relationships": []
}
```

---

## Real-time Monitoring (SSE)

Server-Sent Events for real-time task monitoring.

### Monitor Single Task

Stream updates for a specific task.

**Endpoint**: `GET /sse/task/{task_id}`

**Response**: SSE stream
```
data: {"task_id": "task-abc123", "status": "PROCESSING", "progress": 25.0}

data: {"task_id": "task-abc123", "status": "PROCESSING", "progress": 50.0}

data: {"task_id": "task-abc123", "status": "SUCCESS", "progress": 100.0}
```

### Monitor All Tasks

Stream updates for all tasks.

**Endpoint**: `GET /sse/tasks?status={status}`

**Parameters**:
- `status` (string, optional): Filter by status

**Response**: SSE stream
```
data: {"event": "task_update", "task_id": "task-1", "status": "PROCESSING"}

data: {"event": "task_update", "task_id": "task-2", "status": "SUCCESS"}
```

### Get SSE Statistics

Get active SSE connection statistics.

**Endpoint**: `GET /sse/stats`

**Response**:
```json
{
  "active_connections": 5,
  "task_streams": 3,
  "global_streams": 2
}
```

---

## Error Handling

All endpoints follow consistent error response format.

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Common Errors

**Invalid Parameters**:
```json
{
  "detail": "Invalid task type. Must be one of: document_processing, schema_parsing, knowledge_graph_construction, batch_processing"
}
```

**Resource Not Found**:
```json
{
  "detail": "Task not found"
}
```

**Service Error**:
```json
{
  "detail": "Failed to initialize Neo4j connection"
}
```

---

## Rate Limits

Currently no rate limits are enforced. This may change in future versions.

## Pagination

Endpoints that return lists support pagination:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

Response includes:
- `total`: Total item count
- `page`: Current page
- `page_size`: Items per page

---

**Last Updated**: 2025-01-15
**API Version**: 1.0.0
**Documentation Version**: 1.0
