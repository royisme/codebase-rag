"""
task persistent storage based on SQLite
ensures task data is not lost, supports task state recovery after service restart
"""

import sqlite3
import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger
from src.codebase_rag.config import settings

from .task_queue import TaskResult, TaskStatus

class TaskType(Enum):
    DOCUMENT_PROCESSING = "document_processing"
    SCHEMA_PARSING = "schema_parsing"
    KNOWLEDGE_GRAPH_CONSTRUCTION = "knowledge_graph_construction"
    BATCH_PROCESSING = "batch_processing"

@dataclass
class Task:
    id: str
    type: TaskType
    status: TaskStatus
    payload: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    lock_id: Optional[str] = None
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['type'] = self.type.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        
        # Add error handling for large payload serialization
        try:
            payload_json = json.dumps(self.payload)
            # Check if payload is too large
            if len(payload_json) > settings.max_payload_size:
                logger.warning(f"Task {self.id} payload is very large ({len(payload_json)} bytes)")
                # For very large payloads, store a summary instead
                summary_payload = {
                    "error": "Payload too large for storage",
                    "original_size": len(payload_json),
                    "original_keys": list(self.payload.keys()) if isinstance(self.payload, dict) else str(type(self.payload)),
                    "truncated_sample": str(self.payload)[:1000] + "..." if len(str(self.payload)) > 1000 else str(self.payload)
                }
                data['payload'] = json.dumps(summary_payload)
            else:
                data['payload'] = payload_json
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize payload for task {self.id}: {e}")
            # Store a truncated version for debugging
            data['payload'] = json.dumps({
                "error": "Payload too large to serialize",
                "original_keys": list(self.payload.keys()) if isinstance(self.payload, dict) else str(type(self.payload)),
                "serialization_error": str(e)
            })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        # Handle payload deserialization with error handling
        payload = {}
        try:
            if isinstance(data['payload'], str):
                payload = json.loads(data['payload'])
            else:
                payload = data['payload']
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to deserialize payload for task {data['id']}: {e}")
            payload = {"error": "Failed to deserialize payload", "raw_payload": str(data['payload'])[:1000]}
        
        return cls(
            id=data['id'],
            type=TaskType(data['type']),
            status=TaskStatus(data['status']),
            payload=payload,
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data['started_at'] else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None,
            error_message=data['error_message'],
            progress=data['progress'],
            lock_id=data['lock_id'],
            priority=data['priority']
        )

class TaskStorage:
    """task persistent storage manager"""
    
    def __init__(self, db_path: str = "data/tasks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_database()
    
    def _init_database(self):
        """initialize database table structure"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    progress REAL DEFAULT 0.0,
                    lock_id TEXT,
                    priority INTEGER DEFAULT 0
                )
            """)
            
            # create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_lock_id ON tasks(lock_id)")
            
            conn.commit()
        
        logger.info(f"Task storage initialized at {self.db_path}")
    
    async def create_task(self, task_type: TaskType, payload: Dict[str, Any], priority: int = 0) -> Task:
        """Create a new task"""
        async with self._lock:
            task = Task(
                id=str(uuid.uuid4()),
                type=task_type,
                status=TaskStatus.PENDING,
                payload=payload,
                created_at=datetime.now(),
                priority=priority
            )
            
            await asyncio.to_thread(self._insert_task, task)
            logger.info(f"Created task {task.id} of type {task_type.value}")
            return task
    
    def _insert_task(self, task: Task):
        """Insert task into database (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            task_data = task.to_dict()
            conn.execute("""
                INSERT INTO tasks (id, type, status, payload, created_at, started_at, 
                                 completed_at, error_message, progress, lock_id, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data['id'], task_data['type'], task_data['status'], 
                task_data['payload'], task_data['created_at'], task_data['started_at'],
                task_data['completed_at'], task_data['error_message'], 
                task_data['progress'], task_data['lock_id'], task_data['priority']
            ))
            conn.commit()
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        async with self._lock:
            return await asyncio.to_thread(self._get_task_sync, task_id)
    
    def _get_task_sync(self, task_id: str) -> Optional[Task]:
        """Get task by ID (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return Task.from_dict(dict(row))
            return None
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                error_message: Optional[str] = None, 
                                progress: Optional[float] = None) -> bool:
        """Update task status and related fields"""
        async with self._lock:
            return await asyncio.to_thread(
                self._update_task_status_sync, task_id, status, error_message, progress
            )
    
    def _update_task_status_sync(self, task_id: str, status: TaskStatus, 
                                error_message: Optional[str] = None, 
                                progress: Optional[float] = None) -> bool:
        """Update task status (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            updates = ["status = ?"]
            params = [status.value]
            
            if status == TaskStatus.PROCESSING:
                updates.append("started_at = ?")
                params.append(datetime.now().isoformat())
            elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                updates.append("completed_at = ?")
                params.append(datetime.now().isoformat())
            
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)
            
            params.append(task_id)
            
            cursor = conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    async def acquire_task_lock(self, task_id: str, lock_id: str) -> bool:
        """Acquire a lock on a task"""
        async with self._lock:
            return await asyncio.to_thread(self._acquire_task_lock_sync, task_id, lock_id)
    
    def _acquire_task_lock_sync(self, task_id: str, lock_id: str) -> bool:
        """Acquire task lock (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE tasks SET lock_id = ? WHERE id = ? AND (lock_id IS NULL OR lock_id = ?)",
                (lock_id, task_id, lock_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    async def release_task_lock(self, task_id: str, lock_id: str) -> bool:
        """Release a task lock"""
        async with self._lock:
            return await asyncio.to_thread(self._release_task_lock_sync, task_id, lock_id)
    
    def _release_task_lock_sync(self, task_id: str, lock_id: str) -> bool:
        """Release task lock (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE tasks SET lock_id = NULL WHERE id = ? AND lock_id = ?",
                (task_id, lock_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """Get pending tasks ordered by priority and creation time"""
        async with self._lock:
            return await asyncio.to_thread(self._get_pending_tasks_sync, limit)
    
    def _get_pending_tasks_sync(self, limit: int) -> List[Task]:
        """Get pending tasks (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM tasks 
                WHERE status = ? 
                ORDER BY priority DESC, created_at ASC 
                LIMIT ?
            """, (TaskStatus.PENDING.value, limit))
            
            return [Task.from_dict(dict(row)) for row in cursor.fetchall()]
    
    async def list_tasks(self, status: Optional[TaskStatus] = None, 
                        task_type: Optional[TaskType] = None,
                        limit: int = 100, offset: int = 0) -> List[Task]:
        """List tasks with optional filtering"""
        async with self._lock:
            return await asyncio.to_thread(
                self._list_tasks_sync, status, task_type, limit, offset
            )
    
    def _list_tasks_sync(self, status: Optional[TaskStatus] = None, 
                        task_type: Optional[TaskType] = None,
                        limit: int = 100, offset: int = 0) -> List[Task]:
        """List tasks (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            if task_type:
                query += " AND type = ?"
                params.append(task_type.value)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            return [Task.from_dict(dict(row)) for row in cursor.fetchall()]
    
    async def get_task_stats(self) -> Dict[str, int]:
        """Get task statistics"""
        async with self._lock:
            return await asyncio.to_thread(self._get_task_stats_sync)
    
    def _get_task_stats_sync(self) -> Dict[str, int]:
        """Get task statistics (synchronous)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM tasks 
                GROUP BY status
            """)
            
            stats = {status.value: 0 for status in TaskStatus}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]
            
            return stats
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up completed tasks older than specified days"""
        async with self._lock:
            return await asyncio.to_thread(self._cleanup_old_tasks_sync, days)
    
    def _cleanup_old_tasks_sync(self, days: int) -> int:
        """Clean up old tasks (synchronous)"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM tasks 
                WHERE status IN (?, ?, ?) 
                AND completed_at < ?
            """, (
                TaskStatus.SUCCESS.value, 
                TaskStatus.FAILED.value, 
                TaskStatus.CANCELLED.value,
                cutoff_date.isoformat()
            ))
            conn.commit()
            return cursor.rowcount

# global storage instance
task_storage = TaskStorage() 