"""
Pytest configuration and fixtures for codebase-rag tests
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

# Ensure the project root and `src/` directory are available for imports.
# pytest executes from the repository root, but our package lives in `src/`.
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / "src"

for path in (ROOT_DIR, SRC_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from fastapi.testclient import TestClient
from src.codebase_rag.services.code import Neo4jGraphService


@pytest.fixture(scope="session")
def test_repo_path(tmp_path_factory):
    """Create a temporary test repository with sample files"""
    repo_dir = tmp_path_factory.mktemp("test_repo")

    # Create sample Python files
    (repo_dir / "main.py").write_text("""
def main():
    print("Hello World")

if __name__ == "__main__":
    main()
""")

    (repo_dir / "utils").mkdir()
    (repo_dir / "utils" / "__init__.py").write_text("")
    (repo_dir / "utils" / "helpers.py").write_text("""
def helper_function():
    return "helper"

class HelperClass:
    def method(self):
        pass
""")

    # Create sample TypeScript files
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "index.ts").write_text("""
function greet(name: string): string {
    return `Hello, ${name}`;
}

export { greet };
""")

    return str(repo_dir)


@pytest.fixture(scope="session")
def test_repo_id():
    """Test repository ID"""
    return "test-repo-001"


@pytest.fixture(scope="function")
def graph_service():
    """
    Graph service fixture
    Note: This requires a running Neo4j instance
    """
    service = Neo4jGraphService()
    # Skip if Neo4j is not available
    try:
        import asyncio
        connected = asyncio.run(service.connect())
        if connected:
            yield service
            asyncio.run(service.close())
        else:
            pytest.skip("Neo4j not available for testing")
    except Exception as e:
        pytest.skip(f"Neo4j connection failed: {e}")


@pytest.fixture(scope="module")
def test_client():
    """FastAPI test client"""
    from src.codebase_rag.server.web import app
    return TestClient(app)


@pytest.fixture
def sample_files():
    """Sample file data for testing"""
    return [
        {
            "path": "src/auth/token.py",
            "lang": "python",
            "size": 1024,
            "content": "def generate_token(): pass",
            "sha": "abc123"
        },
        {
            "path": "src/auth/user.py",
            "lang": "python",
            "size": 2048,
            "content": "class User: pass",
            "sha": "def456"
        },
        {
            "path": "src/api/routes.ts",
            "lang": "typescript",
            "size": 3072,
            "content": "export function handler() {}",
            "sha": "ghi789"
        }
    ]


# ============================================================================
# MCP Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_knowledge_service():
    """Mock Neo4jKnowledgeService for testing"""
    service = AsyncMock()
    service.query = AsyncMock()
    service.search_similar_nodes = AsyncMock()
    service.add_document = AsyncMock()
    service.add_file = AsyncMock()
    service.get_graph_schema = AsyncMock()
    service.get_statistics = AsyncMock()
    service.clear_knowledge_base = AsyncMock()
    return service


@pytest.fixture
def mock_memory_store():
    """Mock MemoryStore for testing"""
    store = AsyncMock()
    store.add_memory = AsyncMock()
    store.search_memories = AsyncMock()
    store.get_memory = AsyncMock()
    store.update_memory = AsyncMock()
    store.delete_memory = AsyncMock()
    store.supersede_memory = AsyncMock()
    store.get_project_summary = AsyncMock()
    return store


@pytest.fixture
def mock_task_queue():
    """Mock TaskQueue for testing"""
    queue = AsyncMock()
    queue.get_task = AsyncMock()
    queue.get_all_tasks = AsyncMock()
    queue.cancel_task = AsyncMock()
    queue.get_stats = AsyncMock()
    return queue


@pytest.fixture
def mock_task_status():
    """Mock TaskStatus enum for testing"""
    from unittest.mock import Mock

    class MockTaskStatus:
        PENDING = Mock(value="pending")
        RUNNING = Mock(value="running")
        COMPLETED = Mock(value="completed")
        FAILED = Mock(value="failed")

    return MockTaskStatus


@pytest.fixture
def mock_graph_service():
    """Mock graph service for code graph operations"""
    service = AsyncMock()
    service.fulltext_search = AsyncMock()
    service.impact_analysis = AsyncMock()
    return service


@pytest.fixture
def mock_code_ingestor():
    """Mock code ingestor factory"""
    return Mock()


@pytest.fixture
def mock_git_utils():
    """Mock git utilities"""
    utils = Mock()
    utils.is_git_repo = Mock()
    return utils


@pytest.fixture
def mock_ranker():
    """Mock file ranker for code graph"""
    ranker = Mock()
    ranker.rank_files = Mock()
    return ranker


@pytest.fixture
def mock_pack_builder():
    """Mock context pack builder"""
    builder = AsyncMock()
    builder.build_context_pack = AsyncMock()
    return builder


@pytest.fixture
def mock_submit_document_task():
    """Mock document processing task submission"""
    return AsyncMock()


@pytest.fixture
def mock_submit_directory_task():
    """Mock directory processing task submission"""
    return AsyncMock()


@pytest.fixture
def mock_settings():
    """Mock settings object"""
    from unittest.mock import Mock

    settings = Mock()
    settings.llm_provider = "ollama"
    settings.embedding_provider = "ollama"
    settings.neo4j_uri = "bolt://localhost:7687"
    return settings


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing"""
    return {
        "project_id": "test-project",
        "memory_type": "decision",
        "title": "Use JWT for authentication",
        "content": "Decided to use JWT tokens for API authentication",
        "reason": "Need stateless auth for mobile clients",
        "tags": ["auth", "security"],
        "importance": 0.9,
        "related_refs": []
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    from unittest.mock import Mock
    from datetime import datetime

    task = Mock()
    task.task_id = "task-123"
    task.status = Mock(value="running")
    task.created_at = datetime.now().isoformat()
    task.result = None
    task.error = None
    return task


@pytest.fixture
def sample_query_result():
    """Sample knowledge query result"""
    return {
        "success": True,
        "answer": "This is a test answer from the knowledge base.",
        "source_nodes": [
            {"text": "Source node 1 with relevant information"},
            {"text": "Source node 2 with additional context"}
        ]
    }


@pytest.fixture
def sample_memory_list():
    """Sample list of memories for testing"""
    return [
        {
            "id": "mem-1",
            "type": "decision",
            "title": "Use PostgreSQL",
            "content": "Selected PostgreSQL for main database",
            "importance": 0.9,
            "tags": ["database", "architecture"]
        },
        {
            "id": "mem-2",
            "type": "preference",
            "title": "Code style",
            "content": "Use black formatter for Python",
            "importance": 0.6,
            "tags": ["code-style", "python"]
        },
        {
            "id": "mem-3",
            "type": "experience",
            "title": "Docker networking",
            "content": "Use service names in Docker compose",
            "importance": 0.7,
            "tags": ["docker", "networking"]
        }
    ]


@pytest.fixture
def sample_code_nodes():
    """Sample code graph nodes for testing"""
    return [
        {
            "path": "src/auth/token.py",
            "name": "token.py",
            "score": 0.95,
            "ref": "ref://token",
            "type": "file"
        },
        {
            "path": "src/auth/user.py",
            "name": "user.py",
            "score": 0.85,
            "ref": "ref://user",
            "type": "file"
        },
        {
            "path": "src/api/routes.py",
            "name": "routes.py",
            "score": 0.75,
            "ref": "ref://routes",
            "type": "file"
        }
    ]


# Test configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Neo4j)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
