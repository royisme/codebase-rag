"""
异步任务队列服务
用于处理长时间运行的文档处理任务，避免阻塞用户请求
集成SQLite持久化存储，确保任务数据不会丢失
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

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
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class TaskQueue:
    """异步任务队列管理器（带持久化存储）"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, TaskResult] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._cleanup_interval = 3600  # 1小时清理一次完成的任务
        self._cleanup_task = None
        self._storage = None  # 延迟初始化，避免循环导入
        self._worker_id = str(uuid.uuid4())  # 唯一工作者ID用于锁定
        
    async def start(self):
        """启动任务队列"""
        # 延迟导入避免循环依赖
        from .task_storage import TaskStorage
        self._storage = TaskStorage()
        
        # 从数据库恢复任务
        await self._restore_tasks_from_storage()
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_completed_tasks())
        
        # 启动工作者处理待处理任务
        asyncio.create_task(self._process_pending_tasks())
        
        logger.info(f"Task queue started with max {self.max_concurrent_tasks} concurrent tasks")
    
    async def stop(self):
        """停止任务队列"""
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            task.cancel()
            if self._storage:
                await self._storage.update_task_status(task_id, TaskStatus.CANCELLED)
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.CANCELLED
        
        # 停止清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        
        logger.info("Task queue stopped")
    
    async def _restore_tasks_from_storage(self):
        """从存储中恢复任务状态"""
        if not self._storage:
            return
            
        try:
            # 恢复所有未完成的任务
            stored_tasks = await self._storage.list_tasks(limit=1000)
            
            for task in stored_tasks:
                # 创建TaskResult对象用于内存管理
                task_result = TaskResult(
                    task_id=task.id,
                    status=task.status,
                    progress=task.progress,
                    message="",
                    error=task.error_message,
                    created_at=task.created_at,
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                    metadata=task.payload
                )
                self.tasks[task.id] = task_result
                
                # 重新启动被中断的运行中任务
                if task.status == TaskStatus.PROCESSING:
                    logger.warning(f"Task {task.id} was processing when service stopped, marking as failed")
                    await self._storage.update_task_status(
                        task.id, 
                        TaskStatus.FAILED,
                        error_message="Service was restarted while task was processing"
                    )
                    task_result.status = TaskStatus.FAILED
                    task_result.error = "Service was restarted while task was processing"
                    task_result.completed_at = datetime.now()
            
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
        """提交一个新任务到队列"""
        from .task_storage import TaskType
        
        task_kwargs = task_kwargs or {}
        metadata = metadata or {}
        
        # 准备任务载荷
        payload = {
            "task_name": task_name,
            "task_type": task_type,
            "args": task_args,
            "kwargs": task_kwargs,
            "func_name": getattr(task_func, '__name__', str(task_func)),
            **metadata
        }
        
        # 映射任务类型
        task_type_enum = TaskType.DOCUMENT_PROCESSING
        if task_type == "schema_parsing":
            task_type_enum = TaskType.SCHEMA_PARSING
        elif task_type == "knowledge_graph_construction":
            task_type_enum = TaskType.KNOWLEDGE_GRAPH_CONSTRUCTION
        elif task_type == "batch_processing":
            task_type_enum = TaskType.BATCH_PROCESSING
        
        # 在数据库中创建任务
        if self._storage:
            task = await self._storage.create_task(task_type_enum, payload, priority)
            task_id = task.id
        else:
            task_id = str(uuid.uuid4())
        
        # 创建内存中的任务结果对象
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
        """持续处理待处理的任务"""
        while True:
            try:
                if self._storage:
                    # 获取待处理的任务
                    pending_tasks = await self._storage.get_pending_tasks(
                        limit=self.max_concurrent_tasks
                    )
                    
                    for task in pending_tasks:
                        # 检查是否已经在运行
                        if task.id in self.running_tasks:
                            continue
                        
                        # 尝试获取任务锁
                        if await self._storage.acquire_task_lock(task.id, self._worker_id):
                            # 启动任务执行
                            async_task = asyncio.create_task(
                                self._execute_stored_task(task)
                            )
                            self.running_tasks[task.id] = async_task
                
                # 等待一段时间再检查
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(5)
    
    async def _execute_stored_task(self, task):
        """执行存储的任务"""
        task_id = task.id
        task_result = self.tasks.get(task_id)
        
        if not task_result:
            # 创建任务结果对象
            task_result = TaskResult(
                task_id=task_id,
                status=task.status,
                progress=task.progress,
                created_at=task.created_at,
                metadata=task.payload
            )
            self.tasks[task_id] = task_result
        
        try:
            # 更新任务状态为处理中
            task_result.status = TaskStatus.PROCESSING
            task_result.started_at = datetime.now()
            task_result.message = "Task is processing"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.PROCESSING
                )
            
            logger.info(f"Task {task_id} started execution")
            
            # 从载荷中恢复任务函数和参数
            payload = task.payload
            task_name = payload.get("task_name", "Unknown Task")
            
            # 这里需要根据任务类型动态恢复任务函数
            # 暂时使用占位符，实际实现需要任务注册机制
            result = await self._execute_task_by_type(task)
            
            # 任务完成
            task_result.status = TaskStatus.SUCCESS
            task_result.completed_at = datetime.now()
            task_result.progress = 100.0
            task_result.result = result
            task_result.message = "Task completed successfully"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.SUCCESS
                )
            
            # 通知WebSocket客户端
            await self._notify_websocket_clients(task_id)
            
            logger.info(f"Task {task_id} completed successfully")
            
        except asyncio.CancelledError:
            task_result.status = TaskStatus.CANCELLED
            task_result.completed_at = datetime.now()
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
            task_result.completed_at = datetime.now()
            task_result.error = str(e)
            task_result.message = f"Task failed: {str(e)}"
            
            if self._storage:
                await self._storage.update_task_status(
                    task_id, TaskStatus.FAILED,
                    error_message=str(e)
                )
            
            # 通知WebSocket客户端
            await self._notify_websocket_clients(task_id)
            
            logger.error(f"Task {task_id} failed: {e}")
            
        finally:
            # 释放任务锁
            if self._storage:
                await self._storage.release_task_lock(task_id, self._worker_id)
            
            # 从运行任务列表中移除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _execute_task_by_type(self, task):
        """根据任务类型执行任务"""
        from .task_processors import processor_registry
        
        # 获取对应的任务处理器
        processor = processor_registry.get_processor(task.type)
        
        if not processor:
            raise ValueError(f"No processor found for task type: {task.type.value}")
        
        # 创建进度回调函数
        def progress_callback(progress: float, message: str = ""):
            self.update_task_progress(task.id, progress, message)
        
        # 执行任务
        result = await processor.process(task, progress_callback)
        
        return result
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    async def get_task_from_storage(self, task_id: str):
        """从存储中获取任务详情"""
        if self._storage:
            return await self._storage.get_task(task_id)
        return None
    
    def get_all_tasks(self, 
                     status_filter: Optional[TaskStatus] = None,
                     limit: int = 100) -> List[TaskResult]:
        """获取所有任务"""
        tasks = list(self.tasks.values())
        
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            # 取消正在运行的任务
            self.running_tasks[task_id].cancel()
            return True
        
        if task_id in self.tasks:
            task_result = self.tasks[task_id]
            if task_result.status == TaskStatus.PENDING:
                task_result.status = TaskStatus.CANCELLED
                task_result.completed_at = datetime.now()
                task_result.message = "Task was cancelled"
                
                if self._storage:
                    await self._storage.update_task_status(
                        task_id, TaskStatus.CANCELLED,
                        error_message="Task was cancelled"
                    )
                
                # 通知WebSocket客户端
                await self._notify_websocket_clients(task_id)
                
                return True
        
        return False
    
    def update_task_progress(self, task_id: str, progress: float, message: str = ""):
        """更新任务进度"""
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
            if message:
                self.tasks[task_id].message = message
            
            # 异步更新存储
            if self._storage:
                asyncio.create_task(
                    self._storage.update_task_status(
                        task_id, self.tasks[task_id].status, 
                        progress=progress
                    )
                )
            
            # 通知WebSocket客户端
            asyncio.create_task(self._notify_websocket_clients(task_id))
    
    async def _cleanup_completed_tasks(self):
        """定期清理已完成的任务"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                # 清理内存中的已完成任务（保留最近100个）
                completed_tasks = [
                    (task_id, task) for task_id, task in self.tasks.items()
                    if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]
                ]
                
                if len(completed_tasks) > 100:
                    # 按完成时间排序，删除最旧的
                    completed_tasks.sort(key=lambda x: x[1].completed_at or datetime.now())
                    tasks_to_remove = completed_tasks[:-100]
                    
                    for task_id, _ in tasks_to_remove:
                        del self.tasks[task_id]
                    
                    logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks from memory")
                
                # 清理数据库中的旧任务
                if self._storage:
                    cleaned_count = await self._storage.cleanup_old_tasks(days=30)
                    if cleaned_count > 0:
                        logger.info(f"Cleaned up {cleaned_count} old tasks from database")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        stats = {
            "total_tasks": len(self.tasks),
            "running_tasks": len(self.running_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "available_slots": self.task_semaphore._value,
        }
        
        # 状态统计
        status_counts = {}
        for task in self.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        stats["status_breakdown"] = status_counts
        
        # 从存储获取更详细的统计
        if self._storage:
            storage_stats = await self._storage.get_task_stats()
            stats["storage_stats"] = storage_stats
        
        return stats
    
    async def _notify_websocket_clients(self, task_id: str):
        """通知WebSocket客户端任务状态变化"""
        try:
            # 延迟导入避免循环依赖
            from api.websocket_routes import notify_task_status_change
            await notify_task_status_change(task_id, self.tasks[task_id].status.value, self.tasks[task_id].progress)
        except Exception as e:
            logger.error(f"Failed to notify WebSocket clients: {e}")

# 全局任务队列实例
task_queue = TaskQueue()

# 便捷函数
async def submit_document_processing_task(
    service_method: Callable,
    *args,
    task_name: str = "Document Processing",
    **kwargs
) -> str:
    """提交文档处理任务"""
    return await task_queue.submit_task(
        service_method,
        args,
        kwargs,
        task_name=task_name,
        task_type="document_processing"
    )

async def submit_directory_processing_task(
    service_method: Callable,
    directory_path: str,
    task_name: str = "Directory Processing",
    **kwargs
) -> str:
    """提交目录处理任务"""
    return await task_queue.submit_task(
        service_method,
        (directory_path,),
        kwargs,
        task_name=task_name,
        task_type="batch_processing"
    ) 