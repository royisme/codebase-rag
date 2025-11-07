"""
modern knowledge graph service based on Neo4j's native vector index
uses LlamaIndex's KnowledgeGraphIndex and Neo4j's native vector search functionality
supports multiple LLM and embedding model providers
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from loguru import logger
import time

from llama_index.core import (
    KnowledgeGraphIndex,
    Settings,
    StorageContext,
)

# LLM Providers
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from llama_index.llms.gemini import Gemini
from llama_index.llms.openrouter import OpenRouter

# Embedding Providers
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Graph Store
from llama_index.graph_stores.neo4j import Neo4jGraphStore

from codebase_rag.config import settings
from codebase_rag.services.knowledge.pipeline_components import (
    PipelineBundle,
    build_pipeline_bundle,
    merge_pipeline_configs,
)

class Neo4jKnowledgeService:
    """knowledge graph service based on Neo4j's native vector index"""
    
    def __init__(self):
        self.graph_store = None
        self.knowledge_index = None
        self.query_engine = None
        self._initialized = False
        self._pipeline_bundles: Dict[str, PipelineBundle] = {}
        
        # get timeout settings from config
        self.connection_timeout = settings.connection_timeout
        self.operation_timeout = settings.operation_timeout
        self.large_document_timeout = settings.large_document_timeout
        
        logger.info("Neo4j Knowledge Service created")
    
    def _create_llm(self):
        """create LLM instance based on config"""
        provider = settings.llm_provider.lower()
        
        if provider == "ollama":
            return Ollama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.temperature,
                request_timeout=self.operation_timeout
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
                timeout=self.operation_timeout
            )
        elif provider == "gemini":
            if not settings.google_api_key:
                raise ValueError("Google API key is required for Gemini provider")
            return Gemini(
                model=settings.gemini_model,
                api_key=settings.google_api_key,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens
            )
        elif provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("OpenRouter API key is required for OpenRouter provider")
            return OpenRouter(
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                temperature=settings.temperature,
                max_tokens=settings.openrouter_max_tokens,
                timeout=self.operation_timeout
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
                request_timeout=self.operation_timeout
            )
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI embedding provider")
            return OpenAIEmbedding(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
                api_base=settings.openai_base_url,
                timeout=self.operation_timeout
            )
        elif provider == "gemini":
            if not settings.google_api_key:
                raise ValueError("Google API key is required for Gemini embedding provider")
            return GeminiEmbedding(
                model_name=settings.gemini_embedding_model,
                api_key=settings.google_api_key
            )
        elif provider == "huggingface":
            return HuggingFaceEmbedding(
                model_name=settings.huggingface_embedding_model
            )
        elif provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("OpenRouter API key is required for OpenRouter embedding provider")
            return OpenAIEmbedding(
                model=settings.openrouter_embedding_model,
                api_key=settings.openrouter_api_key,
                api_base=settings.openrouter_base_url,
                timeout=self.operation_timeout
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

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

    async def initialize(self) -> bool:
        """initialize service"""
        try:
            logger.info(f"Initializing with LLM provider: {settings.llm_provider}, Embedding provider: {settings.embedding_provider}")
            
            # set LlamaIndex global config
            Settings.llm = self._create_llm()
            Settings.embed_model = self._create_embedding_model()
            
            Settings.chunk_size = settings.chunk_size
            Settings.chunk_overlap = settings.chunk_overlap
            
            logger.info(f"LLM: {settings.llm_provider} - {getattr(settings, f'{settings.llm_provider}_model')}")
            logger.info(f"Embedding: {settings.embedding_provider} - {getattr(settings, f'{settings.embedding_provider}_embedding_model')}")
            
            # initialize Neo4j graph store, add timeout config
            self.graph_store = Neo4jGraphStore(
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                url=settings.neo4j_uri,
                database=settings.neo4j_database,
                timeout=self.connection_timeout
            )
            
            # create storage context
            storage_context = StorageContext.from_defaults(
                graph_store=self.graph_store
            )
            
            # try to load existing index, if not exists, create new one
            try:
                self.knowledge_index = await asyncio.wait_for(
                    asyncio.to_thread(
                        KnowledgeGraphIndex.from_existing,
                        storage_context=storage_context
                    ),
                    timeout=self.connection_timeout
                )
                logger.info("Loaded existing knowledge graph index")
            except asyncio.TimeoutError:
                logger.warning("Loading existing index timed out, creating new index")
                self.knowledge_index = KnowledgeGraphIndex(
                    nodes=[],
                    storage_context=storage_context,
                    show_progress=True
                )
                logger.info("Created new knowledge graph index")
            except Exception:
                # create empty knowledge graph index
                self.knowledge_index = KnowledgeGraphIndex(
                    nodes=[],
                    storage_context=storage_context,
                    show_progress=True
                )
                logger.info("Created new knowledge graph index")
            
            # 创建查询引擎
            self.query_engine = self.knowledge_index.as_query_engine(
                include_text=True,
                response_mode="tree_summarize",
                embedding_mode="hybrid"
            )

            self._setup_ingestion_pipelines()

            self._initialized = True
            logger.success("Neo4j Knowledge Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Neo4j Knowledge Service: {e}")
            return False

    async def _run_ingestion_pipeline(
        self,
        pipeline_name: str,
        *,
        connector_overrides: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        if pipeline_name not in self._pipeline_bundles:
            raise ValueError(f"Pipeline '{pipeline_name}' is not configured")

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
            error_msg = (
                f"Pipeline '{pipeline_name}' execution timed out after {timeout}s"
            )
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "timeout": timeout}
        except Exception as exc:
            logger.error(f"Pipeline '{pipeline_name}' failed: {exc}")
            return {"success": False, "error": str(exc)}

    async def add_document(self,
                         content: str,
                         title: str = None,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
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
    
    async def add_directory(self,
                          directory_path: str,
                          recursive: bool = True,
                          file_extensions: List[str] = None) -> Dict[str, Any]:
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
    
    async def query(self, 
                   question: str,
                   mode: str = "hybrid") -> Dict[str, Any]:
        """query knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # create different query engines based on mode
            if mode == "hybrid":
                # hybrid mode: graph traversal + vector search
                query_engine = self.knowledge_index.as_query_engine(
                    include_text=True,
                    response_mode="tree_summarize",
                    embedding_mode="hybrid"
                )
            elif mode == "graph_only":
                # graph only mode
                query_engine = self.knowledge_index.as_query_engine(
                    include_text=False,
                    response_mode="tree_summarize"
                )
            elif mode == "vector_only":
                # vector only mode
                query_engine = self.knowledge_index.as_query_engine(
                    include_text=True,
                    response_mode="compact",
                    embedding_mode="embedding"
                )
            else:
                query_engine = self.query_engine
            
            # execute query, add timeout control
            response = await asyncio.wait_for(
                asyncio.to_thread(query_engine.query, question),
                timeout=self.operation_timeout
            )
            
            # extract source node information
            source_nodes = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    source_nodes.append({
                        "node_id": node.node_id,
                        "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                        "metadata": node.metadata,
                        "score": getattr(node, 'score', None)
                    })
            
            logger.info(f"Successfully answered query: {question[:50]}...")
            
            return {
                "success": True,
                "answer": str(response),
                "source_nodes": source_nodes,
                "query_mode": mode
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Query timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timeout": self.operation_timeout
            }
        except Exception as e:
            logger.error(f"Failed to query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_graph_schema(self) -> Dict[str, Any]:
        """get graph schema information"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # get graph statistics, add timeout control
            schema_info = await asyncio.wait_for(
                asyncio.to_thread(self.graph_store.get_schema),
                timeout=self.connection_timeout
            )
            
            return {
                "success": True,
                "schema": schema_info
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Schema retrieval timed out after {self.connection_timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            logger.error(f"Failed to get graph schema: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_similar_nodes(self, 
                                 query: str, 
                                 top_k: int = 10) -> Dict[str, Any]:
        """search nodes by vector similarity"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # use retriever for vector search, add timeout control
            retriever = self.knowledge_index.as_retriever(
                similarity_top_k=top_k,
                include_text=True
            )
            
            nodes = await asyncio.wait_for(
                asyncio.to_thread(retriever.retrieve, query),
                timeout=self.operation_timeout
            )
            
            # format results
            results = []
            for node in nodes:
                results.append({
                    "node_id": node.node_id,
                    "text": node.text,
                    "metadata": node.metadata,
                    "score": getattr(node, 'score', None)
                })
            
            return {
                "success": True,
                "results": results,
                "total_count": len(results)
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Similar nodes search timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timeout": self.operation_timeout
            }
        except Exception as e:
            logger.error(f"Failed to search similar nodes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """get knowledge graph statistics"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # try to get basic statistics, add timeout control
            try:
                # if graph store supports statistics query
                stats = await asyncio.wait_for(
                    asyncio.to_thread(lambda: {
                        "index_type": "KnowledgeGraphIndex with Neo4j vector store",
                        "graph_store_type": type(self.graph_store).__name__,
                        "initialized": self._initialized
                    }),
                    timeout=self.connection_timeout
                )
                
                return {
                    "success": True,
                    "statistics": stats,
                    "message": "Knowledge graph is active"
                }
                
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Statistics retrieval timed out after {self.connection_timeout}s"
                }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_knowledge_base(self) -> Dict[str, Any]:
        """clear knowledge base"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # recreate empty index, add timeout control
            storage_context = StorageContext.from_defaults(
                graph_store=self.graph_store
            )
            
            self.knowledge_index = await asyncio.wait_for(
                asyncio.to_thread(lambda: KnowledgeGraphIndex(
                    nodes=[],
                    storage_context=storage_context,
                    show_progress=True
                )),
                timeout=self.connection_timeout
            )
            
            # recreate query engine
            self.query_engine = self.knowledge_index.as_query_engine(
                include_text=True,
                response_mode="tree_summarize",
                embedding_mode="hybrid"
            )
            
            logger.info("Knowledge base cleared successfully")
            
            return {
                "success": True,
                "message": "Knowledge base cleared successfully"
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Clear operation timed out after {self.connection_timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """close service"""
        try:
            if self.graph_store:
                # if graph store has close method, call it
                if hasattr(self.graph_store, 'close'):
                    await asyncio.wait_for(
                        asyncio.to_thread(self.graph_store.close),
                        timeout=self.connection_timeout
                    )
                elif hasattr(self.graph_store, '_driver') and self.graph_store._driver:
                    # close Neo4j driver connection
                    await asyncio.wait_for(
                        asyncio.to_thread(self.graph_store._driver.close),
                        timeout=self.connection_timeout
                    )
            
            self._initialized = False
            logger.info("Neo4j Knowledge Service closed")
            
        except asyncio.TimeoutError:
            logger.warning(f"Service close timed out after {self.connection_timeout}s")
        except Exception as e:
            logger.error(f"Error closing service: {e}")
    
    def set_timeouts(self, connection_timeout: int = None, operation_timeout: int = None, large_document_timeout: int = None):
        """dynamic set timeout parameters"""
        if connection_timeout is not None:
            self.connection_timeout = connection_timeout
            logger.info(f"Connection timeout set to {connection_timeout}s")
        
        if operation_timeout is not None:
            self.operation_timeout = operation_timeout
            logger.info(f"Operation timeout set to {operation_timeout}s")
        
        if large_document_timeout is not None:
            self.large_document_timeout = large_document_timeout
            logger.info(f"Large document timeout set to {large_document_timeout}s")

# global service instance
neo4j_knowledge_service = Neo4jKnowledgeService() 
