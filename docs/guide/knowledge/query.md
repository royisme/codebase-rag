# Intelligent Query Guide

Master the art of querying your knowledge base using RAG (Retrieval-Augmented Generation) for intelligent, context-aware answers.

## Overview

The Knowledge RAG query system combines three powerful techniques:

1. **Vector Search**: Find semantically similar content using embeddings
2. **Graph Traversal**: Navigate relationships between documents
3. **LLM Generation**: Synthesize intelligent answers from retrieved context

## Query Modes

### 1. Hybrid Mode (Recommended)

Combines vector search and graph traversal for best results.

**When to use**:
- General-purpose queries
- Complex questions requiring multiple sources
- When you want comprehensive answers
- Default choice for most use cases

**Example**:
```json
{
  "tool": "query_knowledge",
  "input": {
    "question": "How does JWT authentication work in the system?",
    "mode": "hybrid"
  }
}
```

**Response**:
```json
{
  "success": true,
  "answer": "JWT authentication in the system works by...",
  "sources": [
    {
      "node_id": "node_123",
      "content": "The JWT middleware validates tokens...",
      "score": 0.92,
      "metadata": {"file": "auth.py", "type": "code"}
    },
    {
      "node_id": "node_456",
      "content": "JWT tokens contain user claims...",
      "score": 0.87,
      "metadata": {"file": "jwt_docs.md", "type": "docs"}
    }
  ],
  "mode": "hybrid",
  "retrieval_time_ms": 150,
  "generation_time_ms": 2300
}
```

### 2. Vector-Only Mode

Pure similarity search using embeddings.

**When to use**:
- Finding similar documents
- Semantic search without context
- Fast lookups
- When graph relationships aren't important

**Example**:
```json
{
  "tool": "query_knowledge",
  "input": {
    "question": "authentication security",
    "mode": "vector_only"
  }
}
```

**Characteristics**:
- ✅ Fast (50-200ms)
- ✅ Good for keyword-like queries
- ✅ Scales well with large datasets
- ❌ Misses relationship context
- ❌ May return disconnected results

### 3. Graph-Only Mode

Uses only graph relationships and structure.

**When to use**:
- Exploring document relationships
- Finding connected concepts
- When semantic similarity isn't needed
- Structured knowledge navigation

**Example**:
```json
{
  "tool": "query_knowledge",
  "input": {
    "question": "Show all API documentation",
    "mode": "graph_only"
  }
}
```

**Characteristics**:
- ✅ Preserves document structure
- ✅ Good for hierarchical queries
- ✅ Finds related documents
- ❌ Requires well-structured graph
- ❌ May miss semantically similar content

## Query Techniques

### 1. Simple Questions

Direct, straightforward questions:

```json
{
  "question": "What is the purpose of the Memory Store?"
}

{
  "question": "How do I configure Neo4j?"
}

{
  "question": "What are the system requirements?"
}
```

### 2. Comparative Questions

Compare different concepts or approaches:

```json
{
  "question": "What's the difference between Ollama and OpenAI?"
}

{
  "question": "Compare vector_only and hybrid query modes"
}

{
  "question": "Should I use local or cloud LLM for my use case?"
}
```

### 3. How-To Questions

Step-by-step instructions:

```json
{
  "question": "How do I deploy the system with Docker?"
}

{
  "question": "How to add documents to the knowledge base?"
}

{
  "question": "How to configure MCP in Claude Desktop?"
}
```

### 4. Conceptual Questions

Understanding concepts:

```json
{
  "question": "Explain how RAG works in this system"
}

{
  "question": "What is the architecture of the Code Graph?"
}

{
  "question": "Describe the document processing pipeline"
}
```

### 5. Code-Related Questions

When your knowledge base includes code:

```json
{
  "question": "Show me how to use the memory_store API"
}

{
  "question": "What parameters does add_document accept?"
}

{
  "question": "Find examples of async function implementation"
}
```

## Advanced Query Features

### Top-K Results

Control the number of source documents retrieved:

```json
{
  "tool": "query_knowledge",
  "input": {
    "question": "What are deployment options?",
    "top_k": 10  // Retrieve top 10 most relevant chunks
  }
}
```

**Guidelines**:
- `top_k=3-5`: Focused, specific answers
- `top_k=10`: Comprehensive, detailed answers
- `top_k=20+`: Exhaustive, may include noise

**Default**: `TOP_K=5` (from `.env` configuration)

### Similarity Search

Find similar documents without LLM generation:

```json
{
  "tool": "search_similar_nodes",
  "input": {
    "query": "authentication implementation",
    "top_k": 5
  }
}
```

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "node_id": "node_789",
      "content": "JWT authentication middleware...",
      "score": 0.94,
      "metadata": {"file": "auth.py"}
    },
    {
      "node_id": "node_790",
      "content": "OAuth2 implementation...",
      "score": 0.89,
      "metadata": {"file": "oauth.py"}
    }
  ],
  "total_results": 5,
  "search_time_ms": 85
}
```

**Use cases**:
- Finding related documents
- Building custom result displays
- Quick content discovery
- Bypassing LLM for speed

## Query Optimization

### 1. Formulate Clear Questions

**Good questions**:
```
✅ "How do I configure Ollama for local LLM?"
✅ "What are the differences between lite and full mode?"
✅ "Show me code examples for adding memories"
```

**Poor questions**:
```
❌ "ollama?"  (Too vague)
❌ "Tell me everything"  (Too broad)
❌ "thing about the stuff"  (Unclear)
```

### 2. Use Specific Terms

Include technical terms and keywords:

```json
// Good: Specific technical terms
{
  "question": "How does Neo4j vector index improve search performance?"
}

// Less effective: Generic terms
{
  "question": "How does the database make things faster?"
}
```

### 3. Provide Context

Add context for ambiguous terms:

```json
// Good: Contextual
{
  "question": "How do I configure JWT authentication in the FastAPI application?"
}

// Ambiguous: Lacks context
{
  "question": "How do I configure authentication?"
}
```

### 4. Break Down Complex Queries

Split complex questions:

```json
// Instead of:
{
  "question": "How do I set up the system with Docker using Ollama with GPU support and configure Neo4j for production?"
}

// Do this:
// Query 1:
{
  "question": "How do I set up the system with Docker?"
}

// Query 2:
{
  "question": "How do I configure Ollama with GPU support?"
}

// Query 3:
{
  "question": "How do I configure Neo4j for production?"
}
```

## Understanding Query Results

### Result Structure

```json
{
  "success": true,
  "answer": "Generated answer text...",
  "sources": [
    {
      "node_id": "unique_node_id",
      "content": "Source content snippet...",
      "score": 0.92,  // Similarity score (0-1)
      "metadata": {
        "title": "Document Title",
        "file": "path/to/file",
        "chunk_index": 0,
        "type": "documentation"
      }
    }
  ],
  "mode": "hybrid",
  "retrieval_time_ms": 150,
  "generation_time_ms": 2300,
  "total_time_ms": 2450
}
```

### Interpreting Scores

Similarity scores indicate relevance:

- **0.90 - 1.00**: Highly relevant, exact match
- **0.80 - 0.89**: Very relevant, strong semantic match
- **0.70 - 0.79**: Relevant, good match
- **0.60 - 0.69**: Somewhat relevant, partial match
- **0.50 - 0.59**: Weakly relevant, tangential
- **< 0.50**: Likely not relevant

### Source Attribution

Each answer includes source nodes for verification:

```python
# Example: Verify answer sources
result = query_knowledge("How does RAG work?")

print(f"Answer: {result['answer']}\n")
print("Sources:")
for source in result['sources']:
    print(f"  - {source['metadata']['title']} (score: {source['score']:.2f})")
    print(f"    {source['content'][:100]}...")
```

## HTTP API Usage

### Basic Query

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the deployment architecture?",
    "mode": "hybrid",
    "top_k": 5
  }'
```

### Similarity Search

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "docker configuration",
    "top_k": 10
  }'
```

### Python Client

```python
import httpx
import asyncio

async def query_knowledge(question: str, mode: str = "hybrid"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/knowledge/query",
            json={
                "question": question,
                "mode": mode,
                "top_k": 5
            },
            timeout=30.0
        )
        return response.json()

# Usage
result = asyncio.run(query_knowledge(
    "How do I configure the system?"
))
print(result['answer'])
```

## Query Performance

### Performance Characteristics

| Operation | Speed | Quality | Use Case |
|-----------|-------|---------|----------|
| Vector search | 50-200ms | Good | Fast lookups |
| Hybrid mode | 100-500ms | Excellent | General queries |
| Graph-only | 100-300ms | Good | Structured data |
| LLM generation | 1-5s | Excellent | Answer synthesis |

### Performance Tips

1. **Use vector-only for speed**:
   ```json
   {"question": "quick lookup", "mode": "vector_only"}
   ```

2. **Cache frequent queries** (implement client-side):
   ```python
   query_cache = {}

   def cached_query(question):
       if question in query_cache:
           return query_cache[question]
       result = query_knowledge(question)
       query_cache[question] = result
       return result
   ```

3. **Adjust top_k based on needs**:
   ```python
   # Fast: fewer sources
   query_knowledge(q, top_k=3)

   # Comprehensive: more sources
   query_knowledge(q, top_k=10)
   ```

4. **Use similarity search for bulk operations**:
   ```python
   # Faster than multiple query_knowledge calls
   results = search_similar_nodes(query, top_k=20)
   ```

## Common Query Patterns

### 1. Documentation Lookup

Finding specific documentation:

```json
{
  "question": "Show me the API documentation for the memory store"
}
```

### 2. Configuration Help

Getting configuration guidance:

```json
{
  "question": "What are the required environment variables for Full mode?"
}
```

### 3. Code Examples

Finding code snippets:

```json
{
  "question": "Show me examples of using the add_document function"
}
```

### 4. Troubleshooting

Getting help with issues:

```json
{
  "question": "Why is my Ollama connection failing?"
}
```

### 5. Comparison

Comparing options:

```json
{
  "question": "Compare the performance of different embedding providers"
}
```

## Integration with Other Tools

### Memory Store Integration

Query knowledge base and save important findings:

```python
# Query for information
result = query_knowledge("How does authentication work?")

# Save as memory
add_memory(
    project_id="myapp",
    memory_type="note",
    title="Authentication Overview",
    content=result['answer'],
    importance=0.7,
    tags=["authentication", "security"]
)
```

### Code Graph Integration

Combine code analysis with documentation:

```python
# Find code implementations
code_results = code_graph_search("authentication")

# Find related documentation
doc_results = query_knowledge("authentication implementation guide")

# Correlate results
combined_context = {
    "code": code_results,
    "docs": doc_results
}
```

## Error Handling

### Common Errors

**1. No results found**:
```json
{
  "success": true,
  "answer": "I couldn't find relevant information about...",
  "sources": [],
  "note": "Try rephrasing your question or adding more context"
}
```

**2. LLM timeout**:
```json
{
  "success": false,
  "error": "LLM generation timeout",
  "retrieval_successful": true,
  "sources": [...]  // Sources still available
}
```

**3. Empty knowledge base**:
```json
{
  "success": false,
  "error": "Knowledge base is empty. Add documents first."
}
```

### Error Handling Code

```python
try:
    result = query_knowledge(question)

    if not result['success']:
        print(f"Query failed: {result['error']}")
        return

    if not result['sources']:
        print("No relevant information found. Try different keywords.")
        return

    print(result['answer'])

except httpx.TimeoutException:
    print("Query timeout. Try a simpler question or check system load.")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

### 1. Start Broad, Then Narrow

```python
# First query: broad
result1 = query_knowledge("deployment options")

# Follow-up: specific
result2 = query_knowledge("how to deploy with Docker Compose")
```

### 2. Verify Sources

Always check source documents:

```python
result = query_knowledge(question)

# Review sources
print(f"Answer based on {len(result['sources'])} sources:")
for src in result['sources']:
    print(f"  - {src['metadata']['title']} (score: {src['score']})")
```

### 3. Use Right Mode for Task

```python
# Exploration: hybrid
query_knowledge(q, mode="hybrid")

# Quick lookup: vector
query_knowledge(q, mode="vector_only")

# Structured navigation: graph
query_knowledge(q, mode="graph_only")
```

### 4. Monitor Performance

```python
result = query_knowledge(question)

print(f"Retrieval: {result['retrieval_time_ms']}ms")
print(f"Generation: {result['generation_time_ms']}ms")
print(f"Total: {result['total_time_ms']}ms")

# Adjust if too slow
if result['total_time_ms'] > 5000:
    # Consider vector_only or reduce top_k
    pass
```

## Advanced Techniques

### 1. Multi-Query Strategy

Ask related questions for comprehensive understanding:

```python
questions = [
    "What is the system architecture?",
    "What are the core components?",
    "How do components interact?"
]

results = [query_knowledge(q) for q in questions]
```

### 2. Result Aggregation

Combine results from multiple queries:

```python
def comprehensive_search(topic):
    results = []

    # Different query angles
    queries = [
        f"What is {topic}?",
        f"How to use {topic}?",
        f"{topic} examples and best practices"
    ]

    for q in queries:
        result = query_knowledge(q)
        results.append(result)

    return aggregate_results(results)
```

### 3. Context Building

Build context from related queries:

```python
# Initial query
base_result = query_knowledge("JWT authentication")

# Extract key terms from answer
key_terms = extract_key_terms(base_result['answer'])

# Query for each key term
context = {}
for term in key_terms:
    context[term] = search_similar_nodes(term, top_k=3)
```

### 4. Feedback Loop

Use query results to refine questions:

```python
def iterative_query(initial_question, max_iterations=3):
    question = initial_question

    for i in range(max_iterations):
        result = query_knowledge(question)

        if result['success'] and result['sources']:
            return result

        # Refine question based on failure
        question = refine_question(question, result)

    return result
```

## Troubleshooting

### Poor Quality Answers

**Symptoms**:
- Irrelevant answers
- Incomplete information
- Contradictory results

**Solutions**:
1. Add more documents to knowledge base
2. Improve document metadata
3. Adjust chunk size/overlap
4. Try different embedding model
5. Rephrase question

### Slow Query Performance

**Symptoms**:
- Queries taking >5 seconds
- Timeouts

**Solutions**:
1. Reduce `top_k` value
2. Use `vector_only` mode
3. Check Neo4j performance
4. Verify LLM provider responsiveness
5. Enable query caching

### No Results Found

**Symptoms**:
- Empty sources list
- Generic "no information" answers

**Solutions**:
1. Verify documents are indexed
2. Check embeddings were generated
3. Try broader query terms
4. Use different query mode
5. Inspect Neo4j vector index

## Next Steps

- **[MCP Integration](../mcp/overview.md)**: Connect to AI assistants
- **[Claude Desktop Setup](../mcp/claude-desktop.md)**: Use queries in Claude
- **[VS Code Integration](../mcp/vscode.md)**: Query from your editor

## Additional Resources

- **LlamaIndex Query Engine**: https://docs.llamaindex.ai/en/stable/module_guides/deploying/query_engine/
- **RAG Techniques**: https://docs.llamaindex.ai/en/stable/optimizing/production_rag/
- **Neo4j Vector Search**: https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/
