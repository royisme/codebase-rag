# Quick Start Guide

Get Code Graph Knowledge System up and running in 5 minutes!

## 🎯 Choose Your Deployment Mode

Code Graph Knowledge System offers **three deployment modes** based on which features you need:

| Mode | Description | Ports | LLM Required | Use Case |
|------|-------------|-------|--------------|----------|
| **Minimal** | Code Graph only | 7474, 7687, 8000, 8080 | ❌ No | Static code analysis, repository exploration |
| **Standard** | Code Graph + Memory Store | 7474, 7687, 8000, 8080 | Embedding only | Project knowledge tracking, AI agent memory |
| **Full** | All Features + Knowledge RAG | 7474, 7687, 8000, 8080 | LLM + Embedding | Complete intelligent knowledge management |

!!! info "What's Running?"
    All modes start **two servers**:

    - **Port 8000**: MCP SSE Service (for AI assistants)
    - **Port 8080**: Web UI + REST API (for humans & programs)

    See [Architecture Overview](../architecture/overview.md) to understand how these work together.

## 🚀 Choose Your Path

=== "Minimal (Recommended)"
    **Code Graph only** - No LLM required

    Perfect for getting started and trying out the system.

    ```bash
    # Clone repository
    git clone https://github.com/royisme/codebase-rag.git
    cd codebase-rag

    # Initialize environment
    make init-env
    # Choose: minimal

    # Start services
    make docker-minimal
    ```

=== "Standard"
    **Code Graph + Memory** - Embedding required

    ```bash
    git clone https://github.com/royisme/codebase-rag.git
    cd codebase-rag

    # Initialize environment
    make init-env
    # Choose: standard

    # Edit .env and add your embedding provider
    # e.g., EMBEDDING_PROVIDER=ollama

    make docker-standard
    ```

=== "Full"
    **All Features** - LLM + Embedding required

    ```bash
    git clone https://github.com/royisme/codebase-rag.git
    cd codebase-rag

    # Initialize environment
    make init-env
    # Choose: full

    # Edit .env and add your LLM provider
    # e.g., LLM_PROVIDER=ollama

    make docker-full-with-ollama
    ```

## ✅ Verify Installation

After starting the services, verify everything is running:

```bash
# Check service health
make health-check

# View logs
make docker-logs
```

You should see:

- ✅ Neo4j running at http://localhost:7474
- ✅ API running at http://localhost:8000
- ✅ API docs at http://localhost:8000/docs

## 📡 Understanding the Interfaces

After starting the services, you have **three ways** to interact with the system:

### 1. REST API (Port 8080)

**For**: Programmatic access, scripts, CI/CD integration

```bash
# Health check
curl http://localhost:8080/api/v1/health

# Query knowledge
curl -X POST http://localhost:8080/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How does authentication work?"}'
```

**Use cases**:
- Automation scripts
- CI/CD pipelines
- Custom applications
- Testing and monitoring

[Full REST API Documentation](../api/rest.md)

### 2. Web UI (Port 8080)

**For**: Human users, visual monitoring

Open in browser: http://localhost:8080

Features:
- 📊 Task monitoring dashboard
- 📁 File and directory upload
- 📈 System health and statistics
- ⚙️ Configuration management

### 3. MCP Protocol (Port 8000)

**For**: AI assistants (Claude Desktop, Cursor, etc.)

Configure your AI tool to connect via MCP. The system provides 25+ tools for code intelligence.

[MCP Integration Guide](../guide/mcp/overview.md)

---

## 🚀 First Steps

### 1. Access Neo4j Browser

1. Open http://localhost:7474 in your browser
2. Connect with:
   - **URL**: `bolt://localhost:7687`
   - **User**: `neo4j`
   - **Password**: (from your `.env` file)

### 2. Test the API

```bash
# Check health
curl http://localhost:8000/api/v1/health

# Get statistics
curl http://localhost:8000/api/v1/statistics
```

### 3. Ingest Your First Repository

#### Option A: Using REST API

```bash
curl -X POST http://localhost:8000/api/v1/code-graph/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/path/to/your/repo",
    "repo_url": "https://github.com/user/repo",
    "mode": "incremental"
  }'
```

#### Option B: Using MCP (Claude Desktop)

1. Configure Claude Desktop to connect to MCP server
2. Use the tool:

```
code_graph_ingest_repo({
  "local_path": "/path/to/your/repo",
  "mode": "incremental"
})
```

### 4. Search Your Code

```bash
# Find files related to "authentication"
curl -X POST http://localhost:8000/api/v1/code-graph/related \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication",
    "repo_id": "your-repo-name",
    "limit": 10
  }'
```

### 5. Analyze Impact

```bash
# See what depends on a specific file
curl -X POST http://localhost:8000/api/v1/code-graph/impact \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "your-repo-name",
    "file_path": "src/auth/login.py",
    "depth": 2
  }'
```

## 🎓 Next Steps

### Learn Code Graph Features

- [Repository Ingestion](../guide/code-graph/ingestion.md) - Index your codebase
- [Search & Discovery](../guide/code-graph/search.md) - Find related files
- [Impact Analysis](../guide/code-graph/impact.md) - Understand dependencies
- [Context Packing](../guide/code-graph/context.md) - Generate AI context

### Explore Advanced Features

!!! info "Available in Standard/Full modes only"

- [Memory Store](../guide/memory/overview.md) - Project knowledge management
- [Knowledge RAG](../guide/knowledge/overview.md) - Document Q&A
- [Auto Extraction](../guide/memory/extraction.md) - Automated memory curation

### Integrate with Your Workflow

- [Claude Desktop Setup](../guide/mcp/claude-desktop.md) - Use with Claude
- [VS Code Integration](../guide/mcp/vscode.md) - Editor integration
- [API Reference](../api/mcp-tools.md) - Complete tool documentation

## 🔧 Common Issues

### Port Already in Use

If ports 7474, 7687, or 8000 are already in use:

```bash
# Edit .env file
NEO4J_HTTP_PORT=17474
NEO4J_BOLT_PORT=17687
APP_PORT=18000

# Restart
make docker-stop
make docker-minimal
```

### Neo4j Connection Failed

1. Check Neo4j is healthy:
   ```bash
   docker ps | grep neo4j
   docker logs codebase-rag-neo4j
   ```

2. Verify credentials in `.env` match

3. Wait for Neo4j to fully start (can take 30s)

### Ollama Not Found (Full mode)

If using local Ollama on your host:

```env
# In .env file
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

If Ollama is not installed:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2
ollama pull nomic-embed-text
```

## 📚 Documentation Links

- [Deployment Overview](../deployment/overview.md) - Choose the right mode
- [Configuration Guide](configuration.md) - Detailed configuration options
- [Docker Guide](../deployment/docker.md) - Docker-specific information
- [Troubleshooting](../troubleshooting.md) - Common problems and solutions

## 💡 Tips & Tricks

### Use Incremental Mode

Always use `"mode": "incremental"` for repository ingestion. It's 60x faster than full mode.

### Start Small

Test with a small repository first (< 1000 files) before ingesting large monorepos.

### Monitor Resources

```bash
# Watch Docker resource usage
docker stats

# Check Neo4j memory
docker logs codebase-rag-neo4j | grep memory
```

### Batch Operations

For multiple repositories, use the batch ingestion API or write a simple script:

```bash
for repo in repo1 repo2 repo3; do
  curl -X POST http://localhost:8000/api/v1/code-graph/ingest \
    -H "Content-Type: application/json" \
    -d "{\"local_path\": \"/repos/$repo\", \"mode\": \"incremental\"}"
done
```

## 🎉 You're Ready!

Congratulations! You now have Code Graph Knowledge System running.

Try exploring your codebase with the MCP tools or REST API. Check out the [User Guide](../guide/code-graph/overview.md) for detailed feature documentation.

---

**Need help?** Join our [GitHub Discussions](https://github.com/royisme/codebase-rag/discussions) or [report an issue](https://github.com/royisme/codebase-rag/issues).
