# Codebase RAG v0.2 - Minimal Viable API

This document describes the v0.2 implementation of codebase-rag, providing 3 minimal APIs for code knowledge management without requiring LLM for basic operations.

## Architecture

```
backend/
  app/
    main.py                          # FastAPI application
    config.py                        # Configuration
    dependencies.py                  # FastAPI dependencies
    routers/
      ingest.py                      # POST /ingest/repo
      graph.py                       # GET /graph/related
      context.py                     # GET /context/pack
    services/
      ingest/
        code_ingestor.py            # Code scanning & ingestion
        git_utils.py                # Git operations (clone/checkout)
      graph/
        neo4j_service.py            # Neo4j connection & queries
        schema.cypher               # Database schema
      ranking/
        ranker.py                   # BM25/keyword ranking
      context/
        pack_builder.py             # Context pack builder
    models/
      ingest_models.py              # Ingest request/response models
      graph_models.py               # Graph query models
      context_models.py             # Context pack models
scripts/
  neo4j_bootstrap.sh                # Initialize Neo4j schema
  demo_curl.sh                      # Demo API calls
```

## Features (v0.2)

### 1. Repository Ingestion API
**Endpoint:** `POST /api/v1/ingest/repo`

Ingests a code repository into Neo4j knowledge graph:
- Supports local paths and remote git URLs
- File pattern matching (include/exclude globs)
- Creates Repo and File nodes
- Fulltext indexing for search

**Request:**
```json
{
  "repo_url": "https://github.com/user/repo.git",  // or use local_path
  "local_path": null,
  "branch": "main",
  "include_globs": ["**/*.py", "**/*.ts", "**/*.tsx"],
  "exclude_globs": ["**/node_modules/**", "**/.git/**"]
}
```

**Response:**
```json
{
  "task_id": "ing-20251103-120000-abc123",
  "status": "done",
  "message": "Successfully ingested 42 files",
  "files_processed": 42
}
```

### 2. Related Files API
**Endpoint:** `GET /api/v1/graph/related`

Searches for related files using fulltext + keyword matching:
- Neo4j fulltext search
- Keyword relevance ranking
- Returns file summaries with ref:// handles

**Query Parameters:**
- `query`: Search query (e.g., "auth token")
- `repoId`: Repository ID
- `limit`: Max results (default: 30)

**Response:**
```json
{
  "nodes": [
    {
      "type": "file",
      "ref": "ref://file/src/auth/token.py#L1-L200",
      "path": "src/auth/token.py",
      "lang": "python",
      "score": 0.83,
      "summary": "Python file token.py in auth/ directory"
    }
  ],
  "query": "auth token",
  "repo_id": "my-repo"
}
```

### 3. Context Pack API
**Endpoint:** `GET /api/v1/context/pack`

Builds a context pack within token budget:
- Uses /graph/related results
- Budget-aware item selection
- Focus path prioritization
- Returns structured context for LLM prompts

**Query Parameters:**
- `repoId`: Repository ID
- `stage`: Stage (plan/review/implement)
- `budget`: Token budget (default: 1500)
- `keywords`: Comma-separated keywords (optional)
- `focus`: Comma-separated focus paths (optional)

**Response:**
```json
{
  "items": [
    {
      "kind": "file",
      "title": "auth/token.py",
      "summary": "Python file token.py in auth/ directory",
      "ref": "ref://file/src/auth/token.py#L1-L200",
      "extra": {
        "lang": "python",
        "score": 0.83
      }
    }
  ],
  "budget_used": 412,
  "budget_limit": 1500,
  "stage": "plan",
  "repo_id": "my-repo"
}
```

## Setup

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Configure Environment
Copy `env.example` to `.env` and configure:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 3. Initialize Neo4j Schema
```bash
./scripts/neo4j_bootstrap.sh
```

Or manually with cypher-shell:
```bash
cat backend/app/services/graph/schema.cypher | cypher-shell -u neo4j -p password
```

### 4. Run Server
```bash
# Using the new backend app
cd backend/app
python main.py

# Or using uvicorn directly
uvicorn backend.app.main:app --host 0.0.0.0 --port 8123
```

## API Usage Examples

### Ingest a Repository
```bash
curl -X POST http://localhost:8123/api/v1/ingest/repo \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/path/to/repo",
    "include_globs": ["**/*.py", "**/*.ts"],
    "exclude_globs": ["**/node_modules/**", "**/.git/**"]
  }'
```

### Search Related Files
```bash
curl "http://localhost:8123/api/v1/graph/related?repoId=my-repo&query=auth%20token&limit=10"
```

### Get Context Pack
```bash
curl "http://localhost:8123/api/v1/context/pack?repoId=my-repo&stage=plan&budget=1500&keywords=auth,token"
```

## ref:// Handle Format

All file references use the `ref://` handle format for MCP integration:

```
ref://file/<relative-path>#L<start>-L<end>
```

Examples:
- `ref://file/src/auth/token.py#L1-L200`
- `ref://file/src/services/auth.ts#L1-L300`

These handles can be resolved by MCP tools (like `active-file` or `context7`) to fetch actual code content on demand.

## Neo4j Schema

### Nodes
- **Repo**: `{id: string}`
- **File**: `{repoId: string, path: string, lang: string, size: int, content: string, sha: string}`

### Relationships
- `(File)-[:IN_REPO]->(Repo)`

### Indexes
- Fulltext index on `File.path`, `File.lang`, `File.content`
- Constraint: Repo.id is unique
- Constraint: (File.repoId, File.path) is node key

## Integration with CoPal

CoPal can use these APIs through MCP hooks:

1. **Analysis Phase**: Call `/graph/related` to find relevant modules
2. **Planning Phase**: Call `/context/pack` with stage=plan to get context
3. **Review Phase**: Use context pack to assess impact

The ref:// handles in responses can be used with MCP tools to fetch code on demand, keeping prompts compact.

## Roadmap

### v0.3 (Code Graph)
- AST parsing for Python/TypeScript
- Symbol nodes (functions, classes)
- IMPORTS and CALLS relationships
- Impact analysis API

### v0.4 (Hybrid Retrieval & Incremental)
- Vector embeddings + hybrid search
- Git diff incremental updates
- Enhanced context pack with deduplication

### v0.5 (MCP & Observability)
- MCP server wrapper
- Prometheus metrics
- Docker compose setup

## Testing

```bash
# Run demo script
./scripts/demo_curl.sh

# Test specific endpoints
python -m pytest tests/  # (tests to be added)
```

## License

See main repository LICENSE file.
