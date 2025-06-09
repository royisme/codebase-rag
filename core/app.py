"""
FastAPI application configuration module
Responsible for creating and configuring FastAPI application instance
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

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
    
    # static file service
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # root path
    @app.get("/")
    async def root():
        """root path interface"""
        return {
            "message": "Welcome to Code Graph Knowledge Service",
            "version": settings.app_version,
            "docs": "/docs" if settings.debug else "Documentation disabled in production",
            "health": "/api/v1/health",
            "task_monitor": "/static/index.html"
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
                    "embedding_model": settings.embedding_model
                }
            }
        }
    
    return app 