# Frequently Asked Questions (FAQ)

Common questions and answers about the Code Graph Knowledge System.

## Table of Contents

- [General Questions](#general-questions)
- [Deployment and Installation](#deployment-and-installation)
- [Features and Capabilities](#features-and-capabilities)
- [LLM Providers and Models](#llm-providers-and-models)
- [Memory Store](#memory-store)
- [Performance and Scaling](#performance-and-scaling)
- [Cost and Resources](#cost-and-resources)
- [Security and Privacy](#security-and-privacy)
- [Integration and APIs](#integration-and-apis)
- [Troubleshooting](#troubleshooting)

## General Questions

### What is Code Graph Knowledge System?

Code Graph Knowledge System is an intelligent knowledge management system designed specifically for software development. It combines:

- **Neo4j Graph Database**: Stores relationships between code, documents, and memories
- **Vector Search**: Semantic search across your codebase and documentation
- **LLM Integration**: AI-powered code analysis and question answering
- **Memory Store**: Long-term knowledge persistence for AI agents
- **MCP Protocol**: Integration with AI assistants like Claude

**Use Cases:**
- Intelligent code navigation and search
- Automated documentation generation
- AI-assisted development with persistent memory
- Code relationship mapping
- Database schema analysis

### What's new in version 0.7?

Version 0.7 introduces **Automatic Memory Extraction**:

- Extract memories from AI conversations
- Analyze git commits for decisions and experiences
- Mine code comments (TODO, FIXME, NOTE markers)
- Suggest important memories from Q&A sessions
- Batch extract from entire repositories

See the [Changelog](./changelog.md) for complete details.

### Is this project open source?

Yes! Code Graph Knowledge System is open source under [appropriate license]. You can:

- View source code on [GitHub](https://github.com/royisme/codebase-rag)
- Contribute improvements
- Fork for custom needs
- Use commercially (check license terms)

### Who maintains this project?

The project is maintained by a team of contributors led by [@royisme](https://github.com/royisme). See [Contributing Guide](./development/contributing.md) to join the community.

## Deployment and Installation

### What are the different deployment modes?

Three Docker deployment modes are available:

**1. Minimal Mode** (Code Graph only)
- **Size**: ~800MB
- **Features**: Code graph, vector search, basic RAG
- **Best for**: Lightweight code analysis, resource-constrained environments
- **RAM**: 2-4GB
- **Pull**: `docker pull royisme/codebase-rag:minimal`

**2. Standard Mode** (Code Graph + Memory)
- **Size**: ~1.2GB
- **Features**: Everything in Minimal + Memory Store for AI agents
- **Best for**: AI-assisted development with memory
- **RAM**: 4-8GB
- **Pull**: `docker pull royisme/codebase-rag:standard`

**3. Full Mode** (All Features)
- **Size**: ~1.5GB
- **Features**: Everything + Web UI, monitoring, Prometheus metrics
- **Best for**: Production deployment, team environments
- **RAM**: 8-16GB
- **Pull**: `docker pull royisme/codebase-rag:full`

### Which deployment mode should I choose?

**Choose Minimal if:**
- You only need code analysis
- Running on limited resources (Raspberry Pi, small VPS)
- Don't need memory features
- Want smallest footprint

**Choose Standard if:**
- Using with AI assistants (Claude Desktop, VSCode)
- Need memory persistence
- Want balanced features and size
- Typical development environment

**Choose Full if:**
- Need web UI for teams
- Want monitoring and metrics
- Production deployment
- Multiple users
- Have resources available

### Can I switch between deployment modes later?

Yes! Data is stored in Neo4j volumes, which are shared across modes:

```bash
# Start with minimal
docker-compose -f docker/docker-compose.minimal.yml up -d

# Later, switch to standard (data preserved)
docker-compose -f docker/docker-compose.minimal.yml down
docker-compose -f docker/docker-compose.standard.yml up -d
```

**Note**: Switching modes doesn't delete your data, but some features may not be available in smaller modes.

### What are the minimum system requirements?

**Development (Minimal Mode):**
- CPU: 2 cores
- RAM: 4GB
- Disk: 10GB
- OS: Linux, macOS, Windows with WSL2

**Development (Standard/Full Mode):**
- CPU: 4 cores
- RAM: 8GB
- Disk: 20GB
- OS: Linux, macOS, Windows with WSL2

**Production:**
- CPU: 8 cores
- RAM: 16GB (32GB with Ollama)
- Disk: 50GB+ (depends on data size)
- OS: Linux (Ubuntu 22.04+ recommended)

### Can I run this without Docker?

Yes, you can run natively:

```bash
# Install Python 3.13+
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Install Neo4j separately
# Follow: https://neo4j.com/docs/operations-manual/current/installation/

# Configure and run
python start.py
```

**Note**: Docker is recommended for easier setup and isolation.

### How do I upgrade to a new version?

```bash
# Pull new images
docker pull royisme/codebase-rag:latest

# Or specific version
docker pull royisme/codebase-rag:0.7.0-full

# Restart with new version
docker-compose down
docker-compose up -d

# Check version
curl http://localhost:8000/api/v1/health | jq .version
```

Your data is preserved in volumes across upgrades.

## Features and Capabilities

### What programming languages are supported?

**Fully Supported** (with import/relationship analysis):
- Python (`.py`)
- TypeScript/JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`)
- Java (`.java`)
- PHP (`.php`)
- Go (`.go`)

**Document Processing** (any file type):
- Markdown (`.md`)
- Text files (`.txt`)
- Code files (analyzed as text if not in supported list)
- SQL files (`.sql`) with schema parsing

**Future Support** (planned):
- Rust, C++, C#, Ruby, Kotlin

### What's the difference between Memory Store and Knowledge Graph?

**Knowledge Graph:**
- **Purpose**: Store documents, code, and their relationships
- **Content**: Code files, documentation, SQL schemas
- **Search**: Vector similarity + graph traversal
- **Updates**: Add/remove documents
- **Use Case**: "Show me all files that import module X"

**Memory Store:**
- **Purpose**: Long-term knowledge for AI agents
- **Content**: Decisions, preferences, experiences, conventions
- **Search**: Semantic search + importance filtering
- **Updates**: Add, update, supersede memories
- **Use Case**: "Remember we decided to use PostgreSQL because..."

**Analogy:**
- Knowledge Graph = Your codebase and documentation
- Memory Store = Your project's institutional memory

### Can I use this with GitHub Copilot or other AI assistants?

**GitHub Copilot**: No direct integration (closed API)

**Claude Desktop**: ✅ Yes, via MCP protocol
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["/path/to/start_mcp.py"]
    }
  }
}
```

**VS Code with MCP**: ✅ Yes (requires MCP extension)

**Any Tool with HTTP API**: ✅ Yes, use REST API
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/query \
  -d '{"query": "how does authentication work?"}'
```

### Can I analyze private repositories?

Yes! All processing is local:

1. **Clone your private repo** to your machine
2. **Ingest with MCP**:
   ```
   Use ingest_directory tool with your repo path
   ```
3. **Or via API**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/ingest/directory \
     -d '{"path": "/path/to/private/repo"}'
   ```

**Privacy**: No code leaves your machine (unless you use cloud LLM providers).

### Does it work with monorepos?

Yes, monorepos are fully supported:

```bash
# Ingest entire monorepo
ingest_directory(/path/to/monorepo)

# Or specific workspaces
ingest_directory(/path/to/monorepo/packages/frontend)
ingest_directory(/path/to/monorepo/packages/backend)

# Query across entire monorepo
query_knowledge("How does the API communicate with frontend?")
```

**Tip**: Use project-specific tags to organize large monorepos.

### Can I customize the code analysis?

Yes, several customization options:

**1. File Patterns:**
```python
# Include/exclude specific patterns
include_globs = ["**/*.py", "**/*.ts"]
exclude_globs = ["**/test_*.py", "**/node_modules/**"]
```

**2. Chunk Size:**
```env
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

**3. Embedding Model:**
```env
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # Fast
# or
OLLAMA_EMBEDDING_MODEL=mxbai-embed-large  # More accurate
```

**4. Custom Parsers:**
Extend `services/pipeline/transformers.py` to add new language support.

## LLM Providers and Models

### Which LLM provider should I use?

**Ollama (Recommended for Development):**
- ✅ Free
- ✅ No API keys needed
- ✅ Unlimited requests
- ✅ Privacy (100% local)
- ❌ Requires powerful hardware
- ❌ Slower than cloud APIs

**OpenAI (Recommended for Production):**
- ✅ Fast and accurate
- ✅ No local resources needed
- ✅ Best quality results
- ❌ Costs money per request
- ❌ Requires API key
- ❌ Data sent to OpenAI

**Google Gemini:**
- ✅ Good free tier
- ✅ Fast response times
- ✅ Large context window
- ❌ Requires API key
- ❌ Data sent to Google

**OpenRouter:**
- ✅ Access to many models
- ✅ Pay-as-you-go pricing
- ✅ Model flexibility
- ❌ Requires API key
- ❌ Variable quality

### Can I use multiple LLM providers?

Currently, one provider at a time is supported:

```env
# Choose one
LLM_PROVIDER=ollama  # or openai, gemini, openrouter
```

**Workaround**: Run multiple instances with different configurations on different ports.

**Future**: Multi-provider support is planned for v0.8.

### What Ollama models do you recommend?

**For LLM (text generation):**

- **llama3.2:3b** - Fast, good for development (4GB RAM)
- **mistral:7b** - Balanced quality and speed (8GB RAM)
- **llama3.1:8b** - High quality (8GB RAM)
- **codellama:13b** - Best for code (16GB RAM)

**For Embeddings:**

- **nomic-embed-text** - Fast, good quality (recommended)
- **mxbai-embed-large** - Better quality, slower
- **all-minilm** - Smallest, fastest

**Install:**
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### How do I switch LLM providers?

Simply update `.env` and restart:

```env
# From Ollama to OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4

EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

```bash
# Restart
docker-compose restart api
# or
pkill -f start.py && python start.py
```

No data migration needed - embeddings are recalculated automatically.

## Memory Store

### What is the Memory Store for?

Memory Store provides **long-term project knowledge** for AI agents:

**Without Memory:**
```
Session 1: "Use PostgreSQL" → AI learns
Session 2: AI forgot, suggests MySQL again ❌
```

**With Memory:**
```
Session 1: "Use PostgreSQL" → Saved to memory
Session 2: AI remembers: "You decided on PostgreSQL" ✅
```

**Types of Memories:**
- **Decisions**: "Chose JWT for auth"
- **Preferences**: "Use raw SQL over ORM"
- **Experiences**: "Redis fails with localhost in Docker"
- **Conventions**: "API endpoints use kebab-case"
- **Plans**: "Migrate to PostgreSQL 16"

### How is Memory Store different from conversation history?

**Conversation History** (Short-term):
- Temporary (session only)
- All messages (including noise)
- Lost when session ends
- Not searchable
- No importance ranking

**Memory Store** (Long-term):
- Permanent (persisted in Neo4j)
- Curated knowledge only
- Survives restarts/sessions
- Searchable by topic/tag
- Importance-ranked

Think of Memory Store as your project's **institutional memory**.

### Do I need Memory Store?

**You need Memory Store if:**
- Using AI assistants (Claude, Copilot, etc.)
- Working on long-term projects
- Multiple people/agents on same project
- Want AI to remember past decisions
- Need consistent AI behavior

**You don't need Memory Store if:**
- Just analyzing code (use Minimal mode)
- One-off queries
- Don't use AI assistants
- Limited to Knowledge Graph features

### How do I add memories manually?

**Via MCP (in Claude Desktop):**
```
Add a memory:
- Type: decision
- Title: Use PostgreSQL
- Content: Selected PostgreSQL for main database
- Reason: Need advanced JSON support
- Importance: 0.9
```

**Via HTTP API:**
```bash
curl -X POST http://localhost:8000/api/v1/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "myapp",
    "memory_type": "decision",
    "title": "Use PostgreSQL",
    "content": "Selected PostgreSQL for main database",
    "reason": "Need advanced JSON support",
    "importance": 0.9,
    "tags": ["database", "architecture"]
  }'
```

### Can memories be automatically extracted?

Yes! Version 0.7 added automatic extraction:

**1. From Conversations:**
```python
# Extract from AI chat history
extract_from_conversation(project_id, conversation_history)
```

**2. From Git Commits:**
```python
# Analyze git commits
extract_from_git_commit(project_id, commit_sha, commit_message)
```

**3. From Code Comments:**
```python
# Mine TODO, FIXME, NOTE markers
extract_from_code_comments(project_id, file_path)
```

**4. From Repository:**
```python
# Full repo analysis
batch_extract_from_repository(project_id, repo_path)
```

See [Memory Extraction Guide](./guide/memory/extraction.md) for details.

### How do I search memories?

**MCP Tool:**
```
search_memories(
  project_id="myapp",
  query="database decisions",
  memory_type="decision",
  min_importance=0.7
)
```

**HTTP API:**
```bash
curl -X POST http://localhost:8000/api/v1/memory/search \
  -d '{
    "project_id": "myapp",
    "query": "database",
    "memory_type": "decision",
    "min_importance": 0.7
  }'
```

**Results ranked by:**
- Relevance to query
- Importance score
- Recency

## Performance and Scaling

### How fast is document processing?

**Speed depends on:**
- File size
- LLM provider
- Hardware specs
- Chunk size

**Typical Performance:**

| File Size | Ollama (Local) | OpenAI (Cloud) |
|-----------|----------------|----------------|
| 10KB      | 2-5 seconds    | 1-2 seconds    |
| 100KB     | 20-30 seconds  | 5-10 seconds   |
| 1MB       | 3-5 minutes    | 30-60 seconds  |

**Tips for faster processing:**
- Use smaller embedding models
- Reduce chunk size
- Use OpenAI (fastest)
- Process in background/batch

### Can it handle large codebases?

Yes! Tested with:

- **Large PHP Project**: 25,000+ files, 5GB code
- **Oracle Database Schema**: 356 tables, 4,511 columns
- **Monorepo**: Multiple packages, 100,000+ LOC

**Performance Tips:**
1. **Use batch ingestion**: Process directories in background
2. **Filter files**: Use `.gitignore` patterns to skip unnecessary files
3. **Increase resources**: Allocate more RAM to Neo4j
4. **Add indexes**: Create Neo4j indexes on frequently queried fields

### What's the maximum document size?

**Recommended Limits:**
- **API upload**: 50KB (configurable)
- **Directory processing**: No limit (batch mode)
- **Single file processing**: 1MB recommended

**For Large Files:**
```bash
# Use MCP client with automatic temp file handling
# Or process directory in batch mode
ingest_directory(/path/to/large/files)
```

### How do I improve query performance?

**1. Add Neo4j Indexes:**
```cypher
CREATE INDEX document_content IF NOT EXISTS
FOR (d:Document) ON (d.content);

CREATE INDEX memory_tags IF NOT EXISTS
FOR (m:Memory) ON (m.tags);
```

**2. Optimize Chunk Size:**
```env
CHUNK_SIZE=512  # Smaller = faster search
```

**3. Use Faster Embeddings:**
```env
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # Fast
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # Fastest
```

**4. Increase Neo4j Memory:**
```yaml
environment:
  - NEO4J_dbms_memory_heap_max__size=4G
```

**5. Limit Results:**
```python
# Request fewer results
query_knowledge("...", limit=10)  # Instead of 100
```

## Cost and Resources

### How much does it cost to run?

**Infrastructure Costs:**

**Local Deployment (Ollama):**
- Hardware: One-time cost ($1000-$3000 for good GPU)
- Electricity: ~$20-50/month (GPU running 24/7)
- Internet: Standard connection sufficient
- **Total**: $0/month after initial investment

**Cloud Deployment (Minimal, OpenAI):**
- VPS: $20-40/month (4GB RAM, 2 CPU)
- Neo4j Cloud: $65/month (Aura free tier available)
- OpenAI API: Variable (see below)
- **Total**: $20-105/month + API costs

**Cloud Deployment (Full, OpenAI):**
- VPS: $80-160/month (16GB RAM, 8 CPU)
- Neo4j Cloud: $65/month
- OpenAI API: Variable
- **Total**: $145-225/month + API costs

**LLM API Costs:**

**OpenAI (GPT-4):**
- Embeddings: $0.00002/1K tokens (~$0.02 per 1MB document)
- Queries: $0.03/1K tokens (~$0.30 per complex query)
- **Estimate**: $10-50/month for moderate use

**OpenAI (GPT-3.5):**
- 10x cheaper than GPT-4
- **Estimate**: $1-5/month for moderate use

**Google Gemini:**
- Free tier: 15 RPM, 1M tokens/day
- Paid: $0.35/1M input tokens
- **Estimate**: Free to $5/month

**OpenRouter:**
- Variable per model
- Usually cheaper than direct APIs
- **Estimate**: $5-20/month

### Can I use the free tiers of LLM providers?

**Ollama**: ✅ Completely free, no limits

**Google Gemini**: ✅ Generous free tier (15 RPM, 1M tokens/day)

**OpenAI**: ❌ No free tier, but trial credits available

**OpenRouter**: ⚠️ Small free tier, then pay-as-you-go

**Recommendation**: Start with Ollama or Gemini free tier.

### What are the hosting costs?

**Self-Hosted (Recommended for Development):**
- Your own machine: $0/month
- Electric cost: ~$10-30/month (if running 24/7)

**VPS Hosting:**
- DigitalOcean Droplet: $24/month (4GB RAM)
- Linode: $24/month (4GB RAM)
- AWS EC2: $30-50/month (t3.medium)
- Google Cloud: $25-45/month (e2-standard-2)

**Platform-as-a-Service:**
- Railway.app: ~$20/month (with free trial)
- Render.com: ~$25/month
- Heroku: Not recommended (disk limitations)

**Managed Neo4j:**
- Neo4j Aura Free: $0/month (limited)
- Neo4j Aura Pro: $65/month (production)

### How can I reduce costs?

**1. Use Ollama Locally:**
- Zero API costs
- One-time hardware investment

**2. Use Smaller Models:**
```env
OLLAMA_MODEL=llama3.2:3b  # Instead of 13b
OPENAI_MODEL=gpt-3.5-turbo  # Instead of gpt-4
```

**3. Batch Operations:**
- Process multiple files at once
- Reduce API calls with caching

**4. Optimize Chunk Size:**
```env
CHUNK_SIZE=1024  # Larger chunks = fewer embeddings = lower cost
```

**5. Use Minimal Mode:**
- Smaller Docker image
- Lower resource requirements

**6. Self-Host Neo4j:**
- Avoid managed database costs
- Use Docker Neo4j

## Security and Privacy

### Is my code sent to external services?

**Depends on LLM provider:**

**Ollama (Local):**
- ✅ 100% local processing
- ✅ No data leaves your machine
- ✅ Complete privacy

**OpenAI/Gemini/OpenRouter:**
- ⚠️ Code sent to provider for processing
- ⚠️ Subject to provider's terms of service
- ⚠️ Check provider's data retention policies

**Recommendation**: Use Ollama for sensitive/proprietary code.

### How is data stored?

**Neo4j Database:**
- Stored in Docker volumes (encrypted at rest if configured)
- Local machine or private VPS
- Not shared with external services

**File System:**
- Temporary files during processing (deleted after)
- Logs (can contain query text, check before sharing)

**No external storage** unless you explicitly configure cloud backups.

### Can I use this in an enterprise environment?

Yes, with considerations:

**✅ Suitable for Enterprise:**
- Self-hosted (complete control)
- Local Ollama (no data leakage)
- Isolated networks
- Compliance with data residency requirements

**⚠️ Considerations:**
- Review LLM provider terms (if using cloud APIs)
- Implement access controls
- Secure Neo4j with authentication
- Use HTTPS for API endpoints
- Regular security updates

**Enterprise Checklist:**
- [ ] Use Ollama or enterprise LLM provider
- [ ] Enable Neo4j authentication
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS
- [ ] Implement audit logging
- [ ] Regular backups
- [ ] Security scanning

### Are there any security best practices?

**1. Secure Neo4j:**
```env
NEO4J_AUTH=neo4j/strong-password-here
NEO4J_dbms_security_auth__enabled=true
```

**2. Use Environment Variables:**
```bash
# Never commit .env to git
echo ".env" >> .gitignore
```

**3. API Authentication** (not implemented yet, planned for v0.8):
```python
# Coming soon: JWT authentication for API
```

**4. Network Isolation:**
```yaml
# docker-compose.yml
services:
  api:
    networks:
      - internal  # Not exposed to internet
```

**5. Regular Updates:**
```bash
# Pull latest security patches
docker pull royisme/codebase-rag:latest
```

**6. Audit Logging:**
```env
LOG_LEVEL=INFO  # Log all API access
```

## Integration and APIs

### What APIs are available?

**REST API** (HTTP):
- `/api/v1/knowledge/query` - Query knowledge base
- `/api/v1/knowledge/search` - Vector search
- `/api/v1/documents/*` - Document management
- `/api/v1/memory/*` - Memory operations
- `/api/v1/sql/*` - SQL schema analysis

**MCP Protocol** (AI Assistants):
- 30 tools across 6 categories
- Knowledge, Code Graph, Memory, Tasks, System
- Compatible with Claude Desktop, VSCode

**Real-time APIs**:
- Server-Sent Events (SSE) for task monitoring
- WebSocket (via NiceGUI monitoring UI)

See [REST API Documentation](./api/rest.md) for details.

### Can I integrate this with my CI/CD pipeline?

Yes! Several integration options:

**1. Pre-commit Hook:**
```bash
# .git/hooks/pre-commit
#!/bin/bash
# Extract memories from commit
curl -X POST http://localhost:8000/api/v1/memory/extract/commit \
  -d "{\"commit_sha\": \"$(git rev-parse HEAD)\"}"
```

**2. GitHub Actions:**
```yaml
# .github/workflows/code-analysis.yml
name: Code Analysis
on: [push]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: Analyze code
        run: |
          curl -X POST http://code-graph-server/api/v1/ingest/directory \
            -d '{"path": "${{ github.workspace }}"}'
```

**3. Build Script:**
```bash
# In your build.sh
python -c "
from services.memory_store import MemoryStore
# Auto-extract memories after build
"
```

### How do I backup my data?

**Neo4j Backup:**
```bash
# Export Neo4j data
docker exec code-graph-neo4j neo4j-admin dump \
  --database=neo4j --to=/backups/neo4j-backup.dump

# Copy from container
docker cp code-graph-neo4j:/backups/neo4j-backup.dump ./backups/

# Or backup volume
docker run --rm \
  -v code-graph_neo4j_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/neo4j-data.tar.gz /data
```

**Restore Backup:**
```bash
# Stop Neo4j
docker-compose stop neo4j

# Restore
docker cp ./backups/neo4j-backup.dump code-graph-neo4j:/backups/
docker exec code-graph-neo4j neo4j-admin load \
  --from=/backups/neo4j-backup.dump --database=neo4j --force

# Restart
docker-compose start neo4j
```

### Can I export my data?

**Export Memories as JSON:**
```bash
curl http://localhost:8000/api/v1/memory/project/myapp/export > memories.json
```

**Export Knowledge Graph:**
```cypher
// In Neo4j Browser
CALL apoc.export.json.all("/export/graph.json", {})
```

**Export to CSV:**
```cypher
MATCH (m:Memory)
RETURN m.title, m.content, m.importance
// Click "Export" in Neo4j Browser
```

## Troubleshooting

### Where can I find logs?

**Docker Logs:**
```bash
# Application logs
docker logs code-graph-api

# Neo4j logs
docker logs code-graph-neo4j

# Follow logs
docker logs -f code-graph-api
```

**Local Logs:**
```bash
# Application logs
tail -f logs/application.log

# Debug logs
tail -f logs/debug.log
```

### The application won't start. What should I check?

**Quick Checklist:**

1. **Neo4j Running:**
   ```bash
   docker ps | grep neo4j
   ```

2. **Environment Variables:**
   ```bash
   cat .env | grep NEO4J
   ```

3. **Dependencies Installed:**
   ```bash
   pip list | grep llama-index
   ```

4. **Port Available:**
   ```bash
   lsof -i :8000
   ```

5. **Logs for Errors:**
   ```bash
   docker logs code-graph-api | grep ERROR
   ```

See [Troubleshooting Guide](./troubleshooting.md) for detailed solutions.

### Where can I get help?

**Documentation:**
- Main docs: https://code-graph.vantagecraft.dev
- This FAQ
- Troubleshooting guide
- API documentation

**Community:**
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community help
- Discord/Slack: Real-time chat (if available)

**Support:**
- Email maintainers for critical issues
- Check existing issues before posting
- Include logs and error messages

### How do I report a bug?

**Good Bug Report:**

1. **Search existing issues** first
2. **Use issue template** if available
3. **Include**:
   - System info (OS, Python version, Docker version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
   - Configuration (sanitized .env)
4. **Create minimal reproduction** if possible

See [Contributing Guide](./development/contributing.md) for details.

### Is there a community forum or chat?

Check the [GitHub Discussions](https://github.com/royisme/codebase-rag/discussions) for:
- Questions and answers
- Feature discussions
- Show and tell
- Community support

**Coming soon**: Discord/Slack community (watch for announcements).

## Still Have Questions?

Can't find your answer here?

1. Search the [full documentation](https://code-graph.vantagecraft.dev)
2. Check [Troubleshooting Guide](./troubleshooting.md)
3. Search [GitHub Issues](https://github.com/royisme/codebase-rag/issues)
4. Ask in [GitHub Discussions](https://github.com/royisme/codebase-rag/discussions)
5. Review the [source code](https://github.com/royisme/codebase-rag)

**Found an error in this FAQ?** Please [open an issue](https://github.com/royisme/codebase-rag/issues/new) or submit a PR!
