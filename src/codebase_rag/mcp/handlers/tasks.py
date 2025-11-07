"""
Task Management Handler Functions for MCP Server v2

This module contains handlers for task queue operations:
- Get task status
- Watch single task
- Watch multiple tasks
- List tasks
- Cancel task
- Get queue statistics
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
from loguru import logger


async def handle_get_task_status(args: Dict, task_queue, TaskStatus) -> Dict:
    """
    Get status of a specific task.

    Args:
        args: Arguments containing task_id
        task_queue: Task queue instance
        TaskStatus: TaskStatus enum

    Returns:
        Task status details
    """
    task_id = args["task_id"]
    task = await task_queue.get_task(task_id)

    if task:
        result = {
            "success": True,
            "task_id": task_id,
            "status": task.status.value,
            "created_at": task.created_at,
            "result": task.result,
            "error": task.error
        }
    else:
        result = {"success": False, "error": "Task not found"}

    logger.info(f"Task status: {task_id} - {task.status.value if task else 'not found'}")
    return result


async def handle_watch_task(args: Dict, task_queue, TaskStatus) -> Dict:
    """
    Monitor a task in real-time until completion.

    Args:
        args: Arguments containing task_id, timeout, poll_interval
        task_queue: Task queue instance
        TaskStatus: TaskStatus enum

    Returns:
        Final task status with history
    """
    task_id = args["task_id"]
    timeout = args.get("timeout", 300)
    poll_interval = args.get("poll_interval", 2)

    start_time = asyncio.get_event_loop().time()
    history = []

    while True:
        task = await task_queue.get_task(task_id)

        if not task:
            return {"success": False, "error": "Task not found"}

        current = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": task.status.value
        }
        history.append(current)

        # Check if complete
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            result = {
                "success": True,
                "task_id": task_id,
                "final_status": task.status.value,
                "result": task.result,
                "error": task.error,
                "history": history
            }
            logger.info(f"Task completed: {task_id} - {task.status.value}")
            return result

        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            result = {
                "success": False,
                "error": "Timeout",
                "task_id": task_id,
                "current_status": task.status.value,
                "history": history
            }
            logger.warning(f"Task watch timeout: {task_id}")
            return result

        await asyncio.sleep(poll_interval)


async def handle_watch_tasks(args: Dict, task_queue, TaskStatus) -> Dict:
    """
    Monitor multiple tasks until all complete.

    Args:
        args: Arguments containing task_ids, timeout, poll_interval
        task_queue: Task queue instance
        TaskStatus: TaskStatus enum

    Returns:
        Status of all tasks
    """
    task_ids = args["task_ids"]
    timeout = args.get("timeout", 300)
    poll_interval = args.get("poll_interval", 2)

    start_time = asyncio.get_event_loop().time()
    results = {}

    while True:
        all_done = True

        for task_id in task_ids:
            if task_id in results:
                continue

            task = await task_queue.get_task(task_id)

            if not task:
                results[task_id] = {"status": "not_found"}
                continue

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                results[task_id] = {
                    "status": task.status.value,
                    "result": task.result,
                    "error": task.error
                }
            else:
                all_done = False

        if all_done:
            logger.info(f"All tasks completed: {len(task_ids)} tasks")
            return {"success": True, "tasks": results}

        if asyncio.get_event_loop().time() - start_time > timeout:
            logger.warning(f"Tasks watch timeout: {len(task_ids)} tasks")
            return {"success": False, "error": "Timeout", "tasks": results}

        await asyncio.sleep(poll_interval)


async def handle_list_tasks(args: Dict, task_queue) -> Dict:
    """
    List tasks with optional status filter.

    Args:
        args: Arguments containing status_filter, limit
        task_queue: Task queue instance

    Returns:
        List of tasks with metadata
    """
    status_filter = args.get("status_filter")
    limit = args.get("limit", 20)

    all_tasks = await task_queue.get_all_tasks()

    # Filter by status
    if status_filter:
        filtered = [t for t in all_tasks if t.status.value == status_filter]
    else:
        filtered = all_tasks

    # Limit
    limited = filtered[:limit]

    tasks_data = [
        {
            "task_id": t.task_id,
            "status": t.status.value,
            "created_at": t.created_at,
            "has_result": t.result is not None,
            "has_error": t.error is not None
        }
        for t in limited
    ]

    result = {
        "success": True,
        "tasks": tasks_data,
        "total_count": len(filtered),
        "returned_count": len(tasks_data)
    }

    logger.info(f"List tasks: {len(tasks_data)} tasks")
    return result


async def handle_cancel_task(args: Dict, task_queue) -> Dict:
    """
    Cancel a pending or running task.

    Args:
        args: Arguments containing task_id
        task_queue: Task queue instance

    Returns:
        Cancellation result
    """
    task_id = args["task_id"]
    success = await task_queue.cancel_task(task_id)

    result = {
        "success": success,
        "task_id": task_id,
        "message": "Task cancelled" if success else "Failed to cancel task"
    }

    logger.info(f"Cancel task: {task_id} - {'success' if success else 'failed'}")
    return result


async def handle_get_queue_stats(args: Dict, task_queue) -> Dict:
    """
    Get task queue statistics.

    Args:
        args: Arguments (none required)
        task_queue: Task queue instance

    Returns:
        Queue statistics with counts by status
    """
    stats = await task_queue.get_stats()
    logger.info(f"Queue stats: {stats}")
    return {"success": True, "stats": stats}
