# Tests Directory

This directory contains the test suite for the Codebase RAG project.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_mcp_handlers.py           # Unit tests for MCP handler functions (46 tests)
├── test_mcp_utils.py              # Unit tests for MCP utilities (24 tests)
├── test_mcp_integration.py        # Integration tests for MCP server (35 tests)
├── test_memory_store.py           # Memory store service tests
├── test_ingest.py                 # Code ingestion tests
├── test_context_pack.py           # Context pack builder tests
├── test_related.py                # Related files finder tests
├── MCP_TEST_SUMMARY.md            # Detailed MCP test suite documentation
└── README.md                      # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_mcp_handlers.py -v

# Run specific test class
pytest tests/test_mcp_handlers.py::TestKnowledgeHandlers -v

# Run specific test function
pytest tests/test_mcp_handlers.py::TestKnowledgeHandlers::test_handle_query_knowledge_success -v
```

### Using uv (Recommended)

```bash
# Run tests with uv
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=mcp_tools --cov-report=html

# Run only MCP tests
uv run pytest tests/test_mcp_*.py -v
```

### Test Markers

Tests can be marked with custom markers:

```bash
# Run only unit tests (no external dependencies)
pytest tests/ -v -m unit

# Run only integration tests (requires Neo4j)
pytest tests/ -v -m integration

# Skip integration tests
pytest tests/ -v -m "not integration"
```

## Test Categories

### 1. MCP Server Tests (NEW)
- **test_mcp_handlers.py**: Tests all 25 MCP handler functions
- **test_mcp_utils.py**: Tests MCP utility functions (format_result)
- **test_mcp_integration.py**: Tests complete MCP server integration

These tests are fully mocked and don't require external services.

### 2. Service Tests
- **test_memory_store.py**: Memory store CRUD operations
- **test_ingest.py**: Code repository ingestion
- **test_context_pack.py**: Context pack building
- **test_related.py**: Related files finder

These tests may require Neo4j connection (marked with `@pytest.mark.integration`).

## Fixtures

Shared test fixtures are defined in `conftest.py`:

### Mock Service Fixtures
- `mock_knowledge_service` - Mock Neo4jKnowledgeService
- `mock_memory_store` - Mock MemoryStore
- `mock_task_queue` - Mock TaskQueue
- `mock_graph_service` - Mock graph service
- `mock_code_ingestor` - Mock code ingestor
- And 17 more...

### Sample Data Fixtures
- `sample_memory_data` - Sample memory for testing
- `sample_task_data` - Sample task data
- `sample_query_result` - Sample query result
- `sample_memory_list` - Sample memory list
- `sample_code_nodes` - Sample code nodes

### Existing Fixtures
- `test_repo_path` - Temporary test repository
- `test_repo_id` - Test repository ID
- `graph_service` - Neo4j graph service (requires Neo4j)
- `test_client` - FastAPI test client

## Writing New Tests

### Test Naming Convention

Follow the pattern: `test_<function>_<scenario>_<expected>`

```python
def test_handle_query_knowledge_success()  # Good
def test_query()                           # Bad - not descriptive
```

### Test Structure (AAA Pattern)

```python
@pytest.mark.asyncio
async def test_my_handler_success(mock_service):
    """Test description"""
    # Arrange - Set up test data and mocks
    mock_service.method.return_value = {"success": True}

    # Act - Execute the function under test
    result = await my_handler(args={...}, service=mock_service)

    # Assert - Verify the results
    assert result["success"] is True
    mock_service.method.assert_called_once()
```

### Using Fixtures

```python
@pytest.mark.asyncio
async def test_with_fixture(mock_knowledge_service, sample_memory_data):
    """Fixtures are automatically injected"""
    result = await handle_something(
        args=sample_memory_data,
        service=mock_knowledge_service
    )
    assert result["success"] is True
```

### Testing Async Functions

Always use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_handler():
    result = await async_function()
    assert result is not None
```

### Mocking Best Practices

```python
# Use AsyncMock for async functions
mock_service = AsyncMock()
mock_service.async_method.return_value = {...}

# Use Mock for sync functions
mock_util = Mock()
mock_util.sync_method.return_value = "value"

# Simulate exceptions
mock_service.method.side_effect = Exception("Error message")
```

## Test Coverage

View test coverage:

```bash
# Generate HTML coverage report
pytest tests/ --cov=mcp_tools --cov=services --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Current coverage targets:
- **MCP handlers**: ~80% (105 tests covering 25 handlers)
- **Overall**: Target >80%

## Continuous Integration

Tests should be run in CI pipeline before merging:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest tests/ -v --cov=mcp_tools --cov=services
```

## Common Issues

### Import Errors

If you get import errors, ensure the project root is in PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

Or use `sys.path` in conftest.py (already configured).

### Missing Dependencies

Install test dependencies:

```bash
pip install -e .
# or
uv pip install -e .
```

### Neo4j Connection Required

Some tests require Neo4j. Skip them if not available:

```bash
pytest tests/ -v -m "not integration"
```

Or mark your test to skip if Neo4j unavailable:

```python
@pytest.mark.integration
async def test_requires_neo4j(graph_service):
    # Will skip if Neo4j not available
    pass
```

## Test Performance

Expected test execution times:
- **MCP unit tests**: <5 seconds (fully mocked)
- **Integration tests**: 10-30 seconds (requires services)
- **Full suite**: <60 seconds

Slow tests should be marked and can be skipped:

```python
@pytest.mark.slow
def test_heavy_operation():
    pass

# Skip slow tests
pytest tests/ -v -m "not slow"
```

## Best Practices

1. **Keep tests independent**: No shared state between tests
2. **Use descriptive names**: Test name should describe what it tests
3. **One assertion per test**: Focus tests on single behavior
4. **Mock external dependencies**: Tests should be fast and reliable
5. **Document edge cases**: Use docstrings to explain tricky scenarios
6. **Clean up resources**: Use fixtures for setup/teardown
7. **Test both success and failure**: Cover error handling
8. **Keep tests simple**: If test is complex, refactor code being tested

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [MCP Test Summary](./MCP_TEST_SUMMARY.md) - Detailed MCP test documentation

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass: `pytest tests/ -v`
3. Add test fixtures to conftest.py if needed
4. Update this README if adding new test categories
5. Aim for >80% code coverage

## Questions?

For questions about tests, see:
- [MCP_TEST_SUMMARY.md](./MCP_TEST_SUMMARY.md) - MCP test details
- [conftest.py](./conftest.py) - Available fixtures
- Existing test files for examples
