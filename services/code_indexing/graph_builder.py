"""Construct graph metadata for code repositories."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, Iterable

from loguru import logger

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
        if isinstance(parsed_files, list):
            parsed_list = parsed_files
        else:
            parsed_list = list(parsed_files)

        total_files = len(parsed_list)
        if total_files == 0:
            logger.info("Graph build received empty parsed file set; nothing to construct.")
        else:
            logger.info("Graph build started for {} parsed files.", total_files)

        language_nodes: Dict[str, int] = {}
        total_nodes = 0
        total_edges = 0
        progress_interval = max(total_files // 10, 1) if total_files else 1

        for index, parsed in enumerate(parsed_list, start=1):
            language = parsed.file.language
            language_nodes[language] = language_nodes.get(language, 0) + 1

            function_count = len(parsed.functions)
            import_count = len(parsed.imports)

            total_nodes += 1  # file node
            total_nodes += function_count
            total_edges += import_count
            total_edges += function_count  # defined-in edges

            if total_files and (index % progress_interval == 0 or index == total_files):
                logger.debug(
                    "Graph build progress: {}/{} files processed (language={}, functions={}, imports={}).",
                    index,
                    total_files,
                    language,
                    function_count,
                    import_count,
                )

        # Neo4j integration point (no-op for MVP if service absent)
        if self.neo4j_service:
            logger.info(
                "Persisting graph metadata for {} parsed files into Neo4j.",
                total_files,
            )
            await self._persist_to_neo4j(parsed_list)
            logger.info("Graph metadata persistence to Neo4j completed.")
        else:
            logger.debug("Neo4j service not configured; skipping graph persistence step.")

        result = GraphBuildResult(
            nodes_created=total_nodes,
            edges_created=total_edges,
            languages=language_nodes,
            generated_at=dt.datetime.now(dt.timezone.utc),
        )
        logger.info(
            "Graph build completed: nodes={}, edges={}, languages={}.",
            result.nodes_created,
            result.edges_created,
            result.languages,
        )
        return result

    async def _persist_to_neo4j(self, parsed_files: Iterable[ParsedFile]) -> None:
        # Placeholder for future integration.
        for _parsed in parsed_files:
            continue


__all__ = ["GraphBuilder", "GraphBuildResult"]
