# Changelog

All notable changes to the Code Graph Knowledge System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- API authentication with JWT
- Web-based configuration UI
- Multi-provider LLM support (simultaneous)
- Advanced code refactoring suggestions
- Rust, C++, C# language support
- Real-time collaboration features
- Plugin system for custom extensions

## [0.7.0] - 2025-01-15

### Added - Automatic Memory Extraction
- **Conversation Analysis**: Extract memories from AI conversation history
  - LLM-powered decision and experience detection
  - Confidence scoring for automatic saving
  - Configurable auto-save threshold
- **Git Commit Analysis**: Analyze git commits for architectural decisions
  - Parse commit messages and changed files
  - Extract decisions, experiences, and conventions
  - Link memories to specific commits
- **Code Comment Mining**: Extract TODO, FIXME, NOTE, DECISION markers
  - Automatic scanning of code comments
  - Convert markers to structured memories
  - Track technical debt and action items
- **Query-based Memory Suggestions**: Suggest important memories from Q&A
  - Analyze knowledge base queries and answers
  - Identify information worth remembering
  - Suggest memory creation with auto-populated fields
- **Batch Repository Extraction**: Comprehensive codebase analysis
  - Extract from git history (configurable commit limit)
  - Mine code comments across file patterns
  - Bulk memory creation from repository insights

### Added - New MCP Tools (5 tools)
- `extract_from_conversation`: Extract memories from conversation history
- `extract_from_git_commit`: Analyze git commits for memories
- `extract_from_code_comments`: Mine code comments for action items
- `suggest_memory_from_query`: Suggest memories from Q&A sessions
- `batch_extract_from_repository`: Full repository analysis

### Added - New API Endpoints (5 endpoints)
- `POST /api/v1/memory/extract/conversation`: Extract from conversations
- `POST /api/v1/memory/extract/commit`: Extract from git commits
- `POST /api/v1/memory/extract/comments`: Extract from code comments
- `POST /api/v1/memory/suggest`: Suggest memory from query/answer
- `POST /api/v1/memory/extract/batch`: Batch repository extraction

### Changed
- Enhanced memory extraction service with LLM-powered analysis
- Improved error messages for memory operations
- Updated MCP handler architecture documentation
- Enhanced memory search relevance scoring

### Fixed
- Neo4j connection timeout in Docker environments
- Memory search not finding recently added memories
- Environment variable handling in Docker deployment
- Race condition in concurrent memory additions

### Documentation
- Added comprehensive memory extraction guide
- Updated API documentation with extraction endpoints
- New examples for automatic memory extraction
- Enhanced troubleshooting guide

## [0.6.0] - 2024-12-20

### Added - Memory Store for AI Agents
- **Memory Management System**: Long-term project knowledge persistence
  - Decision memory type: Architecture and technical choices
  - Preference memory type: Coding styles and conventions
  - Experience memory type: Problems encountered and solutions
  - Convention memory type: Team rules and standards
  - Plan memory type: Future improvements and TODOs
  - Note memory type: General project information
- **Memory Operations**: Full CRUD operations for memories
  - Add memory with importance scoring
  - Search memories with semantic search
  - Update existing memories
  - Delete memories (soft delete)
  - Supersede memories (version history)
  - Project memory summaries
- **Memory Relationships**: Graph-based memory connections
  - `BELONGS_TO`: Memory to project relationships
  - `RELATES_TO`: Inter-memory relationships
  - `SUPERSEDES`: Memory version history

### Added - Multi-Language Support (3 languages)
- **Java Support**: Complete Java code analysis
  - Import statement parsing (standard and static)
  - Class inheritance and interface tracking
  - Method visibility detection (public/protected/private)
  - Package dependency mapping
- **PHP Support**: PHP code analysis
  - Use statement parsing (class, function, const)
  - Require/include dependency tracking
  - Class extends and implements relationships
  - Function type hint extraction
- **Go Support**: Golang code analysis
  - Package import parsing (single and blocks)
  - Struct and interface detection
  - Function and method extraction (with receivers)
  - Package alias tracking

### Added - Docker Multi-Mode Deployment
- **Three deployment modes**:
  - Minimal: Code Graph only (~800MB)
  - Standard: Code Graph + Memory (~1.2GB)
  - Full: All features (~1.5GB)
- **Docker Compose configurations**:
  - `docker-compose.minimal.yml`
  - `docker-compose.standard.yml`
  - `docker-compose.full.yml`
- **Multi-platform support**: amd64, arm64
- **Helper scripts**: Simplified deployment commands

### Added - MCP Tools (7 memory tools)
- `add_memory`: Save new project knowledge
- `search_memories`: Find relevant memories
- `get_memory`: Retrieve specific memory
- `update_memory`: Modify existing memory
- `delete_memory`: Remove memory
- `supersede_memory`: Create new memory that replaces old one
- `get_project_summary`: Get project memory overview

### Added - API Endpoints (7 memory endpoints)
- `POST /api/v1/memory/add`: Add new memory
- `POST /api/v1/memory/search`: Search memories
- `GET /api/v1/memory/{memory_id}`: Get specific memory
- `PUT /api/v1/memory/{memory_id}`: Update memory
- `DELETE /api/v1/memory/{memory_id}`: Delete memory
- `POST /api/v1/memory/supersede`: Supersede old memory
- `GET /api/v1/memory/project/{project_id}/summary`: Project summary

### Changed
- Updated file patterns to include Java, PHP, Go files
- Enhanced code graph to support new language relationships
- Improved transformer architecture for multi-language support

### Documentation
- Added Memory Store user guide
- Added memory API documentation
- Updated examples with memory usage
- Enhanced CLAUDE.md with memory workflows

## [0.5.0] - 2024-11-15

### Added - MCP Protocol Support
- **Official MCP SDK Integration**: Model Context Protocol v1.1.0+
- **Modular Architecture**: Handler-based design (310-line main server)
  - Knowledge handlers: Query, search, document management
  - Code graph handlers: Ingestion, analysis, statistics
  - System handlers: Health checks, configuration
  - Task handlers: Background processing, monitoring
- **30 MCP Tools**: Comprehensive AI assistant integration
  - 8 knowledge tools
  - 10 code graph tools
  - 4 system tools
  - 8 task monitoring tools
- **Advanced Features**:
  - Session management framework
  - Streaming support (SSE)
  - Multi-transport capability (stdio, SSE, WebSocket)

### Added - Prometheus Metrics
- **15+ metrics** for monitoring:
  - Request counters (total, by endpoint, by status)
  - Request duration histograms
  - Active request gauges
  - Neo4j operation metrics
  - Document processing metrics
  - Error rate tracking
- **Metrics endpoint**: `GET /api/v1/metrics`
- **Grafana dashboard** configuration (optional)

### Added - Neo4j Health Monitoring
- Connection status tracking
- Query performance metrics
- Database size monitoring
- Index usage statistics

### Changed
- Refactored MCP server from 1400 lines to 310 lines (78% reduction)
- Extracted handlers into `mcp_tools/` package
- Improved error handling and logging
- Enhanced code organization and maintainability

### Documentation
- Added MCP v2 modularization guide
- Updated MCP integration documentation
- Added Prometheus metrics documentation
- Enhanced deployment guides

## [0.4.0] - 2024-10-20

### Added - Real-time Task Monitoring
- **Web UI Monitoring**: NiceGUI-based monitoring interface
  - Real-time task status updates via WebSocket
  - File upload functionality (50KB size limit)
  - Directory batch processing
  - Task progress visualization
  - Accessible at `/ui/monitor` when `ENABLE_MONITORING=true`
- **Server-Sent Events (SSE)**: Streaming APIs for real-time updates
  - `/api/v1/sse/task/{task_id}`: Monitor single task
  - `/api/v1/sse/tasks`: Monitor all tasks with filtering
  - `/api/v1/sse/stats`: SSE connection statistics
- **Task Queue System**: Background processing with monitoring
  - Async task execution
  - Progress tracking
  - Error handling and retry logic
  - Task history and logs

### Added - Large File Handling
- **Multi-strategy approach**:
  - Direct processing: Files < 10KB
  - Temporary file strategy: Files 10-50KB
  - Directory processing prompt: Files > 50KB
  - MCP automatic temp files: All sizes
- **Configurable limits**: Size thresholds via environment variables

### Added - Client Examples
- `examples/pure_mcp_client.py`: Pure MCP client with watch tools
- `examples/hybrid_http_sse_client.py`: HTTP + SSE hybrid approach
- Real-time monitoring demonstrations

### Changed
- Enhanced file upload handling with size validation
- Improved error messages for large file uploads
- Better timeout handling for large documents

### Fixed
- Memory leaks in long-running tasks
- SSE connection stability issues
- File upload timeout for large files

## [0.3.0] - 2024-09-15

### Added - Universal SQL Schema Parser
- **Multi-dialect support**: Oracle, MySQL, PostgreSQL, SQL Server
- **Configurable business domain classification**: YAML/JSON configuration
- **Pre-built industry templates**:
  - Insurance: Policies, claims, underwriting
  - E-commerce: Products, orders, customers
  - Banking: Accounts, transactions, loans
  - Healthcare: Patients, diagnoses, treatments
- **Comprehensive parsing**:
  - Table and column extraction
  - Foreign key relationships
  - Index definitions
  - Business domain classification
- **Professional documentation generation**: Markdown output
- **Real-world tested**: 356-table Oracle database (4,511 columns)

### Added - SQL API Endpoints
- `POST /api/v1/sql/parse`: Parse SQL schema files
- `POST /api/v1/sql/analyze`: Analyze database structure
- `GET /api/v1/sql/templates`: List available templates

### Changed
- Enhanced schema parsing with configurable templates
- Improved relationship detection
- Better error handling for malformed SQL

### Documentation
- Added SQL parsing user guide
- Industry template documentation
- Configuration examples

## [0.2.0] - 2024-08-01

### Added - Multi-Provider LLM Support
- **Ollama integration**: Local LLM hosting (default)
- **OpenAI integration**: GPT models and embeddings
- **Google Gemini integration**: Gemini models and embeddings
- **OpenRouter integration**: Multi-provider access
- **HuggingFace embeddings**: Local embedding models
- **Provider configuration**: Via `.env` file with flexible switching

### Added - Enhanced Configuration
- Environment-based configuration system
- Support for multiple embedding providers
- Configurable timeouts and limits
- Feature flags (monitoring, Prometheus)

### Changed
- Refactored service initialization for multi-provider support
- Improved LLM provider abstraction layer
- Enhanced error messages for provider issues

### Fixed
- OpenAI API compatibility issues
- Gemini embedding dimension mismatches
- Provider-specific timeout handling

## [0.1.0] - 2024-07-01

### Added - Initial Release
- **Core Features**:
  - Neo4j GraphRAG integration
  - Vector search with LlamaIndex
  - Document processing (text, markdown, code)
  - Knowledge graph construction
  - Intelligent query engine
  - RESTful API
- **Code Analysis**:
  - Python code parsing
  - TypeScript/JavaScript parsing
  - Import relationship mapping
  - Basic code graph visualization
- **Document Management**:
  - Multi-format support
  - Asynchronous processing
  - Chunk-based indexing
  - Vector similarity search
- **API Endpoints**:
  - `/api/v1/health`: Health check
  - `/api/v1/knowledge/query`: Query knowledge base
  - `/api/v1/knowledge/search`: Vector search
  - `/api/v1/documents/upload`: Upload documents
  - `/api/v1/documents/list`: List documents
- **Infrastructure**:
  - FastAPI backend
  - Neo4j database
  - Docker support
  - Basic logging and error handling

### Documentation
- Initial README
- API documentation
- Basic deployment guide
- Example scripts

---

## Version History Summary

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| 0.7.0   | 2025-01-15   | Automatic memory extraction (5 tools) |
| 0.6.0   | 2024-12-20   | Memory Store, Multi-language (Java/PHP/Go), Docker modes |
| 0.5.0   | 2024-11-15   | MCP protocol, Prometheus metrics, Modular architecture |
| 0.4.0   | 2024-10-20   | Real-time monitoring, SSE, Large file handling |
| 0.3.0   | 2024-09-15   | Universal SQL parser, Business domain templates |
| 0.2.0   | 2024-08-01   | Multi-provider LLM support (Ollama/OpenAI/Gemini) |
| 0.1.0   | 2024-07-01   | Initial release with core features |

## Upgrade Guides

### Upgrading from 0.6.x to 0.7.0

**No breaking changes**. Simply pull new Docker image:

```bash
docker pull royisme/codebase-rag:0.7.0-full
docker-compose restart
```

**New Features Available:**
- Memory extraction endpoints and MCP tools
- Automatic memory mining from git and code

### Upgrading from 0.5.x to 0.6.0

**Breaking Changes:**
- None, fully backward compatible

**New Configuration Options:**
```env
# Optional: Enable memory features (included in standard/full modes)
ENABLE_MEMORY_STORE=true
```

**Data Migration:**
- No migration needed
- Memory Store creates new nodes in existing Neo4j database

### Upgrading from 0.4.x to 0.5.0

**Breaking Changes:**
- MCP server entry point changed from `mcp_server.py` to `start_mcp.py`

**Configuration Update:**
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["/path/to/start_mcp.py"]  // Changed from mcp_server.py
    }
  }
}
```

**Data Migration:**
- No database changes
- MCP protocol fully backward compatible

### Upgrading from 0.3.x to 0.4.0

**No breaking changes**. New features are opt-in:

```env
# Enable monitoring UI
ENABLE_MONITORING=true

# Enable Prometheus metrics
ENABLE_PROMETHEUS=true
```

## Migration Notes

### Python Version Upgrade
As of v0.6.0, Python 3.13+ is required. If upgrading from older versions:

```bash
# Update Python
python3.13 -m venv .venv
source .venv/bin/activate

# Reinstall dependencies
pip install --upgrade pip
pip install -e .
```

### Neo4j Version Compatibility
All versions support Neo4j 5.0+. No database migration needed between versions.

### Environment Variables
Check `.env.example` for new configuration options in each version.

## Deprecation Notices

### Deprecated in 0.7.0
- None

### Deprecated in 0.6.0
- None

### Deprecated in 0.5.0
- **Old MCP server entry point** (`mcp_server.py`): Use `start_mcp.py` instead
- Will be removed in: v1.0.0

### Removed in 0.5.0
- None

## Contributing

See [CONTRIBUTING.md](./development/contributing.md) for guidelines on contributing to this project.

## Support

- **Documentation**: https://code-graph.vantagecraft.dev
- **Issues**: https://github.com/royisme/codebase-rag/issues
- **Discussions**: https://github.com/royisme/codebase-rag/discussions

## Links

- [Homepage](https://code-graph.vantagecraft.dev)
- [GitHub Repository](https://github.com/royisme/codebase-rag)
- [Docker Hub](https://hub.docker.com/r/royisme/codebase-rag)
- [Issue Tracker](https://github.com/royisme/codebase-rag/issues)

---

**Note**: Dates in this changelog are illustrative. Check [GitHub Releases](https://github.com/royisme/codebase-rag/releases) for actual release dates.
