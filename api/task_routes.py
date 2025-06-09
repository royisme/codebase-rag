"""
Task management API routes
Provide REST API interface for task queue
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from services.task_queue import task_queue, TaskStatus
from services.task_storage import TaskType
from loguru import logger

router = APIRouter(prefix="/tasks", tags=["Task Management"])

# request model
class CreateTaskRequest(BaseModel):
    task_type: str
    task_name: str
    payload: Dict[str, Any]
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any]

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int

class TaskStatsResponse(BaseModel):
    total_tasks: int
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int

# API endpoints

@router.post("/", response_model=Dict[str, str])
async def create_task(request: CreateTaskRequest):
    """create new task"""
    try:
        # validate task type
        valid_task_types = ["document_processing", "schema_parsing", "knowledge_graph_construction", "batch_processing"]
        if request.task_type not in valid_task_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid task type. Must be one of: {', '.join(valid_task_types)}"
            )
        
        # prepare task parameters
        task_kwargs = request.payload.copy()
        if request.metadata:
            task_kwargs.update(request.metadata)
        
        # select processing function based on task type
        task_func = None
        if request.task_type == "document_processing":
            from services.task_processors import process_document_task
            task_func = process_document_task
        elif request.task_type == "schema_parsing":
            from services.task_processors import process_schema_parsing_task
            task_func = process_schema_parsing_task
        elif request.task_type == "knowledge_graph_construction":
            from services.task_processors import process_knowledge_graph_task
            task_func = process_knowledge_graph_task
        elif request.task_type == "batch_processing":
            from services.task_processors import process_batch_task
            task_func = process_batch_task
        
        if not task_func:
            raise HTTPException(status_code=400, detail="Task processor not found")
        
        # submit task
        task_id = await task_queue.submit_task(
            task_func=task_func,
            task_kwargs=task_kwargs,
            task_name=request.task_name,
            task_type=request.task_type,
            metadata=request.metadata or {},
            priority=request.priority
        )
        
        logger.info(f"Task {task_id} created successfully")
        return {"task_id": task_id, "status": "created"}
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """get task status"""
    try:
        # first get from memory
        task_result = task_queue.get_task_status(task_id)
        
        if not task_result:
            # get from storage
            stored_task = await task_queue.get_task_from_storage(task_id)
            if not stored_task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # convert to TaskResponse format
            return TaskResponse(
                task_id=stored_task.id,
                status=stored_task.status.value,
                progress=stored_task.progress,
                message=stored_task.error_message or "Task stored",
                result=None,
                error=stored_task.error_message,
                created_at=stored_task.created_at,
                started_at=stored_task.started_at,
                completed_at=stored_task.completed_at,
                metadata=stored_task.payload
            )
        
        return TaskResponse(
            task_id=task_result.task_id,
            status=task_result.status.value,
            progress=task_result.progress,
            message=task_result.message,
            result=task_result.result,
            error=task_result.error,
            created_at=task_result.created_at,
            started_at=task_result.started_at,
            completed_at=task_result.completed_at,
            metadata=task_result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    task_type: Optional[str] = Query(None, description="Filter by task type")
):
    """get task list"""
    try:
        # validate status parameter
        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status. Must be one of: {', '.join([s.value for s in TaskStatus])}"
                )
        
        # get task list
        tasks = task_queue.get_all_tasks(status_filter=status_filter, limit=page_size * 10)
        
        # apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = tasks[start_idx:end_idx]
        
        # convert to response format
        task_responses = []
        for task in paginated_tasks:
            task_responses.append(TaskResponse(
                task_id=task.task_id,
                status=task.status.value,
                progress=task.progress,
                message=task.message,
                result=task.result,
                error=task.error,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                metadata=task.metadata
            ))
        
        return TaskListResponse(
            tasks=task_responses,
            total=len(tasks),
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """cancel task"""
    try:
        success = await task_queue.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        
        logger.info(f"Task {task_id} cancelled successfully")
        return {"message": "Task cancelled successfully", "task_id": task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview", response_model=TaskStatsResponse)
async def get_task_stats():
    """get task statistics"""
    try:
        all_tasks = task_queue.get_all_tasks(limit=1000)
        
        stats = {
            "total_tasks": len(all_tasks),
            "pending_tasks": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "processing_tasks": len([t for t in all_tasks if t.status == TaskStatus.PROCESSING]),
            "completed_tasks": len([t for t in all_tasks if t.status == TaskStatus.SUCCESS]),
            "failed_tasks": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
            "cancelled_tasks": len([t for t in all_tasks if t.status == TaskStatus.CANCELLED])
        }
        
        return TaskStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{task_id}/retry")
async def retry_task(task_id: str):
    """retry failed task"""
    try:
        # get task information
        task_result = task_queue.get_task_status(task_id)
        if not task_result:
            stored_task = await task_queue.get_task_from_storage(task_id)
            if not stored_task:
                raise HTTPException(status_code=404, detail="Task not found")
        
        # check task status
        current_status = task_result.status if task_result else TaskStatus(stored_task.status)
        if current_status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=400, 
                detail="Only failed or cancelled tasks can be retried"
            )
        
        # resubmit task
        metadata = task_result.metadata if task_result else stored_task.payload
        task_name = metadata.get("task_name", "Retried Task")
        task_type = metadata.get("task_type", "unknown")
        
        # select processing function based on task type
        task_func = None
        if task_type == "document_processing":
            from services.task_processors import process_document_task
            task_func = process_document_task
        elif task_type == "schema_parsing":
            from services.task_processors import process_schema_parsing_task
            task_func = process_schema_parsing_task
        elif task_type == "knowledge_graph_construction":
            from services.task_processors import process_knowledge_graph_task
            task_func = process_knowledge_graph_task
        elif task_type == "batch_processing":
            from services.task_processors import process_batch_task
            task_func = process_batch_task
        
        if not task_func:
            raise HTTPException(status_code=400, detail="Task processor not found")
        
        new_task_id = await task_queue.submit_task(
            task_func=task_func,
            task_kwargs=metadata,
            task_name=f"Retry: {task_name}",
            task_type=task_type,
            metadata=metadata,
            priority=0
        )
        
        logger.info(f"Task {task_id} retried as {new_task_id}")
        return {"message": "Task retried successfully", "original_task_id": task_id, "new_task_id": new_task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/status")
async def get_queue_status():
    """get queue status"""
    try:
        running_tasks = len(task_queue.running_tasks)
        max_concurrent = task_queue.max_concurrent_tasks
        
        return {
            "running_tasks": running_tasks,
            "max_concurrent_tasks": max_concurrent,
            "available_slots": max_concurrent - running_tasks,
            "queue_active": True
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 