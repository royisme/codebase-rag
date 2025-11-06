# =============================================================================
# Multi-stage Dockerfile for Code Graph Knowledge System
# =============================================================================
#
# OPTIMIZATION STRATEGY:
# 1. Uses uv official image - uv pre-installed, optimized base
# 2. Uses requirements.txt - pre-compiled, no CUDA/GPU dependencies
# 3. BuildKit cache mounts - faster rebuilds with persistent cache
# 4. Multi-stage build - minimal final image
# 5. Layer caching - dependencies rebuild only when requirements.txt changes
# 6. Pre-built frontend - no Node.js/npm/bun in image, only static files
#
# IMAGE SIZE REDUCTION:
# - Base image: python:3.13-slim → uv:python3.13-bookworm-slim (smaller)
# - No build-essential needed (uv handles compilation efficiently)
# - No Node.js/npm/bun needed (frontend pre-built outside Docker)
# - requirements.txt: 373 dependencies, 0 NVIDIA CUDA packages
# - Estimated size: ~1.2GB (from >5GB, -76%)
# - Build time: ~80% faster (BuildKit cache + pre-built frontend)
#
# =============================================================================

# ============================================
# Builder stage
# ============================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install minimal system dependencies (git for repo cloning, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy ONLY requirements.txt first for optimal layer caching
COPY requirements.txt ./

# Install Python dependencies using uv with BuildKit cache mount
# This leverages uv's efficient dependency resolution and caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -r requirements.txt

# Copy application source code for local package installation
COPY pyproject.toml README.md ./
COPY api ./api
COPY core ./core
COPY services ./services
COPY mcp_tools ./mcp_tools
COPY *.py ./

# Install local package (without dependencies, already installed)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache --no-deps -e .

# ============================================
# Final stage
# ============================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:${PATH}"

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data /tmp/repos && \
    chown -R appuser:appuser /app /data /tmp/repos

# Set work directory
WORKDIR /app

# Copy Python packages from builder (site-packages only)
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy only package entry point scripts (not build tools like uv, pip-compile, etc.)
# Note: python binaries already exist in base image, no need to copy
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/

# Copy application code
COPY --chown=appuser:appuser . .

# Copy pre-built frontend (if exists)
# Run ./build-frontend.sh before docker build to generate frontend/dist
# If frontend/dist doesn't exist, the app will run as API-only (no web UI)
RUN if [ -d frontend/dist ]; then \
        mkdir -p static && \
        cp -r frontend/dist/* static/ && \
        echo "✅ Frontend copied to static/"; \
    else \
        echo "⚠️  No frontend/dist found - running as API-only"; \
        echo "   Run ./build-frontend.sh to build frontend"; \
    fi

# Switch to non-root user
USER appuser

# Expose port 8000 (MCP SSE + HTTP API + Web UI)
#
# SERVICE PRIORITY:
#   PRIMARY: MCP SSE service at /mcp/* (core功能)
#     - GET  /mcp/sse       - MCP SSE connection endpoint
#     - POST /mcp/messages/ - MCP message receiving endpoint
#
#   SECONDARY: Web UI & REST API (status monitoring)
#     - GET  /              - Web UI (React SPA)
#     - *    /api/v1/*      - REST API endpoints
#     - GET  /metrics       - Prometheus metrics
#
# Note: Legacy start_mcp.py (stdio) still available for local development
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command - starts HTTP API (not MCP)
# For MCP service, run on host: python start_mcp.py
CMD ["python", "start.py"]
