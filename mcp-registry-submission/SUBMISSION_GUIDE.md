# Docker MCP Registry Submission Guide

## Prerequisites Checklist

Before submitting, ensure:

- [x] **License**: Project has MIT or Apache 2 license (GPL not allowed)
- [x] **Docker Images**: Built and available on Docker Hub
  - `royisme/codebase-rag:minimal`
  - `royisme/codebase-rag:standard`
  - `royisme/codebase-rag:full`
- [x] **Dockerfiles**: Present in repository
- [x] **Tools List**: `tools.json` files created for all variants
- [x] **Server Config**: `server.yaml` files completed
- [x] **Public Repository**: GitHub repository is public
- [ ] **Documentation**: docs.vantagecraft.dev is live (pending DNS)
- [ ] **CI Passing**: GitHub Actions workflows succeed

## Step-by-Step Submission

### 1. Verify Docker Images Are Published

```bash
# Check images are available
docker pull royisme/codebase-rag:minimal
docker pull royisme/codebase-rag:standard
docker pull royisme/codebase-rag:full

# Verify they work
docker run --rm royisme/codebase-rag:minimal --help
```

### 2. Fork MCP Registry

1. Go to https://github.com/docker/mcp-registry
2. Click "Fork" button
3. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp-registry.git
   cd mcp-registry
   ```

### 3. Add Server Configurations

```bash
# Copy our submission files
cp -r /path/to/codebase-rag/mcp-registry-submission/codebase-rag-minimal servers/
cp -r /path/to/codebase-rag/mcp-registry-submission/codebase-rag-standard servers/
cp -r /path/to/codebase-rag/mcp-registry-submission/codebase-rag-full servers/

# Verify structure
ls -la servers/codebase-rag-*
```

Each directory should contain:
- `server.yaml`
- `tools.json`

### 4. Test Locally (Optional)

If the registry has a test command:

```bash
# Install dependencies (if task tool is available)
task validate server=codebase-rag-minimal
task validate server=codebase-rag-standard
task validate server=codebase-rag-full
```

### 5. Create Pull Request

```bash
# Create branch
git checkout -b add-codebase-rag

# Stage files
git add servers/codebase-rag-*

# Commit
git commit -m "Add Code Graph Knowledge System (3 variants: minimal, standard, full)

This PR adds Code Graph Knowledge System, an AI-powered code intelligence
and knowledge management system.

Three deployment variants:

1. codebase-rag-minimal (Code Graph only, no LLM)
   - Repository analysis and indexing
   - File relationship discovery
   - Impact analysis
   - Context packing for AI assistants

2. codebase-rag-standard (Code Graph + Memory Store)
   - All minimal features
   - Manual memory management
   - Vector-based memory search
   - Requires: Embedding model

3. codebase-rag-full (All features)
   - All standard features
   - Automatic memory extraction (git, conversations, comments)
   - Knowledge base RAG (document Q&A)
   - Batch repository analysis
   - Requires: LLM + Embedding

Repository: https://github.com/royisme/codebase-rag
Docker Hub: https://hub.docker.com/r/royisme/codebase-rag
Documentation: https://docs.vantagecraft.dev
License: MIT"

# Push
git push origin add-codebase-rag
```

### 6. Open Pull Request on GitHub

1. Go to your fork on GitHub
2. Click "Contribute" → "Open pull request"
3. Title: `Add Code Graph Knowledge System (3 variants)`
4. Description:
   ```markdown
   ## Overview

   Adding Code Graph Knowledge System - an AI-powered code intelligence system
   with three deployment modes based on LLM requirements.

   ## Variants Included

   1. **codebase-rag-minimal** - Code Graph only (no LLM)
   2. **codebase-rag-standard** - + Memory Store (embedding required)
   3. **codebase-rag-full** - All features (LLM + embedding)

   ## Links

   - Repository: https://github.com/royisme/codebase-rag
   - Docker Hub: https://hub.docker.com/r/royisme/codebase-rag
   - Documentation: https://docs.vantagecraft.dev

   ## Testing

   All three variants have been tested locally with:
   - Neo4j 5.15
   - Multiple LLM providers (Ollama, OpenAI, Gemini)
   - Various repository sizes

   ## License

   MIT License - compliant with Docker MCP Registry requirements.

   ## Checklist

   - [x] Dockerfiles present in repository
   - [x] Images published to Docker Hub
   - [x] Tools list provided (tools.json)
   - [x] Configuration schema defined
   - [x] Multi-architecture support (AMD64, ARM64)
   - [x] Public repository
   - [ ] CI passing (waiting for initial push)
   ```
5. Click "Create pull request"

### 7. Monitor PR Status

1. Watch for CI/CD checks
2. Address any failures reported by automated checks
3. Respond to reviewer comments
4. Wait for Docker team approval

## Common Issues and Solutions

### Issue: Build Failures

**Cause**: Tools can't be listed without configuration

**Solution**: We've provided `tools.json` files to avoid this

### Issue: CI Failures

**Cause**: Invalid YAML syntax or schema

**Solution**: Validate YAML files:
```bash
# Install yamllint
pip install yamllint

# Validate
yamllint servers/codebase-rag-*/server.yaml
```

### Issue: Image Not Found

**Cause**: Docker images not yet pushed to Docker Hub

**Solution**:
```bash
# Ensure images are published
make docker-build-all
make docker-push
```

### Issue: Missing Required Fields

**Cause**: server.yaml missing required fields

**Solution**: Check all required fields are present:
- `name`
- `type`
- `meta.category`
- `about.title`
- `about.description`
- `source.project`

## Expected Timeline

1. **PR Opened**: You submit the PR
2. **Automated Checks**: ~5-10 minutes
3. **Docker Team Review**: 1-7 days
4. **Approval & Merge**: Same day as approval
5. **Catalog Update**: Within 24 hours
6. **Available Everywhere**:
   - MCP catalog
   - Docker Desktop toolkit
   - Docker Hub `mcp` namespace

## Post-Approval

Once approved and merged:

1. **Verify Listing**:
   - Check Docker MCP catalog
   - Check Docker Desktop's MCP toolkit
   - Search for "codebase-rag" or "code graph"

2. **Update Documentation**:
   - Add badge to README
   - Update docs with MCP registry information
   - Add quick start guide for Docker Desktop users

3. **Announce**:
   - GitHub Discussions
   - Social media
   - Blog post (optional)

## Badge for README

Once approved, add this badge to your README:

```markdown
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-Available-blue?logo=docker)](https://mcp-registry.docker.com/search?q=codebase-rag)
```

## Support

If you encounter issues:

1. Check Docker MCP Registry documentation
2. Review other approved servers for examples
3. Open issue in mcp-registry repository
4. Ask in Docker Community forums

## Contact

For questions about this submission:
- GitHub Issues: https://github.com/royisme/codebase-rag/issues
- Repository: https://github.com/royisme/codebase-rag
