"""Reusable ingestion pipeline components for the Neo4j knowledge service."""

from __future__ import annotations

import asyncio
import copy
import time
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Type

from llama_index.core import Document
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import BaseNode, TransformComponent

from codebase_rag.config import settings

try:  # pragma: no cover - optional dependency surface differs by version
    from llama_index.core.ingestion import BaseConnector, BaseWriter
except ImportError:  # pragma: no cover
    from typing import Protocol

    class BaseConnector(Protocol):  # type: ignore[misc]
        """Minimal connector protocol used for runtime type checking."""

        def load_data(self) -> Sequence[Document]:
            ...

        async def aload_data(self) -> Sequence[Document]:
            ...

    class BaseWriter(Protocol):  # type: ignore[misc]
        """Minimal writer protocol used for runtime type checking."""

        def write(self, nodes: Sequence[BaseNode]) -> None:
            ...

        async def awrite(self, nodes: Sequence[BaseNode]) -> None:
            ...


class BaseTransformation(TransformComponent):
    """Alias for TransformComponent for readability."""

    # TransformComponent already implements __call__/acall


class ManualDocumentConnector(BaseConnector):
    """Connector that materialises a single document from raw text input."""

    def __init__(
        self,
        content: str,
        *,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._content = content
        self._title = title or "Untitled"
        self._metadata = metadata or {}

    def _build_document(self) -> Document:
        base_metadata = {
            "title": self._title,
            "source": self._metadata.get("source", "manual_input"),
            "timestamp": self._metadata.get("timestamp", time.time()),
        }
        merged_metadata = {**base_metadata, **self._metadata}
        return Document(text=self._content, metadata=merged_metadata)

    def load_data(self) -> Sequence[Document]:
        return [self._build_document()]

    async def aload_data(self) -> Sequence[Document]:
        return self.load_data()


class SimpleFileConnector(BaseConnector):
    """Connector that loads a single file via SimpleDirectoryReader."""

    def __init__(self, file_path: str | Path, **reader_kwargs: Any) -> None:
        self._file_path = Path(file_path)
        self._reader_kwargs = reader_kwargs

    def load_data(self) -> Sequence[Document]:
        from llama_index.core import SimpleDirectoryReader

        reader = SimpleDirectoryReader(
            input_files=[str(self._file_path)],
            **self._reader_kwargs,
        )
        return reader.load_data()

    async def aload_data(self) -> Sequence[Document]:
        return await asyncio.to_thread(self.load_data)


class SimpleDirectoryConnector(BaseConnector):
    """Connector that loads all supported files from a directory."""

    def __init__(
        self,
        directory_path: str | Path,
        *,
        recursive: bool = True,
        file_extensions: Optional[Sequence[str]] = None,
        reader_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._directory_path = Path(directory_path)
        self._recursive = recursive
        self._file_extensions = list(file_extensions or [])
        self._reader_kwargs = reader_kwargs or {}

    def load_data(self) -> Sequence[Document]:
        from llama_index.core import SimpleDirectoryReader

        file_extractor = None
        if self._file_extensions:
            file_extractor = {ext: None for ext in self._file_extensions}

        reader = SimpleDirectoryReader(
            input_dir=str(self._directory_path),
            recursive=self._recursive,
            file_extractor=file_extractor,
            **self._reader_kwargs,
        )
        return reader.load_data()

    async def aload_data(self) -> Sequence[Document]:
        return await asyncio.to_thread(self.load_data)


class MetadataEnrichmentTransformation(BaseTransformation):
    """Inject static metadata into every processed node."""

    def __init__(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._metadata = metadata or {}

    def __call__(self, nodes: Sequence[BaseNode], **kwargs: Any) -> Sequence[BaseNode]:
        for node in nodes:
            node.metadata.update(self._metadata)
        return nodes


class Neo4jKnowledgeGraphWriter(BaseWriter):
    """Writer that persists nodes through the KnowledgeGraphIndex."""

    def __init__(self, knowledge_index, graph_store) -> None:
        self._knowledge_index = knowledge_index
        self._graph_store = graph_store

    def write(self, nodes: Sequence[BaseNode]) -> None:
        if not nodes:
            return
        self._knowledge_index.insert_nodes(nodes)

    async def awrite(self, nodes: Sequence[BaseNode]) -> None:
        if not nodes:
            return
        await asyncio.to_thread(self._knowledge_index.insert_nodes, nodes)


@dataclass
class PipelineBundle:
    """Container for an ingestion pipeline and its runtime dependencies."""

    name: str
    connector_cls: Type[BaseConnector]
    connector_kwargs: Dict[str, Any]
    pipeline: IngestionPipeline
    writer: BaseWriter

    def instantiate_connector(self, **overrides: Any) -> BaseConnector:
        params = {**self.connector_kwargs, **overrides}
        return self.connector_cls(**params)


def import_from_string(dotted_path: str) -> Any:
    """Import a class from a dotted module path."""

    module_path, _, attribute = dotted_path.rpartition(".")
    if not module_path:
        raise ImportError(f"Invalid class path (must contain at least one dot): {dotted_path}")
    module = import_module(module_path)
    try:
        return getattr(module, attribute)
    except AttributeError as exc:  # pragma: no cover - invalid config
        raise ImportError(f"Module '{module_path}' has no attribute '{attribute}'") from exc


def build_pipeline_bundle(
    name: str,
    *,
    knowledge_index,
    graph_store,
    configuration: Dict[str, Any],
) -> PipelineBundle:
    """Construct a PipelineBundle from configuration metadata."""

    connector_cfg = configuration.get("connector", {})
    connector_cls = import_from_string(connector_cfg.get("class_path", ""))
    connector_kwargs = connector_cfg.get("kwargs", {})

    transformations: List[TransformComponent] = []
    for transform_cfg in configuration.get("transformations", []):
        transform_cls = import_from_string(transform_cfg["class_path"])
        kwargs = transform_cfg.get("kwargs", {})
        transformations.append(transform_cls(**kwargs))

    if not transformations:
        from llama_index.core.node_parser import SimpleNodeParser

        transformations.append(
            SimpleNodeParser.from_defaults(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        )

    writer_cfg = configuration.get("writer", {})
    writer_cls = import_from_string(writer_cfg.get("class_path", ""))
    writer_kwargs = writer_cfg.get("kwargs", {})
    writer = writer_cls(knowledge_index=knowledge_index, graph_store=graph_store, **writer_kwargs)

    pipeline = IngestionPipeline(transformations=transformations)
    return PipelineBundle(
        name=name,
        connector_cls=connector_cls,
        connector_kwargs=connector_kwargs,
        pipeline=pipeline,
        writer=writer,
    )


def merge_pipeline_configs(
    default_config: Dict[str, Dict[str, Any]],
    override_config: Optional[Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    """Merge user supplied pipeline configuration with defaults."""

    def _merge_values(default: Any, override: Any) -> Any:
        if isinstance(default, dict) and isinstance(override, dict):
            merged_dict: Dict[str, Any] = {}
            for key in default.keys() | override.keys():
                if key in override:
                    if key in default:
                        merged_dict[key] = _merge_values(default[key], override[key])
                    else:
                        merged_dict[key] = copy.deepcopy(override[key])
                else:
                    merged_dict[key] = copy.deepcopy(default[key])
            return merged_dict
        if isinstance(override, dict):
            return copy.deepcopy(override)
        return copy.deepcopy(override)

    merged = copy.deepcopy(default_config)
    if not override_config:
        return merged

    for key, value in override_config.items():
        if key in merged:
            merged[key] = _merge_values(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged

