# Full Mode Deployment

Full Mode provides **all features** including Code Graph, Memory Store, Knowledge RAG, and LLM-powered auto-extraction.

## Complete Feature Set

###All Features Enabled
- ✅ **Code Graph**: Repository indexing, search, impact analysis
- ✅ **Memory Store**: Project knowledge with vector search
- ✅ **Knowledge RAG**: Document processing and intelligent Q&A
- ✅ **Auto-Extraction**: LLM-powered memory extraction from:
  - Git commits
  - Code comments (TODO, FIXME, NOTE)
  - AI conversations
  - Knowledge base queries

### Use Cases
- Full-featured AI coding assistant
- Intelligent documentation systems
- Automated knowledge capture
- Enterprise code intelligence platform

## System Requirements

### With Local LLM (Ollama)
- **CPU**: 8+ cores (16+ recommended)
- **RAM**: 16GB minimum (32GB recommended)
- **GPU**: Optional but highly recommended (8GB+ VRAM)
- **Disk**: 100GB SSD

### With Cloud LLM
- **CPU**: 4 cores
- **RAM**: 8GB
- **Disk**: 50GB SSD
- **API Access**: OpenAI, Gemini, or OpenRouter

## Quick Start

### 1. Choose LLM Provider

=== "Ollama (Local, Private)"

    ```bash
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh

    # Pull models
    ollama pull llama3.2          # 8B parameter model
    ollama pull nomic-embed-text  # Embedding model

    # For better quality (requires more RAM)
    # ollama pull mistral:7b
    # ollama pull qwen2.5:14b
    ```

=== "OpenAI (Cloud, Best Quality)"

    ```bash
    # Get API key
    # Visit: https://platform.openai.com/api-keys
    export OPENAI_API_KEY=sk-proj-...
    ```

=== "Google Gemini (Cloud, Cost-Effective)"

    ```bash
    # Get API key
    # Visit: https://makersuite.google.com/app/apikey
    export GOOGLE_API_KEY=AIza...
    ```

=== "OpenRouter (Multi-Provider)"

    ```bash
    # Get API key
    # Visit: https://openrouter.ai/keys
    export OPENROUTER_API_KEY=sk-or-v1-...
    ```

### 2. Configure Environment

```bash
# Copy full template
cp docker/.env.template/.env.full .env

# Edit configuration
nano .env
```

Example with Ollama:

```bash
# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=neo4j

# Deployment Mode - Enable all features
DEPLOYMENT_MODE=full
ENABLE_KNOWLEDGE_RAG=true
ENABLE_AUTO_EXTRACTION=true

# LLM Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2

# Embedding Configuration
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 3. Start Services

=== "With Bundled Ollama"

    ```bash
    # Start with Ollama container included
    make docker-full-with-ollama

    # Or
    docker-compose -f docker/docker-compose.full.yml --profile with-ollama up -d
    ```

=== "With External Ollama"

    ```bash
    # Start without Ollama (use system Ollama)
    make docker-full

    # Or
    docker-compose -f docker/docker-compose.full.yml up -d
    ```

### 4. Verify Deployment

```bash
# Check all containers
docker ps
# Should see: mcp, neo4j, (optionally ollama)

# Test LLM
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'

# Test embedding
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "test embedding"
}'

# Check service health (if using FastAPI)
curl http://localhost:8000/api/v1/health
```

## Available MCP Tools

Full mode provides **30 tools** across 6 categories:

### Code Graph Tools (4)
- `code_graph_ingest_repo`
- `code_graph_fulltext_search`
- `code_graph_impact_analysis`
- `code_graph_pack_context`

### Memory Management Tools (7)
- `add_memory`
- `search_memories`
- `get_memory`
- `update_memory`
- `delete_memory`
- `supersede_memory`
- `get_project_summary`

### Auto-Extraction Tools (5) - New!
- `extract_from_conversation`
- `extract_from_git_commit`
- `extract_from_code_comments`
- `suggest_memory_from_query`
- `batch_extract_from_repository`

### Knowledge RAG Tools (8) - New!
- `knowledge_add_document`
- `knowledge_add_directory`
- `knowledge_query`
- `knowledge_search`
- `knowledge_list_documents`
- `knowledge_delete_document`
- `knowledge_update_document`
- `knowledge_get_stats`

### Task Queue Tools (4)
- `task_submit`
- `task_status`
- `task_cancel`
- `list_tasks`

### System Tools (2)
- `health_check`
- `system_info`

## Advanced Features

### Auto-Extraction from Git Commits

Automatically extract decisions and learnings:

```json
{
  "tool": "extract_from_git_commit",
  "input": {
    "project_id": "myapp",
    "commit_sha": "abc123...",
    "commit_message": "feat: implement JWT authentication\n\nAdded JWT middleware for API auth",
    "changed_files": ["src/auth/jwt.py", "src/middleware/auth.py"],
    "auto_save": true
  }
}
```

### Mine Code Comments

Extract TODOs and decisions from code:

```json
{
  "tool": "extract_from_code_comments",
  "input": {
    "project_id": "myapp",
    "file_path": "src/api/routes.py"
  }
}
```

### Conversation Analysis

Extract memories from AI conversations:

```json
{
  "tool": "extract_from_conversation",
  "input": {
    "project_id": "myapp",
    "conversation": [
      {"role": "user", "content": "Should we use Redis or Memcached?"},
      {"role": "assistant", "content": "Redis is better because..."}
    ],
    "auto_save": false
  }
}
```

### Knowledge RAG

Process and query documents:

```json
{
  "tool": "knowledge_add_document",
  "input": {
    "file_path": "/docs/architecture.md",
    "metadata": {"type": "architecture", "version": "1.0"}
  }
}

{
  "tool": "knowledge_query",
  "input": {
    "query": "How does the authentication system work?",
    "max_results": 5
  }
}
```

### Batch Repository Extraction

Comprehensive analysis:

```json
{
  "tool": "batch_extract_from_repository",
  "input": {
    "project_id": "myapp",
    "repo_path": "/repos/myapp",
    "max_commits": 100,
    "file_patterns": ["*.py", "*.js", "*.go"]
  }
}
```

## LLM Provider Comparison

### Ollama (Local)

**Pros**:
- Free and private
- No API limits
- Works offline
- Full control

**Cons**:
- Requires powerful hardware
- Slower than cloud
- Manual model management

**Recommended Models**:
- `llama3.2` (8B) - Good balance
- `mistral` (7B) - Fast
- `qwen2.5` (14B) - Better quality (needs 16GB+ RAM)

### OpenAI

**Pros**:
- Best quality
- Fast responses
- No infrastructure needed

**Cons**:
- Costs money
- Requires internet
- Data sent to OpenAI

**Cost** (Nov 2024):
- GPT-4o: $5/$15 per 1M tokens (in/out)
- GPT-4o-mini: $0.15/$0.60 per 1M tokens
- Embeddings: $0.02 per 1M tokens

### Google Gemini

**Pros**:
- Cost-effective
- Good quality
- Fast

**Cons**:
- Requires internet
- Data sent to Google

**Cost**:
- Gemini 1.5 Flash: Lower cost
- Gemini 1.5 Pro: Higher quality
- Free tier available

## Performance Optimization

### Ollama GPU Acceleration

```yaml
# Add to docker-compose.full.yml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Neo4j Performance for Large Scale

```bash
# In docker-compose.full.yml
NEO4J_server_memory_heap_initial__size=4G
NEO4J_server_memory_heap_max__size=8G
NEO4J_server_memory_pagecache_size=4G
NEO4J_dbms_memory_transaction_total_max=2G
```

### LLM Context Optimization

```python
# Use context packing to stay within token limits
tool: code_graph_pack_context
input: {
  "entry_points": ["src/main.py"],
  "task_type": "implement",
  "token_budget": 8000  # Adjust based on model
}
```

## Cost Estimation

### Local Deployment (Ollama)
- **VPS**: $40-80/month (32GB RAM, 8 cores)
- **GPU VPS**: $100-200/month (with GPU)
- **LLM**: $0
- **Embeddings**: $0
- **Total**: $40-200/month

### Cloud Deployment (OpenAI)
- **VPS**: $10-20/month (8GB RAM)
- **LLM**: $20-100/month (depends on usage)
- **Embeddings**: $1-5/month
- **Total**: $31-125/month

### Hybrid (Ollama Embeddings + OpenAI LLM)
- **VPS**: $10-20/month
- **LLM**: $20-100/month
- **Embeddings**: $0 (local)
- **Total**: $30-120/month

## Production Deployment

- High availability configuration
- Backup strategies
- Monitoring setup
- Security hardening
- Scaling considerations

## Troubleshooting

### LLM Generation Fails

```bash
# Check Ollama
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "test"
}'

# Check model is pulled
ollama list

# View Ollama logs
docker logs codebase-rag-ollama
```

### Out of Memory Errors

```bash
# Check memory usage
docker stats

# Reduce model size
ollama pull llama3.2:3b  # Smaller 3B model

# Or increase Docker memory limit
# Docker Desktop: Settings → Resources → Memory
```

### Slow Response Times

```bash
# Enable GPU acceleration (if available)
# Check GPU is detected
nvidia-smi

# Or switch to smaller model
OLLAMA_MODEL=mistral  # 7B instead of 13B

# Or use cloud LLM for faster responses
LLM_PROVIDER=openai
```

## Next Steps

- [Knowledge RAG Guide](../guide/knowledge/overview.md) - Document processing
- [Auto-Extraction Guide](../guide/memory/extraction.md) - Automated memory capture
