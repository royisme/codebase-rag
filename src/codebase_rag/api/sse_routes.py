"""
Server-Sent Events (SSE) routes for real-time task monitoring
"""

import asyncio
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from codebase_rag.services.task_queue import task_queue, TaskStatus

router = APIRouter(prefix="/sse", tags=["SSE"])

# Active SSE connections
active_connections: Dict[str, Dict[str, Any]] = {}

@router.get("/task/{task_id}")
async def stream_task_progress(task_id: str, request: Request):
    """
    Stream task progress via Server-Sent Events
    
    Args:
        task_id: Task ID to monitor
    """
    
    async def event_generator():
        connection_id = f"{task_id}_{id(request)}"
        active_connections[connection_id] = {
            "task_id": task_id,
            "request": request,
            "start_time": asyncio.get_event_loop().time()
        }
        
        try:
            logger.info(f"Starting SSE stream for task {task_id}")
            
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id, 'timestamp': asyncio.get_event_loop().time()})}\n\n"
            
            last_progress = -1
            last_status = None
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from SSE stream for task {task_id}")
                    break
                
                # Get task status
                task_result = task_queue.get_task_status(task_id)
                
                if task_result is None:
                    # Task does not exist
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Task not found', 'task_id': task_id})}\n\n"
                    break
                
                # Check for progress updates
                if (task_result.progress != last_progress or 
                    task_result.status.value != last_status):
                    
                    event_data = {
                        "type": "progress",
                        "task_id": task_id,
                        "progress": task_result.progress,
                        "status": task_result.status.value,
                        "message": task_result.message,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                    last_progress = task_result.progress
                    last_status = task_result.status.value
                
                # Check if task is completed
                if task_result.status.value in ['success', 'failed', 'cancelled']:
                    completion_data = {
                        "type": "completed",
                        "task_id": task_id,
                        "final_status": task_result.status.value,
                        "final_progress": task_result.progress,
                        "final_message": task_result.message,
                        "result": task_result.result,
                        "error": task_result.error,
                        "created_at": task_result.created_at.isoformat(),
                        "started_at": task_result.started_at.isoformat() if task_result.started_at else None,
                        "completed_at": task_result.completed_at.isoformat() if task_result.completed_at else None,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    logger.info(f"Task {task_id} completed via SSE: {task_result.status.value}")
                    break
                
                # Wait 1 second before next check
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for task {task_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'task_id': task_id})}\n\n"
        finally:
            # Clean up connection
            if connection_id in active_connections:
                del active_connections[connection_id]
            logger.info(f"SSE stream ended for task {task_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/tasks")
async def stream_all_tasks(request: Request, status_filter: Optional[str] = None):
    """
    Stream all tasks progress via Server-Sent Events
    
    Args:
        status_filter: Optional status filter (pending, processing, success, failed, cancelled)
    """
    
    async def event_generator():
        connection_id = f"all_tasks_{id(request)}"
        active_connections[connection_id] = {
            "task_id": "all",
            "request": request,
            "start_time": asyncio.get_event_loop().time(),
            "status_filter": status_filter
        }
        
        try:
            logger.info(f"Starting SSE stream for all tasks (filter: {status_filter})")
            
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'scope': 'all_tasks', 'filter': status_filter, 'timestamp': asyncio.get_event_loop().time()})}\n\n"
            
            # 发送初始任务列表
            status_enum = None
            if status_filter:
                try:
                    status_enum = TaskStatus(status_filter.lower())
                except ValueError:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Invalid status filter: {status_filter}'})}\n\n"
                    return
            
            last_task_count = 0
            last_task_states = {}
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("Client disconnected from all tasks SSE stream")
                    break
                
                # 获取当前任务列表
                tasks = task_queue.get_all_tasks(status_filter=status_enum, limit=50)
                current_task_count = len(tasks)
                
                # 检查任务数量变化
                if current_task_count != last_task_count:
                    count_data = {
                        "type": "task_count_changed",
                        "total_tasks": current_task_count,
                        "filter": status_filter,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    yield f"data: {json.dumps(count_data)}\n\n"
                    last_task_count = current_task_count
                
                # 检查每个任务的状态变化
                current_states = {}
                for task in tasks:
                    task_key = task.task_id
                    current_state = {
                        "status": task.status.value,
                        "progress": task.progress,
                        "message": task.message
                    }
                    current_states[task_key] = current_state
                    
                    # 比较状态变化
                    if (task_key not in last_task_states or 
                        last_task_states[task_key] != current_state):
                        
                        task_data = {
                            "type": "task_updated",
                            "task_id": task.task_id,
                            "status": task.status.value,
                            "progress": task.progress,
                            "message": task.message,
                            "metadata": task.metadata,
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        yield f"data: {json.dumps(task_data)}\n\n"
                
                last_task_states = current_states
                
                # 等待2秒再检查
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            logger.info("All tasks SSE stream cancelled")
        except Exception as e:
            logger.error(f"Error in all tasks SSE stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            # Clean up connection
            if connection_id in active_connections:
                del active_connections[connection_id]
            logger.info("All tasks SSE stream ended")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/stats")
async def get_sse_stats():
    """
    Get SSE connection statistics
    """
    stats = {
        "active_connections": len(active_connections),
        "connections": []
    }
    
    for conn_id, conn_info in active_connections.items():
        stats["connections"].append({
            "connection_id": conn_id,
            "task_id": conn_info["task_id"],
            "duration": asyncio.get_event_loop().time() - conn_info["start_time"],
            "status_filter": conn_info.get("status_filter")
        })
    
    return stats