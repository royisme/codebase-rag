"""
主应用入口文件
"""

import uvicorn
from loguru import logger

from config import settings
from core.app import create_app
from core.logging import setup_logging

# 配置日志
setup_logging()

# 创建FastAPI应用
app = create_app()

# 启动函数
def start_server():
    """启动服务器"""
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=settings.debug
    )

if __name__ == "__main__":
    start_server() 