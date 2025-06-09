"""
FastAPI应用配置模块
负责创建和配置FastAPI应用实例
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
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title=settings.app_name,
        description="基于FastAPI的代码知识图谱服务，集成SQL解析、向量检索、图查询和RAG功能",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # 设置中间件
    setup_middleware(app)
    
    # 设置异常处理器
    setup_exception_handlers(app)
    
    # 设置路由
    setup_routes(app)
    
    # 静态文件服务
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # 根路径
    @app.get("/")
    async def root():
        """根路径接口"""
        return {
            "message": "Welcome to Code Graph Knowledge Service",
            "version": settings.app_version,
            "docs": "/docs" if settings.debug else "Documentation disabled in production",
            "health": "/api/v1/health",
            "task_monitor": "/static/index.html"
        }
    
    # 系统信息接口
    @app.get("/info")
    async def system_info():
        """系统信息接口"""
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