# Version Management

Complete guide to version management in the Code Graph Knowledge System.

## Overview

We use **Semantic Versioning** (SemVer) with automated tooling to ensure consistency across all version references.

**Version Format**: `MAJOR.MINOR.PATCH` (e.g., `0.7.0`, `1.2.3`)

**Version Rules**:
- **MAJOR** (x.0.0): Breaking changes, major architecture updates
- **MINOR** (0.x.0): New features, backward compatible
- **PATCH** (0.0.x): Bug fixes, small improvements

## Tools

### bump-my-version

We use [bump-my-version](https://github.com/callowayproject/bump-my-version) (formerly `bump2version`) to automate version updates.

**Installation**:
```bash
pip install bump-my-version
```

**Configuration**: `.bumpversion.toml`

## Version Sources

### Single Source of Truth: `pyproject.toml`

The authoritative version is stored in `pyproject.toml`:

```toml
[project]
version = "0.7.0"
```

### Synchronized Files

These files are automatically updated by bump-my-version:

1. **`pyproject.toml`** - Package version
2. **`src/__version__.py`** - Runtime version access
3. **`docs/changelog.md`** - Version history
4. **Git tag** - `v0.7.0`

## Bumping Versions

### Method 1: Automated Script (Recommended)

```bash
# Patch version (0.7.0 → 0.7.1)
./scripts/bump-version.sh patch

# Minor version (0.7.1 → 0.8.0)
./scripts/bump-version.sh minor

# Major version (0.8.0 → 1.0.0)
./scripts/bump-version.sh major

# Dry run to preview changes
./scripts/bump-version.sh minor --dry-run
```

**What the script does**:
1. ✅ Validates no uncommitted changes
2. ✅ Shows current and new version
3. ✅ Asks for confirmation
4. ✅ Updates all version files
5. ✅ Creates git commit
6. ✅ Creates git tag
7. ✅ Shows next steps

### Method 2: Manual bump-my-version

```bash
# Bump patch version
bump-my-version bump patch

# Bump minor version
bump-my-version bump minor

# Bump major version
bump-my-version bump major

# Dry run
bump-my-version bump minor --dry-run

# Show current configuration
bump-my-version show-bump
```

### Method 3: Manual (Not Recommended)

If you need to bump manually:

```bash
# 1. Update version in all files
vim pyproject.toml          # version = "0.8.0"
vim src/__version__.py      # __version__ = "0.8.0"
vim docs/changelog.md       # Add new version entry

# 2. Commit changes
git add pyproject.toml src/__version__.py docs/changelog.md
git commit -m "chore: bump version to 0.8.0"

# 3. Create tag
git tag -a v0.8.0 -m "Release v0.8.0"

# 4. Push
git push origin main
git push origin v0.8.0
```

## Release Workflow

### Standard Release

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull origin main

# 2. Update changelog with release notes
vim docs/changelog.md
# Add release notes under [Unreleased] section

# 3. Commit changelog updates
git add docs/changelog.md
git commit -m "docs: update changelog for v0.8.0"
git push origin main

# 4. Bump version (creates commit + tag)
./scripts/bump-version.sh minor

# 5. Push changes and tag
git push origin main
git push origin v0.8.0

# 6. GitHub Actions automatically:
#    - Builds Docker images (minimal, standard, full)
#    - Pushes to Docker Hub with version tags
#    - Creates GitHub Release
```

### Hotfix Release

For urgent bug fixes on production:

```bash
# 1. Create hotfix branch from tag
git checkout -b hotfix/v0.7.1 v0.7.0

# 2. Fix the bug
git add <files>
git commit -m "fix: critical bug description"

# 3. Bump patch version
./scripts/bump-version.sh patch

# 4. Push and create PR
git push origin hotfix/v0.7.1

# 5. After merge, tag is already created
git checkout main
git pull origin main
git push origin v0.7.1
```

## Docker Image Versioning

When you push a tag `v0.7.0`, GitHub Actions creates these Docker images:

### Full Version Tags
```bash
royisme/codebase-rag:0.7.0-minimal
royisme/codebase-rag:0.7.0-standard
royisme/codebase-rag:0.7.0-full
```

### Minor Version Tags (auto-updated for patches)
```bash
royisme/codebase-rag:0.7-minimal
royisme/codebase-rag:0.7-standard
royisme/codebase-rag:0.7-full
```

### Latest Tags (from main branch)
```bash
royisme/codebase-rag:minimal
royisme/codebase-rag:standard
royisme/codebase-rag:full
royisme/codebase-rag:latest  # Points to full
```

### Development Tags (main branch, no tag)
```bash
royisme/codebase-rag:dev-minimal
royisme/codebase-rag:dev-standard
royisme/codebase-rag:dev-full
```

## Runtime Version Access

### Python Code

```python
from src.__version__ import __version__, get_features

# Get version string
print(f"Version: {__version__}")  # "0.7.0"

# Get version tuple
from src.__version__ import __version_info
print(__version_info__)  # (0, 7, 0)

# Check features
features = get_features()
if features["auto_extraction"]:
    print("Auto-extraction available")
```

### API Endpoint

```bash
# Health endpoint includes version
curl http://localhost:8000/api/v1/health

{
  "status": "healthy",
  "version": "0.7.0",
  "deployment_mode": "full"
}
```

### MCP Tool

```json
{
  "tool": "system_info",
  "response": {
    "version": "0.7.0",
    "features": ["code_graph", "memory_store", "auto_extraction"]
  }
}
```

## Version Validation in CI/CD

GitHub Actions validates version consistency:

```yaml
- name: Validate Version Consistency
  run: |
    # Get version from pyproject.toml
    PROJECT_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

    # Get version from __version__.py
    VERSION_PY=$(grep '__version__ = ' src/__version__.py | cut -d'"' -f2)

    # Get tag version (if tagged)
    if [[ $GITHUB_REF == refs/tags/* ]]; then
      TAG_VERSION=${GITHUB_REF#refs/tags/v}
      if [[ "$PROJECT_VERSION" != "$TAG_VERSION" ]]; then
        echo "Error: Version mismatch!"
        echo "pyproject.toml: $PROJECT_VERSION"
        echo "Git tag: $TAG_VERSION"
        exit 1
      fi
    fi

    # Validate Python version file
    if [[ "$PROJECT_VERSION" != "$VERSION_PY" ]]; then
      echo "Error: Version mismatch!"
      echo "pyproject.toml: $PROJECT_VERSION"
      echo "__version__.py: $VERSION_PY"
      exit 1
    fi

    echo "✓ All versions consistent: $PROJECT_VERSION"
```

## Changelog Format

Follow this format in `docs/changelog.md`:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features go here

### Changed
- Changes in existing functionality

### Fixed
- Bug fixes

## [0.8.0] - 2025-01-20

### Added
- Feature A
- Feature B

### Changed
- Updated dependency X

### Fixed
- Bug #123

## [0.7.0] - 2025-01-15

...
```

## Troubleshooting

### Version mismatch error

```bash
# If versions are out of sync, manually fix:
vim pyproject.toml src/__version__.py

# Then commit
git add pyproject.toml src/__version__.py
git commit -m "fix: synchronize version numbers"
```

### Tag already exists

```bash
# Delete local tag
git tag -d v0.7.0

# Delete remote tag
git push origin :refs/tags/v0.7.0

# Recreate tag
git tag -a v0.7.0 -m "Release v0.7.0"
git push origin v0.7.0
```

### Uncommitted changes

```bash
# Stash changes
git stash

# Bump version
./scripts/bump-version.sh patch

# Restore changes
git stash pop
```

## Best Practices

1. **Always bump on main branch** - Never bump version on feature branches
2. **Update changelog first** - Write release notes before bumping
3. **Use dry-run** - Preview changes with `--dry-run` flag
4. **Test before release** - Ensure all tests pass before creating tag
5. **Semantic meaning** - Follow SemVer strictly for predictability
6. **Document breaking changes** - Clearly mark breaking changes in changelog

## Quick Reference

| Task | Command |
|------|---------|
| Bump patch | `./scripts/bump-version.sh patch` |
| Bump minor | `./scripts/bump-version.sh minor` |
| Bump major | `./scripts/bump-version.sh major` |
| Dry run | `./scripts/bump-version.sh minor --dry-run` |
| Show current | `bump-my-version show-bump` |
| Manual bump | `bump-my-version bump patch` |
| Push release | `git push origin main && git push origin v0.x.0` |

## Resources

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [bump-my-version Docs](https://callowayproject.github.io/bump-my-version/)
- [Release Process Guide](release.md)
