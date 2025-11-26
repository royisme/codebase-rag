"""Shared helpers for embedding configuration and dimensions."""

from __future__ import annotations

from typing import Optional

from config import settings

_PROVIDER_DIMENSIONS = {
    "ollama": 768,
    "openai": 1536,
    "gemini": 768,
    "openrouter": 1536,
    # huggingface models vary widely; rely on configured dimension
    "huggingface": None,
}


def expected_dimension_for_provider(provider: Optional[str] = None) -> Optional[int]:
    """Return the known default embedding dimension for the provider, if any."""
    provider_name = (provider or settings.embedding_provider or "").lower()
    return _PROVIDER_DIMENSIONS.get(provider_name)


def effective_vector_dimension(configured_dimension: Optional[int] = None) -> int:
    """Return the actual dimension that should be used for embeddings."""
    configured = configured_dimension or settings.vector_dimension
    expected = expected_dimension_for_provider()
    return expected or configured


__all__ = ["expected_dimension_for_provider", "effective_vector_dimension"]
