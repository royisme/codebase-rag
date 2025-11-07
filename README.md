# Code Graph Knowledge System

A comprehensive intelligent knowledge management system for software development, leveraging Neo4j GraphRAG technology to build advanced code intelligence and automated development assistance.

## Overview

Code Graph Knowledge System is an enterprise-grade solution that transforms unstructured development documentation and code into a structured, queryable knowledge graph. By combining vector search, graph database technology, and large language models, it provides intelligent code analysis, documentation management, and development assistance capabilities.

## Key Features

### Current Features (Phase 1: Document Intelligence & Vector Search)
- **Multi-format Document Processing**: Support for various document formats including text, markdown, PDF, and code files
- **Neo4j GraphRAG Integration**: Advanced graph-based retrieval augmented generation using Neo4j's native vector index
- **Universal SQL Schema Parser**: Configurable database schema analysis with industry-specific templates
- **Intelligent Query Engine**: Hybrid search combining vector similarity and graph traversal
- **Asynchronous Task Processing**: Background processing for large document collections with real-time monitoring
- **Real-time Task Monitoring**: Multiple real-time monitoring solutions
  - Web UI Monitoring: NiceGUI interface with file upload and directory batch processing
  - SSE Streaming API: HTTP Server-Sent Events for real-time task progress updates
  - MCP Real-time Tools: AI assistant integrated task monitoring tools
- **Multi-Database Support**: Oracle, MySQL, PostgreSQL, SQL Server schema parsing and analysis
- **RESTful API**: Complete API endpoints for document management and knowledge querying
- **MCP Protocol Support**: Model Context Protocol integration for AI assistant compatibility
- **Multi-provider LLM Support**: Compatible with Ollama, OpenAI, Gemini, and OpenRouter models
- **Large File Handling Strategy**: Intelligent file size detection with multiple processing approaches

### Technical Architecture
- **FastAPI Backend**: High-performance async web framework
- **Neo4j Database**: Graph database with native vector search capabilities
- **LlamaIndex Integration**: Advanced document processing and retrieval pipeline
- **Flexible Embedding Models**: Support for HuggingFace and Ollama embedding models
- **Modular Design**: Clean separation of concerns with pluggable components

## Project Roadmap

### Phase 2: Structured Data & Graph Enhancement (SQL & Graph-Awareness)
**Objective**: Integrate SQL file parsing capabilities and build a comprehensive knowledge graph for precise structured queries.

**Completed Features**:
- ✅ **Universal SQL Schema Parser** with configurable business domain classification
- ✅ **Multi-dialect Support** (Oracle, MySQL, PostgreSQL, SQL Server)
- ✅ **Pre-built Industry Templates** (Insurance, E-commerce, Banking, Healthcare)
- ✅ **Configuration-driven** business domain classification via YAML/JSON
- ✅ **Real-world Testing** on 356 table Oracle database with 4,511 columns
- ✅ **Zero-impact Integration** with existing codebase
- ✅ **Professional Documentation** generation

**In Progress**:
- Neo4j knowledge graph integration for schema querying
- Natural language queries for database structure exploration

**Planned Features**:
- Database relationship mapping and foreign key detection
- Cross-reference linking between code and database schemas
- Enhanced graph traversal algorithms
- Structured query optimization

### Phase 3: Deep Code Intelligence & Automation (Code Intelligence & Automation)
**Objective**: Enable the system to "understand" code and introduce asynchronous tasks with Git integration, creating a "living" system.

**Planned Features**:
- Advanced code parsing and analysis (AST-based)
- Function and class relationship mapping
- Git repository integration and change tracking
- Automated code documentation generation
- Code review assistance and suggestions
- Intelligent code completion and refactoring suggestions
- Dependency analysis and impact assessment
- Continuous integration pipeline integration

## Installation

### Prerequisites
- Python 3.13 or higher
- Neo4j 5.0 or higher
- Ollama (optional, for local LLM support)

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/code-graph.git
   cd code-graph
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # or using uv (recommended)
   uv pip install -e .
   ```

3. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Start Neo4j Database**
   ```bash
   # Using Docker
   docker run \
       --name neo4j-code-graph \
       -p 7474:7474 -p 7687:7687 \
       -e NEO4J_AUTH=neo4j/password \
       -e NEO4J_PLUGINS='["apoc"]' \
       neo4j:5.15
   ```

5. **Run the Application**
   ```bash
   # Start main service
   python start.py
   # or use script entry points
   uv run server
   
   # Start MCP service (optional)
   python start_mcp.py
   # or use script entry points
   uv run mcp_client
   ```

6. **Access the Interface**
   - API Documentation: http://localhost:8000/docs
   - Task Monitor: http://localhost:8000/ui/monitor
   - Real-time SSE Monitor: http://localhost:8000/api/v1/sse/tasks
   - Health Check: http://localhost:8000/api/v1/health

## API Usage

### Adding Documents
```python
import httpx

# Add a single document
response = httpx.post("http://localhost:8000/api/v1/documents/", json={
    "content": "Your document content here",
    "title": "Document Title",
    "metadata": {"source": "manual", "type": "documentation"}
})

# Add a file
response = httpx.post("http://localhost:8000/api/v1/documents/file", json={
    "file_path": "/path/to/your/document.md"
})

# Add a directory
response = httpx.post("http://localhost:8000/api/v1/documents/directory", json={
    "directory_path": "/path/to/docs",
    "recursive": true,
    "file_extensions": [".md", ".txt", ".py"]
})
```

### Querying Knowledge
```python
# Query the knowledge base
response = httpx.post("http://localhost:8000/api/v1/knowledge/query", json={
    "question": "How does the authentication system work?",
    "mode": "hybrid",  # or "graph_only", "vector_only"
    "use_tools": False,
    "top_k": 5
})

# Search similar documents
response = httpx.post("http://localhost:8000/api/v1/knowledge/search", json={
    "query": "user authentication",
    "top_k": 10
})
```

## Real-time Task Monitoring

The system provides three real-time task monitoring approaches:

### 1. Web UI Monitoring Interface
Access http://localhost:8000/ui/monitor for graphical monitoring:
- Real-time task status updates
- File upload functionality (50KB size limit)
- Directory batch processing
- Task progress visualization

### 2. Server-Sent Events (SSE) API
Real-time monitoring via HTTP streaming endpoints:

```javascript
// Monitor single task
const eventSource = new EventSource('/api/v1/sse/task/task-id');
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Task progress:', data.progress);
};

// Monitor all tasks
const allTasksSource = new EventSource('/api/v1/sse/tasks');
```

### 3. MCP Real-time Tools
Task monitoring via MCP protocol:

```python
# Use pure MCP client monitoring
# See examples/pure_mcp_client.py

# Monitor single task
result = await session.call_tool("watch_task", {
    "task_id": task_id,
    "timeout": 300,
    "interval": 1.0
})

# Monitor multiple tasks
result = await session.call_tool("watch_tasks", {
    "task_ids": [task1, task2, task3],
    "timeout": 300
})
```

## MCP Integration

The system supports Model Context Protocol (MCP) for seamless integration with AI assistants:

```bash
# Start MCP server
python start_mcp.py

# Or integrate with your MCP client
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["start_mcp.py"],
      "cwd": "/path/to/code-graph"
    }
  }
}
```

### Client Implementation Examples
- `examples/pure_mcp_client.py`: Pure MCP client using MCP tools for monitoring
- `examples/hybrid_http_sse_client.py`: HTTP + SSE hybrid approach

## Configuration

Key configuration options in `.env`:

```bash
# Application
APP_NAME=Code Graph Knowledge System
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Monitoring Interface
ENABLE_MONITORING=true        # Enable/disable web monitoring interface
MONITORING_PATH=/ui          # Base path for monitoring interface

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# LLM Configuration
LLM_PROVIDER=ollama  # or openai, gemini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text

# Processing Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=10
VECTOR_DIMENSION=768
```

## Development

### Project Structure
```
code_graph/
├── api/                    # FastAPI route handlers
├── core/                   # Application core (FastAPI setup, middleware)
├── services/               # Business logic services
│   ├── neo4j_knowledge_service.py      # Neo4j knowledge graph service
│   ├── sql_schema_parser.py            # Legacy SQL parser (insurance-specific)
│   ├── universal_sql_schema_parser.py  # Universal configurable SQL parser
│   ├── sql_parser.py                   # Individual SQL statement parser
│   └── task_queue.py                   # Asynchronous task management
├── monitoring/             # Task monitoring interface (NiceGUI)
├── configs/                # Configuration files
│   └── insurance_schema_config.yaml    # Example schema parser configuration
├── data/                   # Data storage and models
├── tests/                  # Test suite including SQL parser tests
├── docs/                   # Documentation
└── config.py              # Configuration management
```

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black .
isort .

# Run linting
ruff check .
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [GitHub Wiki](https://github.com/yourusername/code-graph/wiki)
- Neo4j Technical Guide: [README_Neo4j.md](README_Neo4j.md)
- Issues: [GitHub Issues](https://github.com/yourusername/code-graph/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/code-graph/discussions)

## Acknowledgments

- [Neo4j](https://neo4j.com/) for the powerful graph database technology
- [LlamaIndex](https://llamaindex.ai/) for the document processing framework
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [NiceGUI](https://nicegui.io/) for the monitoring interface
