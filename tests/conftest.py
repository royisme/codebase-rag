"""
Pytest configuration and fixtures for codebase-rag tests
"""
import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from services.graph_service import Neo4jGraphService


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
    from main import app
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


# Test configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Neo4j)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
