"""
Prompt Handlers for MCP Server v2

This module contains handlers for MCP prompts:
- List prompts
- Get prompt content
"""

from typing import Dict, List
from mcp.types import Prompt, PromptMessage, PromptArgument


def get_prompt_list() -> List[Prompt]:
    """
    Get list of available prompts.

    Returns:
        List of Prompt objects
    """
    return [
        Prompt(
            name="suggest_queries",
            description="Generate suggested queries for the knowledge graph",
            arguments=[
                PromptArgument(
                    name="domain",
                    description="Domain to focus on",
                    required=False
                )
            ]
        )
    ]


def get_prompt_content(name: str, arguments: Dict[str, str]) -> List[PromptMessage]:
    """
    Get content for a specific prompt.

    Args:
        name: Prompt name
        arguments: Prompt arguments

    Returns:
        List of PromptMessage objects

    Raises:
        ValueError: If prompt name is unknown
    """
    if name == "suggest_queries":
        domain = arguments.get("domain", "general")

        suggestions = {
            "general": [
                "What are the main components of this system?",
                "How does the knowledge pipeline work?",
                "What databases are used?"
            ],
            "code": [
                "Show me Python functions for data processing",
                "Find code examples for Neo4j integration",
                "What are the main classes?"
            ],
            "memory": [
                "What decisions have been made about architecture?",
                "Show me coding preferences for this project",
                "What problems have we encountered?"
            ]
        }

        domain_suggestions = suggestions.get(domain, suggestions["general"])

        content = f"""Here are suggested queries for {domain}:

{chr(10).join(f"• {s}" for s in domain_suggestions)}

Available query modes:
• hybrid: Graph + vector search (recommended)
• graph_only: Graph relationships only
• vector_only: Vector similarity only

You can use query_knowledge tool with these questions."""

        return [
            PromptMessage(
                role="user",
                content={"type": "text", "text": content}
            )
        ]

    else:
        raise ValueError(f"Unknown prompt: {name}")
