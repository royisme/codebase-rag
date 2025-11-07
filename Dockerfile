# =============================================================================
# Dockerfile for Code Graph Knowledge System (Development/Local Use)
# =============================================================================
#
# NOTE: For production deployments, use the optimized variants:
#   - docker/Dockerfile.minimal  - Code Graph only (No LLM required)
#   - docker/Dockerfile.standard - Code Graph + Memory Store (Embedding required)
#   - docker/Dockerfile.full     - All features (LLM + Embedding required)
#
# This Dockerfile is for local development and testing.
#
# OPTIMIZATION STRATEGY:
# 1. Uses uv official image - uv pre-installed, optimized base (~150MB)
# 2. Uses requirements.txt - 118 dependencies (no CUDA/PyTorch)
# 3. BuildKit cache mounts - faster rebuilds with persistent cache
# 4. Multi-stage build - minimal final image (~500-700MB total)
# 5. Layer caching - dependencies rebuild only when requirements.txt changes
# 6. Pre-built frontend - no Node.js/npm/bun in image, only static files
#
# ARCHITECTURE:
# - Builder stage: Install Python dependencies only
# - Final stage: Runtime with git (for repo cloning) + curl (for health checks)
#
# =============================================================================

# ============================================
# Builder stage - Install dependencies only
# ============================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Copy requirements.txt for optimal layer caching
COPY requirements.txt ./

# Install Python dependencies using uv with BuildKit cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -r requirements.txt

# ============================================
# Final stage - Runtime environment
# ============================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:${PATH}"

# Install ONLY runtime dependencies (git for repo cloning, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data /repos && \
    chown -R appuser:appuser /app /data /repos

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/

# Copy application code (only src/)
COPY --chown=appuser:appuser src ./src

# Copy pre-built frontend (if exists)
# Run ./scripts/build-frontend.sh before docker build to generate frontend/dist
RUN if [ -d frontend/dist ]; then \
        cp -r frontend/dist ./static && \
        echo "✅ Frontend copied to static/"; \
    else \
        echo "⚠️  No frontend/dist found - running as API-only"; \
        echo "   Run ./scripts/build-frontend.sh to build frontend"; \
    fi

USER appuser

# Two-Port Architecture
#
# PORT 8000: MCP SSE Service (PRIMARY)
#   - GET  /sse       - MCP SSE connection endpoint
#   - POST /messages/ - MCP message receiving endpoint
#   Purpose: Core MCP service for AI clients
#
# PORT 8080: Web UI + REST API (SECONDARY)
#   - GET  /          - Web UI (React SPA for monitoring)
#   - *    /api/v1/*  - REST API endpoints
#   - GET  /metrics   - Prometheus metrics
#   Purpose: Status monitoring and programmatic access
EXPOSE 8000 8080

# Health check on Web UI port
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Start application (dual-port mode)
CMD ["python", "-m", "codebase_rag"]
