#!/bin/bash
# =============================================================================
# Frontend Build Script using Bun
# =============================================================================
#
# This script builds the React frontend using Bun and prepares it for Docker.
# The compiled static files are placed in frontend/dist/ which will be copied
# to the Docker image's /app/static directory.
#
# Usage:
#   ./build-frontend.sh [--clean]
#
# Options:
#   --clean    Clean node_modules and dist before building
#
# Requirements:
#   - Bun >= 1.3.1
#
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FRONTEND_DIR="frontend"
CLEAN_BUILD=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --clean) CLEAN_BUILD=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Check if bun is installed
if ! command -v bun &> /dev/null; then
    echo -e "${RED}Error: Bun is not installed${NC}"
    echo "Install Bun: curl -fsSL https://bun.sh/install | bash"
    exit 1
fi

# Check bun version
BUN_VERSION=$(bun --version)
echo -e "${GREEN}Using Bun version: ${BUN_VERSION}${NC}"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Error: Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"

# Clean if requested
if [ "$CLEAN_BUILD" = true ]; then
    echo -e "${YELLOW}Cleaning node_modules and dist...${NC}"
    rm -rf node_modules dist .vite
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies with bun...${NC}"
bun install --frozen-lockfile

# Run type check
echo -e "${YELLOW}Running TypeScript type check...${NC}"
bun run tsc -b

# Run linting
echo -e "${YELLOW}Running linters...${NC}"
bun run lint:oxlint || true  # oxlint is optional
bun run lint

# Build for production
echo -e "${YELLOW}Building frontend for production...${NC}"
bun run build

# Verify build output
if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo -e "${RED}Error: Build failed - dist/index.html not found${NC}"
    exit 1
fi

# Show build output size
DIST_SIZE=$(du -sh dist | cut -f1)
echo -e "${GREEN}✅ Frontend build completed successfully${NC}"
echo -e "${GREEN}   Build output: dist/ (${DIST_SIZE})${NC}"
echo -e "${GREEN}   Ready for Docker build${NC}"

cd ..

# Show next steps
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Build Docker image: ${GREEN}docker build -t codebase-rag .${NC}"
echo "  2. Or use docker-compose: ${GREEN}docker-compose build${NC}"
echo ""
echo -e "${YELLOW}The frontend/dist/ directory will be copied to /app/static in the Docker image${NC}"
