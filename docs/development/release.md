# Release Process

This guide covers the complete release process for the Code Graph Knowledge System, including version management, Docker builds, and deployment.

## Overview

### Release Types

1. **Major Release** (x.0.0) - Breaking changes, major new features
2. **Minor Release** (0.x.0) - New features, backward compatible
3. **Patch Release** (0.0.x) - Bug fixes, minor improvements
4. **Hotfix Release** (0.0.x) - Critical bug fixes

### Release Artifacts

Each release produces:
- **Git tag** (`vX.Y.Z`)
- **GitHub release** with release notes
- **Docker images** (minimal, standard, full)
- **PyPI package** (future)
- **Updated documentation**

### Release Schedule

- **Major releases**: As needed (quarterly target)
- **Minor releases**: Monthly
- **Patch releases**: As needed
- **Hotfixes**: Immediate (for critical issues)

## Version Strategy

### Semantic Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH
  |     |     |
  |     |     +-- Bug fixes, minor improvements
  |     +-------- New features, backward compatible
  +-------------- Breaking changes, major features
```

### Version Examples

**Patch Release (0.6.1 → 0.6.2):**
- Fix Neo4j connection timeout
- Update dependency versions
- Fix documentation typos

**Minor Release (0.6.2 → 0.7.0):**
- Add automatic memory extraction
- New MCP tools
- Performance improvements

**Major Release (0.7.0 → 1.0.0):**
- Complete API redesign
- New authentication system
- Breaking configuration changes

### Current Version

Version is managed in:
- `pyproject.toml`: `version = "0.3.0"`
- Git tags: `v0.7.0`
- Docker images: `royisme/codebase-rag:0.7.0-*`

## Pre-Release Checklist

Before starting a release, ensure:

### Code Quality

- [ ] All tests pass locally
- [ ] CI/CD pipeline is green
- [ ] Code coverage meets requirements (70%+)
- [ ] No known critical bugs
- [ ] Security scan passes (Trivy)
- [ ] Code review completed for all changes

### Documentation

- [ ] CHANGELOG.md updated
- [ ] API documentation current
- [ ] User guides updated
- [ ] Breaking changes documented
- [ ] Migration guide created (if needed)
- [ ] README.md updated

### Dependencies

- [ ] Dependencies up to date
- [ ] Security vulnerabilities addressed
- [ ] Compatibility tested
- [ ] Requirements files updated

### Testing

```bash
# Run full test suite
pytest tests/ -v --cov=services --cov=api --cov=mcp_tools

# Run integration tests
pytest tests/ -m integration

# Test Docker builds locally
docker build -f docker/Dockerfile.minimal -t test:minimal .
docker build -f docker/Dockerfile.standard -t test:standard .
docker build -f docker/Dockerfile.full -t test:full .
```

### Communication

- [ ] Release notes drafted
- [ ] Breaking changes communicated
- [ ] Known issues documented
- [ ] User announcements prepared

## Release Process

### Step 1: Prepare Release Branch

```bash
# Ensure main branch is up to date
git checkout main
git pull origin main

# Create release branch
git checkout -b release/v0.7.0
```

### Step 2: Update Version Numbers

Update version in `pyproject.toml`:

```toml
[project]
name = "code-graph"
version = "0.7.0"  # Update this
description = "Add your description here"
```

**Optional**: Update version in other files if needed:
```bash
# If version is defined elsewhere
find . -name "*.py" -exec grep -l "__version__" {} \;
```

### Step 3: Update CHANGELOG.md

```markdown
# Changelog

## [0.7.0] - 2025-01-15

### Added
- Automatic memory extraction from conversations
- Git commit analysis for memory extraction
- Code comment mining for TODO/FIXME markers
- Query-based memory suggestions
- Batch repository extraction

### Changed
- Improved MCP handler architecture
- Enhanced error messages for memory operations

### Fixed
- Neo4j connection timeout in Docker
- Memory search relevance scoring

### Security
- Updated dependencies with security patches

## [0.6.0] - 2024-12-20
...
```

### Step 4: Update Documentation

```bash
# Update user documentation
vim docs/guide/memory-extraction.md

# Update API documentation
vim docs/api/memory-endpoints.md

# Update README if needed
vim README.md
```

### Step 5: Commit Changes

```bash
# Commit version and changelog updates
git add pyproject.toml docs/changelog.md README.md
git commit -m "chore: prepare release v0.7.0"

# Push release branch
git push origin release/v0.7.0
```

### Step 6: Create Pull Request

1. Create PR from `release/v0.7.0` to `main`
2. Title: "Release v0.7.0"
3. Description: Include release notes
4. Request review from maintainers
5. Wait for CI/CD to pass
6. Merge when approved

### Step 7: Tag the Release

```bash
# After PR is merged, checkout main
git checkout main
git pull origin main

# Create annotated tag
git tag -a v0.7.0 -m "Release version 0.7.0

### Added
- Automatic memory extraction features
- Enhanced MCP tools

### Changed
- Improved error handling

### Fixed
- Neo4j connection issues"

# Push tag to trigger release workflow
git push origin v0.7.0
```

### Step 8: Monitor Automated Builds

The tag push triggers GitHub Actions workflows:

1. **Docker builds** (`docker-build.yml`)
   - Builds minimal, standard, and full images
   - Tags with version number and latest
   - Pushes to Docker Hub

2. **GitHub release** (`docker-build.yml`)
   - Creates GitHub release
   - Generates release notes
   - Attaches artifacts

Monitor at: `https://github.com/royisme/codebase-rag/actions`

## Docker Image Builds

### Build Configuration

Three Docker images are built for each release:

#### 1. Minimal Image
**Tag**: `royisme/codebase-rag:0.7.0-minimal`
**Contents**: Code Graph only, no memory features
**Size**: ~800MB
**Use case**: Lightweight code analysis

```dockerfile
# docker/Dockerfile.minimal
FROM python:3.13-slim
# ... minimal dependencies
```

#### 2. Standard Image
**Tag**: `royisme/codebase-rag:0.7.0-standard`
**Contents**: Code Graph + Memory Store
**Size**: ~1.2GB
**Use case**: Memory-enhanced development

```dockerfile
# docker/Dockerfile.standard
FROM python:3.13-slim
# ... includes memory features
```

#### 3. Full Image
**Tag**: `royisme/codebase-rag:0.7.0-full` (also `latest`)
**Contents**: All features + UI + monitoring
**Size**: ~1.5GB
**Use case**: Complete development environment

```dockerfile
# docker/Dockerfile.full
FROM python:3.13-slim
# ... all features included
```

### Automated Build Process

When a version tag is pushed:

1. **GitHub Actions** triggered by tag push
2. **Build images** for all three variants
3. **Multi-platform build** (amd64, arm64)
4. **Push to Docker Hub** with multiple tags:
   - Version tag: `0.7.0-minimal`
   - Major.minor tag: `0.7-minimal`
   - Variant tag: `minimal`
   - Latest tag: `latest` (full image only)

### Manual Docker Build

For testing or emergency releases:

```bash
# Build minimal
docker build -f docker/Dockerfile.minimal -t royisme/codebase-rag:0.7.0-minimal .

# Build standard
docker build -f docker/Dockerfile.standard -t royisme/codebase-rag:0.7.0-standard .

# Build full
docker build -f docker/Dockerfile.full -t royisme/codebase-rag:0.7.0-full .

# Test image
docker run -d --name test-release \
  -p 8000:8000 \
  -e NEO4J_URI=bolt://neo4j:7687 \
  royisme/codebase-rag:0.7.0-full

# Verify
curl http://localhost:8000/api/v1/health

# Cleanup
docker stop test-release
docker rm test-release

# Push manually (if needed)
docker push royisme/codebase-rag:0.7.0-minimal
docker push royisme/codebase-rag:0.7.0-standard
docker push royisme/codebase-rag:0.7.0-full
```

### Docker Image Testing

```bash
# Test minimal image
docker-compose -f docker/docker-compose.minimal.yml up -d
# Run smoke tests
curl http://localhost:8000/api/v1/health
docker-compose -f docker/docker-compose.minimal.yml down

# Test standard image
docker-compose -f docker/docker-compose.standard.yml up -d
# Test memory endpoints
curl -X POST http://localhost:8000/api/v1/memory/add -H "Content-Type: application/json" -d '{"project_id":"test","memory_type":"decision","title":"Test","content":"Test"}'
docker-compose -f docker/docker-compose.standard.yml down

# Test full image
docker-compose -f docker/docker-compose.full.yml up -d
# Access monitoring UI
open http://localhost:8000/ui/monitor
docker-compose -f docker/docker-compose.full.yml down
```

## GitHub Release

### Automated Release Creation

The `docker-build.yml` workflow automatically creates a GitHub release when a tag is pushed:

```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    generate_release_notes: true
    body: |
      ## Docker Images

      ### Minimal (Code Graph only)
      ```bash
      docker pull royisme/codebase-rag:0.7.0-minimal
      ```

      ### Standard (Code Graph + Memory)
      ```bash
      docker pull royisme/codebase-rag:0.7.0-standard
      ```

      ### Full (All Features)
      ```bash
      docker pull royisme/codebase-rag:0.7.0-full
      ```
```

### Manual Release Creation

If automated release fails:

1. Go to: `https://github.com/royisme/codebase-rag/releases/new`
2. **Tag**: Select `v0.7.0`
3. **Title**: "Release v0.7.0 - Automatic Memory Extraction"
4. **Description**: Copy from CHANGELOG.md and add Docker pull commands
5. **Attachments**: Add any additional files
6. Click "Publish release"

### Release Notes Template

```markdown
## What's New in v0.7.0

This release introduces automatic memory extraction capabilities, enabling the system to learn from conversations, code comments, and git commits.

### 🚀 New Features

- **Automatic Memory Extraction**: Extract memories from AI conversations
- **Git Commit Analysis**: Analyze commits for decisions and experiences
- **Code Comment Mining**: Extract TODO, FIXME, NOTE markers
- **Batch Repository Extraction**: Comprehensive codebase analysis
- **5 new MCP tools** for memory extraction

### 🔧 Improvements

- Enhanced error messages for memory operations
- Improved MCP handler architecture (78% code reduction)
- Better timeout handling for large documents

### 🐛 Bug Fixes

- Fixed Neo4j connection timeout in Docker environments
- Resolved memory search relevance scoring issues
- Fixed environment variable handling in Docker

### 📚 Documentation

- Complete memory extraction guide
- Updated API documentation
- New troubleshooting guide

### 🐳 Docker Images

#### Minimal (Code Graph only)
```bash
docker pull royisme/codebase-rag:0.7.0-minimal
```

#### Standard (Code Graph + Memory)
```bash
docker pull royisme/codebase-rag:0.7.0-standard
```

#### Full (All Features)
```bash
docker pull royisme/codebase-rag:0.7.0-full
docker pull royisme/codebase-rag:latest
```

### 📖 Documentation

Full documentation: https://code-graph.vantagecraft.dev

### ⚠️ Breaking Changes

None in this release.

### 🙏 Contributors

Thanks to all contributors who made this release possible!

**Full Changelog**: https://github.com/royisme/codebase-rag/compare/v0.6.0...v0.7.0
```

## Documentation Updates

### Update Documentation Site

```bash
# Update MkDocs documentation
cd docs/

# Build documentation locally
mkdocs build

# Test locally
mkdocs serve
# Open http://localhost:8000

# Documentation auto-deploys via GitHub Actions
# Verify at: https://code-graph.vantagecraft.dev
```

### Update Docker Hub

1. Go to: `https://hub.docker.com/r/royisme/codebase-rag`
2. Update description with latest version info
3. Update README with new features
4. Add release notes

### Update README Badges

Update version badges in `README.md`:

```markdown
[![Version](https://img.shields.io/badge/version-0.7.0-blue.svg)](https://github.com/royisme/codebase-rag/releases/tag/v0.7.0)
[![Docker](https://img.shields.io/docker/v/royisme/codebase-rag?label=docker)](https://hub.docker.com/r/royisme/codebase-rag)
```

## Post-Release Tasks

### Immediate Tasks (Within 24 Hours)

1. **Monitor Docker Hub** for successful image pushes
2. **Test deployed images** with quick smoke tests
3. **Check documentation** site updated correctly
4. **Monitor error reports** from new release
5. **Respond to GitHub issues** related to release

### Week 1 Tasks

1. **Monitor metrics** for performance regressions
2. **Track user feedback** on new features
3. **Address critical bugs** with hotfix if needed
4. **Update project board** with next milestone
5. **Write blog post** announcing release (optional)

### Ongoing Tasks

1. **Close resolved issues** that were fixed in release
2. **Update roadmap** with completed features
3. **Plan next release** with new features
4. **Review and merge** pending PRs
5. **Engage with community** feedback

## Hotfix Process

For critical bugs that need immediate release:

### Step 1: Create Hotfix Branch

```bash
# Branch from latest release tag
git checkout v0.7.0
git checkout -b hotfix/v0.7.1
```

### Step 2: Fix the Bug

```bash
# Make minimal changes to fix critical bug
vim services/memory_store.py

# Add tests
vim tests/test_memory_store.py

# Commit fix
git add .
git commit -m "fix: resolve critical memory corruption issue"
```

### Step 3: Update Version

```bash
# Update to patch version
vim pyproject.toml  # 0.7.0 → 0.7.1

# Update changelog
vim docs/changelog.md
```

### Step 4: Fast-Track Release

```bash
# Push hotfix branch
git push origin hotfix/v0.7.1

# Create PR to main (expedited review)
# After merge, tag immediately
git checkout main
git pull origin main
git tag -a v0.7.1 -m "Hotfix: Critical memory corruption"
git push origin v0.7.1
```

### Step 5: Communicate

- Post GitHub release immediately
- Notify users in discussions
- Update documentation
- Consider backporting to older versions if needed

## Rollback Procedures

If a release has critical issues:

### Docker Rollback

Users can revert to previous version:

```bash
# Pull previous version
docker pull royisme/codebase-rag:0.6.0-full

# Update docker-compose.yml
image: royisme/codebase-rag:0.6.0-full

# Restart
docker-compose down
docker-compose up -d
```

### Git Rollback

For repository issues:

```bash
# Revert to previous release
git checkout v0.6.0

# Or create revert commit
git revert <commit-hash>
git push origin main
```

### Communication

1. **Create GitHub issue** explaining the problem
2. **Update release notes** with warning
3. **Publish hotfix** as soon as possible
4. **Document root cause** and prevention measures

## Release Checklist Summary

```markdown
## Pre-Release
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] Dependencies updated
- [ ] Security scan passed

## Release
- [ ] Create release branch
- [ ] Update version numbers
- [ ] Commit and push changes
- [ ] Create and merge PR
- [ ] Create and push git tag
- [ ] Monitor Docker builds
- [ ] Verify GitHub release created

## Post-Release
- [ ] Test Docker images
- [ ] Verify documentation updated
- [ ] Announce release
- [ ] Monitor for issues
- [ ] Close related issues
- [ ] Plan next release
```

## Questions?

For questions about the release process:

1. Check [Contributing Guide](./contributing.md)
2. Review previous releases
3. Ask in GitHub Discussions
4. Contact maintainers

## Useful Commands Reference

```bash
# Version bump helper
grep -r "version" pyproject.toml

# List all tags
git tag -l

# Show tag details
git show v0.7.0

# Delete local tag
git tag -d v0.7.0

# Delete remote tag (careful!)
git push origin :refs/tags/v0.7.0

# Compare releases
git log v0.6.0..v0.7.0 --oneline

# Build all Docker images
for variant in minimal standard full; do
  docker build -f docker/Dockerfile.$variant -t royisme/codebase-rag:0.7.0-$variant .
done
```

## Resources

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Docker Hub](https://hub.docker.com/r/royisme/codebase-rag)
