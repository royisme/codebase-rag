"""
Main FastAPI application for codebase-rag v0.2+
Minimal viable API with 3 endpoints:
- POST /ingest/repo
- GET /graph/related
- GET /context/pack
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.config import settings
from backend.app.routers import ingest, graph, context


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Codebase RAG API",
        description="Code knowledge graph and RAG system (v0.2)",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(ingest.router, prefix="/api/v1")
    app.include_router(graph.router, prefix="/api/v1")
    app.include_router(context.router, prefix="/api/v1")
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "Codebase RAG API",
            "version": "0.2.0",
            "endpoints": {
                "ingest": "/api/v1/ingest/repo",
                "related": "/api/v1/graph/related",
                "context_pack": "/api/v1/context/pack",
                "docs": "/docs"
            }
        }
    
    @app.get("/api/v1/health")
    async def health():
        """Health check endpoint"""
        from backend.app.services.graph.neo4j_service import get_neo4j_service
        
        try:
            neo4j = get_neo4j_service()
            neo4j_status = "connected" if neo4j._connected else "disconnected"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            neo4j_status = "error"
        
        return {
            "status": "healthy" if neo4j_status == "connected" else "degraded",
            "services": {
                "neo4j": neo4j_status
            },
            "version": "0.2.0"
        }
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        logger.info("Starting Codebase RAG API v0.2")
        
        # Initialize Neo4j connection
        from backend.app.services.graph.neo4j_service import get_neo4j_service
        neo4j = get_neo4j_service()
        
        if neo4j._connected:
            logger.info("Neo4j connection established")
        else:
            logger.warning("Failed to connect to Neo4j")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Shutting down Codebase RAG API")
        
        from backend.app.services.graph.neo4j_service import neo4j_service
        if neo4j_service:
            neo4j_service.close()
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
