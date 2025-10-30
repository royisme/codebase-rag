"""Construct graph metadata for code repositories."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, Iterable

from .code_parser import ParsedFile


@dataclass
class GraphBuildResult:
    """Summary of graph construction work."""

    nodes_created: int
    edges_created: int
    languages: Dict[str, int]
    generated_at: dt.datetime


class GraphBuilder:
    """Builds graph metadata for indexed repositories."""

    def __init__(self, neo4j_service=None) -> None:
        self.neo4j_service = neo4j_service

    async def build(self, parsed_files: Iterable[ParsedFile]) -> GraphBuildResult:
        language_nodes: Dict[str, int] = {}
        total_nodes = 0
        total_edges = 0

        for parsed in parsed_files:
            language = parsed.file.language
            language_nodes[language] = language_nodes.get(language, 0) + 1

            total_nodes += 1  # file node
            total_nodes += len(parsed.functions)
            total_edges += len(parsed.imports)
            total_edges += len(parsed.functions)  # defined-in edges

        # Neo4j integration point (no-op for MVP if service absent)
        if self.neo4j_service:
            await self._persist_to_neo4j(parsed_files)

        return GraphBuildResult(
            nodes_created=total_nodes,
            edges_created=total_edges,
            languages=language_nodes,
            generated_at=dt.datetime.now(dt.timezone.utc),
        )

    async def _persist_to_neo4j(self, parsed_files: Iterable[ParsedFile]) -> None:
        # Placeholder for future integration.
        for _parsed in parsed_files:
            continue


__all__ = ["GraphBuilder", "GraphBuildResult"]
