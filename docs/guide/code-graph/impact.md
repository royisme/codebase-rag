# Impact Analysis Guide

## Introduction

Impact analysis is one of Code Graph's most powerful features. It answers the critical question: **"If I change this file, what else might break?"**

By traversing the dependency graph, Code Graph identifies all files that depend on your target file, helping you understand the blast radius of code changes before making them.

## What is Impact Analysis?

Impact analysis finds **reverse dependencies** - files and symbols that depend on or call the code you're planning to modify.

### The Problem It Solves

**Without impact analysis:**
- Make changes to a file
- Hope nothing breaks
- Discover issues in production
- Spend hours debugging
- Emergency rollback

**With impact analysis:**
- See what depends on the file
- Identify all affected components
- Update dependent code proactively
- Run targeted tests
- Deploy with confidence

### How It Works

Code Graph traverses the dependency graph in reverse:

1. **Start node**: The file you want to analyze
2. **Find symbols**: Functions and classes defined in that file
3. **Traverse backwards**: Find who CALLS or IMPORTS these
4. **Follow chains**: Continue for N levels (depth)
5. **Score results**: Rank by importance and directness
6. **Return impact**: List of affected files with metadata

### Relationship Types

Impact analysis considers two types of relationships:

**IMPORTS relationships:**
```
(FileA)-[:IMPORTS]->(FileB)
```
FileA imports FileB. If you change FileB, FileA is affected.

**CALLS relationships:**
```
(SymbolA)-[:CALLS]->(SymbolB)
```
SymbolA calls SymbolB. If you change SymbolB's behavior, SymbolA is affected.

## Using MCP Tools

### Tool: code_graph_impact

Analyze the impact of changing a specific file.

#### Input Schema

```json
{
  "repo_id": "myapp",
  "file_path": "src/auth/service.py",
  "depth": 2
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_id` | string | Yes | - | Repository identifier |
| `file_path` | string | Yes | - | Path to file to analyze |
| `depth` | integer | No | 2 | Traversal depth (1-5) |

#### Example: Basic Impact Analysis

```json
{
  "repo_id": "myapp",
  "file_path": "src/services/user_service.py",
  "depth": 2
}
```

**Response:**

```json
{
  "success": true,
  "target": {
    "path": "src/services/user_service.py",
    "lang": "python",
    "repo_id": "myapp"
  },
  "impact": [
    {
      "type": "file",
      "path": "src/api/routes/users.py",
      "lang": "python",
      "repoId": "myapp",
      "relationship": "CALLS",
      "depth": 1,
      "score": 1.0
    },
    {
      "type": "file",
      "path": "src/api/routes/auth.py",
      "lang": "python",
      "repoId": "myapp",
      "relationship": "CALLS",
      "depth": 1,
      "score": 1.0
    },
    {
      "type": "file",
      "path": "src/controllers/user_controller.py",
      "lang": "python",
      "repoId": "myapp",
      "relationship": "IMPORTS",
      "depth": 1,
      "score": 0.9
    },
    {
      "type": "file",
      "path": "src/api/routes/admin.py",
      "lang": "python",
      "repoId": "myapp",
      "relationship": "CALLS",
      "depth": 2,
      "score": 0.7
    }
  ],
  "total_count": 4,
  "depth": 2
}
```

#### Example: Shallow Analysis (Depth 1)

For quick checks, use depth=1 to see only direct dependencies:

```json
{
  "repo_id": "myapp",
  "file_path": "src/models/user.py",
  "depth": 1
}
```

This shows only files that **directly** import or call the target file.

#### Example: Deep Analysis (Depth 3)

For comprehensive impact assessment:

```json
{
  "repo_id": "myapp",
  "file_path": "src/database/connection.py",
  "depth": 3
}
```

This traces dependencies through 3 levels, showing the full chain of affected files.

#### Example: Claude Desktop Usage

In Claude Desktop:

```
What would break if I modify src/auth/service.py?
```

Claude calls the MCP tool:

```json
{
  "name": "code_graph_impact",
  "arguments": {
    "repo_id": "myapp",
    "file_path": "src/auth/service.py",
    "depth": 2
  }
}
```

Claude then presents the results in a readable format:

```
If you modify src/auth/service.py, these files would be affected:

Direct Dependencies (depth 1):
- src/api/routes/auth.py (CALLS)
- src/middleware/auth_middleware.py (IMPORTS)

Indirect Dependencies (depth 2):
- src/api/routes/admin.py (CALLS through auth.py)
- tests/integration/test_auth.py (CALLS through middleware)
```

### Understanding Response Fields

#### Impact Node Structure

Each impact node contains:

```json
{
  "type": "file",                          // Always "file" (symbols coming in v0.8)
  "path": "src/api/routes/users.py",      // Dependent file path
  "lang": "python",                        // Programming language
  "repoId": "myapp",                       // Repository ID
  "relationship": "CALLS",                 // Relationship type (CALLS or IMPORTS)
  "depth": 1,                              // Dependency distance
  "score": 1.0                             // Impact score
}
```

#### Relationship Field

- **CALLS**: A symbol in the dependent file calls a symbol in your file
- **IMPORTS**: The dependent file imports your file directly

#### Depth Field

Distance from the target file:

- **depth=1**: Direct dependency (file directly imports/calls target)
- **depth=2**: Transitive dependency (depends through one intermediate)
- **depth=3**: Second-level transitive dependency
- **depth>3**: Deep indirect dependency

#### Score Field

Impact score ranges from 0.5 to 1.0:

| Score | Meaning | Description |
|-------|---------|-------------|
| 1.0 | **Critical** | Direct CALLS at depth 1 |
| 0.9 | **High** | Direct IMPORTS at depth 1 |
| 0.7 | **Medium** | Transitive CALLS at depth 2 |
| 0.6 | **Medium-Low** | Transitive IMPORTS at depth 2 |
| 0.5 | **Low** | Deep dependencies (depth 3+) |

**Score formula:**

```python
if depth == 1 and relationship == "CALLS":
    score = 1.0
elif depth == 1 and relationship == "IMPORTS":
    score = 0.9
elif depth == 2 and relationship == "CALLS":
    score = 0.7
elif depth == 2 and relationship == "IMPORTS":
    score = 0.6
else:
    score = 0.5 / depth
```

## Using REST API

### Endpoint: POST /api/v1/code-graph/impact

#### Request Body

```json
{
  "repo_id": "myapp",
  "file_path": "src/auth/service.py",
  "depth": 2
}
```

#### Response

```json
{
  "success": true,
  "target": {
    "path": "src/auth/service.py",
    "lang": "python"
  },
  "impact": [
    {
      "path": "src/api/routes/auth.py",
      "relationship": "CALLS",
      "depth": 1,
      "score": 1.0
    }
  ],
  "total_count": 1,
  "depth": 2
}
```

#### Example: cURL

```bash
curl -X POST http://localhost:8000/api/v1/code-graph/impact \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "myapp",
    "file_path": "src/services/payment.py",
    "depth": 2
  }'
```

#### Example: Python

```python
import requests

def analyze_impact(repo_id, file_path, depth=2):
    response = requests.post(
        "http://localhost:8000/api/v1/code-graph/impact",
        json={
            "repo_id": repo_id,
            "file_path": file_path,
            "depth": depth
        }
    )

    result = response.json()
    if result["success"]:
        print(f"Impact analysis for {file_path}:")
        print(f"Found {result['total_count']} dependent files\n")

        # Group by depth
        by_depth = {}
        for item in result["impact"]:
            d = item["depth"]
            if d not in by_depth:
                by_depth[d] = []
            by_depth[d].append(item)

        # Print by depth
        for depth in sorted(by_depth.keys()):
            print(f"Depth {depth} ({len(by_depth[depth])} files):")
            for item in by_depth[depth]:
                print(f"  - {item['path']} ({item['relationship']})")
            print()

# Usage
analyze_impact("myapp", "src/auth/service.py", depth=2)
```

#### Example: JavaScript

```javascript
async function analyzeImpact(repoId, filePath, depth = 2) {
  const response = await fetch('http://localhost:8000/api/v1/code-graph/impact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo_id: repoId,
      file_path: filePath,
      depth: depth
    })
  });

  const data = await response.json();

  if (data.success) {
    console.log(`Impact analysis for ${filePath}:`);
    console.log(`Found ${data.total_count} dependent files\n`);

    // Group by score
    const critical = data.impact.filter(i => i.score >= 0.9);
    const medium = data.impact.filter(i => i.score >= 0.6 && i.score < 0.9);
    const low = data.impact.filter(i => i.score < 0.6);

    if (critical.length > 0) {
      console.log('Critical Impact:');
      critical.forEach(i => console.log(`  - ${i.path}`));
    }

    if (medium.length > 0) {
      console.log('\nMedium Impact:');
      medium.forEach(i => console.log(`  - ${i.path}`));
    }

    if (low.length > 0) {
      console.log('\nLow Impact:');
      low.forEach(i => console.log(`  - ${i.path}`));
    }
  }
}

// Usage
analyzeImpact('myapp', 'src/auth/service.py', 2);
```

## Depth Selection

Choosing the right depth is critical for useful impact analysis.

### Depth 1: Direct Dependencies Only

**When to use:**
- Quick sanity check
- Verifying expectations
- Small, focused changes
- Well-understood components

**Pros:**
- Fast (< 100ms)
- Clear, actionable results
- No noise

**Cons:**
- May miss important indirect impacts
- Incomplete picture

**Example use case:**
```
You're renaming a function in a utility file.
Use depth=1 to see direct callers.
```

### Depth 2: Standard (Recommended)

**When to use:**
- Regular refactoring
- API changes
- Most scenarios
- Default choice

**Pros:**
- Comprehensive coverage
- Reasonable performance (< 200ms)
- Catches most real impacts
- Good signal-to-noise ratio

**Cons:**
- May include some indirect effects you don't care about

**Example use case:**
```
You're changing a service layer API.
Use depth=2 to see routes and controllers that depend on it.
```

### Depth 3: Deep Analysis

**When to use:**
- Core infrastructure changes
- Database schema modifications
- Major refactoring
- Architecture analysis

**Pros:**
- Very comprehensive
- Finds deep dependencies
- Good for planning

**Cons:**
- Slower (200-500ms)
- More noise
- Many low-importance results

**Example use case:**
```
You're changing the database connection pool.
Use depth=3 to see everything that might be affected.
```

### Depth 4-5: Exhaustive Search

**When to use:**
- Rarely needed
- Understanding system architecture
- Finding all possible paths
- Academic interest

**Pros:**
- Complete dependency graph
- No missing links

**Cons:**
- Slow (> 500ms)
- Lots of noise
- Diminishing returns
- Hard to interpret

**Example use case:**
```
You're analyzing the full dependency tree of a core module.
Use depth=5 to see the complete picture.
```

## Interpreting Results

### Critical Impact (Score ≥ 0.9)

**These files will definitely break if you change the target.**

```json
{
  "path": "src/api/routes/users.py",
  "relationship": "CALLS",
  "depth": 1,
  "score": 1.0
}
```

**Action items:**
- ✅ Update these files in the same PR
- ✅ Add tests covering these interactions
- ✅ Review these files carefully
- ✅ Communicate changes to owners

### Medium Impact (Score 0.6-0.8)

**These files might break, depending on the nature of your change.**

```json
{
  "path": "src/controllers/admin.py",
  "relationship": "CALLS",
  "depth": 2,
  "score": 0.7
}
```

**Action items:**
- ⚠️ Review if your changes affect them
- ⚠️ Consider updating if interface changes
- ⚠️ Run integration tests
- ⚠️ Document breaking changes

### Low Impact (Score < 0.6)

**These files are unlikely to break, but worth noting.**

```json
{
  "path": "src/utils/logging.py",
  "relationship": "IMPORTS",
  "depth": 3,
  "score": 0.5
}
```

**Action items:**
- ℹ️ Good to know about
- ℹ️ No immediate action needed
- ℹ️ Monitor in case of issues
- ℹ️ Update documentation

### No Impact

**If impact analysis returns 0 results:**

```json
{
  "success": true,
  "impact": [],
  "total_count": 0
}
```

**Possible meanings:**
1. ✅ File is truly isolated (rare)
2. ⚠️ File is new (no dependencies yet)
3. ⚠️ Symbol extraction not complete
4. ❌ File doesn't exist in graph

**Verification:**
```cypher
// Check if file exists
MATCH (f:File {path: 'your/file.py'})
RETURN f

// Check outgoing relationships
MATCH (f:File {path: 'your/file.py'})-[r]-()
RETURN type(r), count(*)
```

## Use Cases

### Use Case 1: Refactoring

**Scenario:** You need to refactor a service class.

**Workflow:**

1. **Analyze impact:**
   ```json
   {
     "repo_id": "myapp",
     "file_path": "src/services/user_service.py",
     "depth": 2
   }
   ```

2. **Review results:**
   - 12 files directly depend on this service
   - 34 files indirectly depend on it

3. **Plan changes:**
   - Update 12 direct dependents
   - Add deprecation warnings
   - Plan migration strategy

4. **Execute:**
   - Refactor service
   - Update dependents
   - Run tests
   - Deploy

**Benefits:**
- Know exactly what to update
- No surprises in production
- Confidence in changes

### Use Case 2: Breaking Changes

**Scenario:** You need to make a breaking change to an API.

**Workflow:**

1. **Analyze impact (depth=3):**
   ```json
   {
     "repo_id": "myapp",
     "file_path": "src/api/v1/users.py",
     "depth": 3
   }
   ```

2. **Categorize results:**
   - Critical: 8 files (must update)
   - Medium: 15 files (might update)
   - Low: 23 files (monitor)

3. **Communication:**
   - Notify owners of critical files
   - Document breaking changes
   - Provide migration guide

4. **Migration:**
   - Create v2 API alongside v1
   - Deprecate v1
   - Monitor usage
   - Sunset v1 after migration

### Use Case 3: Code Review

**Scenario:** Reviewing a PR that modifies shared utilities.

**Workflow:**

1. **For each modified file, run impact analysis:**
   ```python
   changed_files = [
       "src/utils/string.py",
       "src/utils/date.py"
   ]

   for file in changed_files:
       impact = analyze_impact("myapp", file, depth=2)
       print(f"{file}: {impact['total_count']} dependents")
   ```

2. **Check if tests cover impact:**
   - List all dependent files
   - Check if they have tests
   - Verify tests run in CI

3. **Request additional tests:**
   - If high-impact files lack tests
   - If new functionality added
   - If breaking changes made

### Use Case 4: Test Planning

**Scenario:** Determining which tests to run after changes.

**Workflow:**

1. **Get list of changed files (from git):**
   ```bash
   git diff --name-only main
   ```

2. **For each file, get impact:**
   ```python
   changed = ["src/auth/service.py", "src/models/user.py"]
   all_impacted = set()

   for file in changed:
       result = analyze_impact("myapp", file, depth=2)
       for item in result["impact"]:
           all_impacted.add(item["path"])
   ```

3. **Find associated tests:**
   ```python
   test_files = [f for f in all_impacted if "test_" in f or "/tests/" in f]
   ```

4. **Run targeted tests:**
   ```bash
   pytest {' '.join(test_files)}
   ```

**Benefits:**
- Run only relevant tests
- Faster CI/CD
- Better coverage

### Use Case 5: Architecture Analysis

**Scenario:** Understanding system coupling and architecture.

**Workflow:**

1. **Identify core modules:**
   ```python
   core_modules = [
       "src/database/connection.py",
       "src/auth/service.py",
       "src/api/main.py"
   ]
   ```

2. **Analyze each module:**
   ```python
   for module in core_modules:
       result = analyze_impact("myapp", module, depth=3)
       print(f"{module}: {result['total_count']} dependents")
   ```

3. **Identify high-coupling modules:**
   - Modules with > 50 dependents: High coupling
   - Modules with < 5 dependents: Low coupling

4. **Plan improvements:**
   - Reduce coupling in high-coupling modules
   - Add abstraction layers
   - Improve module boundaries

### Use Case 6: Onboarding

**Scenario:** New developer learning codebase structure.

**Workflow:**

1. **Start with entry point:**
   ```json
   {
     "repo_id": "myapp",
     "file_path": "src/main.py",
     "depth": 2
   }
   ```

2. **Understand dependencies:**
   - What does main.py depend on?
   - What are the key services?
   - How are layers organized?

3. **Explore key modules:**
   ```python
   key_files = [
       "src/api/routes/users.py",
       "src/services/auth.py",
       "src/models/user.py"
   ]

   for file in key_files:
       result = analyze_impact("myapp", file, depth=1)
       print(f"\n{file} is used by:")
       for item in result["impact"][:5]:
           print(f"  - {item['path']}")
   ```

4. **Build mental model:**
   - Understand system architecture
   - Identify key dependencies
   - Learn module responsibilities

## Advanced Techniques

### Comparing Blast Radius

Compare impact of different implementation choices:

```python
# Option 1: Modify service layer
impact_service = analyze_impact("myapp", "src/services/user.py", depth=2)

# Option 2: Modify model layer
impact_model = analyze_impact("myapp", "src/models/user.py", depth=2)

print(f"Service change: {len(impact_service['impact'])} files affected")
print(f"Model change: {len(impact_model['impact'])} files affected")

# Choose option with smaller blast radius
if len(impact_service['impact']) < len(impact_model['impact']):
    print("Recommendation: Modify service layer")
else:
    print("Recommendation: Modify model layer")
```

### Finding Critical Files

Identify files that many others depend on:

```python
import asyncio

async def find_critical_files(repo_id, files):
    """Find files with highest dependency count"""
    results = []

    for file in files:
        impact = await analyze_impact(repo_id, file, depth=1)
        results.append({
            "file": file,
            "dependents": len(impact["impact"])
        })

    # Sort by dependent count
    results.sort(key=lambda x: x["dependents"], reverse=True)

    print("Most critical files:")
    for item in results[:10]:
        print(f"{item['dependents']:3d} dependents: {item['file']}")

# Usage
all_files = [
    "src/database/connection.py",
    "src/auth/service.py",
    "src/config/settings.py",
    # ... more files
]

asyncio.run(find_critical_files("myapp", all_files))
```

### Dependency Visualization

Generate dependency graph for visualization:

```python
def build_dependency_graph(repo_id, root_file, depth=2):
    """Build graph structure for visualization"""
    result = analyze_impact(repo_id, root_file, depth)

    nodes = [{"id": root_file, "label": root_file, "type": "target"}]
    edges = []

    for item in result["impact"]:
        nodes.append({
            "id": item["path"],
            "label": item["path"],
            "type": "dependent"
        })
        edges.append({
            "from": item["path"],
            "to": root_file,
            "label": item["relationship"],
            "depth": item["depth"]
        })

    return {"nodes": nodes, "edges": edges}

# Export for visualization tools (D3.js, Cytoscape, etc.)
graph = build_dependency_graph("myapp", "src/auth/service.py", depth=2)

import json
with open("dependency_graph.json", "w") as f:
    json.dump(graph, f, indent=2)
```

### Impact Trending

Track how impact changes over time:

```python
import datetime
import json

def log_impact(repo_id, file_path):
    """Log impact analysis for trending"""
    result = analyze_impact(repo_id, file_path, depth=2)

    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "file": file_path,
        "total_dependents": len(result["impact"]),
        "critical": len([i for i in result["impact"] if i["score"] >= 0.9]),
        "medium": len([i for i in result["impact"] if 0.6 <= i["score"] < 0.9]),
        "low": len([i for i in result["impact"] if i["score"] < 0.6])
    }

    # Append to log file
    with open("impact_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# Run weekly
log_impact("myapp", "src/database/connection.py")
log_impact("myapp", "src/auth/service.py")
```

## Performance Optimization

### Caching Results

Cache impact analysis results for frequently checked files:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_impact_analysis(repo_id, file_path, depth):
    """Cache impact analysis results"""
    return analyze_impact(repo_id, file_path, depth)

# Use cached version
result = cached_impact_analysis("myapp", "src/auth/service.py", 2)
```

### Batch Analysis

Analyze multiple files efficiently:

```python
async def batch_analyze_impact(repo_id, file_paths, depth=2):
    """Analyze impact for multiple files"""
    import asyncio

    tasks = [
        analyze_impact_async(repo_id, path, depth)
        for path in file_paths
    ]

    results = await asyncio.gather(*tasks)

    return dict(zip(file_paths, results))

# Usage
files_to_check = [
    "src/auth/service.py",
    "src/models/user.py",
    "src/api/routes.py"
]

results = await batch_analyze_impact("myapp", files_to_check)
```

### Limiting Results

For very connected files, limit results:

```python
def analyze_impact_limited(repo_id, file_path, depth=2, max_results=50):
    """Limit impact analysis results"""
    result = analyze_impact(repo_id, file_path, depth)

    # Keep only highest-scored results
    impact = sorted(result["impact"], key=lambda x: x["score"], reverse=True)
    result["impact"] = impact[:max_results]
    result["total_count"] = len(impact)
    result["limited"] = len(impact) > max_results

    return result
```

## Troubleshooting

### No Dependencies Found

**Symptoms:**
```json
{
  "success": true,
  "impact": [],
  "total_count": 0
}
```

**Possible causes:**
1. File has no dependencies (rare but possible)
2. File not yet ingested
3. Symbol extraction incomplete
4. Relationships not created

**Solutions:**

1. **Check file exists:**
   ```cypher
   MATCH (f:File {path: 'your/file.py'})
   RETURN f
   ```

2. **Check relationships:**
   ```cypher
   MATCH (f:File {path: 'your/file.py'})<-[r]-()
   RETURN type(r), count(*)
   ```

3. **Re-ingest repository:**
   ```json
   {
     "local_path": "/path/to/repo",
     "mode": "full"
   }
   ```

### Too Many Results

**Symptoms:**
- 100+ dependent files
- Analysis takes > 1 second
- Hard to interpret results

**Solutions:**

1. **Reduce depth:**
   ```python
   # Instead of depth=3
   result = analyze_impact(repo_id, file_path, depth=2)
   ```

2. **Filter by score:**
   ```python
   high_impact = [i for i in result["impact"] if i["score"] >= 0.7]
   ```

3. **Focus on direct dependencies:**
   ```python
   direct = [i for i in result["impact"] if i["depth"] == 1]
   ```

### Unexpected Dependencies

**Symptoms:**
- Files listed that shouldn't be affected
- Missing expected dependencies

**Solutions:**

1. **Verify relationships in Neo4j:**
   ```cypher
   MATCH (f1:File {path: 'your/file.py'})<-[r]-(f2:File)
   RETURN f1.path, type(r), f2.path
   LIMIT 20
   ```

2. **Check for indirect paths:**
   ```cypher
   MATCH path = (f1:File {path: 'unexpected/file.py'})-[*..3]->
                (f2:File {path: 'your/file.py'})
   RETURN [n in nodes(path) | n.path] as dependency_chain
   LIMIT 5
   ```

3. **Re-ingest with full mode:**
   - May fix stale relationships

## Best Practices

### 1. Use Appropriate Depth

- **depth=1**: Quick checks, direct dependencies
- **depth=2**: Standard refactoring, most use cases (recommended)
- **depth=3**: Major changes, core modules
- **depth>3**: Rarely needed, architectural analysis only

### 2. Interpret Scores

- **Focus on score ≥ 0.9**: These files WILL be affected
- **Review score 0.6-0.8**: These files MIGHT be affected
- **Note score < 0.6**: Good to know, but low priority

### 3. Combine with Tests

Always run tests for affected files:

```python
impact_files = [i["path"] for i in result["impact"]]
test_files = [f for f in impact_files if "test" in f]
print(f"Run these tests: {test_files}")
```

### 4. Document Breaking Changes

For high-impact changes:

1. Document all affected files
2. Notify file owners
3. Provide migration guide
4. Add deprecation warnings
5. Plan gradual rollout

### 5. Regular Analysis

Run impact analysis regularly:

- Before major refactoring
- During architecture reviews
- When planning breaking changes
- During onboarding sessions

## Next Steps

Now that you understand impact analysis, learn about:

- **[Context Packing](context.md)**: Generate AI-friendly context bundles from impact analysis results
- **[Search](search.md)**: Find files to analyze with fulltext search

## Reference

### MCP Tool Definition

```json
{
  "name": "code_graph_impact",
  "description": "Analyze impact of changes to a file",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo_id": {
        "type": "string",
        "description": "Repository identifier"
      },
      "file_path": {
        "type": "string",
        "description": "File path to analyze"
      },
      "depth": {
        "type": "integer",
        "minimum": 1,
        "maximum": 5,
        "default": 2,
        "description": "Dependency traversal depth"
      }
    },
    "required": ["repo_id", "file_path"]
  }
}
```

### REST API Specification

**Endpoint:** `POST /api/v1/code-graph/impact`

**Request:**
```typescript
interface ImpactRequest {
  repo_id: string;     // Required: Repository ID
  file_path: string;   // Required: File to analyze
  depth?: number;      // Optional: Depth (default: 2, max: 5)
}
```

**Response:**
```typescript
interface ImpactResponse {
  success: boolean;
  target: {
    path: string;      // Target file path
    lang: string;      // Programming language
    repo_id: string;   // Repository ID
  };
  impact: Array<{
    type: string;      // Always "file"
    path: string;      // Dependent file path
    lang: string;      // Programming language
    repoId: string;    // Repository ID
    relationship: 'CALLS' | 'IMPORTS';  // Dependency type
    depth: number;     // Distance from target
    score: number;     // Impact score (0.5-1.0)
  }>;
  total_count: number; // Number of affected files
  depth: number;       // Requested depth
}
```

### Cypher Query

The underlying Cypher query (simplified):

```cypher
// Find target file
MATCH (target:File {repoId: $repo_id, path: $file_path})

// Find symbols in target file
OPTIONAL MATCH (target)<-[:DEFINED_IN]-(targetSymbol:Symbol)

// Find reverse CALLS
OPTIONAL MATCH (targetSymbol)<-[:CALLS*1..$depth]-(callerSymbol:Symbol)
OPTIONAL MATCH (callerSymbol)-[:DEFINED_IN]->(callerFile:File)

// Find reverse IMPORTS
OPTIONAL MATCH (target)<-[:IMPORTS*1..$depth]-(importerFile:File)

// Aggregate and score
WITH target,
     collect(DISTINCT callerFile) as callers,
     collect(DISTINCT importerFile) as importers

UNWIND (callers + importers) as impactedFile

RETURN DISTINCT
       impactedFile.path as path,
       impactedFile.lang as lang,
       // ... relationship type and score calculation
ORDER BY score DESC
LIMIT $limit
```
