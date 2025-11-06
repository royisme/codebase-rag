# Docker Deployment Guide

Comprehensive guide for deploying Code Graph Knowledge System using Docker and Docker Compose.

## Overview

The system provides three Docker images:
- `royisme/codebase-rag:minimal` - Code Graph only (smallest)
- `royisme/codebase-rag:standard` - Code Graph + Memory
- `royisme/codebase-rag:full` - All features (largest)

## Docker Compose Files

### Location
- `docker-compose.yml` - Default (points to minimal)
- `docker/docker-compose.minimal.yml` - Minimal mode
- `docker/docker-compose.standard.yml` - Standard mode
- `docker/docker-compose.full.yml` - Full mode with optional Ollama

### Common Structure

All compose files include:
```yaml
services:
  neo4j:
    image: neo4j:5-enterprise  # or neo4j:5-community
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j-data:/data
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt

  mcp:
    image: royisme/codebase-rag:MODE
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - DEPLOYMENT_MODE=MODE
    volumes:
      - ./repos:/repos
      - ./data:/data
    depends_on:
      - neo4j
```

## Building Custom Images

### Build from Source

```bash
# Clone repository
git clone https://github.com/royisme/codebase-rag.git
cd codebase-rag

# Build minimal
docker build -f docker/Dockerfile.minimal -t my-codebase-rag:minimal .

# Build standard
docker build -f docker/Dockerfile.standard -t my-codebase-rag:standard .

# Build full
docker build -f docker/Dockerfile.full -t my-codebase-rag:full .
```

### Build with Buildx (Multi-Platform)

```bash
# Create builder
docker buildx create --name mybuilder --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile.minimal \
  -t my-codebase-rag:minimal \
  --push \
  .
```

## Volume Management

### Important Volumes

**1. Neo4j Data** (`neo4j-data`)
```yaml
volumes:
  neo4j-data:
    driver: local
```

Contains all graph database data. **Must be backed up regularly.**

**2. Repository Mount** (`./repos:/repos`)
```yaml
volumes:
  - ./repos:/repos:ro  # Read-only recommended
```

Mount local repositories for ingestion.

**3. Application Data** (`./data:/data`)
```yaml
volumes:
  - ./data:/data
```

Temporary files, logs, and processing data.

### Backup Volumes

```bash
# Backup Neo4j data
docker run --rm \
  -v codebase-rag_neo4j-data:/data \
  -v $(pwd)/backup:/backup \
  alpine \
  tar czf /backup/neo4j-backup-$(date +%Y%m%d).tar.gz /data

# Restore from backup
docker run --rm \
  -v codebase-rag_neo4j-data:/data \
  -v $(pwd)/backup:/backup \
  alpine \
  tar xzf /backup/neo4j-backup-20241106.tar.gz -C /
```

## Network Configuration

### Default Network

```yaml
networks:
  default:
    name: codebase-rag-network
```

### Custom Network

```yaml
networks:
  codebase-rag:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

services:
  neo4j:
    networks:
      codebase-rag:
        ipv4_address: 172.28.0.10
```

### External Services

Connect to external Ollama:

```yaml
services:
  mcp:
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Environment Variables

### Core Variables

```bash
# Neo4j Connection
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure_password>
NEO4J_DATABASE=neo4j

# Deployment Mode
DEPLOYMENT_MODE=minimal|standard|full
ENABLE_KNOWLEDGE_RAG=true|false
ENABLE_AUTO_EXTRACTION=true|false
```

### LLM Configuration

```bash
# Provider Selection
LLM_PROVIDER=ollama|openai|gemini|openrouter
EMBEDDING_PROVIDER=ollama|openai|gemini|huggingface

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Gemini
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001
```

### Performance Tuning

```bash
# Timeouts (seconds)
CONNECTION_TIMEOUT=30
OPERATION_TIMEOUT=300
LARGE_DOCUMENT_TIMEOUT=600

# Neo4j Memory
NEO4J_server_memory_heap_initial__size=2G
NEO4J_server_memory_heap_max__size=4G
NEO4J_server_memory_pagecache_size=2G
```

## Docker Profiles

Use profiles to optionally include services:

```yaml
services:
  ollama:
    profiles:
      - with-ollama
    image: ollama/ollama:latest
```

```bash
# Start without Ollama
docker-compose up -d

# Start with Ollama
docker-compose --profile with-ollama up -d
```

## Health Checks

All images include health checks:

```yaml
services:
  mcp:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      start_period: 40s
      retries: 3
```

Check health:

```bash
# View health status
docker ps

# Check specific container
docker inspect --format='{{.State.Health.Status}}' codebase-rag-mcp

# View health logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' codebase-rag-mcp
```

## Resource Limits

### Memory Limits

```yaml
services:
  mcp:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### CPU Limits

```yaml
services:
  mcp:
    deploy:
      resources:
        limits:
          cpus: '2.0'
        reservations:
          cpus: '1.0'
```

## Logging

### Configure Logging Driver

```yaml
services:
  mcp:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### View Logs

```bash
# Follow logs
docker-compose logs -f mcp

# Last 100 lines
docker-compose logs --tail=100 mcp

# Since timestamp
docker-compose logs --since 2024-11-06T10:00:00 mcp
```

## Multi-Stage Deployment

### Development

```yaml
# docker-compose.dev.yml
services:
  mcp:
    build:
      context: .
      dockerfile: docker/Dockerfile.minimal
    volumes:
      - .:/app  # Mount source code
    environment:
      - DEBUG=true
```

### Production

```yaml
# docker-compose.prod.yml
services:
  mcp:
    image: royisme/codebase-rag:minimal
    restart: unless-stopped
    logging:
      driver: "syslog"
    deploy:
      resources:
        limits:
          memory: 4G
```

## Security Best Practices

### 1. Use Secrets

```yaml
services:
  mcp:
    secrets:
      - neo4j_password
      - openai_api_key

secrets:
  neo4j_password:
    file: ./secrets/neo4j_password.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
```

### 2. Non-Root User

All images run as non-root user `appuser` (UID 1000).

### 3. Read-Only Filesystem

```yaml
services:
  mcp:
    read_only: true
    tmpfs:
      - /tmp
      - /app/temp
```

### 4. Network Isolation

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access

services:
  mcp:
    networks:
      - frontend
  neo4j:
    networks:
      - backend
```

## Updating Images

### Pull Latest

```bash
# Pull latest image
docker pull royisme/codebase-rag:minimal

# Recreate containers
docker-compose up -d --force-recreate mcp
```

### Zero-Downtime Update

```bash
# Scale up new version
docker-compose up -d --scale mcp=2 --no-recreate

# Remove old container
docker stop codebase-rag-mcp-1
docker rm codebase-rag-mcp-1

# Scale back to 1
docker-compose up -d --scale mcp=1
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs codebase-rag-mcp

# Check health
docker inspect codebase-rag-mcp

# Try recreating
docker-compose down
docker-compose up -d
```

### Network Issues

```bash
# Test connectivity
docker exec -it codebase-rag-mcp ping neo4j

# Check network
docker network inspect codebase-rag-network

# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check Neo4j performance
docker exec -it codebase-rag-neo4j cypher-shell -u neo4j -p password
# Run: CALL dbms.listQueries();

# Increase resources in docker-compose.yml
```

## Advanced Patterns

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml codebase-rag

# Scale service
docker service scale codebase-rag_mcp=3
```

### Using Kubernetes

See separate Kubernetes deployment guide (coming soon).

## Next Steps

- [Minimal Mode Guide](minimal.md) - Deploy minimal mode
- [Production Setup](production.md) - Production best practices
- [Troubleshooting](../troubleshooting.md) - Common issues
