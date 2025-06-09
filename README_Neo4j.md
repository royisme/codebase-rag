# Neo4j 知识图谱服务

基于 Neo4j 内置向量索引的现代化 GraphRAG 解决方案，使用 LlamaIndex 和 Ollama 构建智能知识库。

## 🚀 架构优势

### 统一存储架构
- **单一数据库**: 使用 Neo4j 5.x 内置向量索引，无需额外的向量数据库
- **数据一致性**: 文本、图结构和向量存储在同一个数据库中
- **简化运维**: 只需维护一个 Neo4j 实例

### 现代化技术栈
- **LlamaIndex**: 官方推荐的 GraphRAG 框架
- **Neo4j**: 世界领先的图数据库，内置向量搜索
- **Ollama**: 本地化 LLM 和嵌入模型服务
- **FastAPI**: 高性能异步 Web 框架

### 强大的查询能力
- **混合搜索**: 同时进行图遍历和向量相似度搜索
- **多模式查询**: 支持纯图查询、纯向量查询和混合查询
- **智能检索**: 自动选择最佳检索策略

## 📋 系统要求

### 必需服务
- **Neo4j 5.x**: 支持向量索引的版本
- **Ollama**: 本地 LLM 服务
- **Python 3.8+**: 运行环境

### 推荐配置
```bash
# Neo4j
Neo4j 5.15+ (Community 或 Enterprise)
内存: 4GB+
存储: SSD 推荐

# Ollama 模型
LLM: llama2, mistral, qwen
Embedding: nomic-embed-text, all-minilm
```

## 🛠️ 安装配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动 Neo4j
```bash
# 使用 Docker
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -v $HOME/neo4j/data:/data \
    -v $HOME/neo4j/logs:/logs \
    -v $HOME/neo4j/import:/var/lib/neo4j/import \
    -v $HOME/neo4j/plugins:/plugins \
    --env NEO4J_AUTH=neo4j/password \
    neo4j:5.15
```

### 3. 启动 Ollama
```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull llama2
ollama pull nomic-embed-text
```

### 4. 配置环境变量
```bash
# .env 文件
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

OLLAMA_HOST=http://localhost:11434
MODEL=llama2
EMBEDDING_MODEL=nomic-embed-text
```

## 🚀 快速开始

### 启动服务
```bash
python main.py
```

### 初始化知识图谱
```bash
curl -X POST "http://localhost:8123/api/v1/neo4j-knowledge/initialize"
```

### 添加文档
```bash
curl -X POST "http://localhost:8123/api/v1/neo4j-knowledge/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Python 是一种高级编程语言...",
    "title": "Python 编程基础",
    "metadata": {"category": "programming"}
  }'
```

### 查询知识库
```bash
curl -X POST "http://localhost:8123/api/v1/neo4j-knowledge/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是 Python？",
    "mode": "hybrid"
  }'
```

## 📚 API 文档

### 核心端点

#### 初始化服务
```http
POST /api/v1/neo4j-knowledge/initialize
```

#### 文档管理
```http
# 添加文档
POST /api/v1/neo4j-knowledge/documents

# 上传文件
POST /api/v1/neo4j-knowledge/files

# 批量添加目录
POST /api/v1/neo4j-knowledge/directories
```

#### 查询检索
```http
# 智能问答
POST /api/v1/neo4j-knowledge/query

# 向量搜索
POST /api/v1/neo4j-knowledge/search

# 图谱结构
GET /api/v1/neo4j-knowledge/schema
```

#### 系统管理
```http
# 统计信息
GET /api/v1/neo4j-knowledge/statistics

# 健康检查
GET /api/v1/neo4j-knowledge/health

# 清空知识库
DELETE /api/v1/neo4j-knowledge/clear
```

## 🔍 查询模式

### 混合模式 (hybrid)
```json
{
  "question": "Python 有什么特点？",
  "mode": "hybrid"
}
```
同时使用图遍历和向量搜索，提供最全面的答案。

### 向量模式 (vector_only)
```json
{
  "question": "编程语言的特性",
  "mode": "vector_only"
}
```
基于语义相似度搜索，适合概念性查询。

### 图模式 (graph_only)
```json
{
  "question": "Python 与其他语言的关系",
  "mode": "graph_only"
}
```
基于图结构遍历，适合关系性查询。

## 🧪 测试验证

### 运行测试
```bash
python test_neo4j_knowledge.py
```

### 测试内容
- ✅ 服务初始化
- ✅ 文档添加和索引
- ✅ 多模式查询
- ✅ 向量相似度搜索
- ✅ 图谱结构查询
- ✅ 文件上传处理

## 🏗️ 架构

```
文档 → LlamaIndex → Neo4j (向量 + 图)
查询 → 单一 Cypher 查询 → 统一结果
```

## 核心特性

### 智能文档处理
- 自动文档分块
- 实体关系提取
- 向量嵌入生成
- 图结构构建

### 高效查询引擎
- 混合检索策略
- 上下文感知回答
- 多跳图遍历
- 语义相似度匹配

### 灵活扩展性
- 支持多种文档格式
- 可配置嵌入模型
- 自定义查询策略
- 插件化架构

## 🔧 配置选项

### Neo4j 配置
```python
# 向量索引配置
vector_index_name = "knowledge_vectors"
vector_dimension = 384  # 根据嵌入模型调整
```

### LlamaIndex 配置
```python
# 文档处理
chunk_size = 512
chunk_overlap = 50

# 查询配置
similarity_top_k = 10
response_mode = "tree_summarize"
```

### Ollama 配置
```python
# LLM 模型
ollama_model = "llama2"
temperature = 0.1

# 嵌入模型
embedding_model = "nomic-embed-text"
```

## 📈 性能优化

### Neo4j 优化
```cypher
-- 创建向量索引
CREATE VECTOR INDEX knowledge_vectors 
FOR (n:Document) ON (n.embedding) 
OPTIONS {indexConfig: {
  `vector.dimensions`: 384,
  `vector.similarity_function`: 'cosine'
}}

-- 创建文本索引
CREATE FULLTEXT INDEX document_text 
FOR (n:Document) ON EACH [n.text, n.title]
```

### 查询优化
- 使用适当的 `top_k` 值
- 合理设置 `chunk_size`
- 启用查询缓存
- 监控查询性能

## 🚨 故障排除

### 常见问题

#### Neo4j 连接失败
```bash
# 检查 Neo4j 状态
docker logs neo4j

# 验证连接
curl http://localhost:7474
```

#### Ollama 模型未找到
```bash
# 列出已安装模型
ollama list

# 下载缺失模型
ollama pull nomic-embed-text
```

#### 向量索引错误
```cypher
// 检查索引状态
SHOW INDEXES

// 重建索引
DROP INDEX knowledge_vectors IF EXISTS;
CREATE VECTOR INDEX knowledge_vectors ...
```

## 📝 开发指南

### 添加新的文档类型
```python
# 扩展文档处理器
class CustomDocumentProcessor:
    def process(self, content: str) -> Document:
        # 自定义处理逻辑
        return Document(text=content, metadata={...})
```

### 自定义查询策略
```python
# 实现自定义检索器
class CustomRetriever:
    def retrieve(self, query: str) -> List[Node]:
        # 自定义检索逻辑
        return nodes
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🙏 致谢

- [Neo4j](https://neo4j.com/) - 图数据库技术
- [LlamaIndex](https://www.llamaindex.ai/) - RAG 框架
- [Ollama](https://ollama.ai/) - 本地 LLM 服务

---

**现代化 GraphRAG，从 Neo4j 开始！** 🚀 