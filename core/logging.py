"""
日志配置模块
"""

import sys
from loguru import logger

from config import settings


def setup_logging():
    """配置日志系统"""
    
    # 移除默认的日志处理器
    logger.remove()
    
    # 添加控制台日志处理器
    logger.add(
        sys.stderr,
        level="INFO" if not settings.debug else "DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 添加文件日志处理器（如果需要）
    if hasattr(settings, 'log_file') and settings.log_file:
        logger.add(
            settings.log_file,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="30 days",
            compression="zip"
        ) 