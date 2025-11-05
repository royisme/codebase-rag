# Contributing to Codebase RAG

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11, 3.12, or 3.13
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/codebase-rag.git
cd codebase-rag

# Install dependencies
uv pip install -e .

# Or using pip
pip install -e .
```

## Testing

### Running Tests

We have comprehensive unit tests for all MCP handlers. Tests are required for all new features and bug fixes.

```bash
# Run all unit tests
pytest tests/test_mcp_*.py -v

# Run specific test file
pytest tests/test_mcp_handlers.py -v

# Run with coverage report
pytest tests/test_mcp_*.py --cov=mcp_tools --cov-report=html

# Run only unit tests (no external dependencies)
pytest tests/ -v -m "unit"

# Run integration tests (requires Neo4j)
pytest tests/ -v -m "integration"
```

### Writing Tests

When adding new features, please include tests:

1. **Unit Tests**: Test individual functions in isolation
   - Mock all external dependencies
   - Test success and failure cases
   - Test edge cases and validation

2. **Integration Tests**: Test with real services (optional)
   - Mark with `@pytest.mark.integration`
   - Require Neo4j or other external services

Example test:

```python
import pytest
from unittest.mock import AsyncMock
from mcp_tools.knowledge_handlers import handle_query_knowledge

@pytest.mark.asyncio
async def test_handle_query_knowledge_success(mock_knowledge_service):
    """Test successful knowledge query"""
    # Arrange
    mock_knowledge_service.query.return_value = {
        "success": True,
        "answer": "Test response"
    }

    # Act
    result = await handle_query_knowledge(
        args={"question": "test question"},
        knowledge_service=mock_knowledge_service
    )

    # Assert
    assert result["success"] is True
    assert result["answer"] == "Test response"
    mock_knowledge_service.query.assert_called_once()
```

## Code Quality

### Formatting and Linting

We use `black`, `isort`, and `ruff` for code quality:

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Lint with ruff
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Pre-commit Checks

Before committing:

1. Run tests: `pytest tests/test_mcp_*.py -v`
2. Format code: `black . && isort .`
3. Check linting: `ruff check .`

## Pull Request Process

### Creating a Pull Request

1. **Fork the repository** and create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, descriptive commits:
   ```bash
   git commit -m "feat: add new feature X"
   git commit -m "fix: resolve issue with Y"
   ```

3. **Write tests** for your changes

4. **Run tests locally**:
   ```bash
   pytest tests/test_mcp_*.py -v
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

### PR Requirements

For your PR to be merged:

- ✅ All tests must pass
- ✅ Code coverage should not decrease
- ✅ Code must be formatted (black, isort)
- ✅ Linting should pass (ruff)
- ✅ Clear description of changes
- ✅ Tests for new features

### GitHub Actions

When you create a PR, GitHub Actions will automatically:

1. **Run unit tests** on Python 3.11, 3.12, and 3.13
2. **Check code quality** (black, isort, ruff)
3. **Generate coverage report**
4. **Report results** in the PR

**PR cannot be merged until all checks pass.**

### Commit Message Format

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

Examples:
```
feat: add streaming support for MCP tools
fix: resolve memory leak in task queue
docs: update MCP server architecture guide
test: add tests for memory handlers
refactor: extract handlers to modules
```

## Code Organization

### Project Structure

```
codebase-rag/
├── api/                    # FastAPI routes
├── core/                   # Core application logic
├── services/              # Business logic services
├── mcp_tools/             # MCP handler modules
│   ├── knowledge_handlers.py
│   ├── code_handlers.py
│   ├── memory_handlers.py
│   ├── task_handlers.py
│   └── system_handlers.py
├── tests/                 # Test suite
│   ├── test_mcp_handlers.py
│   ├── test_mcp_utils.py
│   └── test_mcp_integration.py
└── docs/                  # Documentation
```

### Adding New MCP Tools

1. Add handler function to appropriate `mcp_tools/*.py` file
2. Add tool definition to `mcp_tools/tool_definitions.py`
3. Update routing in `mcp_server.py`
4. Write tests in `tests/test_mcp_handlers.py`
5. Update documentation

## Getting Help

- 📖 Read the documentation in `docs/`
- 🐛 Report bugs via GitHub Issues
- 💬 Ask questions in Discussions
- 📧 Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing! 🎉
