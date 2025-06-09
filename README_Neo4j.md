# Neo4j GraphRAG Technical Documentation

Advanced technical documentation for the Neo4j-based GraphRAG implementation in the Code Graph Knowledge System.

## Architecture Overview

### Unified Storage Architecture
- **Single Database**: Uses Neo4j 5.x built-in vector index, eliminating the need for additional vector databases
- **Data Consistency**: Text, graph structure, and vectors stored in the same database
- **Simplified Operations**: Only requires maintaining a single Neo4j instance

### Modern Technology Stack
- **LlamaIndex**: Official GraphRAG framework recommended by LlamaIndex
- **Neo4j**: World-leading graph database with built-in vector search
- **Ollama**: Local LLM and embedding model services
- **FastAPI**: High-performance async web framework

### Powerful Query Capabilities
- **Hybrid Search**: Simultaneous graph traversal and vector similarity search
- **Multi-mode Queries**: Support for pure graph, pure vector, and hybrid queries
- **Intelligent Retrieval**: Automatic selection of optimal retrieval strategies

## System Requirements

### Required Services
- **Neo4j 5.x**: Version with vector index support
- **Ollama**: Local LLM service
- **Python 3.13+**: Runtime environment

### Recommended Configuration
```bash
# Neo4j
Neo4j 5.15+ (Community or Enterprise)
Memory: 4GB+
Storage: SSD recommended

# Ollama Models
LLM: llama3.2, mistral, qwen
Embedding: nomic-embed-text, all-minilm
```

## Installation and Configuration

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Neo4j
```bash
# Using Docker
docker run \
    --name neo4j-code-graph \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -v $HOME/neo4j/data:/data \
    -v $HOME/neo4j/logs:/logs \
    -v $HOME/neo4j/import:/var/lib/neo4j/import \
    -v $HOME/neo4j/plugins:/plugins \
    --env NEO4J_AUTH=neo4j/password \
    neo4j:5.15
```

### 3. Start Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download models
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 4. Configure Environment Variables
```bash
# .env file
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## Query Modes

### Hybrid Mode (hybrid)
```json
{
  "question": "What are the characteristics of Python?",
  "mode": "hybrid"
}
```
Uses both graph traversal and vector search for comprehensive answers.

### Vector-Only Mode (vector_only)
```json
{
  "question": "Programming language features",
  "mode": "vector_only"
}
```
Based on semantic similarity search, suitable for conceptual queries.

### Graph-Only Mode (graph_only)
```json
{
  "question": "Python's relationship with other languages",
  "mode": "graph_only"
}
```
Based on graph structure traversal, suitable for relationship queries.

## Performance Optimization

### Neo4j Optimization
```cypher
-- Create vector index
CREATE VECTOR INDEX knowledge_vectors 
FOR (n:Document) ON (n.embedding) 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine'
}}

-- Create text index
CREATE FULLTEXT INDEX document_text 
FOR (n:Document) ON EACH [n.text, n.title]
```

### Query Optimization
- Use appropriate `top_k` values
- Set reasonable `chunk_size`
- Enable query caching
- Monitor query performance

## Configuration Options

### Neo4j Configuration
```python
# Vector index configuration
vector_index_name = "knowledge_vectors"
vector_dimension = 768  # Adjust based on embedding model
```

### LlamaIndex Configuration
```python
# Document processing
chunk_size = 1000
chunk_overlap = 200

# Query configuration
similarity_top_k = 10
response_mode = "tree_summarize"
```

### Ollama Configuration
```python
# LLM model
ollama_model = "llama3.2"
temperature = 0.1

# Embedding model
embedding_model = "nomic-embed-text"
```

## Troubleshooting

### Common Issues

#### Neo4j Connection Failed
```bash
# Check Neo4j status
docker logs neo4j-code-graph

# Verify connection
curl http://localhost:7474
```

#### Ollama Model Not Found
```bash
# List installed models
ollama list

# Download missing model
ollama pull nomic-embed-text
```

#### Vector Index Error
```cypher
// Check index status
SHOW INDEXES

// Rebuild index
DROP INDEX knowledge_vectors IF EXISTS;
CREATE VECTOR INDEX knowledge_vectors ...
```

## Development Guide

### Adding New Document Types
```python
# Extend document processor
class CustomDocumentProcessor:
    def process(self, content: str) -> Document:
        # Custom processing logic
        return Document(text=content, metadata={...})
```

### Custom Query Strategies
```python
# Implement custom retriever
class CustomRetriever:
    def retrieve(self, query: str) -> List[Node]:
        # Custom retrieval logic
        return nodes
```

## Architecture Diagram

```
Documents → LlamaIndex → Neo4j (Vector + Graph)
Query → Single Cypher Query → Unified Results
```

## Core Features

### Intelligent Document Processing
- Automatic document chunking
- Entity relationship extraction
- Vector embedding generation
- Graph structure construction

### Efficient Query Engine
- Hybrid retrieval strategies
- Context-aware responses
- Multi-hop graph traversal
- Semantic similarity matching

### Flexible Extensibility
- Support for multiple document formats
- Configurable embedding models
- Custom query strategies
- Plugin architecture

## Testing and Validation

### Run Tests
```bash
python test_neo4j_knowledge.py
```

### Test Coverage
- Service initialization
- Document addition and indexing
- Multi-mode queries
- Vector similarity search
- Graph structure queries
- File upload processing

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [Neo4j](https://neo4j.com/) - Graph database technology
- [LlamaIndex](https://www.llamaindex.ai/) - RAG framework
- [Ollama](https://ollama.ai/) - Local LLM service

---

**Modern GraphRAG, starting from Neo4j!** 🚀 