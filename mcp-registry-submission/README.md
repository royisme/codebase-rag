# MCP Registry Submission for Code Graph Knowledge System

This directory contains the submission files for registering Code Graph Knowledge System in the Docker MCP Registry.

## Three Deployment Variants

We provide three separate MCP server entries to match different user needs:

### 1. codebase-rag-minimal (Code Graph Only)
- **No LLM required** - Pure graph-based code intelligence
- **Image**: `royisme/codebase-rag:minimal`
- **Tools**: 4 (code graph operations)
- **Use case**: Developers who want code navigation without LLM overhead

### 2. codebase-rag-standard (Code Graph + Memory)
- **Embedding required** - Vector-powered memory search
- **Image**: `royisme/codebase-rag:standard`
- **Tools**: 11 (code graph + memory management)
- **Use case**: Teams building project knowledge bases

### 3. codebase-rag-full (All Features)
- **LLM + Embedding required** - Complete AI capabilities
- **Image**: `royisme/codebase-rag:full`
- **Tools**: 30 (code graph + memory + RAG + auto-extraction)
- **Use case**: AI-assisted development workflows

## Submission Process

1. Fork https://github.com/docker/mcp-registry
2. Copy the three directories to `servers/`:
   ```bash
   cp -r mcp-registry-submission/codebase-rag-* /path/to/mcp-registry/servers/
   ```
3. Test locally (if possible)
4. Create pull request with title: "Add Code Graph Knowledge System (3 variants)"
5. Wait for Docker team review

## File Structure

Each variant contains:
- `server.yaml` - MCP server configuration
- `tools.json` - Static tool list (required for servers needing pre-configuration)

## Requirements Met

✅ **License**: MIT (confirmed in repository)
✅ **Type**: Local (containerized) - Docker builds and hosts images
✅ **Dockerfile**: Available in repository (`docker/Dockerfile.*`)
✅ **Tools List**: Provided (`tools.json`) - prevents build failures
✅ **Public Repository**: https://github.com/royisme/codebase-rag
✅ **Documentation**: https://docs.vantagecraft.dev (once deployed)

## Configuration Requirements

### Minimal
- Neo4j connection (URI, user, password)

### Standard
- Neo4j connection
- Embedding provider (Ollama/OpenAI/Gemini)

### Full
- Neo4j connection
- LLM provider (Ollama/OpenAI/Gemini/OpenRouter)
- Embedding provider

## Notes

- All three images will be built and hosted by Docker
- Images support both AMD64 and ARM64 architectures
- Neo4j database runs as separate container (configured in docker-compose)
- Users can choose cloud or local LLM providers
- Documentation available at https://docs.vantagecraft.dev

## Links

- **Repository**: https://github.com/royisme/codebase-rag
- **Docker Hub**: https://hub.docker.com/r/royisme/codebase-rag
- **Documentation**: https://docs.vantagecraft.dev
- **Issues**: https://github.com/royisme/codebase-rag/issues
