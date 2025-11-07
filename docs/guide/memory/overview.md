# Memory Store Overview

The Memory Store is a project knowledge persistence system designed specifically for AI agents to maintain continuity across development sessions. Unlike short-term conversation history, the Memory Store preserves curated, structured project knowledge.

## Table of Contents

- [What is Memory Store?](#what-is-memory-store)
- [Why Memory Store Matters](#why-memory-store-matters)
- [Core Concepts](#core-concepts)
- [Memory Types](#memory-types)
- [Architecture](#architecture)
- [Operation Modes](#operation-modes)
- [Quick Start](#quick-start)
- [Use Cases](#use-cases)

---

## What is Memory Store?

Memory Store is a Neo4j-based knowledge management system that allows AI agents and developers to:

- **Save Important Decisions**: Architectural choices, technology selections, and their rationale
- **Record Preferences**: Coding styles, tool choices, and team conventions
- **Document Experiences**: Problems encountered and their solutions
- **Track Plans**: Future improvements, TODOs, and roadmap items
- **Preserve Context**: Maintain project knowledge across sessions, weeks, and months

**Key Principle**: Memory = Structured Project Knowledge

Instead of re-explaining project context every session, AI agents can search memories and immediately understand:
- "Why did we choose PostgreSQL over MySQL?"
- "What's our convention for API endpoint naming?"
- "What Redis issues did we encounter in Docker?"

---

## Why Memory Store Matters

### Problem: Context Loss Across Sessions

Without Memory Store, AI agents suffer from:
- ❌ Repeating the same questions every session
- ❌ Forgetting why decisions were made
- ❌ Making inconsistent choices
- ❌ Re-encountering solved problems
- ❌ Breaking established conventions

### Solution: Long-term Project Memory

With Memory Store, AI agents gain:
- ✅ **Cross-session continuity** - Remember decisions from previous sessions
- ✅ **Avoid repeating mistakes** - Recall past problems and solutions
- ✅ **Maintain consistency** - Follow established patterns and conventions
- ✅ **Track evolution** - Document how decisions change over time
- ✅ **Preserve rationale** - Remember *why* something was done, not just *what*

---

## Core Concepts

### 1. Memory as Knowledge

Each memory represents a discrete piece of project knowledge:

```python
{
  "id": "uuid-here",
  "type": "decision",
  "title": "Use JWT for authentication",
  "content": "Decided to use JWT tokens instead of session-based auth",
  "reason": "Need stateless authentication for mobile clients",
  "importance": 0.9,
  "tags": ["auth", "architecture"],
  "created_at": "2025-11-06T10:30:00Z",
  "updated_at": "2025-11-06T10:30:00Z"
}
```

### 2. Project Organization

Memories belong to projects, enabling multi-project knowledge management:

```
Project: web-app
├── Decisions: 15 memories
├── Preferences: 8 memories
├── Experiences: 12 memories
├── Conventions: 6 memories
├── Plans: 10 memories
└── Notes: 5 memories
```

### 3. Knowledge Evolution

Memories can supersede each other, preserving decision history:

```
Original Decision (2024-01-15)
  ↓ superseded by
New Decision (2024-03-20)
  ↓ superseded by
Current Decision (2024-11-06)
```

### 4. Code Integration

Memories can link to code via `ref://` handles:

```python
related_refs = [
  "ref://file/src/auth/jwt.py",
  "ref://symbol/authenticate_user",
  "ref://file/config/database.py#L45"
]
```

---

## Memory Types

The Memory Store supports six memory types, each serving a specific purpose:

### 1. Decision
**Purpose**: Architectural choices, technology selections, and major design decisions

**Importance Range**: 0.7 - 1.0 (high importance)

**Examples**:
- "Use JWT tokens for stateless authentication"
- "Adopt microservices architecture for scalability"
- "Choose PostgreSQL over MySQL for JSON support"

**When to Use**:
- Making technology stack choices
- Deciding on architectural patterns
- Selecting third-party services or libraries
- Establishing security policies

### 2. Preference
**Purpose**: Team coding styles, tool preferences, and development practices

**Importance Range**: 0.5 - 0.7 (medium importance)

**Examples**:
- "Use raw SQL instead of ORM for database queries"
- "Prefer functional components in React"
- "Use kebab-case for API endpoint naming"

**When to Use**:
- Establishing coding style guidelines
- Choosing between equivalent approaches
- Setting team tool preferences
- Defining code review standards

### 3. Experience
**Purpose**: Problems encountered and their solutions, bug fixes, gotchas

**Importance Range**: 0.5 - 0.9 (varies by severity)

**Examples**:
- "Redis fails with 'localhost' in Docker - use service name instead"
- "Large file uploads timeout - need to increase nginx client_max_body_size"
- "Date parsing breaks in Safari - must use ISO 8601 format"

**When to Use**:
- Documenting bugs and their fixes
- Recording deployment issues
- Noting platform-specific quirks
- Sharing debugging insights

### 4. Convention
**Purpose**: Team rules, naming standards, and established practices

**Importance Range**: 0.4 - 0.6 (medium importance)

**Examples**:
- "All API endpoints must use kebab-case"
- "Test files must be in __tests__ directory"
- "Environment variables must use UPPER_SNAKE_CASE"

**When to Use**:
- Documenting naming conventions
- Establishing file organization rules
- Setting commit message standards
- Defining code structure patterns

### 5. Plan
**Purpose**: Future improvements, TODOs, roadmap items

**Importance Range**: 0.3 - 0.7 (varies by priority)

**Examples**:
- "Migrate to PostgreSQL 16 for performance improvements"
- "Add rate limiting to public API endpoints"
- "Refactor authentication middleware for better testability"

**When to Use**:
- Tracking technical debt
- Planning future features
- Recording optimization opportunities
- Documenting refactoring needs

### 6. Note
**Purpose**: General information that doesn't fit other categories

**Importance Range**: 0.2 - 0.8 (varies widely)

**Examples**:
- "Production database backups stored in S3 bucket prod-backups"
- "Weekly deployment window is Thursdays 2-4 PM EST"
- "API rate limit is 100 requests per minute per IP"

**When to Use**:
- Recording operational information
- Documenting deployment procedures
- Noting configuration details
- Capturing miscellaneous knowledge

---

## Architecture

### Storage: Neo4j Graph Database

Memory Store uses Neo4j for flexible, connected knowledge storage:

```cypher
# Node Types
(Memory)  - Individual memory record
(Project) - Project container

# Relationships
(Memory)-[:BELONGS_TO]->(Project)
(Memory)-[:SUPERSEDES]->(Memory)
(Memory)-[:RELATES_TO]->(File)
(Memory)-[:RELATES_TO]->(Symbol)
```

**Why Neo4j?**
- **Graph Relationships**: Natural modeling of memory connections
- **Fulltext Search**: Fast search across title, content, reason, tags
- **Vector Integration**: Future support for semantic search
- **Flexible Schema**: Easy to add new memory types and relationships

### Components

```
┌─────────────────────────────────────────────────┐
│           Application Layer                     │
│  ┌──────────────┐  ┌──────────────┐            │
│  │  MCP Server  │  │  HTTP API    │            │
│  │  (30 tools)  │  │  (FastAPI)   │            │
│  └──────────────┘  └──────────────┘            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│           Service Layer                         │
│  ┌──────────────┐  ┌──────────────┐            │
│  │MemoryStore   │  │MemoryExtractor│           │
│  │  (manual)    │  │  (auto v0.7) │            │
│  └──────────────┘  └──────────────┘            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         Data Layer (Neo4j)                      │
│                                                 │
│  ┌────────┐  ┌────────┐  ┌────────┐           │
│  │ Memory │──│Project │  │  Code  │           │
│  │ Nodes  │  │ Nodes  │  │  Refs  │           │
│  └────────┘  └────────┘  └────────┘           │
└─────────────────────────────────────────────────┘
```

---

## Operation Modes

Memory Store operates in two modes based on your configuration:

### Standard Mode (Fulltext Search)
**Requirements**: Neo4j database only

**Features**:
- ✅ Add, update, delete memories
- ✅ Fulltext search across title, content, reason, tags
- ✅ Filter by type, tags, importance
- ✅ Manual memory management (v0.6)
- ✅ Automatic extraction (v0.7)

**Limitations**:
- ❌ No semantic similarity search
- ❌ No embedding-based retrieval

**Best For**: Projects that don't need semantic search

### Full Mode (With Embeddings)
**Requirements**: Neo4j + Embedding provider (OpenAI/Gemini/HuggingFace)

**Features**:
- ✅ All Standard Mode features
- ✅ Semantic similarity search
- ✅ Embedding-based memory retrieval
- ✅ Find conceptually related memories

**Best For**: Large projects with extensive knowledge bases

**Configuration**:
```bash
# .env file
EMBEDDING_PROVIDER=openai  # or gemini, huggingface
OPENAI_API_KEY=your-key-here
```

---

## Quick Start

### 1. Using MCP Tools (Recommended for AI Agents)

If you're using Claude Desktop, VSCode with MCP, or other MCP-compatible clients:

```python
# Add a decision memory
add_memory(
    project_id="my-project",
    memory_type="decision",
    title="Use JWT for authentication",
    content="Decided to use JWT tokens for stateless auth",
    reason="Need mobile client support and horizontal scaling",
    importance=0.9,
    tags=["auth", "security"]
)

# Search for memories
search_memories(
    project_id="my-project",
    query="authentication",
    memory_type="decision",
    min_importance=0.7
)

# Get project summary
get_project_summary(project_id="my-project")
```

### 2. Using HTTP API

For web applications and custom integrations:

```bash
# Add a memory
curl -X POST http://localhost:8000/api/v1/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "memory_type": "decision",
    "title": "Use JWT for authentication",
    "content": "Decided to use JWT tokens for stateless auth",
    "reason": "Need mobile client support",
    "importance": 0.9,
    "tags": ["auth", "security"]
  }'

# Search memories
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "query": "authentication",
    "min_importance": 0.7
  }'
```

### 3. Using Python Service Directly

For Python applications:

```python
from src.codebase_rag.services.memory import memory_store
import asyncio

async def main():
    # Initialize
    await memory_store.initialize()

    # Add memory
    result = await memory_store.add_memory(
        project_id="my-project",
        memory_type="decision",
        title="Use JWT for authentication",
        content="Decided to use JWT tokens",
        reason="Need stateless auth",
        importance=0.9,
        tags=["auth"]
    )

    print(f"Added memory: {result['memory_id']}")

    # Search
    results = await memory_store.search_memories(
        project_id="my-project",
        query="authentication"
    )

    for memory in results['memories']:
        print(f"- {memory['title']}")

asyncio.run(main())
```

---

## Use Cases

### Use Case 1: AI Agent Development Session

**Scenario**: AI agent starts working on a new feature

**Workflow**:
1. **Search memories** for related decisions and conventions
2. **Review experiences** to avoid known issues
3. **Implement feature** following established patterns
4. **Save new learnings** as memories for future sessions

**Example**:
```python
# Session starts
memories = search_memories(
    project_id="web-app",
    query="database migration",
    memory_type="experience"
)
# AI learns: "Always backup before migrations"

# After implementation
add_memory(
    project_id="web-app",
    memory_type="decision",
    title="Use Alembic for database migrations",
    content="Adopted Alembic for schema migrations",
    reason="Better than custom scripts, team familiar with it",
    importance=0.8
)
```

### Use Case 2: Team Onboarding

**Scenario**: New team member or AI agent needs to understand project

**Workflow**:
```python
# Get project overview
summary = get_project_summary(project_id="web-app")
# Shows: 15 decisions, 8 preferences, 12 experiences

# Review top decisions
decisions = search_memories(
    project_id="web-app",
    memory_type="decision",
    min_importance=0.8
)
# Quickly understand key architectural choices

# Check coding conventions
conventions = search_memories(
    project_id="web-app",
    memory_type="convention"
)
# Learn team standards and practices
```

### Use Case 3: Knowledge Evolution

**Scenario**: Decision needs to change, preserve history

**Workflow**:
```python
# Original decision
old_memory = add_memory(
    memory_type="decision",
    title="Use MySQL as database",
    importance=0.7
)

# Requirements change, decision evolves
supersede_memory(
    old_memory_id=old_memory['memory_id'],
    new_memory_type="decision",
    new_title="Migrate to PostgreSQL",
    new_content="Switched from MySQL to PostgreSQL",
    new_reason="Need advanced JSON support and full-text search",
    new_importance=0.9
)
# Old decision preserved but marked as superseded
# History maintained for audit trail
```

### Use Case 4: Bug Prevention

**Scenario**: Team encounters a tricky bug, wants to prevent recurrence

**Workflow**:
```python
# Document the experience
add_memory(
    project_id="mobile-app",
    memory_type="experience",
    title="iOS date parsing fails without explicit timezone",
    content="Date.parse() in iOS Safari fails on dates without explicit timezone",
    reason="Safari is stricter than Chrome about date formats",
    importance=0.7,
    tags=["ios", "safari", "datetime", "bug"],
    related_refs=["ref://file/src/utils/dateParser.js"]
)

# Future sessions
# AI agent searches for "date parsing" before implementing
# Finds the experience, avoids the bug
```

### Use Case 5: Automatic Knowledge Capture (v0.7)

**Scenario**: Extract memories from git history and code

**Workflow**:
```python
# Extract from conversation
extract_from_conversation(
    project_id="my-app",
    conversation=[
        {"role": "user", "content": "Should we use Redis or Memcached?"},
        {"role": "assistant", "content": "Redis is better because..."}
    ],
    auto_save=True
)
# Automatically extracts and saves the decision

# Extract from git commits
extract_from_git_commit(
    project_id="my-app",
    commit_sha="abc123",
    commit_message="feat: add JWT authentication",
    changed_files=["src/auth/jwt.py"],
    auto_save=True
)
# Extracts architectural decision from commit

# Batch extract from repository
batch_extract_from_repository(
    project_id="my-app",
    repo_path="/path/to/repo",
    max_commits=50
)
# Comprehensive analysis: commits, comments, docs
```

---

## Best Practices

### 1. Importance Scoring Guidelines

| Score | Category | Examples |
|-------|----------|----------|
| 0.9-1.0 | Critical | Security decisions, breaking changes, data model changes |
| 0.7-0.8 | Important | Architecture choices, major features, API contracts |
| 0.5-0.6 | Moderate | Preferences, conventions, common patterns |
| 0.3-0.4 | Low | Plans, future work, minor notes |
| 0.0-0.2 | Minimal | Temporary notes, experimental ideas |

### 2. Tagging Strategy

**Use Domain Tags**:
```python
tags = ["auth", "database", "api", "frontend", "backend"]
```

**Use Category Tags**:
```python
tags = ["security", "performance", "testing", "deployment"]
```

**Use Status Tags**:
```python
tags = ["critical", "deprecated", "experimental", "production"]
```

**Combine Multiple Levels**:
```python
tags = ["auth", "security", "jwt", "production", "critical"]
```

### 3. When to Create Memories

**DO Create Memories For**:
- ✅ Architecture decisions
- ✅ Technology choices
- ✅ Tricky bugs and solutions
- ✅ Team conventions
- ✅ Deployment procedures
- ✅ Security findings
- ✅ Performance optimizations

**DON'T Create Memories For**:
- ❌ Routine code changes
- ❌ Trivial fixes
- ❌ Temporary experiments
- ❌ Information already in documentation
- ❌ Standard best practices

### 4. Memory Maintenance

**Regular Review**:
- Review memories every sprint/month
- Update importance scores as project evolves
- Supersede outdated decisions
- Delete obsolete notes

**Quality Over Quantity**:
- Better to have 20 high-quality memories than 200 low-quality ones
- Focus on non-obvious knowledge
- Prioritize "why" over "what"

---

## Next Steps

- **Manual Memory Management**: See [Manual Guide](./manual.md)
- **Search Strategies**: See [Search Guide](./search.md)
- **Automatic Extraction**: See [Extraction Guide](./extraction.md)
- **API Reference**: See `/api/v1/memory` endpoints
- **MCP Tools**: See MCP server documentation

---

## Version History

- **v0.6** - Manual memory management with fulltext search
- **v0.7** - Automatic extraction from conversations, commits, code comments
  - `extract_from_conversation`: LLM-powered conversation analysis
  - `extract_from_git_commit`: Analyze git commits for decisions
  - `extract_from_code_comments`: Mine TODO, FIXME, NOTE markers
  - `suggest_memory_from_query`: Auto-suggest from knowledge queries
  - `batch_extract_from_repository`: Comprehensive repository analysis

---

## Support

For issues or questions:
- Check the documentation in `/docs/guide/memory/`
- Review examples in `/examples/memory_usage_example.py`
- See test cases in `/tests/test_memory_store.py`
