#!/bin/bash
# Start Code Graph Knowledge System with Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Code Graph Knowledge System - Docker Startup${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker Compose is not available.${NC}"
    exit 1
fi

# Parse arguments
WITH_OLLAMA=false
BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-ollama)
            WITH_OLLAMA=true
            shift
            ;;
        --build)
            BUILD=true
            shift
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            echo "Usage: $0 [--with-ollama] [--build]"
            echo "  --with-ollama: Include Ollama service for local LLM"
            echo "  --build: Rebuild the application image"
            exit 1
            ;;
    esac
done

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from env.example...${NC}"
    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${GREEN}.env file created. Please review and update it if needed.${NC}"
    else
        echo -e "${RED}Error: env.example not found. Cannot create .env file.${NC}"
        exit 1
    fi
fi

# Build command
CMD="docker compose"

if [ "$WITH_OLLAMA" = true ]; then
    echo -e "${GREEN}Starting with Ollama (local LLM)...${NC}"
    CMD="$CMD --profile with-ollama"
fi

if [ "$BUILD" = true ]; then
    echo -e "${GREEN}Building application image...${NC}"
    CMD="$CMD up --build -d"
else
    CMD="$CMD up -d"
fi

# Start services
echo -e "${GREEN}Starting services...${NC}"
$CMD

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
echo -e "${YELLOW}This may take 30-60 seconds...${NC}"
echo ""

# Wait for Neo4j
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker compose exec -T neo4j cypher-shell -u neo4j -p password123 "RETURN 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Neo4j is ready${NC}"
        break
    fi
    RETRY=$((RETRY+1))
    echo -n "."
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Neo4j failed to start${NC}"
    echo -e "${YELLOW}Check logs: docker compose logs neo4j${NC}"
    exit 1
fi

# Wait for application
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is ready${NC}"
        break
    fi
    RETRY=$((RETRY+1))
    echo -n "."
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Application failed to start${NC}"
    echo -e "${YELLOW}Check logs: docker compose logs app${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Services are ready!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "📊 ${GREEN}Application:${NC} http://localhost:8000"
echo -e "📖 ${GREEN}API Docs:${NC} http://localhost:8000/docs"
echo -e "🗄️  ${GREEN}Neo4j Browser:${NC} http://localhost:7474"
echo -e "   ${YELLOW}Username:${NC} neo4j"
echo -e "   ${YELLOW}Password:${NC} password123"

if [ "$WITH_OLLAMA" = true ]; then
    echo -e "🤖 ${GREEN}Ollama:${NC} http://localhost:11434"
    echo ""
    echo -e "${YELLOW}Note: You need to pull Ollama models first:${NC}"
    echo -e "   docker compose exec ollama ollama pull llama3.2"
    echo -e "   docker compose exec ollama ollama pull nomic-embed-text"
fi

echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View logs:        docker compose logs -f"
echo -e "  Stop services:    docker compose down"
echo -e "  Restart:          docker compose restart"
echo -e "  Bootstrap Neo4j:  docker compose exec app python -c 'from src.codebase_rag.services.graph import graph_service; graph_service._setup_schema()'"
echo ""
