"""
中间件配置模块
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import settings


def setup_middleware(app: FastAPI) -> None:
    """设置应用中间件"""
    
    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Gzip压缩中间件
    app.add_middleware(GZipMiddleware, minimum_size=1000) 