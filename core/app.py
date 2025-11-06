"""
FastAPI application configuration module
Responsible for creating and configuring FastAPI application instance
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from loguru import logger
import os

from config import settings
from .exception_handlers import setup_exception_handlers
from .middleware import setup_middleware
from .routes import setup_routes
from .lifespan import lifespan


def create_app() -> FastAPI:
    """create FastAPI application instance"""
    
    app = FastAPI(
        title=settings.app_name,
        description="Code Graph Knowledge Service based on FastAPI, integrated SQL parsing, vector search, graph query and RAG functionality",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # set middleware
    setup_middleware(app)
    
    # set exception handler
    setup_exception_handlers(app)
    
    # set routes
    setup_routes(app)

    # Check if static directory exists (contains built React frontend)
    static_dir = "static"
    if os.path.exists(static_dir) and os.path.exists(os.path.join(static_dir, "index.html")):
        # Mount static assets (JS, CSS, images, etc.)
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

        # SPA fallback - serve index.html for all non-API routes
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            """Serve React SPA with fallback to index.html for client-side routing"""
            # API routes are handled by routers, so we only get here for unmatched routes
            # Check if this looks like an API call that wasn't found
            if full_path.startswith("api/"):
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Not Found"}
                )

            # For all other routes, serve the React SPA
            index_path = os.path.join(static_dir, "index.html")
            return FileResponse(index_path)

        logger.info("React frontend enabled - serving SPA from /static")
        logger.info("Task monitoring available at /tasks")
    else:
        logger.warning("Static directory not found - React frontend not available")
        logger.warning("Run 'cd frontend && npm run build' and copy dist/* to static/")

        # Fallback root endpoint when frontend is not built
        @app.get("/")
        async def root():
            """root path interface"""
            return {
                "message": "Welcome to Code Graph Knowledge Service",
                "version": settings.app_version,
                "docs": "/docs" if settings.debug else "Documentation disabled in production",
                "health": "/api/v1/health",
                "note": "React frontend not built - see logs for instructions"
            }
    
    # system information interface
    @app.get("/info")
    async def system_info():
        """system information interface"""
        import sys
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "python_version": sys.version,
            "debug_mode": settings.debug,
            "services": {
                "neo4j": {
                    "uri": settings.neo4j_uri,
                    "database": settings.neo4j_database,
                    "vector_index": settings.vector_index_name,
                    "vector_dimension": settings.vector_dimension
                },
                "ollama": {
                    "base_url": settings.ollama_base_url,
                    "llm_model": settings.ollama_model,
                    "embedding_model": settings.ollama_embedding_model
                }
            }
        }
    
    return app 