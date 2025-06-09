# Code Graph Knowledge Service

基于 Neo4j 内置向量索引的现代化知识图谱服务，支持多种 LLM 和嵌入模型提供商，提供 Model Context Protocol (MCP) 接口。

## 🚀 主要特性

### 核心功能
- **Neo4j GraphRAG**: 使用 Neo4j 内置向量索引的现代化图检索增强生成
- **多模型支持**: 支持 Ollama、OpenAI、Google Gemini 等多种 LLM 和嵌入模型
- **混合查询**: 支持向量搜索、图遍历、混合模式三种查询方式
- **MCP 接口**: 完整的 Model Context Protocol 服务器实现
- **异步处理**: 完整的异步支持和超时控制

### 技术架构
- **知识图谱**: Neo4j 数据库 + 内置向量索引
- **文档处理**: LlamaIndex 框架进行文档解析和索引
- **向量搜索**: Neo4j 原生向量搜索，无需额外向量数据库
- **图遍历**: 利用 Neo4j 的图查询能力发现实体关系
- **API 接口**: FastAPI + MCP 双重接口支持

## 📋 系统要求

- Python 3.9+
- Neo4j 5.0+ (支持向量索引)
- 至少一个 LLM 提供商:
  - Ollama (本地部署)
  - OpenAI API
  - Google Gemini API

## 🛠️ 安装配置

### 1. 克隆项目
```bash
git clone <repository-url>
cd code_graph
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 启动 Neo4j
```bash
# 使用 Docker
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["apoc"]' \
    neo4j:5.15
```

### 4. 配置环境变量
复制 `env.example` 为 `.env` 并配置:

```bash
# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM 提供商选择 (ollama/openai/gemini)
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama

# Ollama 配置 (如果使用)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:latest
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# OpenAI 配置 (如果使用)
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Gemini 配置 (如果使用)
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-pro
GEMINI_EMBEDDING_MODEL=models/embedding-001
```

## 🚀 使用方法

### 1. 启动 MCP 服务器
```bash
python start_mcp.py
```

### 2. 测试 MCP 功能
```bash
python test_mcp_client.py
```

### 3. 直接使用知识服务
```python
from services.neo4j_knowledge_service import Neo4jKnowledgeService

# 初始化服务
service = Neo4jKnowledgeService()
await service.initialize()

# 添加文档
result = await service.add_document(
    content="这是一个测试文档...",
    title="测试文档",
    metadata={"category": "test"}
)

# 查询知识
result = await service.query(
    question="什么是知识图谱？",
    mode="hybrid"  # hybrid/graph_only/vector_only
)

print(result["answer"])
```

## 🔧 MCP 工具列表

### 核心工具
- `query_knowledge`: 知识图谱查询
- `search_similar_nodes`: 向量相似度搜索
- `add_document`: 添加文档到知识图谱
- `add_file`: 添加文件到知识图谱
- `add_directory`: 批量添加目录文件
- `get_graph_schema`: 获取图谱结构信息
- `get_statistics`: 获取统计信息
- `clear_knowledge_base`: 清空知识库

### 资源
- `knowledge://config`: 系统配置信息
- `knowledge://status`: 系统状态和健康检查
- `knowledge://recent-documents/{limit}`: 最近添加的文档

### 提示
- `suggest_queries`: 根据领域生成查询建议

## 📊 查询模式

### 1. 混合模式 (hybrid)
结合向量搜索和图遍历，推荐使用:
```python
result = await service.query("问题", mode="hybrid")
```

### 2. 仅图遍历 (graph_only)
只使用图关系进行查询:
```python
result = await service.query("问题", mode="graph_only")
```

### 3. 仅向量搜索 (vector_only)
只使用向量相似度搜索:
```python
result = await service.query("问题", mode="vector_only")
```

## ⚙️ 配置说明

### 超时设置
```bash
CONNECTION_TIMEOUT=30      # 连接超时 (秒)
OPERATION_TIMEOUT=120      # 操作超时 (秒)
LARGE_DOCUMENT_TIMEOUT=300 # 大文档处理超时 (秒)
```

### 文档处理
```bash
CHUNK_SIZE=512        # 文档分块大小
CHUNK_OVERLAP=50      # 分块重叠大小
TOP_K=5              # 检索结果数量
```

### 向量设置
```bash
VECTOR_DIMENSION=384  # 向量维度 (取决于嵌入模型)
```

## 🧪 测试

### 运行所有测试
```bash
python test_neo4j_knowledge.py
```

### 测试特定功能
```bash
# 测试 MCP 客户端
python test_mcp_client.py

# 测试知识服务
python test_service.py

# 测试数据管道
python test_pipeline.py
```

## 📁 项目结构

```
code_graph/
├── services/
│   ├── neo4j_knowledge_service.py  # 核心知识服务
│   └── pipeline/                   # 数据处理管道
├── api/                           # FastAPI 接口
├── tests/                         # 测试文件
├── config.py                      # 配置管理
├── mcp_server.py                  # MCP 服务器
├── start_mcp.py                   # MCP 启动脚本
└── requirements.txt               # 依赖列表
```

## 🔍 故障排除

### 常见问题

1. **模型未找到错误**
   - 检查 `.env` 文件中的模型名称
   - 确保 Ollama 服务运行并已下载模型
   - 验证 API 密钥配置

2. **Neo4j 连接失败**
   - 检查 Neo4j 服务状态
   - 验证连接参数和认证信息
   - 确保 Neo4j 版本支持向量索引

3. **超时错误**
   - 调整超时配置参数
   - 检查网络连接和服务响应时间
   - 考虑使用更快的模型

### 日志调试
```bash
# 启用调试日志
DEBUG=true python start_mcp.py
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [Neo4j 文档](https://neo4j.com/docs/)
- [LlamaIndex 文档](https://docs.llamaindex.ai/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP 框架](https://github.com/jlowin/fastmcp)
