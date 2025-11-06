# Manual Memory Management Guide

This guide covers manual memory management operations in the Memory Store (v0.6 features). Learn how to create, search, update, delete, and evolve project knowledge.

## Table of Contents

- [Core Operations](#core-operations)
- [Adding Memories](#adding-memories)
- [Retrieving Memories](#retrieving-memories)
- [Updating Memories](#updating-memories)
- [Deleting Memories](#deleting-memories)
- [Memory Evolution](#memory-evolution)
- [Project Summaries](#project-summaries)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)

---

## Core Operations

Memory Store provides seven core manual operations:

1. **add_memory** - Create new memory
2. **search_memories** - Find memories by query/filters
3. **get_memory** - Retrieve specific memory by ID
4. **update_memory** - Modify existing memory
5. **delete_memory** - Remove memory
6. **supersede_memory** - Create new memory that replaces old one
7. **get_project_summary** - Get project overview

Each operation is available via:
- **MCP Tools** - For AI assistants (Claude Desktop, VSCode)
- **HTTP API** - For web applications
- **Python Service** - For direct integration

---

## Adding Memories

### Basic Memory Creation

**MCP Tool**:
```python
add_memory(
    project_id="my-project",
    memory_type="decision",
    title="Use JWT for authentication",
    content="Decided to use JWT tokens instead of session-based authentication",
    reason="Need stateless authentication for mobile clients and microservices",
    importance=0.9,
    tags=["auth", "security", "architecture"]
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "memory_type": "decision",
    "title": "Use JWT for authentication",
    "content": "Decided to use JWT tokens instead of session-based authentication",
    "reason": "Need stateless authentication for mobile clients",
    "importance": 0.9,
    "tags": ["auth", "security"]
  }'
```

**Python Service**:
```python
from services.memory_store import memory_store

result = await memory_store.add_memory(
    project_id="my-project",
    memory_type="decision",
    title="Use JWT for authentication",
    content="Decided to use JWT tokens",
    reason="Need stateless auth for mobile clients",
    importance=0.9,
    tags=["auth", "security"]
)

memory_id = result['memory_id']
```

**Response**:
```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "decision",
  "title": "Use JWT for authentication"
}
```

### Memory Types and Examples

#### 1. Decision Memory
**Use For**: Architecture choices, technology selections, design decisions

```python
add_memory(
    project_id="web-app",
    memory_type="decision",
    title="Adopt microservices architecture",
    content="Transitioning from monolith to microservices for user service, order service, and payment service",
    reason="Need independent scaling and deployment. User service has different load patterns than order service",
    importance=0.95,
    tags=["architecture", "microservices", "scaling"],
    related_refs=[
        "ref://file/docs/architecture/microservices.md",
        "ref://file/services/user-service/README.md"
    ]
)
```

#### 2. Preference Memory
**Use For**: Team coding styles, tool preferences

```python
add_memory(
    project_id="web-app",
    memory_type="preference",
    title="Use functional components in React",
    content="Team prefers functional components with hooks over class components",
    reason="Hooks provide better code reuse and easier testing. Team is more familiar with functional approach",
    importance=0.6,
    tags=["react", "frontend", "coding-style"]
)
```

#### 3. Experience Memory
**Use For**: Problems encountered and solutions

```python
add_memory(
    project_id="web-app",
    memory_type="experience",
    title="Redis connection timeout in Docker Compose",
    content="Redis connections were timing out when using 'localhost:6379' in Docker environment",
    reason="Docker Compose networking requires using service name 'redis:6379' instead of 'localhost'. Docker creates an internal network where services communicate by name",
    importance=0.7,
    tags=["docker", "redis", "networking", "deployment"],
    related_refs=["ref://file/docker-compose.yml#L15"]
)
```

#### 4. Convention Memory
**Use For**: Team rules, naming standards

```python
add_memory(
    project_id="web-app",
    memory_type="convention",
    title="API endpoints use kebab-case",
    content="All REST API endpoints must use kebab-case naming convention. Example: /api/user-profiles instead of /api/userProfiles",
    reason="Consistency across API, better readability in URLs",
    importance=0.5,
    tags=["api", "naming", "conventions"]
)
```

#### 5. Plan Memory
**Use For**: Future improvements, TODOs

```python
add_memory(
    project_id="web-app",
    memory_type="plan",
    title="Add rate limiting to public API",
    content="Plan to implement rate limiting on all public API endpoints. Use Redis-based rate limiter with sliding window algorithm. Limit: 100 requests per minute per IP",
    reason="Prevent API abuse and ensure fair usage",
    importance=0.6,
    tags=["api", "security", "todo", "performance"]
)
```

#### 6. Note Memory
**Use For**: General information

```python
add_memory(
    project_id="web-app",
    memory_type="note",
    title="Production database backup location",
    content="Production PostgreSQL backups are stored in S3 bucket 'prod-db-backups' with 30-day retention. Daily backups run at 2 AM UTC",
    reason="Critical operational information for disaster recovery",
    importance=0.7,
    tags=["operations", "backup", "production"]
)
```

### Advanced: Linking to Code References

Use `ref://` handles to link memories to specific code:

```python
add_memory(
    project_id="api-service",
    memory_type="decision",
    title="Use dependency injection for services",
    content="Implemented dependency injection pattern for all service classes",
    reason="Improves testability and reduces coupling",
    importance=0.8,
    tags=["architecture", "patterns"],
    related_refs=[
        "ref://file/src/core/container.py",
        "ref://file/src/services/user_service.py#L25",
        "ref://symbol/UserService",
        "ref://symbol/inject_dependencies"
    ]
)
```

**Supported ref:// formats**:
- `ref://file/path/to/file.py` - Link to entire file
- `ref://file/path/to/file.py#L45` - Link to specific line
- `ref://symbol/ClassName` - Link to class/function
- `ref://file/path#section` - Link to section

### Advanced: Custom Metadata

Add custom metadata for application-specific needs:

```python
add_memory(
    project_id="web-app",
    memory_type="decision",
    title="Switch to PostgreSQL 15",
    content="Upgraded from PostgreSQL 13 to 15",
    reason="Better performance and new JSON features",
    importance=0.8,
    tags=["database", "upgrade"],
    metadata={
        "migration_date": "2024-11-01",
        "downtime": "5 minutes",
        "rollback_plan": "restore from backup",
        "approved_by": "tech-lead"
    }
)
```

---

## Retrieving Memories

### Get Specific Memory

**MCP Tool**:
```python
get_memory(memory_id="550e8400-e29b-41d4-a716-446655440000")
```

**HTTP API**:
```bash
curl http://localhost:8000/api/v1/memory/550e8400-e29b-41d4-a716-446655440000
```

**Python Service**:
```python
result = await memory_store.get_memory("550e8400-e29b-41d4-a716-446655440000")

if result['success']:
    memory = result['memory']
    print(f"Title: {memory['title']}")
    print(f"Content: {memory['content']}")
    print(f"Related refs: {memory['related_refs']}")
```

**Response**:
```json
{
  "success": true,
  "memory": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "decision",
    "title": "Use JWT for authentication",
    "content": "Decided to use JWT tokens...",
    "reason": "Need stateless authentication...",
    "tags": ["auth", "security"],
    "importance": 0.9,
    "created_at": "2025-11-06T10:00:00Z",
    "updated_at": "2025-11-06T10:00:00Z",
    "metadata": {},
    "related_refs": [
      {"type": "File", "path": "src/auth/jwt.py"}
    ]
  }
}
```

---

## Updating Memories

### Update Memory Fields

**MCP Tool**:
```python
update_memory(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    importance=0.95,
    tags=["auth", "security", "critical", "production"]
)
```

**HTTP API**:
```bash
curl -X PUT http://localhost:8000/api/v1/memory/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "importance": 0.95,
    "tags": ["auth", "security", "critical"]
  }'
```

**Python Service**:
```python
result = await memory_store.update_memory(
    memory_id="550e8400-e29b-41d4-a716-446655440000",
    title="Use JWT with refresh token rotation",
    content="Updated implementation to include refresh token rotation",
    importance=0.95,
    tags=["auth", "security", "critical"]
)
```

**Updatable Fields**:
- `title` - Change the title
- `content` - Update the content
- `reason` - Modify the rationale
- `tags` - Replace tags (not append - provide full list)
- `importance` - Adjust importance score

**Note**: Only provided fields are updated. Omitted fields remain unchanged.

### Common Update Scenarios

#### Increase Importance After Production Issue
```python
# Security vulnerability discovered
update_memory(
    memory_id=auth_memory_id,
    importance=1.0,
    tags=["auth", "security", "critical", "vulnerability"]
)
```

#### Add Context to Existing Memory
```python
# Found additional information
update_memory(
    memory_id=redis_memory_id,
    content=original_content + "\n\nUpdate: Also affects Redis Sentinel configuration. Must use sentinel service names.",
    reason=original_reason + " Additionally, Sentinel failover requires proper service name configuration."
)
```

#### Reclassify Memory Importance
```python
# Initially thought important, but turned out routine
update_memory(
    memory_id=config_memory_id,
    importance=0.4  # Downgrade from 0.7
)
```

---

## Deleting Memories

### Delete Memory

**MCP Tool**:
```python
delete_memory(memory_id="550e8400-e29b-41d4-a716-446655440000")
```

**HTTP API**:
```bash
curl -X DELETE http://localhost:8000/api/v1/memory/550e8400-e29b-41d4-a716-446655440000
```

**Python Service**:
```python
result = await memory_store.delete_memory("550e8400-e29b-41d4-a716-446655440000")

if result['success']:
    print("Memory deleted")
else:
    print(f"Error: {result['error']}")
```

**Note**: This is a **hard delete** - the memory is permanently removed from the database. For preserving history when decisions change, use `supersede_memory` instead.

### When to Delete vs Supersede

**Use Delete When**:
- ❌ Memory was created by mistake
- ❌ Information is completely wrong
- ❌ Duplicate memory exists
- ❌ Memory is obsolete and not worth preserving

**Use Supersede When**:
- ✅ Decision has changed and you want history
- ✅ Solution was improved and old approach is deprecated
- ✅ Convention evolved and old one should be marked outdated

---

## Memory Evolution

### Superseding Memories

When decisions change, use `supersede_memory` to preserve history:

**MCP Tool**:
```python
supersede_memory(
    old_memory_id="abc-123-def-456",
    new_memory_type="decision",
    new_title="Migrate from MySQL to PostgreSQL",
    new_content="Migrated from MySQL to PostgreSQL for production database",
    new_reason="Need advanced JSON support, full-text search, and better geospatial features",
    new_tags=["database", "postgresql", "migration"],
    new_importance=0.9
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/supersede \
  -H "Content-Type: application/json" \
  -d '{
    "old_memory_id": "abc-123-def-456",
    "new_memory_type": "decision",
    "new_title": "Migrate from MySQL to PostgreSQL",
    "new_content": "Migrated from MySQL to PostgreSQL",
    "new_reason": "Need advanced JSON and full-text search",
    "new_importance": 0.9
  }'
```

**Python Service**:
```python
result = await memory_store.supersede_memory(
    old_memory_id="abc-123-def-456",
    new_memory_data={
        "memory_type": "decision",
        "title": "Migrate from MySQL to PostgreSQL",
        "content": "Migrated from MySQL to PostgreSQL",
        "reason": "Need advanced features",
        "tags": ["database", "postgresql"],
        "importance": 0.9
    }
)

new_memory_id = result['new_memory_id']
old_memory_id = result['old_memory_id']
```

**What Happens**:
1. New memory is created with your data
2. `SUPERSEDES` relationship is created: `(new)-[:SUPERSEDES]->(old)`
3. Old memory gets `superseded_by` and `superseded_at` fields
4. Old memory remains in database but marked as superseded
5. Both memories belong to same project

### Evolution Example: Database Decision

**Phase 1: Original Decision (January)**
```python
mysql_memory = add_memory(
    project_id="web-app",
    memory_type="decision",
    title="Use MySQL as primary database",
    content="Selected MySQL for application database",
    reason="Team familiarity and existing infrastructure",
    importance=0.7,
    tags=["database", "mysql"]
)
# memory_id: "original-123"
```

**Phase 2: Requirements Change (March)**
```python
postgres_v1 = supersede_memory(
    old_memory_id="original-123",
    new_memory_type="decision",
    new_title="Migrate to PostgreSQL",
    new_content="Migrating from MySQL to PostgreSQL",
    new_reason="Need better JSON support and full-text search",
    new_tags=["database", "postgresql", "migration"],
    new_importance=0.8
)
# new_memory_id: "update-456"
# "original-123" now marked as superseded
```

**Phase 3: Full Migration Complete (June)**
```python
postgres_v2 = supersede_memory(
    old_memory_id="update-456",
    new_memory_type="decision",
    new_title="PostgreSQL 15 in production",
    new_content="Completed migration to PostgreSQL 15. All services migrated",
    new_reason="Migration successful. Using advanced features: JSONB, GiST indexes, full-text search",
    new_tags=["database", "postgresql", "production"],
    new_importance=0.9
)
# new_memory_id: "final-789"
# "update-456" now marked as superseded
```

**Result**: Complete decision history preserved:
```
"original-123" (MySQL)
    ← superseded by "update-456" (PostgreSQL migration)
        ← superseded by "final-789" (PostgreSQL production)
```

---

## Project Summaries

### Get Project Overview

**MCP Tool**:
```python
get_project_summary(project_id="web-app")
```

**HTTP API**:
```bash
curl http://localhost:8000/api/v1/memory/project/web-app/summary
```

**Python Service**:
```python
result = await memory_store.get_project_summary("web-app")

summary = result['summary']
print(f"Total memories: {summary['total_memories']}")

for memory_type, data in summary['by_type'].items():
    print(f"{memory_type}: {data['count']}")
    for mem in data['top_memories'][:3]:
        print(f"  - {mem['title']} (importance: {mem['importance']})")
```

**Response**:
```json
{
  "success": true,
  "summary": {
    "project_id": "web-app",
    "total_memories": 56,
    "by_type": {
      "decision": {
        "count": 15,
        "top_memories": [
          {
            "id": "...",
            "title": "Adopt microservices architecture",
            "importance": 0.95
          },
          {
            "id": "...",
            "title": "Use JWT for authentication",
            "importance": 0.9
          }
        ]
      },
      "preference": {
        "count": 8,
        "top_memories": [...]
      },
      "experience": {
        "count": 12,
        "top_memories": [...]
      },
      "convention": {
        "count": 6,
        "top_memories": [...]
      },
      "plan": {
        "count": 10,
        "top_memories": [...]
      },
      "note": {
        "count": 5,
        "top_memories": [...]
      }
    }
  }
}
```

**Use Cases**:
- Onboarding new team members or AI agents
- Project health checks
- Memory audit and cleanup
- Understanding project knowledge distribution

---

## Advanced Patterns

### Pattern 1: AI Agent Session Workflow

```python
# Start of session: Get context
async def start_session(project_id: str, task_area: str):
    # 1. Get project overview
    summary = await memory_store.get_project_summary(project_id)
    print(f"Project has {summary['summary']['total_memories']} memories")

    # 2. Search for relevant context
    context = await memory_store.search_memories(
        project_id=project_id,
        query=task_area,
        min_importance=0.6
    )

    # 3. Review top decisions and experiences
    for memory in context['memories'][:5]:
        print(f"Relevant: {memory['title']}")

    return context

# During work: Check conventions
async def check_conventions(project_id: str, area: str):
    conventions = await memory_store.search_memories(
        project_id=project_id,
        memory_type="convention",
        tags=[area]
    )
    return conventions

# End of session: Save learnings
async def save_learnings(project_id: str, new_knowledge: dict):
    result = await memory_store.add_memory(
        project_id=project_id,
        **new_knowledge
    )
    return result['memory_id']
```

### Pattern 2: Memory Cleanup and Maintenance

```python
async def cleanup_low_value_memories(project_id: str):
    """Remove low-importance notes older than 6 months"""

    # Search for low-importance notes
    old_notes = await memory_store.search_memories(
        project_id=project_id,
        memory_type="note",
        min_importance=0.0,
        limit=100
    )

    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=180)

    deleted_count = 0
    for memory in old_notes['memories']:
        created_at = datetime.fromisoformat(memory['created_at'])

        if memory['importance'] < 0.3 and created_at < cutoff_date:
            await memory_store.delete_memory(memory['id'])
            deleted_count += 1
            print(f"Deleted old note: {memory['title']}")

    return deleted_count
```

### Pattern 3: Memory Migration Between Projects

```python
async def migrate_memory(memory_id: str, from_project: str, to_project: str):
    """Copy memory from one project to another"""

    # Get original memory
    result = await memory_store.get_memory(memory_id)
    memory = result['memory']

    # Create copy in new project
    new_result = await memory_store.add_memory(
        project_id=to_project,
        memory_type=memory['type'],
        title=f"[Migrated] {memory['title']}",
        content=memory['content'],
        reason=memory.get('reason'),
        tags=memory.get('tags', []) + ['migrated'],
        importance=memory.get('importance', 0.5),
        metadata={
            **memory.get('metadata', {}),
            'migrated_from': from_project,
            'original_memory_id': memory_id
        }
    )

    return new_result['memory_id']
```

### Pattern 4: Tag-Based Memory Organization

```python
async def organize_by_tags(project_id: str):
    """Get memories organized by tag"""

    # Get all memories
    all_memories = await memory_store.search_memories(
        project_id=project_id,
        limit=100
    )

    # Organize by tag
    by_tag = {}
    for memory in all_memories['memories']:
        for tag in memory.get('tags', []):
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append({
                'id': memory['id'],
                'title': memory['title'],
                'importance': memory['importance']
            })

    # Sort tags by memory count
    sorted_tags = sorted(
        by_tag.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    print("Top tags:")
    for tag, memories in sorted_tags[:10]:
        print(f"{tag}: {len(memories)} memories")

    return by_tag
```

---

## Best Practices

### 1. Importance Scoring

**Be Consistent**:
```python
# Critical architecture decision
importance=0.95

# Important feature decision
importance=0.8

# Team preference
importance=0.6

# Minor convention
importance=0.4

# Future plan
importance=0.3
```

**Adjust Over Time**:
```python
# Initially seemed important
add_memory(..., importance=0.7)

# Later found to be critical
update_memory(memory_id, importance=0.95)
```

### 2. Effective Tagging

**Use Hierarchical Tags**:
```python
tags = [
    "auth",           # Domain
    "security",       # Category
    "jwt",            # Technology
    "production",     # Environment
    "critical"        # Status
]
```

**Be Specific**:
```python
# ❌ Too vague
tags = ["backend", "code"]

# ✅ Specific and useful
tags = ["auth", "jwt", "refresh-token", "security"]
```

### 3. Writing Good Content

**Include Context**:
```python
# ❌ Too brief
content = "Using Redis"

# ✅ Comprehensive
content = """
Implementing Redis as caching layer for user sessions and API responses.

Configuration:
- Redis 7.0 in cluster mode
- 3 master nodes, 3 replicas
- Maxmemory policy: allkeys-lru
- Persistence: RDB + AOF

Cache strategy:
- User sessions: TTL 24h
- API responses: TTL 5min
- Invalidation on data updates
"""
```

**Explain Why**:
```python
# ❌ No rationale
reason = "Better performance"

# ✅ Clear rationale
reason = """
Need to reduce database load by 70%. Current response times averaging 500ms,
target is 100ms. Redis provides:
1. Sub-millisecond latency
2. Horizontal scaling
3. Built-in data structures
4. Proven at scale by similar companies
"""
```

### 4. Related References

**Link to Relevant Code**:
```python
related_refs = [
    "ref://file/src/cache/redis_client.py",
    "ref://file/config/redis.yml",
    "ref://file/docs/cache-strategy.md"
]
```

**Be Specific**:
```python
# ✅ Point to exact implementation
related_refs = [
    "ref://file/src/auth/jwt.py#L45",  # JWT generation
    "ref://symbol/verify_token"         # Verification function
]
```

### 5. Memory Lifecycle Management

**Regular Reviews**:
```python
# Monthly review
async def monthly_review(project_id: str):
    # Check for outdated plans
    plans = await memory_store.search_memories(
        project_id=project_id,
        memory_type="plan",
        min_importance=0.0
    )

    # Review and update or delete completed plans
    for plan in plans['memories']:
        print(f"Review: {plan['title']}")
        # Manual decision: delete, update, or keep
```

**Update on Changes**:
```python
# When decision evolves, supersede instead of update
# Preserves history
await memory_store.supersede_memory(old_id, new_data)
```

---

## Common Patterns

### Pattern: Feature Development Workflow

```python
async def feature_workflow(project_id: str, feature_name: str):
    # 1. Check existing decisions
    decisions = await memory_store.search_memories(
        project_id=project_id,
        query=feature_name,
        memory_type="decision"
    )

    # 2. Check conventions
    conventions = await memory_store.search_memories(
        project_id=project_id,
        memory_type="convention"
    )

    # 3. Check past experiences
    experiences = await memory_store.search_memories(
        project_id=project_id,
        query=feature_name,
        memory_type="experience"
    )

    # 4. Implement feature...

    # 5. Save new knowledge
    await memory_store.add_memory(
        project_id=project_id,
        memory_type="decision",
        title=f"Implemented {feature_name}",
        content="...",
        reason="...",
        importance=0.7
    )
```

### Pattern: Debugging Workflow

```python
async def document_bug_fix(project_id: str, bug_description: str, solution: str):
    # Save the experience
    result = await memory_store.add_memory(
        project_id=project_id,
        memory_type="experience",
        title=f"Bug: {bug_description}",
        content=f"Problem: {bug_description}\n\nSolution: {solution}",
        reason="Prevent recurrence of this issue",
        importance=0.7,
        tags=["bug", "debugging"]
    )

    return result['memory_id']
```

---

## Troubleshooting

### Memory Not Found

```python
result = await memory_store.get_memory(memory_id)

if not result['success']:
    if "not found" in result['error'].lower():
        print("Memory doesn't exist or was deleted")
    else:
        print(f"Error: {result['error']}")
```

### Update Not Applied

```python
# Make sure at least one field is provided
result = await memory_store.update_memory(
    memory_id=memory_id,
    importance=0.9  # At least one field required
)

if not result['success']:
    if "No updates" in result['error']:
        print("Must provide at least one field to update")
```

### Search Returns No Results

```python
# Try broader search
result = await memory_store.search_memories(
    project_id=project_id,
    query="auth",  # Remove filters
    limit=100      # Increase limit
)

if result['total_count'] == 0:
    print("No memories found for this project")
```

---

## Next Steps

- **Search Guide**: Learn advanced search strategies in [search.md](./search.md)
- **Auto-Extraction**: Discover automatic memory extraction in [extraction.md](./extraction.md)
- **API Reference**: Full API documentation at `/api/v1/memory`
- **Examples**: See `/examples/memory_usage_example.py`
