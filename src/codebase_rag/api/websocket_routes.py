"""
WebSocket routes
Provide real-time task status updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
from loguru import logger

from codebase_rag.services.task_queue import task_queue

router = APIRouter()

class ConnectionManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """disconnect WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """send personal message"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """broadcast message to all connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")
                disconnected.append(connection)
        
        # clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

# global connection manager
manager = ConnectionManager()

@router.websocket("/ws/tasks")
async def websocket_endpoint(websocket: WebSocket):
    """task status WebSocket endpoint"""
    await manager.connect(websocket)
    
    try:
        # send initial data
        await send_initial_data(websocket)
        
        # start periodic update task
        update_task = asyncio.create_task(periodic_updates(websocket))
        
        # listen to client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # handle client requests
                await handle_client_message(websocket, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON format"}),
                    websocket
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": str(e)}),
                    websocket
                )
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # cancel update task
        if 'update_task' in locals():
            update_task.cancel()
        manager.disconnect(websocket)

async def send_initial_data(websocket: WebSocket):
    """send initial data"""
    try:
        # send task statistics
        stats = await get_task_stats()
        await manager.send_personal_message(
            json.dumps({"type": "stats", "data": stats}),
            websocket
        )
        
        # send task list
        tasks = task_queue.get_all_tasks(limit=50)
        task_data = [format_task_for_ws(task) for task in tasks]
        await manager.send_personal_message(
            json.dumps({"type": "tasks", "data": task_data}),
            websocket
        )
        
        # send queue status
        queue_status = {
            "running_tasks": len(task_queue.running_tasks),
            "max_concurrent_tasks": task_queue.max_concurrent_tasks,
            "available_slots": task_queue.max_concurrent_tasks - len(task_queue.running_tasks)
        }
        await manager.send_personal_message(
            json.dumps({"type": "queue_status", "data": queue_status}),
            websocket
        )
        
    except Exception as e:
        logger.error(f"Failed to send initial data: {e}")

async def periodic_updates(websocket: WebSocket):
    """periodic updates"""
    try:
        while True:
            await asyncio.sleep(3)  # update every 3 seconds
            
            # send statistics update
            stats = await get_task_stats()
            await manager.send_personal_message(
                json.dumps({"type": "stats_update", "data": stats}),
                websocket
            )
            
            # send processing task progress update
            processing_tasks = task_queue.get_all_tasks(status_filter=None, limit=100)
            processing_tasks = [t for t in processing_tasks if t.status.value == 'processing']
            
            if processing_tasks:
                task_data = [format_task_for_ws(task) for task in processing_tasks]
                await manager.send_personal_message(
                    json.dumps({"type": "progress_update", "data": task_data}),
                    websocket
                )
    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in periodic updates: {e}")

async def handle_client_message(websocket: WebSocket, message: dict):
    """handle client messages"""
    message_type = message.get("type")
    
    if message_type == "get_tasks":
        # get task list
        status_filter = message.get("status_filter")
        limit = message.get("limit", 50)
        
        if status_filter:
            from services.task_queue import TaskStatus
            try:
                status_enum = TaskStatus(status_filter.upper())
                tasks = task_queue.get_all_tasks(status_filter=status_enum, limit=limit)
            except ValueError:
                tasks = task_queue.get_all_tasks(limit=limit)
        else:
            tasks = task_queue.get_all_tasks(limit=limit)
        
        task_data = [format_task_for_ws(task) for task in tasks]
        await manager.send_personal_message(
            json.dumps({"type": "tasks", "data": task_data}),
            websocket
        )
    
    elif message_type == "get_task_detail":
        # get task detail
        task_id = message.get("task_id")
        if task_id:
            task_result = task_queue.get_task_status(task_id)
            if task_result:
                task_data = format_task_for_ws(task_result)
                await manager.send_personal_message(
                    json.dumps({"type": "task_detail", "data": task_data}),
                    websocket
                )
            else:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Task not found"}),
                    websocket
                )
    
    elif message_type == "subscribe_task":
        # subscribe to specific task updates
        task_id = message.get("task_id")
        # here you can implement specific task subscription logic
        await manager.send_personal_message(
            json.dumps({"type": "subscribed", "task_id": task_id}),
            websocket
        )

async def get_task_stats():
    """get task statistics"""
    try:
        all_tasks = task_queue.get_all_tasks(limit=1000)
        
        from services.task_queue import TaskStatus
        stats = {
            "total_tasks": len(all_tasks),
            "pending_tasks": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "processing_tasks": len([t for t in all_tasks if t.status == TaskStatus.PROCESSING]),
            "completed_tasks": len([t for t in all_tasks if t.status == TaskStatus.SUCCESS]),
            "failed_tasks": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
            "cancelled_tasks": len([t for t in all_tasks if t.status == TaskStatus.CANCELLED])
        }
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return {
            "total_tasks": 0,
            "pending_tasks": 0,
            "processing_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0
        }

def format_task_for_ws(task_result):
    """format task data for WebSocket transmission"""
    return {
        "task_id": task_result.task_id,
        "status": task_result.status.value,
        "progress": task_result.progress,
        "message": task_result.message,
        "error": task_result.error,
        "created_at": task_result.created_at.isoformat() if task_result.created_at else None,
        "started_at": task_result.started_at.isoformat() if task_result.started_at else None,
        "completed_at": task_result.completed_at.isoformat() if task_result.completed_at else None,
        "metadata": task_result.metadata
    }

# task status change notification function
async def notify_task_status_change(task_id: str, status: str, progress: float = None):
    """notify task status change"""
    try:
        task_result = task_queue.get_task_status(task_id)
        if task_result:
            task_data = format_task_for_ws(task_result)
            message = {
                "type": "task_status_change",
                "data": task_data
            }
            await manager.broadcast(json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to notify task status change: {e}") 