# 代码图知识系统

基于 Neo4j GraphRAG 技术构建的软件开发智能知识管理系统，提供先进的代码智能分析和自动化开发辅助能力。

## 概述

代码图知识系统是一个企业级解决方案，将非结构化的开发文档和代码转换为结构化、可查询的知识图谱。通过结合向量搜索、图数据库技术和大语言模型，提供智能代码分析、文档管理和开发辅助功能。

## 核心功能

### 当前功能（第一阶段：文档智能与向量搜索）
- **多格式文档处理**：支持文本、markdown、PDF、代码文件等多种文档格式
- **Neo4j GraphRAG 集成**：使用 Neo4j 原生向量索引的高级图检索增强生成
- **智能查询引擎**：结合向量相似度和图遍历的混合搜索
- **异步任务处理**：支持大型文档集合的后台处理和实时监控
- **实时任务监控**：多种实时监控方案
  - Web UI监控：NiceGUI界面，支持文件上传和目录批处理
  - SSE流式API：HTTP Server-Sent Events实时任务进度推送
  - MCP实时工具：AI助手集成的任务监控工具
- **RESTful API**：完整的文档管理和知识查询 API 端点
- **MCP 协议支持**：模型上下文协议集成，兼容 AI 助手
- **多提供商LLM支持**：兼容 Ollama、OpenAI、Gemini 和 OpenRouter 模型
- **大文件处理策略**：智能文件大小检测和多种处理方案

### 技术架构
- **FastAPI 后端**：高性能异步网络框架
- **Neo4j 数据库**：具有原生向量搜索功能的图数据库
- **LlamaIndex 集成**：先进的文档处理和检索管道
- **灵活的嵌入模型**：支持 HuggingFace 和 Ollama 嵌入模型
- **模块化设计**：清晰的关注点分离和可插拔组件

## 项目路线图

### 第二阶段：结构化数据与图谱增强（SQL 与图感知）
**目标**：集成对 SQL 文件的解析能力，构建一个真正的知识图谱，实现更精确的结构化查询。

**计划功能**：
- SQL 架构解析和分析
- 数据库关系映射
- 代码与数据库架构的交叉引用链接
- 增强的图遍历算法
- 结构化查询优化
- 数据库文档生成

### 第三阶段：深度代码智能与自动化（代码智能与自动化）
**目标**：让系统能够"读懂"代码，并引入异步任务和 Git 集成，使其成为一个"活"的系统。

**计划功能**：
- 先进的代码解析和分析（基于AST）
- 函数和类关系映射
- Git 仓库集成和变更跟踪
- 自动化代码文档生成
- 代码审查辅助和建议
- 智能代码补全和重构建议
- 依赖分析和影响评估
- 持续集成管道集成

## 安装

### 系统要求
- Python 3.13 或更高版本
- Neo4j 5.0 或更高版本
- Ollama（可选，用于本地 LLM 支持）

### 快速开始

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/code-graph.git
   cd code-graph
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   # 或使用 uv（推荐）
   uv pip install -e .
   ```

3. **配置环境**
   ```bash
   cp env.example .env
   # 编辑 .env 文件进行配置
   ```

4. **启动 Neo4j 数据库**
   ```bash
   # 使用 Docker
   docker run \
       --name neo4j-code-graph \
       -p 7474:7474 -p 7687:7687 \
       -e NEO4J_AUTH=neo4j/password \
       -e NEO4J_PLUGINS='["apoc"]' \
       neo4j:5.15
   ```

5. **运行应用程序**
   ```bash
   # 启动主服务
   python start.py
   # 或使用脚本入口点
   uv run server
   
   # 启动MCP服务（可选）
   python start_mcp.py
   # 或使用脚本入口点
   uv run mcp_client
   ```

6. **访问界面**
   - API 文档：http://localhost:8000/docs
   - 任务监控：http://localhost:8000/ui/monitor
   - 实时监控SSE：http://localhost:8000/api/v1/sse/tasks
   - 健康检查：http://localhost:8000/api/v1/health

## API 使用

### 添加文档
```python
import httpx

# 添加单个文档
response = httpx.post("http://localhost:8000/api/v1/documents/", json={
    "content": "您的文档内容",
    "title": "文档标题",
    "metadata": {"source": "manual", "type": "documentation"}
})

# 添加文件
response = httpx.post("http://localhost:8000/api/v1/documents/file", json={
    "file_path": "/path/to/your/document.md"
})

# 添加目录
response = httpx.post("http://localhost:8000/api/v1/documents/directory", json={
    "directory_path": "/path/to/docs",
    "recursive": true,
    "file_extensions": [".md", ".txt", ".py"]
})
```

### 查询知识
```python
# 查询知识库
response = httpx.post("http://localhost:8000/api/v1/knowledge/query", json={
    "question": "认证系统是如何工作的？",
    "mode": "hybrid",  # 或 "graph_only", "vector_only"
    "use_tools": False,
    "top_k": 5
})

# 搜索相似文档
response = httpx.post("http://localhost:8000/api/v1/knowledge/search", json={
    "query": "用户认证",
    "top_k": 10
})
```

## 实时任务监控

系统提供三种实时任务监控方案：

### 1. Web UI 监控界面
访问 http://localhost:8000/ui/monitor 使用图形界面：
- 实时任务状态更新
- 文件上传功能（50KB大小限制）
- 目录批量处理
- 任务进度可视化

### 2. Server-Sent Events (SSE) API
通过 HTTP 流式端点进行实时监控：

```javascript
// 监控单个任务
const eventSource = new EventSource('/api/v1/sse/task/task-id');
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Task progress:', data.progress);
};

// 监控所有任务
const allTasksSource = new EventSource('/api/v1/sse/tasks');
```

### 3. MCP 实时工具
通过 MCP 协议进行任务监控：

```python
# 使用纯MCP客户端监控
# 参见 examples/pure_mcp_client.py

# 监控单个任务
result = await session.call_tool("watch_task", {
    "task_id": task_id,
    "timeout": 300,
    "interval": 1.0
})

# 监控多个任务
result = await session.call_tool("watch_tasks", {
    "task_ids": [task1, task2, task3],
    "timeout": 300
})
```

## MCP 集成

系统支持模型上下文协议（MCP），可与 AI 助手无缝集成：

```bash
# 启动 MCP 服务器
python start_mcp.py

# 或与您的 MCP 客户端集成
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

### 客户端实现示例
- `examples/pure_mcp_client.py`: 纯MCP客户端，使用MCP工具进行监控
- `examples/hybrid_http_sse_client.py`: HTTP + SSE 混合方案

## 配置

`.env` 文件中的关键配置选项：

```bash
# 应用程序
APP_NAME=Code Graph Knowledge System
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 监控界面
ENABLE_MONITORING=true        # 启用/禁用Web监控界面
MONITORING_PATH=/ui          # 监控界面基础路径

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# LLM 配置
LLM_PROVIDER=ollama  # 或 openai, gemini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text

# 处理配置
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=10
VECTOR_DIMENSION=768
```

## 开发

### 项目结构
```
code_graph/
├── api/                    # FastAPI 路由处理器
├── core/                   # 应用核心（FastAPI 设置、中间件）
├── services/               # 业务逻辑服务
├── monitoring/             # 任务监控界面
├── data/                   # 数据存储和模型
├── tests/                  # 测试套件
├── docs/                   # 文档
└── config.py              # 配置管理
```

### 运行测试
```bash
pytest tests/
```

### 代码质量
```bash
# 格式化代码
black .
isort .

# 运行代码检查
ruff check .
```

## 贡献

1. Fork 仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 支持

- 文档：[GitHub Wiki](https://github.com/yourusername/code-graph/wiki)
- Neo4j 技术指南：[README_Neo4j.md](README_Neo4j.md)
- 问题：[GitHub Issues](https://github.com/yourusername/code-graph/issues)
- 讨论：[GitHub Discussions](https://github.com/yourusername/code-graph/discussions)

## 致谢

- [Neo4j](https://neo4j.com/) 提供强大的图数据库技术
- [LlamaIndex](https://llamaindex.ai/) 提供文档处理框架
- [FastAPI](https://fastapi.tiangolo.com/) 提供优秀的网络框架
- [NiceGUI](https://nicegui.io/) 提供监控界面 