# Testing Guide

This guide covers testing practices, conventions, and procedures for the Code Graph Knowledge System.

## Table of Contents

- [Overview](#overview)
- [Test Organization](#test-organization)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Fixtures](#test-fixtures)
- [Mocking Strategies](#mocking-strategies)
- [Coverage Requirements](#coverage-requirements)
- [CI/CD Testing](#cicd-testing)
- [Best Practices](#best-practices)

## Overview

We use **pytest** as our testing framework with support for:

- **Async/await** testing with `pytest-asyncio`
- **Code coverage** tracking with `pytest-cov`
- **Mocking** capabilities with `pytest-mock`
- **Test markers** for categorizing tests

### Testing Philosophy

- **Test early, test often** - Write tests as you develop features
- **Fast unit tests** - Keep unit tests fast and isolated
- **Meaningful integration tests** - Test real interactions with Neo4j
- **High coverage** - Aim for 80%+ coverage on new code
- **Clear test names** - Test names should describe what is being tested

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_mcp_handlers.py     # MCP handler unit tests
├── test_mcp_integration.py  # MCP integration tests
├── test_mcp_utils.py        # MCP utility tests
├── test_memory_store.py     # Memory store tests
├── test_context_pack.py     # Context packing tests
├── test_ingest.py           # Document ingestion tests
├── test_related.py          # Related code tests
└── README.md                # Test documentation
```

### Test File Naming

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

Example:
```python
# test_memory_store.py
class TestMemoryStore:
    def test_add_memory_success(self):
        pass

    async def test_search_memories_async(self):
        pass
```

## Test Types

We use pytest markers to categorize tests:

### Unit Tests

Fast tests with no external dependencies (mocked services).

```python
import pytest

@pytest.mark.unit
async def test_parse_memory_type():
    """Test memory type parsing logic."""
    from services.memory_store import parse_memory_type

    result = parse_memory_type("decision")
    assert result == "decision"

    with pytest.raises(ValueError):
        parse_memory_type("invalid_type")
```

**Characteristics:**
- No database connections
- No external API calls
- No file I/O (use mocks)
- Run in milliseconds
- Can run in parallel

### Integration Tests

Tests that interact with real services (Neo4j, etc.).

```python
import pytest

@pytest.mark.integration
async def test_neo4j_connection(neo4j_service):
    """Test actual Neo4j connection and query."""
    result = await neo4j_service.execute_query("RETURN 1 as num")
    assert result["success"] is True
    assert result["data"][0]["num"] == 1
```

**Characteristics:**
- Require Neo4j running
- May require LLM provider
- Slower execution
- May need setup/teardown
- Test real integrations

### Slow Tests

Tests that take significant time (> 1 second).

```python
import pytest

@pytest.mark.slow
@pytest.mark.integration
async def test_large_document_processing(knowledge_service):
    """Test processing of large document."""
    large_doc = "x" * 100000  # 100KB document
    result = await knowledge_service.ingest_document(large_doc)
    assert result["success"] is True
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with extra verbosity (show test names)
pytest tests/ -vv
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/test_memory_store.py

# Run a specific test class
pytest tests/test_memory_store.py::TestMemoryStore

# Run a specific test function
pytest tests/test_memory_store.py::TestMemoryStore::test_add_memory_success

# Run tests matching a pattern
pytest tests/ -k "memory"
pytest tests/ -k "test_add or test_search"
```

### Running by Markers

```bash
# Run only unit tests (fast)
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run integration tests but not slow ones
pytest tests/ -m "integration and not slow"

# Run all except slow tests
pytest tests/ -m "not slow"
```

### Coverage Reports

```bash
# Run with coverage for specific modules
pytest tests/ --cov=services --cov=api --cov=mcp_tools

# Generate HTML coverage report
pytest tests/ --cov=services --cov=api --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Generate terminal coverage report
pytest tests/ --cov=services --cov-report=term

# Show missing lines
pytest tests/ --cov=services --cov-report=term-missing
```

### Debugging Tests

```bash
# Stop on first failure
pytest tests/ -x

# Show local variables on failure
pytest tests/ -l

# Enter debugger on failure
pytest tests/ --pdb

# Show print statements
pytest tests/ -s

# Increase verbosity for debugging
pytest tests/ -vv --tb=long
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4

# Run unit tests in parallel
pytest tests/ -m unit -n auto
```

## Writing Tests

### Test Function Structure

Follow the **Arrange-Act-Assert** pattern:

```python
import pytest

async def test_add_memory_success():
    """Test adding a memory successfully."""
    # Arrange - Set up test data and dependencies
    project_id = "test-project"
    memory_data = {
        "type": "decision",
        "title": "Use PostgreSQL",
        "content": "Selected PostgreSQL for database",
        "importance": 0.8
    }

    # Act - Execute the code being tested
    result = await memory_store.add_memory(
        project_id=project_id,
        **memory_data
    )

    # Assert - Verify the results
    assert result["success"] is True
    assert "memory_id" in result
    assert result["memory"]["title"] == memory_data["title"]
```

### Testing Async Functions

All async functions must use `pytest.mark.asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Test asynchronous operation."""
    result = await some_async_function()
    assert result is not None
```

### Testing Exceptions

```python
import pytest

def test_invalid_input_raises_error():
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        parse_invalid_input("bad data")

    assert "invalid format" in str(exc_info.value)

async def test_async_exception():
    """Test async function raises exception."""
    with pytest.raises(ConnectionError):
        await connect_to_invalid_service()
```

### Parametrized Tests

Test multiple scenarios with one test function:

```python
import pytest

@pytest.mark.parametrize("memory_type,expected", [
    ("decision", "decision"),
    ("preference", "preference"),
    ("experience", "experience"),
    ("convention", "convention"),
    ("plan", "plan"),
])
def test_memory_type_validation(memory_type, expected):
    """Test memory type validation for various types."""
    result = validate_memory_type(memory_type)
    assert result == expected

@pytest.mark.parametrize("invalid_type", [
    "invalid",
    "unknown",
    "",
    None,
    123,
])
def test_invalid_memory_type(invalid_type):
    """Test that invalid memory types raise errors."""
    with pytest.raises(ValueError):
        validate_memory_type(invalid_type)
```

### Testing with Fixtures

```python
import pytest

@pytest.fixture
def sample_memory_data():
    """Provide sample memory data for tests."""
    return {
        "project_id": "test-project",
        "memory_type": "decision",
        "title": "Test Decision",
        "content": "Test content",
        "importance": 0.7,
        "tags": ["test", "example"]
    }

def test_with_fixture(sample_memory_data):
    """Test using fixture data."""
    assert sample_memory_data["memory_type"] == "decision"
    assert sample_memory_data["importance"] == 0.7
```

## Test Fixtures

### Available Fixtures

Fixtures are defined in `tests/conftest.py`:

#### mock_neo4j_driver
```python
@pytest.fixture
def mock_neo4j_driver(mocker):
    """Mock Neo4j driver for unit tests."""
    # Returns a mock Neo4j driver
```

#### mock_llm_service
```python
@pytest.fixture
def mock_llm_service(mocker):
    """Mock LLM service for unit tests."""
    # Returns a mock LLM service
```

#### mock_knowledge_service
```python
@pytest.fixture
async def mock_knowledge_service(mocker):
    """Mock knowledge service for unit tests."""
    # Returns a mock knowledge service
```

#### neo4j_test_driver
```python
@pytest.fixture(scope="session")
def neo4j_test_driver():
    """Real Neo4j driver for integration tests."""
    # Returns actual Neo4j driver connected to test database
```

### Creating Custom Fixtures

```python
import pytest
from typing import Generator

@pytest.fixture
def temp_directory(tmp_path) -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    yield test_dir
    # Cleanup happens automatically with tmp_path

@pytest.fixture
async def initialized_memory_store():
    """Provide an initialized memory store."""
    store = MemoryStore()
    await store.initialize()
    yield store
    await store.cleanup()
```

### Fixture Scopes

```python
# Function scope (default) - New instance per test
@pytest.fixture
def per_test_fixture():
    return "new instance"

# Class scope - New instance per test class
@pytest.fixture(scope="class")
def per_class_fixture():
    return "shared in class"

# Module scope - New instance per test file
@pytest.fixture(scope="module")
def per_module_fixture():
    return "shared in module"

# Session scope - One instance for entire test session
@pytest.fixture(scope="session")
def per_session_fixture():
    return "shared across all tests"
```

## Mocking Strategies

### Mocking with pytest-mock

```python
def test_with_mock(mocker):
    """Test using mocker fixture."""
    # Mock a function
    mock_func = mocker.patch('services.memory_store.some_function')
    mock_func.return_value = "mocked result"

    # Call code that uses the function
    result = call_code_using_function()

    # Assert mock was called
    mock_func.assert_called_once()
    assert result == "mocked result"
```

### Mocking Neo4j Queries

```python
def test_neo4j_query(mocker):
    """Test code that queries Neo4j."""
    mock_driver = mocker.Mock()
    mock_session = mocker.Mock()
    mock_result = mocker.Mock()

    # Setup mock chain
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = mock_result
    mock_result.data.return_value = [{"id": "123", "title": "Test"}]

    # Test your code
    result = query_neo4j(mock_driver, "MATCH (n) RETURN n")

    assert result[0]["id"] == "123"
    mock_session.run.assert_called_once()
```

### Mocking Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_mock(mocker):
    """Test with async mock."""
    # Create async mock
    mock_async_func = mocker.AsyncMock(return_value={"success": True})

    # Patch the async function
    mocker.patch('services.memory_store.async_function', mock_async_func)

    # Call code that uses it
    result = await some_code_using_async_function()

    # Assert
    assert result["success"] is True
    mock_async_func.assert_awaited_once()
```

### Mocking Environment Variables

```python
def test_with_env_vars(mocker):
    """Test with environment variables."""
    mocker.patch.dict('os.environ', {
        'NEO4J_URI': 'bolt://test:7687',
        'NEO4J_USER': 'test',
        'NEO4J_PASSWORD': 'testpass'
    })

    from core.config import settings
    assert settings.neo4j_uri == 'bolt://test:7687'
```

## Coverage Requirements

### Coverage Goals

- **New Features**: 80%+ coverage
- **Bug Fixes**: 100% coverage of fixed code path
- **Critical Paths**: 90%+ coverage
- **Overall Project**: 70%+ coverage

### Checking Coverage

```bash
# Generate coverage report
pytest tests/ --cov=services --cov=api --cov=mcp_tools --cov-report=term-missing

# Coverage output shows:
# - Lines covered
# - Lines missed
# - Coverage percentage
# - Missing line numbers
```

### Improving Coverage

```bash
# Find uncovered code
pytest tests/ --cov=services --cov-report=term-missing | grep "MISSED"

# Focus on specific module
pytest tests/ --cov=services.memory_store --cov-report=term-missing

# Generate HTML report for detailed view
pytest tests/ --cov=services --cov-report=html
open htmlcov/index.html
```

### Coverage Configuration

Coverage settings in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["mcp_tools", "services", "api", "core"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

## CI/CD Testing

### GitHub Actions

Tests run automatically on:
- **Push to main/develop** - Full test suite
- **Pull requests** - Full test suite with coverage
- **Scheduled** - Nightly integration tests

### CI Test Configuration

See `.github/workflows/ci.yml` and `.github/workflows/pr-tests.yml`.

#### Test Matrix

Tests run on:
- **Python versions**: 3.13
- **OS**: Ubuntu latest
- **Neo4j**: 5.14

#### Running Tests Locally Like CI

```bash
# Start Neo4j with test configuration
docker run -d \
  --name neo4j-test \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/testpassword \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5.14

# Set environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=testpassword

# Run tests like CI
pytest tests/ -v --tb=short --cov=services --cov=api --cov=mcp_tools

# Cleanup
docker stop neo4j-test
docker rm neo4j-test
```

## Best Practices

### Do's

✅ **Write tests first** (TDD) when fixing bugs
✅ **Use descriptive test names** that explain what is tested
✅ **Keep tests independent** - No shared state between tests
✅ **Use fixtures** for common setup
✅ **Mock external dependencies** in unit tests
✅ **Test edge cases** and error conditions
✅ **Use parametrized tests** for multiple similar scenarios
✅ **Add docstrings** to complex tests
✅ **Clean up resources** (use fixtures with yield)
✅ **Test async code** with pytest-asyncio

### Don'ts

❌ **Don't test framework code** (FastAPI, Neo4j internals)
❌ **Don't write flaky tests** (random failures)
❌ **Don't use time.sleep()** in tests (use proper async)
❌ **Don't leave debug code** (print statements, breakpoints)
❌ **Don't skip tests** without good reason and documentation
❌ **Don't test implementation details** - Test behavior
❌ **Don't share state** between tests
❌ **Don't commit commented-out tests**

### Test Naming Conventions

Good test names:
```python
def test_add_memory_with_valid_data_returns_success()
def test_search_memories_with_no_results_returns_empty_list()
def test_invalid_memory_type_raises_value_error()
async def test_concurrent_memory_additions_are_thread_safe()
```

Poor test names:
```python
def test_memory()  # Too vague
def test_1()  # No description
def test_it_works()  # What works?
def test_memory_store_add_memory_function_test()  # Redundant
```

### Example Test File

```python
"""
Tests for memory store service.

This module tests memory CRUD operations, search functionality,
and memory relationships.
"""
import pytest
from typing import Dict, Any

from services.memory_store import MemoryStore


class TestMemoryStore:
    """Test suite for MemoryStore service."""

    @pytest.fixture
    async def memory_store(self):
        """Provide initialized memory store."""
        store = MemoryStore()
        await store.initialize()
        yield store
        await store.cleanup()

    @pytest.fixture
    def sample_memory(self) -> Dict[str, Any]:
        """Provide sample memory data."""
        return {
            "project_id": "test-project",
            "memory_type": "decision",
            "title": "Use PostgreSQL",
            "content": "Selected PostgreSQL for main database",
            "reason": "Need advanced JSON support",
            "importance": 0.8,
            "tags": ["database", "architecture"]
        }

    @pytest.mark.unit
    async def test_add_memory_success(self, memory_store, sample_memory):
        """Test adding a memory successfully."""
        result = await memory_store.add_memory(**sample_memory)

        assert result["success"] is True
        assert "memory_id" in result
        assert result["memory"]["title"] == sample_memory["title"]

    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_type", ["invalid", "", None])
    async def test_add_memory_invalid_type_fails(
        self, memory_store, sample_memory, invalid_type
    ):
        """Test adding memory with invalid type fails."""
        sample_memory["memory_type"] = invalid_type

        with pytest.raises(ValueError):
            await memory_store.add_memory(**sample_memory)

    @pytest.mark.integration
    async def test_search_memories_with_neo4j(self, memory_store, sample_memory):
        """Test searching memories with real Neo4j."""
        # Add memory
        await memory_store.add_memory(**sample_memory)

        # Search
        results = await memory_store.search_memories(
            project_id=sample_memory["project_id"],
            query="PostgreSQL"
        )

        assert len(results) > 0
        assert results[0]["title"] == sample_memory["title"]
```

## Troubleshooting Tests

### Common Issues

**Tests fail with "fixture not found":**
```bash
# Check fixture is defined in conftest.py or test file
# Check fixture name spelling
# Check fixture scope
```

**Async tests fail:**
```bash
# Ensure @pytest.mark.asyncio is present
# Check pytest-asyncio is installed
pip install pytest-asyncio
```

**Neo4j connection failures:**
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Check connection details in .env
NEO4J_URI=bolt://localhost:7687
```

**Import errors in tests:**
```bash
# Ensure package is installed in editable mode
pip install -e .

# Check PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

### Getting Help

- Check test logs: `pytest tests/ -vv`
- Review CI test results on GitHub
- Search issues: [GitHub Issues](https://github.com/royisme/codebase-rag/issues)
- Ask in discussions

## Next Steps

- Read [Contributing Guide](./contributing.md) for overall workflow
- Review [Development Setup](./setup.md) for environment configuration
- Explore existing tests in `tests/` directory
- Write tests for your features!

Happy testing!
