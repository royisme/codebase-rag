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
    SimpleDirectoryReader
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

# Core components
from llama_index.core.node_parser import SimpleNodeParser

from config import settings

class Neo4jKnowledgeService:
    """knowledge graph service based on Neo4j's native vector index"""
    
    def __init__(self):
        self.graph_store = None
        self.knowledge_index = None
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
                timeout=self.connection_timeout
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
                show_progress=True
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
        
        try:
            response = await self._stream_query_response(
                question,
                mode=mode,
                include_evidence=include_evidence,
                max_results=max_results,
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
            raw_confidence = getattr(response, "score", None)
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
        source_nodes = []
        evidence_metadata = []  # 初始化证据元数据列表
        
        logger.debug(f"[PERF-KG] Starting stream query: {question[:50]}...")
        
        try:
            # Get the LLM instance
            llm = Settings.llm
            
            # Build context from graph if query engine is available
            context_text = ""
            if self.query_engine:
                try:
                    # Retrieve relevant nodes first
                    retrieve_start = perf_time.perf_counter()
                    logger.debug(f"[PERF-KG] Starting retrieval...")
                    
                    # Step 1: 创建 retriever
                    retriever_create_start = perf_time.perf_counter()
                    retriever = self.knowledge_index.as_retriever(
                        similarity_top_k=max_results,
                        include_text=True
                    )
                    retriever_create_time = perf_time.perf_counter() - retriever_create_start
                    logger.debug(f"[PERF-KG] Retriever created in {retriever_create_time:.2f}s")
                    
                    # Step 2: 执行检索（包含embedding生成 + 向量搜索）
                    retrieve_exec_start = perf_time.perf_counter()
                    logger.debug(f"[PERF-KG] Calling retriever.retrieve() with question: {question[:50]}...")
                    
                    # 增加超时时间到 60 秒
                    nodes = await asyncio.wait_for(
                        asyncio.to_thread(retriever.retrieve, question),
                        timeout=60
                    )
                    source_nodes = nodes
                    
                    retrieve_exec_time = perf_time.perf_counter() - retrieve_exec_start
                    retrieve_time = perf_time.perf_counter() - retrieve_start
                    logger.info(f"[PERF-KG] Retrieval completed in {retrieve_time:.2f}s (exec: {retrieve_exec_time:.2f}s, {len(nodes)} nodes)")
                    logger.debug(f"[PERF-KG] Breakdown: retriever_create={retriever_create_time:.2f}s, retrieve_exec={retrieve_exec_time:.2f}s")
                    
                    # Build context from nodes with numbered references
                    context_parts = []
                    evidence_metadata = []  # 保留完整元数据
                    
                    for idx, node in enumerate(nodes[:max_results], start=1):
                        metadata = node.metadata or {}
                        text = node.text[:300] if len(node.text) > 300 else node.text
                        
                        # 构建文件路径信息
                        file_path = metadata.get("file_path", "unknown")
                        start_line = metadata.get("start_line")
                        end_line = metadata.get("end_line")
                        
                        # 添加编号的上下文
                        location = f"{file_path}"
                        if start_line:
                            location += f" (L{start_line}"
                            if end_line and end_line != start_line:
                                location += f"-{end_line}"
                            location += ")"
                        
                        context_parts.append(f"[{idx}] {location}:\n{text}")
                        
                        # 保存完整元数据用于生成证据
                        evidence_metadata.append({
                            "id": node.node_id or f"ev_{idx}",
                            "snippet": text,
                            "full_text": node.text,
                            "repo": metadata.get("repo"),
                            "branch": metadata.get("branch", "main"),
                            "file_path": file_path,
                            "start_line": start_line,
                            "end_line": end_line,
                            "source_type": metadata.get("source_type", "code"),
                            "score": getattr(node, 'score', 0.0),
                        })
                    
                    if context_parts:
                        context_text = f"相关上下文:\n\n" + "\n\n".join(context_parts)
                        logger.debug(f"[PERF-KG] Built context with {len(context_parts)} nodes")
                    else:
                        logger.debug("[PERF-KG] No relevant nodes found for context")
                except asyncio.TimeoutError:
                    logger.warning(f"[PERF-KG] Context retrieval timed out after 30s for question: {question[:50]}...")
                except Exception as ctx_exc:
                    logger.warning(f"[PERF-KG] Failed to build context: {ctx_exc.__class__.__name__}: {ctx_exc}")
            else:
                logger.debug("[PERF-KG] Query engine not available, proceeding without context")
            
            # Construct prompt
            prompt_start = perf_time.perf_counter()
            if context_text:
                prompt = f"""基于以下编号的上下文信息，用 Markdown 格式回答问题。引用上下文时请使用编号标记（如 [1] [2]）。

{context_text}

问题: {question}

要求：
1. 使用 Markdown 格式回答（支持标题、列表、代码块等）
2. 代码示例请用代码块包裹，并指定语言，例如：```python
3. **引用上下文时，必须用 [1] [2] 等编号标记来源**
4. 回答要简洁清晰，重点突出
5. 如果有多个要点，使用列表或编号

回答："""
            else:
                prompt = f"""请用 Markdown 格式回答以下问题：

{question}

要求：
1. 使用 Markdown 格式（支持标题、列表、代码块等）
2. 代码示例请用代码块包裹，并指定语言
3. 回答要简洁清晰，重点突出

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
            
            # After streaming completes, yield metadata
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate confidence score
            confidence_score = 0.0
            if source_nodes:
                scores = []
                for node in source_nodes:
                    raw_score = getattr(node, 'score', 0.0)
                    if isinstance(raw_score, (int, float)):
                        scores.append(float(raw_score))
                    else:
                        try:
                            scores.append(float(raw_score))
                        except (TypeError, ValueError):  # pragma: no cover - defensive
                            continue
                confidence_score = max(scores) if scores else 0.0

            # Clamp confidence into [0, 1] to satisfy API schema
            confidence_score = max(0.0, min(1.0, float(confidence_score)))
            
            resolved_sources = source_ids or [
                uuid.UUID(str((node.metadata or {}).get("source_id", uuid.uuid4())))
                if (node.metadata or {}).get("source_id")
                else uuid.uuid4()
                for node in source_nodes[:5]
            ]
            
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
                    # 构建 GitHub 链接（如果有 repo 信息）
                    github_link = None
                    if ev_data.get("repo") and ev_data.get("file_path"):
                        repo = ev_data["repo"]
                        branch = ev_data.get("branch", "main")
                        file_path = ev_data["file_path"]
                        start_line = ev_data.get("start_line")
                        
                        # 假设 repo 格式为 owner/repo_name
                        github_link = f"https://github.com/{repo}/blob/{branch}/{file_path}"
                        if start_line:
                            end_line = ev_data.get("end_line", start_line)
                            if end_line and end_line != start_line:
                                github_link += f"#L{start_line}-L{end_line}"
                            else:
                                github_link += f"#L{start_line}"
                    
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
