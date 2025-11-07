# Development Environment Setup

This guide will help you set up a complete development environment for the Code Graph Knowledge System.

## Table of Contents

- [Prerequisites](#prerequisites)
- [System Requirements](#system-requirements)
- [Python Environment Setup](#python-environment-setup)
- [Neo4j Database Setup](#neo4j-database-setup)
- [LLM Provider Setup](#llm-provider-setup)
- [Project Installation](#project-installation)
- [Environment Configuration](#environment-configuration)
- [IDE Setup](#ide-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have the following installed on your system:

### Required

- **Python 3.13 or higher**
- **Git** (for version control)
- **Docker and Docker Compose** (for Neo4j and optional services)

### Recommended

- **uv** (fast Python package manager)
- **Visual Studio Code** or **PyCharm** (recommended IDEs)

## System Requirements

### Minimum Requirements

- **OS**: Linux, macOS, or Windows (with WSL2)
- **RAM**: 8GB (16GB recommended)
- **Disk Space**: 10GB free space
- **CPU**: 4 cores (8 cores recommended for Ollama)

### For Production Development

- **RAM**: 16GB minimum (32GB for Ollama with large models)
- **GPU**: NVIDIA GPU with CUDA support (optional, for faster Ollama inference)

## Python Environment Setup

### Install Python 3.13

#### Linux (Ubuntu/Debian)

```bash
# Add deadsnakes PPA for latest Python versions
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 python3.13-venv python3.13-dev
```

#### macOS

```bash
# Using Homebrew
brew install python@3.13
```

#### Windows (WSL2)

Follow the Linux instructions after installing WSL2.

### Install uv (Recommended)

uv is a fast Python package manager written in Rust. It's significantly faster than pip.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

**Alternative**: Use pip if you prefer traditional Python package management:

```bash
pip install --upgrade pip
```

## Neo4j Database Setup

Neo4j is required for the knowledge graph functionality. You can run it via Docker or install it natively.

### Option 1: Neo4j with Docker (Recommended for Development)

This is the easiest method for development:

```bash
# Create a docker-compose.yml for Neo4j
cat > docker-compose.dev.yml << 'EOF'
version: '3.8'

services:
  neo4j:
    image: neo4j:5.14
    container_name: code-graph-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/devpassword
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "devpassword", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  neo4j_data:
  neo4j_logs:
EOF

# Start Neo4j
docker-compose -f docker-compose.dev.yml up -d

# Check logs
docker logs -f code-graph-neo4j

# Wait for Neo4j to be ready (look for "Started.")
```

**Verify Neo4j is running:**

```bash
# Check container status
docker ps | grep neo4j

# Access Neo4j Browser
# Open http://localhost:7474 in your browser
# Login: neo4j / devpassword
```

### Option 2: Native Neo4j Installation

#### Linux

```bash
# Add Neo4j repository
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list

# Install Neo4j
sudo apt update
sudo apt install neo4j

# Install APOC plugin
wget https://github.com/neo4j/apoc/releases/download/5.14.0/apoc-5.14.0-core.jar -P /var/lib/neo4j/plugins/

# Configure Neo4j
sudo nano /etc/neo4j/neo4j.conf
# Add: dbms.security.procedures.unrestricted=apoc.*

# Start Neo4j
sudo systemctl start neo4j
sudo systemctl enable neo4j
```

#### macOS

```bash
# Using Homebrew
brew install neo4j

# Start Neo4j
neo4j start
```

### Neo4j Initial Configuration

1. **Access Neo4j Browser**: http://localhost:7474
2. **Initial Login**:
   - Username: `neo4j`
   - Password: `neo4j` (or `devpassword` if using Docker)
3. **Change Password**: Follow the prompt (or keep the Docker password)
4. **Verify APOC**: Run `RETURN apoc.version()` in the browser

## LLM Provider Setup

The system supports multiple LLM providers. Choose at least one:

### Option 1: Ollama (Recommended for Development)

Ollama provides local LLM hosting, which is free and doesn't require API keys.

#### Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows (WSL2)
curl -fsSL https://ollama.com/install.sh | sh
```

#### Start Ollama and Pull Models

```bash
# Start Ollama service
ollama serve  # Keep this running in a terminal

# In another terminal, pull models
ollama pull llama3.2:3b     # Small, fast model
ollama pull mistral:7b      # Good balance
ollama pull nomic-embed-text  # Embedding model

# Verify models are available
ollama list
```

**Note**: Larger models require more RAM:
- 3B parameters: ~4GB RAM
- 7B parameters: ~8GB RAM
- 13B parameters: ~16GB RAM
- 70B parameters: ~48GB RAM

### Option 2: OpenAI

```bash
# Get API key from https://platform.openai.com/api-keys
# No installation needed, just add to .env file
```

### Option 3: Google Gemini

```bash
# Get API key from https://ai.google.dev/
# No installation needed, just add to .env file
```

### Option 4: OpenRouter

```bash
# Get API key from https://openrouter.ai/
# Provides access to multiple LLM providers
# No installation needed, just add to .env file
```

## Project Installation

### Clone the Repository

```bash
# Clone your fork (replace YOUR_USERNAME with your GitHub username)
git clone https://github.com/YOUR_USERNAME/codebase-rag.git
cd codebase-rag

# Add upstream remote
git remote add upstream https://github.com/royisme/codebase-rag.git
```

### Install Dependencies

#### Using uv (Recommended)

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project in editable mode
uv pip install -e .

# Install development dependencies
uv pip install pytest pytest-asyncio pytest-cov pytest-mock black isort ruff
```

#### Using pip

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install project in editable mode
pip install -e .

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock black isort ruff
```

### Verify Installation

```bash
# Check installed packages
uv pip list  # or: pip list

# Verify key packages
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import neo4j; print(f'Neo4j: {neo4j.__version__}')"
python -c "import llama_index; print(f'LlamaIndex: {llama_index.__version__}')"
```

## Environment Configuration

### Create .env File

```bash
# Copy example environment file
cp env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

### Essential Environment Variables

#### Neo4j Configuration

```bash
# Neo4j connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpassword  # Change to your password
NEO4J_DATABASE=neo4j
```

#### LLM Provider Configuration

**For Ollama (Local):**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

**For OpenAI:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4

EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**For Google Gemini:**
```bash
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-1.5-flash

EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
```

#### Application Configuration

```bash
# Server settings
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=DEBUG  # Use DEBUG for development

# Features
ENABLE_MONITORING=true  # Enable NiceGUI monitoring UI
ENABLE_PROMETHEUS=true  # Enable Prometheus metrics

# Timeouts (in seconds)
CONNECTION_TIMEOUT=30
OPERATION_TIMEOUT=300
LARGE_DOCUMENT_TIMEOUT=600
```

### Example Complete .env File

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpassword
NEO4J_DATABASE=neo4j

# LLM Provider (Ollama for development)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Embedding Provider
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=DEBUG

# Features
ENABLE_MONITORING=true
ENABLE_PROMETHEUS=true

# Timeouts
CONNECTION_TIMEOUT=30
OPERATION_TIMEOUT=300
LARGE_DOCUMENT_TIMEOUT=600
```

## IDE Setup

### Visual Studio Code

#### Recommended Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-python.isort",
    "redhat.vscode-yaml",
    "neo4j.cypher",
    "tamasfe.even-better-toml"
  ]
}
```

Save this as `.vscode/extensions.json` in your project root.

#### VS Code Settings

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.rulers": [100]
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".ruff_cache": true
  }
}
```

Save this as `.vscode/settings.json`.

#### Launch Configuration

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: MCP Server",
      "type": "python",
      "request": "launch",
      "program": "start_mcp.py",
      "console": "integratedTerminal",
      "justMyCode": false
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Pytest Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v",
        "--tb=short"
      ],
      "console": "integratedTerminal"
    }
  ]
}
```

Save this as `.vscode/launch.json`.

### PyCharm

#### Setup Steps

1. **Open Project**: File > Open > Select `codebase-rag` directory
2. **Configure Interpreter**:
   - Settings > Project > Python Interpreter
   - Add Interpreter > Existing Environment
   - Select `.venv/bin/python`
3. **Configure Black**:
   - Settings > Tools > Black
   - Enable "On save"
   - Line length: 100
4. **Configure Ruff**:
   - Install Ruff plugin
   - Enable in Settings > Tools > Ruff
5. **Run Configurations**:
   - Create configurations for `start.py` and `start_mcp.py`

## Verification

### Test Development Environment

Run through this checklist to verify everything is set up correctly:

#### 1. Python Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Check Python version
python --version  # Should be 3.13 or higher

# Check installed packages
uv pip list | grep -E "(fastapi|neo4j|llama-index)"
```

#### 2. Neo4j Connection

```bash
# Test Neo4j connection
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'devpassword'))
with driver.session() as session:
    result = session.run('RETURN 1 as num')
    print(f'Neo4j connection successful: {result.single()[0]}')
driver.close()
"
```

#### 3. LLM Provider (Ollama)

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test model availability
ollama list
```

#### 4. Start Application

```bash
# Start the application
python -m codebase_rag

# You should see:
# ✓ All service health checks passed
# Application starting...
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 5. Test API Endpoints

In another terminal:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status":"healthy","neo4j":"connected","llm_provider":"ollama"}

# Test knowledge query
curl -X POST http://localhost:8000/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

#### 6. Run Tests

```bash
# Run unit tests
pytest tests/ -m unit -v

# Should see: All tests passed
```

### Common Verification Issues

**Neo4j not connecting:**
```bash
# Check if Neo4j is running
docker ps | grep neo4j  # For Docker
sudo systemctl status neo4j  # For native installation

# Check logs
docker logs code-graph-neo4j  # For Docker
sudo journalctl -u neo4j -f  # For native installation
```

**Ollama not responding:**
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama if not running
ollama serve
```

**Import errors:**
```bash
# Reinstall dependencies
uv pip install -e .

# Verify PYTHONPATH
echo $PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

## Troubleshooting

For common development environment issues, see the [Troubleshooting Guide](../troubleshooting.md).

### Quick Fixes

**Virtual environment not activating:**
```bash
# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

**Port already in use:**
```bash
# Find process using port 8000
lsof -i :8000  # On Linux/macOS
netstat -ano | findstr :8000  # On Windows

# Kill process or change port in .env
PORT=8001
```

**Neo4j memory issues:**
```bash
# Adjust Neo4j heap size in docker-compose.dev.yml
NEO4J_dbms_memory_heap_max__size=4G  # Increase if needed
```

## Next Steps

Now that your development environment is set up:

1. Read the [Contributing Guide](./contributing.md) for code standards
2. Review the [Testing Guide](./testing.md) to learn about writing tests
3. Explore the codebase starting with `main.py` and `services/`
4. Try running the examples in `examples/`
5. Make your first contribution!

## Getting Help

If you encounter issues during setup:

1. Check the [Troubleshooting Guide](../troubleshooting.md)
2. Search [GitHub Issues](https://github.com/royisme/codebase-rag/issues)
3. Create a new issue with:
   - Your OS and Python version
   - Complete error messages
   - Steps you've already tried

Happy developing!
