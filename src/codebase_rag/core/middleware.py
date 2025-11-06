"""
Middleware configuration module
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.codebase_rag.config import settings


def setup_middleware(app: FastAPI) -> None:
    """set application middleware"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Gzip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000) 