# Knowledge RAG Overview

Knowledge RAG (Retrieval-Augmented Generation) is the document processing and intelligent Q&A system of Code Graph Knowledge System. It combines vector search, graph databases, and LLM integration to provide context-aware answers to questions about your documents.

## What is Knowledge RAG?

Knowledge RAG transforms your documents into an intelligent knowledge base that can:

- **Understand Context**: Process documents and extract semantic meaning
- **Find Relevant Information**: Use vector similarity to find related content
- **Generate Intelligent Answers**: Use LLMs to synthesize information from multiple sources
- **Maintain Relationships**: Store knowledge as a graph with rich connections

## Architecture

```
Documents → Chunking → Embeddings → Neo4j Graph + Vector Index
                                              ↓
Query → Vector Search + Graph Traversal → LLM → Intelligent Answer
```

### Key Components

1. **Document Processing**
   - Chunking: Break documents into semantic chunks (configurable size)
   - Embedding: Convert text to vector representations
   - Graph Storage: Store chunks as nodes with relationships

2. **Query Engine**
   - Vector Search: Find similar content using embeddings
   - Graph Traversal: Navigate relationships between nodes
   - LLM Generation: Synthesize answers from retrieved context

3. **Multi-Provider Support**
   - **LLM Providers**: Ollama, OpenAI, Google Gemini, OpenRouter
   - **Embedding Providers**: Ollama, OpenAI, Google Gemini, HuggingFace

## Feature Set

### Document Processing
- ✅ Text files (.txt, .md, .rst)
- ✅ Code files (all major languages)
- ✅ PDF documents
- ✅ Web pages (HTML)
- ✅ Batch directory processing
- ✅ Recursive subdirectory scanning

### Query Modes
- **Hybrid** (Default): Combines vector search + graph traversal for best results
- **Vector Only**: Pure similarity search using embeddings
- **Graph Only**: Uses only graph relationships

### Intelligent Features
- **Semantic Search**: Find documents by meaning, not just keywords
- **Context-Aware Answers**: LLM generates answers using relevant sources
- **Source Attribution**: Every answer includes source nodes
- **Relationship Discovery**: Find connections between documents

## Deployment Modes

Knowledge RAG is available **only in Full mode** because it requires both LLM and embedding models.

### Full Mode Requirements
- ✅ Neo4j database with vector index support
- ✅ LLM provider (for answer generation)
- ✅ Embedding provider (for vector search)

### Not Available In:
- ❌ Lite mode (no LLM/embeddings)
- ❌ Graph-only mode (no RAG features)

## Quick Start Example

### 1. Add Documents
```python
# Via MCP Tool
{
  "tool": "add_document",
  "input": {
    "content": "Machine learning is a subset of artificial intelligence...",
    "title": "ML Introduction",
    "metadata": {"type": "tutorial", "difficulty": "beginner"}
  }
}
```

### 2. Query Knowledge Base
```python
# Via MCP Tool
{
  "tool": "query_knowledge",
  "input": {
    "question": "What is machine learning?",
    "mode": "hybrid"
  }
}

# Response:
{
  "answer": "Machine learning is a subset of artificial intelligence that...",
  "sources": [
    {"title": "ML Introduction", "content": "...", "score": 0.92}
  ]
}
```

### 3. Search Similar Content
```python
# Via MCP Tool
{
  "tool": "search_similar_nodes",
  "input": {
    "query": "neural networks",
    "top_k": 5
  }
}
```

## Use Cases

### 1. Documentation Search
Build searchable knowledge bases from your documentation:
- Technical documentation
- API references
- User manuals
- Internal wikis

### 2. Codebase Understanding
Index your codebase for intelligent code search:
- Find implementations by description
- Understand code context
- Discover related components
- Navigate large codebases

### 3. Research Assistant
Create research knowledge bases:
- Academic papers
- Research notes
- Literature reviews
- Citation discovery

### 4. Customer Support
Build intelligent support systems:
- Product documentation
- FAQ databases
- Troubleshooting guides
- Knowledge articles

### 5. Learning Platform
Create interactive learning experiences:
- Course materials
- Tutorial content
- Educational resources
- Study guides

## Configuration

Knowledge RAG is configured via environment variables. Key settings:

```bash
# Required for Knowledge RAG
DEPLOYMENT_MODE=full
ENABLE_KNOWLEDGE_RAG=true

# LLM Configuration
LLM_PROVIDER=ollama              # ollama/openai/gemini/openrouter
OLLAMA_MODEL=llama3.2            # or gpt-4, gemini-pro, etc.

# Embedding Configuration
EMBEDDING_PROVIDER=ollama         # ollama/openai/gemini/huggingface
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Processing Settings
CHUNK_SIZE=512                    # Tokens per chunk
CHUNK_OVERLAP=50                  # Overlap between chunks
TOP_K=5                          # Number of results to retrieve

# Timeout Settings
OPERATION_TIMEOUT=120             # Standard operations (seconds)
LARGE_DOCUMENT_TIMEOUT=300        # Large document processing (seconds)
```

## System Requirements

### With Local LLM (Ollama)
- **CPU**: 8+ cores recommended
- **RAM**: 16GB minimum (32GB for large models)
- **GPU**: Optional but highly recommended (8GB+ VRAM)
- **Storage**: 50GB+ for models and data

### With Cloud LLM (OpenAI/Gemini)
- **CPU**: 4+ cores
- **RAM**: 8GB minimum
- **Storage**: 20GB+ for data
- **Network**: Stable internet connection

## Performance Characteristics

### Processing Speed
- **Small documents** (<10KB): Synchronous, <1s
- **Medium documents** (10-50KB): Async queue, 1-10s
- **Large documents** (>50KB): Async queue, 10-60s
- **Directories**: Async queue, varies by size

### Query Performance
- **Vector search**: 50-200ms
- **Hybrid mode**: 100-500ms
- **LLM generation**: 1-5s (local), 0.5-2s (cloud)

### Scaling Considerations
- **Document size**: Up to 10MB per document recommended
- **Total documents**: Scales to millions with proper Neo4j tuning
- **Concurrent queries**: 10-50 depending on hardware
- **Embedding cache**: Speeds up repeated queries

## Integration Points

Knowledge RAG integrates with other system components:

### 1. Task Queue System
- Async processing for large documents
- Background directory ingestion
- Progress tracking
- Error handling and retries

### 2. MCP Tools
- 5 knowledge tools available via MCP
- Integration with Claude Desktop, VS Code
- Real-time query capabilities

### 3. Memory Store
- Suggest memories from Q&A sessions
- Auto-extract knowledge from queries
- Cross-reference with project memories

### 4. Code Graph
- Complement code-specific analysis
- Provide documentation context
- Enhance code understanding

## Limitations and Considerations

### Current Limitations
1. **Text-based only**: Images and binary files not supported
2. **Token limits**: Large documents must fit in LLM context window
3. **Language**: Best results with English (depends on embedding model)
4. **Real-time**: Not suitable for rapidly changing documents

### Best Practices
1. **Document size**: Keep documents focused and well-structured
2. **Chunking**: Adjust chunk size for your content type
3. **Metadata**: Add rich metadata for better filtering
4. **Updates**: Re-process documents when content changes
5. **Query formulation**: Ask specific, well-formed questions

## Security and Privacy

### Data Storage
- Documents stored in Neo4j database
- Embeddings stored as node properties
- No external data transmission (with local LLM)

### Privacy Options
- **Full privacy**: Use Ollama for local processing
- **Cloud processing**: OpenAI/Gemini send data to cloud
- **Hybrid**: Local embeddings + cloud LLM

### Access Control
- No built-in authentication (add via reverse proxy)
- Neo4j database access control
- MCP tool isolation per user

## Cost Considerations

### Local Deployment (Ollama)
- **Hardware**: $0-2000 one-time (GPU recommended)
- **Hosting**: $40-200/month (VPS/cloud)
- **LLM**: $0 (free)
- **Embeddings**: $0 (free)
- **Total ongoing**: $40-200/month

### Cloud Deployment (OpenAI)
- **Hosting**: $10-20/month (small VPS)
- **LLM**: $0.01-0.10 per query (GPT-4o-mini)
- **Embeddings**: $0.0001 per 1K tokens
- **Total**: $50-500/month (usage-dependent)

### Hybrid Deployment
- **Hosting**: $10-20/month
- **LLM**: $0.01-0.10 per query
- **Embeddings**: $0 (local Ollama)
- **Total**: $30-300/month

## Next Steps

- **[Document Processing Guide](documents.md)**: Learn how to add and manage documents
- **[Query Guide](query.md)**: Master intelligent querying techniques
- **[MCP Integration](../mcp/overview.md)**: Connect to AI assistants
- **[Full Mode Deployment](../../deployment/full.md)**: Deploy with all features

## Additional Resources

- **Examples**: See `examples/` directory for code samples
- **API Reference**: HTTP REST API documentation
- **MCP Tools**: Tool definitions and schemas
- **Configuration**: Complete `.env` settings guide
