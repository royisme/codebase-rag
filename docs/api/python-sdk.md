# Python SDK Guide

Complete guide for using Code Graph Knowledge System services directly in Python applications.

**Version**: 1.0.0

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Core Services](#core-services)
- [Neo4jKnowledgeService](#neo4jknowledgeservice)
- [MemoryStore](#memorystore)
- [GraphService](#graphservice)
- [CodeIngestor](#codeingestor)
- [TaskQueue](#taskqueue)
- [Configuration](#configuration)
- [Examples](#examples)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Overview

The Python SDK provides direct access to all system services without going through REST API or MCP. This is ideal for:

- Building custom integrations
- Embedding knowledge graph capabilities in applications
- Batch processing scripts
- Custom AI agents
- Testing and development

**Key Services**:
- `Neo4jKnowledgeService`: Knowledge graph and RAG
- `MemoryStore`: Project memory persistence
- `GraphService`: Low-level Neo4j operations
- `CodeIngestor`: Repository ingestion
- `TaskQueue`: Asynchronous task management

---

## Installation

### Requirements

```bash
# Python 3.10+
python --version

# Install dependencies
pip install -e .

# Or with uv (recommended)
uv pip install -e .
```

### Dependencies

```python
# Core dependencies
neo4j>=5.0.0
llama-index-core>=0.10.0
llama-index-graph-stores-neo4j>=0.2.0
fastapi>=0.104.0
pydantic>=2.0.0
```

### Environment Setup

Create `.env` file:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# LLM Provider (ollama/openai/gemini/openrouter)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Embedding Provider
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# Optional: OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# Optional: Google Gemini
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-pro

# Optional: OpenRouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=anthropic/claude-3-opus
```

---

## Core Services

### Import Services

```python
from src.codebase_rag.services.knowledge import Neo4jKnowledgeService
from src.codebase_rag.services.memory import MemoryStore, memory_store
from src.codebase_rag.services.code import Neo4jGraphService, graph_service
from src.codebase_rag.services.code import CodeIngestor, get_code_ingestor
from src.codebase_rag.services.tasks import TaskQueue, task_queue
from src.codebase_rag.config import settings
```

### Service Initialization Pattern

All services follow async initialization:

```python
import asyncio

async def main():
    # Create service instance
    service = Neo4jKnowledgeService()

    # Initialize (connect to Neo4j, setup LLM, etc.)
    success = await service.initialize()

    if not success:
        print("Failed to initialize service")
        return

    # Use service
    result = await service.query("How does this work?")
    print(result)

asyncio.run(main())
```

---

## Neo4jKnowledgeService

Primary service for knowledge graph operations with LlamaIndex integration.

### Initialization

```python
from src.codebase_rag.services.knowledge import Neo4jKnowledgeService

# Create instance
knowledge_service = Neo4jKnowledgeService()

# Initialize (async)
await knowledge_service.initialize()
```

### Key Methods

#### query()

Query knowledge base using GraphRAG.

```python
async def query(
    question: str,
    mode: str = "hybrid"
) -> Dict[str, Any]:
    """
    Query knowledge base.

    Args:
        question: Question to ask
        mode: "hybrid" | "graph_only" | "vector_only"

    Returns:
        {
            "success": bool,
            "answer": str,
            "source_nodes": List[Dict],
            "mode": str
        }
    """
```

**Example**:
```python
result = await knowledge_service.query(
    question="How does authentication work?",
    mode="hybrid"
)

if result["success"]:
    print(f"Answer: {result['answer']}")
    print(f"Sources: {len(result['source_nodes'])}")
```

#### search_similar_nodes()

Vector similarity search.

```python
async def search_similar_nodes(
    query: str,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Search similar nodes using vector similarity.

    Args:
        query: Search query
        top_k: Number of results (1-50)

    Returns:
        {
            "success": bool,
            "results": List[Dict],
            "query": str
        }
    """
```

**Example**:
```python
result = await knowledge_service.search_similar_nodes(
    query="database configuration",
    top_k=10
)

for node in result["results"]:
    print(f"Score: {node['score']:.2f} - {node['text'][:100]}")
```

#### add_document()

Add document to knowledge base.

```python
async def add_document(
    content: str,
    title: str = "Untitled",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add document to knowledge base.

    Args:
        content: Document content
        title: Document title
        metadata: Additional metadata

    Returns:
        {
            "success": bool,
            "document_id": str,
            "chunks_created": int
        }
    """
```

**Example**:
```python
result = await knowledge_service.add_document(
    content="""
    Authentication System Design

    The system uses JWT tokens for stateless authentication.
    Refresh tokens are stored in Redis with 7-day expiration.
    """,
    title="Auth Design",
    metadata={
        "author": "Team",
        "tags": ["auth", "design"]
    }
)

print(f"Document ID: {result['document_id']}")
print(f"Chunks created: {result['chunks_created']}")
```

#### add_file()

Add file to knowledge base.

```python
async def add_file(
    file_path: str
) -> Dict[str, Any]:
    """
    Add file to knowledge base.

    Args:
        file_path: Absolute path to file

    Returns:
        {
            "success": bool,
            "file_path": str,
            "chunks_created": int
        }
    """
```

**Example**:
```python
result = await knowledge_service.add_file(
    file_path="/path/to/documentation.md"
)
```

#### add_directory()

Add directory of files to knowledge base.

```python
async def add_directory(
    directory_path: str,
    recursive: bool = True,
    file_extensions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Add directory to knowledge base.

    Args:
        directory_path: Absolute directory path
        recursive: Process subdirectories
        file_extensions: File patterns (e.g., [".md", ".txt"])

    Returns:
        {
            "success": bool,
            "files_processed": int,
            "total_chunks": int
        }
    """
```

**Example**:
```python
result = await knowledge_service.add_directory(
    directory_path="/path/to/docs",
    recursive=True,
    file_extensions=[".md", ".txt"]
)

print(f"Processed {result['files_processed']} files")
```

#### get_graph_schema()

Get graph schema information.

```python
async def get_graph_schema() -> Dict[str, Any]:
    """
    Get Neo4j graph schema.

    Returns:
        {
            "success": bool,
            "node_labels": List[str],
            "relationship_types": List[str],
            "statistics": Dict
        }
    """
```

#### get_statistics()

Get knowledge base statistics.

```python
async def get_statistics() -> Dict[str, Any]:
    """
    Get knowledge base statistics.

    Returns:
        {
            "success": bool,
            "total_nodes": int,
            "total_relationships": int,
            "document_count": int,
            "chunk_count": int
        }
    """
```

#### clear_knowledge_base()

**⚠️ DANGEROUS**: Clear all knowledge base data.

```python
async def clear_knowledge_base() -> Dict[str, Any]:
    """Clear all data from knowledge base."""
```

---

## MemoryStore

Project memory persistence for AI agents.

### Initialization

```python
from src.codebase_rag.services.memory import memory_store

# Initialize (async)
await memory_store.initialize()
```

### Key Methods

#### add_memory()

Add a new memory.

```python
async def add_memory(
    project_id: str,
    memory_type: str,  # "decision" | "preference" | "experience" | "convention" | "plan" | "note"
    title: str,
    content: str,
    reason: Optional[str] = None,
    tags: Optional[List[str]] = None,
    importance: float = 0.5,
    related_refs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Add memory to project.

    Returns:
        {
            "success": bool,
            "memory_id": str,
            "project_id": str
        }
    """
```

**Example**:
```python
result = await memory_store.add_memory(
    project_id="myapp",
    memory_type="decision",
    title="Use JWT for authentication",
    content="Decided to use JWT tokens instead of session-based auth",
    reason="Need stateless authentication for mobile clients",
    tags=["auth", "architecture"],
    importance=0.9,
    related_refs=["ref://file/src/auth/jwt.py"]
)

memory_id = result["memory_id"]
```

#### search_memories()

Search memories with filters.

```python
async def search_memories(
    project_id: str,
    query: Optional[str] = None,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_importance: float = 0.0,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search project memories.

    Returns:
        {
            "success": bool,
            "memories": List[Dict],
            "total": int
        }
    """
```

**Example**:
```python
result = await memory_store.search_memories(
    project_id="myapp",
    query="authentication security",
    memory_type="decision",
    min_importance=0.7,
    limit=20
)

for memory in result["memories"]:
    print(f"{memory['title']} (importance: {memory['importance']})")
```

#### get_memory()

Get specific memory by ID.

```python
async def get_memory(
    memory_id: str
) -> Dict[str, Any]:
    """
    Get memory by ID.

    Returns:
        {
            "success": bool,
            "memory": Dict  # Full memory details
        }
    """
```

#### update_memory()

Update existing memory.

```python
async def update_memory(
    memory_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    reason: Optional[str] = None,
    tags: Optional[List[str]] = None,
    importance: Optional[float] = None
) -> Dict[str, Any]:
    """Update memory (partial update supported)."""
```

**Example**:
```python
await memory_store.update_memory(
    memory_id=memory_id,
    importance=0.95,
    tags=["auth", "security", "critical"]
)
```

#### delete_memory()

Delete memory (soft delete).

```python
async def delete_memory(
    memory_id: str
) -> Dict[str, Any]:
    """Delete memory (soft delete - data retained)."""
```

#### supersede_memory()

Create new memory that supersedes old one.

```python
async def supersede_memory(
    old_memory_id: str,
    new_memory_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create memory that supersedes old one.

    Args:
        old_memory_id: ID of memory to supersede
        new_memory_data: Data for new memory
            {
                "memory_type": str,
                "title": str,
                "content": str,
                "reason": str,
                "tags": List[str],
                "importance": float
            }

    Returns:
        {
            "success": bool,
            "old_memory_id": str,
            "new_memory_id": str
        }
    """
```

**Example**:
```python
result = await memory_store.supersede_memory(
    old_memory_id="mem-abc123",
    new_memory_data={
        "memory_type": "decision",
        "title": "Use PostgreSQL instead of MySQL",
        "content": "Switched to PostgreSQL for better JSON support",
        "reason": "Need advanced JSON querying capabilities",
        "importance": 0.8
    }
)
```

#### get_project_summary()

Get project memory summary.

```python
async def get_project_summary(
    project_id: str
) -> Dict[str, Any]:
    """
    Get project memory summary.

    Returns:
        {
            "success": bool,
            "project_id": str,
            "total_memories": int,
            "by_type": Dict  # Breakdown by memory type
        }
    """
```

---

## GraphService

Low-level Neo4j graph operations.

### Initialization

```python
from src.codebase_rag.services.code import graph_service

# Connect to Neo4j
await graph_service.connect()
```

### Key Methods

#### execute_cypher()

Execute Cypher query.

```python
def execute_cypher(
    query: str,
    parameters: Optional[Dict[str, Any]] = None
) -> GraphQueryResult:
    """
    Execute Cypher query.

    Args:
        query: Cypher query string
        parameters: Query parameters

    Returns:
        GraphQueryResult with nodes, relationships, paths
    """
```

**Example**:
```python
result = graph_service.execute_cypher(
    query="""
    MATCH (n:Memory {project_id: $project_id})
    WHERE n.importance > $min_importance
    RETURN n
    LIMIT 10
    """,
    parameters={
        "project_id": "myapp",
        "min_importance": 0.7
    }
)

for node in result.nodes:
    print(f"Node: {node.properties['title']}")
```

#### create_node()

Create a node.

```python
def create_node(
    labels: List[str],
    properties: Dict[str, Any]
) -> str:
    """
    Create node.

    Args:
        labels: Node labels
        properties: Node properties

    Returns:
        Node ID
    """
```

**Example**:
```python
node_id = graph_service.create_node(
    labels=["CustomNode", "Entity"],
    properties={
        "name": "Example",
        "value": 42,
        "created_at": datetime.utcnow().isoformat()
    }
)
```

#### create_relationship()

Create a relationship.

```python
def create_relationship(
    start_node_id: str,
    end_node_id: str,
    relationship_type: str,
    properties: Optional[Dict[str, Any]] = None
) -> str:
    """Create relationship between nodes."""
```

#### fulltext_search()

Perform fulltext search on files.

```python
def fulltext_search(
    query_text: str,
    repo_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Fulltext search on files.

    Args:
        query_text: Search query
        repo_id: Repository ID
        limit: Max results

    Returns:
        List of file matches with paths and languages
    """
```

**Example**:
```python
files = graph_service.fulltext_search(
    query_text="authentication jwt",
    repo_id="myproject",
    limit=30
)

for file in files:
    print(f"{file['path']} ({file['lang']})")
```

#### impact_analysis()

Analyze impact of file changes.

```python
def impact_analysis(
    repo_id: str,
    file_path: str,
    depth: int = 2,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Analyze file impact (reverse dependencies).

    Args:
        repo_id: Repository ID
        file_path: File path to analyze
        depth: Traversal depth
        limit: Max results

    Returns:
        List of dependent files
    """
```

---

## CodeIngestor

Repository code ingestion service.

### Initialization

```python
from src.codebase_rag.services.code import get_code_ingestor
from src.codebase_rag.services.code import graph_service

# Initialize graph service first
await graph_service.connect()

# Get code ingestor
code_ingestor = get_code_ingestor(graph_service)
```

### Key Methods

#### scan_files()

Scan repository files.

```python
def scan_files(
    repo_path: str,
    include_globs: List[str],
    exclude_globs: List[str]
) -> List[Dict[str, Any]]:
    """
    Scan files in repository.

    Args:
        repo_path: Repository path
        include_globs: Include patterns (e.g., ["**/*.py"])
        exclude_globs: Exclude patterns (e.g., ["**/node_modules/**"])

    Returns:
        List of file information dictionaries
    """
```

**Example**:
```python
files = code_ingestor.scan_files(
    repo_path="/path/to/repository",
    include_globs=["**/*.py", "**/*.ts", "**/*.tsx"],
    exclude_globs=["**/node_modules/**", "**/.git/**", "**/__pycache__/**"]
)

print(f"Found {len(files)} files")
```

#### ingest_files()

Ingest files into Neo4j graph.

```python
def ingest_files(
    repo_id: str,
    files: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Ingest files into Neo4j.

    Args:
        repo_id: Repository identifier
        files: List of file info from scan_files()

    Returns:
        {
            "success": bool,
            "files_processed": int,
            "nodes_created": int
        }
    """
```

**Example**:
```python
result = code_ingestor.ingest_files(
    repo_id="myproject",
    files=files
)

print(f"Processed {result['files_processed']} files")
print(f"Created {result['nodes_created']} nodes")
```

---

## TaskQueue

Asynchronous task queue management.

### Initialization

```python
from src.codebase_rag.services.tasks import task_queue, TaskStatus

# Start task queue
await task_queue.start()
```

### Key Methods

#### submit_task()

Submit a task to the queue.

```python
async def submit_task(
    task_func: Callable,
    task_kwargs: Dict[str, Any],
    task_name: str,
    task_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    priority: int = 0
) -> str:
    """
    Submit task to queue.

    Args:
        task_func: Function to execute
        task_kwargs: Function arguments
        task_name: Task name
        task_type: Task type
        metadata: Additional metadata
        priority: Priority (higher = more important)

    Returns:
        Task ID
    """
```

**Example**:
```python
from src.codebase_rag.services.tasks import process_document_task

task_id = await task_queue.submit_task(
    task_func=process_document_task,
    task_kwargs={
        "document_content": "Large document content...",
        "title": "Large Doc"
    },
    task_name="Process Large Document",
    task_type="document_processing",
    metadata={"source": "api"},
    priority=5
)

print(f"Task submitted: {task_id}")
```

#### get_task_status()

Get task status.

```python
def get_task_status(
    task_id: str
) -> Optional[TaskResult]:
    """
    Get task status.

    Returns:
        TaskResult or None if not found
    """
```

**Example**:
```python
task_result = task_queue.get_task_status(task_id)

if task_result:
    print(f"Status: {task_result.status.value}")
    print(f"Progress: {task_result.progress}%")

    if task_result.status == TaskStatus.SUCCESS:
        print(f"Result: {task_result.result}")
    elif task_result.status == TaskStatus.FAILED:
        print(f"Error: {task_result.error}")
```

#### cancel_task()

Cancel a task.

```python
async def cancel_task(
    task_id: str
) -> bool:
    """Cancel task. Returns True if cancelled."""
```

#### get_queue_stats()

Get queue statistics.

```python
def get_queue_stats() -> Dict[str, int]:
    """
    Get queue statistics.

    Returns:
        {
            "pending": int,
            "running": int,
            "completed": int,
            "failed": int
        }
    """
```

---

## Configuration

Access configuration settings.

```python
from src.codebase_rag.config import settings

# Neo4j settings
print(settings.neo4j_uri)
print(settings.neo4j_database)

# LLM settings
print(settings.llm_provider)
print(settings.ollama_model)
print(settings.temperature)

# Embedding settings
print(settings.embedding_provider)
print(settings.embedding_model)

# Timeouts
print(settings.connection_timeout)
print(settings.operation_timeout)
print(settings.large_document_timeout)

# Chunk settings
print(settings.chunk_size)
print(settings.chunk_overlap)
print(settings.top_k)
```

### Get Current Model Info

```python
from src.codebase_rag.config import get_current_model_info

model_info = get_current_model_info()
print(f"LLM: {model_info['llm']}")
print(f"Embedding: {model_info['embedding']}")
```

---

## Examples

### Complete Knowledge Base Example

```python
import asyncio
from src.codebase_rag.services.knowledge import Neo4jKnowledgeService

async def main():
    # Initialize service
    service = Neo4jKnowledgeService()
    await service.initialize()

    # Add documents
    await service.add_document(
        content="JWT authentication guide...",
        title="Auth Guide",
        metadata={"tags": ["auth"]}
    )

    # Query
    result = await service.query(
        question="How does authentication work?",
        mode="hybrid"
    )

    print(f"Answer: {result['answer']}")

    # Search
    search_results = await service.search_similar_nodes(
        query="authentication",
        top_k=5
    )

    for node in search_results["results"]:
        print(f"- {node['text'][:100]}")

asyncio.run(main())
```

### Memory Management Example

```python
import asyncio
from src.codebase_rag.services.memory import memory_store

async def main():
    # Initialize
    await memory_store.initialize()

    # Add decision
    result = await memory_store.add_memory(
        project_id="myapp",
        memory_type="decision",
        title="Use Redis for caching",
        content="Decided to use Redis instead of Memcached",
        reason="Redis supports data persistence",
        importance=0.8,
        tags=["cache", "architecture"]
    )

    memory_id = result["memory_id"]

    # Search memories
    search_result = await memory_store.search_memories(
        project_id="myapp",
        query="caching",
        min_importance=0.5
    )

    for memory in search_result["memories"]:
        print(f"{memory['title']}: {memory['content']}")

    # Get project summary
    summary = await memory_store.get_project_summary("myapp")
    print(f"Total memories: {summary['total_memories']}")
    print(f"By type: {summary['by_type']}")

asyncio.run(main())
```

### Repository Ingestion Example

```python
import asyncio
from src.codebase_rag.services.code import graph_service
from src.codebase_rag.services.code import get_code_ingestor
from src.codebase_rag.services.git_utils import git_utils

async def main():
    # Connect to Neo4j
    await graph_service.connect()

    # Get code ingestor
    code_ingestor = get_code_ingestor(graph_service)

    # Get repository ID
    repo_path = "/path/to/repository"
    repo_id = git_utils.get_repo_id_from_path(repo_path)

    # Scan files
    files = code_ingestor.scan_files(
        repo_path=repo_path,
        include_globs=["**/*.py", "**/*.ts"],
        exclude_globs=["**/node_modules/**", "**/.git/**"]
    )

    print(f"Found {len(files)} files")

    # Ingest into Neo4j
    result = code_ingestor.ingest_files(
        repo_id=repo_id,
        files=files
    )

    print(f"Success: {result['success']}")
    print(f"Files processed: {result['files_processed']}")

    # Search code
    search_results = graph_service.fulltext_search(
        query_text="authentication",
        repo_id=repo_id,
        limit=10
    )

    for file in search_results:
        print(f"- {file['path']} ({file['lang']})")

asyncio.run(main())
```

### Task Queue Example

```python
import asyncio
from src.codebase_rag.services.tasks import task_queue, TaskStatus
from src.codebase_rag.services.tasks import process_document_task

async def main():
    # Start task queue
    await task_queue.start()

    # Submit task
    task_id = await task_queue.submit_task(
        task_func=process_document_task,
        task_kwargs={
            "document_content": "Large document content...",
            "title": "Large Doc"
        },
        task_name="Process Large Document",
        task_type="document_processing"
    )

    print(f"Task submitted: {task_id}")

    # Monitor task
    while True:
        task_result = task_queue.get_task_status(task_id)

        if not task_result:
            break

        print(f"Status: {task_result.status.value}, Progress: {task_result.progress}%")

        if task_result.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
            break

        await asyncio.sleep(2)

    if task_result.status == TaskStatus.SUCCESS:
        print(f"Result: {task_result.result}")
    else:
        print(f"Error: {task_result.error}")

    # Get queue stats
    stats = task_queue.get_queue_stats()
    print(f"Queue stats: {stats}")

asyncio.run(main())
```

---

## Error Handling

All services return structured results with error information.

### Standard Response Format

```python
# Success
{
    "success": True,
    "...": "service-specific data"
}

# Error
{
    "success": False,
    "error": "Error message"
}
```

### Handling Errors

```python
result = await knowledge_service.query("question")

if not result.get("success"):
    error_msg = result.get("error", "Unknown error")
    print(f"Error: {error_msg}")
    # Handle error
else:
    # Process result
    answer = result["answer"]
```

### Exception Handling

```python
try:
    await knowledge_service.initialize()
except Exception as e:
    logger.error(f"Failed to initialize: {e}")
    # Handle exception
```

---

## Best Practices

### 1. Always Initialize Services

```python
# Good
service = Neo4jKnowledgeService()
await service.initialize()

# Bad - will fail
service = Neo4jKnowledgeService()
await service.query("question")  # Error: not initialized
```

### 2. Check Success Status

```python
# Good
result = await service.query("question")
if result["success"]:
    print(result["answer"])
else:
    print(f"Error: {result['error']}")

# Bad
result = await service.query("question")
print(result["answer"])  # May crash if error occurred
```

### 3. Use Context Managers for Neo4j Sessions

```python
# Good
async with graph_service.driver.session() as session:
    result = await session.run("MATCH (n) RETURN n LIMIT 10")
    # Session automatically closed

# Bad
session = graph_service.driver.session()
result = await session.run("MATCH (n) RETURN n LIMIT 10")
# Session not closed - memory leak
```

### 4. Set Appropriate Timeouts

```python
from src.codebase_rag.config import settings

# Adjust timeouts for large operations
settings.operation_timeout = 300  # 5 minutes
settings.large_document_timeout = 600  # 10 minutes

service = Neo4jKnowledgeService()
await service.initialize()
```

### 5. Handle Large Documents Asynchronously

```python
# For large documents, use task queue
if len(document_content) > 10_000:
    task_id = await task_queue.submit_task(
        task_func=process_document_task,
        task_kwargs={"document_content": document_content},
        task_name="Process Large Doc",
        task_type="document_processing"
    )
    # Monitor task_id
else:
    # Process directly
    await knowledge_service.add_document(content=document_content)
```

### 6. Batch Operations

```python
# Good - batch insert
files = code_ingestor.scan_files(repo_path, include_globs, exclude_globs)
result = code_ingestor.ingest_files(repo_id, files)

# Bad - individual inserts
for file in files:
    code_ingestor.ingest_files(repo_id, [file])  # Slow!
```

### 7. Use Memory Store for Long-term Knowledge

```python
# Store important decisions
await memory_store.add_memory(
    project_id="myapp",
    memory_type="decision",
    title="Architecture decision",
    content="Detailed rationale...",
    importance=0.9  # High importance
)

# Search when needed
memories = await memory_store.search_memories(
    project_id="myapp",
    memory_type="decision",
    min_importance=0.7
)
```

### 8. Clean Up Resources

```python
# Close connections when done
await graph_service.driver.close()

# Or use application lifecycle hooks
async def startup():
    await knowledge_service.initialize()
    await memory_store.initialize()
    await task_queue.start()

async def shutdown():
    await graph_service.driver.close()
    await task_queue.stop()
```

---

## Performance Tips

### 1. Connection Pooling

Neo4j driver handles connection pooling automatically. Reuse service instances:

```python
# Good - single instance
service = Neo4jKnowledgeService()
await service.initialize()

for question in questions:
    await service.query(question)

# Bad - multiple instances
for question in questions:
    service = Neo4jKnowledgeService()
    await service.initialize()  # Expensive!
    await service.query(question)
```

### 2. Batch Queries

```python
# Good - batch cypher query
query = """
UNWIND $items as item
CREATE (n:Node {name: item.name, value: item.value})
"""
graph_service.execute_cypher(query, {"items": items})

# Bad - individual queries
for item in items:
    graph_service.execute_cypher(
        "CREATE (n:Node {name: $name, value: $value})",
        item
    )
```

### 3. Use Incremental Repository Ingestion

```python
# 60x faster for updates
from src.codebase_rag.services.git_utils import git_utils

if git_utils.is_git_repo(repo_path):
    changed_files = git_utils.get_changed_files(repo_path)
    files_to_process = filter_by_patterns(changed_files)
else:
    # Fall back to full scan
    files_to_process = code_ingestor.scan_files(repo_path, ...)
```

### 4. Limit Result Sets

```python
# Always use limits for large datasets
result = await knowledge_service.search_similar_nodes(
    query="search term",
    top_k=10  # Limit results
)
```

---

**Last Updated**: 2025-01-15
**SDK Version**: 1.0.0
**Python Version**: 3.10+
