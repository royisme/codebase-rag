# Scripts Directory

This directory contains utility scripts for development, deployment, and maintenance of the Codebase RAG system.

## 📜 Script Inventory

### Build & Frontend

#### `build-frontend.sh`
Builds the React frontend application and prepares it for deployment.

**Usage:**
```bash
./scripts/build-frontend.sh
```

**What it does:**
- Installs frontend dependencies (npm/pnpm)
- Builds the React application
- Copies build artifacts to `frontend/dist/`
- Required before building Docker images with frontend

**When to use:**
- Before building Docker images
- After making frontend changes
- For production deployments

---

### Docker Operations

#### `docker-start.sh`
Starts Docker Compose services with configuration validation.

**Usage:**
```bash
./scripts/docker-start.sh [minimal|standard|full]
```

**Features:**
- Environment validation
- Service dependency checks
- Health monitoring
- Supports all three deployment modes

**Examples:**
```bash
# Start minimal deployment
./scripts/docker-start.sh minimal

# Start full deployment with all features
./scripts/docker-start.sh full
```

#### `docker-stop.sh`
Gracefully stops all running Docker services.

**Usage:**
```bash
./scripts/docker-stop.sh
```

**What it does:**
- Stops all deployment modes (minimal, standard, full)
- Preserves volumes and data
- Clean shutdown of services

#### `docker-deploy.sh`
Comprehensive Docker deployment script with multi-mode support.

**Usage:**
```bash
./scripts/docker-deploy.sh [OPTIONS]
```

**Features:**
- Interactive deployment mode selection
- Environment configuration wizard
- Service health checks
- Ollama integration support

---

### Version Management

#### `bump-version.sh`
Automated version bumping with changelog generation.

**Usage:**
```bash
./scripts/bump-version.sh [major|minor|patch]
```

**What it does:**
1. Generates changelog from git commits
2. Updates version in `pyproject.toml` and `__version__.py`
3. Creates git tag
4. Commits version changes

**Examples:**
```bash
# Patch version: 0.7.0 → 0.7.1
./scripts/bump-version.sh patch

# Minor version: 0.7.0 → 0.8.0
./scripts/bump-version.sh minor

# Major version: 0.7.0 → 1.0.0
./scripts/bump-version.sh major
```

**Dependencies:**
- `bump-my-version` Python package
- Git repository with commits

#### `generate-changelog.py`
Generates CHANGELOG.md from git commit history.

**Usage:**
```bash
python scripts/generate-changelog.py
```

**Features:**
- Parses conventional commits (feat, fix, docs, etc.)
- Groups changes by type
- Generates Markdown format
- Automatically called by `bump-version.sh`

**Commit Format:**
```
feat: add new feature
fix: resolve bug
docs: update documentation
chore: maintenance tasks
```

---

### Database Operations

#### `neo4j_bootstrap.sh`
Bootstrap Neo4j database with schema and initial data.

**Usage:**
```bash
./scripts/neo4j_bootstrap.sh
```

**What it does:**
- Creates Neo4j database schema
- Sets up vector indexes
- Initializes constraints
- Loads seed data (if any)

**When to use:**
- First-time database setup
- After database reset
- Schema migrations

---

## 🔧 Development Workflow

### Building Docker Images

```bash
# 1. Build frontend
./scripts/build-frontend.sh

# 2. Build Docker image
make docker-build-minimal  # or standard/full
```

### Deploying Services

```bash
# Option 1: Using Makefile (recommended)
make docker-minimal

# Option 2: Using script directly
./scripts/docker-start.sh minimal
```

### Version Release

```bash
# 1. Make your changes and commit
git add .
git commit -m "feat: add new feature"

# 2. Bump version (generates changelog)
./scripts/bump-version.sh minor

# 3. Push changes and tags
git push && git push --tags

# 4. Build and push Docker images
make docker-push
```

---

## 📋 Prerequisites

### Required Tools

- **bash** - Shell scripting
- **docker** & **docker-compose** - Container management
- **npm** or **pnpm** - Frontend build
- **python 3.8+** - Changelog generation
- **git** - Version control

### Optional Tools

- **bump-my-version** - Version management (`pip install bump-my-version`)
- **mkdocs** - Documentation (`pip install mkdocs-material`)

---

## 🛡️ Safety Features

All scripts include:

- ✅ Error handling and validation
- ✅ User confirmations for destructive operations
- ✅ Detailed logging and output
- ✅ Rollback capabilities (where applicable)
- ✅ Environment checks

---

## 🐛 Troubleshooting

### Script Won't Execute

```bash
# Make script executable
chmod +x scripts/*.sh
```

### Docker Script Fails

```bash
# Check Docker daemon
docker ps

# Check Docker Compose version
docker-compose --version
```

### Frontend Build Fails

```bash
# Clean and rebuild
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

---

## 📚 Related Documentation

- [Development Setup](../docs/development/setup.md)
- [Version Management](../docs/development/version-management.md)
- [Deployment Guide](../docs/deployment/overview.md)
- [Docker Guide](../docs/deployment/docker.md)

---

## 🤝 Contributing

When adding new scripts:

1. Add executable permissions: `chmod +x scripts/your-script.sh`
2. Include usage documentation at the top of the script
3. Add error handling and validation
4. Update this README.md
5. Test in all deployment modes (if applicable)

---

**Last Updated:** 2025-11-06
**Maintained by:** Codebase RAG Team
