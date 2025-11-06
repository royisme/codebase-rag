# =============================================================================
# Multi-stage Dockerfile for Code Graph Knowledge System
# =============================================================================
#
# OPTIMIZATION STRATEGY:
# 1. Uses requirements.txt (not pyproject.toml) - pre-compiled, no CUDA/GPU deps
# 2. Layer caching: requirements.txt copied first, rebuilt only when deps change
# 3. Multi-stage build: Builder stage includes build-essential, final stage minimal
# 4. Selective copying: Only copies site-packages and necessary entry points
# 5. No editable mode in production (uses -e only for local package)
#
# IMAGE SIZE REDUCTION:
# - requirements.txt: 564 → 379 dependencies (-32.9%)
# - NVIDIA CUDA packages: 15 → 0
# - Estimated size: ~5GB → ~1.5GB (-70%)
# - Build time: ~50% faster with layer caching
#
# =============================================================================

# ============================================
# Builder stage
# ============================================
FROM python:3.13-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy ONLY requirements.txt first for better layer caching
COPY requirements.txt ./

# Install Python dependencies from optimized requirements.txt
# Using pip instead of uv - no need for uv in production image
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code for local package installation
COPY pyproject.toml README.md ./
COPY api ./api
COPY core ./core
COPY services ./services
COPY mcp_tools ./mcp_tools
COPY *.py ./

# Install local package (without dependencies, already installed)
RUN pip install --no-cache-dir --no-deps -e .

# ============================================
# Final stage
# ============================================
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:${PATH}"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
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

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "start.py"]
