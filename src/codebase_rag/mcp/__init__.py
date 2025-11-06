"""
MCP (Model Context Protocol) implementation for Codebase RAG.

This module provides the MCP server and handlers for AI assistant integration.
"""

from src.codebase_rag.mcp import handlers, tools, resources, prompts, utils

__all__ = ["handlers", "tools", "resources", "prompts", "utils"]
