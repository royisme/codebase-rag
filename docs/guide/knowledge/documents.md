# Document Processing Guide

Learn how to add, manage, and optimize documents in the Knowledge RAG system.

## Overview

The document processing pipeline transforms your documents into an intelligent knowledge graph:

1. **Ingestion**: Read document content
2. **Chunking**: Split into semantic chunks
3. **Embedding**: Convert to vector representations
4. **Storage**: Save to Neo4j with vector index
5. **Indexing**: Create search-optimized structures

## Document Processing Methods

### 1. Direct Content (add_document)

Add document content directly as a string.

#### MCP Tool Usage

```json
{
  "tool": "add_document",
  "input": {
    "content": "Your document content here...",
    "title": "Document Title",
    "metadata": {
      "author": "John Doe",
      "category": "tutorial",
      "tags": ["python", "tutorial"]
    }
  }
}
```

#### HTTP API Usage

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/add \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your document content...",
    "title": "Document Title",
    "metadata": {"category": "tutorial"}
  }'
```

#### Python Client Usage

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/knowledge/add",
        json={
            "content": "Document content...",
            "title": "My Document",
            "metadata": {"type": "article"}
        }
    )
    result = response.json()
    print(f"Added: {result}")
```

#### Size-Based Behavior

- **Small documents** (<10KB): Processed synchronously
  ```json
  {
    "success": true,
    "message": "Document added successfully",
    "node_id": "abc123..."
  }
  ```

- **Large documents** (≥10KB): Queued for async processing
  ```json
  {
    "success": true,
    "async": true,
    "task_id": "task_xyz789",
    "message": "Large document queued (size: 25600 bytes)"
  }
  ```

### 2. File Upload (add_file)

Process files from the filesystem.

#### Supported File Types

- **Text files**: .txt, .md, .rst, .log
- **Code files**: .py, .js, .java, .go, .rs, .cpp, .c, .h
- **Documentation**: .pdf, .html, .xml
- **Data files**: .json, .yaml, .yml, .toml, .csv

#### MCP Tool Usage

```json
{
  "tool": "add_file",
  "input": {
    "file_path": "/path/to/document.md"
  }
}
```

#### HTTP API Usage

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/add-file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/document.md"}'
```

#### Example Response

```json
{
  "success": true,
  "message": "File processed successfully",
  "file_path": "/path/to/document.md",
  "chunks_created": 12,
  "node_id": "file_node_123"
}
```

### 3. Directory Batch Processing (add_directory)

Process multiple files from a directory.

#### MCP Tool Usage

```json
{
  "tool": "add_directory",
  "input": {
    "directory_path": "/path/to/docs",
    "recursive": true
  }
}
```

#### HTTP API Usage

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/add-directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/path/to/docs",
    "recursive": true
  }'
```

#### Features

- **Recursive scanning**: Process all subdirectories
- **File filtering**: Automatic filtering by extension
- **Async processing**: Always queued as background task
- **Progress tracking**: Monitor via task queue

#### Example Response

```json
{
  "success": true,
  "async": true,
  "task_id": "dir_task_456",
  "message": "Directory processing queued: /path/to/docs"
}
```

## Task Monitoring

Large documents and directory processing are handled asynchronously. Monitor progress using task queue tools.

### Get Task Status

```json
{
  "tool": "get_task_status",
  "input": {
    "task_id": "task_xyz789"
  }
}
```

### Watch Task Progress

```json
{
  "tool": "watch_task",
  "input": {
    "task_id": "task_xyz789",
    "timeout": 300
  }
}
```

### Task Lifecycle

```
PENDING → PROCESSING → COMPLETED
    ↓          ↓
  FAILED    FAILED
```

## Document Metadata

Metadata enriches documents and enables advanced filtering.

### Standard Metadata Fields

```python
{
  "title": "Document Title",           # Required
  "author": "Author Name",             # Optional
  "created_at": "2024-01-15",          # Auto-generated if not provided
  "updated_at": "2024-01-16",          # Auto-updated
  "category": "tutorial",              # Custom category
  "tags": ["python", "async"],         # List of tags
  "source": "https://example.com",     # Source URL
  "language": "en",                    # Content language
  "version": "1.0",                    # Document version
  "priority": 0.8                      # Relevance priority
}
```

### Custom Metadata

Add any custom fields:

```python
{
  "metadata": {
    "department": "Engineering",
    "project": "Project Alpha",
    "classification": "internal",
    "expires_at": "2025-01-01",
    "custom_field": "custom_value"
  }
}
```

### Metadata Usage

Metadata is stored as node properties and can be:
- Searched in vector queries
- Filtered in graph queries
- Used for relationship inference
- Displayed in query results

## Chunking Strategy

Documents are split into chunks for optimal processing and retrieval.

### Chunking Parameters

Configure in `.env`:

```bash
CHUNK_SIZE=512        # Tokens per chunk
CHUNK_OVERLAP=50      # Overlap between chunks (tokens)
```

### Chunk Size Guidelines

| Document Type | Recommended Chunk Size | Reasoning |
|--------------|----------------------|-----------|
| Technical docs | 512-1024 | Preserve code context |
| Articles | 256-512 | Natural paragraph breaks |
| Code files | 1024-2048 | Keep function context |
| Short content | 128-256 | Small FAQs, snippets |

### Overlap Benefits

Chunk overlap ensures context preservation:

```
Chunk 1: [tokens 0-512] with overlap [462-512]
Chunk 2: [tokens 462-974] with overlap [924-974]
Chunk 3: [tokens 924-1436] ...
```

Benefits:
- ✅ Maintains sentence continuity
- ✅ Preserves context across boundaries
- ✅ Improves retrieval accuracy
- ✅ Reduces information loss

## Embedding Generation

### Embedding Providers

Choose from multiple providers:

#### 1. Ollama (Local, Free)

```bash
# .env configuration
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # 768 dimensions
OLLAMA_BASE_URL=http://localhost:11434

# Available models:
# - nomic-embed-text (768d) - Recommended
# - mxbai-embed-large (1024d) - Higher quality
# - all-minilm (384d) - Faster, smaller
```

#### 2. OpenAI (Cloud, High Quality)

```bash
# .env configuration
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # 1536 dimensions
OPENAI_API_KEY=sk-...

# Available models:
# - text-embedding-3-small (1536d) - Cost-effective
# - text-embedding-3-large (3072d) - Best quality
# - text-embedding-ada-002 (1536d) - Legacy
```

#### 3. Google Gemini (Cloud, Cost-Effective)

```bash
# .env configuration
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=models/embedding-001  # 768 dimensions
GOOGLE_API_KEY=AIza...
```

#### 4. HuggingFace (Local, Customizable)

```bash
# .env configuration
EMBEDDING_PROVIDER=huggingface
HF_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5  # 384 dimensions

# Popular models:
# - BAAI/bge-small-en-v1.5 (384d) - Fast
# - BAAI/bge-base-en-v1.5 (768d) - Balanced
# - BAAI/bge-large-en-v1.5 (1024d) - Best quality
```

### Vector Dimensions

Different models produce different dimension vectors:

```bash
# Configure in .env
VECTOR_DIMENSION=768  # Must match your embedding model

# Common dimensions:
# 384 - Small models (fast, less accurate)
# 768 - Medium models (balanced)
# 1024 - Large models (slower, more accurate)
# 1536 - OpenAI models
# 3072 - OpenAI large model
```

### Embedding Performance

| Provider | Speed | Quality | Cost | Privacy |
|----------|-------|---------|------|---------|
| Ollama | Medium | Good | Free | 100% Private |
| OpenAI | Fast | Excellent | $0.13/1M tokens | Cloud |
| Gemini | Fast | Very Good | Lower cost | Cloud |
| HuggingFace | Fast-Slow | Varies | Free | 100% Private |

## Neo4j Storage

### Node Structure

Each document chunk becomes a Neo4j node:

```cypher
(:Document {
  id: "doc_123",
  title: "Document Title",
  content: "Chunk content...",
  embedding: [0.123, 0.456, ...],  // Vector embedding
  chunk_index: 0,
  total_chunks: 10,
  metadata: {...},
  created_at: datetime(),
  updated_at: datetime()
})
```

### Relationships

Documents can have relationships:

```cypher
// Document parts
(doc:Document)-[:HAS_CHUNK]->(chunk:DocumentChunk)

// Document references
(doc1:Document)-[:REFERENCES]->(doc2:Document)

// Topic relationships
(doc:Document)-[:ABOUT]->(topic:Topic)

// Source relationships
(doc:Document)-[:FROM_FILE]->(file:File)
```

### Vector Index

Neo4j creates a vector index for fast similarity search:

```cypher
// Created automatically
CREATE VECTOR INDEX document_embeddings
FOR (d:Document)
ON d.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
}
```

## Document Management

### List Documents

```bash
# HTTP API
curl http://localhost:8000/api/v1/knowledge/documents
```

Response:
```json
{
  "documents": [
    {
      "id": "doc_123",
      "title": "Document Title",
      "chunks": 10,
      "created_at": "2024-01-15T10:00:00Z",
      "metadata": {...}
    }
  ],
  "total": 1
}
```

### Get Document Details

```bash
# HTTP API
curl http://localhost:8000/api/v1/knowledge/documents/doc_123
```

### Update Document

```bash
# HTTP API
curl -X PUT http://localhost:8000/api/v1/knowledge/documents/doc_123 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "metadata": {"updated": true}
  }'
```

### Delete Document

```bash
# HTTP API
curl -X DELETE http://localhost:8000/api/v1/knowledge/documents/doc_123
```

**Note**: Deletion removes the document and all its chunks from the graph.

## Best Practices

### 1. Document Preparation

**Clean your content**:
```python
# Remove excessive whitespace
content = " ".join(content.split())

# Remove special characters if needed
import re
content = re.sub(r'[^\w\s\.\,\!\?]', '', content)

# Normalize line endings
content = content.replace('\r\n', '\n')
```

### 2. Metadata Strategy

**Use consistent metadata**:
```python
# Good: Consistent structure
metadata = {
    "type": "tutorial",      # Always use "type"
    "difficulty": "beginner", # Standardized values
    "tags": ["python", "async"]  # Normalized tags
}

# Bad: Inconsistent
metadata = {
    "kind": "tutorial",      # Different field name
    "level": "easy",         # Different values
    "categories": "python"   # Wrong type
}
```

### 3. Batch Processing

**Process large collections efficiently**:
```python
# Good: Use directory processing
add_directory("/docs", recursive=True)

# Avoid: Individual file uploads
for file in files:  # Don't do this for many files
    add_file(file)
```

### 4. Error Handling

**Handle failures gracefully**:
```python
try:
    result = await add_document(content, title)
    if not result["success"]:
        logger.error(f"Failed: {result['error']}")
except Exception as e:
    logger.error(f"Exception: {e}")
```

### 5. Resource Management

**Monitor system resources**:
- Check task queue length
- Monitor Neo4j memory usage
- Track embedding generation time
- Watch disk space

## Troubleshooting

### Issue: Document Not Found

**Symptom**: Queries don't return expected document

**Solutions**:
1. Verify document was added successfully
2. Check embeddings were generated
3. Verify vector index exists
4. Try different query terms

### Issue: Slow Processing

**Symptom**: Documents take long to process

**Solutions**:
1. Check chunk size (reduce if too large)
2. Verify embedding provider is responsive
3. Monitor Neo4j performance
4. Use async processing for large docs

### Issue: Poor Search Results

**Symptom**: Queries return irrelevant documents

**Solutions**:
1. Adjust chunk size/overlap
2. Try different embedding model
3. Add more descriptive metadata
4. Use different query mode (hybrid/vector/graph)

### Issue: Out of Memory

**Symptom**: Embedding generation fails

**Solutions**:
1. Reduce batch size
2. Increase system memory
3. Use smaller embedding model
4. Process documents in smaller batches

## Advanced Techniques

### 1. Custom Document Loaders

Create specialized loaders for custom formats:

```python
from llama_index.core import Document

def load_custom_format(file_path):
    # Your custom parsing logic
    content = parse_custom_file(file_path)

    return Document(
        text=content,
        metadata={
            "source": file_path,
            "format": "custom"
        }
    )
```

### 2. Document Versioning

Track document versions:

```python
metadata = {
    "version": "2.0",
    "previous_version": "1.0",
    "change_summary": "Updated API examples",
    "updated_by": "user@example.com"
}
```

### 3. Multi-language Support

Process documents in multiple languages:

```python
# Specify language in metadata
metadata = {
    "language": "es",  # Spanish
    "original_language": "en",
    "translated": True
}

# Use language-specific embedding models
EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"
```

### 4. Incremental Updates

Update specific document chunks:

```python
# Add new version while keeping history
new_content = updated_document_content
metadata = {
    "replaces": "old_doc_id",
    "version": "2.0"
}
add_document(new_content, metadata=metadata)
```

## Performance Optimization

### Embedding Cache

Cache embeddings for repeated content:

```python
# Configure cache in .env
ENABLE_EMBEDDING_CACHE=true
CACHE_SIZE=10000  # Number of embeddings to cache
```

### Batch Processing

Process multiple documents in batches:

```python
# Use directory processing for efficiency
add_directory("/docs", recursive=True)

# Or implement custom batching
for batch in chunks(documents, batch_size=10):
    process_batch(batch)
```

### Parallel Processing

Enable parallel processing for large collections:

```bash
# Configure in .env
MAX_WORKERS=4  # Parallel document processing threads
```

## Next Steps

- **[Query Guide](query.md)**: Learn to query your knowledge base effectively
- **[MCP Integration](../mcp/overview.md)**: Connect to AI assistants
- **[Performance Tuning](../../deployment/production.md)**: Optimize for production

## Additional Resources

- **LlamaIndex Documentation**: https://docs.llamaindex.ai/
- **Neo4j Vector Search**: https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/
- **Embedding Models**: https://huggingface.co/spaces/mteb/leaderboard
