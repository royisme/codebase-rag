# MCP SSE Service Guide

## Architecture Priority

```
┌─────────────────────────────────────────────────────────┐
│                   SERVICE ARCHITECTURE                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PRIMARY SERVICE (Core):                                 │
│    MCP SSE Transport                                     │
│    └── Port: 8000                                       │
│        └── GET  /mcp/sse       (SSE connection)         │
│        └── POST /mcp/messages/ (message receiving)      │
│                                                          │
│  SECONDARY SERVICE (Monitoring):                         │
│    Web UI & REST API                                     │
│    └── Port: 8000 (same port, different paths)         │
│        └── GET  /               (Web UI)                │
│        └── *    /api/v1/*       (REST API)              │
│        └── GET  /metrics        (Prometheus)            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**核心定位**: 这是一个**MCP服务器**，Web UI只是辅助查看状态。

## MCP SSE vs stdio

| 特性 | stdio | SSE (Server-Sent Events) |
|------|-------|-------------------------|
| **用途** | 本地开发 | Docker/生产环境 |
| **传输** | 标准输入/输出 | HTTP网络 |
| **端口** | 无 | 8000 |
| **客户端** | Claude Desktop本地启动 | 网络连接 |
| **Docker** | ❌ 不适合 | ✅ **推荐** |
| **生产环境** | ❌ 不适合 | ✅ **推荐** |
| **最佳实践** | 本地开发调试 | Docker容器服务 |

## MCP SSE Endpoints

### 1. SSE Connection Endpoint

```http
GET http://localhost:8000/mcp/sse
```

**用途**: 建立MCP SSE连接
**协议**: Server-Sent Events (持久连接)
**客户端**: 保持长连接接收服务器推送的消息

**示例**:
```bash
# 使用curl测试SSE连接
curl -N http://localhost:8000/mcp/sse
```

### 2. Message Receiving Endpoint

```http
POST http://localhost:8000/mcp/messages/
Content-Type: application/json
```

**用途**: 接收客户端发送的MCP消息
**协议**: HTTP POST with JSON-RPC 2.0 payload

**示例**:
```bash
# 发送MCP消息
curl -X POST http://localhost:8000/mcp/messages/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## Docker Deployment

### Build and Run

```bash
# 1. Build frontend (optional, for Web UI)
./build-frontend.sh

# 2. Build Docker image
DOCKER_BUILDKIT=1 docker build -t codebase-rag .

# 3. Run container
docker run -p 8000:8000 codebase-rag

# MCP SSE service available at:
# http://localhost:8000/mcp/sse
```

### Docker Compose

```yaml
services:
  codebase-rag:
    build: .
    ports:
      - "8000:8000"  # MCP SSE + Web UI
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
```

```bash
docker-compose up -d

# MCP SSE available at:
http://localhost:8000/mcp/sse
```

## Client Connection

### MCP Client Configuration

**For MCP clients that support SSE transport:**

```json
{
  "mcpServers": {
    "codebase-rag": {
      "transport": "sse",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

### Python Client Example

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    # Connect to MCP SSE server
    async with sse_client("http://localhost:8000/mcp") as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {tools}")

            # Call a tool
            result = await session.call_tool("query_knowledge", {
                "query": "What is this system?",
                "mode": "hybrid"
            })
            print(f"Result: {result}")

asyncio.run(main())
```

### JavaScript/TypeScript Client Example

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

// Connect to MCP SSE server
const transport = new SSEClientTransport(
  new URL("http://localhost:8000/mcp/sse")
);

const client = new Client({
  name: "mcp-client",
  version: "1.0.0",
}, {
  capabilities: {}
});

await client.connect(transport);

// List tools
const tools = await client.listTools();
console.log("Available tools:", tools);

// Call tool
const result = await client.callTool({
  name: "query_knowledge",
  arguments: {
    query: "What is this system?",
    mode: "hybrid"
  }
});
console.log("Result:", result);
```

## Available MCP Tools

The MCP SSE server provides **25 tools** across 5 categories:

### 1. Knowledge Base (5 tools)
- `query_knowledge` - Query with hybrid search
- `search_similar_nodes` - Vector similarity search
- `add_document` - Add single document
- `add_file` - Add file to knowledge base
- `add_directory` - Batch add directory

### 2. Code Graph (4 tools)
- `code_graph_ingest_repo` - Ingest code repository
- `code_graph_related` - Find related code
- `code_graph_impact` - Impact analysis
- `context_pack` - Build context pack

### 3. Memory Store (7 tools)
- `add_memory` - Add project memory
- `search_memories` - Search memories
- `get_memory` - Get specific memory
- `update_memory` - Update memory
- `delete_memory` - Delete memory
- `supersede_memory` - Replace memory
- `get_project_summary` - Get summary

### 4. Task Management (6 tools)
- `get_task_status` - Get task status
- `watch_task` - Watch single task
- `watch_tasks` - Watch multiple tasks
- `list_tasks` - List all tasks
- `cancel_task` - Cancel task
- `get_queue_stats` - Queue statistics

### 5. System (3 tools)
- `get_graph_schema` - Get Neo4j schema
- `get_statistics` - Get system stats
- `clear_knowledge_base` - Clear database

## Testing MCP SSE Service

### 1. Check Service Health

```bash
# Check if service is running
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "neo4j": true,
    "mcp_sse": true
  }
}
```

### 2. Test SSE Connection

```bash
# Establish SSE connection (will hang - that's correct)
curl -N http://localhost:8000/mcp/sse

# You should see SSE events stream
```

### 3. List MCP Tools

```bash
# Send tools/list request
curl -X POST http://localhost:8000/mcp/messages/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### 4. Call MCP Tool

```bash
# Query knowledge base
curl -X POST http://localhost:8000/mcp/messages/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "query_knowledge",
      "arguments": {
        "query": "What is this system?",
        "mode": "hybrid",
        "top_k": 5
      }
    }
  }'
```

## Monitoring & Status

### Web UI (Secondary Service)

Access the Web UI for visual monitoring:

```
http://localhost:8000/
```

**Features:**
- Task status monitoring
- System metrics
- Prometheus metrics visualization
- Real-time updates

### Prometheus Metrics

```bash
# Get Prometheus metrics
curl http://localhost:8000/metrics

# Metrics include:
# - graph_queries_total
# - task_queue_size
# - task_processing_duration
# - memory_store_operations
```

### REST API (Secondary Service)

```bash
# Get system statistics
curl http://localhost:8000/api/v1/statistics

# Get task list
curl http://localhost:8000/api/v1/tasks

# Get task status
curl http://localhost:8000/api/v1/tasks/{task_id}
```

## Development Mode

### Local Development with stdio (Legacy)

For local development without Docker, you can still use stdio:

```bash
# Run MCP stdio server
python start_mcp.py

# Configure Claude Desktop:
{
  "mcpServers": {
    "codebase-rag-local": {
      "command": "python",
      "args": ["/absolute/path/to/start_mcp.py"]
    }
  }
}
```

**When to use stdio:**
- ✅ Local development
- ✅ Claude Desktop integration
- ✅ Debugging MCP tools
- ❌ NOT for Docker/production

### Production with SSE (Recommended)

```bash
# Run with Docker
docker run -p 8000:8000 codebase-rag

# MCP SSE available at:
http://localhost:8000/mcp/sse
```

**When to use SSE:**
- ✅ Docker deployment
- ✅ Production environment
- ✅ Network access
- ✅ Multiple clients
- ✅ Scalability

## Security Considerations

### Network Security

1. **HTTPS in Production**
   ```nginx
   # Use nginx/traefik for HTTPS termination
   location /mcp/ {
     proxy_pass http://codebase-rag:8000/mcp/;
     proxy_set_header Host $host;
     proxy_set_header Upgrade $http_upgrade;
     proxy_set_header Connection "upgrade";
   }
   ```

2. **Authentication** (Optional)
   - Add API key authentication
   - Use OAuth 2.0
   - Implement JWT tokens

3. **CORS Configuration**
   - Configure allowed origins
   - Restrict to trusted domains

### Firewall

```bash
# Only expose port 8000
# Do NOT expose Neo4j port 7687 to public
docker run -p 8000:8000 codebase-rag  # ✅ Correct
docker run -p 8000:8000 -p 7687:7687 codebase-rag  # ❌ Dangerous
```

## Troubleshooting

### SSE Connection Failed

```bash
# Check if service is running
docker ps | grep codebase-rag

# Check logs
docker logs codebase-rag

# Look for:
# "MCP SSE service mounted at /mcp/*"
```

### No Response from MCP Tools

```bash
# Check Neo4j connection
curl http://localhost:8000/api/v1/health

# Ensure Neo4j is running
docker-compose up neo4j
```

### CORS Errors

```bash
# Check CORS middleware configuration
# in core/middleware.py

# Allow your client origin
ALLOWED_ORIGINS = [
  "http://localhost:3000",  # Frontend dev
  "http://localhost:8000",  # Production
  "https://your-domain.com"  # Your domain
]
```

## Best Practices

### 1. Use SSE for Docker/Production

```bash
# ✅ Recommended
docker run -p 8000:8000 codebase-rag
# Connect via: http://localhost:8000/mcp/sse
```

### 2. Use stdio for Local Development

```bash
# ✅ For local dev only
python start_mcp.py
# Configure Claude Desktop to use stdio
```

### 3. Monitor via Web UI

```bash
# Access Web UI for monitoring
http://localhost:8000/

# View:
# - Task status
# - System metrics
# - Tool usage
```

### 4. Scale with Multiple Instances

```yaml
# docker-compose.yml
services:
  codebase-rag:
    build: .
    deploy:
      replicas: 3  # Multiple instances
    ports:
      - "8000:8000"
```

## Migration from stdio to SSE

### Before (stdio only)

```json
{
  "mcpServers": {
    "codebase-rag": {
      "command": "python",
      "args": ["start_mcp.py"]
    }
  }
}
```

**Limitations:**
- ❌ Can't use in Docker
- ❌ No network access
- ❌ Single client only

### After (SSE recommended)

```json
{
  "mcpServers": {
    "codebase-rag": {
      "transport": "sse",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

**Benefits:**
- ✅ Works in Docker
- ✅ Network accessible
- ✅ Multiple clients
- ✅ Production ready

## Summary

### 🎯 Core Concept

**This is an MCP SERVER with SSE transport, not just an HTTP API.**

### 📋 Quick Reference

| What | Where | Protocol |
|------|-------|----------|
| **MCP SSE** (primary) | `http://localhost:8000/mcp/sse` | SSE |
| **MCP Messages** (primary) | `http://localhost:8000/mcp/messages/` | HTTP POST |
| Web UI (secondary) | `http://localhost:8000/` | HTTP |
| REST API (secondary) | `http://localhost:8000/api/v1/*` | HTTP |
| Metrics (secondary) | `http://localhost:8000/metrics` | HTTP |

### ✅ Recommendations

- **Docker/Production**: Use **SSE transport** (this implementation)
- **Local Development**: Use **stdio** (start_mcp.py)
- **Monitoring**: Use **Web UI** (secondary service)
- **Testing**: Use **REST API** (secondary service)

---

**MCP SSE is the PRIMARY service. Web UI is SECONDARY for monitoring.**
