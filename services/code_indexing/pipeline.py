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

from config import settings
from database.models import ParseStatus
from schemas import ParseJobUpdate
from services.source_service import SourceService

from .code_parser import CodeParser, ParseSummary, ParsedFile
from .embedding import DeterministicEmbeddingGenerator, EmbeddingSummary
from .file_scanner import FileScanner, FileScanResult
from .git_sync import GitSyncService, GitSyncResult
from .graph_builder import GraphBuilder, GraphBuildResult


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
        "file_scan": 35,
        "code_parse": 60,
        "embedding": 80,
        "graph_build": 95,
    }

    def __init__(
        self,
        *,
        source_service: SourceService,
        session,
        neo4j_service=None,
    ) -> None:
        self.source_service = source_service
        self.session = session
        self.neo4j_service = neo4j_service

        self.git_service = GitSyncService()
        self.scanner = FileScanner(
            include_patterns=settings.code_include_patterns,
            exclude_patterns=settings.code_exclude_patterns,
            max_file_size_kb=settings.code_max_file_size_kb,
        )
        self.parser = CodeParser()
        self.embedder = DeterministicEmbeddingGenerator()
        self.graph_builder = GraphBuilder(neo4j_service=neo4j_service)

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

        connection_config = dict(source.connection_config or {})
        overrides: Dict[str, Any] = {}

        if isinstance(sync_config, dict):
            nested = sync_config.get("connection_config")
            if isinstance(nested, dict):
                overrides.update(nested)

            for key, value in sync_config.items():
                if key == "connection_config":
                    continue
                overrides[key] = value

        if overrides:
            connection_config.update({k: v for k, v in overrides.items() if v is not None})

        depth_override = overrides.get("git_depth") or overrides.get("clone_depth")
        if depth_override is None:
            depth_override = connection_config.get("git_depth") or connection_config.get("clone_depth")
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
        include_patterns = connection_config.get("include_patterns") or settings.code_include_patterns
        exclude_patterns = connection_config.get("exclude_patterns") or settings.code_exclude_patterns
        max_file_size_kb = connection_config.get("max_file_size_kb") or settings.code_max_file_size_kb

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
            job_uuid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))
        repo_path = Path(settings.code_repo_root) / str(source.id)

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
        )

        duration = time.perf_counter() - start_time

        # Update knowledge source metadata
        source.source_metadata = {
            "last_commit_sha": git_result.commit_sha,
            "total_files": len(scan_result.files),
            "total_functions": parse_summary.functions_extracted,
            "languages": graph_result.languages,
            "graph_nodes": graph_result.nodes_created,
            "graph_edges": graph_result.edges_created,
            "index_version": "mvp-1",
            "embedding_dimension": embedding_summary.embedding_dimension,
        }

        self.summary["duration_seconds"] = duration
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
        scan_result: FileScanResult = await asyncio.to_thread(self.scanner.scan, repo_path)
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
        functions = [function for parsed in parsed_files for function in parsed.functions]
        summary = await asyncio.to_thread(self.embedder.generate, functions)
        duration = time.perf_counter() - start

        stage_payload = {
            "functions_embedded": summary.functions_embedded,
            "average_magnitude": summary.average_magnitude,
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
    ) -> GraphBuildResult:
        start = time.perf_counter()
        result = await self.graph_builder.build(parsed_files)
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
            await self.source_service.update_job(
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
            task_progress_callback(progress, message)

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
