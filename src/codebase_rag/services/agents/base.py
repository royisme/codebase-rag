"""Factories for constructing LlamaIndex workflow agents."""

from typing import Sequence

from llama_index.core import Settings
from llama_index.core.agent.workflow import FunctionAgent

from codebase_rag.config import settings

from .tools import AGENT_TOOLS


def create_default_agent(*, tools: Sequence = AGENT_TOOLS) -> FunctionAgent:
    """Create a FunctionAgent wired with the default toolset.

    The agent uses the globally configured LlamaIndex LLM settings and provides
    instructions aimed at orchestrating knowledge retrieval, memory extraction and
    lightweight task tracking across a project-oriented workflow.
    """

    if Settings.llm is None:
        raise ValueError(
            "Settings.llm is not configured. Initialize the Neo4j knowledge service "
            "or configure Settings.llm before creating agents."
        )

    description = (
        "Project knowledge orchestrator capable of looking up graph knowledge, "
        "searching vector similarities, extracting new memories and persisting them."
    )

    system_prompt = (
        "You are the CodebaseRAG coordinator. Always inspect the available tools to "
        "answer user questions, retrieve supporting context from Neo4j, and store new "
        "memories when relevant. Make sure responses explain which tools were used."
    )

    return FunctionAgent(
        name=settings.app_name or "codebase-rag-agent",
        description=description,
        system_prompt=system_prompt,
        tools=list(tools),
        llm=Settings.llm,
    )
