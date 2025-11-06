# MCP Service Architecture

## 重要说明：MCP 不使用 HTTP 端口！

MCP (Model Context Protocol) 使用 **stdio** (标准输入/输出) 通信，**不是** HTTP 端口。

### 两种服务模式

本项目提供两种独立的服务模式：

```
┌─────────────────────────────────────────────────────────────┐
│                   Service Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. HTTP API Service (Docker/Production)                     │
│     ├── Command: python start.py                            │
│     ├── Port: 8000 (HTTP)                                   │
│     ├── Protocol: REST API + FastAPI                        │
│     ├── Usage: Web UI, HTTP clients, curl                   │
│     └── Access: http://localhost:8000                       │
│                                                              │
│  2. MCP Service (Local Development)                         │
│     ├── Command: python start_mcp.py                        │
│     ├── Port: NONE (stdio)                                  │
│     ├── Protocol: MCP via stdin/stdout                      │
│     ├── Usage: Claude Desktop, VS Code MCP                  │
│     └── Access: Process communication                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 详细说明

### 1. HTTP API Service（在 Docker 中运行）

**启动方式:**
```bash
python start.py
```

**传输协议:**
- HTTP REST API
- 监听端口：8000
- 协议：TCP/HTTP

**通信方式:**
```
Client → HTTP Request → http://localhost:8000/api/v1/* → FastAPI → Response
```

**用途:**
- ✅ Web UI 访问
- ✅ HTTP 客户端调用
- ✅ curl/Postman 测试
- ✅ 生产环境部署
- ✅ Docker 容器运行

**Docker 配置:**
```dockerfile
EXPOSE 8000  # ✅ HTTP API 端口
CMD ["python", "start.py"]
```

### 2. MCP Service（本地开发环境）

**启动方式:**
```bash
python start_mcp.py
```

**传输协议:**
- **stdio** (标准输入/输出)
- **无 TCP 端口**
- 进程间通信

**通信方式:**
```
Claude Desktop → 启动子进程 → python start_mcp.py
                    ↓
              stdin/stdout 通信
                    ↓
           MCP Protocol JSON-RPC
```

**关键代码** (mcp_server.py:346-358):
```python
async def main():
    from mcp.server.stdio import stdio_server  # ← stdio，不是 HTTP！

    logger.info("Transport: stdio")  # ← 明确标注

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,   # ← stdin
            write_stream,  # ← stdout
            ...
        )
```

**用途:**
- ✅ Claude Desktop 集成
- ✅ VS Code MCP 扩展
- ✅ 其他 MCP 客户端
- ✅ 本地开发调试

**MCP 客户端配置** (Claude Desktop):
```json
{
  "mcpServers": {
    "codebase-rag": {
      "command": "python",
      "args": ["/path/to/start_mcp.py"],
      "env": {}
    }
  }
}
```

## Docker 中的 MCP

### ❌ 常见误解

> "MCP 需要在 Docker 中 expose 端口"

**错误！** MCP 使用 stdio，不使用网络端口。

### ✅ 正确理解

**Docker 中运行的是 HTTP API，不是 MCP:**

```bash
# Docker 运行 HTTP API
docker run -p 8000:8000 codebase-rag
# ↓
# python start.py
# ↓
# FastAPI 监听 8000 端口
# ↓
# http://localhost:8000/api/v1/*
```

**MCP 在本地运行，连接到 Docker 容器中的服务:**

```
┌─────────────────────────────────────────────────────────────┐
│  Host Machine (你的电脑)                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Claude Desktop                                              │
│       │                                                      │
│       │ 启动子进程                                            │
│       ↓                                                      │
│  python start_mcp.py (stdio)                                 │
│       │                                                      │
│       │ MCP tools 内部调用                                    │
│       ↓                                                      │
│  HTTP 请求 → http://localhost:8000/api/v1/*                 │
│       │                                                      │
│ ─────│─────────────────────────────────────────────────── │
│       ↓ Docker bridge network                                │
├─────────────────────────────────────────────────────────────┤
│  Docker Container                                            │
│                                                              │
│  FastAPI (port 8000)                                         │
│       │                                                      │
│       ↓                                                      │
│  Neo4j, Services, etc.                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 如果想在 Docker 中使用 MCP

有两种方式：

#### 方式 1: 宿主机运行 MCP，Docker 运行 HTTP API（推荐）

**宿主机:**
```bash
# 配置 MCP 客户端（Claude Desktop等）
# 让 MCP 调用 http://localhost:8000/api/v1/*
python start_mcp.py
```

**Docker:**
```bash
# 运行 HTTP API
docker run -p 8000:8000 codebase-rag
```

**优点:**
- ✅ MCP 和 HTTP API 分离
- ✅ MCP 客户端（Claude Desktop）在本地运行
- ✅ 简单直接

#### 方式 2: Docker 中同时运行两个服务（不推荐）

如果需要在容器中运行 MCP（不常见），需要：

1. **在容器内启动 MCP:**
   ```bash
   docker exec -it codebase-rag python start_mcp.py
   ```

2. **通过 docker exec 进入容器:**
   ```bash
   docker exec -it codebase-rag /bin/bash
   python start_mcp.py
   ```

3. **配置客户端连接到容器内的 MCP:**
   ```json
   {
     "mcpServers": {
       "codebase-rag": {
         "command": "docker",
         "args": ["exec", "-i", "codebase-rag", "python", "start_mcp.py"]
       }
     }
   }
   ```

**缺点:**
- ❌ 复杂
- ❌ MCP 客户端需要 docker 访问权限
- ❌ 不利于生产环境

## 端口总结

| 服务 | 启动命令 | 端口 | 协议 | Docker |
|------|---------|------|------|--------|
| **HTTP API** | `python start.py` | **8000** | HTTP/REST | ✅ 需要 EXPOSE 8000 |
| **MCP Service** | `python start_mcp.py` | **无** | stdio | ❌ 不需要端口 |

## 当前 Dockerfile 配置（正确）

```dockerfile
# ✅ 只需要 expose HTTP API 端口
EXPOSE 8000

# ✅ 默认启动 HTTP API
CMD ["python", "start.py"]
```

**不需要额外的 MCP 端口配置！**

## 使用场景

### 场景 1: 生产环境（推荐）

```bash
# Docker 运行 HTTP API
docker-compose up -d

# 访问 Web UI
http://localhost:8000

# 使用 REST API
curl http://localhost:8000/api/v1/health
```

### 场景 2: 本地开发 + Claude Desktop

```bash
# 1. 启动 Docker（HTTP API）
docker-compose up -d

# 2. 配置 Claude Desktop 使用 MCP
# 编辑 claude_desktop_config.json:
{
  "mcpServers": {
    "codebase-rag": {
      "command": "python",
      "args": ["/absolute/path/to/start_mcp.py"],
      "env": {
        "API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}

# 3. 在 Claude Desktop 中使用 MCP tools
```

### 场景 3: VS Code + MCP 扩展

```bash
# 1. 启动 Docker（HTTP API）
docker-compose up -d

# 2. 安装 VS Code MCP 扩展

# 3. 配置 MCP server
# VS Code settings.json:
{
  "mcp.servers": {
    "codebase-rag": {
      "command": "python",
      "args": ["/absolute/path/to/start_mcp.py"]
    }
  }
}
```

## 常见问题

### Q: Docker 容器中的 MCP 功能会受影响吗？

**A:** 不会！因为：
- Docker 运行的是 **HTTP API**（端口 8000）
- MCP 是独立服务，在**宿主机**运行
- MCP tools 内部调用 HTTP API
- 两者完全独立

### Q: 为什么 MCP 不用 HTTP 端口？

**A:** MCP 协议设计：
- 使用 stdio (标准输入/输出)
- 作为子进程被客户端启动
- 通过 JSON-RPC over stdio 通信
- 更安全（不暴露网络端口）
- 更简单（不需要处理 HTTP）

### Q: 能否让 MCP 也用 HTTP？

**A:** 技术上可以，但：
- ❌ 违反 MCP 规范
- ❌ 失去 stdio 的安全性
- ❌ 客户端不支持
- ✅ 应该使用 HTTP API（已有）

### Q: Dockerfile 需要改动吗？

**A:** **不需要！** 当前配置完全正确：
```dockerfile
EXPOSE 8000          # ✅ HTTP API 端口
CMD ["python", "start.py"]  # ✅ 启动 HTTP API
```

## 架构对比

### 传统 HTTP 服务（单一）

```
Client → HTTP → Server (port 8000)
```

### 本项目（双模式）

```
模式 1 (Docker):
Web UI/curl → HTTP → FastAPI (port 8000) → Services

模式 2 (本地):
Claude Desktop → stdio → MCP Server → HTTP → FastAPI (port 8000) → Services
                  ↑                      ↑
              无端口                  内部调用
```

## 总结

### ✅ 重要结论

1. **MCP 使用 stdio，不是 HTTP 端口**
2. **Docker 只需要 EXPOSE 8000（HTTP API）**
3. **MCP 和 HTTP API 是两个独立的服务**
4. **MCP 在宿主机运行，HTTP API 在 Docker 运行**
5. **两者可以并存，互不影响**

### 📋 快速检查清单

- ✅ Dockerfile EXPOSE 8000
- ✅ HTTP API 可访问：`http://localhost:8000`
- ✅ MCP 在本地运行（如需要）
- ✅ MCP 客户端配置正确
- ✅ 两个服务独立工作

**当前 Docker 配置完全正确，无需修改！**
