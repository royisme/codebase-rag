import asyncio
import importlib.util
from pathlib import Path
from typing import Dict

import pytest

try:
    spec = importlib.util.spec_from_file_location(
        "codebase_rag.services.knowledge.pipeline_components",
        Path("src/codebase_rag/services/knowledge/pipeline_components.py"),
    )
    pipeline_components = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(pipeline_components)
except ImportError:  # pragma: no cover - dependency mismatch
    pipeline_components = None
    build_pipeline_bundle = merge_pipeline_configs = None
else:
    build_pipeline_bundle = pipeline_components.build_pipeline_bundle
    merge_pipeline_configs = pipeline_components.merge_pipeline_configs

pytestmark = pytest.mark.skipif(
    pipeline_components is None, reason="llama_index could not be imported"
)


class DummyKnowledgeIndex:
    def __init__(self) -> None:
        self.inserted_nodes = []

    def insert_nodes(self, nodes):
        self.inserted_nodes.extend(nodes)


class DummyGraphStore:
    pass


@pytest.mark.asyncio
async def test_build_pipeline_bundle_executes_pipeline():
    config: Dict[str, Dict] = {
        "connector": {
            "class_path": "codebase_rag.services.knowledge.pipeline_components.ManualDocumentConnector",
            "kwargs": {"metadata": {"source": "test"}},
        },
        "transformations": [
            {
                "class_path": "llama_index.core.node_parser.SimpleNodeParser",
                "kwargs": {"chunk_size": 64, "chunk_overlap": 0},
            },
        ],
        "writer": {
            "class_path": "codebase_rag.services.knowledge.pipeline_components.Neo4jKnowledgeGraphWriter",
        },
    }

    knowledge_index = DummyKnowledgeIndex()
    bundle = build_pipeline_bundle(
        "test",
        knowledge_index=knowledge_index,
        graph_store=DummyGraphStore(),
        configuration=config,
    )

    connector = bundle.instantiate_connector(content="hello world", title="Test")
    documents = await connector.aload_data()
    assert len(documents) == 1

    nodes = await asyncio.to_thread(
        bundle.pipeline.run,
        False,
        documents,
    )
    assert nodes, "Pipeline should produce nodes"

    bundle.writer.write(nodes)
    assert knowledge_index.inserted_nodes, "Writer should forward nodes to knowledge index"


def test_merge_pipeline_configs_allows_override():
    default = {
        "file": {
            "connector": {"class_path": "default.Connector"},
            "transformations": [],
            "writer": {"class_path": "default.Writer"},
        }
    }
    override = {
        "file": {
            "connector": {"kwargs": {"recursive": False}},
        },
        "custom": {
            "connector": {"class_path": "custom.Connector"},
            "transformations": [],
            "writer": {"class_path": "custom.Writer"},
        },
    }

    merged = merge_pipeline_configs(default, override)
    assert merged["file"]["connector"]["class_path"] == "default.Connector"
    assert merged["file"]["connector"]["kwargs"] == {"recursive": False}
    assert "custom" in merged
