"""
modern knowledge graph service based on Neo4j's native vector index
uses LlamaIndex's KnowledgeGraphIndex and Neo4j's native vector search functionality
supports multiple LLM and embedding model providers
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
from loguru import logger
import time
import uuid

from llama_index.core import (
    KnowledgeGraphIndex,
    Document,
    Settings,
    StorageContext,
    SimpleDirectoryReader,
    VectorStoreIndex,
)

# LLM Providers
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI
from llama_index.llms.gemini import Gemini
from llama_index.llms.openrouter import OpenRouter

# Embedding Providers
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Graph Store
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.vector_stores.neo4jvector import Neo4jVectorStore

# Core components
from llama_index.core.node_parser import SimpleNodeParser

from neo4j import GraphDatabase

from config import settings
from services.embedding_utils import expected_dimension_for_provider

class Neo4jKnowledgeService:
    """knowledge graph service based on Neo4j's native vector index"""
    
    def __init__(self):
        self.graph_store = None
        self.knowledge_index = None
        self.vector_store = None
        self.vector_index = None
        self.query_engine = None
        self._initialized = False
        
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
            return GoogleGenAIEmbedding(
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

    def _ensure_vector_index_dimension(self, embedding_dimension: int) -> None:
        """Ensure Neo4j vector index exists with the correct embedding dimension."""
        driver = None

        try:
            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
            )
            with driver.session(database=settings.neo4j_database) as session:
                record = session.run(
                    """
                    SHOW INDEXES YIELD name, type, options
                    WHERE name = $name
                    RETURN name, type, options
                    """,
                    {"name": settings.vector_index_name},
                ).single()

                should_create = False

                if record:
                    index_type = record.get("type")
                    index_options = record.get("options") or {}
                    index_config = index_options.get("indexConfig") or {}
                    current_dim = index_config.get("vector.dimensions")

                    if index_type != "VECTOR":
                        logger.warning(
                            "Index %s exists but is %s instead of VECTOR. Recreating.",
                            settings.vector_index_name,
                            index_type,
                        )
                        session.run(
                            f"DROP INDEX {settings.vector_index_name} IF EXISTS"
                        )
                        should_create = True
                    elif current_dim != embedding_dimension:
                        logger.warning(
                            "Vector index %s dimension %s mismatches embedding dimension %s. Recreating index.",
                            settings.vector_index_name,
                            current_dim,
                            embedding_dimension,
                        )
                        session.run(
                            f"DROP INDEX {settings.vector_index_name} IF EXISTS"
                        )
                        should_create = True
                else:
                    should_create = True

                if should_create:
                    session.run(
                        f"""
                        CREATE VECTOR INDEX {settings.vector_index_name} IF NOT EXISTS
                        FOR (n:Document) ON (n.embedding)
                        OPTIONS {{
                            indexConfig: {{
                                `vector.dimensions`: {embedding_dimension},
                                `vector.similarity_function`: 'cosine'
                            }}
                        }}
                        """
                    )
                    logger.info(
                        f"Ensured Neo4j vector index {settings.vector_index_name} exists with dimension {embedding_dimension}."
                    )
                else:
                    logger.info(
                        f"Neo4j vector index {settings.vector_index_name} already matches dimension {embedding_dimension}."
                    )
        finally:
            if driver:
                driver.close()
    
    async def initialize(self) -> bool:
        """initialize service"""
        # 如果已经初始化，直接返回
        if self._initialized:
            logger.debug("Neo4j Knowledge Service already initialized")
            return True
            
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
                timeout=self.connection_timeout,
            )
            embedding_dimension = settings.vector_dimension
            embed_model = settings.embedding_provider.lower()
            expected_dim = expected_dimension_for_provider(embed_model)
            if expected_dim and embedding_dimension != expected_dim:
                logger.warning(
                    f"VECTOR_DIMENSION={embedding_dimension} does not match "
                    f"{embed_model} embedding dimension ({expected_dim}). Using {expected_dim}."
                )
                embedding_dimension = expected_dim

            self._ensure_vector_index_dimension(embedding_dimension)
            self.vector_store = Neo4jVectorStore(
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                url=settings.neo4j_uri,
                embedding_dimension=embedding_dimension,
                database=settings.neo4j_database,
                index_name=settings.vector_index_name,
                node_label="Document",
                text_node_property="text",
                embedding_node_property="embedding",
                metadata_node_property="metadata",
            )
            
            # create storage context
            storage_context = StorageContext.from_defaults(
                graph_store=self.graph_store
            )
            
            # KnowledgeGraphIndex 会自动从 graph_store 加载现有数据
            # 不需要显式调用 from_existing
            logger.info("Creating/Loading knowledge graph index from Neo4j...")
            self.knowledge_index = KnowledgeGraphIndex(
                nodes=[],
                storage_context=storage_context,
                show_progress=True,
            )
            self.vector_index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                show_progress=True,
            )
            logger.info("Knowledge graph index initialized (data loaded from Neo4j if exists)")
            
            # 创建查询引擎
            self.query_engine = self.knowledge_index.as_query_engine(
                include_text=True,
                response_mode="tree_summarize",
                embedding_mode="hybrid"
            )
            
            self._initialized = True
            logger.success("Neo4j Knowledge Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j Knowledge Service: {e}")
            return False
    
    async def add_document(self, 
                         content: str, 
                         title: str = None,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """add document to knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # create document
            doc = Document(
                text=content,
                metadata={
                    "title": title or "Untitled",
                    "source": "manual_input",
                    "timestamp": time.time(),
                    **(metadata or {})
                }
            )
            
            # select timeout based on document size
            content_size = len(content)
            timeout = self.operation_timeout if content_size < 10000 else self.large_document_timeout
            
            logger.info(f"Adding document '{title}' (size: {content_size} chars, timeout: {timeout}s)")
            
            # use async timeout control for insert operation
            await asyncio.wait_for(
                asyncio.to_thread(self.knowledge_index.insert, doc),
                timeout=timeout
            )
            
            logger.info(f"Successfully added document: {title}")
            
            return {
                "success": True,
                "message": f"Document '{title}' added to knowledge graph",
                "document_id": doc.doc_id,
                "content_size": content_size
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Document insertion timed out after {timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timeout": timeout
            }
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def insert_documents(self, documents: List[Document]) -> int:
        """Insert multiple documents into the Neo4j vector index."""

        if not self.vector_index:
            raise RuntimeError("Vector index is not initialized")

        inserted = 0
        for doc in documents:
            try:
                await asyncio.to_thread(self.vector_index.insert, doc)
                inserted += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to insert document %s: %s", doc.metadata.get("file_path"), exc)
        return inserted

    async def _build_vector_context(
        self,
        question: str,
        max_results: int,
    ) -> tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Retrieve vector nodes and format them into context/evidence structures."""

        if not self.vector_index:
            return "", [], []

        retriever = self.vector_index.as_retriever(
            similarity_top_k=max_results,
            include_text=True,
        )
        nodes = await asyncio.to_thread(retriever.retrieve, question)
        return self._format_nodes_as_context(nodes, max_results)

    def _format_nodes_as_context(
        self,
        nodes: List[Any],
        max_results: int,
    ) -> tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Format retrieved nodes into context text, source nodes, and evidence data."""

        context_parts: List[str] = []
        source_nodes: List[Dict[str, Any]] = []
        evidence_metadata: List[Dict[str, Any]] = []

        for idx, node in enumerate(nodes[:max_results], start=1):
            metadata = getattr(node, "metadata", None) or {}
            snippet = (getattr(node, "text", None) or "")
            truncated = snippet[:300] + ("..." if len(snippet) > 300 else "")

            file_path = metadata.get("file_path", metadata.get("title", "unknown"))
            location = file_path
            start_line = metadata.get("start_line")
            end_line = metadata.get("end_line")
            if start_line:
                location += f" (L{start_line}"
                if end_line and end_line != start_line:
                    location += f"-{end_line}"
                location += ")"

            context_parts.append(f"[{idx}] {location}:\n{truncated}")
            source_nodes.append(
                {
                    "node_id": getattr(node, "node_id", None),
                    "text": truncated,
                    "metadata": metadata,
                    "score": getattr(node, "score", 0.0),
                }
            )
            evidence_metadata.append(
                {
                    "id": getattr(node, "node_id", None) or f"node_{idx}",
                    "snippet": truncated,
                    "full_text": snippet,
                    "repo": metadata.get("repo"),
                    "branch": metadata.get("branch", "main"),
                    "file_path": file_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    "source_type": metadata.get("source_type", "code"),
                    "score": getattr(node, "score", 0.0),
                }
            )

        context_text = "\n\n".join(context_parts)
        return context_text, source_nodes, evidence_metadata

    @staticmethod
    def _build_evidence_link(ev_data: Dict[str, Any]) -> Optional[str]:
        repo = ev_data.get("repo")
        file_path = ev_data.get("file_path")
        if not repo or not file_path:
            return None
        branch = ev_data.get("branch", "main")
        start_line = ev_data.get("start_line")
        end_line = ev_data.get("end_line")
        link = f"https://github.com/{repo}/blob/{branch}/{file_path}"
        if start_line:
            link += f"#L{start_line}"
            if end_line and end_line != start_line:
                link += f"-L{end_line}"
        return link

    @classmethod
    def _format_reference_lines(cls, evidence_metadata: List[Dict[str, Any]]) -> List[str]:
        if not evidence_metadata:
            return []
        lines = ["\n\n**参考资料**"]
        for idx, ev in enumerate(evidence_metadata, start=1):
            label = ev.get("file_path") or ev.get("id") or f"来源 {idx}"
            link = cls._build_evidence_link(ev)
            if link:
                lines.append(f"[{idx}] {label} ([链接]({link}))")
            else:
                lines.append(f"[{idx}] {label}")
        return lines

    async def _query_via_vector_index(
        self,
        question: str,
        *,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Retrieve contexts via vector index and run the LLM."""

        if not self.vector_index:
            raise RuntimeError("Vector index not available")

        context_text, source_nodes, _ = await self._build_vector_context(
            question, max_results
        )
        llm = Settings.llm
        prompt = (
            f"基于以下上下文，用 Markdown 回答问题。引用上下文时必须使用半角格式，如 `[1]` `[2]`，禁止出现 `【】`、`（）` 等符号。若没有可引用内容，直接写“暂无参考”。\n\n"
            f"{context_text}\n\n问题: {question}\n\n回答："
            if context_text
            else f"请回答下列问题：{question}\n\n要求：\n1. 输出 Markdown。\n2. 如果引用上下文，必须使用 `[1]` `[2]` 等半角格式，不得使用其他括号。\n3. 若无可引用内容，直接说明“暂无参考”。\n\n回答："
        )

        if hasattr(llm, "acomplete"):
            llm_response = await llm.acomplete(prompt)
        else:
            llm_response = await asyncio.to_thread(llm.complete, prompt)

        confidence = max((item.get("score") or 0.0 for item in source_nodes), default=0.0)

        return {
            "answer": str(llm_response),
            "source_nodes": source_nodes,
            "confidence": confidence,
        }
    
    async def add_file(self, file_path: str) -> Dict[str, Any]:
        """add file to knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # read file
            documents = await asyncio.to_thread(
                lambda: SimpleDirectoryReader(input_files=[file_path]).load_data()
            )
            
            if not documents:
                return {
                    "success": False,
                    "error": "No documents loaded from file"
                }
            
            # batch insert, handle timeout for each document
            success_count = 0
            errors = []
            
            for i, doc in enumerate(documents):
                try:
                    content_size = len(doc.text)
                    timeout = self.operation_timeout if content_size < 10000 else self.large_document_timeout
                    
                    await asyncio.wait_for(
                        asyncio.to_thread(self.knowledge_index.insert, doc),
                        timeout=timeout
                    )
                    success_count += 1
                    logger.debug(f"Added document {i+1}/{len(documents)} from {file_path}")
                    
                except asyncio.TimeoutError:
                    error_msg = f"Document {i+1} timed out"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                except Exception as e:
                    error_msg = f"Document {i+1} failed: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            logger.info(f"Added {success_count}/{len(documents)} documents from {file_path}")
            
            return {
                "success": success_count > 0,
                "message": f"Added {success_count}/{len(documents)} documents from {file_path}",
                "documents_count": len(documents),
                "success_count": success_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to add file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_directory(self, 
                          directory_path: str,
                          recursive: bool = True,
                          file_extensions: List[str] = None) -> Dict[str, Any]:
        """batch add files in directory"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # set file extension filter
            if file_extensions is None:
                file_extensions = [".txt", ".md", ".py", ".js", ".ts", ".sql", ".json", ".yaml", ".yml"]
            
            # read directory
            reader = SimpleDirectoryReader(
                input_dir=directory_path,
                recursive=recursive,
                file_extractor={ext: None for ext in file_extensions}
            )
            
            documents = await asyncio.to_thread(reader.load_data)
            
            if not documents:
                return {
                    "success": False,
                    "error": "No documents found in directory"
                }
            
            # batch insert, handle timeout for each document
            success_count = 0
            errors = []
            
            logger.info(f"Processing {len(documents)} documents from {directory_path}")
            
            for i, doc in enumerate(documents):
                try:
                    content_size = len(doc.text)
                    timeout = self.operation_timeout if content_size < 10000 else self.large_document_timeout
                    
                    await asyncio.wait_for(
                        asyncio.to_thread(self.knowledge_index.insert, doc),
                        timeout=timeout
                    )
                    success_count += 1
                    
                    if i % 10 == 0:  # record progress every 10 documents
                        logger.info(f"Progress: {i+1}/{len(documents)} documents processed")
                        
                except asyncio.TimeoutError:
                    error_msg = f"Document {i+1} ({doc.metadata.get('file_name', 'unknown')}) timed out"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                except Exception as e:
                    error_msg = f"Document {i+1} ({doc.metadata.get('file_name', 'unknown')}) failed: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            logger.info(f"Successfully added {success_count}/{len(documents)} documents from {directory_path}")
            
            return {
                "success": success_count > 0,
                "message": f"Added {success_count}/{len(documents)} documents from {directory_path}",
                "documents_count": len(documents),
                "success_count": success_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to add directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _stream_query_response(
        self,
        question: str,
        *,
        mode: str = "hybrid",
        include_evidence: bool = True,
        max_results: int = 10,
    ):
        """Execute the underlying LlamaIndex query with timeout and async fallback.

        The public ``query`` method expects a response object that exposes
        ``source_nodes`` and ``score`` attributes (as returned by
        ``QueryEngine.aquery``).  Historically the synchronous ``query`` method
        was used directly.  During the streaming refactor we switched the
        call-site to ``_stream_query_response`` but forgot to implement the
        helper, which now restores the original behaviour while keeping the
        hook for future true streaming support.

        Parameters other than ``question`` are currently informational.  They
        allow us to adjust the execution strategy later (e.g. switching
        between hybrid/vector modes or truncating responses) without touching
        the caller contract.
        """

        if not self._initialized:
            raise Exception("Service not initialized")

        if not self.query_engine:
            raise RuntimeError("Query engine is not available")

        async def _execute() -> Any:
            # Prefer the async API when the query engine exposes it; fall back
            # to the blocking variant otherwise.
            if hasattr(self.query_engine, "aquery") and callable(
                getattr(self.query_engine, "aquery")
            ):
                return await self.query_engine.aquery(question)

            logger.debug(
                "Query engine missing 'aquery', falling back to synchronous call"
            )
            return await asyncio.to_thread(self.query_engine.query, question)

        try:
            return await asyncio.wait_for(_execute(), timeout=self.operation_timeout)
        except asyncio.TimeoutError:
            logger.error(
                "Query execution timed out after {}s (mode={}, include_evidence={}, max_results={})",
                self.operation_timeout,
                mode,
                include_evidence,
                max_results,
            )
            raise
        except Exception as exc:
            logger.error(
                "Query execution failed: {} (mode={}, include_evidence={}, max_results={})",
                exc,
                mode,
                include_evidence,
                max_results,
            )
            raise

    async def query(
        self,
        question: str,
        mode: str = "hybrid",
        *,
        max_results: int = 10,
        include_evidence: bool = True,
        source_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, Any]:
        """query knowledge graph"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        use_vector = self.vector_index is not None
        
        try:
            if use_vector:
                response_payload = await self._query_via_vector_index(
                    question,
                    max_results=max_results,
                )
                response = response_payload["answer"]
                source_nodes = response_payload["source_nodes"]
            else:
                response = await self._stream_query_response(
                    question,
                    mode=mode,
                    include_evidence=include_evidence,
                    max_results=max_results,
                )
            
            # extract source node information
            if not use_vector:
                source_nodes: List[Dict[str, Any]] = []
                if hasattr(response, 'source_nodes'):
                    for node in response.source_nodes:
                        source_nodes.append({
                            "node_id": node.node_id,
                            "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                            "metadata": node.metadata,
                            "score": getattr(node, 'score', None)
                        })
            else:
                source_nodes = response_payload["source_nodes"]

            # Respect max results for downstream consumers
            source_nodes = source_nodes[:max_results]

            def _safe_uuid(raw: Any) -> uuid.UUID:
                if isinstance(raw, uuid.UUID):
                    return raw
                if raw is None:
                    return uuid.uuid4()
                try:
                    return uuid.UUID(str(raw))
                except (ValueError, TypeError):
                    return uuid.uuid5(uuid.NAMESPACE_URL, f"knowledge-node:{raw}")

            evidence: List[Dict[str, Any]] = []
            if include_evidence:
                for node in source_nodes:
                    metadata = node.get("metadata") or {}
                    evidence.append(
                        {
                            "source_id": metadata.get("source_id")
                            or metadata.get("id")
                            or node.get("node_id"),
                            "source_name": metadata.get("source_name")
                            or metadata.get("title")
                            or metadata.get("file_path")
                            or "未知来源",
                            "content": metadata.get("content") or node.get("text", ""),
                            "content_snippet": node.get("text", "")[:200],
                            "relevance_score": metadata.get("relevance_score")
                            or metadata.get("score")
                            or node.get("score")
                            or 0.0,
                            "page_number": metadata.get("page_number"),
                            "section_title": metadata.get("section_title")
                            or metadata.get("section"),
                        }
                    )

            # Derive confidence score
            raw_confidence = getattr(response, "score", None) if not use_vector else response_payload.get("confidence")
            if raw_confidence is None:
                raw_confidence = max(
                    (item.get("score") or 0.0 for item in source_nodes), default=0.0
                )
            confidence_score = max(0.0, min(1.0, float(raw_confidence)))

            resolved_sources = source_ids or [
                _safe_uuid(
                    (node.get("metadata") or {}).get("source_id") or node.get("node_id")
                )
                for node in source_nodes
            ]
            
            logger.info(f"Successfully answered query: {question[:50]}...")
            
            return {
                "success": True,
                "answer": str(response),
                "source_nodes": source_nodes,
                "query_mode": mode,
                "confidence_score": confidence_score,
                "evidence": evidence if include_evidence else [],
                "sources_queried": resolved_sources,
            }
            
        except asyncio.TimeoutError:
            error_msg = f"Query timed out after {self.operation_timeout}s"
            logger.error(error_msg)
            return {
                "success": False,
                "error": "TIMEOUT",
                "message": error_msg,
                "timeout": self.operation_timeout,
                "sources_queried": source_ids or [],
            }
        except Exception as e:
            import traceback
            logger.error(f"Failed to query: {e}")
            logger.debug(f"Neo4j query stack:\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "sources_queried": source_ids or [],
            }
    
    async def stream_query(
        self,
        question: str,
        mode: str = "hybrid",
        *,
        max_results: int = 10,
        include_evidence: bool = True,
        source_ids: Optional[List[uuid.UUID]] = None,
    ):
        """Stream query with token-level chunks using LLM's native streaming API.
        
        Yields dictionaries with:
        - type: "text_delta" | "metadata" | "error" | "done"
        - relevant payload fields
        """
        if not self._initialized:
            raise Exception("Service not initialized")
        
        import time as perf_time
        perf_start = perf_time.perf_counter()
        
        start_time = time.time()
        accumulated_text = ""
        source_nodes: List[Dict[str, Any]] = []
        evidence_metadata: List[Dict[str, Any]] = []  # 初始化证据元数据列表

        logger.debug(f"[PERF-KG] Starting stream query: {question[:50]}...")

        def _node_metadata(node: Any) -> Dict[str, Any]:
            if isinstance(node, dict):
                return node.get("metadata") or {}
            return getattr(node, "metadata", None) or {}

        def _node_score(node: Any) -> float:
            if isinstance(node, dict):
                return float(node.get("score") or 0.0)
            raw = getattr(node, "score", 0.0)
            try:
                return float(raw)
            except (TypeError, ValueError):
                return 0.0

        def _node_id(node: Any) -> Optional[str]:
            if isinstance(node, dict):
                return node.get("node_id")
            return getattr(node, "node_id", None)

        try:
            # Get the LLM instance
            llm = Settings.llm
            
            # Build context, prefer vector index
            context_text = ""
            if self.vector_index:
                vector_start = perf_time.perf_counter()
                context_text, source_nodes, evidence_metadata = await self._build_vector_context(
                    question, max_results
                )
                logger.info(
                    f"[PERF-KG] Vector retrieval completed in {perf_time.perf_counter() - vector_start:.2f}s (nodes={len(source_nodes)})"
                )
            
            if not context_text and self.query_engine:
                try:
                    retrieve_start = perf_time.perf_counter()
                    logger.debug(f"[PERF-KG] Starting graph retrieval...")
                    retriever_create_start = perf_time.perf_counter()
                    retriever = self.knowledge_index.as_retriever(
                        similarity_top_k=max_results,
                        include_text=True,
                    )
                    retriever_create_time = perf_time.perf_counter() - retriever_create_start
                    nodes = await asyncio.wait_for(
                        asyncio.to_thread(retriever.retrieve, question),
                        timeout=180,
                    )
                    context_text, source_nodes, evidence_metadata = self._format_nodes_as_context(
                        nodes, max_results
                    )
                    retrieve_time = perf_time.perf_counter() - retrieve_start
                    logger.info(
                        f"[PERF-KG] Graph retrieval completed in {retrieve_time:.2f}s (nodes={len(source_nodes)})"
                    )
                    logger.debug(
                        f"[PERF-KG] Graph retriever create time={retriever_create_time:.2f}s"
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        f"[PERF-KG] Graph context retrieval timed out after 180s for question: {question[:50]}..."
                    )
                except Exception as ctx_exc:
                    logger.warning(
                        f"[PERF-KG] Failed to build graph context: {ctx_exc.__class__.__name__}: {ctx_exc}"
                    )
            elif not context_text:
                logger.debug("[PERF-KG] No vector or graph context available")
            
            # Construct prompt
            prompt_start = perf_time.perf_counter()
            if context_text:
                prompt = f"""基于以下编号的上下文信息，用 Markdown 格式回答问题。引用上下文时只能使用半角 `[1]`、`[2]` 等格式，禁止使用 `【】`、`（）` 等其他括号；若无可引用内容，直接写“暂无参考”。

{context_text}

问题: {question}

要求：
1. 使用 Markdown 格式回答（支持标题、列表、代码块等）
2. 代码示例请用代码块包裹，并指定语言，例如：```python
3. **引用上下文时，必须用 `[1]` `[2]` 等半角编号标记来源，禁止出现其他括号**
4. 回答要简洁清晰，重点突出
5. 如果有多个要点，使用列表或编号

回答："""
            else:
                prompt = f"""请用 Markdown 格式回答以下问题：

{question}

要求：
1. 使用 Markdown 格式（支持标题、列表、代码块等）
2. 代码示例请用代码块包裹，并指定语言
3. 若引用上下文，必须使用半角 `[1]` `[2]` 等格式；若无上下文可引用，直接说明“暂无参考”。
 
回答："""
            logger.debug(f"[PERF-KG] Prompt constructed (length={len(prompt)})")
            
            # Stream from LLM
            llm_start = perf_time.perf_counter()
            first_chunk_received = False
            chunk_count = 0
            
            logger.info(f"[PERF-KG] Starting LLM streaming...")
            
            if hasattr(llm, 'astream_complete'):
                # Use async streaming if available
                stream_response = await llm.astream_complete(prompt)
                async for chunk in stream_response:
                    if not first_chunk_received:
                        first_chunk_time = perf_time.perf_counter() - llm_start
                        logger.info(f"[PERF-KG] First LLM chunk received in {first_chunk_time:.2f}s")
                        first_chunk_received = True
                    
                    chunk_count += 1
                    delta_text = str(chunk.delta) if hasattr(chunk, 'delta') else str(chunk)
                    if delta_text:
                        accumulated_text += delta_text
                        yield {
                            "type": "text_delta",
                            "content": delta_text,
                        }
            elif hasattr(llm, 'stream_complete'):
                # Fallback to sync streaming wrapped in async
                stream_iter = llm.stream_complete(prompt)
                for chunk in stream_iter:
                    delta_text = str(chunk.delta) if hasattr(chunk, 'delta') else str(chunk)
                    if delta_text:
                        accumulated_text += delta_text
                        yield {
                            "type": "text_delta",
                            "content": delta_text,
                        }
                    await asyncio.sleep(0)  # Yield control
            else:
                # No streaming support - fall back to batch
                logger.warning("LLM does not support streaming, falling back to batch mode")
                if hasattr(llm, 'acomplete'):
                    response = await llm.acomplete(prompt)
                else:
                    response = await asyncio.to_thread(llm.complete, prompt)
                text = str(response)
                accumulated_text = text
                # Split into chunks for pseudo-streaming
                for i in range(0, len(text), 32):
                    chunk = text[i:i+32]
                    yield {
                        "type": "text_delta",
                        "content": chunk,
                    }
                    await asyncio.sleep(0.01)

            reference_lines = self._format_reference_lines(evidence_metadata)
            if reference_lines:
                reference_text = "\n".join(reference_lines) + "\n"
                accumulated_text += reference_text
                yield {
                    "type": "text_delta",
                    "content": reference_text,
                }
            
            # After streaming completes, yield metadata
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate confidence score
            confidence_score = 0.0
            if source_nodes:
                scores = [_node_score(node) for node in source_nodes]
                confidence_score = max(scores) if scores else 0.0

            # Clamp confidence into [0, 1] to satisfy API schema
            confidence_score = max(0.0, min(1.0, float(confidence_score)))
            
            if source_ids:
                resolved_sources = source_ids
            else:
                resolved_sources = []
                for node in source_nodes[:5]:
                    metadata = _node_metadata(node)
                    source_id = metadata.get("source_id")
                    if source_id:
                        try:
                            resolved_sources.append(uuid.UUID(str(source_id)))
                        except (ValueError, TypeError):
                            resolved_sources.append(
                                uuid.uuid5(uuid.NAMESPACE_URL, f"stream-source:{source_id}")
                            )
                    else:
                        resolved_sources.append(uuid.uuid4())
            
            yield {
                "type": "metadata",
                "confidence_score": confidence_score,
                "execution_time_ms": processing_time_ms,
                        "sources_queried": [str(s) for s in resolved_sources],
                "retrieval_mode": mode,
            }
            
            # Extract evidence if requested - 使用保留的完整元数据
            if include_evidence and evidence_metadata:
                for idx, ev_data in enumerate(evidence_metadata, start=1):
                    github_link = self._build_evidence_link(ev_data)
                    
                    yield {
                        "type": "evidence",
                        "evidence": {
                            "id": ev_data.get("id"),
                            "index": idx,  # 对应 [1] [2] [3]
                            "snippet": ev_data.get("snippet", ""),
                            "repo": ev_data.get("repo"),
                            "branch": ev_data.get("branch", "main"),
                            "file_path": ev_data.get("file_path"),
                            "start_line": ev_data.get("start_line"),
                            "end_line": ev_data.get("end_line"),
                            "source_type": ev_data.get("source_type", "code"),
                            "score": ev_data.get("score", 0.0),
                            "link": github_link,
                        }
                    }
            
            # Done
            total_time = perf_time.perf_counter() - perf_start
            llm_time = perf_time.perf_counter() - llm_start
            
            logger.info(f"[PERF-KG] Stream query completed in {total_time:.2f}s")
            logger.info(f"[PERF-KG] LLM streaming took {llm_time:.2f}s ({chunk_count} chunks)")
            if chunk_count > 0 and llm_time > 0:
                logger.info(f"[PERF-KG] LLM throughput: {chunk_count/llm_time:.1f} chunks/s")
            
            yield {
                "type": "done",
                "query_id": str(uuid.uuid4()),
                "summary": accumulated_text,
                "processing_time_ms": processing_time_ms,
                "confidence_score": confidence_score,
                "sources_queried": [str(s) for s in resolved_sources],
            }
            
        except asyncio.TimeoutError:
            processing_time_ms = int((time.time() - start_time) * 1000)
            yield {
                "type": "error",
                "message": f"Query timed out after {self.operation_timeout}s",
                "code": "TIMEOUT",
                "processing_time_ms": processing_time_ms,
            }
        except Exception as exc:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Stream query failed: {exc}")
            yield {
                "type": "error",
                "message": str(exc),
                "code": "PROCESSING_ERROR",
                "processing_time_ms": processing_time_ms,
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
