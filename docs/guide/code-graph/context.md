# Context Packing Guide

## Introduction

Context packing is the art of generating curated, token-budget-aware context bundles for AI assistants. It solves one of the most common problems in AI-assisted development: **"What code should I show the LLM?"**

Instead of manually copying files or overwhelming the AI with too much context, context packing automatically selects the most relevant code within your specified token budget.

## The Context Problem

### Without Context Packing

**The manual approach:**

1. Search for relevant files
2. Copy-paste into chat
3. Realize you exceeded token limit
4. Remove some files
5. Wonder if you removed the wrong ones
6. Repeat process

**Problems:**
- ❌ Time-consuming
- ❌ Inconsistent results
- ❌ Easy to exceed token limits
- ❌ Hard to know what's most relevant
- ❌ Manual deduplication needed

### With Context Packing

**The automated approach:**

1. Specify repo_id, stage, and budget
2. Get curated context bundle
3. Use directly with AI

**Benefits:**
- ✅ Automatic relevance ranking
- ✅ Budget-aware selection
- ✅ Stage-optimized content
- ✅ Deduplication included
- ✅ Consistent, reproducible

## How It Works

Context packing follows a multi-stage process:

1. **Query the graph**: Search for relevant files/symbols
2. **Rank by relevance**: Score each item based on multiple factors
3. **Apply filters**: Remove duplicates and low-quality results
4. **Budget management**: Select items within token budget
5. **Category balancing**: Balance files vs symbols vs guidelines
6. **Format output**: Generate ref:// handles for AI tools

### The Pack Builder Algorithm

```python
def build_context_pack(nodes, budget, stage):
    # 1. Deduplicate nodes by ref handle
    nodes = deduplicate(nodes)

    # 2. Sort by relevance score
    nodes = sort_by_score(nodes, descending=True)

    # 3. Apply stage-specific prioritization
    nodes = prioritize_by_stage(nodes, stage)

    # 4. Pack within budget and category limits
    pack = []
    budget_used = 0
    file_count = 0
    symbol_count = 0

    for node in nodes:
        # Check category limits
        if node.type == "file" and file_count >= FILE_LIMIT:
            continue
        if node.type == "symbol" and symbol_count >= SYMBOL_LIMIT:
            continue

        # Estimate token cost
        tokens = estimate_tokens(node)

        # Check budget
        if budget_used + tokens > budget:
            break

        # Add to pack
        pack.append(node)
        budget_used += tokens

        if node.type == "file":
            file_count += 1
        elif node.type == "symbol":
            symbol_count += 1

    return pack, budget_used
```

## Using MCP Tools

### Tool: context_pack

Build a context pack within specified token budget.

#### Input Schema

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 1500,
  "keywords": "authentication user",
  "focus": "src/auth/service.py"
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_id` | string | Yes | - | Repository identifier |
| `stage` | string | No | `implement` | Development stage (`plan`, `review`, `implement`) |
| `budget` | integer | No | 1500 | Token budget (500-10000) |
| `keywords` | string | No | - | Focus keywords (optional) |
| `focus` | string | No | - | Focus file paths (optional) |

#### Example: Basic Context Pack

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 2000
}
```

**Response:**

```json
{
  "success": true,
  "items": [
    {
      "kind": "file",
      "title": "auth/service.py",
      "summary": "Python file service.py in auth/ directory",
      "ref": "ref://file/src/auth/service.py#L1-L1000",
      "extra": {
        "lang": "python",
        "score": 2.85
      }
    },
    {
      "kind": "file",
      "title": "api/routes.py",
      "summary": "Python file routes.py in api/ directory",
      "ref": "ref://file/src/api/routes.py#L1-L1000",
      "extra": {
        "lang": "python",
        "score": 2.41
      }
    }
  ],
  "budget_used": 1847,
  "budget_limit": 2000,
  "stage": "implement",
  "repo_id": "myapp",
  "category_counts": {
    "file": 2,
    "symbol": 0
  }
}
```

#### Example: Planning Stage

For high-level project overview:

```json
{
  "repo_id": "myapp",
  "stage": "plan",
  "budget": 1000
}
```

**Optimized for:**
- Project structure
- Entry points
- Key modules
- Architecture overview
- High-level organization

#### Example: Review Stage

For code review focus:

```json
{
  "repo_id": "myapp",
  "stage": "review",
  "budget": 2000,
  "focus": "src/api/routes/users.py"
}
```

**Optimized for:**
- Code quality
- Patterns and conventions
- Related files
- Test coverage
- Documentation

#### Example: Implementation Stage

For detailed coding work:

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 3000,
  "keywords": "authentication jwt token",
  "focus": "src/auth/"
}
```

**Optimized for:**
- Implementation details
- Function signatures
- Class definitions
- Detailed logic
- Dependencies

#### Example: Large Context

For comprehensive analysis:

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 8000,
  "keywords": "user authentication authorization"
}
```

**Use when:**
- Working with large context window LLMs (Claude Opus, GPT-4)
- Need comprehensive understanding
- Multiple related features
- Complex refactoring

#### Example: Claude Desktop Usage

In Claude Desktop:

```
I need to implement JWT authentication. Can you give me relevant context?
```

Claude calls the MCP tool:

```json
{
  "name": "context_pack",
  "arguments": {
    "repo_id": "myapp",
    "stage": "implement",
    "budget": 2000,
    "keywords": "jwt authentication"
  }
}
```

Claude then uses the ref:// handles to fetch file contents and provide informed assistance.

### Understanding Response Fields

#### Context Item Structure

Each item in the pack:

```json
{
  "kind": "file",                           // Item type (file/symbol/guideline)
  "title": "auth/service.py",               // Short display title
  "summary": "Python file service.py...",   // Human-readable description
  "ref": "ref://file/...",                  // Reference handle
  "extra": {
    "lang": "python",                       // Additional metadata
    "score": 2.85                           // Relevance score
  }
}
```

#### Budget Fields

```json
{
  "budget_used": 1847,        // Tokens used in pack
  "budget_limit": 2000,       // Requested budget
  "category_counts": {
    "file": 2,                // Number of file items
    "symbol": 0               // Number of symbol items
  }
}
```

#### Reference Handles

The `ref` field provides standardized file references:

```
ref://file/{path}#L{start}-L{end}
```

**Usage:**
- MCP clients can fetch content
- AI tools can request specific lines
- Deduplication by ref
- Future symbol references

## Using REST API

### Endpoint: POST /api/v1/code-graph/context-pack

#### Request Body

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 2000,
  "keywords": "authentication",
  "focus": "src/auth/"
}
```

#### Response

```json
{
  "success": true,
  "items": [
    {
      "kind": "file",
      "title": "auth/service.py",
      "summary": "Python file service.py in auth/ directory",
      "ref": "ref://file/src/auth/service.py#L1-L1000",
      "extra": {
        "lang": "python",
        "score": 2.85
      }
    }
  ],
  "budget_used": 1847,
  "budget_limit": 2000,
  "stage": "implement",
  "repo_id": "myapp"
}
```

#### Example: cURL

```bash
curl -X POST http://localhost:8000/api/v1/code-graph/context-pack \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "myapp",
    "stage": "implement",
    "budget": 2000,
    "keywords": "payment processing"
  }'
```

#### Example: Python

```python
import requests

def build_context(repo_id, stage, budget, keywords=None, focus=None):
    """Build context pack for AI assistant"""
    response = requests.post(
        "http://localhost:8000/api/v1/code-graph/context-pack",
        json={
            "repo_id": repo_id,
            "stage": stage,
            "budget": budget,
            "keywords": keywords,
            "focus": focus
        }
    )

    result = response.json()

    if result["success"]:
        print(f"Context Pack ({result['budget_used']}/{result['budget_limit']} tokens):")
        print(f"  {result['category_counts']['file']} files")
        print(f"  {result['category_counts']['symbol']} symbols")
        print("\nItems:")

        for item in result["items"]:
            print(f"  - {item['title']} (score: {item['extra']['score']:.2f})")
            print(f"    {item['ref']}")

        return result["items"]

# Usage
context = build_context(
    repo_id="myapp",
    stage="implement",
    budget=2000,
    keywords="user authentication"
)
```

#### Example: JavaScript

```javascript
async function buildContextPack(repoId, stage, budget, keywords = null, focus = null) {
  const response = await fetch('http://localhost:8000/api/v1/code-graph/context-pack', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_id: repoId,
      stage: stage,
      budget: budget,
      keywords: keywords,
      focus: focus
    })
  });

  const data = await response.json();

  if (data.success) {
    console.log(`Context Pack (${data.budget_used}/${data.budget_limit} tokens):`);
    console.log(`  ${data.category_counts.file} files`);
    console.log(`  ${data.category_counts.symbol} symbols`);
    console.log('\nItems:');

    data.items.forEach(item => {
      console.log(`  - ${item.title} (score: ${item.extra.score.toFixed(2)})`);
      console.log(`    ${item.ref}`);
    });

    return data.items;
  }
}

// Usage
const context = await buildContextPack(
  'myapp',
  'implement',
  2000,
  'payment processing'
);
```

## Stages Explained

### Plan Stage

**Purpose:** High-level project understanding and planning

**Optimized for:**
- Project structure overview
- Key entry points
- Main modules and their purposes
- Architectural patterns
- Technology stack

**Typical budget:** 500-1000 tokens

**Example use cases:**
- Starting new feature
- Understanding codebase structure
- Planning architecture changes
- Creating project roadmap
- Onboarding new developers

**What gets prioritized:**
- README and documentation files
- Main entry points (main.py, index.ts)
- Configuration files
- Package manifests
- Top-level directories

### Review Stage

**Purpose:** Code review and quality analysis

**Optimized for:**
- Code quality patterns
- Testing coverage
- Documentation completeness
- Convention adherence
- Related changes

**Typical budget:** 1000-2000 tokens

**Example use cases:**
- Code review preparation
- Quality audits
- Finding similar patterns
- Checking consistency
- Test coverage analysis

**What gets prioritized:**
- Files modified in recent commits
- Related test files
- Similar implementation patterns
- Documentation files
- Style and lint configs

### Implement Stage (Default)

**Purpose:** Detailed implementation work

**Optimized for:**
- Function and class definitions
- Implementation details
- Dependencies and imports
- Type definitions
- Helper utilities

**Typical budget:** 1500-3000 tokens

**Example use cases:**
- Writing new features
- Refactoring existing code
- Fixing bugs
- Understanding implementation
- API integration

**What gets prioritized:**
- Focused area files (via keywords/focus)
- Related utility functions
- Type definitions
- Interface definitions
- Helper modules

## Budget Guidelines

### Token Estimation

Context packing estimates tokens using:

```
estimated_tokens = (title_length + summary_length + ref_length + 50) / 4
```

**Character-to-token ratio:** ~4 characters per token (conservative estimate)

### Budget Recommendations

#### Small Context (500-1000 tokens)

**Best for:**
- Quick questions
- Focused tasks
- Planning stage
- Limited context LLMs

**Example:**
```json
{
  "stage": "plan",
  "budget": 800
}
```

**Typical result:** 3-5 files, high-level overview

#### Medium Context (1000-2000 tokens)

**Best for:**
- Regular development
- Code reviews
- Bug fixes
- Standard tasks

**Example:**
```json
{
  "stage": "implement",
  "budget": 1500
}
```

**Typical result:** 5-8 files, detailed content

#### Large Context (2000-5000 tokens)

**Best for:**
- Complex features
- Major refactoring
- Architecture changes
- Comprehensive analysis

**Example:**
```json
{
  "stage": "implement",
  "budget": 3000
}
```

**Typical result:** 10-15 files, comprehensive coverage

#### Extra Large Context (5000-10000 tokens)

**Best for:**
- Large context window LLMs (Claude Opus, GPT-4 Turbo)
- System-wide refactoring
- Complete feature implementation
- Deep analysis

**Example:**
```json
{
  "stage": "implement",
  "budget": 8000
}
```

**Typical result:** 20-30 files, exhaustive coverage

### LLM Context Windows

Match budget to your LLM's capabilities:

| LLM | Context Window | Recommended Budget | Use Case |
|-----|----------------|-------------------|----------|
| GPT-3.5 | 4K tokens | 500-1000 | Quick tasks |
| GPT-4 | 8K tokens | 1000-2000 | Regular dev |
| GPT-4 | 32K tokens | 2000-5000 | Complex tasks |
| GPT-4 Turbo | 128K tokens | 5000-10000 | Large refactoring |
| Claude 2 | 100K tokens | 5000-10000 | Comprehensive |
| Claude 3 | 200K tokens | 8000-10000+ | Full system |

**Rule of thumb:** Use 20-30% of context window for Code Graph context, leaving room for conversation.

## Keywords and Focus

### Using Keywords

Keywords filter and rank results based on relevance.

**Syntax:**
```
"keyword1 keyword2 keyword3"
```

**Examples:**

```json
// Authentication-related code
{"keywords": "authentication login jwt"}

// Payment processing
{"keywords": "payment stripe checkout"}

// Database operations
{"keywords": "database postgres migration"}

// API endpoints
{"keywords": "api routes endpoints"}
```

**Effect:**
- Files matching keywords get higher scores
- Non-matching files may be excluded if budget is tight
- Multiple keywords create AND logic (all should match)

### Using Focus

Focus prioritizes specific files or directories.

**Syntax:**
```
"path/to/file.py"           // Single file
"path/to/directory/"        // Directory
"file1.py,file2.py"         // Multiple files
```

**Examples:**

```json
// Focus on specific file
{"focus": "src/auth/service.py"}

// Focus on directory
{"focus": "src/api/routes/"}

// Focus on multiple files
{"focus": "src/auth/service.py,src/models/user.py"}
```

**Effect:**
- Focused files/directories appear first in results
- Gets priority in budget allocation
- Ensures important context is included

### Combining Keywords and Focus

For maximum precision:

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 2000,
  "keywords": "payment processing stripe",
  "focus": "src/api/routes/payment.py"
}
```

**Result:**
1. `src/api/routes/payment.py` (focused)
2. Other files matching "payment processing stripe"
3. Related files by dependency
4. Within 2000 token budget

## Category Limits

Context packing enforces category limits to ensure balanced context.

### Default Limits

```python
FILE_LIMIT = 8          # Maximum 8 file items
SYMBOL_LIMIT = 12       # Maximum 12 symbol items
```

**Why limits?**
- Prevents pack from being all files or all symbols
- Ensures variety in context
- Maintains readability
- Respects token budget

### File Items

**What counts as a file item:**
- Complete source files
- Configuration files
- Documentation files

**Current state (v0.7):**
- Only files are indexed
- Symbol extraction in progress
- FILE_LIMIT is primary constraint

### Symbol Items

**What will count as symbol items (v0.8+):**
- Functions
- Classes
- Methods
- Constants
- Type definitions

**Coming soon:**
- Function-level context
- Class-level context
- Mixed file + symbol packs

### Customizing Limits

Currently not exposed via API, but coming in v0.8:

```json
{
  "repo_id": "myapp",
  "stage": "implement",
  "budget": 2000,
  "file_limit": 12,       // Override default
  "symbol_limit": 8       // Override default
}
```

## Deduplication

Context packing automatically removes duplicates based on ref:// handles.

### How Deduplication Works

```python
def deduplicate(nodes):
    seen_refs = {}

    for node in nodes:
        ref = node.ref

        if ref in seen_refs:
            # Keep node with higher score
            if node.score > seen_refs[ref].score:
                seen_refs[ref] = node
        else:
            seen_refs[ref] = node

    return list(seen_refs.values())
```

### Why Deduplication Matters

**Without deduplication:**
```
ref://file/src/auth/service.py#L1-L1000  (score: 2.5)
ref://file/src/auth/service.py#L1-L1000  (score: 2.3)
ref://file/src/auth/service.py#L1-L1000  (score: 1.9)
```

**With deduplication:**
```
ref://file/src/auth/service.py#L1-L1000  (score: 2.5)  ← Highest score kept
```

**Benefits:**
- Avoids redundant context
- Saves token budget
- Cleaner output
- Better LLM performance

### Duplicate Sources

Files may appear multiple times from:

1. **Multiple searches**: Same file matches different keywords
2. **Dependency chains**: File appears at different depths
3. **Different rankings**: Different scoring methods
4. **Impact analysis**: File appears in multiple dependency paths

Deduplication resolves all of these automatically.

## Advanced Usage

### Pattern 1: Progressive Context Building

Start small, expand as needed:

```python
# 1. Start with small context
context = build_context_pack(
    repo_id="myapp",
    stage="plan",
    budget=500
)

# 2. User needs more detail
context = build_context_pack(
    repo_id="myapp",
    stage="implement",
    budget=1500,
    focus=context[0]["ref"]  # Focus on most relevant file
)

# 3. Deep dive into specific area
context = build_context_pack(
    repo_id="myapp",
    stage="implement",
    budget=3000,
    keywords="authentication security",
    focus="src/auth/"
)
```

### Pattern 2: Multi-Feature Context

Build context for multiple related features:

```python
features = [
    {"keywords": "user authentication", "budget": 1000},
    {"keywords": "payment processing", "budget": 1000},
    {"keywords": "email notifications", "budget": 1000}
]

all_context = []
for feature in features:
    pack = build_context_pack(
        repo_id="myapp",
        stage="implement",
        **feature
    )
    all_context.extend(pack["items"])

# Deduplicate across features
unique_refs = {}
for item in all_context:
    if item["ref"] not in unique_refs:
        unique_refs[item["ref"]] = item

print(f"Total unique files: {len(unique_refs)}")
```

### Pattern 3: Dependency-Aware Context

Combine search, impact analysis, and context packing:

```python
# 1. Find relevant files
search_results = search("authentication", "myapp", limit=10)

# 2. Analyze impact of top result
top_file = search_results[0]["path"]
impact = analyze_impact("myapp", top_file, depth=2)

# 3. Build context including dependencies
all_files = [top_file] + [i["path"] for i in impact["impact"][:5]]
focus_paths = ",".join(all_files)

context = build_context_pack(
    repo_id="myapp",
    stage="implement",
    budget=3000,
    focus=focus_paths
)
```

### Pattern 4: Stage-Specific Workflow

Use different stages for different tasks:

```python
# Planning phase
plan_context = build_context_pack(
    repo_id="myapp",
    stage="plan",
    budget=800,
    keywords="new feature"
)
# → Get overview for planning

# Review phase
review_context = build_context_pack(
    repo_id="myapp",
    stage="review",
    budget=1500,
    focus="src/new_feature/"
)
# → Review code quality

# Implementation phase
impl_context = build_context_pack(
    repo_id="myapp",
    stage="implement",
    budget=2500,
    keywords="new feature",
    focus="src/new_feature/"
)
# → Write implementation
```

### Pattern 5: Budget Optimization

Find optimal budget for your use case:

```python
budgets = [500, 1000, 1500, 2000, 3000, 5000]

for budget in budgets:
    pack = build_context_pack(
        repo_id="myapp",
        stage="implement",
        budget=budget,
        keywords="authentication"
    )

    print(f"Budget {budget}: "
          f"{pack['budget_used']} tokens used, "
          f"{pack['category_counts']['file']} files")

# Output:
# Budget 500: 487 tokens used, 2 files
# Budget 1000: 945 tokens used, 4 files
# Budget 1500: 1423 tokens used, 6 files
# Budget 2000: 1897 tokens used, 8 files  ← Hits file limit
# Budget 3000: 1897 tokens used, 8 files  ← Same (limit reached)
# Budget 5000: 1897 tokens used, 8 files  ← Same (limit reached)
```

## Integration Patterns

### Claude Desktop Integration

Claude Desktop automatically uses context packs via MCP:

**User:**
```
I need to add JWT authentication to the API
```

**Claude (internal):**
1. Calls `code_graph_related` to find relevant files
2. Calls `context_pack` with appropriate budget
3. Fetches file contents via ref:// handles
4. Provides informed response

**User sees:**
```
Based on your codebase, here's how to add JWT authentication...

[Response includes relevant code context]
```

### VS Code Extension

Custom VS Code extension can use context packing:

```typescript
// vscode-extension/context-provider.ts
async function getContextForCursor(document, position) {
  // Get current file
  const currentFile = document.fileName;

  // Build context pack
  const response = await fetch('http://localhost:8000/api/v1/code-graph/context-pack', {
    method: 'POST',
    body: JSON.stringify({
      repo_id: workspace.name,
      stage: 'implement',
      budget: 2000,
      focus: currentFile
    })
  });

  const pack = await response.json();

  // Show in sidebar
  showContextPanel(pack.items);

  return pack;
}
```

### Custom AI Agent

Build custom AI agents with context packing:

```python
class CodeAssistant:
    def __init__(self, repo_id, llm_client):
        self.repo_id = repo_id
        self.llm = llm_client

    async def answer_question(self, question, budget=2000):
        """Answer question with relevant code context"""

        # 1. Extract keywords from question
        keywords = self.extract_keywords(question)

        # 2. Build context pack
        pack = await build_context_pack(
            repo_id=self.repo_id,
            stage="implement",
            budget=budget,
            keywords=" ".join(keywords)
        )

        # 3. Fetch file contents
        context_text = ""
        for item in pack["items"]:
            content = await self.fetch_ref(item["ref"])
            context_text += f"\n\n=== {item['title']} ===\n{content}"

        # 4. Query LLM with context
        prompt = f"""
        Based on this code context:
        {context_text}

        Answer this question:
        {question}
        """

        response = await self.llm.complete(prompt)
        return response

# Usage
assistant = CodeAssistant("myapp", llm_client)
answer = await assistant.answer_question(
    "How does the authentication system work?"
)
```

### Continuous Integration

Use context packing in CI/CD for automated analysis:

```yaml
# .github/workflows/code-analysis.yml
name: Code Analysis

on: [pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Get changed files
        id: changes
        run: |
          FILES=$(git diff --name-only ${{ github.event.pull_request.base.sha }} ${{ github.sha }} | tr '\n' ',')
          echo "files=$FILES" >> $GITHUB_OUTPUT

      - name: Build context pack
        run: |
          curl -X POST http://code-graph:8000/api/v1/code-graph/context-pack \
            -H "Content-Type: application/json" \
            -d "{
              \"repo_id\": \"${{ github.repository }}\",
              \"stage\": \"review\",
              \"budget\": 3000,
              \"focus\": \"${{ steps.changes.outputs.files }}\"
            }" > context.json

      - name: AI Code Review
        run: |
          # Use context to perform AI-powered code review
          python scripts/ai_review.py context.json
```

## Troubleshooting

### Budget Not Fully Used

**Symptoms:**
```json
{
  "budget_used": 500,
  "budget_limit": 2000
}
```

**Possible causes:**
1. Hit category limit (FILE_LIMIT=8)
2. Not enough relevant files
3. Keywords too specific
4. Small repository

**Solutions:**
1. Check category counts
2. Remove or broaden keywords
3. Increase file limit (coming in v0.8)
4. Use focus parameter less restrictively

### Empty Context Pack

**Symptoms:**
```json
{
  "items": [],
  "budget_used": 0
}
```

**Possible causes:**
1. Repository not ingested
2. Keywords don't match anything
3. Focus path doesn't exist
4. Repository empty

**Solutions:**
1. Verify ingestion: `MATCH (f:File {repoId: 'myapp'}) RETURN count(f)`
2. Try without keywords
3. Check focus path spelling
4. Ingest repository

### Irrelevant Results

**Symptoms:**
- Files don't match expected content
- Low relevance scores
- Wrong files prioritized

**Solutions:**
1. Add more specific keywords
2. Use focus parameter
3. Try different stage
4. Adjust budget (smaller may be more focused)

### Inconsistent Results

**Symptoms:**
- Different results each time
- Unpredictable ordering

**Possible causes:**
1. Non-deterministic scoring
2. Database state changes
3. Recent ingestion

**Solutions:**
1. Use focus parameter for consistency
2. Wait after ingestion completes
3. Use specific keywords
4. Clear cache if implemented

## Best Practices

### 1. Match Budget to LLM

Use appropriate budgets for your LLM:

```python
# GPT-3.5 (4K context)
budget = 800

# GPT-4 (8K context)
budget = 1500

# GPT-4 (32K context)
budget = 3000

# Claude Opus (200K context)
budget = 8000
```

### 2. Use Appropriate Stage

```python
# High-level planning
stage = "plan"

# Code review
stage = "review"

# Implementation work
stage = "implement"
```

### 3. Leverage Keywords

Be specific:

```python
# ❌ Too generic
keywords = "code"

# ✅ Specific and relevant
keywords = "user authentication jwt token"
```

### 4. Focus When Needed

Use focus for targeted context:

```python
# Working on specific feature
focus = "src/features/payment/"

# Refactoring specific file
focus = "src/services/user_service.py"
```

### 5. Iterate and Refine

Start small, expand as needed:

```python
# 1. Quick overview
pack = build_pack(budget=500, stage="plan")

# 2. More detail
pack = build_pack(budget=1500, stage="implement", keywords="auth")

# 3. Comprehensive
pack = build_pack(budget=3000, stage="implement", keywords="auth jwt", focus="src/auth/")
```

## Next Steps

You've now learned all four Code Graph features:

1. ✅ [Repository Ingestion](ingestion.md)
2. ✅ [Search and Discovery](search.md)
3. ✅ [Impact Analysis](impact.md)
4. ✅ [Context Packing](context.md)

**Ready to use Code Graph?**

- **[Installation](../../getting-started/installation.md)**: Set up Code Graph
- **[Quick Start](../../getting-started/quickstart.md)**: Get started in 5 minutes
- **[MCP Setup](../../guide/mcp/setup.md)**: Configure Claude Desktop integration

## Reference

### MCP Tool Definition

```json
{
  "name": "context_pack",
  "description": "Build a context pack for AI agents within token budget",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo_id": {
        "type": "string",
        "description": "Repository identifier"
      },
      "stage": {
        "type": "string",
        "enum": ["plan", "review", "implement"],
        "default": "implement",
        "description": "Development stage"
      },
      "budget": {
        "type": "integer",
        "minimum": 500,
        "maximum": 10000,
        "default": 1500,
        "description": "Token budget"
      },
      "keywords": {
        "type": "string",
        "description": "Focus keywords (optional)"
      },
      "focus": {
        "type": "string",
        "description": "Focus file paths (optional)"
      }
    },
    "required": ["repo_id"]
  }
}
```

### REST API Specification

**Endpoint:** `POST /api/v1/code-graph/context-pack`

**Request:**
```typescript
interface ContextPackRequest {
  repo_id: string;                          // Required
  stage?: 'plan' | 'review' | 'implement'; // Default: 'implement'
  budget?: number;                          // Default: 1500, range: 500-10000
  keywords?: string;                        // Optional: space-separated
  focus?: string;                           // Optional: comma-separated paths
}
```

**Response:**
```typescript
interface ContextPackResponse {
  success: boolean;
  items: Array<{
    kind: 'file' | 'symbol' | 'guideline';  // Item type
    title: string;                           // Display title
    summary: string;                         // Description
    ref: string;                             // ref:// handle
    extra: {
      lang?: string;                         // Language
      score?: number;                        // Relevance score
    };
  }>;
  budget_used: number;                       // Tokens used
  budget_limit: number;                      // Requested budget
  stage: string;                             // Stage used
  repo_id: string;                           // Repository ID
  category_counts: {
    file: number;                            // File item count
    symbol: number;                          // Symbol item count
  };
}
```

### Category Limits

```python
FILE_LIMIT = 8          # Maximum file items
SYMBOL_LIMIT = 12       # Maximum symbol items
```

**Customization coming in v0.8**
