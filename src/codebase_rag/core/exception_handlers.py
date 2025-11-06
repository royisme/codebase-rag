"""
Exception handler module
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from src.codebase_rag.config import settings


def setup_exception_handlers(app: FastAPI) -> None:
    """set exception handler"""
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """global exception handler"""
        logger.error(f"Global exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc) if settings.debug else "An unexpected error occurred"
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """HTTP exception handler"""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "message": exc.detail
            }
        ) 