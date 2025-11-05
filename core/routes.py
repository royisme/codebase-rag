"""
Route configuration module
"""

from fastapi import FastAPI

from api.routes import router
from api.auth import router as auth_router
from api.neo4j_routes import router as neo4j_router
from api.task_routes import router as task_router
from api.websocket_routes import router as ws_router
from api.sse_routes import router as sse_router
from api.admin_routes import router as admin_router
from api.knowledge_routes import router as knowledge_router
from api.dashboard import router as dashboard_router
from api.knowledge_notes import router as knowledge_notes_router


def setup_routes(app: FastAPI) -> None:
    """set application routes"""

    # include all API routes
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(router, prefix="/api/v1", tags=["General"])
    app.include_router(admin_router)  # admin routes already have prefix
    app.include_router(knowledge_router)  # knowledge routes already have prefix
    app.include_router(dashboard_router)
    app.include_router(knowledge_notes_router)
    app.include_router(neo4j_router, prefix="/api/v1", tags=["Neo4j Knowledge"])
    app.include_router(task_router, prefix="/api/v1", tags=["Task Management"])
    app.include_router(sse_router, prefix="/api/v1", tags=["Real-time Updates"])
    app.include_router(ws_router, prefix="/api/v1", tags=["WebSocket"])
 
