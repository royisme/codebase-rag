# Docker Setup Guide

This guide explains how to run the Code Graph Knowledge System using Docker Compose for one-command local setup.

## Quick Start

### 1. Prerequisites

- Docker (v20.10+)
- Docker Compose (v2.0+)
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

### 2. Start Services

**Basic setup (without local LLM):**
```bash
./docker-start.sh
```

**With Ollama (local LLM):**
```bash
./docker-start.sh --with-ollama
```

**Rebuild application:**
```bash
./docker-start.sh --build
```

### 3. Access Services

Once started, you can access:

- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/api/v1/metrics
- **Neo4j Browser**: http://localhost:7474
  - Username: `neo4j`
  - Password: `password123`
- **Ollama** (if enabled): http://localhost:11434

### 4. Stop Services

**Stop (keep data):**
```bash
./docker-stop.sh
```

**Stop and remove all data:**
```bash
./docker-stop.sh --remove-data
```

## Configuration

### Environment Variables

The application uses `.env` file for configuration. Copy `env.example` to `.env` and customize:

```bash
cp env.example .env
```

Key configuration options:

```bash
# Neo4j (automatically configured in Docker)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM Provider (ollama, openai, gemini, openrouter)
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama

# For OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4

# For Gemini
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=...
# GEMINI_MODEL=gemini-pro
```

### Using Ollama

If you started with `--with-ollama`, you need to pull models:

```bash
# Pull LLM model
docker compose exec ollama ollama pull llama3.2

# Pull embedding model
docker compose exec ollama ollama pull nomic-embed-text

# List available models
docker compose exec ollama ollama list
```

## Architecture

The Docker Compose setup includes:

1. **Neo4j** - Graph database for code knowledge
   - Persistent data in `neo4j_data` volume
   - APOC plugins enabled
   - Web interface on port 7474

2. **Application** - FastAPI backend
   - Auto-restarts on failure
   - Health checks enabled
   - Logs to `./logs` directory

3. **Ollama** (Optional) - Local LLM hosting
   - Models stored in `ollama_data` volume
   - Supports various models (llama, mistral, etc.)

## Common Operations

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f neo4j
docker compose logs -f ollama
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart app
```

### Execute Commands

```bash
# Run Python command in app container
docker compose exec app python -c "print('Hello')"

# Access Neo4j shell
docker compose exec neo4j cypher-shell -u neo4j -p password123

# Pull Ollama model
docker compose exec ollama ollama pull llama3.2
```

### Bootstrap Neo4j Schema

```bash
docker compose exec app python scripts/neo4j_bootstrap.py
```

### Update Application Code

After updating code, rebuild and restart:

```bash
docker compose up --build -d app
```

## Data Persistence

### Volumes

Data is persisted in Docker volumes:

- `neo4j_data` - Neo4j database
- `neo4j_logs` - Neo4j logs
- `ollama_data` - Ollama models

### Backup Neo4j Data

```bash
# Create backup
docker compose exec neo4j neo4j-admin database dump neo4j \
  --to-path=/var/lib/neo4j/data/dumps

# Copy backup to host
docker compose cp neo4j:/var/lib/neo4j/data/dumps/neo4j.dump ./backup.dump
```

### Restore Neo4j Data

```bash
# Copy backup to container
docker compose cp ./backup.dump neo4j:/var/lib/neo4j/data/dumps/neo4j.dump

# Stop database and restore
docker compose exec neo4j neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/data/dumps
```

## Troubleshooting

### Services Won't Start

1. Check Docker is running:
   ```bash
   docker info
   ```

2. Check logs:
   ```bash
   docker compose logs
   ```

3. Remove old containers and try again:
   ```bash
   docker compose down
   ./docker-start.sh
   ```

### Neo4j Connection Issues

1. Verify Neo4j is healthy:
   ```bash
   docker compose ps
   ```

2. Test connection:
   ```bash
   docker compose exec neo4j cypher-shell -u neo4j -p password123 "RETURN 1"
   ```

3. Check APOC is loaded:
   ```bash
   docker compose exec neo4j cypher-shell -u neo4j -p password123 "CALL apoc.help('all')"
   ```

### Application Errors

1. Check application logs:
   ```bash
   docker compose logs -f app
   ```

2. Verify environment variables:
   ```bash
   docker compose exec app env | grep NEO4J
   ```

3. Restart application:
   ```bash
   docker compose restart app
   ```

### Ollama Issues

1. Verify Ollama is running:
   ```bash
   docker compose ps ollama
   ```

2. Check available models:
   ```bash
   docker compose exec ollama ollama list
   ```

3. Test model:
   ```bash
   docker compose exec ollama ollama run llama3.2 "Hello"
   ```

## Performance Tuning

### Neo4j Memory

Edit `docker-compose.yml` to adjust Neo4j memory:

```yaml
environment:
  - NEO4J_dbms_memory_heap_max__size=4G
  - NEO4J_dbms_memory_pagecache_size=1G
```

### Application Workers

Add environment variable to app service:

```yaml
environment:
  - WORKERS=4
```

## Security Notes

### Production Deployment

For production:

1. Change Neo4j password:
   ```yaml
   - NEO4J_AUTH=neo4j/your-strong-password
   ```

2. Use environment variable files:
   ```bash
   docker compose --env-file .env.production up -d
   ```

3. Enable HTTPS with reverse proxy (nginx, traefik)

4. Use Docker secrets for sensitive data

5. Limit container resources:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

## Advanced Usage

### Custom Network

The services use a custom bridge network `codebase-rag-network`. You can connect other services:

```yaml
services:
  my-service:
    networks:
      - codebase-rag-network

networks:
  codebase-rag-network:
    external: true
```

### Development Mode

For development with hot-reload:

```yaml
services:
  app:
    volumes:
      - .:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Multiple Environments

Create environment-specific compose files:

```bash
# Development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## Support

For issues or questions:
- Check logs: `docker compose logs -f`
- View service status: `docker compose ps`
- Restart services: `docker compose restart`
- Full reset: `./docker-stop.sh --remove-data && ./docker-start.sh --build`
