# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the Code Graph Knowledge System.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Connection Issues](#connection-issues)
- [Docker Deployment Issues](#docker-deployment-issues)
- [Neo4j Problems](#neo4j-problems)
- [LLM Provider Issues](#llm-provider-issues)
- [Performance Problems](#performance-problems)
- [Memory Issues](#memory-issues)
- [MCP Server Problems](#mcp-server-problems)
- [API Errors](#api-errors)
- [Installation Issues](#installation-issues)
- [Data and Storage Issues](#data-and-storage-issues)
- [Common Error Messages](#common-error-messages)

## Quick Diagnostics

### Health Check

Start with the health check endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

**Healthy Response:**
```json
{
  "status": "healthy",
  "neo4j": "connected",
  "llm_provider": "ollama",
  "version": "0.7.0"
}
```

**Unhealthy Response:**
```json
{
  "status": "unhealthy",
  "neo4j": "disconnected",
  "llm_provider": "error",
  "error": "Connection timeout"
}
```

### System Check Command

```bash
# Check all services
python start.py --check

# Check logs
tail -f logs/application.log

# Check Docker containers
docker ps -a
docker logs code-graph-api
docker logs code-graph-neo4j
```

### Common Issues Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| Application won't start | Missing dependencies | `uv pip install -e .` |
| Connection timeout | Neo4j not running | `docker-compose up -d neo4j` |
| 502 Bad Gateway | Service crashed | Check logs, restart service |
| Slow responses | Memory/CPU limits | Increase Docker resources |
| Import errors | Wrong Python path | `export PYTHONPATH=$PWD` |
| API 500 errors | Configuration issue | Check .env file |

## Connection Issues

### Neo4j Connection Timeout

**Symptom:**
```
neo4j.exceptions.ServiceUnavailable: Failed to establish connection to bolt://localhost:7687
```

**Diagnosis:**
```bash
# Check if Neo4j is running
docker ps | grep neo4j
# or
sudo systemctl status neo4j

# Try connecting manually
docker exec -it code-graph-neo4j cypher-shell -u neo4j -p yourpassword
```

**Solutions:**

1. **Neo4j not running:**
   ```bash
   # Docker
   docker-compose up -d neo4j

   # Native
   sudo systemctl start neo4j
   ```

2. **Wrong connection details:**
   ```bash
   # Check .env file
   cat .env | grep NEO4J

   # Should be:
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your-password
   ```

3. **Neo4j not ready yet:**
   ```bash
   # Wait for Neo4j to fully start (30-60 seconds)
   docker logs -f code-graph-neo4j
   # Look for: "Started."
   ```

4. **Firewall blocking connection:**
   ```bash
   # Check port accessibility
   telnet localhost 7687
   nc -zv localhost 7687

   # Allow port in firewall
   sudo ufw allow 7687
   ```

5. **Docker network issues:**
   ```bash
   # Check network
   docker network ls
   docker network inspect code-graph_default

   # Recreate network
   docker-compose down
   docker-compose up -d
   ```

### Ollama Connection Failed

**Symptom:**
```
httpx.ConnectError: [Errno 111] Connection refused
```

**Diagnosis:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
ps aux | grep ollama
```

**Solutions:**

1. **Ollama not running:**
   ```bash
   # Start Ollama
   ollama serve

   # Or run in background
   nohup ollama serve > /dev/null 2>&1 &
   ```

2. **Model not downloaded:**
   ```bash
   # Check available models
   ollama list

   # Pull required models
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```

3. **Wrong Ollama URL:**
   ```bash
   # Check .env
   OLLAMA_BASE_URL=http://localhost:11434

   # If Ollama is on different host
   OLLAMA_BASE_URL=http://192.168.1.100:11434
   ```

### OpenAI API Connection Issues

**Symptom:**
```
openai.error.AuthenticationError: Invalid API key
```

**Solutions:**

1. **Invalid API key:**
   ```bash
   # Check .env file
   cat .env | grep OPENAI_API_KEY

   # Get new key from: https://platform.openai.com/api-keys
   OPENAI_API_KEY=sk-your-key-here
   ```

2. **Network connectivity:**
   ```bash
   # Test OpenAI connectivity
   curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **Rate limiting:**
   ```bash
   # Wait and retry
   # Implement exponential backoff in code
   # Upgrade OpenAI plan for higher limits
   ```

## Docker Deployment Issues

### Container Won't Start

**Symptom:**
```bash
docker ps -a
# Shows container with status "Exited (1)"
```

**Diagnosis:**
```bash
# Check container logs
docker logs code-graph-api

# Check all container logs
docker-compose logs
```

**Common Issues:**

1. **Missing environment variables:**
   ```bash
   # Check docker-compose.yml has environment section
   environment:
     - NEO4J_URI=bolt://neo4j:7687
     - NEO4J_USER=neo4j
     - NEO4J_PASSWORD=${NEO4J_PASSWORD}

   # Check .env file exists
   ls -la .env
   ```

2. **Port already in use:**
   ```bash
   # Check what's using port 8000
   lsof -i :8000  # Linux/macOS
   netstat -ano | findstr :8000  # Windows

   # Kill process or change port
   docker-compose down
   # Edit docker-compose.yml to use different port
   ports:
     - "8001:8000"
   docker-compose up -d
   ```

3. **Out of disk space:**
   ```bash
   # Check disk space
   df -h

   # Clean up Docker
   docker system prune -a
   docker volume prune
   ```

4. **Memory limits:**
   ```bash
   # Increase Docker memory
   # Docker Desktop: Settings > Resources > Memory (increase to 4GB+)

   # Or in docker-compose.yml
   services:
     api:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

### Docker Compose Errors

**Error: "Version is not supported"**
```bash
# Update Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Or use docker compose (without hyphen)
docker compose up -d
```

**Error: "Network not found"**
```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

**Error: "Volume not found"**
```bash
# List volumes
docker volume ls

# Recreate volumes
docker-compose down -v
docker-compose up -d
```

### Container Networking Issues

**Containers can't communicate:**

```bash
# Check network
docker network ls
docker network inspect code-graph_default

# Ensure containers are on same network
docker-compose ps

# Test connectivity
docker exec code-graph-api ping neo4j
```

**DNS resolution fails:**

```bash
# Use service name, not localhost
NEO4J_URI=bolt://neo4j:7687  # Correct in Docker
NEO4J_URI=bolt://localhost:7687  # Wrong in Docker
```

## Neo4j Problems

### Neo4j Out of Memory

**Symptom:**
```
Neo4j heap memory exceeded
OutOfMemoryError: Java heap space
```

**Solutions:**

1. **Increase heap size:**
   ```yaml
   # docker-compose.yml
   services:
     neo4j:
       environment:
         - NEO4J_dbms_memory_heap_max__size=4G
         - NEO4J_dbms_memory_pagecache_size=2G
   ```

2. **Clear old data:**
   ```cypher
   // In Neo4j Browser (http://localhost:7474)

   // Delete old nodes
   MATCH (n:Document) WHERE n.created < datetime() - duration('P30D')
   DETACH DELETE n

   // Or clear all data (CAUTION!)
   MATCH (n) DETACH DELETE n
   ```

3. **Optimize queries:**
   ```cypher
   // Add indexes
   CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id)
   CREATE INDEX memory_project IF NOT EXISTS FOR (m:Memory) ON (m.project_id)
   ```

### Neo4j Browser Not Accessible

**Symptom:**
Cannot access http://localhost:7474

**Solutions:**

1. **Check port mapping:**
   ```bash
   docker ps | grep neo4j
   # Should show: 0.0.0.0:7474->7474/tcp

   # If not, check docker-compose.yml
   ports:
     - "7474:7474"
     - "7687:7687"
   ```

2. **Neo4j not ready:**
   ```bash
   # Wait for startup
   docker logs -f code-graph-neo4j
   # Look for: "Started."
   ```

3. **Firewall blocking:**
   ```bash
   sudo ufw allow 7474
   ```

### APOC Plugin Issues

**Symptom:**
```
There is no procedure with the name `apoc.meta.data` registered
```

**Solutions:**

1. **APOC not installed:**
   ```yaml
   # docker-compose.yml
   services:
     neo4j:
       environment:
         - NEO4J_PLUGINS=["apoc"]
         - NEO4J_dbms_security_procedures_unrestricted=apoc.*
   ```

2. **Restart Neo4j:**
   ```bash
   docker-compose restart neo4j
   ```

3. **Verify APOC:**
   ```cypher
   // In Neo4j Browser
   RETURN apoc.version()
   ```

### Neo4j Authentication Failed

**Symptom:**
```
Neo4j.ClientError.Security.Unauthorized
```

**Solutions:**

```bash
# Reset password
docker exec -it code-graph-neo4j cypher-shell -u neo4j -p neo4j
# Follow prompts to change password

# Update .env
NEO4J_PASSWORD=new-password

# Restart application
docker-compose restart api
```

## LLM Provider Issues

### Ollama Model Not Found

**Symptom:**
```
Error: model 'llama3.2:3b' not found
```

**Solutions:**

```bash
# List available models
ollama list

# Pull required model
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Verify in .env
OLLAMA_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Ollama Out of Memory

**Symptom:**
```
Error loading model: insufficient memory
```

**Solutions:**

1. **Use smaller model:**
   ```bash
   # 3B model instead of 7B
   ollama pull llama3.2:3b

   # Update .env
   OLLAMA_MODEL=llama3.2:3b
   ```

2. **Increase system memory:**
   - Close other applications
   - Increase Docker memory limit
   - Use smaller context window

3. **Use CPU offloading:**
   ```bash
   # Ollama automatically offloads to CPU when GPU memory is full
   # Monitor with:
   ollama ps
   ```

### OpenAI Rate Limit Exceeded

**Symptom:**
```
openai.error.RateLimitError: Rate limit exceeded
```

**Solutions:**

1. **Wait and retry:**
   ```python
   # Application has exponential backoff
   # Wait 1 minute and try again
   ```

2. **Upgrade OpenAI plan:**
   - Visit OpenAI dashboard
   - Increase rate limits
   - Add payment method

3. **Switch to Ollama:**
   ```bash
   # No rate limits with local Ollama
   LLM_PROVIDER=ollama
   ```

### Gemini API Quota Exceeded

**Symptom:**
```
google.api_core.exceptions.ResourceExhausted: Quota exceeded
```

**Solutions:**

1. **Check quota:**
   - Visit Google AI Studio
   - Check daily quota usage
   - Wait for quota reset (midnight Pacific)

2. **Request quota increase:**
   - Contact Google support
   - Upgrade to paid plan

## Performance Problems

### Slow Query Responses

**Symptom:**
Queries take > 30 seconds

**Diagnosis:**

```bash
# Check system resources
top
htop
docker stats

# Check Neo4j query performance
# In Neo4j Browser, run with PROFILE:
PROFILE MATCH (n:Document) RETURN n LIMIT 10
```

**Solutions:**

1. **Add Neo4j indexes:**
   ```cypher
   // Create indexes on frequently queried fields
   CREATE INDEX document_content IF NOT EXISTS
   FOR (d:Document) ON (d.content)

   CREATE INDEX memory_tags IF NOT EXISTS
   FOR (m:Memory) ON (m.tags)

   // Check indexes
   SHOW INDEXES
   ```

2. **Optimize chunk size:**
   ```python
   # In .env
   CHUNK_SIZE=512  # Smaller chunks for faster search
   CHUNK_OVERLAP=50
   ```

3. **Use smaller embedding model:**
   ```bash
   # Ollama
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # Fast

   # OpenAI
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # Fast & cheap
   ```

4. **Increase timeouts:**
   ```bash
   # .env
   OPERATION_TIMEOUT=600  # 10 minutes
   LARGE_DOCUMENT_TIMEOUT=1200  # 20 minutes
   ```

### High Memory Usage

**Symptom:**
```bash
docker stats
# Shows 90%+ memory usage
```

**Solutions:**

1. **Increase Docker memory:**
   ```bash
   # Docker Desktop: Settings > Resources
   # Increase memory to 8GB or more
   ```

2. **Reduce Neo4j memory:**
   ```yaml
   # docker-compose.yml
   services:
     neo4j:
       environment:
         - NEO4J_dbms_memory_heap_max__size=2G  # Reduce from 4G
   ```

3. **Process documents in batches:**
   ```python
   # Use directory processing with batch size
   # MCP: ingest_directory with smaller batches
   # API: Process files one at a time
   ```

4. **Clear cache:**
   ```bash
   # Restart services
   docker-compose restart

   # Clear Neo4j page cache
   # In Neo4j Browser:
   CALL dbms.clearQueryCaches()
   ```

### High CPU Usage

**Symptom:**
CPU at 100% constantly

**Solutions:**

1. **Check what's consuming CPU:**
   ```bash
   docker stats
   # Identify the container

   docker top code-graph-api
   ```

2. **Ollama consuming CPU:**
   ```bash
   # Normal during inference
   # Use GPU if available
   # Reduce concurrent requests
   ```

3. **Limit concurrent operations:**
   ```python
   # In code, limit concurrent tasks
   # Default: 5 concurrent operations
   MAX_CONCURRENT_OPERATIONS=3
   ```

## Memory Issues

### Memory Store Search Slow

**Symptom:**
Memory search takes > 5 seconds

**Solutions:**

1. **Add fulltext index:**
   ```cypher
   // In Neo4j Browser
   CREATE FULLTEXT INDEX memory_fulltext IF NOT EXISTS
   FOR (m:Memory)
   ON EACH [m.title, m.content, m.reason, m.tags]

   // Verify
   SHOW INDEXES
   ```

2. **Limit search results:**
   ```python
   # When searching, use limit
   search_memories(query="...", limit=20)  # Instead of 100
   ```

3. **Filter by importance:**
   ```python
   # Only search important memories
   search_memories(query="...", min_importance=0.7)
   ```

### Memory Not Found After Adding

**Symptom:**
Memory added successfully but search doesn't find it

**Diagnosis:**

```cypher
// Check if memory exists
MATCH (m:Memory {project_id: "your-project"})
RETURN m LIMIT 10

// Check memory count
MATCH (m:Memory {project_id: "your-project"})
RETURN count(m)
```

**Solutions:**

1. **Index not updated:**
   ```cypher
   // Rebuild fulltext index
   DROP INDEX memory_fulltext IF EXISTS
   CREATE FULLTEXT INDEX memory_fulltext
   FOR (m:Memory)
   ON EACH [m.title, m.content, m.reason, m.tags]
   ```

2. **Search query too specific:**
   ```python
   # Use broader search terms
   # Instead of: "PostgreSQL database configuration"
   # Try: "PostgreSQL" or "database"
   ```

3. **Project ID mismatch:**
   ```bash
   # Check project ID is consistent
   echo $PROJECT_ID
   ```

## MCP Server Problems

### MCP Server Won't Start

**Symptom:**
```
Error: MCP server failed to start
```

**Diagnosis:**

```bash
# Try starting manually
python start_mcp.py

# Check logs
python start_mcp.py 2>&1 | tee mcp.log
```

**Solutions:**

1. **Missing MCP package:**
   ```bash
   uv pip install mcp>=1.1.0
   ```

2. **Port already in use:**
   ```bash
   # Check ports
   lsof -i :8001

   # Kill process or use different port
   # MCP server uses stdio by default (no port needed)
   ```

3. **Neo4j not accessible:**
   ```bash
   # MCP server needs Neo4j
   # Check Neo4j is running
   docker ps | grep neo4j
   ```

### MCP Tools Not Appearing in Claude

**Symptom:**
MCP tools don't show up in Claude Desktop

**Solutions:**

1. **Check Claude config:**
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Should contain:
   {
     "mcpServers": {
       "code-graph": {
         "command": "python",
         "args": ["/path/to/codebase-rag/start_mcp.py"]
       }
     }
   }
   ```

2. **Check MCP server path:**
   ```bash
   # Use absolute path
   "args": ["/home/user/codebase-rag/start_mcp.py"]

   # Not relative path
   "args": ["./start_mcp.py"]  # Wrong
   ```

3. **Restart Claude Desktop:**
   ```bash
   # Completely quit and restart Claude Desktop
   # Check MCP status in Claude: cmd/ctrl + ,
   ```

4. **Check Python environment:**
   ```json
   {
     "mcpServers": {
       "code-graph": {
         "command": "/path/to/.venv/bin/python",
         "args": ["/path/to/start_mcp.py"],
         "env": {
           "PYTHONPATH": "/path/to/codebase-rag"
         }
       }
     }
   }
   ```

### MCP Tool Execution Fails

**Symptom:**
```
Error executing tool: Connection timeout
```

**Solutions:**

1. **Increase timeouts:**
   ```bash
   # .env
   OPERATION_TIMEOUT=600
   CONNECTION_TIMEOUT=60
   ```

2. **Check Neo4j connection:**
   ```bash
   # MCP tools need working Neo4j
   python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password')); driver.verify_connectivity(); print('OK')"
   ```

3. **Check file paths:**
   ```bash
   # Use absolute paths in MCP tool calls
   # Not: "documents/file.txt"
   # Use: "/home/user/project/documents/file.txt"
   ```

## API Errors

### 500 Internal Server Error

**Diagnosis:**

```bash
# Check application logs
docker logs code-graph-api

# Or local logs
tail -f logs/application.log
```

**Common Causes:**

1. **Configuration error:**
   ```bash
   # Check .env file
   cat .env
   # Ensure all required variables are set
   ```

2. **Database connection lost:**
   ```bash
   # Restart Neo4j
   docker-compose restart neo4j
   ```

3. **Unhandled exception:**
   ```bash
   # Check logs for stack trace
   # Report bug with full error message
   ```

### 422 Validation Error

**Symptom:**
```json
{
  "detail": [
    {
      "loc": ["body", "memory_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Solution:**
Check your request body includes all required fields.

**Example correct request:**
```bash
curl -X POST http://localhost:8000/api/v1/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "myapp",
    "memory_type": "decision",
    "title": "Use PostgreSQL",
    "content": "Selected PostgreSQL as database",
    "importance": 0.8
  }'
```

### 404 Not Found

**Diagnosis:**

```bash
# Check available endpoints
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

**Solutions:**

1. **Check API version:**
   ```bash
   # Correct
   curl http://localhost:8000/api/v1/health

   # Wrong
   curl http://localhost:8000/health
   ```

2. **Check URL spelling:**
   ```bash
   # Correct
   /api/v1/memory/add

   # Wrong
   /api/v1/memories/add
   ```

## Installation Issues

### uv Installation Fails

**Symptom:**
```
curl: command not found
```

**Solution:**

```bash
# Install curl first
sudo apt-get install curl  # Debian/Ubuntu
brew install curl  # macOS

# Then install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Python Version Issues

**Symptom:**
```
ERROR: This package requires Python 3.13+
```

**Solutions:**

```bash
# Check Python version
python --version

# Install Python 3.13
## Ubuntu/Debian
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13

## macOS
brew install python@3.13

# Create venv with correct Python
python3.13 -m venv .venv
source .venv/bin/activate
```

### Dependency Installation Fails

**Symptom:**
```
ERROR: Could not build wheels for llama-index
```

**Solutions:**

1. **Install build dependencies:**
   ```bash
   # Debian/Ubuntu
   sudo apt-get install build-essential python3.13-dev

   # macOS
   xcode-select --install
   ```

2. **Clear cache and retry:**
   ```bash
   uv cache clean
   uv pip install -e .
   ```

3. **Use pre-built wheels:**
   ```bash
   uv pip install --only-binary :all: -e .
   ```

## Data and Storage Issues

### Disk Space Full

**Symptom:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**

```bash
# Check disk space
df -h

# Clean up Docker
docker system prune -a
docker volume prune

# Clean up Neo4j data (CAUTION: deletes all data)
docker-compose down -v
docker-compose up -d

# Clean up logs
rm -rf logs/*.log.*
```

### Data Corruption

**Symptom:**
```
Neo4j database files are corrupted
```

**Solutions:**

1. **Backup and restore:**
   ```bash
   # Stop Neo4j
   docker-compose stop neo4j

   # Backup data
   docker cp code-graph-neo4j:/data ./neo4j-backup

   # Remove corrupted data
   docker volume rm code-graph_neo4j_data

   # Restart and restore
   docker-compose up -d neo4j
   # Re-import your data
   ```

2. **Check disk health:**
   ```bash
   # Check for disk errors
   dmesg | grep error
   sudo fsck /dev/sda1
   ```

## Common Error Messages

### "Cannot connect to Neo4j"
- Check Neo4j is running: `docker ps | grep neo4j`
- Check connection string in `.env`
- Check network connectivity

### "LLM provider not configured"
- Set `LLM_PROVIDER` in `.env`
- Install provider (Ollama/OpenAI/Gemini)
- Download models if using Ollama

### "Memory not found"
- Check project_id is correct
- Verify memory exists: `MATCH (m:Memory) RETURN m`
- Rebuild search index

### "Operation timeout"
- Increase timeout in `.env`
- Check system resources
- Process smaller documents

### "Permission denied"
- Check file permissions: `ls -la`
- Fix with: `chmod +x start.py`
- Check Docker permissions: Add user to docker group

### "Module not found"
- Install dependencies: `uv pip install -e .`
- Check virtual environment is activated
- Set PYTHONPATH: `export PYTHONPATH=$PWD`

## Getting More Help

### Collect Diagnostic Information

When reporting issues, include:

```bash
# System information
uname -a
python --version
docker --version

# Application logs
docker logs code-graph-api > api.log
docker logs code-graph-neo4j > neo4j.log

# Configuration (remove sensitive data!)
cat .env | sed 's/PASSWORD=.*/PASSWORD=REDACTED/'

# Neo4j information
# In Neo4j Browser:
CALL dbms.components()
CALL apoc.version()
```

### Where to Get Help

1. **Documentation**: https://code-graph.vantagecraft.dev
2. **GitHub Issues**: Search existing issues or create new one
3. **GitHub Discussions**: Ask questions
4. **Discord/Slack**: Community chat (if available)

### Creating a Good Bug Report

Include:

1. **Environment**: OS, Python version, deployment mode
2. **Steps to reproduce**: Exact commands and actions
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Logs**: Relevant error messages and stack traces
6. **Configuration**: Sanitized `.env` file contents
7. **Attempts to fix**: What you've already tried

### Example Bug Report Template

```markdown
## Environment
- OS: Ubuntu 22.04
- Python: 3.13.1
- Deployment: Docker Compose
- Version: 0.7.0

## Issue
Memory search returns no results despite having memories in database.

## Steps to Reproduce
1. Add memory: `curl -X POST ...`
2. Search memory: `curl -X POST ...`
3. Gets empty result: `{"memories": []}`

## Expected Behavior
Should return the memory added in step 1.

## Logs
```
[ERROR] Memory search failed: Index not found
```

## Configuration
```env
NEO4J_URI=bolt://neo4j:7687
LLM_PROVIDER=ollama
```

## Attempts to Fix
- Restarted Neo4j: No change
- Checked memory exists: Confirmed with Cypher query
- Rebuilt index: Same error
```

## Need Immediate Help?

For critical production issues:

1. Check [Status Page](https://status.example.com) (if available)
2. Rollback to previous version
3. Enable debug logging: `LOG_LEVEL=DEBUG`
4. Contact maintainers directly
5. Post in #urgent channel (if community exists)

Remember: Most issues are configuration-related. Double-check your `.env` file and ensure all services are running!
