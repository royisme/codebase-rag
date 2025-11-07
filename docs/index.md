# Code Graph Knowledge System


**Enterprise Knowledge Management Platform**

*Neo4j-powered graph database with multi-interface architecture (MCP/Web/REST) and intelligent code analysis*

[![Docker Hub](https://img.shields.io/docker/pulls/royisme/codebase-rag?style=flat-square)](https://hub.docker.com/r/royisme/codebase-rag)
[![GitHub](https://img.shields.io/github/stars/royisme/codebase-rag?style=flat-square)](https://github.com/royisme/codebase-rag)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)


---

## What is Code Graph Knowledge System?

Code Graph Knowledge System is an enterprise-grade solution that transforms unstructured development documentation and code into a structured, queryable knowledge graph. By combining **vector search**, **graph database technology**, and **large language models**, it provides intelligent code analysis, documentation management, and development assistance capabilities.

## ✨ Key Features

### 🎯 Deployment Modes

Choose the right deployment mode for your needs:

| Feature | Minimal | Standard | Full |
|---------|---------|----------|------|
| **Code Graph** | | | |
| └ Repository ingestion | ✅ | ✅ | ✅ |
| └ File relationship search | ✅ | ✅ | ✅ |
| └ Impact analysis | ✅ | ✅ | ✅ |
| └ Context packing | ✅ | ✅ | ✅ |
| **Memory Store** | | | |
| └ Manual management | ❌ | ✅ | ✅ |
| └ Vector search | ❌ | ✅ | ✅ |
| └ Auto extraction (Git) | ❌ | ❌ | ✅ |
| └ Auto extraction (Conversations) | ❌ | ❌ | ✅ |
| **Knowledge RAG** | | | |
| └ Document vectorization | ❌ | ❌ | ✅ |
| └ Intelligent Q&A | ❌ | ❌ | ✅ |
| **Requirements** | | | |
| └ Neo4j | ✅ | ✅ | ✅ |
| └ Embedding Model | ❌ | ✅ | ✅ |
| └ LLM | ❌ | ❌ | ✅ |
| **Image Size** | ~500MB | ~600MB | ~800MB |
| **Startup Time** | ~5s | ~8s | ~15s |

### 🚀 Core Capabilities

=== "Code Graph"
    **No LLM Required** - Pure graph-based code intelligence

    - **Repository Ingestion**: Parse and index entire codebases
    - **Relationship Discovery**: Find file dependencies and imports
    - **Impact Analysis**: Understand the blast radius of changes
    - **Context Packing**: Generate AI-friendly context bundles

    ```bash
    # Start minimal deployment
    make docker-minimal
    ```

=== "Memory Store"
    **Embedding Required** - Long-term project knowledge

    - **Manual Memory Management**: Add, search, update memories
    - **Vector Search**: Find relevant project decisions
    - **Auto Extraction**: Extract from git commits and conversations
    - **Knowledge Evolution**: Track decision changes over time

    ```bash
    # Start standard deployment
    make docker-standard
    ```

=== "Knowledge RAG"
    **LLM + Embedding Required** - Full AI capabilities

    - **Document Processing**: Index documentation and code
    - **Intelligent Q&A**: Answer questions about your codebase
    - **Multi-format Support**: Markdown, PDF, code files
    - **Hybrid Search**: Combine vector and graph traversal

    ```bash
    # Start full deployment
    make docker-full
    ```

## 🎯 Quick Start

### 1. Choose Your Deployment Mode

```bash
# Minimal - Code Graph only (No LLM needed)
make docker-minimal

# Standard - Code Graph + Memory (Embedding needed)
make docker-standard

# Full - All features (LLM + Embedding needed)
make docker-full
```

### 2. Access the System

- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Neo4j Browser**: [http://localhost:7474](http://localhost:7474)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 3. Ingest Your Repository

=== "MCP (Claude Desktop)"
    ```json
    // In Claude Desktop, use MCP tools:
    code_graph_ingest_repo({
      "local_path": "/path/to/your/repo",
      "mode": "incremental"
    })
    ```

=== "REST API"
    ```bash
    curl -X POST http://localhost:8000/api/v1/code-graph/ingest \
      -H "Content-Type: application/json" \
      -d '{
        "local_path": "/path/to/your/repo",
        "mode": "incremental"
      }'
    ```

## 🎨 Use Cases

### For Individual Developers

- **Learn Large Codebases**: Quickly understand unfamiliar projects
- **Code Navigation**: Find relationships and dependencies
- **Impact Assessment**: See what breaks before making changes

### For Development Teams

- **Project Knowledge Base**: Preserve team decisions and context
- **Onboarding**: Help new team members get up to speed
- **Documentation**: Auto-generate context for AI coding assistants

### For AI-Assisted Development

- **Claude Desktop Integration**: Use as MCP server for enhanced code understanding
- **VS Code Integration**: Access code graph directly in your editor
- **Context Generation**: Create optimal context for LLM queries

## 📚 Documentation

- [**Quick Start Guide**](getting-started/quickstart.md) - Get running in 5 minutes
- [**Deployment Overview**](deployment/overview.md) - Choose the right mode
- [**Code Graph Guide**](guide/code-graph/overview.md) - Learn code intelligence features
- [**MCP Integration**](guide/mcp/overview.md) - Use with Claude Desktop
- [**API Reference**](api/mcp-tools.md) - Complete tool documentation

## 🌟 Why Code Graph Knowledge System?

### 🎯 Flexible Architecture

- **No Vendor Lock-in**: Use Ollama, OpenAI, Gemini, or any LLM
- **Scalable**: From single developer to enterprise teams
- **Modular**: Only use what you need

### 🚀 Performance Optimized

- **Incremental Updates**: 60x faster than full re-indexing
- **Smart Caching**: Reduce redundant processing
- **Efficient Storage**: Neo4j native vector indexes

### 🔒 Privacy Focused

- **Self-Hosted**: Keep your code on your infrastructure
- **No Data Leaks**: Optional local LLM support
- **Secure**: Enterprise-grade Neo4j backend

## 🛠️ Technology Stack

- **Backend**: Python 3.13, FastAPI
- **Database**: Neo4j 5.15+ with APOC
- **AI**: LlamaIndex, Multiple LLM providers
- **Protocol**: Model Context Protocol (MCP)
- **Deployment**: Docker, Docker Compose

## 🤝 Community

- **GitHub**: [royisme/codebase-rag](https://github.com/royisme/codebase-rag)
- **Docker Hub**: [royisme/codebase-rag](https://hub.docker.com/r/royisme/codebase-rag)
- **Issues**: [Report bugs](https://github.com/royisme/codebase-rag/issues)
- **Discussions**: [Community forum](https://github.com/royisme/codebase-rag/discussions)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/royisme/codebase-rag/blob/main/LICENSE) file for details.

---

<div align="center">

**Ready to get started?** → [Quick Start Guide](getting-started/quickstart.md)

</div>
