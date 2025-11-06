"""
Backward compatibility shim for config module.

DEPRECATED: This module is deprecated. Please use:
    from src.codebase_rag.config import settings

instead of:
    from config import settings

This shim will be removed in version 0.9.0.
"""

import warnings

warnings.warn(
    "Importing from 'config' is deprecated. "
    "Use 'from src.codebase_rag.config import settings' instead. "
    "This compatibility layer will be removed in version 0.9.0.",
    DeprecationWarning,
    stacklevel=2
)

# Import everything from new location for backward compatibility
from src.codebase_rag.config import (
    Settings,
    settings,
    validate_neo4j_connection,
    validate_ollama_connection,
    validate_openai_connection,
    validate_gemini_connection,
    validate_openrouter_connection,
    get_current_model_info,
)

__all__ = [
    "Settings",
    "settings",
    "validate_neo4j_connection",
    "validate_ollama_connection",
    "validate_openai_connection",
    "validate_gemini_connection",
    "validate_openrouter_connection",
    "get_current_model_info",
]
