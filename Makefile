# Makefile for Code Graph Knowledge System
# Provides convenient commands for Docker operations

.PHONY: help docker-minimal docker-standard docker-full docker-full-with-ollama \
        docker-build-minimal docker-build-standard docker-build-full docker-build-all \
        docker-push docker-pull docker-clean docker-logs docker-stop \
        dev-minimal dev-standard dev-full docs-serve docs-build docs-deploy

# Docker Hub username
DOCKER_USER ?= royisme

# Default target
help:
	@echo "Code Graph Knowledge System - Docker Commands"
	@echo "=============================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make docker-minimal          - Start minimal deployment (Code Graph only, no LLM)"
	@echo "  make docker-standard         - Start standard deployment (+ Memory, needs Embedding)"
	@echo "  make docker-full             - Start full deployment (all features, needs LLM)"
	@echo "  make docker-full-with-ollama - Start full deployment with local Ollama"
	@echo ""
	@echo "Build Commands:"
	@echo "  make docker-build-minimal    - Build minimal image"
	@echo "  make docker-build-standard   - Build standard image"
	@echo "  make docker-build-full       - Build full image"
	@echo "  make docker-build-all        - Build all images"
	@echo ""
	@echo "Management:"
	@echo "  make docker-stop             - Stop all services"
	@echo "  make docker-clean            - Stop and remove all containers/volumes"
	@echo "  make docker-logs             - Show logs from all services"
	@echo "  make docker-push             - Push all images to Docker Hub"
	@echo "  make docker-pull             - Pull all images from Docker Hub"
	@echo ""
	@echo "Development:"
	@echo "  make dev-minimal             - Start minimal in dev mode (mounted code)"
	@echo "  make dev-standard            - Start standard in dev mode"
	@echo "  make dev-full                - Start full in dev mode"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs-serve              - Serve documentation locally"
	@echo "  make docs-build              - Build documentation"
	@echo "  make docs-deploy             - Deploy documentation to vantagecraft.dev"
	@echo ""

# ============================================
# Deployment Commands
# ============================================

docker-minimal:
	@echo "🚀 Starting Minimal deployment (Code Graph only)..."
	@echo "   ✓ No LLM or Embedding required"
	@echo "   ✓ Code Graph tools available"
	@echo ""
	docker-compose -f docker/docker-compose.minimal.yml up -d
	@echo ""
	@echo "✅ Minimal deployment started!"
	@echo "   API: http://localhost:8000"
	@echo "   Neo4j Browser: http://localhost:7474"
	@echo ""
	@echo "Check status: make docker-logs"

docker-standard:
	@echo "🚀 Starting Standard deployment (Code Graph + Memory)..."
	@echo "   ⚠️  Embedding provider required (check .env)"
	@echo "   ✓ Code Graph + Memory Store"
	@echo ""
	docker-compose -f docker/docker-compose.standard.yml up -d
	@echo ""
	@echo "✅ Standard deployment started!"
	@echo "   API: http://localhost:8000"
	@echo "   Neo4j Browser: http://localhost:7474"

docker-full:
	@echo "🚀 Starting Full deployment (All features)..."
	@echo "   ⚠️  LLM + Embedding required (check .env)"
	@echo "   ✓ Code Graph + Memory + Knowledge RAG"
	@echo ""
	docker-compose -f docker/docker-compose.full.yml up -d
	@echo ""
	@echo "✅ Full deployment started!"
	@echo "   API: http://localhost:8000"
	@echo "   Neo4j Browser: http://localhost:7474"

docker-full-with-ollama:
	@echo "🚀 Starting Full deployment with local Ollama..."
	@echo "   ✓ Ollama will be started in Docker"
	@echo "   ✓ All features enabled"
	@echo ""
	docker-compose -f docker/docker-compose.full.yml --profile with-ollama up -d
	@echo ""
	@echo "✅ Full deployment with Ollama started!"
	@echo "   API: http://localhost:8000"
	@echo "   Neo4j Browser: http://localhost:7474"
	@echo "   Ollama: http://localhost:11434"
	@echo ""
	@echo "⏳ Ollama may take a few minutes to download models..."
	@echo "   Check: docker logs codebase-rag-ollama-full -f"

# ============================================
# Build Commands
# ============================================

docker-build-minimal:
	@echo "🔨 Building minimal image..."
	docker-compose -f docker/docker-compose.minimal.yml build
	@echo "✅ Minimal image built: royisme/codebase-rag:minimal"

docker-build-standard:
	@echo "🔨 Building standard image..."
	docker-compose -f docker/docker-compose.standard.yml build
	@echo "✅ Standard image built: royisme/codebase-rag:standard"

docker-build-full:
	@echo "🔨 Building full image..."
	docker-compose -f docker/docker-compose.full.yml build
	@echo "✅ Full image built: royisme/codebase-rag:full"

docker-build-all: docker-build-minimal docker-build-standard docker-build-full
	@echo ""
	@echo "✅ All images built successfully!"

# ============================================
# Docker Hub Commands
# ============================================

docker-push: docker-build-all
	@echo "📤 Pushing images to Docker Hub..."
	docker tag royisme/codebase-rag:minimal royisme/codebase-rag:minimal-latest
	docker tag royisme/codebase-rag:standard royisme/codebase-rag:standard-latest
	docker tag royisme/codebase-rag:full royisme/codebase-rag:full-latest
	docker push royisme/codebase-rag:minimal
	docker push royisme/codebase-rag:minimal-latest
	docker push royisme/codebase-rag:standard
	docker push royisme/codebase-rag:standard-latest
	docker push royisme/codebase-rag:full
	docker push royisme/codebase-rag:full-latest
	@echo "✅ All images pushed to Docker Hub!"

docker-pull:
	@echo "📥 Pulling images from Docker Hub..."
	docker pull royisme/codebase-rag:minimal
	docker pull royisme/codebase-rag:standard
	docker pull royisme/codebase-rag:full
	@echo "✅ All images pulled!"

# ============================================
# Management Commands
# ============================================

docker-stop:
	@echo "🛑 Stopping all services..."
	-docker-compose -f docker/docker-compose.minimal.yml down
	-docker-compose -f docker/docker-compose.standard.yml down
	-docker-compose -f docker/docker-compose.full.yml down
	@echo "✅ All services stopped"

docker-clean:
	@echo "🧹 Cleaning up all containers and volumes..."
	@read -p "This will remove all data. Continue? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose -f docker/docker-compose.minimal.yml down -v; \
		docker-compose -f docker/docker-compose.standard.yml down -v; \
		docker-compose -f docker/docker-compose.full.yml down -v; \
		echo "✅ Cleanup complete"; \
	else \
		echo "❌ Cleanup cancelled"; \
	fi

docker-logs:
	@echo "📋 Showing logs from all services..."
	@echo "   Press Ctrl+C to exit"
	@echo ""
	@if docker ps | grep -q codebase-rag-mcp-minimal; then \
		docker-compose -f docker/docker-compose.minimal.yml logs -f; \
	elif docker ps | grep -q codebase-rag-mcp-standard; then \
		docker-compose -f docker/docker-compose.standard.yml logs -f; \
	elif docker ps | grep -q codebase-rag-mcp-full; then \
		docker-compose -f docker/docker-compose.full.yml logs -f; \
	else \
		echo "❌ No services running. Start with: make docker-minimal"; \
	fi

# ============================================
# Development Mode
# ============================================

docker-compose.dev.yml:
	@echo "Creating dev compose file..."
	@echo "version: '3.8'" > docker/docker-compose.dev.yml
	@echo "services:" >> docker/docker-compose.dev.yml
	@echo "  mcp:" >> docker/docker-compose.dev.yml
	@echo "    volumes:" >> docker/docker-compose.dev.yml
	@echo "      - .:/app:delegated  # Mount source code" >> docker/docker-compose.dev.yml
	@echo "    environment:" >> docker/docker-compose.dev.yml
	@echo "      - DEBUG=true" >> docker/docker-compose.dev.yml
	@echo "      - PYTHONDONTWRITEBYTECODE=1" >> docker/docker-compose.dev.yml

dev-minimal: docker-compose.dev.yml
	@echo "🔧 Starting minimal in development mode..."
	docker-compose -f docker/docker-compose.minimal.yml -f docker/docker-compose.dev.yml up

dev-standard: docker-compose.dev.yml
	@echo "🔧 Starting standard in development mode..."
	docker-compose -f docker/docker-compose.standard.yml -f docker/docker-compose.dev.yml up

dev-full: docker-compose.dev.yml
	@echo "🔧 Starting full in development mode..."
	docker-compose -f docker/docker-compose.full.yml -f docker/docker-compose.dev.yml up

# ============================================
# Documentation Commands
# ============================================

docs-serve:
	@echo "📚 Serving documentation locally..."
	@if ! command -v mkdocs &> /dev/null; then \
		echo "❌ MkDocs not installed. Installing..."; \
		pip install mkdocs-material mkdocs-i18n; \
	fi
	mkdocs serve

docs-build:
	@echo "🔨 Building documentation..."
	@if ! command -v mkdocs &> /dev/null; then \
		echo "❌ MkDocs not installed. Installing..."; \
		pip install mkdocs-material mkdocs-i18n; \
	fi
	mkdocs build

docs-deploy:
	@echo "🚀 Deploying documentation to vantagecraft.dev..."
	@echo "   Building documentation..."
	mkdocs build
	@echo "✅ Documentation built in site/ directory"
	@echo ""
	@echo "📝 Next steps for vantagecraft.dev deployment:"
	@echo "   1. Upload site/ contents to your web server"
	@echo "   2. Configure DNS: docs.vantagecraft.dev -> your server"
	@echo "   3. Set up SSL certificate (recommended: Let's Encrypt)"
	@echo ""
	@echo "   Or use GitHub Pages:"
	@echo "   - mkdocs gh-deploy"

# ============================================
# Utility Commands
# ============================================

health-check:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "Neo4j:"
	@curl -s http://localhost:7474 > /dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "API:"
	@curl -s http://localhost:8000/api/v1/health > /dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
	@if docker ps | grep -q ollama; then \
		echo "Ollama:"; \
		curl -s http://localhost:11434/api/tags > /dev/null && echo "  ✅ Running" || echo "  ❌ Not running"; \
	fi

init-env:
	@echo "📝 Initializing environment file..."
	@echo "Which deployment mode? [minimal/standard/full]"
	@read mode; \
	if [ "$$mode" = "minimal" ]; then \
		cp docker/.env.template/.env.minimal .env; \
		echo "✅ Created .env for minimal deployment"; \
	elif [ "$$mode" = "standard" ]; then \
		cp docker/.env.template/.env.standard .env; \
		echo "✅ Created .env for standard deployment"; \
		echo "⚠️  Don't forget to configure EMBEDDING_PROVIDER"; \
	elif [ "$$mode" = "full" ]; then \
		cp docker/.env.template/.env.full .env; \
		echo "✅ Created .env for full deployment"; \
		echo "⚠️  Don't forget to configure LLM_PROVIDER and EMBEDDING_PROVIDER"; \
	else \
		echo "❌ Invalid mode. Choose: minimal, standard, or full"; \
	fi
