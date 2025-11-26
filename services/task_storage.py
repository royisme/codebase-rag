"""
task persistent storage based on SQLite
ensures task data is not lost, supports task state recovery after service restart
"""

import sqlite3
import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger
from sqlalchemy import text

from config import settings
from database.session import sync_engine, async_engine

from .task_queue import TaskResult, TaskStatus


def utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_aware(dt_value: Optional[datetime]) -> Optional[datetime]:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value

class TaskType(Enum):
    DOCUMENT_PROCESSING = "document_processing"
    SCHEMA_PARSING = "schema_parsing"
    KNOWLEDGE_GRAPH_CONSTRUCTION = "knowledge_graph_construction"
    BATCH_PROCESSING = "batch_processing"
    KNOWLEDGE_SOURCE_SYNC = "knowledge_source_sync"

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

        def _parse_datetime(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return ensure_aware(value)
            try:
                parsed = datetime.fromisoformat(value)
                return ensure_aware(parsed)
            except (ValueError, TypeError):
                logger.warning("Unexpected datetime format for task %s: %s", data['id'], value)
                return None
        
        return cls(
            id=data['id'],
            type=TaskType(data['type']),
            status=TaskStatus(data['status']),
            payload=payload,
            created_at=_parse_datetime(data['created_at']) or utcnow(),
            started_at=_parse_datetime(data.get('started_at')),
            completed_at=_parse_datetime(data.get('completed_at')),
            error_message=data['error_message'],
            progress=data['progress'],
            lock_id=data['lock_id'],
            priority=data['priority']
        )

class TaskStorage:
    """task persistent storage manager"""
    
    def __init__(self, db_path: str = "data/tasks.db"):
        self._use_sqlite = settings.db_driver_sync.lower().startswith("sqlite")
        if self._use_sqlite:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._engine = None
        else:
            self.db_path = None
            self._engine = sync_engine
        self._lock = asyncio.Lock()
        self._init_database()
    
    def _init_database(self):
        """initialize database table structure"""
        if self._use_sqlite:
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
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_lock_id ON tasks(lock_id)")
                conn.commit()
            logger.info(f"Task storage initialized at {self.db_path}")
        else:
            with self._engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id VARCHAR(128) PRIMARY KEY,
                        type VARCHAR(64) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                        started_at TIMESTAMP WITHOUT TIME ZONE,
                        completed_at TIMESTAMP WITHOUT TIME ZONE,
                        error_message TEXT,
                        progress DOUBLE PRECISION DEFAULT 0.0,
                        lock_id VARCHAR(128),
                        priority INTEGER DEFAULT 0
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_lock_id ON tasks(lock_id)"))
            logger.info("Task storage initialized using SQL database")
    
    async def create_task(self, task_type: TaskType, payload: Dict[str, Any], priority: int = 0) -> Task:
        """Create a new task"""
        async with self._lock:
            task = Task(
                id=str(uuid.uuid4()),
                type=task_type,
                status=TaskStatus.PENDING,
                payload=payload,
                created_at=utcnow(),
                priority=priority
            )
            
            await asyncio.to_thread(self._insert_task, task)
            logger.info(f"Created task {task.id} of type {task_type.value}")
            return task
    
    def _insert_task(self, task: Task):
        """Insert task into database (synchronous)"""
        task_data = task.to_dict()
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
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
        else:
            payload = task_data['payload']
            with self._engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO tasks (
                            id, type, status, payload, created_at, started_at,
                            completed_at, error_message, progress, lock_id, priority
                        )
                        VALUES (
                            :id, :type, :status, :payload, :created_at, :started_at,
                            :completed_at, :error_message, :progress, :lock_id, :priority
                        )
                    """),
                    {
                        **task_data,
                        "payload": payload,
                    },
                )
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        async with self._lock:
            return await asyncio.to_thread(self._get_task_sync, task_id)
    
    def _get_task_sync(self, task_id: str) -> Optional[Task]:
        """Get task by ID (synchronous)"""
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
        else:
            with self._engine.connect() as conn:
                row = conn.execute(
                    text("SELECT * FROM tasks WHERE id = :id"),
                    {"id": task_id},
                ).mappings().fetchone()
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
        now_iso = utcnow().isoformat()
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                updates = ["status = ?"]
                params = [status.value]

                if status == TaskStatus.PROCESSING:
                    updates.append("started_at = ?")
                    params.append(now_iso)
                elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    updates.append("completed_at = ?")
                    params.append(now_iso)

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
        else:
            updates = ["status = :status"]
            params = {"status": status.value, "id": task_id}

            if status == TaskStatus.PROCESSING:
                updates.append("started_at = :started_at")
                params["started_at"] = now_iso
            elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                updates.append("completed_at = :completed_at")
                params["completed_at"] = now_iso

            if error_message is not None:
                updates.append("error_message = :error_message")
                params["error_message"] = error_message

            if progress is not None:
                updates.append("progress = :progress")
                params["progress"] = progress

            with self._engine.begin() as conn:
                result = conn.execute(
                    text(f"UPDATE tasks SET {', '.join(updates)} WHERE id = :id"),
                    params,
                )
                return result.rowcount > 0
    
    async def acquire_task_lock(self, task_id: str, lock_id: str) -> bool:
        """Acquire a lock on a task"""
        async with self._lock:
            return await asyncio.to_thread(self._acquire_task_lock_sync, task_id, lock_id)
    
    def _acquire_task_lock_sync(self, task_id: str, lock_id: str) -> bool:
        """Acquire task lock (synchronous)"""
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE tasks SET lock_id = ? WHERE id = ? AND (lock_id IS NULL OR lock_id = ?)",
                    (lock_id, task_id, lock_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        else:
            with self._engine.begin() as conn:
                result = conn.execute(
                    text("""
                        UPDATE tasks
                        SET lock_id = :lock_id
                        WHERE id = :id AND (lock_id IS NULL OR lock_id = :lock_id_cond)
                    """),
                    {"lock_id": lock_id, "lock_id_cond": lock_id, "id": task_id},
                )
                return result.rowcount > 0
    
    async def release_task_lock(self, task_id: str, lock_id: str) -> bool:
        """Release a task lock"""
        async with self._lock:
            return await asyncio.to_thread(self._release_task_lock_sync, task_id, lock_id)
    
    def _release_task_lock_sync(self, task_id: str, lock_id: str) -> bool:
        """Release task lock (synchronous)"""
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE tasks SET lock_id = NULL WHERE id = ? AND lock_id = ?",
                    (task_id, lock_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        else:
            with self._engine.begin() as conn:
                result = conn.execute(
                    text("""
                        UPDATE tasks
                        SET lock_id = NULL
                        WHERE id = :id AND lock_id = :lock_id
                    """),
                    {"id": task_id, "lock_id": lock_id},
                )
                return result.rowcount > 0
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """Get pending tasks ordered by priority and creation time"""
        async with self._lock:
            return await asyncio.to_thread(self._get_pending_tasks_sync, limit)
    
    def _get_pending_tasks_sync(self, limit: int) -> List[Task]:
        """Get pending tasks (synchronous)"""
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM tasks 
                    WHERE status = ? 
                    ORDER BY priority DESC, created_at ASC 
                    LIMIT ?
                """, (TaskStatus.PENDING.value, limit))
                rows = cursor.fetchall()
        else:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text("""
                        SELECT * FROM tasks
                        WHERE status = :status
                        ORDER BY priority DESC, created_at ASC
                        LIMIT :limit
                    """),
                    {"status": TaskStatus.PENDING.value, "limit": limit},
                ).mappings().all()
        return [Task.from_dict(dict(row)) for row in rows]
    
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
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM tasks WHERE 1=1"
                params: List[Any] = []

                if status:
                    query += " AND status = ?"
                    params.append(status.value)

                if task_type:
                    query += " AND type = ?"
                    params.append(task_type.value)

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
        else:
            clauses = ["1=1"]
            params = {"limit": limit, "offset": offset}
            if status:
                clauses.append("status = :status")
                params["status"] = status.value
            if task_type:
                clauses.append("type = :type")
                params["type"] = task_type.value

            sql = f"""
                SELECT * FROM tasks
                WHERE {' AND '.join(clauses)}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """
            with self._engine.connect() as conn:
                rows = conn.execute(text(sql), params).mappings().all()

        return [Task.from_dict(dict(row)) for row in rows]
    
    async def get_task_stats(self) -> Dict[str, int]:
        """Get task statistics"""
        async with self._lock:
            return await asyncio.to_thread(self._get_task_stats_sync)
    
    def _get_task_stats_sync(self) -> Dict[str, int]:
        """Get task statistics (synchronous)"""
        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM tasks 
                    GROUP BY status
                """)
                rows = cursor.fetchall()
        else:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text("""
                        SELECT status, COUNT(*) AS count
                        FROM tasks
                        GROUP BY status
                    """)
                ).fetchall()

        stats = {status.value: 0 for status in TaskStatus}
        for row in rows:
            status_key = row[0] if self._use_sqlite else row["status"]
            count_val = row[1] if self._use_sqlite else row["count"]
            stats[status_key] = count_val
        return stats
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up completed tasks older than specified days"""
        async with self._lock:
            return await asyncio.to_thread(self._cleanup_old_tasks_sync, days)
    
    def _cleanup_old_tasks_sync(self, days: int) -> int:
        """Clean up old tasks (synchronous)"""
        cutoff_date = utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        if self._use_sqlite:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM tasks 
                    WHERE status IN (?, ?, ?) 
                    AND completed_at < ?
                """, (
                    TaskStatus.SUCCESS.value, 
                    TaskStatus.FAILED.value, 
                    TaskStatus.CANCELLED.value,
                    cutoff_iso
                ))
                conn.commit()
                return cursor.rowcount
        else:
            with self._engine.begin() as conn:
                result = conn.execute(
                    text("""
                        DELETE FROM tasks
                        WHERE status IN (:success, :failed, :cancelled)
                        AND completed_at < :cutoff
                    """),
                    {
                        "success": TaskStatus.SUCCESS.value,
                        "failed": TaskStatus.FAILED.value,
                        "cancelled": TaskStatus.CANCELLED.value,
                        "cutoff": cutoff_iso,
                    },
                )
                return result.rowcount

# global storage instance
task_storage = TaskStorage() 
