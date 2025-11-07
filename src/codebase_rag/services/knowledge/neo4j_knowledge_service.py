
"""
modern knowledge graph service based on Neo4j's native vector index
uses LlamaIndex's KnowledgeGraphIndex and Neo4j's native vector search functionality
supports multiple LLM and embedding model providers
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
from loguru import logger
import time

from llama_index.core import (
    KnowledgeGraphIndex,
    Settings,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.indices.knowledge_graph import KnowledgeGraphRAGRetriever
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.schema import QueryBundle, NodeWithScore

# LLM Providers
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from llama_index.llms.gemini import Gemini
from llama_index.llms.openrouter import OpenRouter

# Embedding Providers
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.gemini import GeminiEmbedding

# Graph Store
from llama_index.graph_stores.neo4j import Neo4jGraphStore

# Tools / workflow
from llama_index.core.tools import FunctionTool
try:  # Optional dependency for advanced workflow integration
    from llama_index.core.workflow.tool_node import ToolNode
except Exception:  # pragma: no cover - optional runtime dependency
    ToolNode = None  # type: ignore

from codebase_rag.config import settings
from codebase_rag.services.knowledge.pipeline_components import (
    PipelineBundle,
    build_pipeline_bundle,
    merge_pipeline_configs,
)


# =========================
# Retrieval Pipeline Config
# =========================

@dataclass
class PipelineConfig:
    """Configuration for running a retrieval pipeline."""

    run_graph: bool = True
    run_vector: bool = True
    run_tools: bool = False
    top_k: int = 5
    graph_depth: int = 2
    tool_kwargs: Dict[str, Any] = field(default_factory=dict)


class Neo4jRAGPipeline:
    """Lightweight query pipeline that orchestrates graph/vector retrieval and synthesis."""

    def __init__(
        self,
        storage_context: StorageContext,
        response_synthesizer,
        llm,
        *,
        default_top_k: int = 5,
        default_graph_depth: int = 2,
        max_knowledge_sequence: int = 30,
        verbose: bool = False,
        vector_index: Optional[VectorStoreIndex] = None,
        function_tools: Optional[List[FunctionTool]] = None,
        tool_node: Optional["ToolNode"] = None,
    ) -> None:
        self.storage_context = storage_context
        self.response_synthesizer = response_synthesizer
        self.llm = llm
        self.default_top_k = default_top_k
        self.default_graph_depth = default_graph_depth
        self.max_knowledge_sequence = max_knowledge_sequence
        self.verbose = verbose
        self.vector_index = vector_index
        self.function_tools = function_tools or []
        self.tool_node = tool_node

    def _merge_nodes(
        self,
        aggregated: Dict[str, NodeWithScore],
        nodes: List[NodeWithScore],
    ) -> None:
        """Merge retrieved nodes by keeping the highest scoring entry per node id."""
        for node in nodes:
            node_id = node.node.node_id if getattr(node, "node", None) else node.node_id
            if node_id not in aggregated or (
                (aggregated[node_id].score or 0) < (node.score or 0)
            ):
                aggregated[node_id] = node

    @staticmethod
    def _summarize_nodes(nodes: List[NodeWithScore]) -> List[Dict[str, Any]]:
        """Return a lightweight representation of retrieved nodes for tracing."""
        summaries: List[Dict[str, Any]] = []
        for node in nodes:
            text = ""
            try:
                text = node.get_text() or ""
            except Exception:
                text = getattr(node, "text", "") or ""
            if len(text) > 200:
                text = text[:200] + "..."
            summaries.append(
                {
                    "node_id": node.node.node_id if getattr(node, "node", None) else node.node_id,
                    "score": node.score,
                    "metadata": dict(getattr(getattr(node, "node", None), "metadata", {}) or {}),
                    "text": text,
                }
            )
        return summaries

    def run(self, question: str, config: PipelineConfig) -> Dict[str, Any]:
        """Execute the pipeline synchronously."""
        query_bundle = QueryBundle(query_str=question)
        aggregated_nodes: Dict[str, NodeWithScore] = {}
        pipeline_steps: List[Dict[str, Any]] = []

        # Graph retrieval
        if config.run_graph:
            graph_retriever = KnowledgeGraphRAGRetriever(
                storage_context=self.storage_context,
                llm=self.llm,
                graph_traversal_depth=config.graph_depth or self.default_graph_depth,
                max_knowledge_sequence=self.max_knowledge_sequence,
                verbose=self.verbose,
            )
            graph_nodes = graph_retriever.retrieve(query_bundle)
            self._merge_nodes(aggregated_nodes, graph_nodes)
            pipeline_steps.append(
                {
                    "step": "graph_retrieval",
                    "node_count": len(graph_nodes),
                    "config": {
                        "graph_traversal_depth": config.graph_depth or self.default_graph_depth,
                        "max_knowledge_sequence": self.max_knowledge_sequence,
                    },
                    "nodes": self._summarize_nodes(graph_nodes),
                }
            )

        # Vector retrieval
        if config.run_vector and self.vector_index is not None:
            vector_retriever = VectorIndexRetriever(
                self.vector_index,
                similarity_top_k=config.top_k or self.default_top_k,
            )
            vector_nodes = vector_retriever.retrieve(query_bundle)
            self._merge_nodes(aggregated_nodes, vector_nodes)
            pipeline_steps.append(
                {
                    "step": "vector_retrieval",
                    "node_count": len(vector_nodes),
                    "config": {"top_k": config.top_k or self.default_top_k},
                    "nodes": self._summarize_nodes(vector_nodes),
                }
            )

        aggregated_list = list(aggregated_nodes.values())
        response = self.response_synthesizer.synthesize(query_bundle, aggregated_list)
        source_nodes = getattr(response, "source_nodes", aggregated_list)

        tool_outputs: List[Dict[str, Any]] = []
        if config.run_tools:
            if self.tool_node is not None:
                try:
                    payload = {"input": question, **(config.tool_kwargs or {})}
                    if hasattr(self.tool_node, "invoke"):
                        result = self.tool_node.invoke(payload)
                    elif callable(self.tool_node):
                        result = self.tool_node(payload)
                    else:
                        raise RuntimeError("Unsupported ToolNode interface")
                    tool_outputs.append(
                        {
                            "tool": getattr(result, "tool_name", "tool_node"),
                            "output": getattr(result, "raw_output", str(result)),
                            "is_error": getattr(result, "is_error", False),
                        }
                    )
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(f"Tool node execution failed: {exc}")
                    tool_outputs.append(
                        {"tool": "tool_node", "error": str(exc), "is_error": True}
                    )
            elif self.function_tools:
                for tool in self.function_tools:
                    try:
                        result = tool(question=question, **(config.tool_kwargs or {}))
                        tool_outputs.append(
                            {
                                "tool": result.tool_name,
                                "output": result.raw_output,
                                "is_error": result.is_error,
                            }
                        )
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.warning(f"Function tool execution failed: {exc}")
                        tool_outputs.append(
                            {"tool": tool.metadata.name, "error": str(exc), "is_error": True}
                        )

        return {
            "response": response,
            "source_nodes": source_nodes,
            "retrieved_nodes": aggregated_list,
            "steps": pipeline_steps,
            "tool_outputs": tool_outputs,
        }


# ======================
# Knowledge Service Main
# ======================

class Neo4jKnowledgeService:
    """knowledge graph service based on Neo4j's native vector index"""

    def __init__(self):
        self.graph_store = None
        self.storage_context: Optional[StorageContext] = None
        self.knowledge_index = None
        self.vector_index: Optional[VectorStoreIndex] = None
        self.response_synthesizer = None
        self.query_pipeline: Optional[Neo4jRAGPipeline] = None

        # tools / workflow
        self.function_tools: List[FunctionTool] = []
        self.tool_node: Optional["ToolNode"] = None

        # ingestion pipelines
        self._pipeline_bundles: Dict[str, PipelineBundle] = {}

        self._initialized = False

        # get timeout settings from config
        self.connection_timeout = settings.connection_timeout
        self.operation_timeout = settings.operation_timeout
        self.large_document_timeout = settings.large_document_timeout

        logger.info("Neo4j Knowledge Service created")

    # --------------------------
    # LLM / Embedding factories
    # --------------------------

    def _create_llm(self):
        """create LLM instance based on config"""
        provider = settings.llm_provider.lower()

        if provider == "ollama":
            return Ollama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.temperature,
                request_timeout=self.operation_timeout,
            )
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI provider")
            return OpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                api_base=settings.openai_base_url,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                timeout=self.operation_timeout,
            )
        elif provider == "gemini":
            if not settings.google_api_key:
                raise ValueError("Google API key is required for Gemini provider")
            return Gemini(
                model=settings.gemini_model,
                api_key=settings.google_api_key,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
        elif provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("OpenRouter API key is required for OpenRouter provider")
            return OpenRouter(
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                temperature=settings.temperature,
                max_tokens=settings.openrouter_max_tokens,
                timeout=self.operation_timeout,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _create_embedding_model(self):
        """create embedding model instance based on config"""
        provider = settings.embedding_provider.lower()

        if provider == "ollama":
            return OllamaEmbedding(
                model_name=settings.ollama_embedding_model,
                base_url=settings.ollama_base_url,
                request_timeout=self.operation_timeout,
            )
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError(
                    "OpenAI API key is required for OpenAI embedding provider"
                )
            return OpenAIEmbedding(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
                api_base=settings.openai_base_url,
                timeout=self.operation_timeout,
            )
        elif provider == "gemini":
            if not settings.google_api_key:
                raise ValueError(
                    "Google API key is required for Gemini embedding provider"
                )
            return GeminiEmbedding(
                model_name=settings.gemini_embedding_model,
                api_key=settings.google_api_key,
            )
        elif provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError(
                    "OpenRouter API key is required for OpenRouter embedding provider"
                )
            return OpenAIEmbedding(
                model=settings.openrouter_embedding_model,
                api_key=settings.openrouter_api_key,
                api_base=settings.openrouter_base_url,
                timeout=self.operation_timeout,
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    # --------------
    # Tool registry
    # --------------

    def _register_tools(self) -> None:
        """Create FunctionTool/ToolNode hooks for workflow integration."""
        self.function_tools = []
        try:
            tool = FunctionTool.from_defaults(
                fn=self._tool_query,
                name="neo4j_knowledge_query",
                description="Run a Neo4j knowledge service query via the retrieval pipeline.",
            )
            self.function_tools.append(tool)
        except Exception as exc:  # pragma: no cover - best-effort registration
            logger.warning(f"Failed to register FunctionTool: {exc}")

        if ToolNode is not None and self.function_tools:
            try:
                self.tool_node = ToolNode(self.function_tools)
            except Exception as exc:  # pragma: no cover - optional dep
                logger.warning(f"Failed to initialize ToolNode: {exc}")
                self.tool_node = None

        if self.query_pipeline is not None:
            self.query_pipeline.function_tools = self.function_tools
            self.query_pipeline.tool_node = self.tool_node

    # -----------------------
    # Retrieval pipeline (RAG)
    # -----------------------

    def _build_pipeline(self) -> None:
        """(Re)build the retrieval pipeline and refresh tool bindings."""
        if self.storage_context is None:
            raise RuntimeError("Storage context is not available")
        if self.response_synthesizer is None:
            raise RuntimeError("Response synthesizer is not available")

        self.query_pipeline = Neo4jRAGPipeline(
            storage_context=self.storage_context,
            response_synthesizer=self.response_synthesizer,
            llm=Settings.llm,
            default_top_k=settings.top_k,
            default_graph_depth=2,
            max_knowledge_sequence=30,
            verbose=settings.debug,
            vector_index=self.vector_index,
        )
        self._register_tools()

    # -----------------------
    # Ingestion pipeline (ETL)
    # -----------------------

    def _default_pipeline_configs(self) -> Dict[str, Dict[str, Any]]:
        """Return the built-in ingestion pipeline configuration."""
        node_parser_config = {
            "class_path": "llama_index.core.node_parser.SimpleNodeParser",
            "kwargs": {
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
            },
        }
        metadata_transform = (
            "codebase_rag.services.knowledge.pipeline_components.MetadataEnrichmentTransformation"
        )
        writer_path = (
            "codebase_rag.services.knowledge.pipeline_components.Neo4jKnowledgeGraphWriter"
        )

        return {
            "manual_input": {
                "connector": {
                    "class_path": "codebase_rag.services.knowledge.pipeline_components.ManualDocumentConnector",
                },
                "transformations": [
                    dict(node_parser_config),
                    {
                        "class_path": metadata_transform,
                        "kwargs": {"metadata": {"pipeline": "manual_input"}},
                    },
                ],
                "writer": {"class_path": writer_path},
            },
            "file": {
                "connector": {
                    "class_path": "codebase_rag.services.knowledge.pipeline_components.SimpleFileConnector",
                },
                "transformations": [
                    dict(node_parser_config),
                    {
                        "class_path": metadata_transform,
                        "kwargs": {"metadata": {"pipeline": "file"}},
                    },
                ],
                "writer": {"class_path": writer_path},
            },
            "directory": {
                "connector": {
                    "class_path": "codebase_rag.services.knowledge.pipeline_components.SimpleDirectoryConnector",
                    "kwargs": {
                        "recursive": True,
                        "file_extensions": [
                            ".txt",
                            ".md",
                            ".py",
                            ".js",
                            ".ts",
                            ".sql",
                            ".json",
                            ".yaml",
                            ".yml",
                        ],
                    },
                },
                "transformations": [
                    dict(node_parser_config),
                    {
                        "class_path": metadata_transform,
                        "kwargs": {"metadata": {"pipeline": "directory"}},
                    },
                ],
                "writer": {"class_path": writer_path},
            },
        }

    def _setup_ingestion_pipelines(self) -> None:
        """Build ingestion pipelines from defaults and user configuration."""
        default_config = self._default_pipeline_configs()
        merged_config = merge_pipeline_configs(default_config, settings.ingestion_pipelines)

        bundles: Dict[str, PipelineBundle] = {}
        for name, config in merged_config.items():
            try:
                bundles[name] = build_pipeline_bundle(
                    name,
                    knowledge_index=self.knowledge_index,
                    graph_store=self.graph_store,
                    configuration=config,
                )
                logger.debug(f"Built ingestion pipeline '{name}'")
            except Exception as exc:
                logger.error(f"Failed to build ingestion pipeline '{name}': {exc}")

        self._pipeline_bundles = bundles

    # -----------
    # Initialize
    # -----------

    async def initialize(self) -> bool:
        """initialize service"""
        try:
            logger.info(
                f"Initializing with LLM provider: {settings.llm_provider}, Embedding provider: {settings.embedding_provider}"
            )

            # set LlamaIndex global config
            Settings.llm = self._create_llm()
            Settings.embed_model = self._create_embedding_model()

            Settings.chunk_size = settings.chunk_size
            Settings.chunk_overlap = settings.chunk_overlap

            logger.info(
                f"LLM: {settings.llm_provider} - {getattr(settings, f'{settings.llm_provider}_model')}"
            )
            logger.info(
                f"Embedding: {settings.embedding_provider} - {getattr(settings, f'{settings.embedding_provider}_embedding_model')}"
            )

            # initialize Neo4j graph store, add timeout config
            self.graph_store = Neo4jGraphStore(
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                url=settings.neo4j_uri,
                database=settings.neo4j_database,
                timeout=self.connection_timeout,
            )

            # create storage context
            self.storage_context = StorageContext.from_defaults(
                graph_store=self.graph_store
            )

            # try to load existing index, if not exists, create new one
            try:
                self.knowledge_index = await asyncio.wait_for(
                    asyncio.to_thread(
                        KnowledgeGraphIndex.from_existing,
                        storage_context=self.storage_context,
                    ),
                    timeout=self.connection_timeout,
                )
                logger.info("Loaded existing knowledge graph index")
            except asyncio.TimeoutError:
                logger.warning("Loading existing index timed out, creating new index")
                self.knowledge_index = KnowledgeGraphIndex(
                    nodes=[],
                    storage_context=self.storage_context,
                    show_progress=True,
                )
                logger.info("Created new knowledge graph index")
            except Exception:
                # create empty knowledge graph index
                self.knowledge_index = KnowledgeGraphIndex(
                    nodes=[],
                    storage_context=self.storage_context,
                    show_progress=True,
                )
                logger.info("Created new knowledge graph index")

            # build vector index and response synthesizer
            self.vector_index = VectorStoreIndex.from_vector_store(
                self.storage_context.vector_store,
                embed_model=Settings.embed_model,
            )
            self.response_synthesizer = get_response_synthesizer(
                response_mode="tree_summarize",
                llm=Settings.llm,
            )

            # Build both query pipeline (RAG) and ingestion pipelines (ETL)
            self._build_pipeline()
            self._setup_ingestion_pipelines()

            self._initialized = True
            logger.success("Neo4j Knowledge Service initialized successfully")
            return True

            # End try
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j Knowledge Service: {e}")
            return False

    # -----------------
    # Querying (RAG)
    # -----------------

    def _resolve_pipeline_config(
        self,
        mode: str,
        *,
        use_graph: Optional[bool] = None,
        use_vector: Optional[bool] = None,
        use_tools: bool = False,
        top_k: Optional[int] = None,
        graph_depth: Optional[int] = None,
        tool_kwargs: Optional[Dict[str, Any]] = None,
    ) -> PipelineConfig:
        """Translate user configuration into a pipeline configuration."""
        mode = (mode or "hybrid").lower()
        run_graph = use_graph if use_graph is not None else mode in ("hybrid", "graph_only", "graph_first")
        run_vector = use_vector if use_vector is not None else mode in ("hybrid", "vector_only", "vector_first")

        if not run_graph and not run_vector:
            raise ValueError("At least one of graph or vector retrieval must be enabled")

        config = PipelineConfig()
        config.run_graph = run_graph
        config.run_vector = run_vector
        config.run_tools = use_tools
        config.top_k = top_k or settings.top_k
        config.graph_depth = graph_depth or 2
        config.tool_kwargs = tool_kwargs or {}
        return config

    def _format_source_nodes(self, nodes: List[NodeWithScore]) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for node in nodes:
            try:
                text = node.get_text() or ""
            except Exception:
                text = getattr(node, "text", "") or ""
            if len(text) > 200:
                text = text[:200] + "..."
            formatted.append(
                {
                    "node_id": node.node.node_id if getattr(node, "node", None) else node.node_id,
                    "text": text,
                    "metadata": dict(getattr(getattr(node, "node", None), "metadata", {}) or {}),
                    "score": node.score,
                }
            )
        return formatted

    def _tool_query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: Optional[int] = None,
        graph_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Synchronous query helper exposed to FunctionTool."""
        if self.query_pipeline is None:
            raise RuntimeError("Query pipeline is not initialized")

        config = self._resolve_pipeline_config(
            mode,
            top_k=top_k,
            graph_depth=graph_depth,
            use_tools=False,
        )
        result = self.query_pipeline.run(query, config)
        response = result["response"]
        source_nodes = self._format_source_nodes(result["source_nodes"])
        return {
            "answer": str(response),
            "sources": source_nodes,
            "pipeline_steps": result["steps"],
        }

    async def query(
        self,
        question: str,
        mode: str = "hybrid",
        *,
        use_graph: Optional[bool] = None,
        use_vector: Optional[bool] = None,
        use_tools: bool = False,
        top_k: Optional[int] = None,
        graph_depth: Optional[int] = None,
        tool_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """query knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")
        if self.query_pipeline is None:
            raise Exception("Query pipeline is not available")

        try:
            config = self._resolve_pipeline_config(
                mode,
                use_graph=use_graph,
                use_vector=use_vector,
                use_tools=use_tools,
                top_k=top_k,
                graph_depth=graph_depth,
                tool_kwargs=tool_kwargs,
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        try:
            pipeline_result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.query_pipeline.run,
                    question,
                    config,
                ),
                timeout=self.operation_timeout,
            )
        except asyncio.TimeoutError:
            error_msg = f"Query timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timeout": self.operation_timeout,
            }
        except Exception as e:
            logger.error(f"Failed to query: {e}")
            return {"success": False, "error": str(e)}

        response = pipeline_result["response"]
        source_nodes = self._format_source_nodes(pipeline_result["source_nodes"])

        logger.info(f"Successfully answered query: {question[:50]}...")

        return {
            "success": True,
            "answer": str(response),
            "source_nodes": source_nodes,
            "retrieved_nodes": self._format_source_nodes(pipeline_result["retrieved_nodes"]),
            "pipeline_steps": pipeline_result["steps"],
            "tool_outputs": pipeline_result["tool_outputs"],
            "query_mode": mode,
            "config": {
                "graph": config.run_graph,
                "vector": config.run_vector,
                "tools": config.run_tools,
                "top_k": config.top_k,
                "graph_depth": config.graph_depth,
            },
        }

    # -----------------
    # Ingestion helpers
    # -----------------

    async def _run_ingestion_pipeline(
        self,
        pipeline_name: str,
        *,
        connector_overrides: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        if pipeline_name not in self._pipeline_bundles:
            available_pipelines = ", ".join(self._pipeline_bundles.keys())
            raise ValueError(
                f"Pipeline '{pipeline_name}' is not configured. Available pipelines: {available_pipelines}"
            )
        bundle = self._pipeline_bundles[pipeline_name]
        connector = bundle.instantiate_connector(**connector_overrides)

        documents = await connector.aload_data()
        documents = list(documents)
        if not documents:
            return {
                "success": False,
                "error": f"Pipeline '{pipeline_name}' produced no documents",
            }

        timeout = timeout or self.operation_timeout
        total_chars = sum(len(doc.text) for doc in documents)
        logger.info(
            f"Running pipeline '{pipeline_name}' with {len(documents)} documents (total chars: {total_chars})"
        )

        def _process_pipeline() -> Dict[str, Any]:
            nodes = bundle.pipeline.run(show_progress=False, documents=documents)
            bundle.writer.write(nodes)
            return {
                "nodes_count": len(nodes),
                "documents_count": len(documents),
            }

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_process_pipeline),
                timeout=timeout,
            )
            logger.info(
                f"Pipeline '{pipeline_name}' completed with {result['nodes_count']} nodes"
            )
            return {
                "success": True,
                "pipeline": pipeline_name,
                "documents_count": result["documents_count"],
                "nodes_count": result["nodes_count"],
                "total_chars": total_chars,
            }
        except asyncio.TimeoutError:
            error_msg = f"Pipeline '{pipeline_name}' execution timed out after {timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": timeout}
        except Exception as exc:
            logger.error(f"Pipeline '{pipeline_name}' failed: {exc}")
            return {"success": False, "error": str(exc)}

    async def add_document(
        self,
        content: str,
        title: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """add document to knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")

        metadata = metadata or {}
        metadata.setdefault("title", title or metadata.get("title", "Untitled"))
        metadata.setdefault("source", metadata.get("source", "manual_input"))
        metadata.setdefault("timestamp", metadata.get("timestamp", time.time()))

        content_size = len(content)
        timeout = (
            self.operation_timeout if content_size < 10000 else self.large_document_timeout
        )

        result = await self._run_ingestion_pipeline(
            "manual_input",
            connector_overrides={
                "content": content,
                "title": title,
                "metadata": metadata,
            },
            timeout=timeout,
        )

        if result.get("success"):
            result.update({
                "message": f"Document '{metadata['title']}' added to knowledge graph",
                "content_size": content_size,
            })
        return result

    async def add_file(self, file_path: str) -> Dict[str, Any]:
        """add file to knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")

        absolute_path = str(Path(file_path).expanduser())
        result = await self._run_ingestion_pipeline(
            "file",
            connector_overrides={"file_path": absolute_path},
        )

        if result.get("success"):
            result.setdefault(
                "message",
                f"File '{absolute_path}' processed with {result.get('nodes_count', 0)} nodes",
            )
        else:
            result.setdefault("error", f"Failed to process file '{absolute_path}'")
        return result

    async def add_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        file_extensions: List[str] = None,
    ) -> Dict[str, Any]:
        """batch add files in directory"""
        if not self._initialized:
            raise Exception("Service not initialized")

        absolute_path = str(Path(directory_path).expanduser())
        overrides: Dict[str, Any] = {
            "directory_path": absolute_path,
            "recursive": recursive,
        }
        if file_extensions is not None:
            overrides["file_extensions"] = file_extensions

        result = await self._run_ingestion_pipeline(
            "directory",
            connector_overrides=overrides,
        )

        if result.get("success"):
            result.setdefault(
                "message",
                f"Directory '{absolute_path}' processed with {result.get('documents_count', 0)} documents",
            )
        else:
            result.setdefault("error", f"Failed to process directory '{absolute_path}'")
        return result

    # -----------------
    # Introspection / Ops
    # -----------------

    async def get_graph_schema(self) -> Dict[str, Any]:
        """get graph schema information"""
        if not self._initialized:
            raise Exception("Service not initialized")

        try:
            # get graph statistics, add timeout control
            schema_info = await asyncio.wait_for(
                asyncio.to_thread(self.graph_store.get_schema),
                timeout=self.connection_timeout,
            )

            return {"success": True, "schema": schema_info}

        except asyncio.TimeoutError:
            error_msg = f"Schema retrieval timed out after {self.connection_timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Failed to get graph schema: {e}")
            return {"success": False, "error": str(e)}

    async def search_similar_nodes(
        self,
        query: str,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """search nodes by vector similarity"""
        if not self._initialized:
            raise Exception("Service not initialized")

        try:
            # use retriever for vector search, add timeout control
            retriever = self.knowledge_index.as_retriever(
                similarity_top_k=top_k,
                include_text=True,
            )

            nodes = await asyncio.wait_for(
                asyncio.to_thread(retriever.retrieve, query),
                timeout=self.operation_timeout,
            )

            results = []
            for node in nodes:
                try:
                    text = node.get_text() if hasattr(node, "get_text") else node.text
                except Exception:
                    text = getattr(node, "text", "")
                if text and len(text) > 200:
                    text = text[:200] + "..."
                results.append(
                    {
                        "node_id": node.node.node_id if getattr(node, "node", None) else node.node_id,
                        "text": text,
                        "metadata": dict(getattr(getattr(node, "node", None), "metadata", {}) or {}),
                        "score": node.score,
                    }
                )

            return {"success": True, "results": results, "query": query}

        except asyncio.TimeoutError:
            error_msg = f"Search timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": self.operation_timeout}
        except Exception as e:
            logger.error(f"Failed to search similar nodes: {e}")
            return {"success": False, "error": str(e)}

    async def get_statistics(self) -> Dict[str, Any]:
        """Return lightweight service statistics for legacy API compatibility."""
        if not self._initialized:
            raise Exception("Service not initialized")

        def _collect_statistics() -> Dict[str, Any]:
            base_stats: Dict[str, Any] = {
                "initialized": self._initialized,
                "graph_store_type": type(self.graph_store).__name__ if self.graph_store else None,
                "vector_index_type": type(self.vector_index).__name__ if self.vector_index else None,
                "pipeline": {
                    "default_top_k": getattr(self.query_pipeline, "default_top_k", None),
                    "default_graph_depth": getattr(self.query_pipeline, "default_graph_depth", None),
                    "supports_tools": bool(self.function_tools),
                },
            }

            if self.graph_store is None:
                return base_stats

            try:
                node_result = self.graph_store.query("MATCH (n) RETURN count(n) AS node_count")
                base_stats["node_count"] = node_result[0].get("node_count", 0) if node_result else 0
            except Exception as exc:
                base_stats["node_count_error"] = str(exc)

            try:
                rel_result = self.graph_store.query("MATCH ()-[r]->() RETURN count(r) AS relationship_count")
                base_stats["relationship_count"] = rel_result[0].get("relationship_count", 0) if rel_result else 0
            except Exception as exc:
                base_stats["relationship_count_error"] = str(exc)

            return base_stats

        try:
            statistics = await asyncio.wait_for(
                asyncio.to_thread(_collect_statistics),
                timeout=self.operation_timeout,
            )
            return {"success": True, "statistics": statistics}
        except asyncio.TimeoutError:
            error_msg = f"Statistics retrieval timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": self.operation_timeout}
        except Exception as exc:
            logger.error(f"Failed to collect statistics: {exc}")
            return {"success": False, "error": str(exc)}

    async def clear_knowledge_base(self) -> Dict[str, Any]:
        """Clear Neo4j data and rebuild service indices for legacy API compatibility."""
        if not self._initialized:
            raise Exception("Service not initialized")

        async def _clear_graph() -> None:
            def _clear_sync() -> None:
                if self.graph_store is None:
                    raise RuntimeError("Graph store is not available")

                # Remove all nodes/relationships
                self.graph_store.query("MATCH (n) DETACH DELETE n")

                # Best-effort vector store reset (depends on backend capabilities)
                vector_store = getattr(self.storage_context, "vector_store", None)
                if vector_store is not None:
                    delete_method = getattr(vector_store, "delete", None)
                    if callable(delete_method):
                        try:
                            delete_method(delete_all=True)
                        except TypeError:
                            delete_method()
                        except Exception as exc:  # pragma: no cover - defensive logging
                            logger.warning(f"Vector store clear failed: {exc}")

            await asyncio.to_thread(_clear_sync)

        try:
            await asyncio.wait_for(_clear_graph(), timeout=self.operation_timeout)

            # Recreate storage context and indexes to reflect cleared state
            self.storage_context = StorageContext.from_defaults(graph_store=self.graph_store)
            self.knowledge_index = KnowledgeGraphIndex(
                nodes=[],
                storage_context=self.storage_context,
                show_progress=True,
            )
            self.vector_index = VectorStoreIndex.from_vector_store(
                self.storage_context.vector_store,
                embed_model=Settings.embed_model,
            )

            # Rebuild both pipelines
            self._build_pipeline()
            self._setup_ingestion_pipelines()

            logger.info("Knowledge base cleared successfully")
            return {"success": True, "message": "Knowledge base cleared successfully"}
        except asyncio.TimeoutError:
            error_msg = f"Clear operation timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": self.operation_timeout}
        except Exception as exc:
            logger.error(f"Failed to clear knowledge base: {exc}")
            return {"success": False, "error": str(exc)}

    async def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """execute cypher query"""
        if not self._initialized:
            raise Exception("Service not initialized")

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.graph_store.query,
                    query,
                    parameters or {},
                ),
                timeout=self.operation_timeout,
            )

            return {"success": True, "result": result, "query": query}

        except asyncio.TimeoutError:
            error_msg = f"Cypher execution timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": self.operation_timeout}
        except Exception as e:
            logger.error(f"Failed to execute cypher query: {e}")
            return {"success": False, "error": str(e)}

    async def export_graph(self, output_path: Union[str, Path]) -> Dict[str, Any]:
        """export knowledge graph to file"""
        if not self._initialized:
            raise Exception("Service not initialized")

        output_path = Path(output_path)
        try:
            export_result = await asyncio.wait_for(
                asyncio.to_thread(self.graph_store.export_graph, str(output_path)),
                timeout=self.operation_timeout,
            )

            return {"success": True, "output_path": str(output_path), "result": export_result}

        except asyncio.TimeoutError:
            error_msg = f"Graph export timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": self.operation_timeout}
        except Exception as e:
            logger.error(f"Failed to export graph: {e}")
            return {"success": False, "error": str(e)}

    async def close(self) -> None:
        """close service"""
        if self.graph_store:
            await asyncio.to_thread(self.graph_store.close)
        self._initialized = False
        logger.info("Neo4j Knowledge Service closed")

