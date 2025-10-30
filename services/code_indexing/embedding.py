"""Lightweight embedding generation helpers for code indexing."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, List

from .code_parser import ParsedFunction


@dataclass
class EmbeddingSummary:
    """Aggregate metrics for generated embeddings."""

    functions_embedded: int
    embedding_dimension: int
    average_magnitude: float


class DeterministicEmbeddingGenerator:
    """Generate deterministic vectors without external dependencies."""

    def __init__(self, dimension: int = 32) -> None:
        self.dimension = dimension

    def generate(self, functions: Iterable[ParsedFunction]) -> EmbeddingSummary:
        magnitudes: List[float] = []
        count = 0

        for function in functions:
            vector = self._embed_function(function)
            magnitude = math.sqrt(sum(component ** 2 for component in vector))
            magnitudes.append(magnitude)
            count += 1

        average = sum(magnitudes) / count if count else 0.0
        return EmbeddingSummary(
            functions_embedded=count,
            embedding_dimension=self.dimension,
            average_magnitude=average,
        )

    def _embed_function(self, function: ParsedFunction) -> List[float]:
        signature = f"{function.language}:{function.file_path}:{function.name}:{function.start_line}:{function.end_line}"
        digest = hashlib.sha256(signature.encode("utf-8")).digest()

        vector = []
        for index in range(self.dimension):
            # Use 2 bytes per dimension to derive a stable pseudo-random value
            start = (index * 2) % len(digest)
            value = int.from_bytes(digest[start : start + 2], "big", signed=False)
            vector.append((value % 2000) / 1000.0 - 1.0)  # scale to [-1, 1]
        return vector


__all__ = ["DeterministicEmbeddingGenerator", "EmbeddingSummary"]
