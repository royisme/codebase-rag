# Quick Start Guide - Codebase RAG v0.2

This guide will help you get started with codebase-rag v0.2 in 5 minutes.

## Prerequisites

- Python 3.12+
- Neo4j 5.0+ (or use Docker Compose)
- Git

## Option 1: Docker Compose (Recommended)

The easiest way to get started:

```bash
# Start Neo4j and codebase-rag
docker-compose -f docker-compose.v02.yml up -d

# Wait for services to start (~30 seconds)
docker-compose -f docker-compose.v02.yml logs -f codebase-rag

# Initialize Neo4j schema
docker-compose -f docker-compose.v02.yml exec codebase-rag \
  ./scripts/neo4j_bootstrap.sh

# Access the API
curl http://localhost:8123/api/v1/health
```

API will be available at http://localhost:8123

## Option 2: Manual Setup

### 1. Install Dependencies

```bash
# Install the package
pip install -e .

# Or install just the core dependencies
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv loguru neo4j httpx
```

### 2. Configure Environment

```bash
# Copy example env file
cp env.example .env

# Edit .env and set:
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=password
```

### 3. Initialize Neo4j Schema

Make sure Neo4j is running, then:

```bash
./scripts/neo4j_bootstrap.sh
```

### 4. Start the Server

```bash
# Using the startup script
python start_v02.py

# Or using uvicorn directly
uvicorn backend.app.main:app --host 0.0.0.0 --port 8123
```

## Quick Test

Once the server is running:

### 1. Health Check

```bash
curl http://localhost:8123/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "neo4j": "connected"
  },
  "version": "0.2.0"
}
```

### 2. Ingest a Repository

```bash
curl -X POST http://localhost:8123/api/v1/ingest/repo \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/path/to/your/repo",
    "include_globs": ["**/*.py", "**/*.ts"],
    "exclude_globs": ["**/node_modules/**", "**/.git/**"]
  }'
```

Expected response:
```json
{
  "task_id": "ing-20251103-120000-abc123",
  "status": "done",
  "message": "Successfully ingested 42 files",
  "files_processed": 42
}
```

### 3. Search Related Files

```bash
curl "http://localhost:8123/api/v1/graph/related?repoId=your-repo&query=authentication&limit=5"
```

Expected response:
```json
{
  "nodes": [
    {
      "type": "file",
      "ref": "ref://file/src/auth/handler.py#L1-L200",
      "path": "src/auth/handler.py",
      "lang": "python",
      "score": 0.85,
      "summary": "Python file handler.py in auth/ directory"
    }
  ],
  "query": "authentication",
  "repo_id": "your-repo"
}
```

### 4. Get Context Pack

```bash
curl "http://localhost:8123/api/v1/context/pack?repoId=your-repo&stage=plan&budget=1500&keywords=auth,login"
```

Expected response:
```json
{
  "items": [
    {
      "kind": "file",
      "title": "auth/handler.py",
      "summary": "Python file handler.py in auth/ directory",
      "ref": "ref://file/src/auth/handler.py#L1-L200",
      "extra": {
        "lang": "python",
        "score": 0.85
      }
    }
  ],
  "budget_used": 412,
  "budget_limit": 1500,
  "stage": "plan",
  "repo_id": "your-repo"
}
```

## API Documentation

Once the server is running, visit:
- **Interactive Docs**: http://localhost:8123/docs
- **ReDoc**: http://localhost:8123/redoc

## Using the ref:// Handles

The API returns `ref://` handles that can be used with MCP tools:

```
ref://file/src/auth/handler.py#L1-L200
```

These handles represent code locations that can be resolved by:
1. MCP tools (like `active-file` or `context7`)
2. Your own tooling to fetch actual code content
3. IDE integrations

## Example Workflow

1. **Ingest your codebase**
   ```bash
   ./scripts/demo_curl.sh
   ```

2. **Search for relevant files**
   - Use `/graph/related` to find files related to your task

3. **Build context packs**
   - Use `/context/pack` to create compact context for LLM prompts
   - Adjust budget and keywords based on your needs

4. **Use ref:// handles**
   - Pass handles to MCP tools to fetch actual code
   - Keep prompts compact by using handles instead of full code

## Troubleshooting

### Neo4j Connection Failed

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Check connection
cypher-shell -u neo4j -p password "RETURN 1"
```

### Schema Initialization Failed

```bash
# Manually run schema
cat backend/app/services/graph/schema.cypher | \
  cypher-shell -u neo4j -p password
```

### Import Errors

```bash
# Ensure package is installed
pip install -e .

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

## Next Steps

- See [README_v02.md](README_v02.md) for full API documentation
- Check [backend/app/](backend/app/) for implementation details
- Explore [scripts/](scripts/) for utility scripts
- Plan v0.3 features: AST parsing, symbol extraction, impact analysis

## Support

For issues or questions:
1. Check the logs: `docker-compose -f docker-compose.v02.yml logs`
2. Verify health: `curl http://localhost:8123/api/v1/health`
3. Review [README_v02.md](README_v02.md) for detailed documentation
