"""
应用生命周期管理模块
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from services.neo4j_knowledge_service import neo4j_knowledge_service
from services.task_queue import task_queue
from services.task_processors import processor_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting Code Graph Knowledge Service...")
    
    try:
        # 初始化服务
        await initialize_services()
        
        yield
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise
    finally:
        # 清理资源
        await cleanup_services()


async def initialize_services():
    """初始化所有服务"""
    
    # 初始化 Neo4j 知识图谱服务
    logger.info("Initializing Neo4j Knowledge Service...")
    if not await neo4j_knowledge_service.initialize():
        logger.error("Failed to initialize Neo4j Knowledge Service")
        raise RuntimeError("Neo4j service initialization failed")
    logger.info("Neo4j Knowledge Service initialized successfully")
    
    # 初始化任务处理器
    logger.info("Initializing Task Processors...")
    processor_registry.initialize_default_processors(neo4j_knowledge_service)
    logger.info("Task Processors initialized successfully")
    
    # 初始化任务队列
    logger.info("Initializing Task Queue...")
    await task_queue.start()
    logger.info("Task Queue initialized successfully")


async def cleanup_services():
    """清理所有服务"""
    logger.info("Shutting down services...")
    
    try:
        # 停止任务队列
        await task_queue.stop()
        
        # 关闭Neo4j服务
        await neo4j_knowledge_service.close()
        
        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}") 