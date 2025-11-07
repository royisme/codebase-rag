# Repository Ingestion Guide

## Introduction

Repository ingestion is the process of transforming your source code into a queryable graph database. This guide covers everything you need to know about ingesting repositories into Code Graph, from basic usage to advanced optimization techniques.

## Overview

When you ingest a repository, Code Graph:

1. **Scans** all source files matching configured patterns
2. **Detects** programming languages based on file extensions
3. **Reads** file content (for files < 100KB)
4. **Calculates** SHA hashes for change detection
5. **Creates** Neo4j nodes for repositories and files
6. **Establishes** relationships between files and repos
7. **Indexes** content for fulltext search

The entire process is automated and typically completes in seconds for most repositories.

## Ingestion Modes

Code Graph supports two ingestion modes, each optimized for different scenarios.

### Incremental Mode (Recommended)

**What it does:**
- Uses `git diff` to identify changed files
- Only processes files that have been added, modified, or deleted
- Updates existing nodes instead of recreating everything
- Preserves historical data and relationships

**Performance:**
- **60x faster** than full mode for typical changes
- Processes 10-100 files per second
- Sub-second updates for small commits
- Scales to very large repositories

**Requirements:**
- Repository must be a git repository
- `.git` directory must be present
- Git binary must be accessible

**When to use:**
- Regular updates during development
- CI/CD pipeline integration
- Daily/hourly sync operations
- After pulling new commits

**Example timing:**
- 10 changed files: < 1 second
- 100 changed files: 1-3 seconds
- 1,000 changed files: 10-30 seconds

### Full Mode

**What it does:**
- Scans all files in the repository
- Deletes existing data for the repository
- Recreates all nodes and relationships from scratch
- Complete re-ingestion

**Performance:**
- Slower than incremental mode
- Processes 100-500 files per second
- Time scales linearly with repository size

**Requirements:**
- None (works with any directory)
- Does not require git

**When to use:**
- First-time ingestion
- Non-git repositories
- After major refactoring
- Monthly full refresh (optional)
- When incremental mode produces errors

**Example timing:**
- 100 files: 5-10 seconds
- 1,000 files: 30-60 seconds
- 10,000 files: 5-10 minutes
- 50,000 files: 30-60 minutes

## Using MCP Tools

MCP (Model Context Protocol) is the recommended way to use Code Graph from AI assistants like Claude Desktop.

### Tool: code_graph_ingest_repo

#### Input Schema

```json
{
  "local_path": "/absolute/path/to/repository",
  "repo_url": "https://github.com/user/repo.git",  // optional
  "mode": "incremental"  // or "full"
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `local_path` | string | Yes | - | Absolute path to local repository |
| `repo_url` | string | No | `file://{local_path}` | Repository URL for identification |
| `mode` | string | No | `incremental` | Ingestion mode (`incremental` or `full`) |

#### Example: Basic Ingestion

```json
{
  "local_path": "/Users/developer/projects/myapp",
  "mode": "incremental"
}
```

**Response:**

```json
{
  "success": true,
  "repo_id": "myapp",
  "files_processed": 45,
  "files_added": 3,
  "files_updated": 42,
  "files_deleted": 0,
  "duration_ms": 1247,
  "mode": "incremental"
}
```

#### Example: Full Ingestion

```json
{
  "local_path": "/Users/developer/projects/myapp",
  "mode": "full"
}
```

**Response:**

```json
{
  "success": true,
  "repo_id": "myapp",
  "files_processed": 847,
  "total_files": 847,
  "duration_ms": 34521,
  "mode": "full"
}
```

#### Example: With Repository URL

```json
{
  "local_path": "/Users/developer/projects/myapp",
  "repo_url": "https://github.com/company/myapp.git",
  "mode": "incremental"
}
```

**Benefits of providing repo_url:**
- Better repository identification
- Useful for tracking multiple clones
- Enables future multi-repo features

#### Example: Claude Desktop Usage

In Claude Desktop, you can ingest a repository by saying:

```
Please ingest my repository at /Users/developer/projects/myapp
```

Claude will automatically call the MCP tool:

```json
{
  "name": "code_graph_ingest_repo",
  "arguments": {
    "local_path": "/Users/developer/projects/myapp",
    "mode": "incremental"
  }
}
```

### Error Handling

The tool returns structured errors when ingestion fails:

```json
{
  "success": false,
  "error": "Repository not found: /invalid/path",
  "error_type": "FileNotFoundError"
}
```

**Common errors:**

- `FileNotFoundError`: Path doesn't exist
- `PermissionError`: No read access to directory
- `GitError`: Not a git repository (when using incremental mode)
- `Neo4jConnectionError`: Database connection failed

## Using REST API

For HTTP clients and custom integrations, use the REST API.

### Endpoint: POST /api/v1/code-graph/ingest

#### Request Body

```json
{
  "local_path": "/path/to/repository",
  "repo_url": "https://github.com/user/repo.git",
  "mode": "incremental",
  "include_patterns": ["**/*.py", "**/*.js"],  // optional
  "exclude_patterns": ["**/node_modules/**", "**/.git/**"]  // optional
}
```

#### Response

```json
{
  "success": true,
  "task_id": "ing-20231215-143022-a3f8c2d1",
  "message": "Ingestion started",
  "repo_id": "myapp"
}
```

#### Example: cURL

```bash
curl -X POST http://localhost:8000/api/v1/code-graph/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "local_path": "/Users/developer/projects/myapp",
    "mode": "incremental"
  }'
```

#### Example: Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/code-graph/ingest",
    json={
        "local_path": "/Users/developer/projects/myapp",
        "mode": "incremental"
    }
)

result = response.json()
print(f"Task ID: {result['task_id']}")
```

#### Example: JavaScript fetch

```javascript
const response = await fetch('http://localhost:8000/api/v1/code-graph/ingest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    local_path: '/Users/developer/projects/myapp',
    mode: 'incremental'
  })
});

const result = await response.json();
console.log('Task ID:', result.task_id);
```

### Monitoring Progress

Large repositories return a task ID for async processing. Monitor progress using:

#### GET /api/v1/tasks/{task_id}

```bash
curl http://localhost:8000/api/v1/tasks/ing-20231215-143022-a3f8c2d1
```

**Response:**

```json
{
  "task_id": "ing-20231215-143022-a3f8c2d1",
  "status": "running",
  "progress": 45,
  "total": 100,
  "message": "Processing file 45/100: src/services/auth.py",
  "started_at": "2023-12-15T14:30:22Z",
  "updated_at": "2023-12-15T14:30:45Z"
}
```

**Status values:**
- `pending`: Queued, not started yet
- `running`: Currently processing
- `completed`: Successfully finished
- `failed`: Error occurred

#### Server-Sent Events (SSE)

For real-time updates:

```bash
curl -N http://localhost:8000/api/v1/sse/task/ing-20231215-143022-a3f8c2d1
```

**Stream output:**

```
data: {"status": "running", "progress": 10, "message": "Scanning files..."}

data: {"status": "running", "progress": 50, "message": "Processing file 50/100"}

data: {"status": "completed", "progress": 100, "message": "Ingestion complete"}
```

## File Patterns

Control which files are ingested using include and exclude patterns.

### Default Patterns

**Include patterns (default):**

```python
[
    "**/*.py",      # Python
    "**/*.ts",      # TypeScript
    "**/*.tsx",     # TypeScript React
    "**/*.js",      # JavaScript
    "**/*.jsx",     # JavaScript React
    "**/*.go",      # Go
    "**/*.rs",      # Rust
    "**/*.java",    # Java
    "**/*.cpp",     # C++
    "**/*.c",       # C
    "**/*.h",       # C/C++ headers
    "**/*.cs",      # C#
    "**/*.rb",      # Ruby
    "**/*.php",     # PHP
    "**/*.swift",   # Swift
    "**/*.kt",      # Kotlin
    "**/*.scala"    # Scala
]
```

**Exclude patterns (default):**

```python
[
    "**/.git/**",
    "**/node_modules/**",
    "**/venv/**",
    "**/env/**",
    "**/__pycache__/**",
    "**/build/**",
    "**/dist/**",
    "**/.next/**",
    "**/target/**",
    "**/*.min.js",
    "**/*.bundle.js"
]
```

### Custom Patterns

Override default patterns with custom ones:

```json
{
  "local_path": "/path/to/repo",
  "include_patterns": [
    "**/*.py",
    "**/*.yaml",
    "**/*.json"
  ],
  "exclude_patterns": [
    "**/tests/**",
    "**/docs/**"
  ]
}
```

### Pattern Syntax

Patterns use glob syntax:

- `*`: Matches any characters except `/`
- `**`: Matches any characters including `/`
- `?`: Matches single character
- `[abc]`: Matches any character in brackets
- `{a,b}`: Matches either `a` or `b`

**Examples:**

```python
"src/**/*.py"           # All Python files in src/ and subdirectories
"**/test_*.py"          # All test files
"**/{models,views}/**"  # Files in models or views directories
"**/api/*.ts"           # TypeScript files directly in api/
"**/*.{js,ts}"          # JavaScript or TypeScript files
```

## Language Detection

Files are automatically categorized by language based on extension.

### Supported Languages

| Extension | Language | Symbol Extraction |
|-----------|----------|-------------------|
| `.py` | Python | ✅ Functions, Classes |
| `.ts`, `.tsx` | TypeScript | ⚠️ Basic |
| `.js`, `.jsx` | JavaScript | ⚠️ Basic |
| `.go` | Go | ⚠️ Basic |
| `.rs` | Rust | ⚠️ Basic |
| `.java` | Java | ⚠️ Basic |
| `.cpp`, `.c`, `.h` | C/C++ | ⚠️ Basic |
| `.cs` | C# | ⚠️ Basic |
| `.rb` | Ruby | ⚠️ Basic |
| `.php` | PHP | ⚠️ Basic |
| `.swift` | Swift | ⚠️ Basic |
| `.kt` | Kotlin | ⚠️ Basic |
| `.scala` | Scala | ⚠️ Basic |

**Symbol extraction status:**
- ✅ Full support: Complete AST parsing
- ⚠️ Basic: File-level indexing only
- ❌ Not supported: Treated as unknown

**Note:** In v0.7, only file-level indexing is implemented. Symbol extraction is planned for v0.8.

### Unknown Files

Files with unsupported extensions are still indexed:

- Path is indexed for search
- File size is recorded
- Language is marked as `unknown`
- Content is not indexed
- No symbol extraction

**Example:** A `.xyz` file is still searchable by filename but not by content.

## Repository Identification

Code Graph needs a unique identifier for each repository.

### Auto-generated repo_id

If you don't provide `repo_url`, the system generates `repo_id` from:

1. **Last directory name**: `/path/to/myapp` → `myapp`
2. **Git remote URL**: If available, extracts from `git remote -v`
3. **Fallback**: Uses directory name

### Explicit repo_id

For better control, provide `repo_url`:

```json
{
  "local_path": "/Users/dev/work/project",
  "repo_url": "https://github.com/company/project.git"
}
```

Extracted `repo_id`: `project`

### Multiple Clones

You can ingest multiple clones of the same repository:

```json
// Clone 1: Main branch
{
  "local_path": "/repos/myapp-main",
  "repo_url": "https://github.com/company/myapp.git"
}

// Clone 2: Feature branch
{
  "local_path": "/repos/myapp-feature",
  "repo_url": "https://github.com/company/myapp.git#feature-branch"
}
```

**Note:** Currently, both clones will share the same `repo_id`. Multi-branch support is planned for v0.9.

## Performance Optimization

### Small Repositories (<1,000 files)

**Recommended settings:**
- Mode: Either `full` or `incremental`
- Frequency: After every commit
- Integration: Git hooks or CI/CD

**Performance:**
- Full mode: 5-10 seconds
- Incremental: <1 second

**Strategy:**
- Simple workflow, any mode works fine
- Run after every `git pull`
- Automate with pre-commit hooks

### Medium Repositories (1,000-10,000 files)

**Recommended settings:**
- Mode: `incremental` (always)
- Frequency: After major changes
- Integration: CI/CD on push

**Performance:**
- Full mode: 30-60 seconds
- Incremental: 1-5 seconds

**Strategy:**
- Always use incremental mode
- Run on every push to main branch
- Full re-ingestion weekly (optional)
- Exclude large generated files

### Large Repositories (>10,000 files)

**Recommended settings:**
- Mode: `incremental` (mandatory)
- Frequency: Scheduled updates
- Integration: Background jobs

**Performance:**
- Full mode: 5-30 minutes
- Incremental: 5-15 seconds

**Strategy:**
- Never use full mode in regular workflow
- Schedule incremental every hour/day
- Full re-ingestion monthly
- Aggressive exclusion patterns
- Monitor Neo4j memory usage

### Optimization Checklist

✅ Use incremental mode for regular updates
✅ Exclude build directories (node_modules, dist, build)
✅ Exclude generated files (*.min.js, *.bundle.js)
✅ Keep files under 100KB for content indexing
✅ Run ingestion during off-peak hours
✅ Monitor Neo4j disk usage
✅ Schedule full re-ingestion monthly

## CI/CD Integration

Automate ingestion in your CI/CD pipeline.

### GitHub Actions

```yaml
name: Update Code Graph

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Ingest to Code Graph
        run: |
          curl -X POST ${{ secrets.CODE_GRAPH_URL }}/api/v1/code-graph/ingest \
            -H "Content-Type: application/json" \
            -d '{
              "local_path": "${{ github.workspace }}",
              "repo_url": "${{ github.repository }}",
              "mode": "incremental"
            }'
```

### GitLab CI

```yaml
update-code-graph:
  stage: deploy
  script:
    - |
      curl -X POST ${CODE_GRAPH_URL}/api/v1/code-graph/ingest \
        -H "Content-Type: application/json" \
        -d "{
          \"local_path\": \"${CI_PROJECT_DIR}\",
          \"repo_url\": \"${CI_REPOSITORY_URL}\",
          \"mode\": \"incremental\"
        }"
  only:
    - main
```

### Git Hooks

**Post-merge hook** (`.git/hooks/post-merge`):

```bash
#!/bin/bash
# Update Code Graph after pulling changes

curl -X POST http://localhost:8000/api/v1/code-graph/ingest \
  -H "Content-Type: application/json" \
  -d "{
    \"local_path\": \"$(pwd)\",
    \"mode\": \"incremental\"
  }" &
```

Make executable:

```bash
chmod +x .git/hooks/post-merge
```

### Docker Compose

Add ingestion to your Docker Compose setup:

```yaml
services:
  code-graph:
    image: royisme/codebase-rag:minimal
    volumes:
      - ./:/workspace
    environment:
      - AUTO_INGEST=true
      - INGEST_PATH=/workspace
      - INGEST_MODE=incremental
```

## Troubleshooting

### Common Issues

#### Issue: "Not a git repository"

**Error:**
```json
{
  "success": false,
  "error": "Not a git repository: /path/to/repo"
}
```

**Solutions:**
1. Check `.git` directory exists
2. Use `mode: "full"` instead of `incremental`
3. Initialize git: `git init`

#### Issue: "Permission denied"

**Error:**
```json
{
  "success": false,
  "error": "PermissionError: Permission denied: '/path/to/repo'"
}
```

**Solutions:**
1. Check directory permissions: `ls -ld /path/to/repo`
2. Make directory readable: `chmod -R 755 /path/to/repo`
3. Run with appropriate user permissions

#### Issue: Slow ingestion

**Symptoms:**
- Full mode takes > 5 minutes
- Incremental mode takes > 30 seconds
- High CPU usage

**Solutions:**
1. Add more exclude patterns
2. Check Neo4j memory settings
3. Reduce include patterns
4. Skip large binary files
5. Increase Neo4j heap size

#### Issue: Files not appearing in search

**Symptoms:**
- Ingestion succeeds
- File count looks correct
- But search returns no results

**Solutions:**
1. Check fulltext index exists:
   ```cypher
   SHOW INDEXES
   ```
2. Rebuild fulltext index:
   ```cypher
   DROP INDEX file_text IF EXISTS;
   CREATE FULLTEXT INDEX file_text FOR (f:File) ON EACH [f.path, f.lang];
   ```
3. Wait for index to build (may take 1-2 minutes)
4. Verify files have content: `MATCH (f:File) RETURN f.path, f.content LIMIT 10`

#### Issue: Duplicate files

**Symptoms:**
- Same file appears multiple times
- Ingestion reports more files than exist

**Possible causes:**
1. Multiple ingestions with different `repo_id`
2. Case-sensitive path issues (Windows/Mac)
3. Symbolic links creating duplicates

**Solutions:**
1. Delete and re-ingest:
   ```cypher
   MATCH (r:Repo {id: 'myapp'})
   DETACH DELETE r
   ```
2. Use consistent `repo_url` parameter
3. Add symlink exclusions to patterns

#### Issue: Out of memory

**Symptoms:**
- Neo4j crashes during ingestion
- Java heap space errors
- System becomes unresponsive

**Solutions:**
1. Increase Neo4j heap size in `docker-compose.yml`:
   ```yaml
   environment:
     - NEO4J_dbms_memory_heap_initial__size=1G
     - NEO4J_dbms_memory_heap_max__size=2G
   ```
2. Use incremental mode instead of full
3. Process repository in batches
4. Exclude large files/directories

### Debug Mode

Enable debug logging for detailed ingestion information:

**Environment variable:**
```bash
export LOG_LEVEL=DEBUG
```

**Docker Compose:**
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

**Output example:**
```
DEBUG - Scanning directory: /path/to/repo
DEBUG - Found 1247 files matching patterns
DEBUG - Processing file 1/1247: src/main.py
DEBUG - File size: 4523 bytes, language: python
DEBUG - Creating node: File {path: src/main.py, lang: python}
DEBUG - Created relationship: (File)-[:IN_REPO]->(Repo)
```

## Best Practices

### 1. Choose the Right Mode

- **Incremental for:**
  - Active development
  - Frequent updates
  - CI/CD pipelines
  - Large repositories

- **Full for:**
  - First-time setup
  - Non-git repositories
  - Major refactoring
  - Monthly refreshes

### 2. Optimize Patterns

```json
{
  "include_patterns": [
    "src/**/*.{py,ts,js}",     // Source code only
    "lib/**/*.{py,ts,js}"      // Library code
  ],
  "exclude_patterns": [
    "**/node_modules/**",      // Dependencies
    "**/venv/**",              // Virtual env
    "**/__pycache__/**",       // Python cache
    "**/build/**",             // Build output
    "**/dist/**",              // Distribution
    "**/*.test.{ts,js}",       // Test files (optional)
    "**/*.min.js"              // Minified files
  ]
}
```

### 3. Schedule Regular Updates

```bash
# Cron job: Update every hour
0 * * * * curl -X POST http://localhost:8000/api/v1/code-graph/ingest \
  -H "Content-Type: application/json" \
  -d '{"local_path": "/path/to/repo", "mode": "incremental"}'
```

### 4. Monitor Ingestion

Track ingestion metrics:

```cypher
// Check repository stats
MATCH (r:Repo {id: 'myapp'})
OPTIONAL MATCH (r)<-[:IN_REPO]-(f:File)
RETURN r.id as repo_id,
       r.file_count as expected,
       count(f) as actual,
       r.created as created
```

### 5. Verify Data Quality

```cypher
// Check for files without content
MATCH (f:File)
WHERE f.content IS NULL AND f.size < 100000
RETURN f.path, f.size, f.lang
LIMIT 10

// Check language distribution
MATCH (f:File)
RETURN f.lang as language, count(*) as count
ORDER BY count DESC
```

## Advanced Topics

### Custom Ingestion Script

For complex workflows, use the Python API directly:

```python
from src.codebase_rag.services.code import graph_service
from src.codebase_rag.services.code import CodeIngestor

# Initialize
await graph_service.connect()
ingestor = CodeIngestor(graph_service)

# Scan files
files = ingestor.scan_files(
    repo_path="/path/to/repo",
    include_globs=["**/*.py", "**/*.js"],
    exclude_globs=["**/node_modules/**"]
)

# Ingest
result = ingestor.ingest_files(
    repo_id="myapp",
    files=files
)

print(f"Ingested {result['files_processed']} files")
```

### Batch Ingestion

Ingest multiple repositories:

```python
repositories = [
    {"path": "/repos/app1", "url": "https://github.com/org/app1"},
    {"path": "/repos/app2", "url": "https://github.com/org/app2"},
    {"path": "/repos/app3", "url": "https://github.com/org/app3"},
]

for repo in repositories:
    result = await ingest_repo(
        local_path=repo["path"],
        repo_url=repo["url"],
        mode="incremental"
    )
    print(f"Ingested {repo['url']}: {result['files_processed']} files")
```

## Next Steps

Now that your repository is ingested, learn how to search and analyze it:

- **[Search and Discovery](search.md)**: Find relevant files using fulltext search
- **[Impact Analysis](impact.md)**: Understand code dependencies and blast radius
- **[Context Packing](context.md)**: Generate AI-friendly context bundles

## Reference

### MCP Tool Definition

```json
{
  "name": "code_graph_ingest_repo",
  "description": "Ingest a code repository into the graph database",
  "inputSchema": {
    "type": "object",
    "properties": {
      "local_path": {
        "type": "string",
        "description": "Local repository path"
      },
      "repo_url": {
        "type": "string",
        "description": "Repository URL (optional)"
      },
      "mode": {
        "type": "string",
        "enum": ["full", "incremental"],
        "default": "incremental",
        "description": "Ingestion mode"
      }
    },
    "required": ["local_path"]
  }
}
```

### REST API Specification

**Endpoint:** `POST /api/v1/code-graph/ingest`

**Request:**
```typescript
interface IngestRequest {
  local_path: string;           // Required
  repo_url?: string;            // Optional
  mode?: 'full' | 'incremental'; // Default: 'incremental'
  include_patterns?: string[];  // Optional
  exclude_patterns?: string[];  // Optional
}
```

**Response:**
```typescript
interface IngestResponse {
  success: boolean;
  task_id?: string;
  repo_id?: string;
  files_processed?: number;
  duration_ms?: number;
  error?: string;
}
```
