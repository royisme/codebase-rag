"""
Memory Store Usage Examples

This file demonstrates how to use the Memory Store for project knowledge management.

Two main approaches:
1. MCP Tools (for AI assistants like Claude Desktop)
2. HTTP API (for web clients)
"""

import asyncio
import httpx
from typing import Dict, Any


# ============================================================================
# Example 1: Using Memory Store Service Directly
# ============================================================================

async def example_direct_service_usage():
    """Example: Using MemoryStore service directly in Python"""
    from services.memory_store import MemoryStore

    # Initialize
    store = MemoryStore()
    await store.initialize()

    project_id = "my-awesome-project"

    # Add a decision memory
    result = await store.add_memory(
        project_id=project_id,
        memory_type="decision",
        title="Use JWT for authentication",
        content="Decided to use JWT tokens instead of session-based authentication",
        reason="Need stateless authentication for mobile clients and microservices architecture",
        tags=["auth", "architecture", "security"],
        importance=0.9,
        related_refs=["ref://file/src/auth/jwt.py", "ref://file/src/auth/middleware.py"]
    )

    print(f"✅ Added decision memory: {result['memory_id']}")

    # Add an experience memory
    exp_result = await store.add_memory(
        project_id=project_id,
        memory_type="experience",
        title="Redis connection timeout in Docker",
        content="Redis connections were timing out when using 'localhost' in Docker environment",
        reason="Docker networking requires using service name 'redis' instead of 'localhost'",
        tags=["docker", "redis", "networking"],
        importance=0.7
    )

    print(f"✅ Added experience memory: {exp_result['memory_id']}")

    # Add a preference memory
    pref_result = await store.add_memory(
        project_id=project_id,
        memory_type="preference",
        title="Use raw SQL instead of ORM",
        content="Team prefers writing raw SQL queries over using an ORM like SQLAlchemy",
        reason="Better performance control and team is more familiar with SQL",
        tags=["database", "coding-style"],
        importance=0.6
    )

    print(f"✅ Added preference memory: {pref_result['memory_id']}")

    # Search for memories
    print("\n🔍 Searching for authentication-related memories...")
    search_result = await store.search_memories(
        project_id=project_id,
        query="authentication",
        min_importance=0.5
    )

    for memory in search_result['memories']:
        print(f"  - [{memory['type']}] {memory['title']} (importance: {memory['importance']})")

    # Get project summary
    print(f"\n📊 Project summary for '{project_id}':")
    summary = await store.get_project_summary(project_id)

    if summary['success']:
        total = summary['summary']['total_memories']
        print(f"  Total memories: {total}")

        for mem_type, data in summary['summary']['by_type'].items():
            count = data['count']
            print(f"  - {mem_type}: {count}")

    await store.close()


# ============================================================================
# Example 2: Using HTTP API
# ============================================================================

async def example_http_api_usage():
    """Example: Using Memory Management HTTP API"""

    base_url = "http://localhost:8000/api/v1/memory"

    async with httpx.AsyncClient() as client:
        # Add a decision memory
        add_response = await client.post(
            f"{base_url}/add",
            json={
                "project_id": "web-app-project",
                "memory_type": "decision",
                "title": "Use PostgreSQL for main database",
                "content": "Selected PostgreSQL over MySQL for the main application database",
                "reason": "Need better JSON support, full-text search, and advanced indexing",
                "tags": ["database", "architecture"],
                "importance": 0.9,
                "related_refs": ["ref://file/config/database.py"]
            }
        )

        if add_response.status_code == 200:
            memory_id = add_response.json()["memory_id"]
            print(f"✅ Added memory via HTTP API: {memory_id}")

            # Get the memory back
            get_response = await client.get(f"{base_url}/{memory_id}")
            if get_response.status_code == 200:
                memory = get_response.json()["memory"]
                print(f"  Title: {memory['title']}")
                print(f"  Type: {memory['type']}")
                print(f"  Importance: {memory['importance']}")

        # Search memories
        search_response = await client.post(
            f"{base_url}/search",
            json={
                "project_id": "web-app-project",
                "memory_type": "decision",
                "min_importance": 0.7,
                "limit": 10
            }
        )

        if search_response.status_code == 200:
            results = search_response.json()
            print(f"\n🔍 Found {results['total_count']} high-importance decisions")

        # Get project summary
        summary_response = await client.get(
            f"{base_url}/project/web-app-project/summary"
        )

        if summary_response.status_code == 200:
            summary = summary_response.json()["summary"]
            print(f"\n📊 Project Summary:")
            print(f"  Total: {summary['total_memories']} memories")


# ============================================================================
# Example 3: Typical AI Agent Workflow
# ============================================================================

async def example_ai_agent_workflow():
    """
    Example workflow showing how an AI agent would use memories.

    This simulates:
    1. Agent starts working on auth feature
    2. Agent searches for related memories
    3. Agent finds previous decisions and preferences
    4. Agent implements feature following established patterns
    5. Agent saves new learnings as memories
    """
    from services.memory_store import MemoryStore

    store = MemoryStore()
    await store.initialize()

    project_id = "e-commerce-platform"

    print("🤖 AI Agent starting work on authentication feature...")

    # Step 1: Search for existing decisions and preferences
    print("\n1️⃣ Checking for existing authentication-related memories...")
    auth_memories = await store.search_memories(
        project_id=project_id,
        query="authentication auth",
        min_importance=0.5
    )

    if auth_memories['total_count'] > 0:
        print(f"   Found {auth_memories['total_count']} relevant memories:")
        for mem in auth_memories['memories'][:3]:
            print(f"   - {mem['title']} ({mem['type']})")
    else:
        print("   No existing memories found - this is a new area")

    # Step 2: Check for coding style preferences
    print("\n2️⃣ Checking coding style preferences...")
    style_prefs = await store.search_memories(
        project_id=project_id,
        memory_type="preference",
        tags=["coding-style"]
    )

    if style_prefs['total_count'] > 0:
        print(f"   Found {style_prefs['total_count']} style preferences")

    # Step 3: Check for known issues/experiences
    print("\n3️⃣ Checking for past experiences and known issues...")
    experiences = await store.search_memories(
        project_id=project_id,
        memory_type="experience",
        tags=["security", "auth"]
    )

    if experiences['total_count'] > 0:
        print(f"   Found {experiences['total_count']} past experiences")

    # Step 4: Implement feature (simulated)
    print("\n4️⃣ Implementing authentication feature...")
    print("   (Implementation happens here...)")

    # Step 5: Save new learnings as memory
    print("\n5️⃣ Saving learnings as memories...")

    # Save the implementation decision
    await store.add_memory(
        project_id=project_id,
        memory_type="decision",
        title="Implement OAuth 2.0 with JWT tokens",
        content="Implemented OAuth 2.0 authorization code flow with JWT access tokens",
        reason="Provides standard auth flow compatible with third-party integrations",
        tags=["auth", "oauth", "jwt"],
        importance=0.8,
        related_refs=["ref://file/src/auth/oauth.py"]
    )

    print("   ✅ Saved implementation decision")

    # Save an experience if something went wrong
    await store.add_memory(
        project_id=project_id,
        memory_type="experience",
        title="Token refresh endpoint needs CORS headers",
        content="OAuth token refresh endpoint was failing in browser due to missing CORS headers",
        reason="Browser blocks refresh requests without proper CORS configuration",
        tags=["auth", "cors", "browser"],
        importance=0.6
    )

    print("   ✅ Saved debugging experience")

    print("\n✨ AI Agent workflow complete!")

    await store.close()


# ============================================================================
# Example 4: Memory Evolution (Superseding)
# ============================================================================

async def example_memory_evolution():
    """
    Example showing how memories evolve over time.

    Demonstrates using supersede_memory when decisions change.
    """
    from services.memory_store import MemoryStore

    store = MemoryStore()
    await store.initialize()

    project_id = "mobile-app"

    # Original decision: Use MySQL
    print("📝 Initial decision: Use MySQL")
    original = await store.add_memory(
        project_id=project_id,
        memory_type="decision",
        title="Use MySQL as primary database",
        content="Selected MySQL for the application database",
        reason="Team familiarity and existing infrastructure",
        importance=0.7
    )

    original_id = original["memory_id"]

    # Time passes... requirements change

    # New decision: Switch to PostgreSQL
    print("\n🔄 Decision changed: Switching to PostgreSQL")
    supersede_result = await store.supersede_memory(
        old_memory_id=original_id,
        new_memory_data={
            "memory_type": "decision",
            "title": "Migrate from MySQL to PostgreSQL",
            "content": "Migrated from MySQL to PostgreSQL",
            "reason": "Need advanced features: JSONB, full-text search, and better geo support",
            "tags": ["database", "migration", "postgresql"],
            "importance": 0.9
        }
    )

    new_id = supersede_result["new_memory_id"]
    print(f"   ✅ New decision created: {new_id}")
    print(f"   ⚠️  Old decision superseded: {original_id}")

    # The old memory is still in the database but marked as superseded
    # This preserves history while making the new decision primary

    await store.close()


# ============================================================================
# Example 5: MCP Tool Usage (for Claude Desktop etc.)
# ============================================================================

def example_mcp_tool_usage():
    """
    Example MCP tool invocations for AI assistants.

    These would be called by Claude Desktop, VSCode with MCP, etc.
    """

    print("""
    # MCP Tool Usage Examples (for Claude Desktop, etc.)

    ## Add a decision memory
    ```
    add_memory(
        project_id="my-project",
        memory_type="decision",
        title="Use React for frontend",
        content="Selected React over Vue and Angular",
        reason="Team experience and ecosystem maturity",
        tags=["frontend", "react"],
        importance=0.8
    )
    ```

    ## Search for memories when starting a task
    ```
    search_memories(
        project_id="my-project",
        query="database migration",
        memory_type="experience",
        min_importance=0.5
    )
    ```

    ## Get project overview before starting work
    ```
    get_project_summary(project_id="my-project")
    ```

    ## Update a memory's importance
    ```
    update_memory(
        memory_id="abc-123-def",
        importance=0.95,
        tags=["critical", "security", "auth"]
    )
    ```

    ## When a decision changes
    ```
    supersede_memory(
        old_memory_id="old-decision-id",
        new_memory_type="decision",
        new_title="Updated architecture decision",
        new_content="Changed approach based on new requirements",
        new_reason="Performance requirements increased",
        new_importance=0.9
    )
    ```
    """)


# ============================================================================
# Run Examples
# ============================================================================

async def main():
    """Run all examples"""

    print("=" * 70)
    print("MEMORY STORE USAGE EXAMPLES")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("Example 1: Direct Service Usage")
    print("=" * 70)
    await example_direct_service_usage()

    print("\n" + "=" * 70)
    print("Example 2: HTTP API Usage")
    print("=" * 70)
    print("(Requires server running at http://localhost:8000)")
    # Uncomment to run:
    # await example_http_api_usage()

    print("\n" + "=" * 70)
    print("Example 3: AI Agent Workflow")
    print("=" * 70)
    await example_ai_agent_workflow()

    print("\n" + "=" * 70)
    print("Example 4: Memory Evolution")
    print("=" * 70)
    await example_memory_evolution()

    print("\n" + "=" * 70)
    print("Example 5: MCP Tool Usage")
    print("=" * 70)
    example_mcp_tool_usage()


if __name__ == "__main__":
    asyncio.run(main())
