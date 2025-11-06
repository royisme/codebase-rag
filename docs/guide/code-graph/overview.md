# Code Graph Overview

## Introduction

Code Graph is the foundational feature of the Code Graph Knowledge System, providing intelligent code intelligence capabilities **without requiring vector embeddings or large language models**. It works in all deployment modes (minimal, standard, and full), making it the most accessible and performant feature for code analysis.

Unlike traditional code search tools that rely on simple text matching, Code Graph uses Neo4j's graph database and native fulltext indexing to understand code structure, file relationships, and dependency chains. This enables powerful capabilities like impact analysis, smart search, and context generation for AI assistants.

## What is Code Graph?

Code Graph is a graph-based representation of your codebase stored in Neo4j. When you ingest a repository, the system:

1. **Scans code files** across your repository (Python, TypeScript, JavaScript, Go, Rust, Java, etc.)
2. **Creates graph nodes** for repositories, files, and symbols (functions, classes)
3. **Establishes relationships** like IMPORTS, CALLS, DEFINED_IN, IN_REPO
4. **Indexes content** using Neo4j's native fulltext search for fast retrieval
5. **Calculates metrics** like file size, language, and change frequency

The result is a queryable graph that understands:

- Which files import other files
- Which functions call which other functions
- What would break if you modify a specific file
- Which files are most central to your codebase

## Key Features

### 1. Repository Ingestion

Transform your codebase into a searchable graph database.

**Modes:**

- **Incremental** (60x faster): Only process changed files using git diff
- **Full**: Complete re-ingestion for non-git projects or first-time setup

**Supported Languages:**

- Python (`.py`)
- TypeScript/JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`)
- Go (`.go`)
- Rust (`.rs`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`, `.hpp`)
- C# (`.cs`)
- Ruby (`.rb`)
- PHP (`.php`)
- Swift (`.swift`)
- Kotlin (`.kt`)
- Scala (`.scala`)

**What gets indexed:**

- File paths (for pattern matching)
- Programming language
- File size
- File content (for files < 100KB)
- SHA hash (for change detection)
- Git commit information (in incremental mode)

### 2. Fulltext Search

Find relevant files using Neo4j's native fulltext search engine. Unlike vector-based semantic search, fulltext search:

- Works **without embeddings or LLM**
- Provides **instant results** (< 100ms)
- Supports **fuzzy matching** and relevance scoring
- Scales to **large repositories** (10,000+ files)

**Search capabilities:**

- Keyword matching in file paths
- Language filtering
- Relevance ranking
- Multi-term queries
- Path pattern matching

### 3. Impact Analysis

Understand the blast radius of code changes before making them. Impact analysis traverses the dependency graph to find:

- **Direct dependents**: Files that directly import your file
- **Transitive dependents**: Files that indirectly depend on your file
- **Function callers**: Code that calls functions you're modifying
- **Import chains**: Complete dependency paths

This is critical for:

- **Refactoring**: Know what you'll break
- **Code review**: Understand change implications
- **Testing strategy**: Identify affected test suites
- **Architecture analysis**: Map system boundaries

### 4. Context Packing

Generate curated, token-budget-aware context bundles for AI assistants. Context packing solves the problem of "what code should I show the LLM?"

**Features:**

- **Budget-aware**: Respects token limits (500-10,000 tokens)
- **Stage-specific**: Different content for plan/review/implement stages
- **Smart ranking**: Prioritizes most relevant files
- **Deduplication**: Removes redundant references
- **Category limits**: Balances files vs symbols vs guidelines

**Use cases:**

- Claude Desktop integration via MCP
- VS Code Copilot context
- Custom AI agents
- Automated code review
- Documentation generation

## Architecture

### Graph Schema

Code Graph uses the following Neo4j schema:

```
Nodes:
  - Repo: Repository root
    - Properties: id, created, file_count

  - File: Source code file
    - Properties: repoId, path, lang, size, content, sha, updated
    - Constraints: Composite key (repoId, path)

  - Symbol: Function or class
    - Properties: id, name, type, lang
    - Constraints: Unique id

Relationships:
  - (File)-[:IN_REPO]->(Repo): File belongs to repository
  - (File)-[:IMPORTS]->(File): File imports another file
  - (Symbol)-[:DEFINED_IN]->(File): Symbol defined in file
  - (Symbol)-[:CALLS]->(Symbol): Symbol calls another symbol
```

### Indexes

Code Graph creates several indexes for optimal performance:

1. **Fulltext Index** (`file_text`):
   - Indexes: File path, language
   - Used for: Fast fulltext search
   - Type: Neo4j native fulltext

2. **Property Indexes**:
   - `file_path`: Exact path lookups
   - `file_repo`: Filter by repository
   - `symbol_name`: Symbol name lookups

3. **Composite Keys**:
   - `(repoId, path)`: Unique file identification
   - Allows same filename in different repos

### Performance Characteristics

| Operation | Small Repo (<1K files) | Medium Repo (1K-10K files) | Large Repo (>10K files) |
|-----------|----------------------|---------------------------|------------------------|
| **Full Ingestion** | 5-10s | 30-60s | 2-5min |
| **Incremental Update** | <1s | 1-3s | 3-10s |
| **Fulltext Search** | <50ms | <100ms | <200ms |
| **Impact Analysis** | <100ms | <200ms | <500ms |
| **Context Pack** | <200ms | <300ms | <500ms |

**Scalability:**

- Tested with repositories up to 50,000 files
- Neo4j graph database scales horizontally
- Fulltext index automatically optimized
- Memory usage: ~50MB per 1,000 files

## Integration Points

### 1. MCP Server (Model Context Protocol)

Code Graph provides 4 MCP tools for AI assistants:

- `code_graph_ingest_repo`: Ingest repository
- `code_graph_related`: Find related files
- `code_graph_impact`: Analyze impact
- `context_pack`: Build context bundle

**Compatible with:**

- Claude Desktop
- VS Code with MCP extension
- Any MCP-compatible client

### 2. REST API

All Code Graph features are available via HTTP REST API:

```
POST /api/v1/code-graph/ingest       - Ingest repository
POST /api/v1/code-graph/search       - Fulltext search
POST /api/v1/code-graph/impact       - Impact analysis
POST /api/v1/code-graph/context-pack - Build context pack
```

### 3. Direct Service Access

For custom integrations, use Python services directly:

```python
from services.graph_service import graph_service
from services.code_ingestor import code_ingestor
from services.ranker import ranker
from services.pack_builder import pack_builder
```

## Deployment Modes

Code Graph works identically across all deployment modes:

### Minimal Mode

**What's included:**
- Neo4j database only
- Code Graph (all features)
- No embeddings or LLM required

**Resource requirements:**
- Docker image: ~500MB
- Memory: 512MB minimum
- CPU: 1 core minimum
- Startup time: ~5 seconds

**Best for:**
- Individual developers
- Learning the system
- CI/CD integration
- Budget-conscious deployments

### Standard Mode

**What's included:**
- Neo4j database
- Code Graph (all features)
- Memory Store (manual management)
- Embedding model (for memory search)

**Additional capabilities:**
- Memory Store for project knowledge
- Vector search for memories
- Still no LLM required for Code Graph

### Full Mode

**What's included:**
- Everything from Standard
- LLM integration
- Memory auto-extraction
- Knowledge RAG

**Additional capabilities:**
- Memory extraction from git commits
- Knowledge base Q&A
- Advanced AI features

**Note:** Code Graph features work identically in all modes. Only additional features change.

## Use Cases

### 1. Understanding Unfamiliar Codebases

**Scenario:** You've joined a new team and need to understand a large codebase quickly.

**Workflow:**
1. Ingest the repository
2. Search for key terms (e.g., "authentication", "database")
3. Use impact analysis to understand dependencies
4. Generate context packs for specific areas

**Benefits:**
- No need to read thousands of files
- Quickly identify entry points
- Understand system architecture
- Find related code automatically

### 2. Refactoring with Confidence

**Scenario:** You need to refactor a core module but don't know what depends on it.

**Workflow:**
1. Run impact analysis on the file you want to change
2. Review all dependent files (direct and transitive)
3. Assess the blast radius
4. Plan your refactoring strategy

**Benefits:**
- Know exactly what you'll break
- Identify all test files to update
- Plan migration strategy
- Avoid surprise breakages

### 3. AI-Assisted Development

**Scenario:** You want to use Claude Desktop to help with development but need relevant context.

**Workflow:**
1. Ingest your repository
2. Use MCP tools in Claude Desktop
3. Generate context packs for specific tasks
4. Ask Claude questions with full context

**Benefits:**
- AI has relevant code context
- Token budget automatically managed
- No manual copy-pasting
- Stay within LLM context limits

### 4. Code Review Assistance

**Scenario:** Reviewing a pull request that touches multiple files.

**Workflow:**
1. Run impact analysis on changed files
2. Identify all affected components
3. Search for related test files
4. Generate review context pack

**Benefits:**
- Complete picture of PR impact
- Don't miss hidden dependencies
- Find affected tests automatically
- Better review quality

### 5. Architectural Analysis

**Scenario:** Need to understand system architecture and identify tightly coupled components.

**Workflow:**
1. Ingest the repository
2. Query the graph for high-degree nodes (many connections)
3. Analyze import/call patterns
4. Identify architectural boundaries

**Benefits:**
- Discover hidden dependencies
- Identify refactoring opportunities
- Understand layer violations
- Plan architecture improvements

## Comparison with Alternatives

### vs. grep/ripgrep

| Feature | grep/ripgrep | Code Graph |
|---------|-------------|------------|
| Text search | ✅ Excellent | ✅ Good |
| Relationship analysis | ❌ None | ✅ Full support |
| Impact analysis | ❌ Manual | ✅ Automatic |
| Ranking | ❌ None | ✅ Relevance-based |
| Scalability | ⚠️ Slows on large repos | ✅ Constant time |

**When to use grep:** Quick one-off searches, simple text matching

**When to use Code Graph:** Understanding relationships, impact analysis, repeated searches

### vs. ctags/universal-ctags

| Feature | ctags | Code Graph |
|---------|-------|------------|
| Symbol indexing | ✅ Excellent | ✅ Good |
| Cross-file analysis | ❌ Limited | ✅ Full support |
| Dependency tracking | ❌ None | ✅ Complete |
| Search capabilities | ⚠️ Basic | ✅ Advanced |
| Graph traversal | ❌ None | ✅ Full support |

**When to use ctags:** Editor integration, local navigation

**When to use Code Graph:** Cross-file analysis, dependency tracking, impact analysis

### vs. Vector-based semantic search

| Feature | Vector Search | Code Graph |
|---------|--------------|------------|
| Semantic understanding | ✅ Excellent | ⚠️ Limited |
| Relationship analysis | ❌ None | ✅ Full support |
| Setup complexity | ⚠️ High (embeddings) | ✅ Low (no LLM) |
| Performance | ⚠️ Slower | ✅ Fast |
| Resource requirements | ⚠️ High | ✅ Low |

**When to use Vector Search:** Natural language queries, semantic similarity

**When to use Code Graph:** Structural analysis, fast searches, resource-constrained environments

### vs. Language Server Protocol (LSP)

| Feature | LSP | Code Graph |
|---------|-----|------------|
| Real-time analysis | ✅ Excellent | ⚠️ Batch |
| Cross-file features | ✅ Good | ✅ Excellent |
| Language support | ⚠️ Per-language | ✅ Universal |
| Historical analysis | ❌ None | ✅ Git integration |
| AI integration | ❌ Limited | ✅ Native |

**When to use LSP:** Editor integration, real-time feedback, language-specific features

**When to use Code Graph:** Cross-language analysis, historical changes, AI assistance

## Best Practices

### 1. Ingestion Strategy

**For active development:**
- Use **incremental mode** for fast updates
- Run ingestion on every pull request
- Automate with CI/CD hooks

**For initial setup:**
- Use **full mode** first time
- Verify ingestion completed successfully
- Check Neo4j for expected file count

**For large repositories (>10K files):**
- Use incremental mode exclusively
- Schedule full re-ingestion monthly
- Monitor ingestion performance

### 2. Search Optimization

**For best search results:**
- Use specific terms (not single letters)
- Include file extensions for language filtering
- Combine multiple keywords
- Use path segments for targeted search

**Examples:**
- Good: `authentication service typescript`
- Bad: `auth ts`
- Good: `api/routes payment`
- Bad: `pay`

### 3. Impact Analysis

**When running impact analysis:**
- Start with `depth=1` for direct dependencies
- Increase to `depth=2` for transitive dependencies
- Rarely go beyond `depth=3` (too much noise)
- Focus on high-score results first

**Interpreting results:**
- `score=1.0`: Direct CALLS relationship, depth 1
- `score=0.9`: Direct IMPORTS relationship, depth 1
- `score=0.7`: Transitive CALLS, depth 2
- `score<0.5`: Indirect dependencies, lower priority

### 4. Context Packing

**Budget recommendations:**
- **Planning**: 500-1000 tokens (high-level overview)
- **Review**: 1000-2000 tokens (focused analysis)
- **Implementation**: 1500-3000 tokens (detailed context)
- **Large context**: 3000-10000 tokens (comprehensive)

**Stage selection:**
- `plan`: Project structure, entry points, key files
- `review`: Code quality, patterns, conventions
- `implement`: Detailed implementation, symbols, logic

### 5. Performance Tuning

**For optimal performance:**
- Keep files under 100KB (for content indexing)
- Exclude generated files (node_modules, build/)
- Run incremental updates frequently
- Monitor Neo4j memory usage

**Troubleshooting slow queries:**
- Check Neo4j indexes are created
- Verify fulltext index exists
- Reduce search result limit
- Add more specific search terms

## Limitations

### Current Limitations

1. **No semantic understanding**: Code Graph uses fulltext search, not embeddings
   - Can't find synonyms or related concepts
   - Requires keyword matching
   - No natural language queries

2. **Limited symbol analysis**: Basic function/class detection only
   - No deep AST parsing
   - No type inference
   - No cross-language call graphs (yet)

3. **File size limits**: Files > 100KB are not content-indexed
   - Path and metadata still indexed
   - Impact analysis still works
   - Just no fulltext search of content

4. **No real-time updates**: Ingestion is batch-based
   - Not suitable for editor integration
   - Run manually or via CI/CD
   - Use incremental mode for faster updates

### Planned Improvements

**v0.8 (Next Release):**
- Enhanced AST parsing for better symbol detection
- Cross-language call graph analysis
- Real-time file watching (optional)

**v0.9 (Future):**
- Hybrid vector + fulltext search
- AI-powered code summarization
- Natural language query support

**v1.0 (Long-term):**
- Multi-repo dependency tracking
- Language-specific analyzers
- Performance profiling integration

## Getting Started

Ready to use Code Graph? Check out these guides:

1. [**Repository Ingestion**](ingestion.md) - Learn how to ingest your codebase
2. [**Search and Discovery**](search.md) - Master fulltext search and ranking
3. [**Impact Analysis**](impact.md) - Understand dependencies and blast radius
4. [**Context Packing**](context.md) - Generate AI-friendly context bundles

## FAQ

### Does Code Graph require an LLM or embeddings?

**No.** Code Graph works with Neo4j alone. It uses native fulltext indexing, not vector embeddings or LLMs.

### What deployment mode do I need?

**Any mode.** Code Graph works identically in minimal, standard, and full deployment modes.

### How is this different from GitHub Copilot?

Code Graph is a **knowledge management system**, not a code completion tool. It helps you understand your codebase structure, dependencies, and relationships. It can feed context to Copilot, but doesn't replace it.

### Can I use this with private/confidential code?

**Yes.** Code Graph runs entirely on-premise or in your infrastructure. No code is sent to external services. It's completely self-hosted.

### How much disk space does it need?

**Approximately 10-20% of your source code size.** A 1GB repository typically requires 100-200MB of Neo4j storage.

### Does it work with monorepos?

**Yes.** Code Graph handles monorepos well. You can ingest the entire monorepo and search across all projects, or ingest individual projects separately.

### Can I query the graph directly?

**Yes.** You can access Neo4j Browser at `http://localhost:7474` and run Cypher queries directly. See the Neo4j documentation for query syntax.

### What if my language isn't supported?

Files are still indexed by path and metadata, just without language-specific symbol extraction. Fulltext search and impact analysis still work. Language support is expanding in future releases.

## Next Steps

- **[Ingestion Guide](ingestion.md)**: Learn how to ingest your first repository
- **[Search Guide](search.md)**: Master search and discovery techniques
- **[Impact Analysis](impact.md)**: Understand code dependencies
- **[Context Packing](context.md)**: Generate AI context bundles
