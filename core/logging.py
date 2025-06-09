"""
Logging configuration module
"""

import sys
from loguru import logger

from config import settings


def setup_logging():
    """configure logging system"""
    
    # remove default log handler
    logger.remove()
    
    # add console log handler
    logger.add(
        sys.stderr,
        level="INFO" if not settings.debug else "DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # add file log handler (if needed)
    if hasattr(settings, 'log_file') and settings.log_file:
        logger.add(
            settings.log_file,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="30 days",
            compression="zip"
        ) 