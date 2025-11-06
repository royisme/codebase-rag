# Minimal Mode Deployment

Minimal Mode provides **Code Graph functionality only** - no LLM or embedding model required. Perfect for:

- Resource-constrained environments
- Privacy-sensitive projects
- Cost-conscious deployments
- Pure code analysis without AI

## Features Available

### ✅ What's Included

- **Repository Ingestion**: Parse and index code repositories
- **Fulltext Search**: Fast code search using Neo4j native indexes
- **Graph Traversal**: Navigate code relationships (calls, imports, inheritance)
- **Impact Analysis**: Find what code depends on a given symbol
- **Context Packing**: Intelligently select relevant code for LLM context

### ❌ What's Not Included

- Vector similarity search (no embeddings)
- Memory Store for AI agents
- LLM-powered auto-extraction
- Knowledge RAG document Q&A

## System Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB SSD
- **Docker**: 20.10+
- **Neo4j**: 5.0+ (included)

### Recommended
- **CPU**: 4 cores
- **RAM**: 8GB
- **Disk**: 50GB SSD

## Quick Start

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/royisme/codebase-rag.git
cd codebase-rag

# Copy minimal environment template
cp docker/.env.template/.env.minimal .env

# Edit configuration
nano .env
```

### 2. Configure Environment

Edit `.env`:

```bash
# Neo4j Configuration (required)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change_this_password  # ⚠️ Change this!
NEO4J_DATABASE=neo4j

# Deployment Mode
DEPLOYMENT_MODE=minimal
ENABLE_KNOWLEDGE_RAG=false
ENABLE_AUTO_EXTRACTION=false
```

### 3. Start Services

```bash
# Using Makefile (recommended)
make docker-minimal

# Or using docker-compose directly
docker-compose -f docker/docker-compose.minimal.yml up -d

# Or using helper script
./scripts/docker-deploy.sh
# Choose option 1: Minimal
```

### 4. Verify Deployment

```bash
# Check containers
docker ps
# Should show: codebase-rag-mcp-minimal and codebase-rag-neo4j

# Check Neo4j
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p your_password
# Run: RETURN 'Connected' as status;

# View logs
docker logs codebase-rag-mcp-minimal
```

## MCP Client Configuration

Configure Claude Desktop or VS Code to use the minimal MCP server:

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "codebase-rag-minimal": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "codebase-rag-mcp-minimal",
        "python",
        "start_mcp.py",
        "--mode=minimal"
      ]
    }
  }
}
```

### VS Code with MCP Extension

Add to VS Code settings:

```json
{
  "mcp.servers": {
    "codebase-rag-minimal": {
      "command": "docker",
      "args": ["exec", "-i", "codebase-rag-mcp-minimal", "python", "start_mcp.py", "--mode=minimal"],
      "type": "stdio"
    }
  }
}
```

## Available MCP Tools

Minimal mode provides 4 core Code Graph tools:

### 1. code_graph_ingest_repo

Index a code repository:

```json
{
  "local_path": "/repos/myproject",
  "mode": "full"
}
```

### 2. code_graph_fulltext_search

Search code by keywords:

```json
{
  "query": "authentication middleware",
  "language": "python",
  "limit": 20
}
```

### 3. code_graph_impact_analysis

Find code dependencies:

```json
{
  "symbol": "UserService.authenticate",
  "direction": "reverse"
}
```

### 4. code_graph_pack_context

Build intelligent context for LLM:

```json
{
  "entry_points": ["src/api/routes.py"],
  "task_type": "implement",
  "token_budget": 8000
}
```

## Usage Examples

### Example 1: Index and Search

```bash
# 1. Ingest repository
# (Via Claude or MCP client)
Tool: code_graph_ingest_repo
Input: {"local_path": "/repos/myapp", "mode": "full"}

# 2. Search for authentication code
Tool: code_graph_fulltext_search
Input: {"query": "JWT token validation", "language": "python"}

# 3. Analyze impact of changing auth function
Tool: code_graph_impact_analysis
Input: {"symbol": "validate_token", "direction": "reverse"}
```

### Example 2: Prepare Context for Code Review

```bash
# Pack relevant context for reviewing auth changes
Tool: code_graph_pack_context
Input: {
  "entry_points": ["src/auth/jwt.py", "src/middleware/auth.py"],
  "task_type": "review",
  "token_budget": 12000
}
```

## Performance Optimization

### Neo4j Tuning

For large repositories, adjust Neo4j memory in `docker-compose.minimal.yml`:

```yaml
services:
  neo4j:
    environment:
      - NEO4J_server_memory_heap_initial__size=2G
      - NEO4J_server_memory_heap_max__size=4G
      - NEO4J_server_memory_pagecache_size=2G
```

### Ingestion Performance

```bash
# Incremental updates for large repos
Tool: code_graph_ingest_repo
Input: {"local_path": "/repos/myapp", "mode": "incremental"}

# Full re-index when needed
Input: {"local_path": "/repos/myapp", "mode": "full"}
```

## Monitoring

Check system health:

```bash
# Container stats
docker stats codebase-rag-mcp-minimal codebase-rag-neo4j

# Neo4j query performance
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p password
# Run: CALL dbms.listQueries();

# View ingestion logs
docker logs -f codebase-rag-mcp-minimal
```

## Upgrading to Standard/Full Mode

When you need more features:

```bash
# Stop minimal mode
docker-compose -f docker/docker-compose.minimal.yml down

# Copy and configure for standard mode
cp docker/.env.template/.env.standard .env
nano .env  # Add embedding configuration

# Start standard mode
docker-compose -f docker/docker-compose.standard.yml up -d
```

Your Neo4j data persists, so existing code graphs are preserved.

## Troubleshooting

### Neo4j Connection Failed

```bash
# Check Neo4j status
docker logs codebase-rag-neo4j

# Verify Neo4j is ready
docker exec codebase-rag-neo4j neo4j status

# Test connection
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p password
```

### Ingestion Stuck

```bash
# Check MCP server logs
docker logs codebase-rag-mcp-minimal

# Check disk space
df -h

# Restart if needed
docker restart codebase-rag-mcp-minimal
```

### Poor Search Results

```bash
# Rebuild fulltext indexes
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p password

# Run these queries:
CALL db.index.fulltext.drop('code_search');
CALL db.index.fulltext.createNodeIndex('code_search', ['Function', 'Class'], ['name', 'content']);
```

## Cost Analysis

Minimal mode is the most cost-effective option:

- **Infrastructure**: ~$5-10/month (small VPS)
- **LLM costs**: $0 (no LLM required)
- **Embedding costs**: $0 (no embeddings)
- **Total**: ~$5-10/month for hosting only

Perfect for individual developers and small teams!

## Next Steps

- [Docker Guide](docker.md) - Advanced Docker configuration
- [Code Graph User Guide](../guide/code-graph/overview.md) - Learn all features
