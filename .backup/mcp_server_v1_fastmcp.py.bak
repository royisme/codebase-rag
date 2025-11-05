from fastmcp import FastMCP, Context
from typing import Dict, Any, Optional, List

from loguru import logger

from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.task_queue import task_queue, TaskStatus, submit_document_processing_task, submit_directory_processing_task
from services.task_processors import processor_registry
from services.graph_service import graph_service
from services.code_ingestor import get_code_ingestor
from services.ranker import ranker
from services.pack_builder import pack_builder
from services.git_utils import git_utils
from services.memory_store import memory_store
from config import settings, get_current_model_info
from datetime import datetime
import uuid

# initialize MCP server
mcp = FastMCP("Neo4j Knowledge Graph MCP Server")

# initialize Neo4j knowledge service
knowledge_service = Neo4jKnowledgeService()

# service initialization status
_service_initialized = False

async def ensure_service_initialized():
    """ensure service is initialized"""
    global _service_initialized
    if not _service_initialized:
        success = await knowledge_service.initialize()
        if success:
            # initialize memory store
            memory_success = await memory_store.initialize()
            if not memory_success:
                logger.warning("Memory Store initialization failed, continuing without memory features")

            _service_initialized = True
            # start task queue
            await task_queue.start()
            # initialize task processors
            processor_registry.initialize_default_processors(knowledge_service)
            logger.info("Neo4j Knowledge Service, Memory Store, Task Queue, and Processors initialized for MCP")
        else:
            raise Exception("Failed to initialize Neo4j Knowledge Service")

# MCP tool: query knowledge
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

# MCP tool: search similar nodes
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

# MCP tool: add document (synchronous version, small document)
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
        
        # for small documents (<10KB), process directly synchronously
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
            # for large documents (>=10KB), save to temporary file first
            import tempfile
            import os
            
            temp_fd, temp_path = tempfile.mkstemp(suffix=f"_{title.replace('/', '_')}.txt", text=True)
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                    temp_file.write(content)
                
                # use file path instead of content to avoid payload size issues
                task_id = await submit_document_processing_task(
                    knowledge_service.add_file,  # Use add_file instead of add_document
                    temp_path,
                    task_name=f"Add Large Document: {title}",
                    # Add metadata to track this is a temp file that should be cleaned up
                    _temp_file=True,
                    _original_title=title,
                    _original_metadata=metadata
                )
            except:
                # Clean up on error
                os.close(temp_fd)
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
            
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

# MCP tool: add file (asynchronous task)
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

# MCP tool: add directory (asynchronous task)
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

# MCP tool: get task status
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

# MCP tool: watch task (real-time task monitoring)
@mcp.tool
async def watch_task(
    task_id: str,
    timeout: int = 300,
    interval: float = 1.0,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Watch a task progress with real-time updates until completion.
    
    Args:
        task_id: The task ID to watch
        timeout: Maximum time to wait in seconds (default: 300)
        interval: Check interval in seconds (default: 1.0)
    
    Returns:
        Dict containing final task status and progress history
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Watching task: {task_id} (timeout: {timeout}s, interval: {interval}s)")
        
        import asyncio
        start_time = asyncio.get_event_loop().time()
        progress_history = []
        last_progress = -1
        last_status = None
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                return {
                    "success": False,
                    "error": "Watch timeout exceeded",
                    "progress_history": progress_history
                }
            
            task_result = task_queue.get_task_status(task_id)
            
            if task_result is None:
                return {
                    "success": False,
                    "error": "Task not found",
                    "progress_history": progress_history
                }
            
            # Record progress changes
            if (task_result.progress != last_progress or 
                task_result.status.value != last_status):
                
                progress_entry = {
                    "timestamp": asyncio.get_event_loop().time(),
                    "progress": task_result.progress,
                    "status": task_result.status.value,
                    "message": task_result.message
                }
                progress_history.append(progress_entry)
                
                # Send real-time updates to client
                if ctx:
                    await ctx.info(f"Progress: {task_result.progress:.1f}% - {task_result.message}")
                
                last_progress = task_result.progress
                last_status = task_result.status.value
            
            # Check if task is completed
            if task_result.status.value in ['success', 'failed', 'cancelled']:
                final_result = {
                    "success": True,
                    "task_id": task_result.task_id,
                    "final_status": task_result.status.value,
                    "final_progress": task_result.progress,
                    "final_message": task_result.message,
                    "created_at": task_result.created_at.isoformat(),
                    "started_at": task_result.started_at.isoformat() if task_result.started_at else None,
                    "completed_at": task_result.completed_at.isoformat() if task_result.completed_at else None,
                    "result": task_result.result,
                    "error": task_result.error,
                    "progress_history": progress_history,
                    "total_watch_time": current_time - start_time
                }
                
                if ctx:
                    if task_result.status.value == 'success':
                        await ctx.info(f"Task completed successfully in {current_time - start_time:.1f}s")
                    else:
                        await ctx.error(f"Task {task_result.status.value}: {task_result.error or task_result.message}")
                
                return final_result
            
            # Wait for next check
            await asyncio.sleep(interval)
            
    except Exception as e:
        error_msg = f"Watch task failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "progress_history": progress_history if 'progress_history' in locals() else []
        }

# MCP tool: watch multiple tasks (batch monitoring)
@mcp.tool
async def watch_tasks(
    task_ids: List[str],
    timeout: int = 300,
    interval: float = 2.0,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Watch multiple tasks progress with real-time updates until all complete.
    
    Args:
        task_ids: List of task IDs to watch
        timeout: Maximum time to wait in seconds (default: 300)
        interval: Check interval in seconds (default: 2.0)
    
    Returns:
        Dict containing all task statuses and progress histories
    """
    try:
        await ensure_service_initialized()
        
        if ctx:
            await ctx.info(f"Watching {len(task_ids)} tasks (timeout: {timeout}s, interval: {interval}s)")
        
        import asyncio
        start_time = asyncio.get_event_loop().time()
        tasks_progress = {task_id: [] for task_id in task_ids}
        completed_tasks = set()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                return {
                    "success": False,
                    "error": "Watch timeout exceeded",
                    "tasks_progress": tasks_progress,
                    "completed_tasks": list(completed_tasks),
                    "pending_tasks": list(set(task_ids) - completed_tasks)
                }
            
            # Check all tasks
            active_tasks = []
            for task_id in task_ids:
                if task_id in completed_tasks:
                    continue
                    
                task_result = task_queue.get_task_status(task_id)
                if task_result is None:
                    completed_tasks.add(task_id)
                    continue
                
                # Record progress
                progress_entry = {
                    "timestamp": current_time,
                    "progress": task_result.progress,
                    "status": task_result.status.value,
                    "message": task_result.message
                }
                
                # Only record changed progress
                if (not tasks_progress[task_id] or 
                    tasks_progress[task_id][-1]["progress"] != task_result.progress or
                    tasks_progress[task_id][-1]["status"] != task_result.status.value):
                    
                    tasks_progress[task_id].append(progress_entry)
                    
                    if ctx:
                        await ctx.info(f"Task {task_id}: {task_result.progress:.1f}% - {task_result.message}")
                
                # Check if completed
                if task_result.status.value in ['success', 'failed', 'cancelled']:
                    completed_tasks.add(task_id)
                    if ctx:
                        await ctx.info(f"Task {task_id} completed: {task_result.status.value}")
                else:
                    active_tasks.append(task_id)
            
            # All tasks completed
            if len(completed_tasks) == len(task_ids):
                final_results = {}
                for task_id in task_ids:
                    task_result = task_queue.get_task_status(task_id)
                    if task_result:
                        final_results[task_id] = {
                            "status": task_result.status.value,
                            "progress": task_result.progress,
                            "message": task_result.message,
                            "result": task_result.result,
                            "error": task_result.error
                        }
                
                if ctx:
                    success_count = sum(1 for task_id in task_ids 
                                     if task_queue.get_task_status(task_id) and 
                                     task_queue.get_task_status(task_id).status.value == 'success')
                    await ctx.info(f"All tasks completed! {success_count}/{len(task_ids)} successful")
                
                return {
                    "success": True,
                    "tasks_progress": tasks_progress,
                    "final_results": final_results,
                    "completed_tasks": list(completed_tasks),
                    "total_watch_time": current_time - start_time,
                    "summary": {
                        "total_tasks": len(task_ids),
                        "successful": sum(1 for r in final_results.values() if r["status"] == "success"),
                        "failed": sum(1 for r in final_results.values() if r["status"] == "failed"),
                        "cancelled": sum(1 for r in final_results.values() if r["status"] == "cancelled")
                    }
                }
            
            # Wait for next check
            await asyncio.sleep(interval)
            
    except Exception as e:
        error_msg = f"Watch tasks failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "tasks_progress": tasks_progress if 'tasks_progress' in locals() else {}
        }

# MCP tool: list all tasks
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
        
        # convert status filter
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
        
        # convert to serializable format
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

# MCP tool: cancel task
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

# MCP tool: get queue statistics
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

# MCP tool: get graph schema
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

# MCP tool: get statistics
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

# MCP tool: clear knowledge base
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

# ===================================
# Code Graph MCP Tools (v0.5)
# ===================================

# MCP tool: ingest repository
@mcp.tool
async def code_graph_ingest_repo(
    local_path: Optional[str] = None,
    repo_url: Optional[str] = None,
    branch: str = "main",
    mode: str = "full",
    include_globs: Optional[List[str]] = None,
    exclude_globs: Optional[List[str]] = None,
    since_commit: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Ingest a repository into the code knowledge graph.

    Args:
        local_path: Path to local repository
        repo_url: URL of repository to clone (if local_path not provided)
        branch: Git branch to use (default: "main")
        mode: Ingestion mode - "full" or "incremental" (default: "full")
        include_globs: File patterns to include (default: ["**/*.py", "**/*.ts", "**/*.tsx"])
        exclude_globs: File patterns to exclude (default: ["**/node_modules/**", "**/.git/**", "**/__pycache__/**"])
        since_commit: For incremental mode, compare against this commit

    Returns:
        Dict containing task_id, status, and processing info
    """
    try:
        await ensure_service_initialized()

        if not local_path and not repo_url:
            return {
                "success": False,
                "error": "Either local_path or repo_url must be provided"
            }

        if ctx:
            await ctx.info(f"Ingesting repository (mode: {mode})")

        # Set defaults
        if include_globs is None:
            include_globs = ["**/*.py", "**/*.ts", "**/*.tsx"]
        if exclude_globs is None:
            exclude_globs = ["**/node_modules/**", "**/.git/**", "**/__pycache__/**"]

        # Generate task ID
        task_id = f"ing-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        # Determine repository path and ID
        repo_path = None
        repo_id = None
        cleanup_needed = False

        if local_path:
            repo_path = local_path
            repo_id = git_utils.get_repo_id_from_path(repo_path)
        else:
            # Clone repository
            if ctx:
                await ctx.info(f"Cloning repository: {repo_url}")

            clone_result = git_utils.clone_repo(repo_url, branch=branch)

            if not clone_result.get("success"):
                return {
                    "success": False,
                    "task_id": task_id,
                    "status": "error",
                    "error": clone_result.get("error", "Failed to clone repository")
                }

            repo_path = clone_result["path"]
            repo_id = git_utils.get_repo_id_from_url(repo_url)
            cleanup_needed = True

        # Get code ingestor
        code_ingestor = get_code_ingestor(graph_service)

        # Handle incremental mode
        files_to_process = None
        changed_files_count = 0

        if mode == "incremental" and git_utils.is_git_repo(repo_path):
            if ctx:
                await ctx.info("Using incremental mode - detecting changed files")

            changed_files = git_utils.get_changed_files(
                repo_path,
                since_commit=since_commit,
                include_untracked=True
            )
            changed_files_count = len(changed_files)

            if changed_files_count == 0:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "done",
                    "message": "No changed files detected",
                    "mode": "incremental",
                    "files_processed": 0,
                    "changed_files_count": 0
                }

            # Filter changed files by globs
            files_to_process = [f["path"] for f in changed_files if f["action"] != "deleted"]

            if ctx:
                await ctx.info(f"Found {changed_files_count} changed files")

        # Scan files
        if ctx:
            await ctx.info(f"Scanning repository: {repo_path}")

        scanned_files = code_ingestor.scan_files(
            repo_path=repo_path,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
            specific_files=files_to_process
        )

        if not scanned_files:
            return {
                "success": True,
                "task_id": task_id,
                "status": "done",
                "message": "No files found matching criteria",
                "mode": mode,
                "files_processed": 0,
                "changed_files_count": changed_files_count if mode == "incremental" else None
            }

        # Ingest files
        if ctx:
            await ctx.info(f"Ingesting {len(scanned_files)} files...")

        result = code_ingestor.ingest_files(
            repo_id=repo_id,
            files=scanned_files
        )

        if ctx:
            if result.get("success"):
                await ctx.info(f"Successfully ingested {result.get('files_processed', 0)} files")
            else:
                await ctx.error(f"Ingestion failed: {result.get('error')}")

        return {
            "success": result.get("success", False),
            "task_id": task_id,
            "status": "done" if result.get("success") else "error",
            "message": result.get("message"),
            "files_processed": result.get("files_processed", 0),
            "mode": mode,
            "changed_files_count": changed_files_count if mode == "incremental" else None,
            "repo_id": repo_id,
            "repo_path": repo_path
        }

    except Exception as e:
        error_msg = f"Repository ingestion failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP tool: find related files
@mcp.tool
async def code_graph_related(
    query: str,
    repo_id: str,
    limit: int = 30,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Find related files using fulltext search and keyword matching.

    Args:
        query: Search query text
        repo_id: Repository ID to search in
        limit: Maximum number of results (default: 30, max: 100)

    Returns:
        Dict containing list of related files with ref:// handles
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Finding files related to: {query}")

        # Perform fulltext search
        search_results = graph_service.fulltext_search(
            query_text=query,
            repo_id=repo_id,
            limit=limit * 2  # Get more for ranking
        )

        if not search_results:
            if ctx:
                await ctx.info("No related files found")
            return {
                "success": True,
                "nodes": [],
                "query": query,
                "repo_id": repo_id
            }

        # Rank results
        ranked_files = ranker.rank_files(
            files=search_results,
            query=query,
            limit=limit
        )

        # Convert to node summaries
        nodes = []
        for file in ranked_files:
            summary = ranker.generate_file_summary(
                path=file["path"],
                lang=file["lang"]
            )

            ref = ranker.generate_ref_handle(path=file["path"])

            nodes.append({
                "type": "file",
                "ref": ref,
                "path": file["path"],
                "lang": file["lang"],
                "score": file["score"],
                "summary": summary
            })

        if ctx:
            await ctx.info(f"Found {len(nodes)} related files")

        return {
            "success": True,
            "nodes": nodes,
            "query": query,
            "repo_id": repo_id
        }

    except Exception as e:
        error_msg = f"Related files search failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP tool: impact analysis
@mcp.tool
async def code_graph_impact(
    repo_id: str,
    file_path: str,
    depth: int = 2,
    limit: int = 50,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Analyze the impact of a file by finding reverse dependencies.

    Finds files and symbols that depend on the specified file through:
    - CALLS relationships (who calls functions/methods in this file)
    - IMPORTS relationships (who imports this file)

    Args:
        repo_id: Repository ID
        file_path: Path to file to analyze
        depth: Traversal depth for dependencies (default: 2, max: 5)
        limit: Maximum number of results (default: 50, max: 100)

    Returns:
        Dict containing list of impacted files/symbols
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Analyzing impact of: {file_path}")

        # Perform impact analysis
        impact_results = graph_service.impact_analysis(
            repo_id=repo_id,
            file_path=file_path,
            depth=depth,
            limit=limit
        )

        if not impact_results:
            if ctx:
                await ctx.info("No reverse dependencies found")
            return {
                "success": True,
                "nodes": [],
                "file": file_path,
                "repo_id": repo_id,
                "depth": depth
            }

        # Convert to impact nodes
        nodes = []
        for result in impact_results:
            summary = ranker.generate_file_summary(
                path=result["path"],
                lang=result.get("lang", "unknown")
            )

            ref = ranker.generate_ref_handle(path=result["path"])

            nodes.append({
                "type": result.get("type", "file"),
                "path": result["path"],
                "lang": result.get("lang"),
                "repo_id": result.get("repoId", repo_id),
                "relationship": result.get("relationship", "unknown"),
                "depth": result.get("depth", 1),
                "score": result.get("score", 0.0),
                "ref": ref,
                "summary": summary
            })

        if ctx:
            await ctx.info(f"Found {len(nodes)} impacted files/symbols")

        return {
            "success": True,
            "nodes": nodes,
            "file": file_path,
            "repo_id": repo_id,
            "depth": depth
        }

    except Exception as e:
        error_msg = f"Impact analysis failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP tool: build context pack
@mcp.tool
async def context_pack(
    repo_id: str,
    stage: str = "plan",
    budget: int = 1500,
    keywords: Optional[str] = None,
    focus: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Build a context pack within token budget.

    Searches for relevant files and packages them with summaries and ref:// handles.

    Args:
        repo_id: Repository ID
        stage: Development stage - "plan", "review", or "implement" (default: "plan")
        budget: Token budget (default: 1500, max: 10000)
        keywords: Comma-separated keywords for search (optional)
        focus: Comma-separated focus file paths (optional)

    Returns:
        Dict containing context items within budget
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Building context pack (stage: {stage}, budget: {budget})")

        # Parse keywords
        keyword_list = []
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

        # Parse focus paths
        focus_list = []
        if focus:
            focus_list = [f.strip() for f in focus.split(",") if f.strip()]

        # Search for relevant files
        all_nodes = []

        # Search by keywords
        if keyword_list:
            for keyword in keyword_list:
                search_results = graph_service.fulltext_search(
                    query_text=keyword,
                    repo_id=repo_id,
                    limit=20
                )

                if search_results:
                    ranked = ranker.rank_files(
                        files=search_results,
                        query=keyword,
                        limit=10
                    )

                    for file in ranked:
                        all_nodes.append({
                            "type": "file",
                            "path": file["path"],
                            "lang": file["lang"],
                            "score": file["score"],
                            "ref": ranker.generate_ref_handle(path=file["path"])
                        })

        # Add focus files with high priority
        if focus_list:
            for focus_path in focus_list:
                all_nodes.append({
                    "type": "file",
                    "path": focus_path,
                    "lang": "unknown",
                    "score": 10.0,  # High priority
                    "ref": ranker.generate_ref_handle(path=focus_path)
                })

        # Build context pack
        if ctx:
            await ctx.info(f"Packing {len(all_nodes)} candidate files into context...")

        context_result = pack_builder.build_context_pack(
            nodes=all_nodes,
            budget=budget,
            file_limit=8,
            symbol_limit=12,
            enable_deduplication=True
        )

        # Format items
        items = []
        for item in context_result.get("items", []):
            items.append({
                "kind": item.get("type", "file"),
                "title": item.get("path", "Unknown"),
                "summary": item.get("summary", ""),
                "ref": item.get("ref", ""),
                "extra": {
                    "lang": item.get("lang"),
                    "score": item.get("score", 0.0)
                }
            })

        if ctx:
            await ctx.info(f"Context pack built: {len(items)} items, {context_result.get('budget_used', 0)} tokens")

        return {
            "success": True,
            "items": items,
            "budget_used": context_result.get("budget_used", 0),
            "budget_limit": budget,
            "stage": stage,
            "repo_id": repo_id,
            "category_counts": context_result.get("category_counts", {})
        }

    except Exception as e:
        error_msg = f"Context pack generation failed: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# ===================================
# MCP Resources
# ===================================

# MCP resource: knowledge base config
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

# MCP resource: system status
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
                "neo4j_connection": True,  # if initialized, connection is healthy
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

# MCP resource: recent documents
@mcp.resource("knowledge://recent-documents/{limit}")
async def get_recent_documents(limit: int = 10) -> Dict[str, Any]:
    """Get recently added documents."""
    try:
        await ensure_service_initialized()
        # here can be extended to query recent documents from graph database
        # currently return placeholder information
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

# ============================================================================
# Memory Management Tools
# ============================================================================

@mcp.tool
async def add_memory(
    project_id: str,
    memory_type: str,
    title: str,
    content: str,
    reason: Optional[str] = None,
    tags: Optional[List[str]] = None,
    importance: float = 0.5,
    related_refs: Optional[List[str]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Add a new memory to the project knowledge base.

    Use this to manually save important information about the project:
    - Design decisions and their rationale
    - Team preferences and conventions
    - Problems encountered and solutions
    - Future plans and improvements

    Args:
        project_id: Project identifier (e.g., repo name)
        memory_type: Type of memory - "decision", "preference", "experience", "convention", "plan", or "note"
        title: Short title/summary of the memory
        content: Detailed content and context
        reason: Rationale or explanation (optional)
        tags: Tags for categorization, e.g., ["auth", "security"] (optional)
        importance: Importance score 0-1, higher = more important (default 0.5)
        related_refs: List of ref:// handles this memory relates to (optional)

    Returns:
        Result with memory_id if successful

    Examples:
        # Decision memory
        add_memory(
            project_id="myapp",
            memory_type="decision",
            title="Use JWT for authentication",
            content="Decided to use JWT tokens instead of session-based auth",
            reason="Need stateless authentication for mobile clients and microservices",
            tags=["auth", "architecture"],
            importance=0.9,
            related_refs=["ref://file/src/auth/jwt.py"]
        )

        # Experience memory
        add_memory(
            project_id="myapp",
            memory_type="experience",
            title="Redis connection timeout in Docker",
            content="Redis connections fail with localhost in Docker environment",
            reason="Docker networking requires service name instead of localhost",
            tags=["docker", "redis", "bug"],
            importance=0.7
        )

        # Preference memory
        add_memory(
            project_id="myapp",
            memory_type="preference",
            title="Use raw SQL instead of ORM",
            content="Team prefers writing raw SQL queries over using ORM",
            reason="Better performance control and team is more familiar with SQL",
            tags=["database", "style"],
            importance=0.6
        )
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Adding {memory_type} memory: {title}")

        # Validate memory_type
        valid_types = ["decision", "preference", "experience", "convention", "plan", "note"]
        if memory_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid memory_type. Must be one of: {', '.join(valid_types)}"
            }

        # Validate importance
        if not 0 <= importance <= 1:
            return {
                "success": False,
                "error": "Importance must be between 0 and 1"
            }

        result = await memory_store.add_memory(
            project_id=project_id,
            memory_type=memory_type,
            title=title,
            content=content,
            reason=reason,
            tags=tags,
            importance=importance,
            related_refs=related_refs
        )

        if ctx and result.get("success"):
            await ctx.info(f"Memory saved with ID: {result.get('memory_id')}")

        return result

    except Exception as e:
        error_msg = f"Failed to add memory: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@mcp.tool
async def search_memories(
    project_id: str,
    query: Optional[str] = None,
    memory_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_importance: float = 0.0,
    limit: int = 20,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Search project memories with various filters.

    Use this to find relevant memories when:
    - Starting a new feature (search for related decisions)
    - Debugging an issue (search for similar experiences)
    - Understanding project conventions

    Args:
        project_id: Project identifier
        query: Search query (searches title, content, reason, tags) (optional)
        memory_type: Filter by type - "decision", "preference", "experience", "convention", "plan", or "note" (optional)
        tags: Filter by tags (matches any tag in the list) (optional)
        min_importance: Minimum importance score 0-1 (default 0.0)
        limit: Maximum number of results (default 20)

    Returns:
        List of matching memories sorted by relevance

    Examples:
        # Search for authentication-related decisions
        search_memories(project_id="myapp", query="authentication", memory_type="decision")

        # Find all high-importance decisions
        search_memories(project_id="myapp", memory_type="decision", min_importance=0.7)

        # Search by tags
        search_memories(project_id="myapp", tags=["docker", "redis"])

        # Get all memories
        search_memories(project_id="myapp", limit=50)
    """
    try:
        await ensure_service_initialized()

        if ctx:
            filters = []
            if query:
                filters.append(f"query='{query}'")
            if memory_type:
                filters.append(f"type={memory_type}")
            if tags:
                filters.append(f"tags={tags}")
            filter_str = ", ".join(filters) if filters else "no filters"
            await ctx.info(f"Searching memories with {filter_str}")

        result = await memory_store.search_memories(
            project_id=project_id,
            query=query,
            memory_type=memory_type,
            tags=tags,
            min_importance=min_importance,
            limit=limit
        )

        if ctx and result.get("success"):
            count = result.get("total_count", 0)
            await ctx.info(f"Found {count} matching memories")

        return result

    except Exception as e:
        error_msg = f"Failed to search memories: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@mcp.tool
async def get_memory(
    memory_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get a specific memory by ID with all details and related references.

    Args:
        memory_id: Memory identifier

    Returns:
        Full memory details including related code references

    Example:
        get_memory(memory_id="abc-123-def-456")
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Retrieving memory: {memory_id}")

        result = await memory_store.get_memory(memory_id)

        if ctx and result.get("success"):
            memory = result.get("memory", {})
            await ctx.info(f"Retrieved: {memory.get('title')} ({memory.get('type')})")

        return result

    except Exception as e:
        error_msg = f"Failed to get memory: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@mcp.tool
async def update_memory(
    memory_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    reason: Optional[str] = None,
    tags: Optional[List[str]] = None,
    importance: Optional[float] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Update an existing memory.

    Args:
        memory_id: Memory identifier
        title: New title (optional)
        content: New content (optional)
        reason: New reason (optional)
        tags: New tags (optional)
        importance: New importance score 0-1 (optional)

    Returns:
        Result with success status

    Example:
        update_memory(
            memory_id="abc-123",
            importance=0.9,
            tags=["auth", "security", "critical"]
        )
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Updating memory: {memory_id}")

        # Validate importance if provided
        if importance is not None and not 0 <= importance <= 1:
            return {
                "success": False,
                "error": "Importance must be between 0 and 1"
            }

        result = await memory_store.update_memory(
            memory_id=memory_id,
            title=title,
            content=content,
            reason=reason,
            tags=tags,
            importance=importance
        )

        if ctx and result.get("success"):
            await ctx.info(f"Memory updated successfully")

        return result

    except Exception as e:
        error_msg = f"Failed to update memory: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@mcp.tool
async def delete_memory(
    memory_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Delete a memory (soft delete - marks as deleted but retains data).

    Args:
        memory_id: Memory identifier

    Returns:
        Result with success status

    Example:
        delete_memory(memory_id="abc-123-def-456")
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Deleting memory: {memory_id}")

        result = await memory_store.delete_memory(memory_id)

        if ctx and result.get("success"):
            await ctx.info(f"Memory deleted (soft delete)")

        return result

    except Exception as e:
        error_msg = f"Failed to delete memory: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@mcp.tool
async def supersede_memory(
    old_memory_id: str,
    new_memory_type: str,
    new_title: str,
    new_content: str,
    new_reason: Optional[str] = None,
    new_tags: Optional[List[str]] = None,
    new_importance: float = 0.5,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new memory that supersedes an old one.

    Use this when a decision changes or a better solution is found.
    The old memory will be marked as superseded and linked to the new one.

    Args:
        old_memory_id: ID of the memory to supersede
        new_memory_type: Type of the new memory
        new_title: Title of the new memory
        new_content: Content of the new memory
        new_reason: Reason for the change (optional)
        new_tags: Tags for the new memory (optional)
        new_importance: Importance score for the new memory (default 0.5)

    Returns:
        Result with new_memory_id and old_memory_id

    Example:
        supersede_memory(
            old_memory_id="abc-123",
            new_memory_type="decision",
            new_title="Use PostgreSQL instead of MySQL",
            new_content="Switched to PostgreSQL for better JSON support",
            new_reason="Need advanced JSON querying capabilities",
            new_importance=0.8
        )
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Creating new memory to supersede: {old_memory_id}")

        # Validate memory_type
        valid_types = ["decision", "preference", "experience", "convention", "plan", "note"]
        if new_memory_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid memory_type. Must be one of: {', '.join(valid_types)}"
            }

        # Validate importance
        if not 0 <= new_importance <= 1:
            return {
                "success": False,
                "error": "Importance must be between 0 and 1"
            }

        result = await memory_store.supersede_memory(
            old_memory_id=old_memory_id,
            new_memory_data={
                "memory_type": new_memory_type,
                "title": new_title,
                "content": new_content,
                "reason": new_reason,
                "tags": new_tags,
                "importance": new_importance
            }
        )

        if ctx and result.get("success"):
            await ctx.info(f"New memory created: {result.get('new_memory_id')}")

        return result

    except Exception as e:
        error_msg = f"Failed to supersede memory: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

@mcp.tool
async def get_project_summary(
    project_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get a summary of all memories for a project, organized by type.

    Use this to get an overview of project knowledge:
    - How many decisions have been made
    - What conventions are in place
    - Key experiences and learnings

    Args:
        project_id: Project identifier

    Returns:
        Summary with counts and top memories by type

    Example:
        get_project_summary(project_id="myapp")
    """
    try:
        await ensure_service_initialized()

        if ctx:
            await ctx.info(f"Getting project summary for: {project_id}")

        result = await memory_store.get_project_summary(project_id)

        if ctx and result.get("success"):
            summary = result.get("summary", {})
            total = summary.get("total_memories", 0)
            await ctx.info(f"Project has {total} total memories")

        return result

    except Exception as e:
        error_msg = f"Failed to get project summary: {str(e)}"
        logger.error(error_msg)
        if ctx:
            await ctx.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

# MCP prompt: generate query suggestions
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
    # run MCP server
    mcp.run() 