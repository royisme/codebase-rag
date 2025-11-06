# Search and Discovery Guide

## Introduction

Code Graph provides powerful fulltext search capabilities powered by Neo4j's native search engine. Unlike simple grep or text matching, Code Graph search understands code structure, ranks results by relevance, and works at graph database speed.

This guide covers everything from basic searches to advanced ranking techniques.

## Search Architecture

### How Search Works

When you search Code Graph:

1. **Query parsing**: Your search terms are analyzed and prepared
2. **Fulltext index lookup**: Neo4j's native fulltext index is queried
3. **Result scoring**: Files are ranked by relevance score
4. **Re-ranking**: Additional ranking factors are applied
5. **Result formatting**: Files are enriched with metadata and ref:// handles

### Fulltext vs Vector Search

Code Graph uses **fulltext search**, not vector embeddings:

| Feature | Fulltext Search | Vector Search |
|---------|----------------|---------------|
| **Setup** | No LLM/embeddings | Requires embeddings |
| **Speed** | < 100ms | 200-500ms |
| **Accuracy** | Keyword-based | Semantic |
| **Resources** | Minimal | High |
| **Queries** | Keywords | Natural language |
| **Deployment** | All modes | Full mode only |

**When to use fulltext search:**
- You know specific terms (function names, file paths)
- Need instant results
- Working in minimal/standard mode
- Want minimal resource usage

**When to use vector search:**
- Need semantic understanding
- Natural language queries
- Working in full mode
- Have embedding model available

## Using MCP Tools

### Tool: code_graph_related

Find files related to a search query with intelligent ranking.

#### Input Schema

```json
{
  "query": "authentication service",
  "repo_id": "myapp",
  "limit": 30
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `repo_id` | string | Yes | - | Repository identifier |
| `limit` | integer | No | 30 | Maximum results (1-100) |

#### Example: Basic Search

```json
{
  "query": "user authentication",
  "repo_id": "myapp",
  "limit": 10
}
```

**Response:**

```json
{
  "success": true,
  "nodes": [
    {
      "type": "file",
      "path": "src/auth/user_auth.py",
      "lang": "python",
      "size": 4523,
      "score": 2.85,
      "summary": "Python file user_auth.py in auth/ directory",
      "ref": "ref://file/src/auth/user_auth.py#L1-L1000"
    },
    {
      "type": "file",
      "path": "src/services/authentication.ts",
      "lang": "typescript",
      "size": 6102,
      "score": 2.41,
      "summary": "TypeScript file authentication.ts in services/ directory",
      "ref": "ref://file/src/services/authentication.ts#L1-L1000"
    }
  ],
  "total_count": 2
}
```

#### Example: Language-Specific Search

```json
{
  "query": "database python",
  "repo_id": "myapp",
  "limit": 20
}
```

This will find Python files related to database functionality.

#### Example: Path-Based Search

```json
{
  "query": "api routes payment",
  "repo_id": "myapp",
  "limit": 15
}
```

This searches for files in API routes related to payments.

#### Example: Claude Desktop Usage

In Claude Desktop, simply ask:

```
Find files related to user authentication in myapp
```

Claude will call the MCP tool:

```json
{
  "name": "code_graph_related",
  "arguments": {
    "query": "user authentication",
    "repo_id": "myapp",
    "limit": 30
  }
}
```

### Understanding Response Fields

#### Node Structure

Each result node contains:

```json
{
  "type": "file",                    // Node type (always "file" currently)
  "path": "src/auth/service.py",    // Relative file path
  "lang": "python",                  // Programming language
  "size": 4523,                      // File size in bytes
  "score": 2.85,                     // Relevance score (higher = more relevant)
  "summary": "Python file ...",      // Human-readable summary
  "ref": "ref://file/...",           // Reference handle for AI tools
  "repoId": "myapp"                  // Repository identifier
}
```

#### Score Interpretation

**Score ranges:**

- **3.0+**: Exact match in path, highly relevant
- **2.0-3.0**: Strong match, multiple keywords matched
- **1.0-2.0**: Good match, partial keyword matching
- **0.5-1.0**: Weak match, single keyword or language match
- **< 0.5**: Very weak match, consider refining query

**Score factors:**

1. **Fulltext score** (base): Neo4j relevance score
2. **Exact path match** (×2.0): Query appears in path
3. **Term matching** (×1.0-1.9): Multiple terms matched
4. **Language match** (×1.5): Query matches file language
5. **Directory boost** (×1.2): File in src/, lib/, core/, app/
6. **Test penalty** (×0.5): Test files (unless searching for tests)

#### Reference Handles

The `ref` field provides a standardized way to reference files:

```
ref://file/{path}#L{start}-L{end}
```

**Example:**
```
ref://file/src/auth/service.py#L1-L1000
```

**Usage:**
- AI tools can fetch file content
- MCP clients can load specific line ranges
- Context packing uses refs for deduplication
- Future versions will support symbol refs

## Using REST API

### Endpoint: POST /api/v1/code-graph/search

#### Request Body

```json
{
  "query": "authentication",
  "repo_id": "myapp",
  "limit": 30
}
```

#### Response

```json
{
  "success": true,
  "results": [
    {
      "path": "src/auth/service.py",
      "lang": "python",
      "size": 4523,
      "score": 2.85,
      "ref": "ref://file/src/auth/service.py#L1-L1000"
    }
  ],
  "query": "authentication",
  "repo_id": "myapp",
  "total_count": 15,
  "limit": 30
}
```

#### Example: cURL

```bash
curl -X POST http://localhost:8000/api/v1/code-graph/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication service",
    "repo_id": "myapp",
    "limit": 10
  }'
```

#### Example: Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/code-graph/search",
    json={
        "query": "database connection",
        "repo_id": "myapp",
        "limit": 20
    }
)

results = response.json()
for file in results["results"]:
    print(f"{file['score']:.2f}: {file['path']}")
```

#### Example: JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/code-graph/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'api routes',
    repo_id: 'myapp',
    limit: 15
  })
});

const data = await response.json();
data.results.forEach(file => {
  console.log(`${file.score.toFixed(2)}: ${file.path}`);
});
```

## Search Strategies

### 1. Keyword Search

Search for specific terms in file paths and content.

**Example queries:**
```
"authentication"
"database connection"
"user service"
"payment processing"
```

**Best practices:**
- Use specific terms (not generic words like "code" or "file")
- Include 1-3 keywords per query
- Use domain terminology
- Avoid stop words (the, a, is, etc.)

**When to use:**
- Looking for specific functionality
- Know what you're searching for
- Need precise results

### 2. Multi-term Search

Combine multiple keywords to narrow results.

**Example queries:**
```
"auth service typescript"     # Auth service in TypeScript
"payment api routes"          # Payment API route files
"database models python"      # Database models in Python
"user profile component"      # User profile UI components
```

**Best practices:**
- Start broad, add terms to narrow
- Include language for language-specific search
- Use directory names for path filtering
- Combine feature + component type

**When to use:**
- Initial search too broad
- Need language/path filtering
- Looking for specific combinations

### 3. Path-Based Search

Search for files in specific directories or matching path patterns.

**Example queries:**
```
"src/auth"                    # Files in auth directory
"api/routes payment"          # Payment routes in API
"services/user"               # User service files
"components/profile"          # Profile components
```

**Best practices:**
- Use directory names from your project
- Include path segments for precision
- Combine with feature keywords
- Use consistent naming conventions

**When to use:**
- Know the directory structure
- Searching within specific module
- Finding related files in same area

### 4. Language-Specific Search

Filter results by programming language.

**Example queries:**
```
"database python"             # Python database files
"api typescript"              # TypeScript API files
"utils javascript"            # JavaScript utility files
"models go"                   # Go model files
```

**Best practices:**
- Add language as last term
- Use full language name (not extensions)
- Combine with feature keywords
- Useful for polyglot projects

**When to use:**
- Multi-language projects
- Looking for language-specific implementation
- Comparing implementations across languages

### 5. Component Search

Search for specific types of components.

**Example queries:**
```
"service"                     # Service layer files
"controller"                  # Controller files
"model"                       # Data models
"repository"                  # Repository pattern files
"middleware"                  # Middleware files
"utils" or "helpers"          # Utility files
```

**Best practices:**
- Use architectural terminology
- Combine with domain keywords
- Match your project's naming conventions
- Include common suffixes

**When to use:**
- Following architectural patterns
- Finding similar components
- Understanding layer structure

## Advanced Techniques

### Query Refinement

Start broad, then narrow results iteratively.

**Example workflow:**

1. **Initial query**: `"payment"`
   - Results: 47 files (too many)

2. **Add context**: `"payment service"`
   - Results: 12 files (better)

3. **Add language**: `"payment service typescript"`
   - Results: 4 files (perfect)

4. **Add path**: `"api/services payment typescript"`
   - Results: 2 files (exact match)

### Fuzzy Matching

Neo4j fulltext search automatically handles:

- **Typos**: "autentication" → "authentication"
- **Partial words**: "auth" → "authentication"
- **Case insensitivity**: "USER" → "user"
- **Stemming**: "payments" → "payment"

**No special syntax required** - just type naturally.

### Boolean Logic

Combine terms with implicit AND logic:

```
"user auth service"
```

This finds files matching ALL terms (user AND auth AND service).

**Note:** OR and NOT operators are not currently supported. Use multiple queries instead.

### Wildcards

Not explicitly supported, but partial matching works naturally:

```
"auth"  →  matches "authentication", "authorize", "auth_service"
```

### Result Filtering

After getting results, filter programmatically:

```python
results = search(query="service", repo_id="myapp", limit=100)

# Filter by language
python_files = [r for r in results if r["lang"] == "python"]

# Filter by path
api_files = [r for r in results if "api/" in r["path"]]

# Filter by score
high_score = [r for r in results if r["score"] > 2.0]

# Filter by size
small_files = [r for r in results if r["size"] < 10000]
```

## Search Examples

### Example 1: Finding Authentication Code

**Goal:** Find all authentication-related files

**Query:**
```json
{
  "query": "authentication",
  "repo_id": "myapp",
  "limit": 20
}
```

**Expected results:**
- `src/auth/authentication.py`
- `src/services/auth_service.ts`
- `src/middleware/authenticate.js`
- `tests/auth/test_authentication.py`

**Refinement:** To exclude tests:
```json
{
  "query": "authentication service",
  "repo_id": "myapp",
  "limit": 20
}
```

### Example 2: Finding API Routes

**Goal:** Find all API route handlers

**Query:**
```json
{
  "query": "api routes",
  "repo_id": "myapp",
  "limit": 30
}
```

**Expected results:**
- `src/api/routes/users.py`
- `src/api/routes/payments.ts`
- `src/api/routes/products.js`

**Refinement:** For specific routes:
```json
{
  "query": "api routes payment",
  "repo_id": "myapp",
  "limit": 10
}
```

### Example 3: Finding Database Models

**Goal:** Find all database model definitions

**Query:**
```json
{
  "query": "models database",
  "repo_id": "myapp",
  "limit": 25
}
```

**Expected results:**
- `src/models/user.py`
- `src/models/payment.py`
- `src/database/models/order.ts`

**Refinement:** For specific model:
```json
{
  "query": "models user python",
  "repo_id": "myapp",
  "limit": 5
}
```

### Example 4: Finding Utility Functions

**Goal:** Find utility and helper files

**Query:**
```json
{
  "query": "utils helpers",
  "repo_id": "myapp",
  "limit": 20
}
```

**Expected results:**
- `src/utils/string_helpers.py`
- `src/helpers/date_utils.ts`
- `lib/utils/format.js`

**Refinement:** For specific utility:
```json
{
  "query": "utils date format",
  "repo_id": "myapp",
  "limit": 10
}
```

### Example 5: Finding Configuration Files

**Goal:** Find configuration and settings files

**Query:**
```json
{
  "query": "config settings",
  "repo_id": "myapp",
  "limit": 15
}
```

**Expected results:**
- `src/config/database.py`
- `src/config/app_settings.ts`
- `config/production.js`

## Ranking and Relevance

### How Files Are Ranked

Code Graph uses a multi-factor ranking algorithm:

```python
final_score = (
    fulltext_score *          # Base Neo4j score
    path_match_boost *        # 2.0 if query in path
    term_match_boost *        # 1.0-1.9 based on terms
    language_boost *          # 1.5 if language matches
    directory_boost *         # 1.2 for src/lib/core/app
    test_penalty              # 0.5 for test files (unless searching tests)
)
```

### Improving Search Relevance

#### 1. Use Specific Terms

❌ Bad: `"api"`
✅ Good: `"api routes payment"`

❌ Bad: `"service"`
✅ Good: `"user authentication service"`

#### 2. Include Context

❌ Bad: `"utils"`
✅ Good: `"utils date formatting"`

❌ Bad: `"model"`
✅ Good: `"database models user"`

#### 3. Match Project Terminology

Use terms from your project:

```
# If your project uses "handler"
"payment handler"

# If your project uses "controller"
"payment controller"
```

#### 4. Use Directory Structure

```
"api/routes payment"          # Better than just "payment"
"services/auth user"          # Better than just "auth"
```

#### 5. Specify Language

```
"database python"             # For Python DB files
"api typescript"              # For TypeScript API files
```

### Understanding Low Scores

If results have low scores (< 1.0), try:

1. **More specific terms**: Add keywords
2. **Different terms**: Use synonyms or alternative names
3. **Path hints**: Include directory names
4. **Language filter**: Add language name
5. **Check ingestion**: Verify files were ingested

## Integration Patterns

### Pattern 1: Explore Then Analyze

1. Search for relevant files
2. Use impact analysis on interesting files
3. Build context pack for detailed analysis

```javascript
// 1. Search
const search_result = await search("authentication", "myapp", 10);

// 2. Pick most relevant
const top_file = search_result[0].path;

// 3. Impact analysis
const impact = await analyze_impact("myapp", top_file);

// 4. Context pack
const context = await build_context_pack("myapp", {
  focus: top_file,
  stage: "implement"
});
```

### Pattern 2: Multi-Query Discovery

Search multiple related terms to build comprehensive view:

```python
queries = [
    "authentication service",
    "auth middleware",
    "user login",
    "session management"
]

all_files = set()
for query in queries:
    result = search(query, "myapp", 20)
    for file in result:
        all_files.add(file["path"])

print(f"Found {len(all_files)} unique files")
```

### Pattern 3: Language-Specific Analysis

Compare implementations across languages:

```python
languages = ["python", "typescript", "go"]
implementations = {}

for lang in languages:
    result = search(f"payment service {lang}", "myapp", 5)
    implementations[lang] = [f["path"] for f in result]

# Compare implementations
for lang, files in implementations.items():
    print(f"{lang}: {files}")
```

### Pattern 4: Progressive Refinement

Iteratively narrow results:

```python
query = "payment"
limit = 50

while True:
    result = search(query, "myapp", limit)
    print(f"Query: '{query}' → {len(result)} results")

    if len(result) <= 10:
        break  # Good number of results

    # Add more terms
    refinement = input("Add term to narrow: ")
    query = f"{query} {refinement}"
```

## Performance Tips

### Optimize Query Speed

1. **Use reasonable limits**: Default 30 is good, 100+ is slow
2. **Be specific**: More terms = faster, more accurate results
3. **Cache results**: Reuse results when possible
4. **Batch queries**: Group related searches

### Monitor Performance

```python
import time

start = time.time()
result = search("authentication", "myapp", 30)
duration = time.time() - start

print(f"Search took {duration*1000:.0f}ms")
print(f"Found {len(result)} files")
print(f"Throughput: {len(result)/duration:.0f} files/sec")
```

**Expected performance:**
- Small repos (<1K files): < 50ms
- Medium repos (1-10K files): < 100ms
- Large repos (>10K files): < 200ms

### Troubleshooting Slow Searches

If searches take > 500ms:

1. **Check fulltext index**:
   ```cypher
   SHOW INDEXES
   ```

2. **Rebuild index**:
   ```cypher
   DROP INDEX file_text IF EXISTS;
   CREATE FULLTEXT INDEX file_text FOR (f:File) ON EACH [f.path, f.lang];
   ```

3. **Reduce limit**: Use limit=20 instead of limit=100

4. **Check Neo4j memory**: Ensure adequate heap size

5. **Optimize patterns**: Exclude more files during ingestion

## Best Practices

### 1. Start Simple

Begin with 1-2 keywords, add more if needed:

```
"auth" → "auth service" → "auth service python"
```

### 2. Use Domain Terms

Match terminology used in your codebase:

```
# If your code uses "repository pattern"
"user repository"

# If your code uses "data access layer"
"user data access"
```

### 3. Leverage Path Structure

Include directory names for precision:

```
"api/routes payment"
"services/auth user"
"models/database order"
```

### 4. Filter by Language

For multi-language projects:

```
"database connection python"
"api client typescript"
```

### 5. Iterate Quickly

Don't overthink - search, review, refine:

1. Quick search
2. Scan results
3. Add/change terms
4. Repeat

## Troubleshooting

### No Results Found

**Possible causes:**
1. Files not ingested
2. Query too specific
3. Typo in query
4. Wrong repo_id

**Solutions:**
1. Verify ingestion: `MATCH (f:File {repoId: 'myapp'}) RETURN count(f)`
2. Simplify query: Try single keyword
3. Check spelling
4. List available repos: `MATCH (r:Repo) RETURN r.id`

### Irrelevant Results

**Possible causes:**
1. Query too generic
2. Test files included
3. Low-quality matches

**Solutions:**
1. Add more specific terms
2. Add "service" or "api" to exclude tests
3. Filter results by score > 1.0

### Missing Expected Files

**Possible causes:**
1. File not ingested
2. File too large (>100KB)
3. File excluded by patterns

**Solutions:**
1. Check if file exists in Neo4j
2. Check file size
3. Review ingestion patterns

### Duplicate Results

**Possible causes:**
1. Same repo ingested multiple times
2. File copied in multiple locations

**Solutions:**
1. Re-ingest with full mode
2. Check for actual duplicates in codebase

## Next Steps

Now that you can search effectively, learn about:

- **[Impact Analysis](impact.md)**: Understand code dependencies and blast radius
- **[Context Packing](context.md)**: Generate AI-friendly context bundles from search results

## Reference

### MCP Tool Definition

```json
{
  "name": "code_graph_related",
  "description": "Find files related to a query using fulltext search",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "repo_id": {
        "type": "string",
        "description": "Repository identifier"
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 30,
        "description": "Max results"
      }
    },
    "required": ["query", "repo_id"]
  }
}
```

### REST API Specification

**Endpoint:** `POST /api/v1/code-graph/search`

**Request:**
```typescript
interface SearchRequest {
  query: string;           // Required: Search query
  repo_id: string;         // Required: Repository ID
  limit?: number;          // Optional: Max results (default: 30, max: 100)
}
```

**Response:**
```typescript
interface SearchResponse {
  success: boolean;
  results: Array<{
    type: string;          // Always "file"
    path: string;          // File path
    lang: string;          // Programming language
    size: number;          // File size in bytes
    score: number;         // Relevance score
    summary: string;       // Human-readable description
    ref: string;           // ref:// handle
    repoId: string;        // Repository ID
  }>;
  query: string;           // Original query
  repo_id: string;         // Repository ID
  total_count: number;     // Number of results returned
  limit: number;           // Applied limit
}
```

### Ranking Algorithm

```python
def rank_file(file, query):
    """Calculate relevance score for a file"""
    score = file.fulltext_score  # Base Neo4j score

    # Path match boost
    if query.lower() in file.path.lower():
        score *= 2.0

    # Term matching boost
    query_terms = set(query.lower().split())
    path_terms = set(file.path.lower().split('/'))
    matching_terms = query_terms & path_terms
    if matching_terms:
        score *= (1.0 + len(matching_terms) * 0.3)

    # Language boost
    if query.lower() in file.lang.lower():
        score *= 1.5

    # Directory boost
    if any(prefix in file.path for prefix in ['src/', 'lib/', 'core/', 'app/']):
        score *= 1.2

    # Test penalty
    if 'test' not in query.lower() and ('test' in file.path or 'spec' in file.path):
        score *= 0.5

    return score
```
