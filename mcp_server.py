from fastmcp import FastMCP, Context
from typing import Dict, Any, Optional, List
import asyncio
import json
from loguru import logger

from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.task_queue import task_queue, TaskStatus, submit_document_processing_task, submit_directory_processing_task
from services.task_processors import processor_registry
from config import settings, get_current_model_info

# 初始化MCP服务器
mcp = FastMCP("Neo4j Knowledge Graph MCP Server")

# 初始化Neo4j知识库服务
knowledge_service = Neo4jKnowledgeService()

# 服务初始化状态
_service_initialized = False

async def ensure_service_initialized():
    """确保服务已初始化"""
    global _service_initialized
    if not _service_initialized:
        success = await knowledge_service.initialize()
        if success:
            _service_initialized = True
            # 启动任务队列
            await task_queue.start()
            # 初始化任务处理器
            processor_registry.initialize_default_processors(knowledge_service)
            logger.info("Neo4j Knowledge Service, Task Queue, and Processors initialized for MCP")
        else:
            raise Exception("Failed to initialize Neo4j Knowledge Service")

# MCP工具：通用知识查询
@mcp.tool
async def query_knowledge(
    question: str,
    mode: str = "hybrid",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Query the knowledge base with a question using Neo4j GraphRAG.
    
    Args:
        question: The question to ask the knowledge base
        mode: Query mode - "hybrid", "graph_only", or "vector_only" (default: hybrid)
    
    Returns:
        Dict containing the answer, sources, and metadata
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Querying Neo4j knowledge base: {question}")
        
        result = await knowledge_service.query(
            question=question,
            mode=mode
        )
        
        if ctx and result.get("success"):
            source_count = len(result.get('source_nodes', []))
            await ctx.info(f"Found answer with {source_count} source nodes")
        
        return result
        
    except Exception as e:
        error_msg = f"Knowledge query failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：搜索相似节点
@mcp.tool
async def search_similar_nodes(
    query: str,
    top_k: int = 10,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Search for similar nodes using vector similarity.
    
    Args:
        query: Search query text
        top_k: Number of top results to return (default: 10)
    
    Returns:
        Dict containing similar nodes and metadata
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Searching similar nodes: {query}")
        
        result = await knowledge_service.search_similar_nodes(
            query=query,
            top_k=top_k
        )
        
        if ctx and result.get("success"):
            await ctx.info(f"Found {result.get('total_count', 0)} similar nodes")
        
        return result
        
    except Exception as e:
        error_msg = f"Similar nodes search failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：添加文档（同步版本，小文档）
@mcp.tool
async def add_document(
    content: str,
    title: str = "Untitled",
    metadata: Optional[Dict[str, Any]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Add a document to the Neo4j knowledge graph (synchronous for small documents).
    
    Args:
        content: The document content
        title: Document title (default: "Untitled")
        metadata: Optional metadata dictionary
    
    Returns:
        Dict containing operation result and metadata
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Adding document: {title}")
        
        # 对于小文档（<10KB），直接同步处理
        if len(content) < 10240:
            result = await knowledge_service.add_document(
                content=content,
                title=title,
                metadata=metadata
            )
            
            if ctx and result.get("success"):
                content_size = result.get('content_size', 0)
                await ctx.info(f"Successfully added document ({content_size} characters)")
            
            return result
        else:
            # 大文档使用异步任务队列
            task_id = await submit_document_processing_task(
                knowledge_service.add_document,
                content=content,
                title=title,
                metadata=metadata,
                task_name=f"Add Document: {title}"
            )
            
            if ctx:
                await ctx.info(f"Large document queued for processing. Task ID: {task_id}")
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "Document queued for background processing",
                "content_size": len(content)
            }
        
    except Exception as e:
        error_msg = f"Add document failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：添加文件（异步任务）
@mcp.tool
async def add_file(
    file_path: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Add a file to the Neo4j knowledge graph (asynchronous task).
    
    Args:
        file_path: Path to the file to add
    
    Returns:
        Dict containing task ID and status
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Queuing file for processing: {file_path}")
        
        task_id = await submit_document_processing_task(
            knowledge_service.add_file,
            file_path,
            task_name=f"Add File: {file_path}"
        )
        
        if ctx:
            await ctx.info(f"File queued for processing. Task ID: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "File queued for background processing",
            "file_path": file_path
        }
        
    except Exception as e:
        error_msg = f"Add file failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：添加目录（异步任务）
@mcp.tool
async def add_directory(
    directory_path: str,
    recursive: bool = True,
    file_extensions: Optional[List[str]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Add all files from a directory to the Neo4j knowledge graph (asynchronous task).
    
    Args:
        directory_path: Path to the directory
        recursive: Whether to process subdirectories (default: True)
        file_extensions: List of file extensions to include (default: common text files)
    
    Returns:
        Dict containing task ID and status
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Queuing directory for processing: {directory_path}")
        
        task_id = await submit_directory_processing_task(
            knowledge_service.add_directory,
            directory_path,
            recursive=recursive,
            file_extensions=file_extensions,
            task_name=f"Add Directory: {directory_path}"
        )
        
        if ctx:
            await ctx.info(f"Directory queued for processing. Task ID: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Directory queued for background processing",
            "directory_path": directory_path,
            "recursive": recursive
        }
        
    except Exception as e:
        error_msg = f"Add directory failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：获取任务状态
@mcp.tool
async def get_task_status(
    task_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get the status of a background task.
    
    Args:
        task_id: The task ID to check
    
    Returns:
        Dict containing task status and details
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Checking task status: {task_id}")
        
        task_result = task_queue.get_task_status(task_id)
        
        if task_result is None:
            return {
                "success": False,
                "error": "Task not found"
            }
        
        return {
            "success": True,
            "task_id": task_result.task_id,
            "status": task_result.status.value,
            "progress": task_result.progress,
            "message": task_result.message,
            "created_at": task_result.created_at.isoformat(),
            "started_at": task_result.started_at.isoformat() if task_result.started_at else None,
            "completed_at": task_result.completed_at.isoformat() if task_result.completed_at else None,
            "result": task_result.result,
            "error": task_result.error,
            "metadata": task_result.metadata
        }
        
    except Exception as e:
        error_msg = f"Get task status failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：列出所有任务
@mcp.tool
async def list_tasks(
    status_filter: Optional[str] = None,
    limit: int = 20,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    List all tasks with optional status filtering.
    
    Args:
        status_filter: Filter by task status (pending, running, completed, failed, cancelled)
        limit: Maximum number of tasks to return (default: 20)
    
    Returns:
        Dict containing list of tasks
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Listing tasks (filter: {status_filter}, limit: {limit})")
        
        # 转换状态过滤器
        status_enum = None
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter.lower())
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid status filter: {status_filter}"
                }
        
        tasks = task_queue.get_all_tasks(status_filter=status_enum, limit=limit)
        
        # 转换为可序列化的格式
        task_list = []
        for task in tasks:
            task_list.append({
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress,
                "message": task.message,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "metadata": task.metadata
            })
        
        return {
            "success": True,
            "tasks": task_list,
            "total_count": len(task_list)
        }
        
    except Exception as e:
        error_msg = f"List tasks failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：取消任务
@mcp.tool
async def cancel_task(
    task_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Cancel a running or pending task.
    
    Args:
        task_id: The task ID to cancel
    
    Returns:
        Dict containing cancellation result
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Cancelling task: {task_id}")
        
        success = task_queue.cancel_task(task_id)
        
        if success:
            return {
                "success": True,
                "message": "Task cancelled successfully"
            }
        else:
            return {
                "success": False,
                "error": "Task not found or cannot be cancelled"
            }
        
    except Exception as e:
        error_msg = f"Cancel task failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：获取队列统计
@mcp.tool
async def get_queue_stats(ctx: Context = None) -> Dict[str, Any]:
    """
    Get task queue statistics.
    
    Returns:
        Dict containing queue statistics
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info("Getting queue statistics")
        
        stats = task_queue.get_queue_stats()
        
        return {
            "success": True,
            **stats
        }
        
    except Exception as e:
        error_msg = f"Get queue stats failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：获取图谱结构
@mcp.tool
async def get_graph_schema(ctx: Context = None) -> Dict[str, Any]:
    """
    Get the Neo4j knowledge graph schema information.
    
    Returns:
        Dict containing graph schema and structure information
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info("Retrieving graph schema")
        
        result = await knowledge_service.get_graph_schema()
        
        if ctx and result.get("success"):
            await ctx.info("Successfully retrieved graph schema")
        
        return result
        
    except Exception as e:
        error_msg = f"Get graph schema failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：获取统计信息
@mcp.tool
async def get_statistics(ctx: Context = None) -> Dict[str, Any]:
    """
    Get Neo4j knowledge graph statistics and health information.
    
    Returns:
        Dict containing comprehensive statistics about the knowledge graph
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info("Retrieving knowledge graph statistics")
        
        result = await knowledge_service.get_statistics()
        
        if ctx and result.get("success"):
            await ctx.info("Successfully retrieved statistics")
        
        return result
        
    except Exception as e:
        error_msg = f"Get statistics failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP工具：清空知识库
@mcp.tool
async def clear_knowledge_base(ctx: Context = None) -> Dict[str, Any]:
    """
    Clear the entire Neo4j knowledge base.
    
    Returns:
        Dict containing operation result
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info("Clearing knowledge base")
        
        result = await knowledge_service.clear_knowledge_base()
        
        if ctx and result.get("success"):
            await ctx.info("Successfully cleared knowledge base")
        
        return result
        
    except Exception as e:
        error_msg = f"Clear knowledge base failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP资源：知识库配置
@mcp.resource("knowledge://config")
async def get_knowledge_config() -> Dict[str, Any]:
    """Get knowledge base configuration and settings."""
    model_info = get_current_model_info()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "neo4j_uri": settings.neo4j_uri,
        "neo4j_database": settings.neo4j_database,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "current_models": model_info,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "top_k": settings.top_k,
        "vector_dimension": settings.vector_dimension,
        "timeouts": {
            "connection": settings.connection_timeout,
            "operation": settings.operation_timeout,
            "large_document": settings.large_document_timeout
        }
    }

# MCP资源：系统状态
@mcp.resource("knowledge://status")
async def get_system_status() -> Dict[str, Any]:
    """Get current system status and health."""
    try:
        await ensure_service_initialized()
        stats = await knowledge_service.get_statistics()
        model_info = get_current_model_info()
        
        return {
            "status": "healthy" if stats.get("success") else "degraded",
            "services": {
                "neo4j_knowledge_service": _service_initialized,
                "neo4j_connection": True,  # 如果能初始化说明连接正常
            },
            "current_models": model_info,
            "statistics": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "services": {
                "neo4j_knowledge_service": _service_initialized,
                "neo4j_connection": False,
            }
        }

# MCP资源：最近添加的文档
@mcp.resource("knowledge://recent-documents/{limit}")
async def get_recent_documents(limit: int = 10) -> Dict[str, Any]:
    """Get recently added documents."""
    try:
        await ensure_service_initialized()
        # 这里可以扩展为从图数据库查询最近添加的文档
        # 目前返回占位符信息
        return {
            "message": f"Recent {limit} documents endpoint",
            "note": "This feature can be extended to query Neo4j for recently added documents",
            "limit": limit,
            "implementation_status": "placeholder"
        }
    except Exception as e:
        return {
            "error": str(e)
        }

# MCP提示：生成查询建议
@mcp.prompt
def suggest_queries(domain: str = "general") -> str:
    """
    Generate suggested queries for the Neo4j knowledge graph.
    
    Args:
        domain: Domain to focus suggestions on (e.g., "code", "documentation", "sql", "architecture")
    """
    suggestions = {
        "general": [
            "What are the main components of this system?",
            "How does the Neo4j knowledge pipeline work?",
            "What databases and services are used in this project?",
            "Show me the overall architecture of the system"
        ],
        "code": [
            "Show me Python functions for data processing",
            "Find code examples for Neo4j integration",
            "What are the main classes in the pipeline module?",
            "How is the knowledge service implemented?"
        ],
        "documentation": [
            "What is the system architecture?",
            "How to set up the development environment?",
            "What are the API endpoints available?",
            "How to configure different LLM providers?"
        ],
        "sql": [
            "Show me table schemas for user management",
            "What are the relationships between database tables?",
            "Find SQL queries for reporting",
            "How is the database schema structured?"
        ],
        "architecture": [
            "What is the GraphRAG architecture?",
            "How does the vector search work with Neo4j?",
            "What are the different query modes available?",
            "How are documents processed and stored?"
        ]
    }
    
    domain_suggestions = suggestions.get(domain, suggestions["general"])
    
    return f"""Here are some suggested queries for the {domain} domain in the Neo4j Knowledge Graph:

{chr(10).join(f"• {suggestion}" for suggestion in domain_suggestions)}

Available query modes:
• hybrid: Combines graph traversal and vector search (recommended)
• graph_only: Uses only graph relationships
• vector_only: Uses only vector similarity search

You can use the query_knowledge tool with any of these questions or create your own queries."""

if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run() 