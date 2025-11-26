"""End-to-end indexing pipeline for code repositories."""

from __future__ import annotations

import asyncio
import copy
import datetime as dt
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from config import settings
from database.models import ParseStatus
from schemas import ParseJobUpdate
from services.source_service import SourceService, update_job_with_new_session

from .code_parser import CodeParser, ParseSummary, ParsedFile, ParsedFunction
from .embedding import EmbeddingSummary
from .file_scanner import FileScanner, FileScanResult
from .git_sync import GitSyncService, GitSyncResult, GitDiffResult
from .graph_builder import GraphBuilder, GraphBuildResult
from services.embedding_client import EmbeddingClient
from services.embedding_utils import effective_vector_dimension


@dataclass
class CodeIndexingResult:
    """Structured result returned after indexing completes."""

    repository_path: str
    branch: str
    commit_sha: str
    files_scanned: int
    files_parsed: int
    files_failed: int
    functions_extracted: int
    imports_extracted: int
    nodes_created: int
    edges_created: int
    languages: Dict[str, int]
    duration_seconds: float
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)


class CodeIndexingPipeline:
    """Coordinates git sync, scanning, parsing, embedding, and graph updates."""

    STAGE_PROGRESS = {
        "git_clone": 15,
        "file_scan": 30,
        "code_parse": 50,
        "embedding": 70,
        "graph_build": 85,
        "knowledge_index": 95,
        "completed": 100,
    }

    def __init__(
        self,
        *,
        source_service: SourceService,
        session,
        graph_service=None,
    ) -> None:
        self.source_service = source_service
        self.session = session
        self.graph_service = graph_service

        self.git_service = GitSyncService()
        self.scanner = FileScanner(
            include_patterns=settings.code_include_patterns,
            exclude_patterns=settings.code_exclude_patterns,
            max_file_size_kb=settings.code_max_file_size_kb,
        )
        self.parser = CodeParser()
        effective_dim = effective_vector_dimension(settings.vector_dimension)
        self.embedding_client = EmbeddingClient(dimension=effective_dim)
        self.graph_builder = GraphBuilder(graph_service=graph_service)

        self.summary: Dict[str, Any] = {
            "stage": "initializing",
            "stage_history": [],
            "files_scanned": 0,
            "files_parsed": 0,
            "files_failed": 0,
            "functions_extracted": 0,
            "imports_extracted": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "errors": [],
        }

    async def run(
        self,
        *,
        source,
        job_id: Optional[str],
        sync_config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> CodeIndexingResult:
        start_time = time.perf_counter()
        sync_config = sync_config or {}

        # Extract force_full flag to determine if we should clear existing data
        force_full = sync_config.get("force_full", False)

        # Extract sync_mode (full or incremental)
        sync_mode = sync_config.get(
            "sync_mode", "full" if force_full else "incremental"
        )

        connection_config = dict(source.connection_config or {})
        overrides: Dict[str, Any] = {}

        if isinstance(sync_config, dict):
            nested = sync_config.get("connection_config")
            if isinstance(nested, dict):
                overrides.update(nested)

            for key, value in sync_config.items():
                if key == "connection_config":
                    continue
                # Skip force_full as it's not a connection config
                if key == "force_full":
                    continue
                overrides[key] = value

        if overrides:
            connection_config.update(
                {k: v for k, v in overrides.items() if v is not None}
            )

        depth_override = overrides.get("git_depth") or overrides.get("clone_depth")
        if depth_override is None:
            depth_override = connection_config.get(
                "git_depth"
            ) or connection_config.get("clone_depth")
        if depth_override is not None:
            try:
                self.git_service.depth = int(depth_override)
            except (TypeError, ValueError):
                pass
        # Extract parameters with fallbacks
        repo_url = connection_config.get("repo_url")
        if not repo_url:
            raise ValueError("connection_config.repo_url is required for code indexing")

        branch = connection_config.get("branch") or "main"
        auth_type = connection_config.get("auth_type", "none")
        access_token = connection_config.get("access_token")
        include_patterns = (
            connection_config.get("include_patterns") or settings.code_include_patterns
        )
        exclude_patterns = (
            connection_config.get("exclude_patterns") or settings.code_exclude_patterns
        )
        max_file_size_kb = (
            connection_config.get("max_file_size_kb") or settings.code_max_file_size_kb
        )

        # Normalize pattern configuration
        include_patterns = self._ensure_list(include_patterns)
        exclude_patterns = self._ensure_list(exclude_patterns)

        self.scanner = FileScanner(
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size_kb=max_file_size_kb,
        )

        job_uuid = None
        if job_id:
            job_uuid = (
                job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))
            )
        repo_root = settings.code_repo_root_path
        repo_path = repo_root / str(source.id)
        source_id_str = (
            str(getattr(source, "id", None))
            if getattr(source, "id", None) is not None
            else None
        )
        source_name = getattr(source, "name", None)

        # If force_full is True, clear existing graph data for this source
        if force_full and source_id_str:
            logger.info(
                f"Force full reindex requested - clearing existing graph data for source {source_id_str}"
            )
            await self._clear_source_graph_data(
                source_id_str,
                job_uuid,
                progress_callback,
                task_progress_callback,
            )

        # Get previous commit SHA for incremental indexing
        previous_sha = None
        if source.source_metadata:
            previous_sha = source.source_metadata.get("last_commit_sha")

        git_result = await self._sync_repository(
            repo_url,
            branch,
            auth_type,
            access_token,
            repo_path,
            job_uuid,
            progress_callback,
            task_progress_callback,
        )

        # Determine if we should use incremental indexing
        use_incremental = (
            sync_mode == "incremental"
            and not force_full
            and previous_sha
            and previous_sha != git_result.commit_sha
            and git_result.fetched
        )

        if use_incremental:
            # At this point, previous_sha is guaranteed to be not None due to use_incremental conditions
            assert previous_sha is not None
            logger.info(
                f"Using incremental indexing: {previous_sha[:8]} -> {git_result.commit_sha[:8]}"
            )

            # Get changed files using git diff
            diff_result = await self.git_service.get_changed_files(
                repo_path,
                previous_sha,
                git_result.commit_sha,
            )

            # Process only changed files
            scan_result, parsed_files, parse_summary = await self._process_incremental(
                repo_path,
                diff_result,
                source_id_str,
                job_uuid,
                progress_callback,
                task_progress_callback,
            )
        else:
            if previous_sha and previous_sha == git_result.commit_sha:
                logger.info(
                    f"No changes detected (commit {git_result.commit_sha[:8]}), skipping full scan"
                )
            elif force_full or sync_mode == "full":
                logger.info("Using full indexing mode")
            else:
                logger.info("Using full indexing (no previous commit or first sync)")

            # Full indexing: scan and parse all files
            scan_result = await self._scan_repository(
                repo_path,
                job_uuid,
                progress_callback,
                task_progress_callback,
            )

            parsed_files, parse_summary = await self._parse_repository(
                scan_result,
                job_uuid,
                progress_callback,
                task_progress_callback,
            )

        embedding_summary = await self._embed_functions(
            parsed_files,
            job_uuid,
            progress_callback,
            task_progress_callback,
        )

        graph_result = await self._build_graph(
            parsed_files,
            job_uuid,
            progress_callback,
            task_progress_callback,
            source_id=source_id_str,
        )

        # Build knowledge index for GraphRAG
        knowledge_result = await self._build_knowledge_index(
            parsed_files,
            job_uuid,
            progress_callback,
            task_progress_callback,
            source_id=source_id_str,
            source_name=source_name,
        )

        duration = time.perf_counter() - start_time

        # Update knowledge source metadata
        metadata_update = {
            "last_commit_sha": git_result.commit_sha,
            "last_sync_mode": sync_mode,
            "index_version": "mvp-1",
            "embedding_dimension": embedding_summary.embedding_dimension,
        }

        if sync_mode == "full" or force_full or not source.source_metadata:
            # Full sync: overwrite all metadata
            metadata_update.update(
                {
                    "total_files": len(scan_result.files),
                    "total_functions": parse_summary.functions_extracted,
                    "languages": graph_result.languages,
                    "graph_nodes": graph_result.nodes_created,
                    "graph_edges": graph_result.edges_created,
                }
            )
            source.source_metadata = metadata_update
        else:
            # Incremental sync: update metadata
            if not source.source_metadata:
                source.source_metadata = {}

            # Increment counters for incremental updates
            source.source_metadata.update(metadata_update)
            source.source_metadata["total_files"] = source.source_metadata.get(
                "total_files", 0
            ) + len(scan_result.files)
            source.source_metadata["graph_nodes"] = (
                source.source_metadata.get("graph_nodes", 0)
                + graph_result.nodes_created
            )
            source.source_metadata["graph_edges"] = (
                source.source_metadata.get("graph_edges", 0)
                + graph_result.edges_created
            )

        self.summary["duration_seconds"] = duration
        await self._update_stage(
            "completed",
            progress=self.STAGE_PROGRESS["completed"],
            job_uuid=job_uuid,
            status=ParseStatus.COMPLETED,
            payload={
                "duration_seconds": duration,
                "nodes_created": graph_result.nodes_created,
                "edges_created": graph_result.edges_created,
                "languages": graph_result.languages,
                "files_parsed": parse_summary.files_parsed,
                "functions_embedded": embedding_summary.functions_embedded,
                "errors": self.summary.get("errors", []),
            },
            message="Indexing completed",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )

        source.last_synced_at = dt.datetime.now(dt.timezone.utc)

        result = CodeIndexingResult(
            repository_path=str(repo_path),
            branch=branch,
            commit_sha=git_result.commit_sha,
            files_scanned=len(scan_result.files),
            files_parsed=parse_summary.files_parsed,
            files_failed=self.summary["files_failed"],
            functions_extracted=parse_summary.functions_extracted,
            imports_extracted=parse_summary.imports_extracted,
            nodes_created=graph_result.nodes_created,
            edges_created=graph_result.edges_created,
            languages=graph_result.languages,
            duration_seconds=duration,
            stage_history=self.summary.get("stage_history", []),
            errors=self.summary.get("errors", []),
        )

        return result

    async def _process_incremental(
        self,
        repo_path: Path,
        diff_result: GitDiffResult,
        source_id: Optional[str],
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ):
        """Process only changed files for incremental indexing."""

        # Combine added and modified files for processing
        files_to_process = diff_result.added_files + diff_result.modified_files

        # Handle renamed files (treat as delete old + add new)
        for old_path, new_path in diff_result.renamed_files:
            diff_result.deleted_files.append(old_path)
            files_to_process.append(new_path)

        logger.info(
            f"Incremental sync: processing {len(files_to_process)} files, "
            f"deleting {len(diff_result.deleted_files)} files"
        )

        await self._update_stage(
            "incremental_delete",
            progress=12,
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload={
                "deleted_files": len(diff_result.deleted_files),
            },
            message=f"Deleting {len(diff_result.deleted_files)} removed files from graph",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )

        # Delete nodes for removed/renamed files
        if diff_result.deleted_files and source_id:
            if self.graph_service:
                for file_path in diff_result.deleted_files:
                    try:
                        await self.graph_service.delete_file_nodes(source_id, file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete nodes for {file_path}: {e}")

        # Create a filtered scan result with only changed files
        from .file_scanner import ScannedFile, FileScanResult

        scanned_files = []
        skipped_count = 0
        errors = []

        for file_path in files_to_process:
            absolute_path = repo_path / file_path

            if not absolute_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            # Check if file matches include/exclude patterns
            relative_path_obj = Path(file_path)
            if self.scanner._should_skip(relative_path_obj):
                skipped_count += 1
                continue

            try:
                size_bytes = absolute_path.stat().st_size
                if size_bytes > self.scanner.max_file_size_bytes:
                    skipped_count += 1
                    continue

                language = self.scanner._detect_language(absolute_path)
                if not language:
                    skipped_count += 1
                    continue

                scanned_files.append(
                    ScannedFile(
                        relative_path=relative_path_obj,
                        absolute_path=absolute_path,
                        language=language,
                        size_bytes=size_bytes,
                    )
                )
            except Exception as e:
                errors.append({"file": file_path, "error": str(e)})

        # Build language breakdown
        language_breakdown = {}
        for scanned in scanned_files:
            ext = scanned.absolute_path.suffix.lower()
            language_breakdown[ext] = language_breakdown.get(ext, 0) + 1

        scan_result = FileScanResult(
            files=scanned_files,
            skipped=skipped_count,
            errors=errors,
            language_breakdown=language_breakdown,
        )

        await self._update_stage(
            "incremental_scan",
            progress=20,
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload={
                "files_to_parse": len(scanned_files),
                "files_skipped": skipped_count,
            },
            message=f"Scanning {len(scanned_files)} changed files",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )

        # Parse the changed files
        parsed_files, parse_summary = await self._parse_repository(
            scan_result,
            job_uuid,
            progress_callback,
            task_progress_callback,
        )

        return scan_result, parsed_files, parse_summary

    async def _clear_source_graph_data(
        self,
        source_id: str,
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ) -> None:
        """Clear all existing graph data for this source before full reindex."""
        try:
            await self._update_stage(
                "clear_data",
                progress=5,
                job_uuid=job_uuid,
                status=ParseStatus.RUNNING,
                payload={"action": "clearing_existing_data"},
                message="Clearing existing graph data",
                progress_callback=progress_callback,
                task_progress_callback=task_progress_callback,
            )

            # Delete all nodes and relationships for this source
            deleted = await self.graph_service.delete_source_data(source_id)

            logger.info(
                f"Cleared {deleted.get('nodes_deleted', 0)} nodes and {deleted.get('relationships_deleted', 0)} relationships for source {source_id}"
            )

            await self._update_stage(
                "clear_data",
                progress=8,
                job_uuid=job_uuid,
                status=ParseStatus.RUNNING,
                payload={
                    "action": "data_cleared",
                    "nodes_deleted": deleted.get("nodes_deleted", 0),
                    "relationships_deleted": deleted.get("relationships_deleted", 0),
                },
                message=f"Cleared {deleted.get('nodes_deleted', 0)} nodes",
                progress_callback=progress_callback,
                task_progress_callback=task_progress_callback,
            )
        except Exception as e:
            logger.warning(f"Failed to clear existing graph data: {e}")
            # Don't fail the entire pipeline if clearing fails
            # The new data will overwrite/merge with existing data

    async def _sync_repository(
        self,
        repo_url: str,
        branch: str,
        auth_type: str,
        access_token: Optional[str],
        repo_path: Path,
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ) -> GitSyncResult:
        start = time.perf_counter()
        result = await self.git_service.clone_or_pull(
            repo_url,
            branch,
            repo_path,
            auth_type=auth_type,
            access_token=access_token,
        )
        duration = time.perf_counter() - start

        stage_payload = {
            "commit_sha": result.commit_sha,
            "duration_seconds": duration,
            "branch": branch,
        }
        await self._update_stage(
            "git_clone",
            progress=self.STAGE_PROGRESS["git_clone"],
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload=stage_payload,
            message="Repository synchronized",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )
        return result

    async def _scan_repository(
        self,
        repo_path: Path,
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ) -> FileScanResult:
        start = time.perf_counter()
        scan_result: FileScanResult = await asyncio.to_thread(
            self.scanner.scan, repo_path
        )
        duration = time.perf_counter() - start

        self.summary["files_scanned"] = len(scan_result.files)
        self.summary["errors"].extend(scan_result.errors)
        self.summary["files_failed"] = len(self.summary["errors"])

        stage_payload = {
            "files_scanned": len(scan_result.files),
            "skipped": scan_result.skipped,
            "duration_seconds": duration,
            "languages": scan_result.language_breakdown,
        }
        await self._update_stage(
            "file_scan",
            progress=self.STAGE_PROGRESS["file_scan"],
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload=stage_payload,
            message="Repository scanned",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )
        return scan_result

    async def _parse_repository(
        self,
        scan_result: FileScanResult,
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ) -> tuple[List[ParsedFile], ParseSummary]:
        start = time.perf_counter()
        parsed_files, parse_errors, summary = await asyncio.to_thread(
            self.parser.parse,
            scan_result.files,
        )
        duration = time.perf_counter() - start

        self.summary["files_parsed"] = summary.files_parsed
        self.summary["functions_extracted"] = summary.functions_extracted
        self.summary["imports_extracted"] = summary.imports_extracted
        self.summary["errors"].extend(parse_errors)
        self.summary["files_failed"] = len(self.summary["errors"])

        stage_payload = {
            "files_parsed": summary.files_parsed,
            "functions_extracted": summary.functions_extracted,
            "imports_extracted": summary.imports_extracted,
            "parse_errors": parse_errors,
            "duration_seconds": duration,
        }
        await self._update_stage(
            "code_parse",
            progress=self.STAGE_PROGRESS["code_parse"],
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload=stage_payload,
            message="Code parsed",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )
        return parsed_files, summary

    async def _embed_functions(
        self,
        parsed_files: List[ParsedFile],
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ) -> EmbeddingSummary:
        start = time.perf_counter()

        embed_payloads: List[str] = []
        for parsed in parsed_files:
            try:
                file_text = parsed.file.absolute_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:  # pragma: no cover - filesystem edge case
                logger.debug("Failed to read file for embedding stage {}: {}", parsed.file.relative_path, exc)
                file_text = ""

            lines = file_text.splitlines() if file_text else []
            for function in parsed.functions:
                snippet = ""
                if lines:
                    start_line = max(function.start_line - 1, 0)
                    end_line = max(function.end_line, function.start_line)
                    snippet = "\n".join(lines[start_line:end_line])

                text_parts = [
                    f"Function: {function.name}",
                    f"Language: {function.language}",
                    f"File: {function.file_path.as_posix()}",
                    f"Lines: {function.start_line}-{function.end_line}",
                    "\n",
                    snippet,
                ]
                embed_payloads.append("\n".join(text_parts))

        vectors = await self.embedding_client.embed_texts(embed_payloads)
        duration = time.perf_counter() - start

        embedding_dimension = len(vectors[0]) if vectors else self.embedding_client.dimension
        summary = EmbeddingSummary(
            functions_embedded=len(vectors),
            embedding_dimension=embedding_dimension,
            average_magnitude=self.embedding_client.average_magnitude(vectors),
        )

        stage_payload = {
            "functions_embedded": summary.functions_embedded,
            "average_magnitude": summary.average_magnitude,
            "embedding_dimension": summary.embedding_dimension,
            "duration_seconds": duration,
        }
        self.summary["functions_embedded"] = summary.functions_embedded
        self.summary["embedding_dimension"] = summary.embedding_dimension
        await self._update_stage(
            "embedding",
            progress=self.STAGE_PROGRESS["embedding"],
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload=stage_payload,
            message="Embeddings generated",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )
        return summary

    async def _build_graph(
        self,
        parsed_files: List[ParsedFile],
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
        *,
        source_id: Optional[str],
    ) -> GraphBuildResult:
        job_label = str(job_uuid) if job_uuid else "in-memory job"
        logger.info(
            "Job {} entering graph_build stage with {} parsed files.",
            job_label,
            len(parsed_files),
        )
        start = time.perf_counter()
        result = await self.graph_builder.build(parsed_files, source_id=source_id)
        duration = time.perf_counter() - start

        self.summary["nodes_created"] = result.nodes_created
        self.summary["edges_created"] = result.edges_created
        self.summary["languages"] = result.languages

        stage_payload = {
            "nodes_created": result.nodes_created,
            "edges_created": result.edges_created,
            "languages": result.languages,
            "duration_seconds": duration,
        }
        await self._update_stage(
            "graph_build",
            progress=self.STAGE_PROGRESS["graph_build"],
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload=stage_payload,
            message="Graph metadata updated",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )
        logger.info(
            "Job {} graph_build stage completed in {:.2f} seconds (nodes={}, edges={}).",
            job_label,
            duration,
            result.nodes_created,
            result.edges_created,
        )
        return result

    async def _build_knowledge_index(
        self,
        parsed_files: List[ParsedFile],
        job_uuid: Optional[uuid.UUID],
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
        *,
        source_id: Optional[str],
        source_name: Optional[str],
    ) -> Dict[str, Any]:
        """Build knowledge index for GraphRAG from parsed files."""
        from llama_index.core import Document
        from services.neo4j_knowledge_service import neo4j_knowledge_service

        job_label = str(job_uuid) if job_uuid else "in-memory job"

        if not parsed_files:
            logger.info(
                "Job {} has no parsed files, skipping knowledge index stage.", job_label
            )
            return {"documents_created": 0, "skipped": True}

        logger.info(
            "Job {} entering knowledge_index stage with {} parsed files.",
            job_label,
            len(parsed_files),
        )

        start = time.perf_counter()
        documents_created = 0

        # 确保服务已初始化（应该在应用启动时已初始化）
        if not neo4j_knowledge_service._initialized:
            logger.warning(
                "Knowledge service not initialized, attempting to initialize..."
            )
            try:
                await neo4j_knowledge_service.initialize()
            except Exception as exc:
                logger.error("Failed to initialize knowledge service: {}", exc)
                return {"documents_created": 0, "error": str(exc)}

        knowledge_index = getattr(neo4j_knowledge_service, "knowledge_index", None)
        if not knowledge_index:
            logger.warning(
                "Knowledge index not initialized, skipping knowledge indexing"
            )
            return {"documents_created": 0, "skipped": True}

        documents: List[Document] = []
        for parsed_file in parsed_files:
            scanned = parsed_file.file
            file_path = scanned.relative_path.as_posix()
            language = scanned.language or "unknown"

            try:
                file_text = scanned.absolute_path.read_text(
                    encoding="utf-8", errors="ignore"
                )
            except Exception as exc:  # pragma: no cover - filesystem edge case
                logger.debug("Failed to read snippet for {}: {}", file_path, exc)
                file_text = ""

            # 文件级文档
            content_parts: List[str] = [f"# 文件: {file_path}"]
            if source_name:
                content_parts.append(f"所属仓库: {source_name}")
            content_parts.append(f"\n编程语言: {language}")

            function_names = [fn.name for fn in (parsed_file.functions or [])]
            if function_names:
                content_parts.append("\n## 函数列表")
                for name in function_names[:15]:
                    content_parts.append(f"- {name}")

            class_names = list(parsed_file.classes or [])
            if class_names:
                content_parts.append("\n## 类列表")
                for name in class_names[:10]:
                    content_parts.append(f"- {name}")

            import_modules = [
                imp.module
                for imp in (parsed_file.imports or [])
                if getattr(imp, "module", None)
            ]
            if import_modules:
                content_parts.append("\n## 导入模块")
                for module in import_modules[:10]:
                    content_parts.append(f"- {module}")

            snippet = (file_text or "")[:800]
            if snippet.strip():
                content_parts.append("\n## 代码摘要")
                content_parts.append(snippet)

            metadata = {
                "source_type": "code_file",
                "file_path": file_path,
                "language": language,
                "function_count": len(function_names),
                "class_count": len(class_names),
            }
            if source_id:
                metadata["source_id"] = source_id
            if source_name:
                metadata["source_name"] = source_name
            documents.append(Document(text="\n".join(content_parts), metadata=metadata))

            # 函数级文档
            if file_text:
                lines = file_text.splitlines()
            else:
                lines = []

            for fn in parsed_file.functions:
                fn_lines: List[str] = []
                if lines:
                    start = max(fn.start_line - 1, 0)
                    end = max(fn.end_line, fn.start_line)
                    fn_lines = lines[start:end]
                fn_snippet = "\n".join(fn_lines)[:1500]

                fn_metadata = {
                    "source_type": "code_function",
                    "function_name": fn.name,
                    "file_path": file_path,
                    "language": fn.language,
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                }
                if source_id:
                    fn_metadata["source_id"] = source_id
                if source_name:
                    fn_metadata["source_name"] = source_name

                fn_text_parts = [
                    f"# 函数: {fn.name}",
                    f"文件: {file_path}",
                    f"语言: {fn.language}",
                    f"行号: {fn.start_line}-{fn.end_line}",
                    "\n## 代码实现",
                    fn_snippet or "(内容缺失)",
                ]
                documents.append(Document(text="\n".join(fn_text_parts), metadata=fn_metadata))

        if documents:
            try:
                inserted = await neo4j_knowledge_service.insert_documents(documents)
                documents_created += inserted
            except Exception as exc:  # pragma: no cover - downstream service failure
                logger.error("Failed to insert documents into vector index: {}", exc)

        duration = time.perf_counter() - start

        self.summary["knowledge_documents"] = documents_created

        result = {
            "documents_created": documents_created,
            "duration_seconds": duration,
        }

        await self._update_stage(
            "knowledge_index",
            progress=self.STAGE_PROGRESS["knowledge_index"],
            job_uuid=job_uuid,
            status=ParseStatus.RUNNING,
            payload=result,
            message=f"Created {documents_created} knowledge documents",
            progress_callback=progress_callback,
            task_progress_callback=task_progress_callback,
        )

        logger.info(
            "Job {} knowledge_index stage completed in {:.2f} seconds (documents={}).",
            job_label,
            duration,
            documents_created,
        )

        return result

    async def _update_stage(
        self,
        stage: str,
        *,
        progress: float,
        job_uuid: Optional[uuid.UUID],
        status: ParseStatus,
        payload: Optional[Dict[str, Any]],
        message: str,
        progress_callback: Optional[Callable[[float, str], None]],
        task_progress_callback: Optional[Callable[[float, str], None]],
    ) -> None:
        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        stage_entry = {"stage": stage, "message": message, "timestamp": timestamp}
        if payload:
            stage_entry.update(payload)

        self.summary["stage"] = stage
        self.summary.setdefault("stage_history", []).append(stage_entry)

        if job_uuid:
            await update_job_with_new_session(
                job_uuid,
                ParseJobUpdate(
                    status=status,
                    progress_percentage=int(progress),
                    result_summary=copy.deepcopy(self.summary),
                ),
            )

        if progress_callback:
            progress_callback(progress, message)
        if task_progress_callback:
            # Convert percentage (0-100) to decimal (0.0-1.0) for task storage
            task_progress_callback(progress / 100.0, message)

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        return list(value)


__all__ = ["CodeIndexingPipeline", "CodeIndexingResult"]
