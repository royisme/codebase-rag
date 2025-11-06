"""
Configuration module for Codebase RAG.

This module exports all configuration-related objects and functions.
"""

from src.codebase_rag.config.settings import Settings, settings
from src.codebase_rag.config.validation import (
    validate_neo4j_connection,
    validate_ollama_connection,
    validate_openai_connection,
    validate_gemini_connection,
    validate_openrouter_connection,
    get_current_model_info,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    # Validation functions
    "validate_neo4j_connection",
    "validate_ollama_connection",
    "validate_openai_connection",
    "validate_gemini_connection",
    "validate_openrouter_connection",
    "get_current_model_info",
]
