"""
基于 Neo4j 内置向量索引的现代化知识图谱服务
使用 LlamaIndex 的 KnowledgeGraphIndex 和 Neo4j 的原生向量搜索功能
支持多种 LLM 和嵌入模型提供商
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
from loguru import logger
import time

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

# Embedding Providers
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Graph Store
from llama_index.graph_stores.neo4j import Neo4jGraphStore

# Core components
from llama_index.core.node_parser import SimpleNodeParser

from config import settings

class Neo4jKnowledgeService:
    """基于 Neo4j 内置向量索引的知识图谱服务"""
    
    def __init__(self):
        self.graph_store = None
        self.knowledge_index = None
        self.query_engine = None
        self._initialized = False
        
        # 从配置中获取超时设置
        self.connection_timeout = settings.connection_timeout
        self.operation_timeout = settings.operation_timeout
        self.large_document_timeout = settings.large_document_timeout
        
        logger.info("Neo4j Knowledge Service created")
    
    def _create_llm(self):
        """根据配置创建 LLM 实例"""
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
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def _create_embedding_model(self):
        """根据配置创建嵌入模型实例"""
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
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            logger.info(f"Initializing with LLM provider: {settings.llm_provider}, Embedding provider: {settings.embedding_provider}")
            
            # 设置 LlamaIndex 全局配置
            Settings.llm = self._create_llm()
            Settings.embed_model = self._create_embedding_model()
            
            Settings.chunk_size = settings.chunk_size
            Settings.chunk_overlap = settings.chunk_overlap
            
            logger.info(f"LLM: {settings.llm_provider} - {getattr(settings, f'{settings.llm_provider}_model')}")
            logger.info(f"Embedding: {settings.embedding_provider} - {getattr(settings, f'{settings.embedding_provider}_embedding_model')}")
            
            # 初始化 Neo4j 图存储，添加超时配置
            self.graph_store = Neo4jGraphStore(
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                url=settings.neo4j_uri,
                database=settings.neo4j_database,
                timeout=self.connection_timeout
            )
            
            # 创建存储上下文
            storage_context = StorageContext.from_defaults(
                graph_store=self.graph_store
            )
            
            # 尝试加载现有索引，如果不存在则创建新的
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
                # 创建空的知识图谱索引
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
        """添加文档到知识图谱"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 创建文档
            doc = Document(
                text=content,
                metadata={
                    "title": title or "Untitled",
                    "source": "manual_input",
                    "timestamp": time.time(),
                    **(metadata or {})
                }
            )
            
            # 根据文档大小选择超时时间
            content_size = len(content)
            timeout = self.operation_timeout if content_size < 10000 else self.large_document_timeout
            
            logger.info(f"Adding document '{title}' (size: {content_size} chars, timeout: {timeout}s)")
            
            # 使用异步超时控制插入操作
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
        """添加文件到知识图谱"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 读取文件
            documents = await asyncio.to_thread(
                lambda: SimpleDirectoryReader(input_files=[file_path]).load_data()
            )
            
            if not documents:
                return {
                    "success": False,
                    "error": "No documents loaded from file"
                }
            
            # 批量插入，每个文档单独处理超时
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
        """批量添加目录中的文件"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 设置文件扩展名过滤
            if file_extensions is None:
                file_extensions = [".txt", ".md", ".py", ".js", ".ts", ".sql", ".json", ".yaml", ".yml"]
            
            # 读取目录
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
            
            # 批量插入，每个文档单独处理超时
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
                    
                    if i % 10 == 0:  # 每10个文档记录一次进度
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
    
    async def query(self, 
                   question: str,
                   mode: str = "hybrid") -> Dict[str, Any]:
        """查询知识图谱"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 根据模式创建不同的查询引擎
            if mode == "hybrid":
                # 混合模式：图遍历 + 向量搜索
                query_engine = self.knowledge_index.as_query_engine(
                    include_text=True,
                    response_mode="tree_summarize",
                    embedding_mode="hybrid"
                )
            elif mode == "graph_only":
                # 仅图遍历
                query_engine = self.knowledge_index.as_query_engine(
                    include_text=False,
                    response_mode="tree_summarize"
                )
            elif mode == "vector_only":
                # 仅向量搜索
                query_engine = self.knowledge_index.as_query_engine(
                    include_text=True,
                    response_mode="compact",
                    embedding_mode="embedding"
                )
            else:
                query_engine = self.query_engine
            
            # 执行查询，添加超时控制
            response = await asyncio.wait_for(
                asyncio.to_thread(query_engine.query, question),
                timeout=self.operation_timeout
            )
            
            # 提取源节点信息
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
        """获取图谱结构信息"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 获取图谱统计信息，添加超时控制
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
        """基于向量相似度搜索节点"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 使用检索器进行向量搜索，添加超时控制
            retriever = self.knowledge_index.as_retriever(
                similarity_top_k=top_k,
                include_text=True
            )
            
            nodes = await asyncio.wait_for(
                asyncio.to_thread(retriever.retrieve, query),
                timeout=self.operation_timeout
            )
            
            # 格式化结果
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
        """获取知识图谱统计信息"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 尝试获取基本统计信息，添加超时控制
            try:
                # 如果图存储支持统计查询
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
        """清空知识库"""
        if not self._initialized:
            raise Exception("Service not initialized")
        
        try:
            # 重新创建空的索引，添加超时控制
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
            
            # 重新创建查询引擎
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
        """关闭服务"""
        try:
            if self.graph_store:
                # 如果图存储有关闭方法，调用它
                if hasattr(self.graph_store, 'close'):
                    await asyncio.wait_for(
                        asyncio.to_thread(self.graph_store.close),
                        timeout=self.connection_timeout
                    )
                elif hasattr(self.graph_store, '_driver') and self.graph_store._driver:
                    # 关闭 Neo4j 驱动连接
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
        """动态设置超时参数"""
        if connection_timeout is not None:
            self.connection_timeout = connection_timeout
            logger.info(f"Connection timeout set to {connection_timeout}s")
        
        if operation_timeout is not None:
            self.operation_timeout = operation_timeout
            logger.info(f"Operation timeout set to {operation_timeout}s")
        
        if large_document_timeout is not None:
            self.large_document_timeout = large_document_timeout
            logger.info(f"Large document timeout set to {large_document_timeout}s")

# 全局服务实例
neo4j_knowledge_service = Neo4jKnowledgeService() 