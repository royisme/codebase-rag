# Configuration

This guide explains how to configure Code Graph Knowledge System for different deployment modes and providers.

## Configuration Files

### Environment Variables (.env)

The primary configuration method uses `.env` file. Templates are provided for each deployment mode:

- `docker/.env.template/.env.minimal` - Code Graph only
- `docker/.env.template/.env.standard` - Code Graph + Memory
- `docker/.env.template/.env.full` - All features

## Deployment Mode Configuration

### Minimal Mode (Code Graph Only)

No LLM or embedding model required. Only Neo4j configuration needed:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here
NEO4J_DATABASE=neo4j

# Deployment Mode
DEPLOYMENT_MODE=minimal
ENABLE_KNOWLEDGE_RAG=false
ENABLE_AUTO_EXTRACTION=false
```

### Standard Mode (Code Graph + Memory)

Requires embedding model for vector search:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here
NEO4J_DATABASE=neo4j

# Deployment Mode
DEPLOYMENT_MODE=standard
ENABLE_KNOWLEDGE_RAG=false
ENABLE_AUTO_EXTRACTION=false

# Embedding Provider (choose one)
EMBEDDING_PROVIDER=ollama  # or openai, gemini, huggingface

# Ollama Configuration (if using Ollama)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Or OpenAI Configuration
# OPENAI_API_KEY=sk-...
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Or Google Gemini Configuration
# GOOGLE_API_KEY=...
# GEMINI_EMBEDDING_MODEL=models/embedding-001
```

### Full Mode (All Features)

Requires both LLM and embedding model:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here
NEO4J_DATABASE=neo4j

# Deployment Mode
DEPLOYMENT_MODE=full
ENABLE_KNOWLEDGE_RAG=true
ENABLE_AUTO_EXTRACTION=true

# LLM Provider (choose one)
LLM_PROVIDER=ollama  # or openai, gemini, openrouter

# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_PROVIDER=ollama

# Or OpenAI Configuration
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# EMBEDDING_PROVIDER=openai

# Or Google Gemini Configuration
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=...
# GEMINI_MODEL=gemini-1.5-pro
# GEMINI_EMBEDDING_MODEL=models/embedding-001
# EMBEDDING_PROVIDER=gemini
```

## Provider-Specific Configuration

### Ollama

Run locally for privacy and cost savings:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2
ollama pull nomic-embed-text

# Configuration
OLLAMA_BASE_URL=http://localhost:11434  # or host.docker.internal in Docker
OLLAMA_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

**Recommended Models**:
- LLM: `llama3.2` (8B), `mistral` (7B), `qwen2.5` (7B)
- Embedding: `nomic-embed-text`, `mxbai-embed-large`

### OpenAI

Best performance, requires API key:

```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o  # or gpt-4o-mini for lower cost
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**Cost Considerations**:
- GPT-4o: $5/$15 per 1M tokens (input/output)
- GPT-4o-mini: $0.15/$0.60 per 1M tokens
- Embeddings: $0.02 per 1M tokens

### Google Gemini

Good balance of performance and cost:

```bash
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
GEMINI_EMBEDDING_MODEL=models/embedding-001
```

**Model Options**:
- `gemini-1.5-flash`: Fast, lower cost
- `gemini-1.5-pro`: Higher quality, more expensive

### OpenRouter

Access multiple providers through one API:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENAI_API_BASE=https://openrouter.ai/api/v1
```

### HuggingFace (Local Embeddings)

Free local embeddings without API:

```bash
EMBEDDING_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Advanced Configuration

### Timeout Settings

Adjust timeouts for large operations:

```bash
# Connection timeout (seconds)
CONNECTION_TIMEOUT=30

# Standard operation timeout (seconds)
OPERATION_TIMEOUT=300

# Large document processing timeout (seconds)
LARGE_DOCUMENT_TIMEOUT=600
```

### Neo4j Performance Tuning

For large repositories:

```bash
# Neo4j memory configuration (add to docker-compose.yml)
NEO4J_server_memory_heap_initial__size=2G
NEO4J_server_memory_heap_max__size=4G
NEO4J_server_memory_pagecache_size=2G
```

### Monitoring and Logging

Enable detailed logging:

```bash
# Enable monitoring UI
ENABLE_MONITORING=true

# Log level
LOG_LEVEL=INFO  # or DEBUG for detailed logs

# Enable SSE for real-time updates
ENABLE_SSE=true
```

## Validation

After configuration, validate settings:

```bash
# Test Neo4j connection
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p your_password

# Test LLM provider (if Full mode)
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test"}'

# Check service health
curl http://localhost:8000/api/v1/health
```

## Configuration Best Practices

1. **Use Strong Passwords**: Generate secure Neo4j passwords
   ```bash
   openssl rand -base64 32
   ```

2. **API Key Security**: Never commit `.env` to git
   ```bash
   echo ".env" >> .gitignore
   ```

3. **Resource Allocation**: Allocate sufficient memory for Neo4j based on repository size
   - Small (<1000 files): 2GB heap
   - Medium (<10000 files): 4GB heap
   - Large (>10000 files): 8GB+ heap

4. **Provider Selection**:
   - **Privacy-sensitive**: Use Ollama (local)
   - **Best quality**: Use OpenAI GPT-4o
   - **Cost-effective**: Use Gemini Flash or Ollama
   - **Minimal mode**: No LLM needed!

## Next Steps

- [Quick Start Guide](quickstart.md) - Start using the system
- [Deployment Guides](../deployment/overview.md) - Detailed deployment instructions
- [Troubleshooting](../troubleshooting.md) - Common configuration issues
