# Code Graph Knowledge System

Enterprise knowledge management platform with Neo4j graph database, multi-interface architecture (MCP/Web/REST), and intelligent code analysis for modern software development teams.

## Overview

Code Graph Knowledge System is a production-ready platform that transforms code repositories and development documentation into a queryable knowledge graph. Built on Neo4j's graph database technology and powered by large language models, the system provides three distinct interfaces for different use cases: MCP protocol for AI assistants, Web UI for human users, and REST API for programmatic access.

The platform combines vector search, graph traversal, and LLM-driven analysis to deliver intelligent code intelligence capabilities including repository analysis, dependency mapping, impact assessment, and automated documentation generation.

## Core Capabilities

### Multi-Interface Architecture

**MCP Protocol (Port 8000)** - Model Context Protocol server for AI assistant integration
- Direct integration with Claude Desktop, Cursor, and other MCP-compatible tools
- 25+ specialized tools for code analysis and knowledge management
- Real-time task monitoring via Server-Sent Events
- Supports stdio and SSE transport modes

**Web UI (Port 8080)** - Browser-based interface for team collaboration
- Real-time task monitoring dashboard
- Repository ingestion and management
- Metrics visualization with interactive charts
- Built with React 18, TypeScript, and shadcn/ui components

**REST API (Ports 8000, 8080)** - HTTP endpoints for system integration
- Document ingestion and knowledge querying
- Task management and monitoring
- Prometheus metrics export
- OpenAPI/Swagger documentation

### Knowledge Graph Engine

**Code Intelligence** - Graph-based code analysis without requiring LLMs
- Repository structure mapping and dependency tracking
- Function and class relationship analysis
- Impact analysis for code changes
- Context pack generation for AI assistants
- Support for 15+ programming languages

**Memory Store** - Project knowledge tracking with temporal awareness
- Fact, decision, pattern, and insight recording
- Memory evolution with superseding relationships
- Automatic extraction from conversations, commits, and code
- Vector search with embedding-based retrieval

**Knowledge RAG** - Document processing with hybrid search
- Multi-format document ingestion (Markdown, PDF, code files)
- Neo4j native vector indexing
- Hybrid search combining vector similarity and graph traversal
- Configurable chunking and embedding strategies

**SQL Schema Parser** - Database schema analysis with business domain classification
- Multi-dialect support (Oracle, MySQL, PostgreSQL, SQL Server)
- Configurable business domain templates (Insurance, E-commerce, Banking, Healthcare)
- Automated relationship detection and documentation generation
- Integration with knowledge graph for cross-referencing

## Technology Stack

**Backend Infrastructure**
- FastAPI - High-performance async web framework
- Neo4j 5.x - Graph database with native vector indexing
- Python 3.13+ - Modern Python with type hints
- Uvicorn - ASGI server with WebSocket support

**AI and ML Integration**
- LlamaIndex - Document processing and retrieval pipeline
- Multiple LLM providers (Ollama, OpenAI, Gemini, OpenRouter)
- Flexible embedding models (HuggingFace, Ollama, OpenAI)
- Model Context Protocol (MCP) for AI assistant integration

**Frontend Technology**
- React 18 - Modern UI library with concurrent features
- TypeScript - Type-safe development
- TanStack Router - Type-safe routing
- shadcn/ui - Accessible component library
- Vite - Fast build tooling

## Quick Start

### Prerequisites

- Python 3.13 or higher
- Neo4j 5.0 or higher
- Docker (optional, for containerized deployment)
- Node.js 18+ (for frontend development)

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/royisme/codebase-rag.git
cd codebase-rag
pip install -r requirements.txt
# or using uv (recommended)
uv pip install -e .
```

Configure environment variables:

```bash
cp env.example .env
# Edit .env with your Neo4j credentials and LLM provider settings
```

Start Neo4j database:

```bash
docker run --name neo4j-code-graph \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5.15
```

### Running the System

**Complete System (MCP + Web UI + REST API)**

```bash
python start.py
```

Access points:
- MCP SSE Service: `http://localhost:8000/sse`
- Web UI: `http://localhost:8080`
- REST API Documentation: `http://localhost:8080/docs`
- Prometheus Metrics: `http://localhost:8080/metrics`

**MCP Server Only**

```bash
python start_mcp.py
```

### Docker Deployment

Three deployment modes available:

**Minimal Mode** - Code Graph only (no LLM required)
```bash
make docker-minimal
```

**Standard Mode** - Code Graph + Memory Store (embedding model required)
```bash
make docker-standard
```

**Full Mode** - All features (LLM + embedding required)
```bash
make docker-full
```

## Usage Examples

### MCP Integration

Configure in Claude Desktop or compatible MCP client:

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["/path/to/start_mcp.py"],
      "cwd": "/path/to/codebase-rag"
    }
  }
}
```

Available MCP tools include:
- `code_graph_ingest_repo` - Ingest code repository
- `code_graph_related` - Find related code elements
- `code_graph_impact` - Analyze change impact
- `query_knowledge` - Query knowledge base
- `add_memory` - Store project knowledge
- `extract_from_conversation` - Extract insights from chat
- `watch_task` - Monitor task progress

### REST API

**Ingest a repository:**

```bash
curl -X POST http://localhost:8080/api/v1/repositories/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/user/repo.git",
    "mode": "incremental",
    "languages": ["python", "typescript"]
  }'
```

**Query knowledge base:**

```bash
curl -X POST http://localhost:8080/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does authentication work in this codebase?",
    "mode": "hybrid",
    "top_k": 5
  }'
```

**Monitor tasks:**

```bash
curl http://localhost:8080/api/v1/tasks?status=processing
```

### Web UI

Navigate to `http://localhost:8080` to access:

- **Dashboard** - System health and quick actions
- **Tasks** - Real-time task monitoring with progress indicators
- **Repositories** - Repository management and ingestion
- **Metrics** - System performance and usage metrics

## Configuration

Key environment variables:

```bash
# Server Ports
MCP_PORT=8000              # MCP SSE service
WEB_UI_PORT=8080           # Web UI and REST API

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# LLM Provider (ollama, openai, gemini, openrouter)
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Embedding Provider (ollama, openai, gemini, huggingface)
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Processing Configuration
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K=5
VECTOR_DIMENSION=384
```

For complete configuration options, see [Configuration Guide](https://vantagecraft.dev/docs/code-graph/getting-started/configuration).

## Architecture

### Dual-Server Design

The system employs a dual-server architecture optimized for different access patterns:

**Port 8000 (Primary)** - MCP SSE Service
- Server-Sent Events endpoint for real-time communication
- Optimized for AI assistant integration
- Handles long-running task monitoring
- WebSocket support for bidirectional communication

**Port 8080 (Secondary)** - Web UI + REST API
- React-based monitoring interface
- RESTful API for external integrations
- Prometheus metrics endpoint
- Static file serving for frontend

Both servers share the same backend services and Neo4j database, ensuring consistency across all interfaces.

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Client Interfaces                      │
├──────────────┬──────────────┬──────────────────────────┤
│  MCP Client  │   Web UI     │      REST API            │
│  (AI Tools)  │  (Browser)   │   (External Systems)     │
└──────┬───────┴──────┬───────┴──────────┬───────────────┘
       │              │                  │
       └──────────────┼──────────────────┘
                      │
       ┌──────────────▼──────────────┐
       │     FastAPI Application      │
       ├──────────────┬──────────────┤
       │   Services   │  Task Queue  │
       └──────┬───────┴──────┬───────┘
              │              │
       ┌──────▼──────┐  ┌───▼────┐
       │   Neo4j     │  │  LLM   │
       │  Database   │  │Provider│
       └─────────────┘  └────────┘
```

## Development

### Project Structure

```
codebase-rag/
├── src/codebase_rag/
│   ├── api/                    # FastAPI routes
│   ├── core/                   # Application core
│   ├── services/               # Business logic
│   │   ├── code_ingestor.py    # Code repository processing
│   │   ├── graph_service.py    # Graph operations
│   │   ├── memory_store.py     # Project memory management
│   │   ├── neo4j_knowledge_service.py  # Knowledge base
│   │   ├── task_queue.py       # Async task processing
│   │   └── sql/                # SQL parsing services
│   └── mcp/                    # MCP protocol handlers
├── frontend/                   # React Web UI
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── routes/             # Page routes
│   │   └── lib/                # API client
│   └── package.json
├── tests/                      # Test suite
├── docs/                       # Documentation
└── scripts/                    # Utility scripts
```

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Integration tests (requires Neo4j)
pytest tests/ -m integration

# Coverage report
pytest tests/ --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black .
isort .

# Linting
ruff check .
ruff check . --fix

# Type checking
mypy src/
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev        # Start dev server at http://localhost:3000
npm run build      # Build for production
npm run lint       # Check for issues
npm test           # Run tests
```

## Deployment

### Production Deployment

See [Docker Deployment Guide](https://vantagecraft.dev/docs/code-graph/deployment/docker) for production deployment configurations including:

- Multi-stage Docker builds
- Environment-specific configurations
- Scaling and load balancing
- Security best practices
- Monitoring and logging setup

### System Requirements

**Minimum Configuration**
- CPU: 2 cores
- RAM: 4 GB
- Storage: 10 GB

**Recommended Configuration**
- CPU: 4+ cores
- RAM: 8+ GB
- Storage: 50+ GB SSD
- Network: 100 Mbps+

## Documentation

Complete documentation available at [https://vantagecraft.dev/docs/code-graph](https://vantagecraft.dev/docs/code-graph)

### Key Documentation Sections

- [Quick Start Guide](https://vantagecraft.dev/docs/code-graph/getting-started/quickstart) - Get up and running in 5 minutes
- [Architecture Overview](https://vantagecraft.dev/docs/code-graph/architecture/overview) - System design and components
- [MCP Integration](https://vantagecraft.dev/docs/code-graph/guide/mcp/overview) - AI assistant integration
- [REST API Reference](https://vantagecraft.dev/docs/code-graph/api/rest) - Complete API documentation
- [Deployment Guide](https://vantagecraft.dev/docs/code-graph/deployment/overview) - Production deployment
- [Development Guide](https://vantagecraft.dev/docs/code-graph/development/setup) - Contributing and development

## Community and Support

- **Documentation**: [Complete Documentation](https://vantagecraft.dev/docs/code-graph)
- **Neo4j Guide**: [README_Neo4j.md](README_Neo4j.md)
- **Issues**: [GitHub Issues](https://github.com/royisme/codebase-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/royisme/codebase-rag/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with excellent open source technologies:

- [Neo4j](https://neo4j.com/) - Graph database platform
- [LlamaIndex](https://llamaindex.ai/) - Data framework for LLM applications
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for Python
- [React](https://react.dev/) - Library for building user interfaces
- [Model Context Protocol](https://github.com/anthropics/mcp) - AI assistant integration standard