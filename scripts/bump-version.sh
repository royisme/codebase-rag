#!/bin/bash
# Automated version bumping script using bump-my-version
# Usage: ./scripts/bump-version.sh [major|minor|patch] [--dry-run] [--no-changelog]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if bump-my-version is installed
if ! command -v bump-my-version &>/dev/null; then
  echo -e "${RED}Error: bump-my-version is not installed${NC}"
  echo "Install it with: pip install bump-my-version"
  exit 1
fi

# Parse arguments
BUMP_TYPE=${1:-patch} # Default to patch
DRY_RUN=""
GENERATE_CHANGELOG=true

for arg in "$@"; do
  case $arg in
  --dry-run)
    DRY_RUN="--dry-run"
    ;;
  --no-changelog)
    GENERATE_CHANGELOG=false
    ;;
  esac
done

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
  echo -e "${RED}Error: Invalid bump type '$BUMP_TYPE'${NC}"
  echo "Usage: $0 [major|minor|patch] [--dry-run] [--no-changelog]"
  exit 1
fi

# Get current version (from pyproject.toml)
if ! CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | cut -d'"' -f2); then
  echo -e "${RED}Error: Cannot read current version from pyproject.toml${NC}"
  exit 1
fi

# Calculate new version (preview)
case "$BUMP_TYPE" in
major) NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1+1".0.0"}') ;;
minor) NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2+1".0"}') ;;
patch) NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2"."$3+1}') ;;
esac

echo -e "${YELLOW}=== Version Bump Tool ===${NC}"
echo -e "Current version: ${GREEN}$CURRENT_VERSION${NC}"
echo -e "Bump type:       ${GREEN}$BUMP_TYPE${NC}"
echo -e "New version:     ${GREEN}$NEW_VERSION${NC}"
echo ""

if [[ -n "$DRY_RUN" ]]; then
  echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
  echo ""
fi

# Require clean working tree for real bump (keeps history tidy)
if [[ -z "$DRY_RUN" ]]; then
  if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    echo "Please commit or stash your changes before bumping version"
    git status --short
    exit 1
  fi
fi

# Confirm with user (unless dry run)
if [[ -z "$DRY_RUN" ]]; then
  echo -e "${YELLOW}This will:${NC}"
  if [[ "$GENERATE_CHANGELOG" == true ]]; then
    echo "  1. Update version in pyproject.toml, src/codebase_rag/__version__.py"
    echo "  2. Create a git commit"
    echo "  3. Create a git tag v$NEW_VERSION"
    echo "  4. Generate changelog and merge into the same commit (amend)"
  else
    echo "  1. Update version in pyproject.toml, src/codebase_rag/__version__.py"
    echo "  2. Create a git commit"
    echo "  3. Create a git tag v$NEW_VERSION"
  fi
  echo ""
  read -p "Continue? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 0
  fi
fi

echo ""
echo -e "${GREEN}Running bump-my-version...${NC}"

if [[ -n "$DRY_RUN" ]]; then
  # Preview only; do NOT touch files or tags
  bump-my-version bump "$BUMP_TYPE" --verbose --dry-run --allow-dirty
  echo -e "${YELLOW}Dry-run complete. No files were changed.${NC}"
  exit 0
else
  # 1) Perform the actual bump on a clean tree (creates commit + tag)
  bump-my-version bump "$BUMP_TYPE" --verbose
fi

echo ""
echo -e "${BLUE}Post-bump tasks...${NC}"

# 2) Generate changelog (after bump), then fold it into the same commit
if [[ "$GENERATE_CHANGELOG" == true ]]; then
  echo -e "${BLUE}Generating changelog from commits...${NC}"
  if [[ -f "scripts/generate-changelog.py" ]]; then
    if python3 scripts/generate-changelog.py --update --version "$NEW_VERSION"; then
      echo -e "${GREEN}✓ Changelog generated and updated${NC}"
      git add docs/changelog.md || true

      # 3) Amend the previous bump commit to include changelog
      git commit --amend --no-edit

      # 4) Force-move tag to amended commit (keep tag pointing at final state)
      git tag -f "v$NEW_VERSION"
    else
      echo -e "${YELLOW}⚠ Changelog generation failed, leaving version bump commit as-is${NC}"
    fi
  else
    echo -e "${YELLOW}⚠ scripts/generate-changelog.py not found, skipping changelog generation${NC}"
  fi
else
  echo -e "${YELLOW}Skipping changelog generation (--no-changelog)${NC}"
fi

echo ""
echo -e "${GREEN}✓ Version bumped to v$NEW_VERSION successfully!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review the changes: git show"
echo "  2. Push commit:        git push origin HEAD"
echo "  3. Push tag:           git push -f origin v$NEW_VERSION"
echo ""
echo -e "${GREEN}GitHub Actions will automatically build and publish artifacts (if configured).${NC}"
