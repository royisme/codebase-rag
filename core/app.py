"""
FastAPI application configuration module
Responsible for creating and configuring FastAPI application instance
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from loguru import logger

from config import settings
from services.embedding_utils import effective_vector_dimension
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
    
    # conditionally enable NiceGUI monitoring interface
    if settings.enable_monitoring:
        try:
            from nicegui import ui
            from monitoring.task_monitor import setup_monitoring_routes
            
            # setup NiceGUI monitoring routes
            setup_monitoring_routes()
            
            # integrate NiceGUI with FastAPI
            ui.run_with(app, mount_path=settings.monitoring_path)
            
            logger.info(f"Monitoring interface enabled at {settings.monitoring_path}/monitor")
            
        except ImportError as e:
            logger.warning(f"NiceGUI not available, monitoring interface disabled: {e}")
        except Exception as e:
            logger.error(f"Failed to setup monitoring interface: {e}")
    else:
        logger.info("Monitoring interface disabled by configuration")
    
    # root path
    @app.get("/")
    async def root():
        """root path interface"""
        response_data = {
            "message": "Welcome to Code Graph Knowledge Service",
            "version": settings.app_version,
            "docs": "/docs" if settings.debug else "Documentation disabled in production",
            "health": "/api/v1/health"
        }
        
        # conditionally add monitoring URL
        if settings.enable_monitoring:
            response_data["task_monitor"] = f"{settings.monitoring_path}/monitor"
        
        return response_data
    
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
            "monitoring_enabled": settings.enable_monitoring,
            "services": {
                "neo4j": {
                    "uri": settings.neo4j_uri,
                    "database": settings.neo4j_database,
                    "vector_index": settings.vector_index_name,
                    "vector_dimension": effective_vector_dimension(settings.vector_dimension)
                },
                "ollama": {
                    "base_url": settings.ollama_base_url,
                    "llm_model": settings.ollama_model,
                    "embedding_model": settings.ollama_embedding_model
                }
            }
        }
    
    return app 
