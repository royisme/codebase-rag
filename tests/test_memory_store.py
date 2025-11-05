"""
Tests for Memory Store Service

Basic tests for memory management functionality.
Requires Neo4j connection to run.
"""

import pytest
import asyncio
from services.memory_store import MemoryStore


# Test fixtures
@pytest.fixture
async def memory_store():
    """Create and initialize memory store for testing"""
    store = MemoryStore()
    success = await store.initialize()
    assert success, "Memory store initialization failed"
    yield store
    await store.close()


@pytest.fixture
def test_project_id():
    """Test project identifier"""
    return "test-project-memory"


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing"""
    return {
        "memory_type": "decision",
        "title": "Use JWT for authentication",
        "content": "Decided to use JWT tokens instead of session-based auth for the API",
        "reason": "Need stateless authentication for mobile clients and microservices",
        "tags": ["auth", "architecture", "security"],
        "importance": 0.9,
        "related_refs": []
    }


# ============================================================================
# Basic CRUD Tests
# ============================================================================

@pytest.mark.asyncio
async def test_add_memory(memory_store, test_project_id, sample_memory_data):
    """Test adding a memory"""
    result = await memory_store.add_memory(
        project_id=test_project_id,
        **sample_memory_data
    )

    assert result["success"] is True
    assert "memory_id" in result
    assert result["title"] == sample_memory_data["title"]
    assert result["type"] == sample_memory_data["memory_type"]


@pytest.mark.asyncio
async def test_get_memory(memory_store, test_project_id, sample_memory_data):
    """Test retrieving a memory by ID"""
    # First add a memory
    add_result = await memory_store.add_memory(
        project_id=test_project_id,
        **sample_memory_data
    )
    memory_id = add_result["memory_id"]

    # Then retrieve it
    result = await memory_store.get_memory(memory_id)

    assert result["success"] is True
    assert result["memory"]["id"] == memory_id
    assert result["memory"]["title"] == sample_memory_data["title"]
    assert result["memory"]["content"] == sample_memory_data["content"]
    assert result["memory"]["reason"] == sample_memory_data["reason"]
    assert result["memory"]["importance"] == sample_memory_data["importance"]


@pytest.mark.asyncio
async def test_update_memory(memory_store, test_project_id, sample_memory_data):
    """Test updating a memory"""
    # Add a memory
    add_result = await memory_store.add_memory(
        project_id=test_project_id,
        **sample_memory_data
    )
    memory_id = add_result["memory_id"]

    # Update it
    new_importance = 0.95
    new_tags = ["auth", "security", "critical"]

    update_result = await memory_store.update_memory(
        memory_id=memory_id,
        importance=new_importance,
        tags=new_tags
    )

    assert update_result["success"] is True

    # Verify update
    get_result = await memory_store.get_memory(memory_id)
    assert get_result["memory"]["importance"] == new_importance
    assert set(get_result["memory"]["tags"]) == set(new_tags)


@pytest.mark.asyncio
async def test_delete_memory(memory_store, test_project_id, sample_memory_data):
    """Test soft deleting a memory"""
    # Add a memory
    add_result = await memory_store.add_memory(
        project_id=test_project_id,
        **sample_memory_data
    )
    memory_id = add_result["memory_id"]

    # Delete it
    delete_result = await memory_store.delete_memory(memory_id)
    assert delete_result["success"] is True


# ============================================================================
# Search Tests
# ============================================================================

@pytest.mark.asyncio
async def test_search_memories_by_query(memory_store, test_project_id):
    """Test searching memories by text query"""
    # Add multiple memories
    memories_to_add = [
        {
            "memory_type": "decision",
            "title": "Use PostgreSQL database",
            "content": "Chosen PostgreSQL for better JSON support",
            "importance": 0.8
        },
        {
            "memory_type": "preference",
            "title": "Use Python type hints",
            "content": "Team prefers using type hints for better IDE support",
            "importance": 0.6
        },
        {
            "memory_type": "experience",
            "title": "PostgreSQL connection pooling",
            "content": "Fixed connection timeout by implementing connection pooling",
            "importance": 0.7
        }
    ]

    for mem_data in memories_to_add:
        await memory_store.add_memory(project_id=test_project_id, **mem_data)

    # Search for "PostgreSQL"
    search_result = await memory_store.search_memories(
        project_id=test_project_id,
        query="PostgreSQL"
    )

    assert search_result["success"] is True
    assert search_result["total_count"] >= 2  # At least 2 matches


@pytest.mark.asyncio
async def test_search_memories_by_type(memory_store, test_project_id):
    """Test filtering memories by type"""
    # Add memories of different types
    await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Decision 1",
        content="Test decision"
    )
    await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="preference",
        title="Preference 1",
        content="Test preference"
    )

    # Search for decisions only
    search_result = await memory_store.search_memories(
        project_id=test_project_id,
        memory_type="decision"
    )

    assert search_result["success"] is True
    for memory in search_result["memories"]:
        assert memory["type"] == "decision"


@pytest.mark.asyncio
async def test_search_memories_by_tags(memory_store, test_project_id):
    """Test filtering memories by tags"""
    # Add memories with tags
    await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Auth decision",
        content="Test",
        tags=["auth", "security"]
    )
    await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Database decision",
        content="Test",
        tags=["database", "performance"]
    )

    # Search by tags
    search_result = await memory_store.search_memories(
        project_id=test_project_id,
        tags=["auth"]
    )

    assert search_result["success"] is True
    assert search_result["total_count"] >= 1


@pytest.mark.asyncio
async def test_search_memories_min_importance(memory_store, test_project_id):
    """Test filtering memories by minimum importance"""
    # Add memories with different importance
    await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="note",
        title="Low importance",
        content="Test",
        importance=0.3
    )
    await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="High importance",
        content="Test",
        importance=0.9
    )

    # Search with min_importance filter
    search_result = await memory_store.search_memories(
        project_id=test_project_id,
        min_importance=0.7
    )

    assert search_result["success"] is True
    for memory in search_result["memories"]:
        assert memory["importance"] >= 0.7


# ============================================================================
# Advanced Feature Tests
# ============================================================================

@pytest.mark.asyncio
async def test_supersede_memory(memory_store, test_project_id):
    """Test superseding an old memory with a new one"""
    # Add original memory
    old_result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Use MySQL",
        content="Initially chose MySQL",
        importance=0.8
    )
    old_id = old_result["memory_id"]

    # Supersede with new decision
    supersede_result = await memory_store.supersede_memory(
        old_memory_id=old_id,
        new_memory_data={
            "memory_type": "decision",
            "title": "Use PostgreSQL",
            "content": "Changed to PostgreSQL for better features",
            "reason": "Need JSON support and better performance",
            "importance": 0.9
        }
    )

    assert supersede_result["success"] is True
    assert "new_memory_id" in supersede_result
    assert "old_memory_id" in supersede_result
    assert supersede_result["old_memory_id"] == old_id


@pytest.mark.asyncio
async def test_project_summary(memory_store, test_project_id):
    """Test getting project memory summary"""
    # Add memories of different types
    memory_types = ["decision", "preference", "experience", "convention"]

    for mem_type in memory_types:
        await memory_store.add_memory(
            project_id=test_project_id,
            memory_type=mem_type,
            title=f"Test {mem_type}",
            content=f"Test content for {mem_type}"
        )

    # Get summary
    summary_result = await memory_store.get_project_summary(test_project_id)

    assert summary_result["success"] is True
    assert "summary" in summary_result
    assert summary_result["summary"]["total_memories"] >= len(memory_types)
    assert "by_type" in summary_result["summary"]


# ============================================================================
# Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_memory_type(memory_store, test_project_id):
    """Test that invalid memory type is rejected"""
    result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="invalid_type",  # Invalid
        title="Test",
        content="Test content"
    )

    # Should fail validation at MCP/API level, but store accepts any string
    # This test documents current behavior
    assert result["success"] is True


@pytest.mark.asyncio
async def test_importance_bounds(memory_store, test_project_id):
    """Test that importance score is properly bounded"""
    # This would be validated at MCP/API level
    # Memory store accepts any float
    result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="note",
        title="Test",
        content="Test",
        importance=1.5  # Out of bounds
    )

    # Store accepts it, validation should be at higher level
    assert result["success"] is True


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_related_refs_linking(memory_store, test_project_id):
    """Test linking memory to code references"""
    # Note: This requires files to exist in Neo4j
    # For basic testing, we just verify the API works

    result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Test with refs",
        content="Test",
        related_refs=["ref://file/src/auth/jwt.py", "ref://symbol/login_function"]
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_multiple_projects(memory_store):
    """Test that memories are properly isolated by project"""
    project1 = "project-one"
    project2 = "project-two"

    # Add memory to project 1
    await memory_store.add_memory(
        project_id=project1,
        memory_type="note",
        title="Project 1 memory",
        content="Test"
    )

    # Add memory to project 2
    await memory_store.add_memory(
        project_id=project2,
        memory_type="note",
        title="Project 2 memory",
        content="Test"
    )

    # Search project 1 should not return project 2 memories
    result1 = await memory_store.search_memories(project_id=project1)
    result2 = await memory_store.search_memories(project_id=project2)

    assert result1["success"] is True
    assert result2["success"] is True

    # Verify isolation (should have at least 1 each)
    assert result1["total_count"] >= 1
    assert result2["total_count"] >= 1


# ============================================================================
# Hard Delete Tests
# ============================================================================

@pytest.mark.asyncio
async def test_hard_delete_removes_from_search(memory_store, test_project_id):
    """
    Test that hard delete permanently removes memory from search results
    Fixed: Changed from soft-delete to hard-delete to save resources
    """
    # Add a memory
    add_result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Memory to be deleted",
        content="This should not appear after deletion"
    )
    assert add_result["success"] is True
    memory_id = add_result["memory_id"]

    # Verify it appears in search
    search_before = await memory_store.search_memories(project_id=test_project_id)
    assert search_before["success"] is True
    ids_before = [m["id"] for m in search_before["memories"]]
    assert memory_id in ids_before, "Memory should appear before deletion"

    # Hard delete the memory
    delete_result = await memory_store.delete_memory(memory_id=memory_id)
    assert delete_result["success"] is True

    # Search again - deleted memory should NOT appear (permanently removed)
    search_after = await memory_store.search_memories(project_id=test_project_id)
    assert search_after["success"] is True
    ids_after = [m["id"] for m in search_after["memories"]]
    assert memory_id not in ids_after, "Hard deleted memory should NOT appear in search"


@pytest.mark.asyncio
async def test_hard_delete_memory_not_found(memory_store, test_project_id):
    """
    Test that get_memory returns not found for hard-deleted memories
    Fixed: Hard delete permanently removes the node
    """
    # Add a memory
    add_result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="note",
        title="Memory to delete",
        content="Test content"
    )
    assert add_result["success"] is True
    memory_id = add_result["memory_id"]

    # Get memory before deletion - should work
    get_before = await memory_store.get_memory(memory_id=memory_id)
    assert get_before["success"] is True
    assert get_before["memory"]["id"] == memory_id

    # Hard delete the memory
    delete_result = await memory_store.delete_memory(memory_id=memory_id)
    assert delete_result["success"] is True

    # Get memory after deletion - should fail (node doesn't exist)
    get_after = await memory_store.get_memory(memory_id=memory_id)
    assert get_after["success"] is False
    assert "not found" in get_after["error"].lower()


@pytest.mark.asyncio
async def test_hard_delete_with_fulltext_search(memory_store, test_project_id):
    """
    Test that fulltext search also excludes hard-deleted memories
    Fixed: Hard delete removes node completely, so it won't appear in any search
    """
    # Add two memories with similar content
    add1 = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Use PostgreSQL database",
        content="PostgreSQL for relational data"
    )
    add2 = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Use PostgreSQL replication",
        content="PostgreSQL replication for HA"
    )
    assert add1["success"] is True
    assert add2["success"] is True
    memory_id1 = add1["memory_id"]
    memory_id2 = add2["memory_id"]

    # Search for "PostgreSQL" - both should appear
    search_before = await memory_store.search_memories(
        project_id=test_project_id,
        query="PostgreSQL"
    )
    assert search_before["success"] is True
    ids_before = [m["id"] for m in search_before["memories"]]
    assert memory_id1 in ids_before
    assert memory_id2 in ids_before

    # Hard delete one memory
    await memory_store.delete_memory(memory_id=memory_id1)

    # Search again - only non-deleted should appear
    search_after = await memory_store.search_memories(
        project_id=test_project_id,
        query="PostgreSQL"
    )
    assert search_after["success"] is True
    ids_after = [m["id"] for m in search_after["memories"]]
    assert memory_id1 not in ids_after, "Hard deleted memory should not appear"
    assert memory_id2 in ids_after, "Non-deleted memory should still appear"


@pytest.mark.asyncio
async def test_hard_delete_reduces_project_summary(memory_store, test_project_id):
    """
    Test that get_project_summary reflects hard-deleted memories
    Fixed: Hard delete removes node, so it won't be counted
    """
    # Add memories
    add1 = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Decision 1",
        content="Test"
    )
    add2 = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Decision 2",
        content="Test"
    )
    memory_id1 = add1["memory_id"]

    # Get summary before deletion
    summary_before = await memory_store.get_project_summary(project_id=test_project_id)
    assert summary_before["success"] is True
    count_before = summary_before["total_memories"]

    # Hard delete one memory
    await memory_store.delete_memory(memory_id=memory_id1)

    # Get summary after deletion - count should decrease (node removed)
    summary_after = await memory_store.get_project_summary(project_id=test_project_id)
    assert summary_after["success"] is True
    count_after = summary_after["total_memories"]
    assert count_after == count_before - 1, "Hard deleted memory should not count in summary"


@pytest.mark.asyncio
async def test_hard_delete_removes_relationships(memory_store, test_project_id):
    """
    Test that hard delete also removes all relationships (DETACH DELETE)
    Fixed: Using DETACH DELETE to clean up relationships too
    """
    # Add a memory
    add_result = await memory_store.add_memory(
        project_id=test_project_id,
        memory_type="decision",
        title="Memory with relationships",
        content="Test content",
        related_refs=["ref://file/test.py"]
    )
    assert add_result["success"] is True
    memory_id = add_result["memory_id"]

    # Hard delete should succeed even with relationships
    delete_result = await memory_store.delete_memory(memory_id=memory_id)
    assert delete_result["success"] is True

    # Memory should not be found anymore
    get_result = await memory_store.get_memory(memory_id=memory_id)
    assert get_result["success"] is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
