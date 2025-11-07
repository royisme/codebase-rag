#!/bin/bash
# Automated version bumping script using bump-my-version
# Usage: ./scripts/bump-version.sh [major|minor|patch] [--dry-run] [--no-changelog]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if bump-my-version is installed
if ! command -v bump-my-version &> /dev/null; then
    echo -e "${RED}Error: bump-my-version is not installed${NC}"
    echo "Install it with: pip install bump-my-version"
    exit 1
fi

# Parse arguments
BUMP_TYPE=${1:-patch}  # Default to patch
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

# Get current version
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)

# Calculate new version
case "$BUMP_TYPE" in
    major)
        NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1+1".0.0"}')
        ;;
    minor)
        NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2+1".0"}')
        ;;
    patch)
        NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2"."$3+1}')
        ;;
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

# Check for uncommitted changes
if [[ -z "$DRY_RUN" ]] && ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    echo "Please commit or stash your changes before bumping version"
    git status --short
    exit 1
fi

# Confirm with user (unless dry run)
if [[ -z "$DRY_RUN" ]]; then
    echo -e "${YELLOW}This will:${NC}"
    if [[ "$GENERATE_CHANGELOG" == true ]]; then
        echo "  1. Generate changelog from git commits"
        echo "  2. Update version in pyproject.toml, src/codebase_rag/__version__.py"
        echo "  3. Create a git commit"
        echo "  4. Create a git tag v$NEW_VERSION"
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

# Generate changelog if enabled
if [[ "$GENERATE_CHANGELOG" == true ]] && [[ -z "$DRY_RUN" ]]; then
    echo ""
    echo -e "${BLUE}Generating changelog from commits...${NC}"

    # Check if generate-changelog.py exists
    if [[ -f "scripts/generate-changelog.py" ]]; then
        if python3 scripts/generate-changelog.py --update --version "$NEW_VERSION"; then
            echo -e "${GREEN}✓ Changelog generated and updated${NC}"
            git add docs/changelog.md
        else
            echo -e "${YELLOW}⚠ Changelog generation failed, continuing anyway${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ scripts/generate-changelog.py not found, skipping changelog generation${NC}"
    fi
fi

# Run bump-my-version
echo ""
echo -e "${GREEN}Running bump-my-version...${NC}"

if [[ -n "$DRY_RUN" ]]; then
    bump-my-version bump "$BUMP_TYPE" --verbose --dry-run --allow-dirty
else
    bump-my-version bump "$BUMP_TYPE" --verbose
fi

if [[ $? -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}✓ Version bumped successfully!${NC}"
    echo ""

    if [[ -z "$DRY_RUN" ]]; then
        echo -e "${YELLOW}Next steps:${NC}"
        echo "  1. Review the changes: git show"
        echo "  2. Push changes: git push origin main"
        echo "  3. Push tag: git push origin v$NEW_VERSION"
        echo ""
        echo -e "${GREEN}GitHub Actions will automatically build and publish Docker images${NC}"
    else
        echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
        echo "Run without --dry-run to apply changes."
    fi
else
    echo -e "${RED}✗ Version bump failed${NC}"
    exit 1
fi
