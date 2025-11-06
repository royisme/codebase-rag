# Automatic Changelog Generation

Complete guide to automatically generating changelogs from git commits.

## Overview

Instead of manually writing changelog entries, we automatically generate them from git commit messages using **Conventional Commits** format.

**Benefits**:
- ✅ Never forget to update changelog
- ✅ Consistent formatting
- ✅ Automatic categorization
- ✅ Less manual work
- ✅ Traceable to specific commits

## Conventional Commits Format

All commits should follow this format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

| Type | Changelog Section | Description |
|------|------------------|-------------|
| `feat` | ### Added | New features |
| `fix` | ### Fixed | Bug fixes |
| `docs` | ### Documentation | Documentation changes |
| `perf` | ### Performance | Performance improvements |
| `refactor` | ### Changed | Code refactoring |
| `test` | ### Testing | Test updates |
| `build` | ### Build System | Build system changes |
| `ci` | ### CI/CD | CI/CD changes |
| `chore` | ### Maintenance | Maintenance tasks |
| `style` | ### Changed | Code style changes |

### Examples

**Feature**:
```bash
git commit -m "feat(memory): add auto-extraction from git commits

Implemented LLM-powered extraction of decisions and experiences
from git commit messages and changed files.

Closes #123"
```

**Bug Fix**:
```bash
git commit -m "fix(api): resolve timeout issue in document processing

Increased timeout for large files from 60s to 300s.
Added progress reporting for long-running operations."
```

**Breaking Change**:
```bash
git commit -m "feat(api)!: change memory search API response format

BREAKING CHANGE: The search response now returns results in a
different structure for better consistency with other endpoints.

Before: { "memories": [...] }
After: { "data": [...], "total": 10, "page": 1 }
```

**Documentation**:
```bash
git commit -m "docs: add deployment guide for minimal mode"
```

**Chore**:
```bash
git commit -m "chore: update dependencies to latest versions"
```

## Automatic Generation

### During Version Bump (Recommended)

The `bump-version.sh` script automatically generates changelog:

```bash
# This command will:
# 1. Generate changelog from commits since last tag
# 2. Update version numbers
# 3. Create commit and tag
./scripts/bump-version.sh minor
```

**What happens**:
1. Script finds all commits since last tag (e.g., `v0.7.0`)
2. Parses each commit message
3. Groups by type (Added, Fixed, etc.)
4. Generates formatted changelog section
5. Inserts into `docs/changelog.md` after `[Unreleased]`
6. Proceeds with version bump

### Manual Generation

Generate changelog without bumping version:

```bash
# Generate from latest tag to HEAD
python3 scripts/generate-changelog.py --update --version 0.8.0

# Generate from specific tag
python3 scripts/generate-changelog.py --from-tag v0.7.0 --update --version 0.8.0

# Preview without updating file
python3 scripts/generate-changelog.py --version 0.8.0

# Save to separate file
python3 scripts/generate-changelog.py --version 0.8.0 --output CHANGELOG_DRAFT.md
```

## Generated Format

The script generates entries in **Keep a Changelog** format:

```markdown
## [0.8.0] - 2025-01-20

### Added
- **memory**: Add auto-extraction from git commits
- **api**: Add new endpoint for batch memory operations
- Add support for Rust code parsing

### Fixed
- **api**: Resolve timeout issue in document processing
- **docker**: Fix volume mounting in minimal mode

### Changed
- **refactor**: Improve memory search performance
- Update dependencies to latest versions

### Documentation
- Add deployment guide for minimal mode
- Update API reference with new endpoints
```

## Workflow Integration

### Standard Release Workflow

```bash
# 1. Development - Use conventional commits
git commit -m "feat(api): add new feature X"
git commit -m "fix(core): resolve bug Y"
git push origin main

# 2. Ready to release
git checkout main
git pull origin main

# 3. Bump version (auto-generates changelog)
./scripts/bump-version.sh minor

# Output:
# === Version Bump Tool ===
# Current version: 0.7.0
# Bump type:       minor
# New version:     0.8.0
#
# This will:
#   1. Generate changelog from git commits
#   2. Update version in pyproject.toml, src/__version__.py
#   3. Create a git commit
#   4. Create a git tag v0.8.0
#
# Continue? (y/N) y
#
# Generating changelog from commits...
# Processing 15 commits...
# ✓ Changelog generated and updated
# ✓ Version bumped successfully!

# 4. Review and push
git show  # Review the commit
git push origin main
git push origin v0.8.0
```

### Skip Changelog Generation

If you want to manually edit changelog:

```bash
# Bump version without auto-generating changelog
./scripts/bump-version.sh minor --no-changelog

# Then manually edit
vim docs/changelog.md
git add docs/changelog.md
git commit --amend --no-edit
```

## Best Practices

### 1. Write Good Commit Messages

**Good**:
```bash
feat(memory): add conversation extraction

Implemented LLM-powered analysis of AI conversations to automatically
extract decisions, preferences, and experiences.

- Supports multiple conversation formats
- Configurable confidence threshold
- Auto-save option for high-confidence memories
```

**Bad**:
```bash
added stuff
```

### 2. Use Conventional Format Consistently

```bash
# ✅ Good
feat: add new feature
fix: resolve bug
docs: update guide

# ❌ Bad
Added new feature
Fixed the bug
Updated some docs
```

### 3. Group Related Changes

```bash
# ✅ Good - Separate commits for separate concerns
git commit -m "feat(api): add memory export endpoint"
git commit -m "docs(api): document memory export API"
git commit -m "test(api): add tests for memory export"

# ❌ Bad - Everything in one commit
git commit -m "add memory export with docs and tests"
```

### 4. Use Scopes for Clarity

```bash
feat(api): ...       # API changes
feat(memory): ...    # Memory store changes
feat(docker): ...    # Docker configuration
feat(docs): ...      # Documentation system
```

### 5. Mark Breaking Changes

```bash
# Method 1: Use ! after type
feat(api)!: change response format

# Method 2: Use footer
feat(api): change response format

BREAKING CHANGE: The API now returns data in a different structure.
```

## Customization

### Add New Commit Types

Edit `scripts/generate-changelog.py`:

```python
COMMIT_TYPE_MAP = {
    "feat": "### Added",
    "fix": "### Fixed",
    "docs": "### Documentation",
    # Add custom type
    "security": "### Security",
}
```

### Change Section Order

Edit `scripts/generate-changelog.py`:

```python
preferred_order = [
    "### ⚠️ Breaking Changes",
    "### Security",  # Add this
    "### Added",
    "### Fixed",
    # ...
]
```

### Custom Formatting

The script uses Python string formatting. Customize in `format_changelog_entry()`:

```python
# Current format:
# - **scope**: Subject

# Could change to:
# - [scope] Subject (abc123)  # Include commit hash
```

## Troubleshooting

### No commits found

**Problem**: Script says "No commits found to process"

**Solution**:
```bash
# Check if you have tags
git tag

# If no tags, specify manually
python3 scripts/generate-changelog.py --from-tag "" --update --version 0.8.0

# Or process all commits
python3 scripts/generate-changelog.py --update --version 0.8.0
```

### Commits not following format

**Problem**: Commits don't follow Conventional Commits

**Solution**:
- Old commits: Manually edit changelog
- Future commits: Follow the format
- Mix approach: Auto-generate what you can, manually add the rest

### Wrong version in changelog

**Problem**: Generated with wrong version number

**Solution**:
```bash
# Manually fix
vim docs/changelog.md

# Or regenerate
python3 scripts/generate-changelog.py --update --version 0.8.1
```

### Want to edit generated changelog

**Solution**:
```bash
# Generate first
./scripts/bump-version.sh minor

# Review generated changelog
vim docs/changelog.md

# Edit as needed

# Amend the commit
git add docs/changelog.md
git commit --amend --no-edit
```

## Migration from Manual Changelog

### If you have existing manual changelog

The script will preserve existing content and insert new sections.

**Steps**:
1. Ensure `docs/changelog.md` has `## [Unreleased]` section
2. Run generation - it will insert after Unreleased
3. Review and adjust if needed

### Converting old commits

For retroactive changelog generation:

```bash
# Generate from beginning
python3 scripts/generate-changelog.py --from-tag "" --version 0.7.0 > TEMP_CHANGELOG.md

# Manually merge into docs/changelog.md
# Clean up and adjust as needed
```

## Examples

### Example 1: Feature Release

```bash
# Commits since v0.7.0:
# - feat(memory): add conversation extraction
# - feat(api): add export endpoint
# - fix(docker): resolve volume issue
# - docs: update deployment guide

./scripts/bump-version.sh minor

# Generated changelog:
## [0.8.0] - 2025-01-20

### Added
- **memory**: Add conversation extraction
- **api**: Add export endpoint

### Fixed
- **docker**: Resolve volume issue

### Documentation
- Update deployment guide
```

### Example 2: Hotfix Release

```bash
# Critical bug fix
git commit -m "fix(api): resolve data corruption in memory export

Critical fix for issue where export could truncate large memories.
Added validation and error handling."

# Bump patch version
./scripts/bump-version.sh patch

# Generated:
## [0.7.1] - 2025-01-21

### Fixed
- **api**: Resolve data corruption in memory export
```

### Example 3: Breaking Change Release

```bash
# Breaking API change
git commit -m "feat(api)!: standardize all response formats

BREAKING CHANGE: All API endpoints now return consistent response
structure with 'data', 'meta', and 'errors' fields.

See migration guide in docs/api/migration.md"

# Major version bump
./scripts/bump-version.sh major

# Generated:
## [1.0.0] - 2025-01-25

### ⚠️ Breaking Changes
- **api**: Standardize all response formats

### Added
- **api**: Standardize all response formats
```

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Angular Commit Guidelines](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit)

## Quick Reference

| Command | Description |
|---------|-------------|
| `./scripts/bump-version.sh minor` | Bump version + auto-generate changelog |
| `./scripts/bump-version.sh minor --no-changelog` | Bump version without changelog |
| `python3 scripts/generate-changelog.py --update` | Generate changelog only |
| `python3 scripts/generate-changelog.py --from-tag v0.7.0` | From specific tag |
| `python3 scripts/generate-changelog.py --output FILE` | Save to file |

## Commit Message Template

Save this as `.gitmessage`:

```
<type>(<scope>): <subject>

# <body>

# <footer>

# Type: feat|fix|docs|style|refactor|perf|test|build|ci|chore
# Scope: api|memory|docker|core|docs (optional)
# Subject: imperative mood, lowercase, no period
#
# Body: explain what and why (optional)
#
# Footer: breaking changes, issues (optional)
#   BREAKING CHANGE: description
#   Closes #123
```

Configure git to use it:

```bash
git config commit.template .gitmessage
```
