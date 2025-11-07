"""
Application lifecycle management module
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from codebase_rag.services.knowledge import neo4j_knowledge_service
from codebase_rag.services.tasks import task_queue, processor_registry
from codebase_rag.services.memory import memory_store


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

    # initialize Neo4j knowledge graph service
    logger.info("Initializing Neo4j Knowledge Service...")
    if not await neo4j_knowledge_service.initialize():
        logger.error("Failed to initialize Neo4j Knowledge Service")
        raise RuntimeError("Neo4j service initialization failed")
    logger.info("Neo4j Knowledge Service initialized successfully")

    # initialize Memory Store
    logger.info("Initializing Memory Store...")
    if not await memory_store.initialize():
        logger.warning("Memory Store initialization failed - memory features may not work")
    else:
        logger.info("Memory Store initialized successfully")

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

        # close Memory Store
        await memory_store.close()

        # close Neo4j service
        await neo4j_knowledge_service.close()

        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}") 