"""
Services module for Codebase RAG.

This module provides all business logic services organized into logical subpackages:
- knowledge: Neo4j knowledge graph services
- memory: Conversation memory and extraction
- code: Code analysis and ingestion
- sql: SQL parsing and schema analysis
- tasks: Task queue and processing
- utils: Utility functions (git, ranking, metrics)
- pipeline: Data processing pipeline
- graph: Graph schema and utilities
"""

# Import subpackages
from src.codebase_rag.services import (
    knowledge,
    memory,
    code,
    sql,
    tasks,
    utils,
    pipeline,
    graph,
)

__all__ = [
    "knowledge",
    "memory",
    "code",
    "sql",
    "tasks",
    "utils",
    "pipeline",
    "graph",
]
