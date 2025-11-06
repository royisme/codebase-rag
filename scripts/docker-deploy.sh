#!/bin/bash
# Interactive deployment script for Code Graph Knowledge System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Code Graph Knowledge System - Docker Deployment       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

print_success "Docker and docker-compose are installed"
echo ""

# Display deployment modes
echo "Choose deployment mode:"
echo ""
echo -e "${GREEN}1) Minimal${NC}  - Code Graph only"
echo "   ✓ Repository ingestion and code analysis"
echo "   ✓ File search and relationship discovery"
echo "   ✓ Impact analysis and context packing"
echo "   ✗ No LLM or Embedding required"
echo ""
echo -e "${YELLOW}2) Standard${NC} - Code Graph + Memory Store"
echo "   ✓ All Minimal features"
echo "   ✓ Manual memory management"
echo "   ✓ Vector-based memory search"
echo "   ⚠  Embedding provider required"
echo ""
echo -e "${BLUE}3) Full${NC}     - All features"
echo "   ✓ All Standard features"
echo "   ✓ Automatic memory extraction"
echo "   ✓ Knowledge base RAG"
echo "   ✓ Document processing and Q&A"
echo "   ⚠  LLM + Embedding required"
echo ""

read -p "Enter choice [1-3]: " choice
echo ""

case $choice in
    1)
        MODE="minimal"
        COMPOSE_FILE="docker/docker-compose.minimal.yml"
        ;;
    2)
        MODE="standard"
        COMPOSE_FILE="docker/docker-compose.standard.yml"
        ;;
    3)
        MODE="full"
        COMPOSE_FILE="docker/docker-compose.full.yml"

        echo "Do you want to include local Ollama in Docker?"
        echo "(If you already have Ollama on your host, choose No)"
        read -p "[y/N]: " include_ollama

        if [ "$include_ollama" = "y" ] || [ "$include_ollama" = "Y" ]; then
            OLLAMA_PROFILE="--profile with-ollama"
            print_info "Will start Ollama in Docker container"
        else
            OLLAMA_PROFILE=""
            print_info "Assuming Ollama or other LLM on host/cloud"
        fi
        echo ""
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    print_info "Creating .env from template..."

    if [ -f "docker/.env.template/.env.$MODE" ]; then
        cp "docker/.env.template/.env.$MODE" .env
        print_success ".env file created"
        echo ""
        print_warning "Please edit .env file with your configuration"
        print_info "Required settings for $MODE mode:"

        case $MODE in
            minimal)
                echo "  - NEO4J_PASSWORD"
                ;;
            standard)
                echo "  - NEO4J_PASSWORD"
                echo "  - EMBEDDING_PROVIDER (ollama/openai/gemini)"
                echo "  - Provider-specific settings (API keys, etc.)"
                ;;
            full)
                echo "  - NEO4J_PASSWORD"
                echo "  - LLM_PROVIDER (ollama/openai/gemini/openrouter)"
                echo "  - EMBEDDING_PROVIDER"
                echo "  - Provider-specific settings (API keys, etc.)"
                ;;
        esac

        echo ""
        read -p "Press Enter after configuring .env file..."
    else
        print_error "Template file not found: docker/.env.template/.env.$MODE"
        exit 1
    fi
fi

# Display pre-deployment summary
echo ""
print_info "Deployment Summary:"
echo "  Mode: $MODE"
echo "  Compose file: $COMPOSE_FILE"
if [ -n "$OLLAMA_PROFILE" ]; then
    echo "  Ollama: Included in Docker"
fi
echo ""

# Confirm deployment
read -p "Proceed with deployment? [Y/n]: " confirm
if [ "$confirm" = "n" ] || [ "$confirm" = "N" ]; then
    print_info "Deployment cancelled"
    exit 0
fi

echo ""
print_info "Starting deployment..."

# Pull/build images
read -p "Pull images from Docker Hub or build locally? [pull/build]: " build_choice

if [ "$build_choice" = "pull" ]; then
    print_info "Pulling images from Docker Hub..."
    docker pull royisme/codebase-rag:$MODE || {
        print_warning "Failed to pull image, will build locally"
        build_choice="build"
    }
fi

if [ "$build_choice" = "build" ]; then
    print_info "Building Docker images..."
    docker-compose -f $COMPOSE_FILE build
    print_success "Build complete"
fi

# Start services
echo ""
print_info "Starting services..."
docker-compose -f $COMPOSE_FILE $OLLAMA_PROFILE up -d

# Wait for services to be healthy
echo ""
print_info "Waiting for services to be healthy..."
sleep 5

# Check health
if docker ps | grep -q "codebase-rag-mcp"; then
    print_success "MCP service is running"
else
    print_error "MCP service failed to start"
    print_info "Check logs with: docker-compose -f $COMPOSE_FILE logs"
    exit 1
fi

if docker ps | grep -q "codebase-rag-neo4j"; then
    print_success "Neo4j is running"
else
    print_error "Neo4j failed to start"
    exit 1
fi

# Display access information
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
print_success "Deployment successful!"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Access points:"
echo "  • API:          http://localhost:8000"
echo "  • API Docs:     http://localhost:8000/docs"
echo "  • Neo4j:        http://localhost:7474"
echo "  • Health Check: http://localhost:8000/api/v1/health"

if [ -n "$OLLAMA_PROFILE" ]; then
    echo "  • Ollama:       http://localhost:11434"
fi

echo ""
echo "Useful commands:"
echo "  • View logs:    docker-compose -f $COMPOSE_FILE logs -f"
echo "  • Stop:         docker-compose -f $COMPOSE_FILE down"
echo "  • Restart:      docker-compose -f $COMPOSE_FILE restart"
echo ""

case $MODE in
    minimal)
        print_info "Minimal mode - Available MCP tools:"
        echo "  • code_graph_ingest_repo"
        echo "  • code_graph_related"
        echo "  • code_graph_impact"
        echo "  • context_pack"
        ;;
    standard)
        print_info "Standard mode - Available MCP tools:"
        echo "  • All Code Graph tools"
        echo "  • add_memory, get_memory, update_memory, delete_memory"
        echo "  • search_memories (vector search)"
        ;;
    full)
        print_info "Full mode - All MCP tools available"
        echo "  • Code Graph, Memory, Knowledge RAG"
        echo "  • Automatic extraction from git/conversations"
        ;;
esac

echo ""
print_success "Ready to use!"
