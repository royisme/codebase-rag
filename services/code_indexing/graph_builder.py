"""Construct graph metadata for code repositories."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

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

    def __init__(self, graph_service=None) -> None:
        self.graph_service = graph_service

    async def build(
        self,
        parsed_files: Iterable[ParsedFile],
        *,
        source_id: Optional[str] = None,
    ) -> GraphBuildResult:
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
            class_count = len(parsed.classes)

            total_nodes += 1  # file node
            total_nodes += function_count
            total_nodes += class_count
            total_edges += import_count
            total_edges += function_count  # defined-in edges
            total_edges += class_count  # class defined-in edges

            if total_files and (index % progress_interval == 0 or index == total_files):
                logger.debug(
                    "Graph build progress: {}/{} files processed (language={}, functions={}, classes={}, imports={}).",
                    index,
                    total_files,
                    language,
                    function_count,
                    class_count,
                    import_count,
                )

        # Neo4j integration point (no-op for MVP if service absent)
        if self.graph_service:
            logger.info(
                "Persisting graph metadata for {} parsed files into Neo4j.",
                total_files,
            )
            await self._persist_to_neo4j(parsed_list, source_id)
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

    async def _persist_to_neo4j(
        self,
        parsed_files: Iterable[ParsedFile],
        source_id: Optional[str],
    ) -> None:
        service = self.graph_service
        if not service:
            return

        try:
            if not getattr(service, "_connected", False):
                connected = await service.connect()
                if not connected:
                    logger.warning("Neo4j graph service unavailable; skipping persistence.")
                    return
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to connect to Neo4j graph service: {}", exc)
            return

        parsed_list = list(parsed_files)
        if not parsed_list:
            return

        source_scope = str(source_id) if source_id is not None else "default"

        file_records: List[Dict[str, object]] = []
        function_records: List[Dict[str, object]] = []
        class_records: List[Dict[str, object]] = []
        defined_in_records: List[Dict[str, object]] = []
        import_records: List[Dict[str, object]] = []

        file_id_by_path: Dict[str, str] = {}
        module_lookup: Dict[str, str] = {}

        # First pass: build file nodes and module aliases
        for parsed in parsed_list:
            file_path = parsed.file.relative_path.as_posix()
            file_node_id = f"{source_scope}::file::{file_path}"
            file_id_by_path[file_path] = file_node_id

            file_records.append(
                {
                    "id": file_node_id,
                    "path": file_path,
                    "name": parsed.file.relative_path.name,
                    "language": parsed.file.language,
                    "source_id": source_id,
                    "size_bytes": parsed.file.size_bytes,
                }
            )

            for alias in self._module_aliases(parsed.file.relative_path):
                module_lookup.setdefault(alias, file_node_id)

        # Second pass: functions, classes, imports
        for parsed in parsed_list:
            file_path = parsed.file.relative_path.as_posix()
            file_node_id = file_id_by_path[file_path]

            for func in parsed.functions:
                func_id = f"{source_scope}::function::{file_path}::{func.name}"
                function_records.append(
                    {
                        "id": func_id,
                        "name": func.name,
                        "language": func.language,
                        "file_path": file_path,
                        "source_id": source_id,
                        "start_line": func.start_line,
                        "end_line": func.end_line,
                    }
                )
                defined_in_records.append(
                    {
                        "start_id": func_id,
                        "end_id": file_node_id,
                        "props": {
                            "entity_type": "function",
                            "language": func.language,
                            "name": func.name,
                        },
                    }
                )

            for class_name in parsed.classes:
                class_id = f"{source_scope}::class::{file_path}::{class_name}"
                class_records.append(
                    {
                        "id": class_id,
                        "name": class_name,
                        "language": parsed.file.language,
                        "file_path": file_path,
                        "source_id": source_id,
                    }
                )
                defined_in_records.append(
                    {
                        "start_id": class_id,
                        "end_id": file_node_id,
                        "props": {
                            "entity_type": "class",
                            "language": parsed.file.language,
                            "name": class_name,
                        },
                    }
                )

            for imp in parsed.imports:
                target_id = module_lookup.get(imp.module)
                if not target_id and imp.module:
                    short_name = imp.module.split(".")[-1]
                    target_id = module_lookup.get(short_name)
                if target_id and target_id != file_node_id:
                    import_records.append(
                        {
                            "start_id": file_node_id,
                            "end_id": target_id,
                            "props": {
                                "module": imp.module,
                                "language": imp.language,
                                "source_id": source_id,
                            },
                        }
                    )

        try:
            if file_records:
                await service.execute_cypher(
                    """
                    UNWIND $files AS file
                    MERGE (f:File {id: file.id})
                    SET f.path = file.path,
                        f.name = file.name,
                        f.language = file.language,
                        f.source_id = file.source_id,
                        f.size_bytes = file.size_bytes,
                        f.updated_at = timestamp()
                    """,
                    {"files": file_records},
                )

            if function_records:
                await service.execute_cypher(
                    """
                    UNWIND $functions AS func
                    MERGE (fn:Function {id: func.id})
                    SET fn.name = func.name,
                        fn.language = func.language,
                        fn.file_path = func.file_path,
                        fn.source_id = func.source_id,
                        fn.start_line = func.start_line,
                        fn.end_line = func.end_line,
                        fn.updated_at = timestamp()
                    """,
                    {"functions": function_records},
                )

            if class_records:
                await service.execute_cypher(
                    """
                    UNWIND $classes AS cls
                    MERGE (cl:Class {id: cls.id})
                    SET cl.name = cls.name,
                        cl.language = cls.language,
                        cl.file_path = cls.file_path,
                        cl.source_id = cls.source_id,
                        cl.updated_at = timestamp()
                    """,
                    {"classes": class_records},
                )

            if defined_in_records:
                await service.execute_cypher(
                    """
                    UNWIND $relationships AS rel
                    MATCH (start {id: rel.start_id})
                    MATCH (target {id: rel.end_id})
                    MERGE (start)-[r:DEFINED_IN]->(target)
                    SET r += rel.props,
                        r.updated_at = timestamp()
                    """,
                    {"relationships": defined_in_records},
                )

            if import_records:
                await service.execute_cypher(
                    """
                    UNWIND $imports AS rel
                    MATCH (source {id: rel.start_id})
                    MATCH (target {id: rel.end_id})
                    MERGE (source)-[r:IMPORTS]->(target)
                    SET r += rel.props,
                        r.updated_at = timestamp()
                    """,
                    {"imports": import_records},
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to persist graph metadata to Neo4j: {}", exc)

    @staticmethod
    def _module_aliases(relative_path: Path) -> List[str]:
        """Generate module alias candidates for matching imports to files."""

        path_without_suffix = relative_path.with_suffix("")
        aliases: List[str] = []

        parts = list(path_without_suffix.parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        if parts:
            dotted = ".".join(parts)
            aliases.append(dotted)
            aliases.append(parts[-1])

        aliases.append(path_without_suffix.as_posix())
        aliases.append(relative_path.as_posix())

        # Remove empty strings and duplicates while preserving order
        seen = set()
        unique_aliases: List[str] = []
        for alias in aliases:
            if not alias or alias in seen:
                continue
            seen.add(alias)
            unique_aliases.append(alias)

        return unique_aliases


__all__ = ["GraphBuilder", "GraphBuildResult"]
