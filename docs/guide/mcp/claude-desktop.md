# Claude Desktop MCP Setup

Complete guide to integrating Code Graph Knowledge System with Claude Desktop using the Model Context Protocol.

## Overview

Claude Desktop is Anthropic's official desktop application that supports MCP (Model Context Protocol) integration. This allows Claude to directly call tools in your Code Graph Knowledge System, providing:

- **Direct tool access**: Claude can query your knowledge base, search code, manage memories
- **Natural language interface**: Ask questions in plain English
- **Context awareness**: Claude remembers your project knowledge
- **Real-time responses**: Immediate tool execution and results

## Prerequisites

### 1. Claude Desktop

Download and install Claude Desktop:

**Download Links**:
- **macOS**: https://claude.ai/download
- **Windows**: https://claude.ai/download
- **Linux**: Not officially supported yet (use VS Code extension)

**Minimum Version**: 0.7.0+ (MCP support added in v0.7.0)

### 2. Code Graph Knowledge System

You need a running instance:

```bash
# Option 1: Docker deployment
docker-compose -f docker/docker-compose.full.yml up -d

# Option 2: Local development
python start_mcp.py

# Verify it's running
ps aux | grep start_mcp.py
```

### 3. Python Environment

Claude Desktop needs to invoke your MCP server:

```bash
# Check Python version (3.10+ required)
python --version

# Verify dependencies are installed
cd /path/to/codebase-rag
pip install -e .

# Or with uv
uv pip install -e .
```

## Configuration

### Step 1: Locate Configuration File

Claude Desktop stores MCP configuration in a JSON file:

**macOS**:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows**:
```
%APPDATA%\Claude\claude_desktop_config.json
```

### Step 2: Create Configuration

If the file doesn't exist, create it:

```bash
# macOS
mkdir -p ~/Library/Application\ Support/Claude
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows (PowerShell)
New-Item -Path "$env:APPDATA\Claude\claude_desktop_config.json" -Force
```

### Step 3: Add MCP Server Configuration

Edit `claude_desktop_config.json`:

#### Basic Configuration

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["/absolute/path/to/codebase-rag/start_mcp.py"]
    }
  }
}
```

#### With Environment Variables

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python",
      "args": ["/absolute/path/to/codebase-rag/start_mcp.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/codebase-rag",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your_password",
        "LLM_PROVIDER": "ollama",
        "OLLAMA_HOST": "http://localhost:11434"
      }
    }
  }
}
```

#### Using uv (Recommended)

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "uv",
      "args": ["run", "mcp_server"],
      "cwd": "/absolute/path/to/codebase-rag"
    }
  }
}
```

#### Docker-based Setup

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "codebase-rag-mcp",
        "python",
        "/app/start_mcp.py"
      ]
    }
  }
}
```

### Step 4: Restart Claude Desktop

After configuration changes:

1. **Quit Claude Desktop** completely (not just close window)
   - macOS: Cmd+Q
   - Windows: File → Exit

2. **Restart Claude Desktop**

3. **Verify MCP connection** (see Verification section)

## Configuration Examples

### Example 1: Full Mode with Ollama

```json
{
  "mcpServers": {
    "code-graph-full": {
      "command": "python",
      "args": ["/Users/john/projects/codebase-rag/start_mcp.py"],
      "env": {
        "PYTHONPATH": "/Users/john/projects/codebase-rag",
        "DEPLOYMENT_MODE": "full",
        "ENABLE_KNOWLEDGE_RAG": "true",
        "ENABLE_AUTO_EXTRACTION": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "mypassword",
        "LLM_PROVIDER": "ollama",
        "OLLAMA_HOST": "http://localhost:11434",
        "OLLAMA_MODEL": "llama3.2",
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text"
      }
    }
  }
}
```

### Example 2: Standard Mode (No RAG)

```json
{
  "mcpServers": {
    "code-graph-standard": {
      "command": "python",
      "args": ["/home/user/codebase-rag/start_mcp.py"],
      "env": {
        "PYTHONPATH": "/home/user/codebase-rag",
        "DEPLOYMENT_MODE": "standard",
        "ENABLE_KNOWLEDGE_RAG": "false",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

### Example 3: Multiple MCP Servers

```json
{
  "mcpServers": {
    "code-graph-project-a": {
      "command": "python",
      "args": ["/path/to/project-a/codebase-rag/start_mcp.py"],
      "env": {
        "NEO4J_DATABASE": "project_a"
      }
    },
    "code-graph-project-b": {
      "command": "python",
      "args": ["/path/to/project-b/codebase-rag/start_mcp.py"],
      "env": {
        "NEO4J_DATABASE": "project_b"
      }
    }
  }
}
```

## Verification

### Check MCP Connection

After restarting Claude Desktop:

1. **Start a new conversation**

2. **Look for tool indicator**:
   - You should see a tools icon or "Tools available" indicator
   - Click to view available tools

3. **Verify tools are listed**:
   - You should see 20-30 tools (depending on deployment mode)
   - Tool names: `query_knowledge`, `add_memory`, `code_graph_ingest_repo`, etc.

### Test Basic Functionality

Try these test prompts:

```
"List available MCP tools"
```

Expected: Claude lists all available tools

```
"Use the get_statistics tool to check system stats"
```

Expected: Claude calls `get_statistics` and shows results

```
"Query the knowledge base about deployment"
```

Expected: Claude calls `query_knowledge` with your question

### Check Logs

If tools don't appear:

**MCP Server Logs**:
```bash
# View server logs
tail -f /path/to/codebase-rag/mcp_server.log

# Enable debug mode
MCP_LOG_LEVEL=DEBUG python start_mcp.py
```

**Claude Desktop Logs**:

macOS:
```bash
tail -f ~/Library/Logs/Claude/mcp-server-code-graph.log
```

Windows:
```powershell
Get-Content "$env:APPDATA\Claude\Logs\mcp-server-code-graph.log" -Wait
```

## Usage Patterns

### 1. Query Knowledge Base

**Prompt**:
```
"Query the knowledge base: How do I configure Docker deployment?"
```

**What Claude Does**:
1. Calls `query_knowledge` tool
2. Passes your question
3. Receives answer with sources
4. Formats and presents results

**Response Example**:
```
Based on the knowledge base, here's how to configure Docker deployment:

[Claude presents the answer with source citations]

Sources:
- Docker Guide (score: 0.92)
- Deployment Documentation (score: 0.87)
```

### 2. Search Code

**Prompt**:
```
"Search the code graph for authentication implementations"
```

**What Claude Does**:
1. Calls `code_graph_fulltext_search`
2. Finds matching code files
3. Presents results with context

### 3. Manage Memories

**Prompt**:
```
"Add a memory: We decided to use PostgreSQL for the main database
because it has better JSON support. This is an important architectural decision."
```

**What Claude Does**:
1. Extracts memory details
2. Calls `add_memory` tool
3. Saves to memory store
4. Confirms success

### 4. Analyze Code Repository

**Prompt**:
```
"Ingest the repository at /path/to/my/project in incremental mode"
```

**What Claude Does**:
1. Calls `code_graph_ingest_repo`
2. Processes repository
3. Reports statistics

### 5. Monitor Tasks

**Prompt**:
```
"Check the status of task task_abc123"
```

**What Claude Does**:
1. Calls `get_task_status`
2. Returns current status
3. Shows progress if available

## Advanced Usage

### Chained Tool Calls

Claude can chain multiple tool calls:

**Prompt**:
```
"Index the /path/to/docs directory, then query it about deployment"
```

**What Claude Does**:
1. Calls `add_directory` to index docs
2. Waits for completion (or gets task_id)
3. Calls `query_knowledge` with your question
4. Presents combined results

### Context Building

**Prompt**:
```
"Search my memories for database decisions,
then query the knowledge base for PostgreSQL configuration examples"
```

**What Claude Does**:
1. Calls `search_memories` with "database"
2. Calls `query_knowledge` with "PostgreSQL configuration"
3. Synthesizes information from both sources

### Memory Extraction

**Prompt**:
```
"Extract memories from the last 50 commits in /path/to/repo"
```

**What Claude Does**:
1. Calls `batch_extract_from_repository`
2. Analyzes commits
3. Extracts decisions and learnings
4. Saves as memories

### Impact Analysis

**Prompt**:
```
"Analyze the impact of changing the authentication module"
```

**What Claude Does**:
1. Calls `code_graph_impact_analysis`
2. Finds dependent files
3. Assesses risk level
4. Presents findings

## Best Practices

### 1. Be Specific with Tool Names

**Good**:
```
"Use query_knowledge to find information about Docker"
```

**Less effective**:
```
"Find Docker information"  # Claude might not use the right tool
```

### 2. Provide Complete Paths

**Good**:
```
"Ingest repository at /Users/john/projects/myapp"
```

**Bad**:
```
"Ingest myapp"  # Relative paths don't work
```

### 3. Check Tool Availability

Before using a tool:

```
"What deployment mode are we running? List available tools."
```

### 4. Handle Async Operations

For long-running tasks:

```
"Add the /docs directory. If it's async, give me the task_id
so I can check status later."
```

### 5. Verify Results

After tool calls:

```
"Show me the sources used for that answer"
"Confirm the memory was saved"
"Verify the repository was ingested successfully"
```

## Troubleshooting

### Issue: Tools Not Appearing

**Symptoms**:
- No tools icon in Claude Desktop
- Claude says "I don't have access to tools"

**Solutions**:

1. **Verify configuration file location**:
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Windows
   type %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Check JSON syntax**:
   ```bash
   # Use JSON validator
   python -m json.tool claude_desktop_config.json
   ```

3. **Verify absolute paths**:
   - All paths must be absolute, not relative
   - Expand ~ to full home path

4. **Restart completely**:
   - Force quit Claude Desktop
   - Kill any remaining processes
   - Start fresh

### Issue: Connection Errors

**Symptoms**:
- "Failed to connect to MCP server"
- Tools listed but calls fail

**Solutions**:

1. **Check server is running**:
   ```bash
   ps aux | grep start_mcp.py
   ```

2. **Verify Neo4j connection**:
   ```bash
   curl http://localhost:7474
   ```

3. **Check environment variables**:
   ```bash
   # Test the command manually
   cd /path/to/codebase-rag
   python start_mcp.py
   ```

4. **Review MCP server logs**:
   ```bash
   tail -f mcp_server.log
   ```

### Issue: Tool Calls Timeout

**Symptoms**:
- "Tool call timeout"
- Long delays before failure

**Solutions**:

1. **Increase timeout** in `.env`:
   ```bash
   OPERATION_TIMEOUT=300  # 5 minutes
   ```

2. **Check system resources**:
   ```bash
   # CPU and memory usage
   top
   ```

3. **Use async mode** for large operations:
   - Directory ingestion
   - Large document processing
   - Batch memory extraction

### Issue: Permission Errors

**Symptoms**:
- "Permission denied" when starting MCP server
- Cannot read configuration files

**Solutions**:

1. **Fix file permissions**:
   ```bash
   chmod +x start_mcp.py
   chmod 600 .env
   ```

2. **Check directory permissions**:
   ```bash
   ls -la /path/to/codebase-rag
   ```

3. **Run with correct user**:
   ```bash
   # Ensure Neo4j is accessible by your user
   whoami
   ```

### Issue: Tools Return Errors

**Symptoms**:
- "Tool execution failed"
- Error messages in responses

**Solutions**:

1. **Check backend services**:
   ```bash
   # Verify Neo4j
   cypher-shell "RETURN 1"

   # Verify Ollama (if using)
   curl http://localhost:11434/api/tags
   ```

2. **Review tool-specific logs**:
   ```bash
   grep "ERROR" mcp_server.log
   ```

3. **Test tools directly** via HTTP API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/knowledge/query \
     -H "Content-Type: application/json" \
     -d '{"question": "test"}'
   ```

## Performance Optimization

### Reduce Latency

1. **Use local LLM** (Ollama) to avoid API delays
2. **Enable caching** in configuration
3. **Use incremental mode** for code ingestion
4. **Reduce top_k** for faster queries

### Improve Response Quality

1. **Add more documents** to knowledge base
2. **Use better embeddings** (larger models)
3. **Add rich metadata** to documents
4. **Curate project memories** regularly

### Handle Large Operations

1. **Use async mode** for:
   - Directory ingestion
   - Batch memory extraction
   - Large document processing

2. **Monitor with watch_task**:
   ```
   "Add directory /docs then watch the task until complete"
   ```

## Security Considerations

### Configuration Security

1. **Protect config file**:
   ```bash
   chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Don't commit credentials**:
   - Use environment variables
   - Keep passwords in `.env` file
   - Add `.env` to `.gitignore`

3. **Use authentication**:
   ```bash
   # Add Neo4j authentication
   NEO4J_USER=readonly_user
   NEO4J_PASSWORD=secure_password
   ```

### Network Security

1. **Bind to localhost**:
   ```bash
   # In .env
   HOST=127.0.0.1  # Don't expose to network
   ```

2. **Use firewall rules**:
   ```bash
   # Block external access to Neo4j
   sudo ufw deny 7687
   sudo ufw allow from 127.0.0.1 to any port 7687
   ```

### Tool Restrictions

1. **Disable destructive tools** if needed:
   - Modify `start_mcp.py` to exclude certain tools
   - Implement tool-level access control

2. **Read-only mode**:
   ```bash
   # Configure read-only Neo4j user
   ENABLE_WRITE_OPERATIONS=false
   ```

## Next Steps

- **[MCP Overview](overview.md)**: Learn about MCP protocol
- **[VS Code Setup](vscode.md)**: Configure VS Code extension
- **[Knowledge RAG Guide](../knowledge/overview.md)**: Use query tools
- **[Memory Store Guide](../memory/overview.md)**: Manage project memories

## Additional Resources

- **Claude Desktop**: https://claude.ai/download
- **MCP Documentation**: https://modelcontextprotocol.io/
- **Configuration Examples**: `/examples/mcp_configs/`
- **Troubleshooting**: https://docs.anthropic.com/claude/docs/mcp
