# Contributing to Code Graph Knowledge System

Thank you for your interest in contributing to the Code Graph Knowledge System! This guide will help you understand our development process and how to submit quality contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [Community and Support](#community-and-support)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please:

- Be respectful and considerate in all interactions
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Python 3.13+** installed
2. **uv** package manager ([installation guide](https://github.com/astral-sh/uv))
3. **Neo4j 5.0+** running locally or via Docker
4. **Git** for version control
5. A **GitHub account**

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/codebase-rag.git
cd codebase-rag
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/royisme/codebase-rag.git
```

4. Create a feature branch:

```bash
git checkout -b feature/your-feature-name
```

### Development Environment Setup

See the [Development Setup Guide](./setup.md) for detailed instructions on setting up your local development environment.

## Development Workflow

### 1. Sync with Upstream

Before starting work, sync your fork with the upstream repository:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### 2. Create a Feature Branch

Create a descriptive branch name:

```bash
git checkout -b feature/add-sql-parser-support
git checkout -b fix/neo4j-connection-timeout
git checkout -b docs/update-api-documentation
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications
- `chore/` - Maintenance tasks

### 3. Make Your Changes

- Write clean, readable code
- Follow the code style guidelines (see below)
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 4. Test Your Changes

Run the test suite to ensure everything works:

```bash
# Run all tests
pytest tests/

# Run specific test types
pytest tests/ -m unit
pytest tests/ -m integration

# Run with coverage
pytest tests/ --cov=services --cov=api --cov=mcp_tools --cov-report=term
```

### 5. Commit Your Changes

Follow our commit conventions (see below) and commit your changes:

```bash
git add .
git commit -m "feat: add PostgreSQL schema parser support"
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub following our PR template.

## Code Style Guidelines

We use automated tools to maintain consistent code style across the project.

### Python Code Style

#### Formatting Tools

1. **Black** - Code formatter
   - Line length: 100 characters
   - Target Python versions: 3.11, 3.12, 3.13

2. **isort** - Import sorter
   - Profile: black (compatible with Black)
   - Line length: 100 characters

3. **Ruff** - Fast Python linter
   - Line length: 100 characters
   - Enabled rule sets: pycodestyle (E/W), pyflakes (F), isort (I), comprehensions (C), bugbear (B)

#### Running Code Quality Tools

Format your code before committing:

```bash
# Format with Black
black .

# Sort imports
isort .

# Lint with Ruff
ruff check .

# Fix auto-fixable Ruff issues
ruff check . --fix

# Run all together
black . && isort . && ruff check .
```

#### Code Style Best Practices

**Import Organization:**
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase

# Local imports
from services.neo4j_knowledge_service import Neo4jKnowledgeService
from core.config import settings
```

**Type Hints:**
Always use type hints for function parameters and return values:

```python
from typing import Optional, List, Dict, Any

async def process_document(
    document_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process a document and return results."""
    pass
```

**Docstrings:**
Use clear docstrings for all public functions and classes:

```python
def parse_sql_schema(sql_file: str, dialect: str = "oracle") -> Dict[str, Any]:
    """
    Parse SQL schema file and extract table definitions.

    Args:
        sql_file: Path to SQL file to parse
        dialect: SQL dialect (oracle, mysql, postgresql, sqlserver)

    Returns:
        Dictionary containing parsed schema information including:
        - tables: List of table definitions
        - relationships: Foreign key relationships
        - indexes: Index definitions

    Raises:
        FileNotFoundError: If SQL file doesn't exist
        ValueError: If dialect is not supported
    """
    pass
```

**Async/Await Patterns:**
Use async/await consistently for asynchronous operations:

```python
async def initialize_service(self) -> None:
    """Initialize the service asynchronously."""
    await self._connect_database()
    await self._load_configuration()
    self.initialized = True
```

**Error Handling:**
Use structured error responses:

```python
try:
    result = await process_data(data)
    return {"success": True, "data": result}
except ValueError as e:
    return {"success": False, "error": str(e), "error_type": "validation"}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"success": False, "error": "Internal server error"}
```

### Configuration

Our code style configuration is defined in `pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ['py311', 'py312', 'py313']

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py311"
```

## Commit Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change or bug fix)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `ci`: CI/CD configuration changes
- `revert`: Reverting previous commits

### Commit Message Examples

**Feature Addition:**
```
feat(memory): add automatic memory extraction from conversations

Implement LLM-powered analysis to extract decisions, preferences, and
experiences from AI conversation history. Includes confidence scoring
and auto-save capability for high-confidence memories.

Closes #42
```

**Bug Fix:**
```
fix(neo4j): resolve connection timeout in Docker environment

Fix Redis connection failures when running in Docker by using service
name instead of localhost in connection string.

Fixes #123
```

**Documentation:**
```
docs(api): update memory API endpoint documentation

Add examples for all memory types and update request/response schemas.
```

**Refactoring:**
```
refactor(mcp): extract handlers into modular architecture

Break down monolithic MCP server into smaller, focused handler modules.
Reduces main server file from 1400 lines to 310 lines (78% reduction).

Related to #56
```

### Commit Best Practices

1. **Keep commits atomic** - One logical change per commit
2. **Write clear subjects** - Imperative mood, max 50 characters
3. **Add detailed body when needed** - Explain what and why, not how
4. **Reference issues** - Use `Fixes #123`, `Closes #456`, `Related to #789`
5. **Don't commit generated files** - Keep commits clean and focused

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes
2. **Run all tests** and ensure they pass
3. **Run code quality tools** (black, isort, ruff)
4. **Update documentation** if you've changed functionality
5. **Add tests** for new features or bug fixes
6. **Review your own changes** - catch obvious issues before submission

### PR Title

Follow the same format as commit messages:

```
feat(memory): add batch repository memory extraction
fix(api): handle large file uploads correctly
docs(deployment): add troubleshooting guide
```

### PR Description Template

```markdown
## Description
Brief description of what this PR does and why.

## Changes
- List of specific changes made
- Another change
- And another

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Documentation
- [ ] Code comments added/updated
- [ ] API documentation updated
- [ ] User guide updated (if needed)

## Related Issues
Fixes #123
Related to #456

## Screenshots (if applicable)
Include screenshots for UI changes.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### PR Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
   - Unit tests
   - Integration tests (if applicable)
   - Code quality checks
   - Security scans

2. **Code Review**: At least one maintainer will review
   - Code quality and style
   - Test coverage
   - Documentation completeness
   - Design and architecture

3. **Feedback**: Address review comments
   - Make requested changes
   - Push additional commits
   - Respond to questions

4. **Merge**: Once approved and all checks pass
   - Squash and merge (default)
   - Merge commit (for large features)
   - Rebase and merge (for small fixes)

### PR Best Practices

- Keep PRs focused and reasonably sized (< 500 lines preferred)
- Link to related issues
- Add screenshots for UI changes
- Update tests and documentation
- Respond to feedback promptly
- Don't force-push after review starts (unless requested)

## Testing Requirements

All contributions must include appropriate tests. See the [Testing Guide](./testing.md) for detailed information.

### Test Coverage Expectations

- **New Features**: 80%+ coverage required
- **Bug Fixes**: Add test that reproduces the bug
- **Refactoring**: Maintain or improve existing coverage

### Test Types

1. **Unit Tests** - Fast, isolated tests (no external dependencies)
2. **Integration Tests** - Test with Neo4j and external services
3. **End-to-End Tests** - Full workflow testing (where applicable)

### Running Tests Locally

```bash
# Run all tests
pytest tests/

# Run only unit tests
pytest tests/ -m unit

# Run with coverage
pytest tests/ --cov=services --cov=api --cov=mcp_tools --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Documentation Requirements

Good documentation is as important as good code.

### What to Document

1. **Code Comments**
   - Complex algorithms or business logic
   - Non-obvious design decisions
   - Workarounds and known limitations

2. **Docstrings**
   - All public functions and classes
   - Include parameters, return values, and exceptions

3. **API Documentation**
   - New endpoints or changes to existing ones
   - Request/response examples
   - Error codes and messages

4. **User Documentation**
   - New features visible to end users
   - Configuration changes
   - Migration guides for breaking changes

5. **Architecture Documentation**
   - Significant architectural changes
   - New design patterns introduced
   - System integration points

### Documentation Format

- Use **Markdown** for all documentation
- Follow the existing structure in `docs/`
- Include code examples where helpful
- Add diagrams for complex concepts (use Mermaid)

### Example Documentation Update

If you add a new API endpoint:

1. Update `docs/api/endpoints.md`
2. Add code examples in `examples/`
3. Update the relevant user guide
4. Add entry to changelog (if user-facing)

## Community and Support

### Getting Help

- **Documentation**: Check [docs](https://code-graph.vantagecraft.dev)
- **GitHub Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers for security issues

### Reporting Bugs

When reporting bugs, include:

1. **Environment Information**
   - Python version
   - Operating system
   - Neo4j version
   - Deployment mode (local/Docker)

2. **Steps to Reproduce**
   - Minimal reproducible example
   - Expected vs actual behavior
   - Error messages or logs

3. **Additional Context**
   - Configuration files (redact sensitive data)
   - Screenshots or recordings
   - Related issues or PRs

### Suggesting Features

Before suggesting a feature:

1. **Search existing issues** - Avoid duplicates
2. **Discuss in GitHub Discussions** - Get feedback first
3. **Create a detailed proposal** - Use the feature request template

### Security Issues

**Do NOT** create public issues for security vulnerabilities.

Instead:
- Email maintainers directly
- Provide detailed information privately
- Allow time for patching before disclosure

## Recognition

Contributors are recognized in several ways:

- **Contributors list** in README.md
- **Changelog entries** for significant contributions
- **Social media mentions** for major features
- **Maintainer status** for consistent, quality contributions

## Questions?

If you have questions about contributing:

1. Check the [FAQ](../faq.md)
2. Read the [Development Setup Guide](./setup.md)
3. Search GitHub Issues and Discussions
4. Create a new discussion topic

Thank you for contributing to Code Graph Knowledge System!
