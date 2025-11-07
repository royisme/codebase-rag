# Migration Guide: v0.7.x to v0.8.0

Complete guide for migrating from the old directory structure to the new src-layout.

**Release Date**: 2025-11-06
**Breaking Changes**: Yes
**Migration Effort**: Low (15-30 minutes)

---

## 📋 Summary of Changes

Version 0.8.0 introduces a complete restructuring to adopt Python's standard src-layout. This brings better organization, clearer package boundaries, and follows Python best practices.

### Major Changes

1. **All code moved to `src/codebase_rag/`**
2. **All old entry scripts removed**
3. **Import paths updated**
4. **New standardized entry points**
5. **Backward compatibility removed**

---

## 🚨 Breaking Changes

### 1. Entry Scripts Removed

**Old** (❌ No longer works):
```bash
python start.py
python start_mcp.py
python main.py
```

**New** (✅ Use these instead):
```bash
# Direct module invocation
python -m codebase_rag          # Start both services
python -m codebase_rag --web    # Web only
python -m codebase_rag --mcp    # MCP only
python -m codebase_rag --version

# After installation (pip install -e .)
codebase-rag          # Main CLI
codebase-rag-web      # Web server
codebase-rag-mcp      # MCP server
```

### 2. Import Paths Changed

**Old** (❌ No longer works):
```python
from config import settings
from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.memory_store import MemoryStore
from core.app import create_app
from api.routes import router
from mcp_tools.utils import some_function
```

**New** (✅ Use these instead):
```python
from src.codebase_rag.config import settings
from src.codebase_rag.services.knowledge import Neo4jKnowledgeService
from src.codebase_rag.services.memory import MemoryStore
from src.codebase_rag.core.app import create_app
from src.codebase_rag.api.routes import router
from src.codebase_rag.mcp.utils import some_function
```

### 3. Directory Structure Changed

**Old Structure** (❌ Removed):
```
codebase-rag/
├── api/              # ❌ Deleted
├── core/             # ❌ Deleted
├── services/         # ❌ Deleted
├── mcp_tools/        # ❌ Deleted
├── config.py         # ❌ Deleted
├── main.py           # ❌ Deleted
├── start.py          # ❌ Deleted
└── start_mcp.py      # ❌ Deleted
```

**New Structure** (✅ Current):
```
codebase-rag/
├── src/
│   └── codebase_rag/  # ✅ All code here
│       ├── __init__.py
│       ├── __main__.py
│       ├── config/
│       ├── server/
│       ├── core/
│       ├── api/
│       ├── services/
│       └── mcp/       # Renamed from mcp_tools
├── pyproject.toml     # ✅ Updated
├── docs/
├── tests/
└── ...
```

### 4. Docker Changes

**Dockerfile CMD** changed:

```dockerfile
# Old
CMD ["python", "start.py"]

# New
CMD ["python", "-m", "codebase_rag"]
```

---

## 🔄 Migration Steps

### For End Users (Docker Deployment)

If you're using Docker, **no changes needed**! Just pull the new image:

```bash
# Pull latest
docker pull royisme/codebase-rag:latest

# Or rebuild
docker-compose down
docker-compose pull
docker-compose up -d
```

### For Developers (Local Development)

#### Step 1: Update Repository

```bash
# Pull latest changes
git pull origin main

# Or if on a branch
git fetch origin
git rebase origin/main
```

#### Step 2: Reinstall Package

```bash
# Remove old installation
pip uninstall code-graph -y

# Reinstall with new structure
pip install -e .

# Or with uv
uv pip install -e .
```

#### Step 3: Update Your Code

**Update all import statements** in your custom scripts/tools:

```python
# Old imports (need to update)
from config import settings
from services.xxx import Yyy

# New imports
from src.codebase_rag.config import settings
from src.codebase_rag.services.xxx import Yyy
```

**Find all files to update:**
```bash
# Search for old imports in your codebase
grep -r "from config import" .
grep -r "from services\." .
grep -r "from core\." .
grep -r "from api\." .
grep -r "from mcp_tools\." .
```

#### Step 4: Update Entry Scripts

If you have custom scripts that call the server:

```python
# Old
if __name__ == "__main__":
    from start import main
    main()

# New
if __name__ == "__main__":
    from src.codebase_rag.server.web import main
    main()
```

Or better, use the standard module invocation:

```python
import subprocess
subprocess.run(["python", "-m", "codebase_rag"])
```

#### Step 5: Update MCP Configurations

If using MCP (Claude Desktop, Cursor, etc.):

**Old** `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "codebase-rag": {
      "command": "python",
      "args": ["/path/to/codebase-rag/start_mcp.py"]
    }
  }
}
```

**New**:
```json
{
  "mcpServers": {
    "codebase-rag": {
      "command": "python",
      "args": ["-m", "codebase_rag", "--mcp"],
      "cwd": "/path/to/codebase-rag"
    }
  }
}
```

Or after installation:
```json
{
  "mcpServers": {
    "codebase-rag": {
      "command": "codebase-rag-mcp"
    }
  }
}
```

---

## 🧪 Testing Your Migration

After migration, test all functionality:

### 1. Test Import Paths

```python
# Test configuration import
from src.codebase_rag.config import settings
print(f"✅ Config: {settings.app_name}")

# Test service imports
from src.codebase_rag.services.knowledge import Neo4jKnowledgeService
print("✅ Services import successful")
```

### 2. Test Entry Points

```bash
# Test version
python -m codebase_rag --version
# Should output: codebase-rag version 0.8.0

# Test help
python -m codebase_rag --help

# Test web server (Ctrl+C to stop)
python -m codebase_rag --web
```

### 3. Test Docker

```bash
# Build test image
docker build -t codebase-rag:test .

# Run test container
docker run -p 8000:8000 -p 8080:8080 codebase-rag:test

# Check health
curl http://localhost:8080/api/v1/health
```

### 4. Run Tests

```bash
# Run test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/codebase_rag --cov-report=html
```

---

## 📝 Common Issues

### Issue 1: ModuleNotFoundError

**Error:**
```
ModuleNotFoundError: No module named 'config'
```

**Solution:**
Update import to new path:
```python
from src.codebase_rag.config import settings
```

### Issue 2: start.py not found

**Error:**
```
python: can't open file 'start.py': [Errno 2] No such file or directory
```

**Solution:**
Use new entry point:
```bash
python -m codebase_rag
```

### Issue 3: Old imports in tests

**Error:**
```
ImportError: cannot import name 'Neo4jKnowledgeService' from 'services.neo4j_knowledge_service'
```

**Solution:**
Update test imports:
```python
from src.codebase_rag.services.knowledge import Neo4jKnowledgeService
```

### Issue 4: Docker container fails to start

**Error:**
```
python: can't open file 'start.py'
```

**Solution:**
Rebuild Docker image:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🎯 Benefits of New Structure

### 1. Standard Python Package

- ✅ Follows PyPA src-layout recommendations
- ✅ Proper package namespace (`codebase_rag`)
- ✅ Cleaner imports

### 2. Better Organization

- ✅ All source code in `src/`
- ✅ Clear separation of concerns
- ✅ Logical service grouping

### 3. Easier Development

- ✅ Standard entry points (`python -m codebase_rag`)
- ✅ Proper console scripts after installation
- ✅ No confusion about root vs package code

### 4. Improved Maintainability

- ✅ No duplicate code
- ✅ Clear module boundaries
- ✅ Easier to navigate for new contributors

---

## 📚 Additional Resources

- [Python Packaging Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [src-layout vs flat-layout](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#src-layout)
- [Development Setup](./setup.md)
- [Python SDK Guide](../api/python-sdk.md)

---

## 🆘 Need Help?

If you encounter issues not covered in this guide:

1. Check [Troubleshooting](../troubleshooting.md)
2. Check [FAQ](../faq.md)
3. Open an issue on GitHub
4. Ask in Discussions

---

**Last Updated**: 2025-11-06
**Next Version**: 0.9.0 (planned)
