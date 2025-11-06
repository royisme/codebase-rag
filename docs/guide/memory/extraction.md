# Automatic Memory Extraction Guide (v0.7)

Comprehensive guide to automatic memory extraction features. Learn how to extract memories from conversations, git commits, code comments, and entire repositories.

## Table of Contents

- [Extraction Overview](#extraction-overview)
- [Conversation Extraction](#conversation-extraction)
- [Git Commit Extraction](#git-commit-extraction)
- [Code Comment Mining](#code-comment-mining)
- [Query-Based Suggestions](#query-based-suggestions)
- [Batch Repository Extraction](#batch-repository-extraction)
- [Integration Patterns](#integration-patterns)
- [Configuration](#configuration)
- [Best Practices](#best-practices)

---

## Extraction Overview

Memory Store v0.7 introduces automatic extraction capabilities that use LLM analysis to identify and extract important project knowledge from various sources.

### Extraction Sources

1. **Conversations** - AI conversations with users
2. **Git Commits** - Commit messages and file changes
3. **Code Comments** - TODO, FIXME, NOTE, DECISION markers
4. **Knowledge Queries** - Q&A interactions
5. **Repository Batch** - Comprehensive codebase analysis

### How It Works

```
Source Content
     ↓
LLM Analysis
     ↓
Memory Extraction
     ↓
Confidence Scoring
     ↓
Auto-save (optional) or Suggestions
```

**Confidence Threshold**: Memories with confidence ≥ 0.7 can be auto-saved

### Key Features

- **LLM-Powered**: Uses project's configured LLM for intelligent analysis
- **Confidence Scores**: Each extraction includes confidence rating
- **Auto-Save Option**: High-confidence memories can be saved automatically
- **Structured Output**: Extracts proper memory type, importance, tags
- **Batch Processing**: Handle multiple sources efficiently

---

## Conversation Extraction

### Overview

Extract memories from AI-user conversations by analyzing dialogue for important decisions, preferences, and learnings.

**Best For**:
- Design discussions
- Technical decision-making conversations
- Problem-solving sessions
- Architecture planning discussions

### Basic Usage

**MCP Tool**:
```python
extract_from_conversation(
    project_id="my-project",
    conversation=[
        {
            "role": "user",
            "content": "Should we use Redis or Memcached for caching?"
        },
        {
            "role": "assistant",
            "content": "I recommend Redis because it supports data persistence, has richer data structures, and provides better tooling. Redis also allows you to use it as both cache and message queue."
        },
        {
            "role": "user",
            "content": "Great, let's go with Redis then."
        }
    ],
    auto_save=True
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/extract/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "conversation": [
      {"role": "user", "content": "Should we use Redis or Memcached?"},
      {"role": "assistant", "content": "I recommend Redis because..."}
    ],
    "auto_save": true
  }'
```

**Python Service**:
```python
from services.memory_extractor import memory_extractor

result = await memory_extractor.extract_from_conversation(
    project_id="my-project",
    conversation=[
        {"role": "user", "content": "Should we use Redis or Memcached?"},
        {"role": "assistant", "content": "I recommend Redis..."}
    ],
    auto_save=True
)

print(f"Auto-saved: {result['auto_saved_count']} memories")
print(f"Suggestions: {len(result['suggestions'])} memories")
```

**Response**:
```json
{
  "success": true,
  "extracted_memories": [
    {
      "type": "decision",
      "title": "Use Redis for caching",
      "content": "Decided to use Redis over Memcached for caching layer",
      "reason": "Redis supports persistence, richer data structures, and better tooling",
      "tags": ["cache", "redis", "infrastructure"],
      "importance": 0.8,
      "memory_id": "550e8400-...",
      "auto_saved": true
    }
  ],
  "auto_saved_count": 1,
  "suggestions": [],
  "total_extracted": 1
}
```

### Advanced: Conversation Analysis

**Multi-turn Discussions**:
```python
conversation = [
    {"role": "user", "content": "How should we handle user authentication?"},
    {"role": "assistant", "content": "For your use case, I'd recommend JWT tokens with refresh token rotation..."},
    {"role": "user", "content": "What about session storage?"},
    {"role": "assistant", "content": "For JWTs, you don't need server-side sessions. Store tokens in httpOnly cookies..."},
    {"role": "user", "content": "Should we use Redis for token blacklisting?"},
    {"role": "assistant", "content": "Yes, Redis is perfect for token blacklisting with TTL support..."}
]

result = await memory_extractor.extract_from_conversation(
    project_id="web-app",
    conversation=conversation,
    auto_save=False  # Review before saving
)

# Review suggestions
for suggestion in result['suggestions']:
    print(f"Type: {suggestion['type']}")
    print(f"Title: {suggestion['title']}")
    print(f"Confidence: {suggestion['confidence']}")
    print(f"Importance: {suggestion['importance']}")
    print()

# Manually save high-value suggestions
for suggestion in result['suggestions']:
    if suggestion['confidence'] >= 0.8:
        await memory_store.add_memory(
            project_id="web-app",
            **suggestion
        )
```

### Extraction Quality

**What Gets Extracted**:
- ✅ Technical decisions and rationale
- ✅ Technology choices with reasoning
- ✅ Architectural patterns discussed
- ✅ Problems and solutions
- ✅ Best practices agreed upon
- ✅ Security considerations

**What Doesn't Get Extracted**:
- ❌ Casual greetings
- ❌ Clarifying questions
- ❌ Routine code snippets
- ❌ Trivial preferences
- ❌ Temporary experiments

### Auto-Save vs Manual Review

**Auto-Save (auto_save=true)**:
```python
# Automatically save memories with confidence >= 0.7
result = await memory_extractor.extract_from_conversation(
    project_id="my-project",
    conversation=conversation,
    auto_save=True
)

# Only high-confidence memories are saved
print(f"Auto-saved: {result['auto_saved_count']}")
```

**Manual Review (auto_save=false)**:
```python
# Get suggestions, review before saving
result = await memory_extractor.extract_from_conversation(
    project_id="my-project",
    conversation=conversation,
    auto_save=False
)

# Review each suggestion
for suggestion in result['suggestions']:
    print(f"Review: {suggestion['title']}")
    print(f"Confidence: {suggestion['confidence']}")

    # Manually save selected ones
    if user_approves(suggestion):
        await memory_store.add_memory(
            project_id="my-project",
            memory_type=suggestion['type'],
            title=suggestion['title'],
            content=suggestion['content'],
            reason=suggestion['reason'],
            tags=suggestion['tags'],
            importance=suggestion['importance']
        )
```

---

## Git Commit Extraction

### Overview

Extract memories from git commits by analyzing commit messages, changed files, and commit types.

**Best For**:
- Feature additions (decisions)
- Bug fixes (experiences)
- Breaking changes (critical decisions)
- Refactoring (experiences/conventions)

### Basic Usage

**MCP Tool**:
```python
extract_from_git_commit(
    project_id="my-project",
    commit_sha="abc123def456",
    commit_message="feat: add JWT authentication\n\nImplemented JWT-based authentication for API endpoints. Tokens expire after 24 hours with refresh token support.",
    changed_files=[
        "src/auth/jwt.py",
        "src/middleware/auth.py",
        "tests/test_auth.py"
    ],
    auto_save=True
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/extract/commit \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "commit_sha": "abc123def456",
    "commit_message": "feat: add JWT authentication",
    "changed_files": ["src/auth/jwt.py", "src/middleware/auth.py"],
    "auto_save": true
  }'
```

**Python Service**:
```python
from services.memory_extractor import memory_extractor

result = await memory_extractor.extract_from_git_commit(
    project_id="my-project",
    commit_sha="abc123def456",
    commit_message="feat: add JWT authentication\n\nImplemented JWT for API",
    changed_files=["src/auth/jwt.py"],
    auto_save=True
)

print(f"Commit type: {result['commit_type']}")
print(f"Extracted: {result['auto_saved_count']} memories")
```

**Response**:
```json
{
  "success": true,
  "extracted_memories": [
    {
      "type": "decision",
      "title": "Add JWT authentication",
      "content": "Implemented JWT-based authentication for API endpoints with 24-hour token expiry and refresh token support",
      "reason": "Provide secure, stateless authentication for API clients",
      "tags": ["auth", "jwt", "security", "feat"],
      "importance": 0.8,
      "memory_id": "550e8400-...",
      "metadata": {
        "source": "git_commit",
        "commit_sha": "abc123def456",
        "changed_files": ["src/auth/jwt.py", "src/middleware/auth.py"],
        "confidence": 0.85
      }
    }
  ],
  "auto_saved_count": 1,
  "suggestions": [],
  "commit_type": "feat"
}
```

### Commit Type Classification

The extractor automatically classifies commits:

| Commit Type | Memory Type | Importance Range | Example |
|-------------|-------------|------------------|---------|
| `feat` | decision | 0.7-0.9 | "feat: add OAuth support" |
| `fix` | experience | 0.5-0.8 | "fix: resolve Redis timeout in Docker" |
| `refactor` | experience | 0.4-0.7 | "refactor: improve auth middleware" |
| `docs` | convention | 0.3-0.6 | "docs: add API naming conventions" |
| `breaking` | decision | 0.9-1.0 | "feat!: migrate to PostgreSQL" |
| `chore` | note | 0.2-0.4 | "chore: update dependencies" |

### Integration with Git Hooks

**Post-commit hook** (.git/hooks/post-commit):
```bash
#!/bin/bash

# Get commit details
COMMIT_SHA=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)

# Extract memories
curl -X POST http://localhost:8000/api/v1/memory/extract/commit \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"my-project\",
    \"commit_sha\": \"$COMMIT_SHA\",
    \"commit_message\": \"$COMMIT_MSG\",
    \"changed_files\": [$(echo $CHANGED_FILES | sed 's/ /", "/g' | sed 's/^/"/;s/$/"/')]
  }"
```

### Batch Git History Analysis

```python
import subprocess
from pathlib import Path

async def analyze_git_history(
    project_id: str,
    repo_path: str,
    max_commits: int = 50
):
    """Analyze recent git commits and extract memories"""

    # Get recent commits
    result = subprocess.run(
        ["git", "log", f"-{max_commits}", "--pretty=format:%H|%s|%b"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )

    extracted_count = 0

    for line in result.stdout.split('\n'):
        if not line.strip():
            continue

        parts = line.split('|', 2)
        commit_sha = parts[0]
        subject = parts[1]
        body = parts[2] if len(parts) > 2 else ""
        commit_message = f"{subject}\n{body}".strip()

        # Get changed files
        files_result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        changed_files = files_result.stdout.strip().split('\n')

        # Extract memories
        result = await memory_extractor.extract_from_git_commit(
            project_id=project_id,
            commit_sha=commit_sha,
            commit_message=commit_message,
            changed_files=changed_files,
            auto_save=True
        )

        if result.get('success'):
            extracted_count += result.get('auto_saved_count', 0)

    print(f"Analyzed {max_commits} commits, extracted {extracted_count} memories")
    return extracted_count

# Usage
await analyze_git_history("my-project", "/path/to/repo", max_commits=100)
```

---

## Code Comment Mining

### Overview

Extract memories from code comments by identifying special markers: TODO, FIXME, NOTE, DECISION, IMPORTANT, BUG.

**Best For**:
- TODOs and future work
- Known bugs and issues
- Important implementation notes
- Documented decisions

### Basic Usage

**MCP Tool**:
```python
extract_from_code_comments(
    project_id="my-project",
    file_path="/path/to/project/src/service.py"
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/extract/comments \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "file_path": "/path/to/project/src/service.py"
  }'
```

**Python Service**:
```python
from services.memory_extractor import memory_extractor

result = await memory_extractor.extract_from_code_comments(
    project_id="my-project",
    file_path="/path/to/project/src/service.py"
)

print(f"Total comments: {result['total_comments']}")
print(f"Extracted: {result['total_extracted']} memories")
```

**Response**:
```json
{
  "success": true,
  "extracted_memories": [
    {
      "type": "plan",
      "title": "Add rate limiting to API endpoints",
      "content": "TODO: Add rate limiting to API endpoints",
      "importance": 0.4,
      "tags": ["todo", "py"],
      "memory_id": "550e8400-...",
      "line": 45
    },
    {
      "type": "experience",
      "title": "Redis connection pool needs minimum 10 connections",
      "content": "FIXME: Redis connection pool needs minimum 10 connections",
      "importance": 0.6,
      "tags": ["bug", "fixme", "py"],
      "memory_id": "550e8400-...",
      "line": 78
    }
  ],
  "total_comments": 15,
  "total_extracted": 2
}
```

### Comment Marker Mapping

| Marker | Memory Type | Importance | Use Case |
|--------|-------------|------------|----------|
| `TODO:` | plan | 0.4 | Future work, planned improvements |
| `FIXME:` | experience | 0.6 | Known bugs, issues to fix |
| `BUG:` | experience | 0.6 | Documented bugs |
| `NOTE:` | convention | 0.5 | Important notes, gotchas |
| `IMPORTANT:` | convention | 0.5 | Critical information |
| `DECISION:` | decision | 0.7 | Documented decisions |

### Example Code with Markers

**Python**:
```python
class UserService:
    def __init__(self):
        # DECISION: Using Redis for session storage instead of database
        # Reason: Need sub-millisecond latency for session lookups
        self.redis_client = RedisClient()

        # NOTE: Connection pool must have minimum 10 connections
        # Lower values cause connection timeout under load
        self.pool_size = 10

    def authenticate(self, token: str):
        # TODO: Add refresh token rotation for better security
        # This will require database changes and client updates
        pass

    def get_user(self, user_id: int):
        # FIXME: Cache invalidation doesn't work for user updates
        # Need to implement pub/sub pattern for cache invalidation
        return self._fetch_from_db(user_id)
```

**JavaScript**:
```javascript
class AuthService {
  constructor() {
    // DECISION: Using JWT with 15-minute expiry
    // Short expiry reduces risk of token theft
    this.tokenExpiry = 15 * 60; // 15 minutes

    // TODO: Implement token blacklist for logout
    // Will need Redis for fast blacklist lookups
  }

  async verifyToken(token) {
    // IMPORTANT: Must check token expiry AND signature
    // Checking only signature is a security vulnerability
    const decoded = jwt.verify(token, SECRET);

    // FIXME: Token validation doesn't handle clock skew
    // Need to add leeway parameter to jwt.verify()
    return decoded;
  }
}
```

### Batch Comment Extraction

```python
from pathlib import Path

async def extract_from_all_files(
    project_id: str,
    repo_path: str,
    file_patterns: list = ["*.py", "*.js", "*.ts"]
):
    """Extract comments from all matching files"""

    repo = Path(repo_path)
    total_extracted = 0

    for pattern in file_patterns:
        for file_path in repo.rglob(pattern):
            try:
                result = await memory_extractor.extract_from_code_comments(
                    project_id=project_id,
                    file_path=str(file_path)
                )

                if result.get('success'):
                    count = result.get('total_extracted', 0)
                    total_extracted += count
                    print(f"{file_path.name}: {count} memories")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    print(f"Total extracted: {total_extracted} memories")
    return total_extracted

# Usage
await extract_from_all_files(
    "my-project",
    "/path/to/repo",
    file_patterns=["*.py", "*.js", "*.ts", "*.java"]
)
```

---

## Query-Based Suggestions

### Overview

Analyze knowledge base Q&A interactions and suggest creating memories for important information.

**Best For**:
- Frequently asked questions
- Non-obvious solutions
- Architectural information
- Important conventions

### Basic Usage

**MCP Tool**:
```python
suggest_memory_from_query(
    project_id="my-project",
    query="How does the authentication system work?",
    answer="The system uses JWT tokens with refresh token rotation. Access tokens expire after 15 minutes, refresh tokens after 7 days. Tokens are stored in httpOnly cookies to prevent XSS attacks."
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "query": "How does authentication work?",
    "answer": "The system uses JWT tokens with refresh token rotation..."
  }'
```

**Python Service**:
```python
from services.memory_extractor import memory_extractor

result = await memory_extractor.suggest_memory_from_query(
    project_id="my-project",
    query="How does the authentication system work?",
    answer="The system uses JWT tokens with refresh token rotation..."
)

if result['should_save']:
    suggested = result['suggested_memory']
    print(f"Suggested: {suggested['title']}")
    print(f"Type: {suggested['type']}")
    print(f"Importance: {suggested['importance']}")

    # Manually save if approved
    await memory_store.add_memory(
        project_id="my-project",
        **suggested
    )
```

**Response (should save)**:
```json
{
  "success": true,
  "should_save": true,
  "suggested_memory": {
    "type": "note",
    "title": "Authentication system uses JWT with refresh tokens",
    "content": "System uses JWT tokens with refresh token rotation. Access tokens: 15min expiry. Refresh tokens: 7 days. Stored in httpOnly cookies for XSS protection",
    "reason": "Core authentication architecture - important for future development",
    "tags": ["auth", "jwt", "security"],
    "importance": 0.7
  },
  "query": "How does the authentication system work?",
  "answer_excerpt": "The system uses JWT tokens with..."
}
```

**Response (should not save)**:
```json
{
  "success": true,
  "should_save": false,
  "reason": "Routine question about standard library function - not project-specific",
  "query": "How do I use datetime.now()?"
}
```

### Integration with Knowledge Service

```python
from services.neo4j_knowledge_service import knowledge_service
from services.memory_extractor import memory_extractor

async def query_with_memory_suggestion(
    project_id: str,
    query: str
):
    """Query knowledge base and suggest saving as memory if important"""

    # Query knowledge base
    result = await knowledge_service.query_knowledge(query)
    answer = result.get('answer', '')

    # Suggest memory
    suggestion = await memory_extractor.suggest_memory_from_query(
        project_id=project_id,
        query=query,
        answer=answer
    )

    # Auto-save if highly important
    if suggestion.get('should_save'):
        suggested = suggestion['suggested_memory']

        if suggested['importance'] >= 0.8:
            # Auto-save critical information
            await memory_store.add_memory(
                project_id=project_id,
                **suggested,
                metadata={'source': 'auto_query'}
            )
            print(f"Auto-saved memory: {suggested['title']}")

    return {
        'answer': answer,
        'memory_suggested': suggestion.get('should_save', False)
    }
```

---

## Batch Repository Extraction

### Overview

Comprehensive analysis of entire repository: git commits, code comments, and documentation files.

**Best For**:
- Initial project setup
- Onboarding AI agents
- Knowledge base bootstrapping
- Project audits

### Basic Usage

**MCP Tool**:
```python
batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repository",
    max_commits=50,
    file_patterns=["*.py", "*.js", "*.ts"]
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/extract/batch \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "repo_path": "/path/to/repository",
    "max_commits": 50,
    "file_patterns": ["*.py", "*.js"]
  }'
```

**Python Service**:
```python
from services.memory_extractor import memory_extractor

result = await memory_extractor.batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repository",
    max_commits=50,
    file_patterns=["*.py", "*.js", "*.ts"]
)

print(f"Total extracted: {result['total_extracted']}")
print(f"From commits: {result['by_source']['git_commits']}")
print(f"From comments: {result['by_source']['code_comments']}")
print(f"From docs: {result['by_source']['documentation']}")
```

**Response**:
```json
{
  "success": true,
  "total_extracted": 45,
  "by_source": {
    "git_commits": 12,
    "code_comments": 28,
    "documentation": 5
  },
  "extracted_memories": [...],
  "repository": "/path/to/repository"
}
```

### What Gets Analyzed

**1. Git Commits**:
- Recent commits (up to `max_commits`)
- Commit messages (title + body)
- Changed files
- Commit type (feat, fix, refactor, etc.)

**2. Code Comments**:
- Source files matching `file_patterns`
- TODO, FIXME, NOTE, DECISION markers
- Up to 30 files sampled for performance

**3. Documentation**:
- README.md - Project overview
- CHANGELOG.md - Project evolution
- CONTRIBUTING.md - Conventions
- CLAUDE.md - AI agent instructions

### Configuration Options

```python
# Default configuration
await memory_extractor.batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repo",
    max_commits=50,  # Last 50 commits
    file_patterns=["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs"]
)

# Focused on recent commits
await memory_extractor.batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repo",
    max_commits=20,  # Just last 20
    file_patterns=None  # Skip code comments
)

# Deep codebase analysis
await memory_extractor.batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repo",
    max_commits=100,  # More commits
    file_patterns=["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs", "*.cpp", "*.c"]
)
```

### Performance Considerations

**Limits**:
- Max 20 commits processed (even if max_commits is higher)
- Max 30 source files sampled
- Max 3 memories per marker type per file

**Processing Time**:
- Small repo (< 100 files): 1-2 minutes
- Medium repo (100-1000 files): 3-5 minutes
- Large repo (> 1000 files): 5-10 minutes

**Optimization**:
```python
# Quick bootstrap
await memory_extractor.batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repo",
    max_commits=10,  # Limited commits
    file_patterns=["*.py"]  # Single language
)

# Comprehensive analysis (run overnight)
await memory_extractor.batch_extract_from_repository(
    project_id="my-project",
    repo_path="/path/to/repo",
    max_commits=100,
    file_patterns=["*.py", "*.js", "*.ts", "*.java", "*.go"]
)
```

---

## Integration Patterns

### Pattern 1: Post-Session Extraction

Extract memories after AI coding session:

```python
async def post_session_extraction(
    project_id: str,
    conversation: list,
    repo_path: str
):
    """Extract memories after coding session"""

    # 1. Extract from conversation
    conv_result = await memory_extractor.extract_from_conversation(
        project_id=project_id,
        conversation=conversation,
        auto_save=True
    )

    # 2. Get recent commit (if any)
    import subprocess
    try:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            text=True
        ).strip()

        commit_msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=repo_path,
            text=True
        ).strip()

        changed_files = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            cwd=repo_path,
            text=True
        ).strip().split('\n')

        # Extract from commit
        commit_result = await memory_extractor.extract_from_git_commit(
            project_id=project_id,
            commit_sha=commit_sha,
            commit_message=commit_msg,
            changed_files=changed_files,
            auto_save=True
        )

    except Exception as e:
        print(f"No recent commit: {e}")

    return {
        'conversation_memories': conv_result['auto_saved_count'],
        'commit_memories': commit_result.get('auto_saved_count', 0)
    }
```

### Pattern 2: Continuous Git Hook Integration

Extract on every commit:

```python
# .git/hooks/post-commit
#!/usr/bin/env python3

import asyncio
import subprocess
import sys
sys.path.insert(0, '/path/to/project')

from services.memory_extractor import memory_extractor

async def main():
    # Get commit details
    commit_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True
    ).strip()

    commit_msg = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%B"],
        text=True
    ).strip()

    changed_files = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        text=True
    ).strip().split('\n')

    # Extract memories
    result = await memory_extractor.extract_from_git_commit(
        project_id="my-project",
        commit_sha=commit_sha,
        commit_message=commit_msg,
        changed_files=changed_files,
        auto_save=True
    )

    if result.get('auto_saved_count', 0) > 0:
        print(f"✅ Extracted {result['auto_saved_count']} memories from commit")

if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 3: Scheduled Repository Scans

Daily/weekly full repository analysis:

```python
import schedule
import asyncio

async def daily_repository_scan():
    """Daily scan of repository for new knowledge"""

    result = await memory_extractor.batch_extract_from_repository(
        project_id="my-project",
        repo_path="/path/to/repo",
        max_commits=10,  # Last day's commits
        file_patterns=["*.py", "*.js"]
    )

    print(f"Daily scan: {result['total_extracted']} new memories")

    # Send notification
    if result['total_extracted'] > 5:
        send_slack_notification(
            f"⚠️ {result['total_extracted']} new memories extracted from codebase"
        )

# Schedule daily at 2 AM
schedule.every().day.at("02:00").do(lambda: asyncio.run(daily_repository_scan()))
```

---

## Configuration

### LLM Settings

Extraction uses the project's configured LLM:

```bash
# .env file
LLM_PROVIDER=openai  # or ollama, gemini, openrouter
OPENAI_API_KEY=your-key
```

### Confidence Threshold

Adjust auto-save threshold (default: 0.7):

```python
from services.memory_extractor import memory_extractor

# Lower threshold (more auto-saves)
memory_extractor.confidence_threshold = 0.6

# Higher threshold (fewer auto-saves, higher quality)
memory_extractor.confidence_threshold = 0.8
```

### Processing Limits

Adjust processing limits:

```python
from services.memory_extractor import MemoryExtractor

# Custom limits
MemoryExtractor.MAX_COMMITS_TO_PROCESS = 30
MemoryExtractor.MAX_FILES_TO_SAMPLE = 50
MemoryExtractor.MAX_ITEMS_PER_TYPE = 5
```

---

## Best Practices

### 1. Choose Appropriate Auto-Save Settings

```python
# Critical production project: Review before saving
auto_save=False

# Personal project: Auto-save high confidence
auto_save=True
```

### 2. Batch Operations During Off-Hours

```python
# Run comprehensive analysis during off-hours
# Avoid running during active development

# Good: 2 AM daily scan
schedule.every().day.at("02:00").do(run_batch_extraction)

# Bad: Every 10 minutes during work hours
```

### 3. Monitor Extraction Quality

```python
result = await memory_extractor.extract_from_conversation(
    project_id="my-project",
    conversation=conversation,
    auto_save=False
)

# Review confidence distribution
high_confidence = sum(1 for s in result['suggestions'] if s['confidence'] >= 0.8)
medium_confidence = sum(1 for s in result['suggestions'] if 0.6 <= s['confidence'] < 0.8)
low_confidence = sum(1 for s in result['suggestions'] if s['confidence'] < 0.6)

print(f"High: {high_confidence}, Medium: {medium_confidence}, Low: {low_confidence}")
```

### 4. Customize Marker Importance

```python
# For your codebase, adjust marker importance in memory_extractor.py
# Example: Make TODOs more important in your project

# Override classification
def custom_classify_comment(text: str) -> dict:
    if "TODO:" in text.upper():
        # Higher importance for TODOs in your project
        return {
            "type": "plan",
            "importance": 0.7  # Instead of default 0.4
        }
    # ... other markers
```

### 5. Review and Clean Periodically

```python
async def review_auto_extracted_memories(project_id: str):
    """Review and clean auto-extracted memories"""

    # Find all auto-extracted memories
    all_memories = await memory_store.search_memories(
        project_id=project_id,
        limit=100
    )

    auto_extracted = [
        m for m in all_memories['memories']
        if m.get('metadata', {}).get('source') in ['conversation', 'git_commit', 'code_comment']
    ]

    # Review low-importance ones
    for memory in auto_extracted:
        if memory['importance'] < 0.4:
            print(f"Review: {memory['title']} (importance: {memory['importance']})")
            # Manually decide: keep, delete, or update importance
```

---

## Troubleshooting

### No Memories Extracted

**Problem**: Extraction returns 0 memories

**Solutions**:
```python
# 1. Check LLM is configured
from llama_index.core import Settings
print(f"LLM configured: {Settings.llm is not None}")

# 2. Verify source content is substantial
# Short conversations may not yield memories

# 3. Check confidence threshold
memory_extractor.confidence_threshold = 0.5  # Lower threshold

# 4. Disable auto_save to see all suggestions
result = await memory_extractor.extract_from_conversation(
    project_id="my-project",
    conversation=conversation,
    auto_save=False
)
print(f"Suggestions: {len(result['suggestions'])}")
```

### Low Quality Extractions

**Problem**: Extracted memories are not useful

**Solutions**:
```python
# 1. Increase confidence threshold
memory_extractor.confidence_threshold = 0.8

# 2. Use manual review
auto_save=False

# 3. Provide better source content
# More detailed conversations yield better extractions
```

### Extraction Too Slow

**Problem**: Batch extraction takes too long

**Solutions**:
```python
# 1. Reduce max_commits
max_commits=10  # Instead of 50

# 2. Limit file patterns
file_patterns=["*.py"]  # Just Python

# 3. Use sampling
# MemoryExtractor already samples (MAX_FILES_TO_SAMPLE = 30)
```

---

## Next Steps

- **Manual Management**: See [manual.md](./manual.md) for CRUD operations
- **Search Strategies**: See [search.md](./search.md) for finding memories
- **Overview**: See [overview.md](./overview.md) for system introduction
- **API Reference**: See `/api/v1/memory` endpoints
