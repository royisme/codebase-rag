# Upgrade Guide: Two-Port Architecture

## 概述

系统已升级为**双端口架构**，清晰分离MCP服务和Web UI：

```
Port 8000: MCP SSE Service (PRIMARY)
Port 8080: Web UI + REST API (SECONDARY)
```

## 为什么需要两个端口？

### 之前（单端口，混乱）
```
Port 8000:
  - MCP SSE at /mcp/*
  - Web UI at /
  - REST API at /api/v1/*
  - 职责不清晰
```

### 现在（双端口，清晰）
```
Port 8000 (PRIMARY):
  - MCP SSE Service
  - GET /sse
  - POST /messages/
  - 专注MCP协议

Port 8080 (SECONDARY):
  - Web UI (状态监控)
  - REST API
  - Prometheus metrics
  - 辅助功能
```

## 升级步骤

### 1. 更新 docker-compose.yml

**之前:**
```yaml
ports:
  - "${APP_PORT:-8000}:8000"
environment:
  - PORT=8000
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
```

**现在:**
```yaml
ports:
  - "${MCP_PORT:-8000}:8000"      # MCP SSE (PRIMARY)
  - "${WEB_UI_PORT:-8080}:8080"   # Web UI (SECONDARY)
environment:
  - MCP_PORT=8000
  - WEB_UI_PORT=8080
healthcheck:
  # Health check在Web UI端口
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
```

### 2. 更新环境变量（可选）

创建 `.env` 文件：

```bash
# 使用默认端口
MCP_PORT=8000
WEB_UI_PORT=8080

# 或自定义端口
MCP_PORT=9000
WEB_UI_PORT=9001
```

### 3. 更新客户端连接

**MCP客户端配置:**
```json
{
  "mcpServers": {
    "codebase-rag": {
      "transport": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

**Web UI访问:**
```
http://localhost:8080/
```

**REST API调用:**
```bash
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/tasks
```

## Docker Compose 使用

### 默认端口
```bash
docker-compose up -d

# 访问服务:
# MCP SSE: http://localhost:8000/sse
# Web UI:  http://localhost:8080/
```

### 自定义端口
```bash
# 通过环境变量
MCP_PORT=9000 WEB_UI_PORT=9001 docker-compose up -d

# 或使用.env文件
echo "MCP_PORT=9000" > .env
echo "WEB_UI_PORT=9001" >> .env
docker-compose up -d
```

### 端口映射
```bash
# 映射到不同的宿主机端口
docker-compose up -d
# 然后访问:
# MCP:    localhost:8000 → container:8000
# Web UI: localhost:8080 → container:8080

# 自定义映射
docker run \
  -p 9000:8000 \   # MCP映射到9000
  -p 9001:8080 \   # Web UI映射到9001
  codebase-rag
```

## 需要更新的文件

以下文件需要更新为双端口配置：

### ✅ 已更新
- [x] `config.py` - 添加mcp_port和web_ui_port
- [x] `main.py` - 双进程启动两个服务
- [x] `core/app.py` - Web UI专用
- [x] `core/mcp_sse.py` - MCP SSE专用
- [x] `Dockerfile` - EXPOSE 8000 8080
- [x] `docker-compose.yml` - 根docker-compose
- [x] `docker/docker-compose.minimal.yml` - 最小部署模式
- [x] `docker/docker-compose.standard.yml` - 标准部署模式
- [x] `docker/docker-compose.full.yml` - 完整部署模式

**更新模板:**
```yaml
# 在每个文件中，更新mcp服务部分:
ports:
  - "${MCP_PORT:-8000}:8000"
  - "${WEB_UI_PORT:-8080}:8080"
environment:
  - MCP_PORT=8000
  - WEB_UI_PORT=8080
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
```

## 验证升级

### 1. 检查端口监听
```bash
docker-compose up -d
docker-compose ps

# 应该看到:
# codebase-rag-mcp ... 0.0.0.0:8000->8000/tcp, 0.0.0.0:8080->8080/tcp
```

### 2. 测试MCP SSE
```bash
# 测试SSE连接
curl -N http://localhost:8000/sse

# 列出MCP工具
curl -X POST http://localhost:8000/messages/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 3. 测试Web UI
```bash
# 健康检查
curl http://localhost:8080/api/v1/health

# 访问Web UI
open http://localhost:8080/
```

### 4. 检查日志
```bash
docker-compose logs mcp

# 应该看到:
# STARTING PRIMARY SERVICE: MCP SSE
# MCP SSE Server: http://0.0.0.0:8000/sse
# STARTING SECONDARY SERVICE: Web UI + REST API
# Web UI: http://0.0.0.0:8080/
```

## 故障排查

### 问题：端口已被占用
```bash
# 检查端口占用
lsof -i :8000
lsof -i :8080

# 解决方案1：使用不同端口
MCP_PORT=9000 WEB_UI_PORT=9001 docker-compose up -d

# 解决方案2：停止占用端口的服务
sudo kill <PID>
```

### 问题：Health check失败
```bash
# 确保health check在8080端口（不是8000）
docker-compose logs mcp | grep health

# 手动测试
curl http://localhost:8080/api/v1/health
```

### 问题：MCP客户端连接失败
```bash
# 确认MCP SSE端点
curl -N http://localhost:8000/sse

# 检查MCP服务日志
docker-compose logs mcp | grep "MCP SSE"
```

## 向后兼容

### Legacy模式（已弃用）

如果需要临时使用旧的单端口模式：

```python
# 使用旧的启动脚本
python start.py  # 会启动双端口

# 或使用stdio模式（本地开发）
python start_mcp.py
```

### 迁移计划

1. **阶段1（当前）**: 双端口默认，legacy支持
2. **阶段2（未来）**: 移除legacy PORT配置
3. **阶段3（长期）**: 完全移除单端口支持

## 配置参考

### 环境变量
```bash
# 服务器配置
HOST=0.0.0.0                    # 监听地址
MCP_PORT=8000                   # MCP SSE端口（PRIMARY）
WEB_UI_PORT=8080                # Web UI端口（SECONDARY）

# Legacy（不推荐）
PORT=8000                       # 已弃用
```

### Docker Compose
```yaml
version: '3.8'
services:
  mcp:
    ports:
      - "${MCP_PORT:-8000}:8000"
      - "${WEB_UI_PORT:-8080}:8080"
    environment:
      - MCP_PORT=8000
      - WEB_UI_PORT=8080
```

### Dockerfile
```dockerfile
EXPOSE 8000 8080

# MCP_PORT (default: 8000) - MCP SSE Service
# WEB_UI_PORT (default: 8080) - Web UI + REST API
```

## 最佳实践

### 1. 使用环境变量
```bash
# .env文件
MCP_PORT=8000
WEB_UI_PORT=8080
```

### 2. 清晰的端口分配
```
开发环境:
  MCP: 8000
  Web UI: 8080

生产环境:
  MCP: 8000
  Web UI: 8080

测试环境:
  MCP: 9000
  Web UI: 9001
```

### 3. 防火墙配置
```bash
# 只暴露必要的端口
# MCP: 8000（AI客户端访问）
# Web UI: 8080（人类访问）

# 不要暴露Neo4j端口！
# Neo4j: 7687（仅容器内部）
```

## FAQ

### Q: 为什么要两个端口？
A: 清晰分离职责，MCP是PRIMARY（核心功能），Web UI是SECONDARY（监控辅助）

### Q: 可以只用一个端口吗？
A: 技术上可以，但不推荐。双端口更清晰，易于维护和扩展。

### Q: 端口号可以改吗？
A: 可以！通过MCP_PORT和WEB_UI_PORT环境变量配置。

### Q: MCP工具需要改代码吗？
A: 不需要！工具定义与传输层无关，25个MCP工具完全不需要修改。

### Q: stdio模式还能用吗？
A: 可以！`python start_mcp.py`仍然支持stdio（用于本地开发和Claude Desktop）。

## 总结

✅ **升级要点:**
1. 两个端口：8000（MCP）+ 8080（Web UI）
2. 配置驱动：通过MCP_PORT和WEB_UI_PORT环境变量
3. 向后兼容：Legacy模式仍然支持
4. 无需改工具：MCP工具代码不需要修改

✅ **立即行动:**
1. 更新docker-compose配置
2. 测试双端口连接
3. 更新客户端配置
4. 验证功能正常

有问题？查看 `MCP_SSE_GUIDE.md` 获取详细文档。
