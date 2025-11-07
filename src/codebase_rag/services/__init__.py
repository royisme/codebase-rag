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

Note: Subpackages are not eagerly imported to avoid triggering heavy dependencies.
Import specific services from their subpackages as needed:
    from src.codebase_rag.services.code import Neo4jGraphService
    from src.codebase_rag.services.knowledge import Neo4jKnowledgeService
    from src.codebase_rag.services.memory import MemoryStore
"""

# Declare subpackages without eager importing to avoid dependency issues
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
