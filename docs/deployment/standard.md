# Standard Mode Deployment

Standard Mode adds **Memory Store with vector search** to Code Graph functionality. Requires embedding model but no LLM.

## What You Get

### Minimal Mode Features +
- **Memory Store**: Persistent project knowledge for AI agents
- **Vector Search**: Semantic similarity search in memories
- **Memory Management**: Add, search, update, delete memories
- **Memory Evolution**: Supersede outdated decisions

### Use Cases
- AI agent long-term memory across sessions
- Project decision tracking with semantic search
- Team preference documentation
- Problem-solution repository

## System Requirements

### Minimum
- **CPU**: 4 cores
- **RAM**: 8GB (for local embeddings)
- **Disk**: 20GB SSD
- **Docker**: 20.10+

### With Cloud Embeddings
- **CPU**: 2 cores
- **RAM**: 4GB
- **OpenAI/Gemini API key**

## Quick Start

### 1. Choose Embedding Provider

=== "Ollama (Local, Free)"

    ```bash
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh

    # Pull embedding model
    ollama pull nomic-embed-text

    # Verify
    curl http://localhost:11434/api/embeddings \
      -d '{"model":"nomic-embed-text","prompt":"test"}'
    ```

=== "OpenAI (Cloud, Best Quality)"

    ```bash
    # Get API key from https://platform.openai.com/api-keys
    export OPENAI_API_KEY=sk-proj-...
    ```

=== "Google Gemini (Cloud, Cost-Effective)"

    ```bash
    # Get API key from https://makersuite.google.com/app/apikey
    export GOOGLE_API_KEY=AIza...
    ```

### 2. Configure Environment

```bash
# Copy standard template
cp docker/.env.template/.env.standard .env

# Edit configuration
nano .env
```

Example configuration:

```bash
# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=neo4j

# Deployment Mode
DEPLOYMENT_MODE=standard
ENABLE_KNOWLEDGE_RAG=false
ENABLE_AUTO_EXTRACTION=false

# Embedding Provider (choose one)
EMBEDDING_PROVIDER=ollama

# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Or OpenAI
# EMBEDDING_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Start Services

```bash
make docker-standard

# Or
docker-compose -f docker/docker-compose.standard.yml up -d
```

### 4. Verify Deployment

```bash
# Check containers
docker ps

# Test embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test query"}'

# Check Neo4j vector index
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p password
# Run: SHOW INDEXES;
```

## Available MCP Tools

Standard mode provides **11 tools** (4 Code Graph + 7 Memory):

### Memory Management Tools

**1. add_memory** - Save project knowledge
```json
{
  "project_id": "myapp",
  "memory_type": "decision",
  "title": "Use PostgreSQL for main database",
  "content": "Selected PostgreSQL over MySQL",
  "reason": "Need advanced JSON support",
  "importance": 0.9,
  "tags": ["database", "architecture"]
}
```

**2. search_memories** - Semantic search
```json
{
  "project_id": "myapp",
  "query": "database decisions",
  "memory_type": "decision",
  "min_importance": 0.7,
  "limit": 10
}
```

**3. get_memory** - Retrieve specific memory
```json
{
  "memory_id": "mem_123456"
}
```

**4. update_memory** - Modify existing memory
```json
{
  "memory_id": "mem_123456",
  "title": "Updated title",
  "importance": 0.95
}
```

**5. delete_memory** - Soft delete memory
```json
{
  "memory_id": "mem_123456",
  "reason": "No longer relevant"
}
```

**6. supersede_memory** - Replace with new memory
```json
{
  "old_memory_id": "mem_123456",
  "new_title": "Migrate to PostgreSQL 16",
  "new_content": "Upgrading from PostgreSQL 14",
  "new_reason": "Performance improvements",
  "new_importance": 0.9
}
```

**7. get_project_summary** - Overview of all memories
```json
{
  "project_id": "myapp"
}
```

## Usage Examples

### Example 1: AI Agent Workflow

```bash
# Agent starts working on authentication feature

# 1. Search for related decisions
Tool: search_memories
Input: {
  "project_id": "myapp",
  "query": "authentication security",
  "memory_type": "decision"
}

# 2. Implement feature following past decisions

# 3. Save new decision
Tool: add_memory
Input: {
  "project_id": "myapp",
  "memory_type": "decision",
  "title": "Use JWT with RS256",
  "content": "Implemented JWT authentication with RS256 signing",
  "reason": "More secure than HS256, supports key rotation",
  "importance": 0.9,
  "tags": ["auth", "security"]
}
```

### Example 2: Track Problem Solutions

```bash
# Encountered Redis connection issue in Docker

Tool: add_memory
Input: {
  "project_id": "myapp",
  "memory_type": "experience",
  "title": "Redis Docker networking issue",
  "content": "Redis connection fails with localhost in Docker",
  "reason": "Must use service name 'redis' instead of localhost",
  "importance": 0.7,
  "tags": ["docker", "redis", "networking"]
}

# Later, search for Redis issues
Tool: search_memories
Input: {
  "project_id": "myapp",
  "query": "Redis connection problems",
  "memory_type": "experience"
}
```

### Example 3: Update Outdated Decision

```bash
# Original decision to use MySQL
Old Memory ID: mem_abc123

# Decided to migrate to PostgreSQL
Tool: supersede_memory
Input: {
  "old_memory_id": "mem_abc123",
  "new_title": "Migrate to PostgreSQL",
  "new_content": "Migrating from MySQL to PostgreSQL",
  "new_reason": "Need advanced features and better performance",
  "new_importance": 0.95,
  "new_tags": ["database", "migration"]
}
```

## Memory Best Practices

### Importance Scoring
- **0.9-1.0**: Critical architectural decisions, security findings
- **0.7-0.8**: Important technical choices
- **0.5-0.6**: Team preferences, conventions
- **0.3-0.4**: Future plans, minor notes

### Effective Tagging
```bash
# Domain tags
"database", "api", "frontend", "auth"

# Type tags
"performance", "security", "bug", "optimization"

# Status tags
"critical", "deprecated", "planned"
```

### When to Save Memories
- After making architecture decisions
- When solving tricky bugs
- When establishing team conventions
- When discovering important limitations

## Performance Considerations

### Embedding Model Selection

**Local (Ollama)**:
- `nomic-embed-text`: Best quality, 768 dimensions
- `mxbai-embed-large`: Faster, good quality
- `all-minilm`: Lightweight, 384 dimensions

**Cloud**:
- OpenAI `text-embedding-3-small`: $0.02/1M tokens
- OpenAI `text-embedding-3-large`: $0.13/1M tokens
- Gemini `embedding-001`: Free tier available

### Vector Index Tuning

```cypher
// Check vector index status
SHOW INDEXES;

// Rebuild if needed
DROP INDEX memory_content_vector IF EXISTS;
CREATE VECTOR INDEX memory_content_vector
FOR (m:Memory) ON (m.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}};
```

## Cost Analysis

### With Local Ollama
- **Infrastructure**: ~$10-20/month (VPS with 8GB RAM)
- **Embedding**: $0 (local)
- **Total**: ~$10-20/month

### With OpenAI Embeddings
- **Infrastructure**: ~$5-10/month (small VPS)
- **Embeddings**: ~$0.02 per 1M tokens
- **Typical usage**: ~$1-5/month for embeddings
- **Total**: ~$6-15/month

## Upgrading to Full Mode

When you need LLM-powered features:

```bash
# Stop standard mode
docker-compose -f docker/docker-compose.standard.yml down

# Configure for full mode
cp docker/.env.template/.env.full .env
nano .env  # Add LLM configuration

# Start full mode
docker-compose -f docker/docker-compose.full.yml up -d
```

## Troubleshooting

### Embedding Generation Fails

```bash
# Check Ollama logs
docker logs codebase-rag-ollama

# Test embedding locally
curl http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}'

# Restart Ollama
docker restart codebase-rag-ollama
```

### Vector Search Returns No Results

```bash
# Check if vector index exists
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p password
# Run: SHOW INDEXES;

# Check memory count
# Run: MATCH (m:Memory) RETURN count(m);

# Verify embeddings exist
# Run: MATCH (m:Memory) WHERE m.embedding IS NOT NULL RETURN count(m);
```

## Next Steps

- [Memory Store User Guide](../guide/memory/overview.md) - Detailed features
- [Full Mode](full.md) - Upgrade for all features
- [Production Setup](production.md) - Deploy to production
