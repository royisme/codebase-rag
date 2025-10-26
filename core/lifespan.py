"""
Application lifecycle management module
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from database.session import check_database_connection
from database.init_db import init_database
from services.neo4j_knowledge_service import neo4j_knowledge_service
from services.task_queue import task_queue
from services.task_processors import processor_registry
from security.initialization import ensure_default_policies, ensure_default_superuser


@asynccontextmanager
async def lifespan(app: FastAPI):
    """application lifecycle management"""
    logger.info("Starting Code Graph Knowledge Service...")
    
    try:
        # initialize services
        await initialize_services()
        
        yield
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise
    finally:
        # clean up resources
        await cleanup_services()


async def initialize_services():
    """initialize all services"""

    # Initialize database tables first
    logger.info("Initializing database tables...")
    await init_database()
    logger.info("Database tables initialized")

    # 在其他服务启动前确认关系型数据库可用并初始化安全基线
    logger.info("Checking relational database connectivity...")
    await check_database_connection()
    logger.info("Database connection ready")

    superuser = await ensure_default_superuser()
    await ensure_default_policies(superuser_id=superuser.id if superuser else None)

    # initialize Neo4j knowledge graph service
    logger.info("Initializing Neo4j Knowledge Service...")
    try:
        if not await neo4j_knowledge_service.initialize():
            logger.warning("Failed to initialize Neo4j Knowledge Service - Neo4j features will be unavailable")
            logger.info("Application will continue without Neo4j knowledge graph functionality")
        else:
            logger.info("Neo4j Knowledge Service initialized successfully")
    except Exception as e:
        logger.warning(f"Neo4j initialization failed: {e}")
        logger.info("Application will continue without Neo4j knowledge graph functionality")
    
    # initialize task processors
    logger.info("Initializing Task Processors...")
    processor_registry.initialize_default_processors(neo4j_knowledge_service)
    logger.info("Task Processors initialized successfully")
    
    # initialize task queue
    logger.info("Initializing Task Queue...")
    await task_queue.start()
    logger.info("Task Queue initialized successfully")


async def cleanup_services():
    """clean up all services"""
    logger.info("Shutting down services...")
    
    try:
        # stop task queue
        await task_queue.stop()

        # close Neo4j service (if it was initialized)
        try:
            await neo4j_knowledge_service.close()
        except Exception as e:
            logger.warning(f"Error closing Neo4j service: {e}")

        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}") 
