"""
asynchronous task queue service
used to handle long-running document processing tasks, avoiding blocking user requests
integrates SQLite persistence to ensure task data is not lost
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from loguru import logger

def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def ensure_aware(dt_value: Optional[datetime]) -> Optional[datetime]:
    """Return a timezone-aware datetime (default to UTC)."""
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class TaskQueue:
    """asynchronous task queue manager (with persistent storage)"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, TaskResult] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._cleanup_interval = 3600  # 1 hour to clean up completed tasks
        self._cleanup_task = None
        self._storage = None  # delay initialization to avoid circular import
        self._worker_id = str(uuid.uuid4())  # unique worker ID for locking
        self._task_worker = None  # task processing worker
        
    async def start(self):
        """start task queue"""
        # delay import to avoid circular dependency
        from .task_storage import TaskStorage
        self._storage = TaskStorage()
        
        # restore tasks from database
        await self._restore_tasks_from_storage()
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_completed_tasks())
        
        # start worker to process pending tasks
        logger.info("About to start task processing worker...")
        task_worker = asyncio.create_task(self._process_pending_tasks())
        logger.info("Task processing worker started")
        
        # Store the task worker reference to keep it alive
        self._task_worker = task_worker
        
        # Test if we can get pending tasks immediately
        try:
            test_tasks = await self._storage.get_pending_tasks(limit=5)
            logger.info(f"Initial pending tasks check: found {len(test_tasks)} tasks")
            for task in test_tasks:
                logger.info(f"  - Task {task.id}: {task.type.value}")
        except Exception as e:
            logger.error(f"Failed to get initial pending tasks: {e}")
        
        logger.info(f"Task queue started with max {self.max_concurrent_tasks} concurrent tasks")
    
    async def stop(self):
        """stop task queue"""
        # cancel all running tasks
        for task_id, task in self.running_tasks.items():
            task.cancel()
            if self._storage:
                await self._storage.update_task_status(task_id, TaskStatus.CANCELLED)
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.CANCELLED
        
        # stop task worker
        if hasattr(self, '_task_worker') and self._task_worker:
            self._task_worker.cancel()
            self._task_worker = None
        
        # stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        
        logger.info("Task queue stopped")
    
    async def _restore_tasks_from_storage(self):
        """restore task status from storage"""
        if not self._storage:
            return
            
        try:
            # restore all incomplete tasks
            stored_tasks = await self._storage.list_tasks(limit=1000)
            logger.info(f"Restoring {len(stored_tasks)} tasks from storage")
            
            for task in stored_tasks:
                # create TaskResult object for memory management
                task_result = TaskResult(
                    task_id=task.id,
                    status=task.status,
                    progress=task.progress,
                    message="",
                    error=task.error_message,
                    created_at=ensure_aware(task.created_at),
                    started_at=ensure_aware(task.started_at),
                    completed_at=ensure_aware(task.completed_at),
                    metadata=task.payload,
                )
                self.tasks[task.id] = task_result
                
                # restart interrupted running tasks
                if task.status == TaskStatus.PROCESSING:
                    logger.warning(f"Task {task.id} was processing when service stopped, marking as failed")
                    await self._storage.update_task_status(
                        task.id, 
                        TaskStatus.FAILED,
                        error_message="Service was restarted while task was processing"
                    )
                    task_result.status = TaskStatus.FAILED
                    task_result.error = "Service was restarted while task was processing"
                    task_result.completed_at = utcnow()
            
            logger.info(f"Restored {len(stored_tasks)} tasks from storage")
            
        except Exception as e:
            logger.error(f"Failed to restore tasks from storage: {e}")
    
    async def submit_task(self, 
                         task_func: Callable,
                         task_args: tuple = (),
                         task_kwargs: dict = None,
                         task_name: str = "Unknown Task",
                         task_type: str = "unknown",
                         metadata: Dict[str, Any] = None,
                         priority: int = 0) -> str:
        """submit a new task to the queue"""
        from .task_storage import TaskType
        
        task_kwargs = task_kwargs or {}
        metadata = metadata or {}
        
        # prepare task payload
        payload = {
            "task_name": task_name,
            "task_type": task_type,
            "args": task_args,
            "kwargs": task_kwargs,
            "func_name": getattr(task_func, '__name__', str(task_func)),
            **metadata
        }
        
        # map task type
        task_type_enum = TaskType.DOCUMENT_PROCESSING
        if task_type == "schema_parsing":
            task_type_enum = TaskType.SCHEMA_PARSING
        elif task_type == "knowledge_graph_construction":
            task_type_enum = TaskType.KNOWLEDGE_GRAPH_CONSTRUCTION
        elif task_type == "batch_processing":
            task_type_enum = TaskType.BATCH_PROCESSING
        elif task_type == "knowledge_source_sync":
            task_type_enum = TaskType.KNOWLEDGE_SOURCE_SYNC
        
        # create task in database
        if self._storage:
            task = await self._storage.create_task(task_type_enum, payload, priority)
            task_id = task.id
        else:
            task_id = str(uuid.uuid4())
        
        # create task result object in memory
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Task '{task_name}' queued",
            metadata=payload
        )
        
        self.tasks[task_id] = task_result
        
        logger.info(f"Task {task_id} ({task_name}) submitted to queue")
        return task_id
    
    async def _process_pending_tasks(self):
        """continuously process pending tasks"""
        logger.info("Task processing loop started")
        loop_count = 0
        while True:
            loop_count += 1
            if loop_count % 60 == 1:  # Log every 60 iterations (every minute)
                logger.debug(f"Task processing loop iteration {loop_count}")
            try:
                if not self._storage:
                    if loop_count % 50 == 1:  # Log storage issue every 50 iterations
                        logger.warning("No storage available for task processing")
                    await asyncio.sleep(1)
                    continue
                    
                if self._storage:
                    # 获取待处理的任务
                    pending_tasks = await self._storage.get_pending_tasks(
                        limit=self.max_concurrent_tasks
                    )
                    
                    if loop_count % 10 == 1 and pending_tasks:  # Log every 10 iterations if tasks found
                        logger.info(f"Found {len(pending_tasks)} pending tasks")
                    elif pending_tasks:  # Always log when tasks are found
                        logger.debug(f"Found {len(pending_tasks)} pending tasks")
                    
                    for task in pending_tasks:
                        # 检查是否已经在运行
                        if task.id in self.running_tasks:
                            logger.debug(f"Task {task.id} already running, skipping")
                            continue
                        
                        logger.info(f"Attempting to acquire lock for task {task.id}")
                        # 尝试获取任务锁
                        if await self._storage.acquire_task_lock(task.id, self._worker_id):
                            logger.info(f"Lock acquired, starting execution for task {task.id}")
                            # 启动任务执行
                            async_task = asyncio.create_task(
                                self._execute_stored_task(task)
                            )
                            self.running_tasks[task.id] = async_task
                        else:
                            logger.debug(f"Failed to acquire lock for task {task.id}")
                
                # 等待一段时间再检查
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                logger.exception(f"Full traceback for task processing loop error:")
                await asyncio.sleep(5)
    
    async def _execute_stored_task(self, task):
        """execute stored task"""
        task_id = task.id
        logger.info(f"Starting execution of stored task {task_id}")
        task_result = self.tasks.get(task_id)
        
        if not task_result:
            # create task result object
            task_result = TaskResult(
                task_id=task_id,
                status=task.status,
                progress=task.progress,
                created_at=ensure_aware(task.created_at),
                metadata=task.payload,
            )
            self.tasks[task_id] = task_result
        
        try:
            # update task status to processing
            task_result.status = TaskStatus.PROCESSING
            task_result.started_at = utcnow()
            task_result.message = "Task is processing"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.PROCESSING
                )
            
            logger.info(f"Task {task_id} started execution")
            
            # restore task function and parameters from payload
            payload = task.payload
            task_name = payload.get("task_name", "Unknown Task")
            
            # here we need to dynamically restore task function based on task type
            # for now, we use a placeholder, actual implementation needs task registration mechanism
            logger.info(f"Task {task_id} about to execute by type: {task.type}")
            result = await self._execute_task_by_type(task)
            if isinstance(result, dict):
                preview = {key: result[key] for key in list(result)[:5]}
                logger.info("Task {} execution completed with result keys: {}", task_id, list(result.keys()))
                logger.debug("Task {} result preview: {}", task_id, preview)
            else:
                logger.info("Task {} execution completed with result: {}", task_id, repr(result)[:200])
            
            # task completed
            task_result.status = TaskStatus.SUCCESS
            task_result.completed_at = utcnow()
            task_result.progress = 100.0
            task_result.result = result
            task_result.message = "Task completed successfully"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.SUCCESS
                )
            
            # notify WebSocket clients
            await self._notify_websocket_clients(task_id)
            
            logger.info(f"Task {task_id} completed successfully")
            
        except asyncio.CancelledError:
            task_result.status = TaskStatus.CANCELLED
            task_result.completed_at = utcnow()
            task_result.message = "Task was cancelled"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.CANCELLED,
                    error_message="Task was cancelled"
                )
            
            # 通知WebSocket客户端
            await self._notify_websocket_clients(task_id)
            
            logger.info(f"Task {task_id} was cancelled")
            
        except Exception as e:
            task_result.status = TaskStatus.FAILED
            task_result.completed_at = utcnow()
            task_result.error = str(e)
            task_result.message = f"Task failed: {str(e)}"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.FAILED,
                    error_message=str(e)
                )
            
            # notify WebSocket clients
            await self._notify_websocket_clients(task_id)
            
            logger.error(f"Task {task_id} failed: {e}")
            
        finally:
            # release task lock
            if self._storage:
                await self._storage.release_task_lock(task_id, self._worker_id)
            
            # remove task from running tasks list
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _execute_task_by_type(self, task):
        """execute task based on task type"""
        from .task_processors import processor_registry
        
        # get corresponding task processor
        processor = processor_registry.get_processor(task.type)
        
        if not processor:
            raise ValueError(f"No processor found for task type: {task.type.value}")
        
        # create progress callback function
        def progress_callback(progress: float, message: str = ""):
            self.update_task_progress(task.id, progress, message)
        
        # execute task
        result = await processor.process(task, progress_callback)
        
        return result
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """get task status"""
        return self.tasks.get(task_id)
    
    async def get_task_from_storage(self, task_id: str):
        """get task details from storage"""
        if self._storage:
            return await self._storage.get_task(task_id)
        return None
    
    def get_all_tasks(self, 
                     status_filter: Optional[TaskStatus] = None,
                     limit: int = 100) -> List[TaskResult]:
        """get all tasks"""
        tasks = list(self.tasks.values())
        
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        # sort by creation time in descending order
        tasks.sort(key=lambda x: ensure_aware(x.created_at), reverse=True)
        
        return tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """cancel task"""
        if task_id in self.running_tasks:
            # cancel running task
            self.running_tasks[task_id].cancel()
            return True
        
        if task_id in self.tasks:
            task_result = self.tasks[task_id]
            if task_result.status == TaskStatus.PENDING:
                task_result.status = TaskStatus.CANCELLED
                task_result.completed_at = utcnow()
                task_result.message = "Task was cancelled"
                
                if self._storage:
                    await self._storage.update_task_status(
                        task_id, TaskStatus.CANCELLED,
                        error_message="Task was cancelled"
                    )
                
                # notify WebSocket clients
                await self._notify_websocket_clients(task_id)
                
                return True
        
        return False
    
    def update_task_progress(self, task_id: str, progress: float, message: str = ""):
        """update task progress"""
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
            if message:
                self.tasks[task_id].message = message
            
            # async update storage
            if self._storage:
                asyncio.create_task(
                    self._storage.update_task_status(
                        task_id, self.tasks[task_id].status, 
                        progress=progress
                    )
                )
            
            # notify WebSocket clients
            asyncio.create_task(self._notify_websocket_clients(task_id))
    
    async def _cleanup_completed_tasks(self):
        """clean up completed tasks periodically"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                # clean up completed tasks in memory (keep last 100)
                completed_tasks = [
                    (task_id, task) for task_id, task in self.tasks.items()
                    if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]
                ]
                
                if len(completed_tasks) > 100:
                    # sort by completion time, delete oldest
                    completed_tasks.sort(
                        key=lambda x: ensure_aware(x[1].completed_at) or utcnow()
                    )
                    tasks_to_remove = completed_tasks[:-100]
                    
                    for task_id, _ in tasks_to_remove:
                        del self.tasks[task_id]
                    
                    logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks from memory")
                
                # clean up old tasks in database
                if self._storage:
                    cleaned_count = await self._storage.cleanup_old_tasks(days=30)
                    if cleaned_count > 0:
                        logger.info(f"Cleaned up {cleaned_count} old tasks from database")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """get queue statistics"""
        stats = {
            "total_tasks": len(self.tasks),
            "running_tasks": len(self.running_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "available_slots": self.task_semaphore._value,
        }
        
        # status statistics
        status_counts = {}
        for task in self.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        stats["status_breakdown"] = status_counts
        
        # get more detailed statistics from storage
        if self._storage:
            storage_stats = await self._storage.get_task_stats()
            stats["storage_stats"] = storage_stats
        
        return stats
    
    async def _notify_websocket_clients(self, task_id: str):
        """notify WebSocket clients about task status change"""
        try:
            # delay import to avoid circular dependency
            from api.websocket_routes import notify_task_status_change
            await notify_task_status_change(task_id, self.tasks[task_id].status.value, self.tasks[task_id].progress)
        except Exception as e:
            logger.error(f"Failed to notify WebSocket clients: {e}")

# global task queue instance
task_queue = TaskQueue()

# convenience function
async def submit_document_processing_task(
    service_method: Callable,
    *args,
    task_name: str = "Document Processing",
    **kwargs
) -> str:
    """submit document processing task"""
    return await task_queue.submit_task(
        task_func=service_method,
        task_args=args,
        task_kwargs=kwargs,
        task_name=task_name,
        task_type="document_processing"
    )

async def submit_directory_processing_task(
    service_method: Callable,
    directory_path: str,
    task_name: str = "Directory Processing",
    **kwargs
) -> str:
    """submit directory processing task"""
    return await task_queue.submit_task(
        task_func=service_method,
        task_args=(directory_path,),
        task_kwargs=kwargs,
        task_name=task_name,
        task_type="batch_processing"
    )

async def submit_knowledge_source_sync_task(
    source_id: str,
    job_id: str,
    sync_config: Optional[Dict[str, Any]] = None,
    task_name: str = "Knowledge Source Sync",
    **kwargs
) -> str:
    """submit knowledge source sync task"""
    return await task_queue.submit_task(
        task_func=lambda: None,  # 处理逻辑在processor中
        task_kwargs={
            "source_id": source_id,
            "job_id": job_id,
            "sync_config": sync_config or {},
            **kwargs
        },
        task_name=task_name,
        task_type="knowledge_source_sync"
    ) 
