"""
主应用入口文件
"""

import uvicorn
from loguru import logger

from config import settings
from core.app import create_app
from core.logging import setup_logging

# setup logging
setup_logging()

# create FastAPI app
app = create_app()

# start server
def start_server():
    """start server"""
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