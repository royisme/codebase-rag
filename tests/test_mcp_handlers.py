"""
Comprehensive Unit Tests for MCP Handler Functions

This module contains unit tests for all MCP handler functions:
- Knowledge handlers (5 functions)
- Code handlers (4 functions)
- Memory handlers (7 functions)
- Task handlers (6 functions)
- System handlers (3 functions)

All external dependencies are mocked to allow testing without Neo4j/Ollama.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
import asyncio

# Import handlers
from mcp_tools.knowledge_handlers import (
    handle_query_knowledge,
    handle_search_similar_nodes,
    handle_add_document,
    handle_add_file,
    handle_add_directory,
)
from mcp_tools.code_handlers import (
    handle_code_graph_ingest_repo,
    handle_code_graph_related,
    handle_code_graph_impact,
    handle_context_pack,
)
from mcp_tools.memory_handlers import (
    handle_add_memory,
    handle_search_memories,
    handle_get_memory,
    handle_update_memory,
    handle_delete_memory,
    handle_supersede_memory,
    handle_get_project_summary,
)
from mcp_tools.task_handlers import (
    handle_get_task_status,
    handle_watch_task,
    handle_watch_tasks,
    handle_list_tasks,
    handle_cancel_task,
    handle_get_queue_stats,
)
from mcp_tools.system_handlers import (
    handle_get_graph_schema,
    handle_get_statistics,
    handle_clear_knowledge_base,
)


# ============================================================================
# Knowledge Handler Tests
# ============================================================================

class TestKnowledgeHandlers:
    """Test suite for knowledge base handler functions"""

    @pytest.mark.asyncio
    async def test_handle_query_knowledge_success(self, mock_knowledge_service):
        """Test successful knowledge query with hybrid mode"""
        mock_knowledge_service.query.return_value = {
            "success": True,
            "answer": "Test response",
            "source_nodes": [{"text": "source 1"}]
        }

        result = await handle_query_knowledge(
            args={"question": "test question", "mode": "hybrid"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        assert result["answer"] == "Test response"
        assert len(result["source_nodes"]) == 1
        mock_knowledge_service.query.assert_called_once_with(
            question="test question",
            mode="hybrid"
        )

    @pytest.mark.asyncio
    async def test_handle_query_knowledge_default_mode(self, mock_knowledge_service):
        """Test knowledge query with default mode (hybrid)"""
        mock_knowledge_service.query.return_value = {
            "success": True,
            "answer": "Response"
        }

        result = await handle_query_knowledge(
            args={"question": "test"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        mock_knowledge_service.query.assert_called_once_with(
            question="test",
            mode="hybrid"
        )

    @pytest.mark.asyncio
    async def test_handle_search_similar_nodes_success(self, mock_knowledge_service):
        """Test successful similar nodes search"""
        mock_knowledge_service.search_similar_nodes.return_value = {
            "success": True,
            "results": [
                {"text": "result 1", "score": 0.95},
                {"text": "result 2", "score": 0.85}
            ]
        }

        result = await handle_search_similar_nodes(
            args={"query": "test query", "top_k": 10},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        assert len(result["results"]) == 2
        mock_knowledge_service.search_similar_nodes.assert_called_once_with(
            query="test query",
            top_k=10
        )

    @pytest.mark.asyncio
    async def test_handle_search_similar_nodes_default_top_k(self, mock_knowledge_service):
        """Test similar nodes search with default top_k"""
        mock_knowledge_service.search_similar_nodes.return_value = {
            "success": True,
            "results": []
        }

        result = await handle_search_similar_nodes(
            args={"query": "test"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        mock_knowledge_service.search_similar_nodes.assert_called_once_with(
            query="test",
            top_k=10
        )

    @pytest.mark.asyncio
    async def test_handle_add_document_small_sync(self, mock_knowledge_service, mock_submit_document_task):
        """Test adding small document (<10KB) - synchronous processing"""
        mock_knowledge_service.add_document.return_value = {
            "success": True,
            "message": "Document added"
        }

        small_content = "x" * 5000  # 5KB
        result = await handle_add_document(
            args={
                "content": small_content,
                "title": "Small Doc",
                "metadata": {"key": "value"}
            },
            knowledge_service=mock_knowledge_service,
            submit_document_processing_task=mock_submit_document_task
        )

        assert result["success"] is True
        assert "async" not in result or result["async"] is False
        mock_knowledge_service.add_document.assert_called_once_with(
            content=small_content,
            title="Small Doc",
            metadata={"key": "value"}
        )
        mock_submit_document_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_add_document_large_async(self, mock_knowledge_service, mock_submit_document_task):
        """Test adding large document (>=10KB) - asynchronous processing"""
        mock_submit_document_task.return_value = "task-123"

        large_content = "x" * 15000  # 15KB
        result = await handle_add_document(
            args={
                "content": large_content,
                "title": "Large Doc"
            },
            knowledge_service=mock_knowledge_service,
            submit_document_processing_task=mock_submit_document_task
        )

        assert result["success"] is True
        assert result["async"] is True
        assert result["task_id"] == "task-123"
        assert "queued" in result["message"].lower()
        mock_knowledge_service.add_document.assert_not_called()
        mock_submit_document_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_add_file_success(self, mock_knowledge_service):
        """Test successful file addition"""
        mock_knowledge_service.add_file.return_value = {
            "success": True,
            "message": "File added"
        }

        result = await handle_add_file(
            args={"file_path": "/path/to/file.txt"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        mock_knowledge_service.add_file.assert_called_once_with("/path/to/file.txt")

    @pytest.mark.asyncio
    async def test_handle_add_directory_success(self, mock_submit_directory_task):
        """Test adding directory - always async"""
        mock_submit_directory_task.return_value = "task-456"

        result = await handle_add_directory(
            args={"directory_path": "/path/to/dir", "recursive": True},
            submit_directory_processing_task=mock_submit_directory_task
        )

        assert result["success"] is True
        assert result["async"] is True
        assert result["task_id"] == "task-456"
        mock_submit_directory_task.assert_called_once_with(
            directory_path="/path/to/dir",
            recursive=True
        )

    @pytest.mark.asyncio
    async def test_handle_add_directory_default_recursive(self, mock_submit_directory_task):
        """Test adding directory with default recursive=True"""
        mock_submit_directory_task.return_value = "task-789"

        result = await handle_add_directory(
            args={"directory_path": "/path/to/dir"},
            submit_directory_processing_task=mock_submit_directory_task
        )

        assert result["success"] is True
        mock_submit_directory_task.assert_called_once_with(
            directory_path="/path/to/dir",
            recursive=True
        )


# ============================================================================
# Code Handler Tests
# ============================================================================

class TestCodeHandlers:
    """Test suite for code graph handler functions"""

    @pytest.mark.asyncio
    async def test_handle_code_graph_ingest_repo_incremental_git(self, mock_code_ingestor, mock_git_utils):
        """Test incremental repo ingestion for git repository"""
        mock_git_utils.is_git_repo.return_value = True
        mock_ingestor_instance = AsyncMock()
        mock_ingestor_instance.ingest_repo_incremental.return_value = {
            "success": True,
            "files_processed": 10
        }
        mock_code_ingestor.return_value = mock_ingestor_instance

        result = await handle_code_graph_ingest_repo(
            args={
                "local_path": "/path/to/repo",
                "repo_url": "https://github.com/user/repo.git",
                "mode": "incremental"
            },
            get_code_ingestor=mock_code_ingestor,
            git_utils=mock_git_utils
        )

        assert result["success"] is True
        assert result["files_processed"] == 10
        mock_git_utils.is_git_repo.assert_called_once_with("/path/to/repo")
        mock_ingestor_instance.ingest_repo_incremental.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_code_graph_ingest_repo_full_mode(self, mock_code_ingestor, mock_git_utils):
        """Test full repo ingestion mode"""
        mock_git_utils.is_git_repo.return_value = True
        mock_ingestor_instance = AsyncMock()
        mock_ingestor_instance.ingest_repo.return_value = {
            "success": True,
            "files_processed": 20
        }
        mock_code_ingestor.return_value = mock_ingestor_instance

        result = await handle_code_graph_ingest_repo(
            args={
                "local_path": "/path/to/repo",
                "mode": "full"
            },
            get_code_ingestor=mock_code_ingestor,
            git_utils=mock_git_utils
        )

        assert result["success"] is True
        mock_ingestor_instance.ingest_repo.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_code_graph_ingest_repo_error(self, mock_code_ingestor, mock_git_utils):
        """Test repo ingestion error handling"""
        mock_git_utils.is_git_repo.side_effect = Exception("Git error")

        result = await handle_code_graph_ingest_repo(
            args={"local_path": "/bad/path"},
            get_code_ingestor=mock_code_ingestor,
            git_utils=mock_git_utils
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_code_graph_related_success(self, mock_graph_service, mock_ranker):
        """Test finding related files successfully"""
        mock_graph_service.fulltext_search.return_value = {
            "success": True,
            "nodes": [
                {"path": "file1.py", "score": 0.9},
                {"path": "file2.py", "score": 0.8}
            ]
        }
        mock_ranker.rank_files.return_value = [
            {"path": "file1.py", "score": 0.95, "ref": "ref://file1"},
            {"path": "file2.py", "score": 0.85, "ref": "ref://file2"}
        ]

        result = await handle_code_graph_related(
            args={"query": "authentication", "repo_id": "test-repo", "limit": 30},
            graph_service=mock_graph_service,
            ranker=mock_ranker
        )

        assert result["success"] is True
        assert len(result["nodes"]) == 2
        assert result["total_count"] == 2
        mock_graph_service.fulltext_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_code_graph_related_no_results(self, mock_graph_service, mock_ranker):
        """Test finding related files with no results"""
        mock_graph_service.fulltext_search.return_value = {
            "success": True,
            "nodes": []
        }

        result = await handle_code_graph_related(
            args={"query": "nonexistent", "repo_id": "test-repo"},
            graph_service=mock_graph_service,
            ranker=mock_ranker
        )

        assert result["success"] is True
        assert result["nodes"] == []
        assert result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_handle_code_graph_related_search_error(self, mock_graph_service, mock_ranker):
        """Test related files search error"""
        mock_graph_service.fulltext_search.return_value = {
            "success": False,
            "error": "Search failed"
        }

        result = await handle_code_graph_related(
            args={"query": "test", "repo_id": "test-repo"},
            graph_service=mock_graph_service,
            ranker=mock_ranker
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_code_graph_impact_success(self, mock_graph_service):
        """Test impact analysis successfully"""
        mock_graph_service.impact_analysis.return_value = {
            "success": True,
            "impacted_files": ["file1.py", "file2.py"],
            "depth": 2
        }

        result = await handle_code_graph_impact(
            args={"repo_id": "test-repo", "file_path": "main.py", "depth": 2},
            graph_service=mock_graph_service
        )

        assert result["success"] is True
        assert len(result["impacted_files"]) == 2
        mock_graph_service.impact_analysis.assert_called_once_with(
            repo_id="test-repo",
            file_path="main.py",
            depth=2
        )

    @pytest.mark.asyncio
    async def test_handle_code_graph_impact_error(self, mock_graph_service):
        """Test impact analysis error handling"""
        mock_graph_service.impact_analysis.side_effect = Exception("Analysis failed")

        result = await handle_code_graph_impact(
            args={"repo_id": "test-repo", "file_path": "main.py"},
            graph_service=mock_graph_service
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_context_pack_success(self, mock_pack_builder):
        """Test building context pack successfully"""
        mock_pack_builder.build_context_pack.return_value = {
            "success": True,
            "items": [
                {"kind": "file", "title": "main.py", "ref": "ref://main"},
                {"kind": "symbol", "title": "function_a", "ref": "ref://func_a"}
            ],
            "budget_used": 1200,
            "budget_limit": 1500
        }

        result = await handle_context_pack(
            args={
                "repo_id": "test-repo",
                "stage": "implement",
                "budget": 1500,
                "keywords": ["auth", "user"],
                "focus": "authentication"
            },
            pack_builder=mock_pack_builder
        )

        assert result["success"] is True
        assert len(result["items"]) == 2
        assert result["budget_used"] == 1200
        mock_pack_builder.build_context_pack.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_context_pack_error(self, mock_pack_builder):
        """Test context pack error handling"""
        mock_pack_builder.build_context_pack.side_effect = Exception("Pack failed")

        result = await handle_context_pack(
            args={"repo_id": "test-repo"},
            pack_builder=mock_pack_builder
        )

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# Memory Handler Tests
# ============================================================================

class TestMemoryHandlers:
    """Test suite for memory store handler functions"""

    @pytest.mark.asyncio
    async def test_handle_add_memory_success(self, mock_memory_store):
        """Test successfully adding a memory"""
        mock_memory_store.add_memory.return_value = {
            "success": True,
            "memory_id": "mem-123",
            "title": "Test Memory"
        }

        result = await handle_add_memory(
            args={
                "project_id": "test-project",
                "memory_type": "decision",
                "title": "Test Memory",
                "content": "Test content",
                "reason": "Test reason",
                "tags": ["test"],
                "importance": 0.8,
                "related_refs": []
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        assert result["memory_id"] == "mem-123"
        mock_memory_store.add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_add_memory_with_defaults(self, mock_memory_store):
        """Test adding memory with default importance"""
        mock_memory_store.add_memory.return_value = {
            "success": True,
            "memory_id": "mem-456"
        }

        result = await handle_add_memory(
            args={
                "project_id": "test-project",
                "memory_type": "note",
                "title": "Simple Note",
                "content": "Content"
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        # Verify default importance 0.5 was used
        call_args = mock_memory_store.add_memory.call_args
        assert call_args.kwargs["importance"] == 0.5

    @pytest.mark.asyncio
    async def test_handle_search_memories_success(self, mock_memory_store):
        """Test searching memories successfully"""
        mock_memory_store.search_memories.return_value = {
            "success": True,
            "memories": [
                {"id": "mem-1", "title": "Memory 1", "type": "decision"},
                {"id": "mem-2", "title": "Memory 2", "type": "preference"}
            ],
            "total_count": 2
        }

        result = await handle_search_memories(
            args={
                "project_id": "test-project",
                "query": "authentication",
                "memory_type": "decision",
                "tags": ["auth"],
                "min_importance": 0.7,
                "limit": 20
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        assert len(result["memories"]) == 2
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_handle_search_memories_default_params(self, mock_memory_store):
        """Test searching memories with default parameters"""
        mock_memory_store.search_memories.return_value = {
            "success": True,
            "memories": []
        }

        result = await handle_search_memories(
            args={"project_id": "test-project"},
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        call_args = mock_memory_store.search_memories.call_args
        assert call_args.kwargs["min_importance"] == 0.0
        assert call_args.kwargs["limit"] == 20

    @pytest.mark.asyncio
    async def test_handle_get_memory_success(self, mock_memory_store):
        """Test getting a specific memory"""
        mock_memory_store.get_memory.return_value = {
            "success": True,
            "memory": {
                "id": "mem-123",
                "title": "Test Memory",
                "content": "Content",
                "type": "decision"
            }
        }

        result = await handle_get_memory(
            args={"memory_id": "mem-123"},
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        assert result["memory"]["id"] == "mem-123"
        mock_memory_store.get_memory.assert_called_once_with("mem-123")

    @pytest.mark.asyncio
    async def test_handle_get_memory_not_found(self, mock_memory_store):
        """Test getting a non-existent memory"""
        mock_memory_store.get_memory.return_value = {
            "success": False,
            "error": "Memory not found"
        }

        result = await handle_get_memory(
            args={"memory_id": "nonexistent"},
            memory_store=mock_memory_store
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_update_memory_success(self, mock_memory_store):
        """Test updating a memory"""
        mock_memory_store.update_memory.return_value = {
            "success": True,
            "memory_id": "mem-123"
        }

        result = await handle_update_memory(
            args={
                "memory_id": "mem-123",
                "title": "Updated Title",
                "importance": 0.9
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        mock_memory_store.update_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_update_memory_partial(self, mock_memory_store):
        """Test partial memory update (only some fields)"""
        mock_memory_store.update_memory.return_value = {
            "success": True,
            "memory_id": "mem-123"
        }

        result = await handle_update_memory(
            args={
                "memory_id": "mem-123",
                "importance": 0.95  # Only update importance
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        call_args = mock_memory_store.update_memory.call_args
        assert call_args.kwargs["importance"] == 0.95

    @pytest.mark.asyncio
    async def test_handle_delete_memory_success(self, mock_memory_store):
        """Test deleting a memory (soft delete)"""
        mock_memory_store.delete_memory.return_value = {
            "success": True,
            "memory_id": "mem-123"
        }

        result = await handle_delete_memory(
            args={"memory_id": "mem-123"},
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        mock_memory_store.delete_memory.assert_called_once_with("mem-123")

    @pytest.mark.asyncio
    async def test_handle_supersede_memory_success(self, mock_memory_store):
        """Test superseding a memory with a new one"""
        mock_memory_store.supersede_memory.return_value = {
            "success": True,
            "old_memory_id": "mem-old",
            "new_memory_id": "mem-new"
        }

        result = await handle_supersede_memory(
            args={
                "old_memory_id": "mem-old",
                "new_memory_type": "decision",
                "new_title": "Updated Decision",
                "new_content": "New content",
                "new_reason": "Changed approach",
                "new_tags": ["updated"],
                "new_importance": 0.9
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        assert result["new_memory_id"] == "mem-new"
        mock_memory_store.supersede_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_get_project_summary_success(self, mock_memory_store):
        """Test getting project summary"""
        mock_memory_store.get_project_summary.return_value = {
            "success": True,
            "summary": {
                "total_memories": 25,
                "by_type": {
                    "decision": 10,
                    "preference": 5,
                    "experience": 5,
                    "convention": 3,
                    "plan": 2
                }
            }
        }

        result = await handle_get_project_summary(
            args={"project_id": "test-project"},
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        assert result["summary"]["total_memories"] == 25
        mock_memory_store.get_project_summary.assert_called_once_with("test-project")


# ============================================================================
# Task Handler Tests
# ============================================================================

class TestTaskHandlers:
    """Test suite for task management handler functions"""

    @pytest.mark.asyncio
    async def test_handle_get_task_status_found(self, mock_task_queue, mock_task_status):
        """Test getting status of an existing task"""
        mock_task = Mock()
        mock_task.task_id = "task-123"
        mock_task.status = mock_task_status.RUNNING
        mock_task.created_at = "2024-01-01T00:00:00"
        mock_task.result = None
        mock_task.error = None

        mock_task_queue.get_task.return_value = mock_task

        result = await handle_get_task_status(
            args={"task_id": "task-123"},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is True
        assert result["task_id"] == "task-123"
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_handle_get_task_status_not_found(self, mock_task_queue, mock_task_status):
        """Test getting status of non-existent task"""
        mock_task_queue.get_task.return_value = None

        result = await handle_get_task_status(
            args={"task_id": "nonexistent"},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_watch_task_completes(self, mock_task_queue, mock_task_status):
        """Test watching a task that completes successfully"""
        mock_task = Mock()
        mock_task.task_id = "task-123"
        mock_task.status = mock_task_status.COMPLETED
        mock_task.result = {"success": True}
        mock_task.error = None

        mock_task_queue.get_task.return_value = mock_task

        result = await handle_watch_task(
            args={"task_id": "task-123", "timeout": 10, "poll_interval": 0.1},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is True
        assert result["final_status"] == "completed"
        assert "history" in result

    @pytest.mark.asyncio
    async def test_handle_watch_task_fails(self, mock_task_queue, mock_task_status):
        """Test watching a task that fails"""
        mock_task = Mock()
        mock_task.task_id = "task-123"
        mock_task.status = mock_task_status.FAILED
        mock_task.result = None
        mock_task.error = "Processing error"

        mock_task_queue.get_task.return_value = mock_task

        result = await handle_watch_task(
            args={"task_id": "task-123"},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is True
        assert result["final_status"] == "failed"
        assert result["error"] == "Processing error"

    @pytest.mark.asyncio
    async def test_handle_watch_task_not_found(self, mock_task_queue, mock_task_status):
        """Test watching a non-existent task"""
        mock_task_queue.get_task.return_value = None

        result = await handle_watch_task(
            args={"task_id": "nonexistent"},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_watch_tasks_all_complete(self, mock_task_queue, mock_task_status):
        """Test watching multiple tasks until all complete"""
        task1 = Mock()
        task1.status = mock_task_status.COMPLETED
        task1.result = {"success": True}
        task1.error = None

        task2 = Mock()
        task2.status = mock_task_status.COMPLETED
        task2.result = {"success": True}
        task2.error = None

        mock_task_queue.get_task.side_effect = [task1, task2]

        result = await handle_watch_tasks(
            args={"task_ids": ["task-1", "task-2"], "poll_interval": 0.1},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is True
        assert len(result["tasks"]) == 2

    @pytest.mark.asyncio
    async def test_handle_list_tasks_all(self, mock_task_queue):
        """Test listing all tasks"""
        mock_task1 = Mock()
        mock_task1.task_id = "task-1"
        mock_task1.status = Mock(value="completed")
        mock_task1.created_at = "2024-01-01"
        mock_task1.result = {"success": True}
        mock_task1.error = None

        mock_task2 = Mock()
        mock_task2.task_id = "task-2"
        mock_task2.status = Mock(value="running")
        mock_task2.created_at = "2024-01-02"
        mock_task2.result = None
        mock_task2.error = None

        mock_task_queue.get_all_tasks.return_value = [mock_task1, mock_task2]

        result = await handle_list_tasks(
            args={},
            task_queue=mock_task_queue
        )

        assert result["success"] is True
        assert len(result["tasks"]) == 2
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_handle_list_tasks_filtered(self, mock_task_queue):
        """Test listing tasks with status filter"""
        mock_task1 = Mock()
        mock_task1.task_id = "task-1"
        mock_task1.status = Mock(value="completed")
        mock_task1.created_at = "2024-01-01"
        mock_task1.result = {"success": True}
        mock_task1.error = None

        mock_task2 = Mock()
        mock_task2.task_id = "task-2"
        mock_task2.status = Mock(value="running")
        mock_task2.created_at = "2024-01-02"
        mock_task2.result = None
        mock_task2.error = None

        mock_task_queue.get_all_tasks.return_value = [mock_task1, mock_task2]

        result = await handle_list_tasks(
            args={"status_filter": "completed"},
            task_queue=mock_task_queue
        )

        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_handle_cancel_task_success(self, mock_task_queue):
        """Test successfully cancelling a task"""
        mock_task_queue.cancel_task.return_value = True

        result = await handle_cancel_task(
            args={"task_id": "task-123"},
            task_queue=mock_task_queue
        )

        assert result["success"] is True
        assert result["task_id"] == "task-123"
        mock_task_queue.cancel_task.assert_called_once_with("task-123")

    @pytest.mark.asyncio
    async def test_handle_cancel_task_failure(self, mock_task_queue):
        """Test failing to cancel a task"""
        mock_task_queue.cancel_task.return_value = False

        result = await handle_cancel_task(
            args={"task_id": "task-123"},
            task_queue=mock_task_queue
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_handle_get_queue_stats(self, mock_task_queue):
        """Test getting queue statistics"""
        mock_task_queue.get_stats.return_value = {
            "pending": 5,
            "running": 2,
            "completed": 10,
            "failed": 1
        }

        result = await handle_get_queue_stats(
            args={},
            task_queue=mock_task_queue
        )

        assert result["success"] is True
        assert result["stats"]["pending"] == 5
        assert result["stats"]["running"] == 2
        assert result["stats"]["completed"] == 10
        assert result["stats"]["failed"] == 1


# ============================================================================
# System Handler Tests
# ============================================================================

class TestSystemHandlers:
    """Test suite for system handler functions"""

    @pytest.mark.asyncio
    async def test_handle_get_graph_schema(self, mock_knowledge_service):
        """Test getting graph schema"""
        mock_knowledge_service.get_graph_schema.return_value = {
            "success": True,
            "node_labels": ["Document", "Entity"],
            "relationship_types": ["RELATES_TO", "CONTAINS"],
            "node_count": 100
        }

        result = await handle_get_graph_schema(
            args={},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        assert len(result["node_labels"]) == 2
        assert len(result["relationship_types"]) == 2

    @pytest.mark.asyncio
    async def test_handle_get_statistics(self, mock_knowledge_service):
        """Test getting knowledge base statistics"""
        mock_knowledge_service.get_statistics.return_value = {
            "success": True,
            "node_count": 150,
            "relationship_count": 250,
            "document_count": 50
        }

        result = await handle_get_statistics(
            args={},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        assert result["node_count"] == 150
        assert result["relationship_count"] == 250

    @pytest.mark.asyncio
    async def test_handle_clear_knowledge_base_no_confirmation(self, mock_knowledge_service):
        """Test clearing knowledge base without confirmation"""
        result = await handle_clear_knowledge_base(
            args={"confirmation": "no"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is False
        assert "confirmation required" in result["error"].lower()
        mock_knowledge_service.clear_knowledge_base.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_clear_knowledge_base_with_confirmation(self, mock_knowledge_service):
        """Test clearing knowledge base with confirmation"""
        mock_knowledge_service.clear_knowledge_base.return_value = {
            "success": True,
            "message": "Knowledge base cleared"
        }

        result = await handle_clear_knowledge_base(
            args={"confirmation": "yes"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        mock_knowledge_service.clear_knowledge_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_clear_knowledge_base_missing_confirmation(self, mock_knowledge_service):
        """Test clearing knowledge base without confirmation arg"""
        result = await handle_clear_knowledge_base(
            args={},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is False
        assert "confirmation" in result["error"].lower()
