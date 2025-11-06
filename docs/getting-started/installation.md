# Installation

This guide covers different installation methods for Code Graph Knowledge System.

## Prerequisites

### Required
- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Neo4j** 5.0+ (included in Docker setup)

### Optional (depending on deployment mode)
- **Ollama** (for local LLM/embedding) - Full and Standard modes
- **OpenAI API key** (for cloud LLM) - Full mode
- **Google Gemini API key** (for cloud LLM) - Full mode

## Installation Methods

### Method 1: Docker Compose (Recommended)

The easiest way to get started. Choose your deployment mode:

=== "Minimal (Code Graph Only)"

    ```bash
    # Clone repository
    git clone https://github.com/royisme/codebase-rag.git
    cd codebase-rag

    # Copy environment template
    cp docker/.env.template/.env.minimal .env

    # Edit .env and set Neo4j password
    nano .env

    # Start services
    docker-compose up -d
    ```

    **Requirements**: Only Neo4j (included)

=== "Standard (Code Graph + Memory)"

    ```bash
    # Clone repository
    git clone https://github.com/royisme/codebase-rag.git
    cd codebase-rag

    # Copy environment template
    cp docker/.env.template/.env.standard .env

    # Edit .env and configure embedding provider
    nano .env

    # Start services
    docker-compose -f docker/docker-compose.standard.yml up -d
    ```

    **Requirements**: Neo4j + Embedding model (Ollama or cloud)

=== "Full (All Features)"

    ```bash
    # Clone repository
    git clone https://github.com/royisme/codebase-rag.git
    cd codebase-rag

    # Copy environment template
    cp docker/.env.template/.env.full .env

    # Edit .env and configure LLM and embedding
    nano .env

    # Start with bundled Ollama
    docker-compose -f docker/docker-compose.full.yml --profile with-ollama up -d

    # Or use external LLM
    docker-compose -f docker/docker-compose.full.yml up -d
    ```

    **Requirements**: Neo4j + LLM + Embedding model

### Method 2: Docker Hub (Pull Pre-built Images)

Pull official images from Docker Hub:

```bash
# Minimal
docker pull royisme/codebase-rag:minimal

# Standard
docker pull royisme/codebase-rag:standard

# Full
docker pull royisme/codebase-rag:full
```

Then use with docker-compose files or run directly with docker run.

### Method 3: Local Development

For development or local testing without Docker:

```bash
# Clone repository
git clone https://github.com/royisme/codebase-rag.git
cd codebase-rag

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e .

# Start Neo4j separately (required)
# ... see Neo4j installation docs

# Copy and configure environment
cp env.example .env
nano .env

# Start MCP server
python -m codebase_rag --mcp

# Or start FastAPI server
python -m codebase_rag
```

## Verify Installation

After installation, verify services are running:

```bash
# Check Docker containers
docker ps

# Test health endpoint (if using FastAPI)
curl http://localhost:8000/api/v1/health

# Check Neo4j
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p your_password "RETURN 'Connected' as status;"
```

## Next Steps

- [Configuration Guide](configuration.md) - Configure your deployment
- [Quick Start](quickstart.md) - Get started with basic operations
- [Deployment Overview](../deployment/overview.md) - Choose the right deployment mode

## Troubleshooting Installation

### Docker Issues

**Problem**: Port already in use
```bash
# Check what's using the port
sudo lsof -i :7687  # Neo4j
sudo lsof -i :8000  # MCP server

# Change port in docker-compose.yml if needed
```

**Problem**: Permission denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Neo4j Connection Issues

**Problem**: Cannot connect to Neo4j
```bash
# Check Neo4j logs
docker logs codebase-rag-neo4j

# Verify Neo4j is ready
docker exec codebase-rag-neo4j neo4j status
```

### Ollama Issues

**Problem**: Cannot connect to Ollama
```bash
# Check Ollama is running
docker logs codebase-rag-ollama

# Test Ollama connection
curl http://localhost:11434/api/version
```

For more issues, see the [Troubleshooting Guide](../troubleshooting.md).
