# Memory Search Guide

Comprehensive guide to searching and retrieving memories in the Memory Store. Learn fulltext search, filtering strategies, and advanced query patterns.

## Table of Contents

- [Search Overview](#search-overview)
- [Basic Search](#basic-search)
- [Search Filters](#search-filters)
- [Search Modes](#search-modes)
- [Advanced Patterns](#advanced-patterns)
- [Search Strategies](#search-strategies)
- [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)

---

## Search Overview

Memory Store provides powerful search capabilities:

**Search Methods**:
- **Fulltext Search** - Search across title, content, reason, tags (Standard Mode)
- **Vector Search** - Semantic similarity search (Full Mode with embeddings)

**Filter Options**:
- **Memory Type** - Filter by type (decision, preference, etc.)
- **Tags** - Filter by one or more tags
- **Importance** - Minimum importance threshold
- **Limit** - Control number of results

**Ranking**:
- Search results are ranked by relevance score
- Secondary sorting by importance and creation date

---

## Basic Search

### Simple Text Search

**MCP Tool**:
```python
search_memories(
    project_id="my-project",
    query="authentication"
)
```

**HTTP API**:
```bash
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "query": "authentication"
  }'
```

**Python Service**:
```python
from src.codebase_rag.services.memory import memory_store

result = await memory_store.search_memories(
    project_id="my-project",
    query="authentication"
)

for memory in result['memories']:
    print(f"[{memory['type']}] {memory['title']}")
    print(f"  Score: {memory['search_score']}")
    print(f"  Importance: {memory['importance']}")
```

**Response**:
```json
{
  "success": true,
  "memories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "decision",
      "title": "Use JWT for authentication",
      "content": "Decided to use JWT tokens...",
      "reason": "Need stateless authentication...",
      "tags": ["auth", "security", "jwt"],
      "importance": 0.9,
      "created_at": "2025-11-06T10:00:00Z",
      "updated_at": "2025-11-06T10:00:00Z",
      "search_score": 2.45
    }
  ],
  "total_count": 5
}
```

### Search Without Query

Get all memories, sorted by importance:

```python
# Get all memories (no search query)
result = await memory_store.search_memories(
    project_id="my-project",
    limit=20
)

# Returns memories sorted by importance, then creation date
```

---

## Search Filters

### Filter by Memory Type

Find only decisions:

```python
search_memories(
    project_id="my-project",
    memory_type="decision"
)
```

Find only experiences (bug fixes, gotchas):

```python
search_memories(
    project_id="my-project",
    memory_type="experience"
)
```

### Filter by Tags

Single tag:

```python
search_memories(
    project_id="my-project",
    tags=["security"]
)
```

Multiple tags (OR logic - matches any tag):

```python
search_memories(
    project_id="my-project",
    tags=["security", "auth", "jwt"]
)
# Returns memories with ANY of these tags
```

### Filter by Importance

Get only critical memories:

```python
search_memories(
    project_id="my-project",
    min_importance=0.9
)
```

Get medium to high importance:

```python
search_memories(
    project_id="my-project",
    min_importance=0.6
)
```

### Combine Filters

```python
# Find critical security decisions
search_memories(
    project_id="my-project",
    query="authentication authorization",
    memory_type="decision",
    tags=["security"],
    min_importance=0.8,
    limit=10
)
```

---

## Search Modes

### Standard Mode: Fulltext Search

**Available in**: All installations

**How it works**:
- Uses Neo4j fulltext index
- Searches across: title, content, reason, tags
- Returns relevance score based on term frequency
- Case-insensitive
- Supports partial word matching

**Example**:
```python
# Query: "redis cache"
# Matches:
#   - Title: "Redis configuration for caching"
#   - Content: "...using Redis as cache layer..."
#   - Tags: ["redis", "cache", "performance"]
```

**Search Syntax**:
```python
# Single word
query="authentication"

# Multiple words (AND logic)
query="jwt token refresh"

# Phrase search (use quotes in query string)
query="'refresh token rotation'"

# Wildcard (automatic partial matching)
query="auth"  # Matches "authentication", "authorize", etc.
```

### Full Mode: Vector/Semantic Search

**Available in**: Installations with embedding provider configured

**How it works**:
- Converts query to embedding vector
- Finds semantically similar memories
- Understands concept similarity
- Language-independent

**Example**:
```python
# Query: "user login system"
# Semantically matches:
#   - "JWT authentication implementation"
#   - "OAuth 2.0 authorization"
#   - "Session management strategy"
# Even if exact words don't match
```

**Configuration**:
```bash
# .env file
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your-key

# Or use Gemini
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your-key
```

**Note**: Vector search is a planned feature (coming soon).

---

## Advanced Patterns

### Pattern 1: Hierarchical Search

Start broad, then narrow down:

```python
async def hierarchical_search(project_id: str, topic: str):
    # Step 1: Broad search
    broad = await memory_store.search_memories(
        project_id=project_id,
        query=topic,
        limit=50
    )

    print(f"Found {broad['total_count']} total matches")

    # Step 2: Filter for decisions only
    decisions = [m for m in broad['memories'] if m['type'] == 'decision']
    print(f"Found {len(decisions)} decisions")

    # Step 3: Get high-importance only
    critical = [m for m in decisions if m['importance'] >= 0.8]
    print(f"Found {len(critical)} critical decisions")

    return critical
```

### Pattern 2: Multi-Query Search

Search multiple related terms:

```python
async def multi_query_search(project_id: str, queries: list):
    all_results = {}

    for query in queries:
        result = await memory_store.search_memories(
            project_id=project_id,
            query=query
        )

        for memory in result['memories']:
            memory_id = memory['id']
            if memory_id not in all_results:
                all_results[memory_id] = memory
            else:
                # Boost score for multiple matches
                all_results[memory_id]['search_score'] += memory['search_score']

    # Sort by combined score
    sorted_results = sorted(
        all_results.values(),
        key=lambda m: m['search_score'],
        reverse=True
    )

    return sorted_results

# Usage
results = await multi_query_search(
    "my-project",
    ["authentication", "user login", "jwt token"]
)
```

### Pattern 3: Tag-Based Discovery

Find all memories with a specific tag:

```python
async def discover_by_tag(project_id: str, tag: str):
    result = await memory_store.search_memories(
        project_id=project_id,
        tags=[tag],
        limit=100
    )

    # Group by type
    by_type = {}
    for memory in result['memories']:
        mem_type = memory['type']
        if mem_type not in by_type:
            by_type[mem_type] = []
        by_type[mem_type].append(memory)

    # Show distribution
    for mem_type, memories in by_type.items():
        print(f"{mem_type}: {len(memories)}")
        for m in memories[:3]:  # Top 3
            print(f"  - {m['title']} (importance: {m['importance']})")

    return by_type
```

### Pattern 4: Time-Based Search

Find recent memories:

```python
from datetime import datetime, timedelta

async def find_recent_memories(project_id: str, days: int = 7):
    # Get all memories (search doesn't filter by date)
    result = await memory_store.search_memories(
        project_id=project_id,
        limit=100
    )

    # Filter by date
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = []

    for memory in result['memories']:
        created_at = datetime.fromisoformat(memory['created_at'])
        if created_at > cutoff:
            recent.append(memory)

    return recent

# Find what changed in last week
recent = await find_recent_memories("my-project", days=7)
print(f"Found {len(recent)} memories from last 7 days")
```

### Pattern 5: Related Memories

Find memories related to a specific memory:

```python
async def find_related_memories(project_id: str, memory_id: str):
    # Get original memory
    original = await memory_store.get_memory(memory_id)
    memory = original['memory']

    # Search using same tags
    related_by_tags = await memory_store.search_memories(
        project_id=project_id,
        tags=memory['tags'],
        limit=20
    )

    # Search using title/content keywords
    keywords = extract_keywords(memory['title'], memory['content'])
    related_by_content = await memory_store.search_memories(
        project_id=project_id,
        query=" ".join(keywords),
        limit=20
    )

    # Combine and deduplicate
    all_related = {}
    for m in related_by_tags['memories'] + related_by_content['memories']:
        if m['id'] != memory_id:  # Exclude original
            all_related[m['id']] = m

    return list(all_related.values())

def extract_keywords(title: str, content: str) -> list:
    # Simple keyword extraction (can be improved)
    import re
    words = re.findall(r'\w+', (title + " " + content).lower())
    # Remove common words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    keywords = [w for w in words if w not in stopwords and len(w) > 3]
    # Return top 10 most frequent
    from collections import Counter
    return [word for word, count in Counter(keywords).most_common(10)]
```

---

## Search Strategies

### Strategy 1: Task-Based Search

When starting a task, search for relevant context:

```python
async def search_for_task(project_id: str, task_description: str):
    """Search memories relevant to a task"""

    # 1. Search for related decisions
    print("Searching for related decisions...")
    decisions = await memory_store.search_memories(
        project_id=project_id,
        query=task_description,
        memory_type="decision",
        min_importance=0.6
    )

    # 2. Search for conventions
    print("Checking team conventions...")
    conventions = await memory_store.search_memories(
        project_id=project_id,
        memory_type="convention"
    )

    # 3. Search for past experiences
    print("Looking for past experiences...")
    experiences = await memory_store.search_memories(
        project_id=project_id,
        query=task_description,
        memory_type="experience"
    )

    return {
        'decisions': decisions['memories'],
        'conventions': conventions['memories'],
        'experiences': experiences['memories']
    }

# Usage
context = await search_for_task(
    "web-app",
    "implement user authentication with OAuth"
)

print(f"Found {len(context['decisions'])} relevant decisions")
print(f"Found {len(context['conventions'])} conventions to follow")
print(f"Found {len(context['experiences'])} past experiences")
```

### Strategy 2: Progressive Refinement

Start broad, refine based on results:

```python
async def progressive_search(project_id: str, initial_query: str):
    # Round 1: Broad search
    print(f"Searching: {initial_query}")
    round1 = await memory_store.search_memories(
        project_id=project_id,
        query=initial_query,
        limit=50
    )

    if round1['total_count'] == 0:
        print("No results, broadening search...")
        # Try single words from query
        words = initial_query.split()
        for word in words:
            result = await memory_store.search_memories(
                project_id=project_id,
                query=word,
                limit=10
            )
            if result['total_count'] > 0:
                print(f"Found results for: {word}")
                return result

    elif round1['total_count'] > 20:
        print("Too many results, refining...")
        # Add importance filter
        round2 = await memory_store.search_memories(
            project_id=project_id,
            query=initial_query,
            min_importance=0.7,
            limit=50
        )
        return round2

    return round1
```

### Strategy 3: Category-First Search

Search by category, then by content:

```python
async def category_first_search(project_id: str, category: str, query: str):
    """Search within a specific category first"""

    # Map category to memory type and tags
    category_mapping = {
        'security': {
            'types': ['decision', 'experience', 'convention'],
            'tags': ['security', 'auth', 'encryption']
        },
        'database': {
            'types': ['decision', 'preference', 'experience'],
            'tags': ['database', 'sql', 'migration']
        },
        'api': {
            'types': ['decision', 'convention'],
            'tags': ['api', 'rest', 'graphql']
        }
    }

    config = category_mapping.get(category, {})

    # Search within category
    results = []
    for mem_type in config.get('types', []):
        result = await memory_store.search_memories(
            project_id=project_id,
            query=query,
            memory_type=mem_type,
            tags=config.get('tags'),
            limit=20
        )
        results.extend(result['memories'])

    # Sort by relevance
    results.sort(key=lambda m: m['search_score'], reverse=True)

    return results

# Usage
security_results = await category_first_search(
    "my-project",
    "security",
    "password hashing"
)
```

### Strategy 4: Importance-Weighted Search

Prioritize critical memories:

```python
async def importance_weighted_search(project_id: str, query: str):
    """Search with importance-weighted scoring"""

    result = await memory_store.search_memories(
        project_id=project_id,
        query=query,
        limit=50
    )

    # Calculate weighted score
    for memory in result['memories']:
        search_score = memory['search_score']
        importance = memory['importance']

        # Weighted score: 70% relevance, 30% importance
        memory['weighted_score'] = (search_score * 0.7) + (importance * 10 * 0.3)

    # Re-sort by weighted score
    result['memories'].sort(key=lambda m: m['weighted_score'], reverse=True)

    return result

# Critical memories will rank higher even if search score is lower
```

### Strategy 5: Type-Specific Search

Different search strategies for different memory types:

```python
async def type_specific_search(project_id: str):
    """Use different search strategies per type"""

    # For decisions: prioritize high importance
    decisions = await memory_store.search_memories(
        project_id=project_id,
        memory_type="decision",
        min_importance=0.7,
        limit=20
    )

    # For experiences: get all (even low importance can be useful)
    experiences = await memory_store.search_memories(
        project_id=project_id,
        memory_type="experience",
        min_importance=0.0,
        limit=50
    )

    # For conventions: latest first
    conventions = await memory_store.search_memories(
        project_id=project_id,
        memory_type="convention",
        limit=20
    )
    # Sort by creation date
    conventions['memories'].sort(
        key=lambda m: m['created_at'],
        reverse=True
    )

    # For plans: filter out old ones
    plans = await memory_store.search_memories(
        project_id=project_id,
        memory_type="plan",
        limit=30
    )
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=90)
    recent_plans = [
        p for p in plans['memories']
        if datetime.fromisoformat(p['created_at']) > cutoff
    ]

    return {
        'decisions': decisions['memories'],
        'experiences': experiences['memories'],
        'conventions': conventions['memories'],
        'plans': recent_plans
    }
```

---

## Performance Tips

### 1. Use Appropriate Limits

```python
# For quick overview
search_memories(project_id, query="auth", limit=10)

# For comprehensive search
search_memories(project_id, query="auth", limit=50)

# For exhaustive search (use sparingly)
search_memories(project_id, query="auth", limit=100)
```

**Recommendation**: Start with limit=20, increase if needed

### 2. Filter Early

```python
# ❌ Slower: Get all, filter in Python
all_results = await memory_store.search_memories(project_id, limit=100)
critical = [m for m in all_results['memories'] if m['importance'] >= 0.8]

# ✅ Faster: Filter in database
critical = await memory_store.search_memories(
    project_id=project_id,
    min_importance=0.8,
    limit=20
)
```

### 3. Reuse Search Results

```python
# Cache search results if doing multiple operations
search_cache = {}

async def cached_search(project_id: str, query: str):
    cache_key = f"{project_id}:{query}"

    if cache_key not in search_cache:
        result = await memory_store.search_memories(project_id, query=query)
        search_cache[cache_key] = result

    return search_cache[cache_key]
```

### 4. Use Specific Queries

```python
# ❌ Too vague, returns many irrelevant results
query="system"

# ✅ Specific, returns focused results
query="authentication system jwt implementation"
```

### 5. Leverage Tags

```python
# ❌ Broad search
search_memories(project_id, query="bug")

# ✅ Narrow with tags
search_memories(
    project_id,
    query="timeout",
    tags=["database", "performance"],
    memory_type="experience"
)
```

---

## Search Result Ranking

### Default Ranking

Results are sorted by:
1. **Search Score** (primary) - Relevance to query
2. **Importance** (secondary) - Memory importance
3. **Created Date** (tertiary) - Newer first

### Understanding Search Scores

```python
for memory in result['memories']:
    score = memory['search_score']

    if score > 3.0:
        print("Excellent match")
    elif score > 2.0:
        print("Good match")
    elif score > 1.0:
        print("Moderate match")
    else:
        print("Weak match")
```

**Score Factors**:
- Term frequency in title (highest weight)
- Term frequency in content
- Term frequency in reason
- Tag matches
- Exact phrase matches

### Custom Ranking

Implement custom ranking logic:

```python
async def custom_ranked_search(project_id: str, query: str, preferences: dict):
    result = await memory_store.search_memories(
        project_id=project_id,
        query=query,
        limit=50
    )

    # Custom scoring
    for memory in result['memories']:
        score = 0

        # Base search score
        score += memory['search_score'] * preferences.get('relevance_weight', 0.5)

        # Importance factor
        score += memory['importance'] * 10 * preferences.get('importance_weight', 0.3)

        # Recency factor
        from datetime import datetime
        age_days = (datetime.utcnow() - datetime.fromisoformat(memory['created_at'])).days
        recency_score = max(0, 1 - (age_days / 365))  # Decay over 1 year
        score += recency_score * 10 * preferences.get('recency_weight', 0.2)

        # Type preference
        type_weights = preferences.get('type_weights', {})
        score += type_weights.get(memory['type'], 1.0)

        memory['custom_score'] = score

    # Sort by custom score
    result['memories'].sort(key=lambda m: m['custom_score'], reverse=True)

    return result

# Usage: Prioritize recent, high-importance decisions
results = await custom_ranked_search(
    "my-project",
    "database migration",
    preferences={
        'relevance_weight': 0.4,
        'importance_weight': 0.4,
        'recency_weight': 0.2,
        'type_weights': {
            'decision': 2.0,
            'experience': 1.5,
            'preference': 1.0
        }
    }
)
```

---

## Troubleshooting

### No Results Found

**Problem**: Search returns 0 results

**Solutions**:

```python
# 1. Try broader query
search_memories(project_id, query="auth")  # Instead of "authentication jwt token"

# 2. Remove filters
search_memories(project_id, query="auth")  # Remove memory_type, tags filters

# 3. Check if project has any memories
summary = await memory_store.get_project_summary(project_id)
print(f"Total memories: {summary['summary']['total_memories']}")

# 4. Verify project_id is correct
```

### Too Many Results

**Problem**: Search returns hundreds of low-relevance results

**Solutions**:

```python
# 1. Add importance filter
search_memories(project_id, query="database", min_importance=0.7)

# 2. Add type filter
search_memories(project_id, query="database", memory_type="decision")

# 3. Add tag filter
search_memories(project_id, query="database", tags=["postgresql"])

# 4. Use more specific query
search_memories(project_id, query="postgresql migration script")
```

### Low Relevance Results

**Problem**: Results don't match what you're looking for

**Solutions**:

```python
# 1. Use exact phrases
search_memories(project_id, query="'refresh token rotation'")

# 2. Use multiple specific keywords
search_memories(project_id, query="oauth refresh token jwt")

# 3. Combine query with filters
search_memories(
    project_id,
    query="token",
    tags=["auth", "security"],
    memory_type="decision"
)
```

### Slow Search

**Problem**: Search takes too long

**Solutions**:

```python
# 1. Reduce limit
search_memories(project_id, query="auth", limit=20)  # Instead of 100

# 2. Add filters to narrow scope
search_memories(
    project_id,
    query="auth",
    memory_type="decision",
    min_importance=0.7
)

# 3. Check database indexes
# Ensure Neo4j fulltext index exists (automatic in Memory Store)
```

---

## Best Practices

### 1. Start Broad, Then Narrow

```python
# First search: broad
broad = await search_memories(project_id, query="authentication")

# Analyze results
if len(broad['memories']) > 30:
    # Too many, narrow down
    narrow = await search_memories(
        project_id,
        query="authentication",
        memory_type="decision",
        min_importance=0.8
    )
```

### 2. Use Type Filters Appropriately

```python
# Looking for past decisions
search_memories(project_id, query="database", memory_type="decision")

# Looking for known issues
search_memories(project_id, query="timeout", memory_type="experience")

# Looking for standards
search_memories(project_id, memory_type="convention")
```

### 3. Tag Strategically

```python
# Search by domain
search_memories(project_id, tags=["auth"])

# Search by technology
search_memories(project_id, tags=["redis", "cache"])

# Search by status
search_memories(project_id, tags=["critical", "production"])
```

### 4. Consider Importance Thresholds

```python
# Critical only
search_memories(project_id, min_importance=0.9)

# Important and above
search_memories(project_id, min_importance=0.7)

# All memories (including low importance)
search_memories(project_id, min_importance=0.0)
```

### 5. Check Search Quality

```python
result = await search_memories(project_id, query="authentication")

# Review top results
print("Top 5 results:")
for memory in result['memories'][:5]:
    print(f"Score: {memory['search_score']:.2f}")
    print(f"  {memory['title']}")
    print(f"  Type: {memory['type']}, Importance: {memory['importance']}")

# If top results aren't relevant, refine query
```

---

## Next Steps

- **Manual Management**: See [manual.md](./manual.md) for CRUD operations
- **Auto-Extraction**: See [extraction.md](./extraction.md) for automatic memory capture
- **Overview**: See [overview.md](./overview.md) for system introduction
