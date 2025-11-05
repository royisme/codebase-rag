"""
Unit Tests for MCP Utility Functions

This module contains tests for utility functions used by MCP handlers:
- format_result function for formatting different result types
- Error formatting
- Edge cases and special scenarios
"""

import pytest
from mcp_tools.utils import format_result


class TestFormatResult:
    """Test suite for format_result function"""

    def test_format_result_error(self):
        """Test formatting error result"""
        result = {
            "success": False,
            "error": "Something went wrong"
        }

        output = format_result(result)

        assert "❌ Error:" in output
        assert "Something went wrong" in output

    def test_format_result_error_unknown(self):
        """Test formatting error without error message"""
        result = {
            "success": False
        }

        output = format_result(result)

        assert "❌ Error:" in output
        assert "Unknown error" in output

    def test_format_result_query_with_sources(self):
        """Test formatting query result with source nodes"""
        result = {
            "success": True,
            "answer": "This is the answer to your question.",
            "source_nodes": [
                {"text": "Source 1 contains relevant information about the topic."},
                {"text": "Source 2 provides additional context for understanding."},
                {"text": "Source 3 has supporting evidence for the answer."}
            ]
        }

        output = format_result(result)

        assert "Answer: This is the answer" in output
        assert "Sources (3 nodes)" in output
        assert "1. Source 1" in output
        assert "2. Source 2" in output
        assert "3. Source 3" in output

    def test_format_result_query_without_sources(self):
        """Test formatting query result without source nodes"""
        result = {
            "success": True,
            "answer": "This is the answer.",
            "source_nodes": []
        }

        output = format_result(result)

        assert "Answer: This is the answer" in output
        # Should not show sources section
        assert "Sources (0 nodes)" in output

    def test_format_result_search_with_results(self):
        """Test formatting search results"""
        result = {
            "success": True,
            "results": [
                {"score": 0.95, "text": "First search result with high relevance score."},
                {"score": 0.85, "text": "Second search result with good relevance."},
                {"score": 0.75, "text": "Third search result with moderate relevance."}
            ]
        }

        output = format_result(result)

        assert "Found 3 results" in output
        assert "Score: 0.950" in output
        assert "Score: 0.850" in output
        assert "Score: 0.750" in output

    def test_format_result_search_empty(self):
        """Test formatting empty search results"""
        result = {
            "success": True,
            "results": []
        }

        output = format_result(result)

        assert "No results found" in output

    def test_format_result_memories_with_results(self):
        """Test formatting memory search results"""
        result = {
            "success": True,
            "total_count": 3,
            "memories": [
                {
                    "id": "mem-1",
                    "type": "decision",
                    "title": "Use JWT for authentication",
                    "importance": 0.9,
                    "tags": ["auth", "security"]
                },
                {
                    "id": "mem-2",
                    "type": "preference",
                    "title": "Use raw SQL",
                    "importance": 0.6,
                    "tags": ["database"]
                },
                {
                    "id": "mem-3",
                    "type": "experience",
                    "title": "Redis timeout fix",
                    "importance": 0.7,
                    "tags": []
                }
            ]
        }

        output = format_result(result)

        assert "Found 3 memories" in output
        assert "[decision] Use JWT for authentication" in output
        assert "Importance: 0.90" in output
        assert "Tags: auth, security" in output
        assert "[preference] Use raw SQL" in output
        assert "ID: mem-1" in output

    def test_format_result_memories_empty(self):
        """Test formatting empty memory search"""
        result = {
            "success": True,
            "memories": []
        }

        output = format_result(result)

        assert "No memories found" in output

    def test_format_result_single_memory(self):
        """Test formatting single memory detail"""
        result = {
            "success": True,
            "memory": {
                "id": "mem-123",
                "type": "decision",
                "title": "Architecture Decision",
                "content": "We decided to use microservices architecture for scalability.",
                "reason": "Need to scale independently and support multiple teams.",
                "importance": 0.95,
                "tags": ["architecture", "scalability"]
            }
        }

        output = format_result(result)

        assert "Memory: Architecture Decision" in output
        assert "Type: decision" in output
        assert "Importance: 0.95" in output
        assert "Content: We decided to use microservices" in output
        assert "Reason: Need to scale independently" in output
        assert "Tags: architecture, scalability" in output
        assert "ID: mem-123" in output

    def test_format_result_single_memory_minimal(self):
        """Test formatting single memory with minimal fields"""
        result = {
            "success": True,
            "memory": {
                "id": "mem-456",
                "type": "note",
                "title": "Simple Note",
                "content": "Just a quick note."
            }
        }

        output = format_result(result)

        assert "Memory: Simple Note" in output
        assert "Type: note" in output
        assert "Content: Just a quick note" in output

    def test_format_result_code_nodes_with_results(self):
        """Test formatting code graph nodes"""
        result = {
            "success": True,
            "nodes": [
                {"path": "src/auth/token.py", "score": 0.95, "ref": "ref://token"},
                {"path": "src/auth/user.py", "score": 0.85, "ref": "ref://user"},
                {"name": "DatabaseConfig", "score": 0.75, "ref": "ref://db_config"}
            ]
        }

        output = format_result(result)

        assert "Found 3 nodes" in output
        assert "src/auth/token.py" in output
        assert "Score: 0.950" in output
        assert "Ref: ref://token" in output
        assert "DatabaseConfig" in output

    def test_format_result_code_nodes_empty(self):
        """Test formatting empty code nodes result"""
        result = {
            "success": True,
            "nodes": []
        }

        output = format_result(result)

        assert "No nodes found" in output

    def test_format_result_context_pack(self):
        """Test formatting context pack result"""
        result = {
            "success": True,
            "items": [
                {
                    "kind": "file",
                    "title": "main.py",
                    "summary": "Main application entry point with server initialization",
                    "ref": "ref://main"
                },
                {
                    "kind": "symbol",
                    "title": "authenticate_user",
                    "summary": "User authentication function with JWT validation",
                    "ref": "ref://auth_func"
                }
            ],
            "budget_used": 1200,
            "budget_limit": 1500
        }

        output = format_result(result)

        assert "Context Pack (1200/1500 tokens)" in output
        assert "Items: 2" in output
        assert "[file] main.py" in output
        assert "Main application entry point" in output
        assert "Ref: ref://main" in output
        assert "[symbol] authenticate_user" in output

    def test_format_result_context_pack_minimal(self):
        """Test formatting context pack without summaries"""
        result = {
            "success": True,
            "items": [
                {"kind": "file", "title": "utils.py", "ref": "ref://utils"}
            ],
            "budget_used": 500,
            "budget_limit": 1500
        }

        output = format_result(result)

        assert "Context Pack (500/1500 tokens)" in output
        assert "[file] utils.py" in output

    def test_format_result_task_list(self):
        """Test formatting task list"""
        result = {
            "success": True,
            "tasks": [
                {
                    "task_id": "task-1",
                    "status": "completed",
                    "created_at": "2024-01-01T10:00:00"
                },
                {
                    "task_id": "task-2",
                    "status": "running",
                    "created_at": "2024-01-01T11:00:00"
                }
            ]
        }

        output = format_result(result)

        assert "Tasks (2)" in output
        assert "task-1: completed" in output
        assert "task-2: running" in output
        assert "Created: 2024-01-01T10:00:00" in output

    def test_format_result_task_list_empty(self):
        """Test formatting empty task list"""
        result = {
            "success": True,
            "tasks": []
        }

        output = format_result(result)

        assert "No tasks found" in output

    def test_format_result_queue_stats(self):
        """Test formatting queue statistics"""
        result = {
            "success": True,
            "stats": {
                "pending": 5,
                "running": 2,
                "completed": 10,
                "failed": 1
            }
        }

        output = format_result(result)

        assert "Queue Statistics:" in output
        assert "Pending: 5" in output
        assert "Running: 2" in output
        assert "Completed: 10" in output
        assert "Failed: 1" in output

    def test_format_result_generic_success(self):
        """Test formatting generic success result"""
        result = {
            "success": True,
            "message": "Operation completed",
            "data": {"key": "value"}
        }

        output = format_result(result)

        assert "✅ Success" in output
        # Should contain JSON representation
        assert "message" in output
        assert "Operation completed" in output

    def test_format_result_long_text_truncation(self):
        """Test that long text is properly truncated"""
        long_text = "x" * 200  # Very long text
        result = {
            "success": True,
            "results": [
                {"score": 0.9, "text": long_text}
            ]
        }

        output = format_result(result)

        # Should be truncated to 100 chars
        assert len(long_text) > 100
        assert "..." in output

    def test_format_result_source_nodes_limit(self):
        """Test that source nodes are limited to 5"""
        result = {
            "success": True,
            "answer": "Answer",
            "source_nodes": [
                {"text": f"Source {i}"} for i in range(10)
            ]
        }

        output = format_result(result)

        # Should only show first 5
        assert "1. Source 0" in output
        assert "5. Source 4" in output
        # Should not show 6th or beyond
        assert "6. Source 5" not in output

    def test_format_result_search_results_limit(self):
        """Test that search results are limited to 10"""
        result = {
            "success": True,
            "results": [
                {"score": 0.9 - i*0.01, "text": f"Result {i}"} for i in range(20)
            ]
        }

        output = format_result(result)

        # Should only show first 10
        assert "Found 20 results" in output
        assert "1. Score:" in output
        assert "10. Score:" in output
        # Count occurrences - should be exactly 10
        assert output.count("Score:") == 10

    def test_format_result_nodes_limit(self):
        """Test that code nodes are limited to 10"""
        result = {
            "success": True,
            "nodes": [
                {"path": f"file{i}.py", "score": 0.9} for i in range(15)
            ]
        }

        output = format_result(result)

        # Should show "Found 15" but only display 10
        assert "Found 15 nodes" in output
        assert "file0.py" in output
        assert "file9.py" in output
        assert "file10.py" not in output

    def test_format_result_memory_without_tags(self):
        """Test formatting memory without tags"""
        result = {
            "success": True,
            "memory": {
                "id": "mem-1",
                "type": "note",
                "title": "Test",
                "content": "Content"
            }
        }

        output = format_result(result)

        assert "Memory: Test" in output
        # Should not show empty tags line
        assert "Tags:" not in output

    def test_format_result_memory_search_without_tags(self):
        """Test formatting memory search result without tags"""
        result = {
            "success": True,
            "memories": [
                {
                    "id": "mem-1",
                    "type": "note",
                    "title": "Test",
                    "importance": 0.5
                }
            ]
        }

        output = format_result(result)

        assert "[note] Test" in output
        # When no tags, should not show tags line
        # The code checks if mem.get('tags') which would be None/empty
