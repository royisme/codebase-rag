"""
Integration Tests for MCP Server

This module contains integration tests for the complete MCP server:
- Tool definitions and listing
- Tool execution routing
- Resource handling
- Prompt handling
- Server initialization

These tests mock all external dependencies but test the complete MCP server flow.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json

from src.codebase_rag.mcp.tools import get_tool_definitions
from src.codebase_rag.mcp.resources import get_resource_list, read_resource_content
from src.codebase_rag.mcp.prompts import get_prompt_list, get_prompt_content


class TestToolDefinitions:
    """Test suite for tool definitions"""

    def test_get_tool_definitions_count(self):
        """Test that all 30 tools are defined"""
        tools = get_tool_definitions()

        assert len(tools) == 30, "Should have exactly 30 tools"

    def test_get_tool_definitions_knowledge_tools(self):
        """Test knowledge base tool definitions"""
        tools = get_tool_definitions()
        tool_names = [t.name for t in tools]

        # Knowledge tools
        assert "query_knowledge" in tool_names
        assert "search_similar_nodes" in tool_names
        assert "add_document" in tool_names
        assert "add_file" in tool_names
        assert "add_directory" in tool_names

    def test_get_tool_definitions_code_tools(self):
        """Test code graph tool definitions"""
        tools = get_tool_definitions()
        tool_names = [t.name for t in tools]

        # Code tools
        assert "code_graph_ingest_repo" in tool_names
        assert "code_graph_related" in tool_names
        assert "code_graph_impact" in tool_names
        assert "context_pack" in tool_names

    def test_get_tool_definitions_memory_tools(self):
        """Test memory store tool definitions"""
        tools = get_tool_definitions()
        tool_names = [t.name for t in tools]

        # Manual memory tools
        assert "add_memory" in tool_names
        assert "search_memories" in tool_names
        assert "get_memory" in tool_names
        assert "update_memory" in tool_names
        assert "delete_memory" in tool_names
        assert "supersede_memory" in tool_names
        assert "get_project_summary" in tool_names
        
        # Automatic extraction tools (v0.7)
        assert "extract_from_conversation" in tool_names
        assert "extract_from_git_commit" in tool_names
        assert "extract_from_code_comments" in tool_names
        assert "suggest_memory_from_query" in tool_names
        assert "batch_extract_from_repository" in tool_names

    def test_get_tool_definitions_task_tools(self):
        """Test task management tool definitions"""
        tools = get_tool_definitions()
        tool_names = [t.name for t in tools]

        # Task tools
        assert "get_task_status" in tool_names
        assert "watch_task" in tool_names
        assert "watch_tasks" in tool_names
        assert "list_tasks" in tool_names
        assert "cancel_task" in tool_names
        assert "get_queue_stats" in tool_names

    def test_get_tool_definitions_system_tools(self):
        """Test system tool definitions"""
        tools = get_tool_definitions()
        tool_names = [t.name for t in tools]

        # System tools
        assert "get_graph_schema" in tool_names
        assert "get_statistics" in tool_names
        assert "clear_knowledge_base" in tool_names

    def test_tool_definition_has_required_fields(self):
        """Test that all tools have required fields"""
        tools = get_tool_definitions()

        for tool in tools:
            assert hasattr(tool, 'name'), f"Tool missing name: {tool}"
            assert hasattr(tool, 'description'), f"Tool {tool.name} missing description"
            assert hasattr(tool, 'inputSchema'), f"Tool {tool.name} missing inputSchema"
            assert tool.name, f"Tool has empty name"
            assert tool.description, f"Tool {tool.name} has empty description"

    def test_tool_input_schemas_valid(self):
        """Test that all tool input schemas are valid"""
        tools = get_tool_definitions()

        for tool in tools:
            schema = tool.inputSchema
            assert isinstance(schema, dict), f"Tool {tool.name} has invalid schema type"
            assert "type" in schema, f"Tool {tool.name} schema missing type"
            assert schema["type"] == "object", f"Tool {tool.name} schema should be object type"
            assert "properties" in schema, f"Tool {tool.name} schema missing properties"

    def test_query_knowledge_tool_schema(self):
        """Test query_knowledge tool has correct schema"""
        tools = get_tool_definitions()
        query_tool = next(t for t in tools if t.name == "query_knowledge")

        schema = query_tool.inputSchema
        assert "question" in schema["properties"]
        assert "mode" in schema["properties"]
        assert "question" in schema["required"]

        mode_schema = schema["properties"]["mode"]
        assert mode_schema["type"] == "string"
        assert "enum" in mode_schema
        assert "hybrid" in mode_schema["enum"]

    def test_add_memory_tool_schema(self):
        """Test add_memory tool has correct schema"""
        tools = get_tool_definitions()
        add_memory_tool = next(t for t in tools if t.name == "add_memory")

        schema = add_memory_tool.inputSchema
        required_fields = ["project_id", "memory_type", "title", "content"]

        for field in required_fields:
            assert field in schema["properties"], f"Missing field: {field}"
            assert field in schema["required"], f"Field not required: {field}"


class TestResourceHandling:
    """Test suite for resource handling"""

    def test_get_resource_list(self):
        """Test getting list of resources"""
        resources = get_resource_list()

        assert len(resources) == 2
        resource_uris = [str(r.uri) for r in resources]
        assert "knowledge://config" in resource_uris
        assert "knowledge://status" in resource_uris

    def test_resource_list_has_required_fields(self):
        """Test that all resources have required fields"""
        resources = get_resource_list()

        for resource in resources:
            assert hasattr(resource, 'uri')
            assert hasattr(resource, 'name')
            assert hasattr(resource, 'mimeType')
            assert hasattr(resource, 'description')
            assert resource.uri
            assert resource.name
            assert resource.mimeType
            assert resource.description

    @pytest.mark.asyncio
    async def test_read_config_resource(self, mock_knowledge_service, mock_task_queue, mock_settings):
        """Test reading config resource"""
        mock_get_model_info = Mock(return_value={"model": "test-model"})

        content = await read_resource_content(
            uri="knowledge://config",
            knowledge_service=mock_knowledge_service,
            task_queue=mock_task_queue,
            settings=mock_settings,
            get_current_model_info=mock_get_model_info,
            service_initialized=True
        )

        # Should return valid JSON
        config = json.loads(content)
        assert "llm_provider" in config
        assert "embedding_provider" in config
        assert "neo4j_uri" in config
        assert "model_info" in config

    @pytest.mark.asyncio
    async def test_read_status_resource(self, mock_knowledge_service, mock_task_queue, mock_settings):
        """Test reading status resource"""
        mock_knowledge_service.get_statistics.return_value = {
            "node_count": 100,
            "document_count": 50
        }
        mock_task_queue.get_stats.return_value = {
            "pending": 5,
            "running": 2,
            "completed": 10
        }
        mock_get_model_info = Mock(return_value={})

        content = await read_resource_content(
            uri="knowledge://status",
            knowledge_service=mock_knowledge_service,
            task_queue=mock_task_queue,
            settings=mock_settings,
            get_current_model_info=mock_get_model_info,
            service_initialized=True
        )

        # Should return valid JSON
        status = json.loads(content)
        assert "knowledge_base" in status
        assert "task_queue" in status
        assert "services_initialized" in status
        assert status["services_initialized"] is True

    @pytest.mark.asyncio
    async def test_read_unknown_resource(self, mock_knowledge_service, mock_task_queue, mock_settings):
        """Test reading unknown resource raises error"""
        mock_get_model_info = Mock(return_value={})

        with pytest.raises(ValueError, match="Unknown resource"):
            await read_resource_content(
                uri="knowledge://unknown",
                knowledge_service=mock_knowledge_service,
                task_queue=mock_task_queue,
                settings=mock_settings,
                get_current_model_info=mock_get_model_info,
                service_initialized=True
            )


class TestPromptHandling:
    """Test suite for prompt handling"""

    def test_get_prompt_list(self):
        """Test getting list of prompts"""
        prompts = get_prompt_list()

        assert len(prompts) == 1
        assert prompts[0].name == "suggest_queries"
        assert prompts[0].description
        assert len(prompts[0].arguments) == 1
        assert prompts[0].arguments[0].name == "domain"

    def test_get_prompt_content_general_domain(self):
        """Test getting prompt content for general domain"""
        messages = get_prompt_content("suggest_queries", {"domain": "general"})

        assert len(messages) == 1
        message = messages[0]
        assert message.role == "user"

        content_text = message.content.text
        assert "general" in content_text
        assert "main components" in content_text
        assert "hybrid" in content_text

    def test_get_prompt_content_code_domain(self):
        """Test getting prompt content for code domain"""
        messages = get_prompt_content("suggest_queries", {"domain": "code"})

        assert len(messages) == 1
        message = messages[0]

        content_text = message.content.text
        assert "code" in content_text
        assert "Python functions" in content_text

    def test_get_prompt_content_memory_domain(self):
        """Test getting prompt content for memory domain"""
        messages = get_prompt_content("suggest_queries", {"domain": "memory"})

        assert len(messages) == 1
        message = messages[0]

        content_text = message.content.text
        assert "memory" in content_text
        assert "decisions" in content_text

    def test_get_prompt_content_default_domain(self):
        """Test getting prompt content with no domain defaults to general"""
        messages = get_prompt_content("suggest_queries", {})

        assert len(messages) == 1
        message = messages[0]

        content_text = message.content.text
        assert "general" in content_text

    def test_get_prompt_content_unknown_prompt(self):
        """Test getting unknown prompt raises error"""
        with pytest.raises(ValueError, match="Unknown prompt"):
            get_prompt_content("nonexistent_prompt", {})


class TestToolExecutionRouting:
    """Test suite for tool execution routing patterns"""

    @pytest.mark.asyncio
    async def test_knowledge_tool_routing(self, mock_knowledge_service):
        """Test that knowledge tools route to correct service"""
        from src.codebase_rag.mcp.handlers.knowledge import handle_query_knowledge

        mock_knowledge_service.query.return_value = {
            "success": True,
            "answer": "Test"
        }

        result = await handle_query_knowledge(
            args={"question": "test"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        mock_knowledge_service.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_tool_routing(self, mock_memory_store):
        """Test that memory tools route to correct service"""
        from src.codebase_rag.mcp.handlers.memory import handle_add_memory

        mock_memory_store.add_memory.return_value = {
            "success": True,
            "memory_id": "mem-123"
        }

        result = await handle_add_memory(
            args={
                "project_id": "test",
                "memory_type": "note",
                "title": "Test",
                "content": "Content"
            },
            memory_store=mock_memory_store
        )

        assert result["success"] is True
        mock_memory_store.add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_tool_routing(self, mock_task_queue, mock_task_status):
        """Test that task tools route to correct service"""
        from src.codebase_rag.mcp.handlers.tasks import handle_get_queue_stats

        mock_task_queue.get_stats.return_value = {
            "pending": 5,
            "running": 2
        }

        result = await handle_get_queue_stats(
            args={},
            task_queue=mock_task_queue
        )

        assert result["success"] is True
        mock_task_queue.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_tool_routing(self, mock_knowledge_service):
        """Test that system tools route to correct service"""
        from src.codebase_rag.mcp.handlers.system import handle_get_statistics

        mock_knowledge_service.get_statistics.return_value = {
            "success": True,
            "node_count": 100
        }

        result = await handle_get_statistics(
            args={},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is True
        mock_knowledge_service.get_statistics.assert_called_once()


class TestErrorHandlingPatterns:
    """Test suite for error handling patterns across tools"""

    @pytest.mark.asyncio
    async def test_knowledge_service_error(self, mock_knowledge_service):
        """Test knowledge service error handling"""
        from src.codebase_rag.mcp.handlers.knowledge import handle_query_knowledge

        mock_knowledge_service.query.return_value = {
            "success": False,
            "error": "Service unavailable"
        }

        result = await handle_query_knowledge(
            args={"question": "test"},
            knowledge_service=mock_knowledge_service
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_memory_store_error(self, mock_memory_store):
        """Test memory store error handling"""
        from src.codebase_rag.mcp.handlers.memory import handle_get_memory

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
    async def test_task_queue_error(self, mock_task_queue, mock_task_status):
        """Test task queue error handling"""
        from src.codebase_rag.mcp.handlers.tasks import handle_get_task_status

        mock_task_queue.get_task.return_value = None

        result = await handle_get_task_status(
            args={"task_id": "nonexistent"},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_code_handler_exception(self, mock_code_ingestor, mock_git_utils):
        """Test code handler exception handling"""
        from src.codebase_rag.mcp.handlers.code import handle_code_graph_ingest_repo

        mock_git_utils.is_git_repo.side_effect = Exception("Git error")

        result = await handle_code_graph_ingest_repo(
            args={"local_path": "/bad/path"},
            get_code_ingestor=mock_code_ingestor,
            git_utils=mock_git_utils
        )

        assert result["success"] is False
        assert "error" in result


class TestAsyncTaskHandling:
    """Test suite for async task handling patterns"""

    @pytest.mark.asyncio
    async def test_large_document_async_processing(self, mock_knowledge_service, mock_submit_document_task):
        """Test large documents trigger async processing"""
        from src.codebase_rag.mcp.handlers.knowledge import handle_add_document

        mock_submit_document_task.return_value = "task-123"
        large_content = "x" * 15000  # 15KB

        result = await handle_add_document(
            args={"content": large_content},
            knowledge_service=mock_knowledge_service,
            submit_document_processing_task=mock_submit_document_task
        )

        assert result["success"] is True
        assert result["async"] is True
        assert result["task_id"] == "task-123"
        mock_submit_document_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_directory_always_async(self, mock_submit_directory_task):
        """Test directory processing always uses async"""
        from src.codebase_rag.mcp.handlers.knowledge import handle_add_directory

        mock_submit_directory_task.return_value = "task-456"

        result = await handle_add_directory(
            args={"directory_path": "/path/to/dir"},
            submit_directory_processing_task=mock_submit_directory_task
        )

        assert result["success"] is True
        assert result["async"] is True
        assert "task_id" in result

    @pytest.mark.asyncio
    async def test_watch_task_monitors_progress(self, mock_task_queue, mock_task_status):
        """Test watch_task monitors task until completion"""
        from src.codebase_rag.mcp.handlers.tasks import handle_watch_task

        # Simulate task completing immediately
        mock_task = Mock()
        mock_task.task_id = "task-123"
        mock_task.status = mock_task_status.COMPLETED
        mock_task.result = {"success": True}
        mock_task.error = None

        mock_task_queue.get_task.return_value = mock_task

        result = await handle_watch_task(
            args={"task_id": "task-123", "poll_interval": 0.1},
            task_queue=mock_task_queue,
            TaskStatus=mock_task_status
        )

        assert result["success"] is True
        assert result["final_status"] == "completed"
        assert "history" in result


class TestDataValidation:
    """Test suite for data validation patterns"""

    @pytest.mark.asyncio
    async def test_clear_knowledge_base_requires_confirmation(self, mock_knowledge_service):
        """Test clear_knowledge_base requires explicit confirmation"""
        from src.codebase_rag.mcp.handlers.system import handle_clear_knowledge_base

        # Without confirmation
        result = await handle_clear_knowledge_base(
            args={},
            knowledge_service=mock_knowledge_service
        )
        assert result["success"] is False
        assert "confirmation" in result["error"].lower()

        # With wrong confirmation
        result = await handle_clear_knowledge_base(
            args={"confirmation": "no"},
            knowledge_service=mock_knowledge_service
        )
        assert result["success"] is False

        # With correct confirmation
        mock_knowledge_service.clear_knowledge_base.return_value = {
            "success": True
        }
        result = await handle_clear_knowledge_base(
            args={"confirmation": "yes"},
            knowledge_service=mock_knowledge_service
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_memory_importance_defaults(self, mock_memory_store):
        """Test memory importance has sensible default"""
        from src.codebase_rag.mcp.handlers.memory import handle_add_memory

        mock_memory_store.add_memory.return_value = {
            "success": True,
            "memory_id": "mem-123"
        }

        result = await handle_add_memory(
            args={
                "project_id": "test",
                "memory_type": "note",
                "title": "Test",
                "content": "Content"
                # importance not provided
            },
            memory_store=mock_memory_store
        )

        # Check that default 0.5 was used
        call_args = mock_memory_store.add_memory.call_args
        assert call_args.kwargs["importance"] == 0.5

    @pytest.mark.asyncio
    async def test_search_top_k_defaults(self, mock_knowledge_service):
        """Test search top_k has sensible default"""
        from src.codebase_rag.mcp.handlers.knowledge import handle_search_similar_nodes

        mock_knowledge_service.search_similar_nodes.return_value = {
            "success": True,
            "results": []
        }

        result = await handle_search_similar_nodes(
            args={"query": "test"},
            knowledge_service=mock_knowledge_service
        )

        # Check that default 10 was used
        call_args = mock_knowledge_service.search_similar_nodes.call_args
        assert call_args.kwargs["top_k"] == 10
