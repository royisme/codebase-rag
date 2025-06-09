"""
Route configuration module
"""

from fastapi import FastAPI

from api.routes import router
from api.neo4j_routes import router as neo4j_router
from api.task_routes import router as task_router
from api.websocket_routes import router as ws_router


def setup_routes(app: FastAPI) -> None:
    """set application routes"""
    
    # include all API routes
    app.include_router(router, prefix="/api/v1", tags=["General"])
    app.include_router(neo4j_router, prefix="/api/v1", tags=["Neo4j Knowledge"])
    app.include_router(task_router, prefix="/api/v1", tags=["Task Management"])
 