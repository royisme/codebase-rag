#!/bin/bash
# Stop Code Graph Knowledge System Docker services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Code Graph Knowledge System...${NC}"

# Parse arguments
REMOVE_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --remove-data)
            REMOVE_VOLUMES=true
            shift
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            echo "Usage: $0 [--remove-data]"
            echo "  --remove-data: Remove all data volumes (Neo4j data, Ollama models)"
            exit 1
            ;;
    esac
done

if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${RED}WARNING: This will remove all data including Neo4j database and Ollama models!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${GREEN}Cancelled.${NC}"
        exit 0
    fi
    docker compose --profile with-ollama down -v
    echo -e "${GREEN}Services stopped and data removed.${NC}"
else
    docker compose --profile with-ollama down
    echo -e "${GREEN}Services stopped (data preserved).${NC}"
fi

echo -e "${YELLOW}To start again: ./docker-start.sh${NC}"
