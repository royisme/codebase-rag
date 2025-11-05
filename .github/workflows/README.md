# GitHub Actions Workflows

This directory contains CI/CD workflows for the Codebase RAG project.

## Workflows

### 1. PR Tests (`pr-tests.yml`)

**Triggers**: When a Pull Request is opened, synchronized, or reopened

**Purpose**: Ensure code quality and test coverage before merging PRs

**Jobs**:

- **Test** (Python 3.11, 3.12, 3.13)
  - Runs unit tests (no external dependencies required)
  - Generates coverage report
  - Uploads to Codecov

- **Lint**
  - Checks code formatting with `black`
  - Checks import sorting with `isort`
  - Runs linting with `ruff`

- **Test Summary**
  - Aggregates results
  - Blocks PR merge if tests fail

**Requirements for PR Merge**:
- ✅ All unit tests must pass
- ⚠️ Linting warnings don't block (but should be fixed)

```yaml
# Example PR check status:
✅ Test (Python 3.11) - passed
✅ Test (Python 3.12) - passed
✅ Test (Python 3.13) - passed
⚠️  Lint - warnings (not blocking)
✅ Test Summary - passed
```

### 2. CI - Continuous Integration (`ci.yml`)

**Triggers**: Push to main/master/develop branches, or manual dispatch

**Purpose**: Full integration testing with external services

**Jobs**:

- **Test** (with Neo4j service)
  - Spins up Neo4j container
  - Runs all unit tests
  - Runs integration tests (marked with `@pytest.mark.integration`)
  - Generates coverage report

- **Security**
  - Runs Trivy vulnerability scanner
  - Uploads results to GitHub Security

**Services**:
- Neo4j 5.14 with APOC plugin
- Configured with test credentials

```yaml
# Neo4j service configuration:
- Image: neo4j:5.14
- Auth: neo4j/testpassword
- Ports: 7687 (bolt), 7474 (http)
- Plugins: APOC
```

## Configuration

### Environment Variables

Tests use these environment variables (configured in workflows):

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
NEO4J_DATABASE=neo4j
```

### Test Markers

Tests can be marked for selective execution:

- `@pytest.mark.unit` - Unit tests (no external deps)
- `@pytest.mark.integration` - Integration tests (require Neo4j)
- `@pytest.mark.slow` - Slow-running tests

```python
# Example usage:
@pytest.mark.unit
def test_format_result():
    """Unit test - runs in PR workflow"""
    pass

@pytest.mark.integration
def test_neo4j_connection():
    """Integration test - runs only in CI workflow"""
    pass
```

### Coverage Requirements

- Minimum coverage: Not enforced (yet)
- Coverage reports uploaded to Codecov
- Coverage trends tracked per PR

## Local Testing

Before pushing, run tests locally:

```bash
# Unit tests only (fast, no dependencies)
pytest tests/test_mcp_*.py -v -m "not integration"

# With coverage
pytest tests/test_mcp_*.py --cov=mcp_tools --cov-report=html

# Integration tests (requires Neo4j)
pytest tests/ -v -m integration
```

## Workflow Status Badges

Add to README.md:

```markdown
![PR Tests](https://github.com/yourusername/codebase-rag/workflows/PR%20Tests/badge.svg)
![CI](https://github.com/yourusername/codebase-rag/workflows/CI/badge.svg)
[![codecov](https://codecov.io/gh/yourusername/codebase-rag/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/codebase-rag)
```

## Troubleshooting

### Tests Fail in CI but Pass Locally

1. Check Python version compatibility (workflow tests 3.11, 3.12, 3.13)
2. Ensure no hardcoded paths or local dependencies
3. Check environment variables
4. Review workflow logs on GitHub Actions tab

### Linting Failures

```bash
# Auto-fix formatting
black .
isort .

# Auto-fix linting issues
ruff check --fix .
```

### Coverage Decrease

If coverage decreases:
1. Add tests for new code
2. Check if tests are being skipped
3. Review coverage report: `coverage html && open htmlcov/index.html`

### Neo4j Service Issues

If integration tests fail:
1. Check Neo4j health in workflow logs
2. Verify wait time is sufficient (currently 60s)
3. Check Neo4j credentials match

## Updating Workflows

When modifying workflows:

1. **Test locally** using [act](https://github.com/nektos/act):
   ```bash
   act pull_request -W .github/workflows/pr-tests.yml
   ```

2. **Create PR** with workflow changes

3. **Monitor** the workflow run in PR checks

4. **Iterate** based on results

## Best Practices

✅ **DO**:
- Write tests for all new features
- Keep tests fast and isolated
- Use mocks for external dependencies
- Mark integration tests appropriately
- Run tests before pushing

❌ **DON'T**:
- Skip failing tests
- Disable test requirements without discussion
- Commit commented-out tests
- Push without running tests locally

---

For more information, see:
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [tests/README.md](../../tests/README.md) - Test documentation
- [tests/MCP_TEST_SUMMARY.md](../../tests/MCP_TEST_SUMMARY.md) - Test coverage details
