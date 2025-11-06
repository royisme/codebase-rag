# Version Management System Implementation

Complete automated version management system using bump-my-version.

## What Was Created

### 1. Configuration Files

**`.bumpversion.toml`** - bump-my-version configuration
- Defines version format (MAJOR.MINOR.PATCH)
- Lists all files to update
- Configures git commit and tag behavior
- Template for commit messages

### 2. Version Source Files

**`src/__version__.py`** - Runtime version access
- Authoritative version string
- Version tuple for comparisons
- Feature flags based on version
- Helper functions for version queries

**`pyproject.toml`** - Package metadata
- Updated to version 0.7.0
- Added description
- Added optional dev dependencies (bump-my-version, pytest, black, etc.)

### 3. Automation Scripts

**`scripts/bump-version.sh`** - User-friendly version bumping
- Interactive CLI with confirmation
- Validates no uncommitted changes
- Supports --dry-run mode
- Shows next steps after bumping
- Color-coded output

### 4. CI/CD Integration

**`.github/workflows/docker-build.yml`** - Enhanced with version validation
- New `validate-version` job runs first
- Checks pyproject.toml ↔ __version__.py consistency
- Validates git tag matches version (when releasing)
- Fails build if versions mismatch

### 5. Documentation

**`docs/development/version-management.md`** - Complete guide
- Overview of versioning strategy
- Tool usage instructions
- Standard release workflow
- Hotfix release workflow
- Docker image versioning explanation
- Runtime version access examples
- Troubleshooting section

## How It Works

### Version Bumping Flow

```
1. Developer decides to release
   ↓
2. Run: ./scripts/bump-version.sh minor
   ↓
3. Script validates clean working directory
   ↓
4. Script shows current → new version
   ↓
5. User confirms (y/N)
   ↓
6. bump-my-version updates:
   - pyproject.toml
   - src/__version__.py
   - docs/changelog.md (adds new version header)
   ↓
7. Creates git commit: "chore: bump version from 0.7.0 to 0.8.0"
   ↓
8. Creates git tag: v0.8.0
   ↓
9. Developer pushes: git push origin main && git push origin v0.8.0
   ↓
10. GitHub Actions triggers:
    - Validates version consistency
    - Builds 3 Docker images (minimal, standard, full)
    - Pushes to Docker Hub with version tags
    - Creates GitHub Release
```

### Version Validation Flow

```
GitHub Actions triggered by tag push
   ↓
validate-version job runs
   ↓
Reads pyproject.toml version: 0.8.0
   ↓
Reads __version__.py version: 0.8.0
   ↓
Extracts tag version: v0.8.0 → 0.8.0
   ↓
Compares all three ✅
   ↓
If match: Continue to build-minimal, build-standard, build-full
   ↓
If mismatch: ❌ Fail entire workflow
```

## Docker Image Tagging Strategy

When you push tag `v0.7.0`:

```
Created Docker tags:
├── Full version
│   ├── royisme/codebase-rag:0.7.0-minimal
│   ├── royisme/codebase-rag:0.7.0-standard
│   └── royisme/codebase-rag:0.7.0-full
│
├── Minor version (auto-updated for patches)
│   ├── royisme/codebase-rag:0.7-minimal
│   ├── royisme/codebase-rag:0.7-standard
│   └── royisme/codebase-rag:0.7-full
│
└── Latest (from main branch)
    ├── royisme/codebase-rag:minimal
    ├── royisme/codebase-rag:standard
    ├── royisme/codebase-rag:full
    └── royisme/codebase-rag:latest (→ full)
```

## Usage Examples

### Bump Patch Version (Bug Fix)

```bash
./scripts/bump-version.sh patch
# 0.7.0 → 0.7.1
```

### Bump Minor Version (New Feature)

```bash
./scripts/bump-version.sh minor
# 0.7.1 → 0.8.0
```

### Bump Major Version (Breaking Change)

```bash
./scripts/bump-version.sh major
# 0.8.0 → 1.0.0
```

### Dry Run (Preview Changes)

```bash
./scripts/bump-version.sh minor --dry-run
# Shows what would change without making changes
```

## Benefits

### Before (Manual Process)

```bash
# Error-prone, easy to forget steps
vim pyproject.toml        # Manually update version
vim src/__version__.py    # Manually update version
vim docs/changelog.md     # Manually add entry
git add ...
git commit -m "bump version"  # Often inconsistent messages
git tag v0.7.0            # Easy to forget
git push origin main
git push origin v0.7.0    # Easy to forget
# Risk: Versions out of sync, missing tags
```

### After (Automated Process)

```bash
# Single command, consistent, error-free
./scripts/bump-version.sh minor
git push origin main && git push origin v0.8.0
# Benefit: All files updated atomically, consistent messages, no mistakes
```

## Files Changed

1. **Created**:
   - `.bumpversion.toml` (65 lines)
   - `src/__version__.py` (31 lines)
   - `scripts/bump-version.sh` (128 lines, executable)
   - `docs/development/version-management.md` (456 lines)
   - `VERSION_MANAGEMENT_SUMMARY.md` (this file)

2. **Modified**:
   - `pyproject.toml` - Updated version to 0.7.0, added description, added dev dependencies
   - `.github/workflows/docker-build.yml` - Added validate-version job
   - `mkdocs.yml` - Added version-management.md to navigation

## Next Steps

1. **Review this PR**:
   - Check configuration in `.bumpversion.toml`
   - Test dry-run: `./scripts/bump-version.sh patch --dry-run`

2. **Merge to main**:
   ```bash
   # After PR approval
   git checkout main
   git pull origin main
   ```

3. **Create first release tag**:
   ```bash
   # This will trigger Docker builds
   git tag -a v0.7.0 -m "Release v0.7.0: Auto-extraction features + Docker multi-mode deployment"
   git push origin v0.7.0
   ```

4. **Verify**:
   - Check GitHub Actions workflow runs successfully
   - Check Docker Hub for new images: https://hub.docker.com/r/royisme/codebase-rag/tags
   - Check GitHub Release was created

5. **Future releases**:
   ```bash
   # Update changelog first
   vim docs/changelog.md

   # Bump version
   ./scripts/bump-version.sh minor

   # Push
   git push origin main
   git push origin v0.8.0
   ```

## Key Decisions

1. **Tool Choice**: bump-my-version (formerly bump2version)
   - Mature, widely used
   - TOML configuration
   - Git integration
   - Easy to customize

2. **Version Source**: pyproject.toml
   - Standard for Python projects
   - PEP 621 compliant
   - Single source of truth

3. **Tag Format**: `v{version}` (e.g., v0.7.0)
   - Common convention
   - Prefix 'v' for clarity
   - Matches GitHub Release format

4. **Commit Message**: `chore: bump version from X to Y`
   - Conventional Commits format
   - Clear intent
   - Easy to filter in git log

5. **Docker Tag Strategy**: Multiple tags per release
   - Full version for stability
   - Minor version for convenience
   - Latest for simplicity

## Troubleshooting

### Version mismatch error in CI

```bash
# Fix manually
vim pyproject.toml src/__version__.py
git add pyproject.toml src/__version__.py
git commit -m "fix: synchronize version numbers"
```

### Want to re-tag

```bash
# Delete local and remote tag
git tag -d v0.7.0
git push origin :refs/tags/v0.7.0

# Recreate
git tag -a v0.7.0 -m "Release v0.7.0"
git push origin v0.7.0
```

## References

- [Semantic Versioning](https://semver.org/)
- [bump-my-version Documentation](https://callowayproject.github.io/bump-my-version/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
