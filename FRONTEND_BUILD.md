# Frontend Build Strategy

## Philosophy

**Frontend is static files** - after compilation, it's just HTML/CSS/JS that doesn't need Node.js/npm/bun to run. Therefore:

1. ✅ **Pre-build frontend outside Docker** - faster, cleaner
2. ✅ **Only include compiled `dist/` in image** - no source code, no package.json
3. ✅ **No Node.js/npm/bun in final image** - saves ~200MB
4. ✅ **FastAPI serves static files** - no additional web server needed

## Build Process

### Quick Start

```bash
# 1. Build frontend with bun
./build-frontend.sh

# 2. Build Docker image (includes frontend)
docker build -t codebase-rag .

# Or use docker-compose
docker-compose build
```

### Detailed Steps

#### 1. Install Bun (if not installed)

```bash
curl -fsSL https://bun.sh/install | bash
```

Required version: **Bun >= 1.3.1**

#### 2. Build Frontend

```bash
# Standard build
./build-frontend.sh

# Clean build (removes node_modules and dist first)
./build-frontend.sh --clean
```

**What it does:**
- Installs dependencies with `bun install --frozen-lockfile`
- Runs TypeScript type check (`tsc -b`)
- Runs linters (oxlint + eslint)
- Builds for production (`bun run build`)
- Outputs to `frontend/dist/`

**Build output:**
```
frontend/dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── ...
└── ...
```

#### 3. Build Docker Image

```bash
# With BuildKit (recommended)
DOCKER_BUILDKIT=1 docker build -t codebase-rag .
```

**What happens:**
- Dockerfile checks if `frontend/dist/` exists
- If yes: copies `frontend/dist/*` to `/app/static/`
- If no: builds API-only image (no web UI)

## What's Excluded from Docker Image

Thanks to `.dockerignore`, the following are **NOT** copied to the image:

### Frontend Source & Config (Not Needed)
- ❌ `frontend/src/` - Source code
- ❌ `frontend/public/` - Source assets
- ❌ `frontend/package.json` - Dependencies manifest
- ❌ `frontend/*.config.*` - Build configs (vite, eslint, tsconfig)
- ❌ `frontend/node_modules/` - Dependencies
- ❌ `frontend/bun.lockb` - Lock file

### Only Compiled Output (Included)
- ✅ `frontend/dist/` - Compiled static files

## Image Size Comparison

| Approach | Image Size | Node.js | Build Tools |
|----------|-----------|---------|-------------|
| **Build in Docker** | ~1.5GB | ✅ Included | ✅ Included |
| **Pre-build (current)** | ~1.2GB | ❌ Not needed | ❌ Not needed |
| **Savings** | **-300MB** | **-200MB** | **-100MB** |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Install bun
      - uses: oven-sh/setup-bun@v1
        with:
          bun-version: 1.3.1

      # Build frontend
      - name: Build Frontend
        run: ./build-frontend.sh

      # Build Docker image (includes pre-built frontend)
      - name: Build Docker Image
        run: docker build -t codebase-rag .

      # Push to registry
      - name: Push to Registry
        run: docker push codebase-rag
```

### GitLab CI Example

```yaml
build:
  image: oven/bun:1.3.1
  stage: build
  script:
    - ./build-frontend.sh
    - docker build -t codebase-rag .
    - docker push codebase-rag
```

## Development Workflow

### Local Development (with HMR)

```bash
cd frontend
bun install
bun run dev  # Starts dev server at http://localhost:5173
```

**Features:**
- Hot Module Replacement (HMR)
- Fast refresh
- Source maps
- Vite proxy to backend API

### Production Build Testing

```bash
# Build frontend
./build-frontend.sh

# Run backend (serves static files)
python start.py

# Access at http://localhost:8000
```

## API-Only Mode (No Frontend)

If you don't need the web UI, you can skip building frontend:

```bash
# Build Docker image without frontend
docker build -t codebase-rag .
```

**What you get:**
- ✅ Full REST API at `/api/v1/*`
- ✅ Prometheus metrics at `/metrics`
- ✅ Health check at `/api/v1/health`
- ❌ No web UI at `/`

## Troubleshooting

### Error: "bun: command not found"

```bash
# Install bun
curl -fsSL https://bun.sh/install | bash

# Restart shell or source .bashrc/.zshrc
source ~/.bashrc
```

### Error: "frontend/dist not found"

You need to build frontend before Docker build:

```bash
./build-frontend.sh
docker build -t codebase-rag .
```

### Docker image has no web UI

Check if frontend was built:

```bash
ls frontend/dist/index.html

# If not found, build it:
./build-frontend.sh
```

### "Cannot find module" errors in frontend

```bash
# Clean rebuild
./build-frontend.sh --clean
```

## Architecture

### Development Mode

```
┌─────────────────────────────────────────────────────────────┐
│                     Development                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Frontend (Vite dev server)                                  │
│  http://localhost:3000                                       │
│         │                                                    │
│         │ API Request: /api/v1/health                        │
│         ↓                                                    │
│  Vite Proxy (vite.config.ts)                                │
│         │                                                    │
│         │ Forward to: http://localhost:8000/api/v1/health   │
│         ↓                                                    │
│  Backend (FastAPI)                                           │
│  http://localhost:8000                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Development workflow:**
- Run backend: `python start.py` → `http://localhost:8000`
- Run frontend: `cd frontend && bun run dev` → `http://localhost:3000`
- Frontend proxies API requests to backend (configured in vite.config.ts)
- Hot reload for frontend changes
- Fast iteration, full debugging

### Production Mode (Docker)

```
┌─────────────────────────────────────────────────────────────┐
│                     Production (Docker)                      │
│               http://localhost:8000                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│           FastAPI Server (uvicorn)                           │
│                    Single Port: 8000                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Request Router (core/app.py)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ├─ /api/v1/*    → FastAPI REST API               │
│           │                  (JSON responses)                │
│           │                                                  │
│           ├─ /metrics      → Prometheus metrics             │
│           │                  (text/plain)                    │
│           │                                                  │
│           ├─ /assets/*     → Static files                   │
│           │                  (JS/CSS from /app/static/assets)│
│           │                                                  │
│           └─ /*, /tasks    → React SPA                      │
│                              (index.html with client routing)│
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /app/static/ (from frontend/dist/)                  │   │
│  │    ├── index.html                                    │   │
│  │    └── assets/                                       │   │
│  │         ├── index-abc123.js                          │   │
│  │         ├── index-abc123.css                         │   │
│  │         └── ...                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Production workflow:**
1. Build frontend: `./build-frontend.sh` → `frontend/dist/`
2. Build Docker: `docker build .` → copies `dist/` to `/app/static/`
3. Run container: `docker run -p 8000:8000 codebase-rag`
4. Access web UI: `http://localhost:8000`
5. API available at: `http://localhost:8000/api/v1/*`

### Routing Details

| URL | Handler | Response | Description |
|-----|---------|----------|-------------|
| `http://localhost:8000/` | React SPA | HTML | Main page (index.html) |
| `http://localhost:8000/tasks` | React SPA | HTML | Tasks page (client-side route) |
| `http://localhost:8000/assets/index-*.js` | StaticFiles | JS | Compiled JavaScript |
| `http://localhost:8000/assets/index-*.css` | StaticFiles | CSS | Compiled CSS |
| `http://localhost:8000/api/v1/health` | FastAPI | JSON | Health check API |
| `http://localhost:8000/api/v1/tasks` | FastAPI | JSON | Tasks API |
| `http://localhost:8000/metrics` | FastAPI | Text | Prometheus metrics |
| `http://localhost:8000/docs` | FastAPI | HTML | Swagger UI (debug mode) |

### API Communication (frontend → backend)

**Frontend code** (src/lib/api.ts):
```typescript
const api = axios.create({
  baseURL: '/api/v1',  // ✅ Relative path - works in both dev and prod
  timeout: 30000,
})

// Example API call
const response = await api.get('/health')
// → GET http://localhost:8000/api/v1/health (in production)
```

**Why relative paths work:**
- **Development**: Vite proxy forwards `/api` → `http://localhost:8000`
- **Production**: Same origin (both served from `http://localhost:8000`)
- **No CORS issues**: Same origin, no cross-origin requests
- **No hardcoded URLs**: Works in any environment

## Why This Approach?

### ✅ Advantages

1. **Smaller images** - No Node.js/npm/bun runtime (~200MB saved)
2. **Faster builds** - No npm install in Docker (parallel builds possible)
3. **Cleaner separation** - Build-time vs runtime dependencies
4. **CI/CD friendly** - Can cache frontend build separately
5. **No source code in image** - Only compiled artifacts
6. **Single server** - FastAPI serves both API and frontend

### ❌ Avoided Problems

1. **Multi-stage bloat** - No need for node:20 base image
2. **Build time** - No waiting for npm install during Docker build
3. **Security** - No package.json/node_modules in production image
4. **Complexity** - No need to manage Node.js version in Dockerfile

## Comparison with Alternatives

### Alternative 1: Build in Docker (multi-stage)

```dockerfile
# ❌ Slower and larger
FROM oven/bun:1.3.1-slim as frontend-builder
COPY frontend/ /frontend
RUN bun install && bun run build

FROM python:3.13-slim
COPY --from=frontend-builder /frontend/dist ./static
```

**Problems:**
- Longer build time (sequential)
- Can't cache frontend build separately
- Pulls bun image (~150MB base)

### Alternative 2: Separate nginx container

```dockerfile
# ❌ More complex
services:
  nginx:  # Serve frontend
    image: nginx:alpine
    volumes:
      - ./frontend/dist:/usr/share/nginx/html

  backend:  # API only
    image: codebase-rag
```

**Problems:**
- Need nginx configuration
- More containers to manage
- CORS configuration needed
- More complex deployment

### Our Approach: Pre-build + FastAPI serves

```bash
# ✅ Simple and fast
./build-frontend.sh  # Once, locally or in CI
docker build .       # Fast, frontend already built
```

**Advantages:**
- Single container
- Simple deployment
- Fast builds
- Small image

## Summary

**Golden Rule:** Frontend is just static files after build. Don't include build tools in production images.

**Best Practice:**
1. Build frontend with bun **before** Docker build
2. Include only `frontend/dist/` in image
3. Let FastAPI serve static files
4. No Node.js/npm/bun in production image
