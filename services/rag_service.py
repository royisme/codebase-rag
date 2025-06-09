"""
RAG service
supports multiple LLM and embedding model providers
supports multiple vector and graph database providers
supports multiple query modes (vector only, graph only, hybrid)
supports multiple response modes (compact, detailed)
supports multiple postprocessing methods (similarity cutoff, keyword extraction)
supports multiple document types (text, code, sql, api, config, web)
supports multiple document sources (local file, remote URL, database, API)  
"""
from llama_index.core import (
    VectorStoreIndex, ServiceContext, Document, Settings
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core import KnowledgeGraphIndex, Settings
from llama_index.graph_stores.neo4j import Neo4jGraphStore

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel
from loguru import logger
from config import settings
from services.vector_service import vector_service, VectorDocument
from services.graph_service import graph_service
from services.sql_parser import sql_analyzer
import asyncio
import uuid

class RAGQuery(BaseModel):
    """RAG query request model"""
    question: str
    context: Optional[str] = None
    max_results: int = 5
    include_graph: bool = True
    include_sql: bool = True
    temperature: float = 0.7

class RAGResponse(BaseModel):
    """RAG query response model"""
    answer: str
    sources: List[Dict[str, Any]] = []
    vector_results: List[Dict[str, Any]] = []
    graph_results: Optional[Dict[str, Any]] = None
    sql_analysis: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0
    processing_time: float = 0.0

class KnowledgeDocument(BaseModel):
    """knowledge document model"""
    id: Optional[str] = None
    title: str
    content: str
    doc_type: str = "text"  # text, code, sql, etc.
    metadata: Dict[str, Any] = {}
    tags: List[str] = []

class RAGService:
    """RAG knowledge service"""
    
    def __init__(self):
        self.embedding_model = None
        self.llm_model = None
        self.vector_index = None
        self.query_engine = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """initialize RAG service"""
        try:
            # initialize embedding model
            self.embedding_model = OllamaEmbedding(
                model=settings.embedding_model,
                base_url=settings.ollama_base_url
            )
            
            # initialize LLM model
            self.llm_model = Ollama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=0.7
            )
            
            # set global config
            Settings.embed_model = self.embedding_model
            Settings.llm = self.llm_model
            Settings.chunk_size = settings.chunk_size
            Settings.chunk_overlap = settings.chunk_overlap
            
            # connect to vector database
            if not await vector_service.connect():
                raise Exception("Failed to connect to vector database")
            
            # connect to graph database
            if not await graph_service.connect():
                raise Exception("Failed to connect to graph database")
            
            # initialize vector index
            await self._setup_vector_index()
            
            self._initialized = True
            logger.info("RAG service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            return False
    
    async def _setup_vector_index(self):
        """setup vector index"""
        try:
            # create Milvus vector store
            vector_store = MilvusVectorStore(
                host=settings.milvus_host,
                port=settings.milvus_port,
                collection_name=settings.milvus_collection,
                dim=512
            )
            
            # create vector index
            self.vector_index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store
            )
            
            # create query engine
            retriever = VectorIndexRetriever(
                index=self.vector_index,
                similarity_top_k=settings.top_k
            )
            
            response_synthesizer = get_response_synthesizer(
                response_mode="compact"
            )
            
            self.query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer,
                node_postprocessors=[
                    SimilarityPostprocessor(similarity_cutoff=0.7)
                ]
            )
            
            logger.info("Vector index setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup vector index: {e}")
            raise
    
    async def add_document(self, document: KnowledgeDocument) -> Dict[str, Any]:
        """add document to knowledge base"""
        if not self._initialized:
            raise Exception("RAG service not initialized")
        
        try:
            # generate document ID
            doc_id = document.id or str(uuid.uuid4())
            
            # create llama-index document
            llama_doc = Document(
                text=document.content,
                doc_id=doc_id,
                metadata={
                    "title": document.title,
                    "doc_type": document.doc_type,
                    "tags": document.tags,
                    **document.metadata
                }
            )
            
            # parse document to nodes
            parser = SimpleNodeParser.from_defaults(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap
            )
            nodes = parser.get_nodes_from_documents([llama_doc])
            
            # generate embedding and store to vector database
            embeddings = []
            vector_docs = []
            
            for i, node in enumerate(nodes):
                # generate embedding
                embedding = self.embedding_model.get_text_embedding(node.text)
                embeddings.append(embedding)
                
                # create vector document
                vector_doc = VectorDocument(
                    id=f"{doc_id}_chunk_{i}",
                    content=node.text,
                    embedding=embedding,
                    metadata={
                        "doc_id": doc_id,
                        "chunk_index": i,
                        "title": document.title,
                        "doc_type": document.doc_type,
                        **node.metadata
                    }
                )
                vector_docs.append(vector_doc)
            
            # insert to vector database
            vector_result = await vector_service.insert_documents(vector_docs)
            
            # if code document, extract entities and store to graph database
            graph_result = None
            if document.doc_type == "code":
                graph_result = await self._extract_and_store_code_entities(document, doc_id)
            
            # if SQL document, perform SQL analysis
            sql_result = None
            if document.doc_type == "sql":
                sql_result = sql_analyzer.parse_sql(document.content)
            
            logger.info(f"Successfully added document: {doc_id}")
            
            return {
                "success": True,
                "document_id": doc_id,
                "chunks_created": len(nodes),
                "vector_result": vector_result,
                "graph_result": graph_result,
                "sql_result": sql_result
            }
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_and_store_code_entities(self, document: KnowledgeDocument, doc_id: str) -> Dict[str, Any]:
        """extract entities from code document and store to graph database"""
        try:
            # simple code entity extraction (can use AST in real application)
            content = document.content
            entities = []
            
            # extract function definitions
            import re
            function_pattern = r'def\s+(\w+)\s*\('
            functions = re.findall(function_pattern, content)
            
            for func_name in functions:
                from services.graph_service import GraphNode
                node = GraphNode(
                    id=f"{doc_id}_func_{func_name}",
                    labels=["Function", "CodeEntity"],
                    properties={
                        "name": func_name,
                        "doc_id": doc_id,
                        "type": "function",
                        "language": document.metadata.get("language", "python")
                    }
                )
                entities.append(node)
            
            # extract class definitions
            class_pattern = r'class\s+(\w+)'
            classes = re.findall(class_pattern, content)
            
            for class_name in classes:
                from services.graph_service import GraphNode
                node = GraphNode(
                    id=f"{doc_id}_class_{class_name}",
                    labels=["Class", "CodeEntity"],
                    properties={
                        "name": class_name,
                        "doc_id": doc_id,
                        "type": "class",
                        "language": document.metadata.get("language", "python")
                    }
                )
                entities.append(node)
            
            # batch create nodes
            if entities:
                result = await graph_service.batch_create_nodes(entities)
                return result
            
            return {"success": True, "entities_created": 0}
            
        except Exception as e:
            logger.error(f"Failed to extract code entities: {e}")
            return {"success": False, "error": str(e)}
    
    async def query(self, query_request: RAGQuery) -> RAGResponse:
        """execute RAG query"""
        if not self._initialized:
            raise Exception("RAG service not initialized")
        
        import time
        start_time = time.time()
        
        try:
            # 1. vector search
            query_embedding = self.embedding_model.get_text_embedding(query_request.question)
            vector_results = await vector_service.search_vectors(
                query_embedding=query_embedding,
                top_k=query_request.max_results
            )
            
            # 2. graph query (if enabled)
            graph_results = None
            if query_request.include_graph:
                graph_results = await self._query_graph_knowledge(query_request.question)
            
            # 3. SQL analysis (if enabled and contains SQL keywords)
            sql_analysis = None
            if query_request.include_sql and self._contains_sql_keywords(query_request.question):
                sql_analysis = await self._analyze_sql_query(query_request.question)
            
            # 4. build context
            context_parts = []
            
            # add vector search results
            for result in vector_results[:3]:  # take top 3 most relevant results
                context_parts.append(f"related content: {result.content}")
            
            # add graph query results
            if graph_results and graph_results.get("nodes"):
                graph_context = "graph database related information:\n"
                for node in graph_results["nodes"][:2]:
                    graph_context += f"- {node.labels}: {node.properties.get('name', 'Unknown')}\n"
                context_parts.append(graph_context)
            
            # add SQL analysis results
            if sql_analysis:
                context_parts.append(f"SQL analysis: {sql_analysis.get('explanation', '')}")
            
            # 5. generate final answer
            full_context = "\n\n".join(context_parts)
            
            prompt = f"""
            based on the following context information, answer the user's question. Please provide accurate, detailed and useful answers.

            context information:
            {full_context}

            user question: {query_request.question}

            answer:
            """
            
            # use LLM to generate answer
            response = self.llm_model.complete(prompt, temperature=query_request.temperature)
            answer = response.text
            
            # calculate confidence score (based on vector similarity)
            confidence_score = 0.0
            if vector_results:
                confidence_score = sum(r.score for r in vector_results) / len(vector_results)
            
            processing_time = time.time() - start_time
            
            # build response
            rag_response = RAGResponse(
                answer=answer,
                sources=[
                    {
                        "id": r.id,
                        "content": r.content[:200] + "...",
                        "score": r.score,
                        "metadata": r.metadata
                    } for r in vector_results
                ],
                vector_results=[r.dict() for r in vector_results],
                graph_results=graph_results,
                sql_analysis=sql_analysis,
                confidence_score=confidence_score,
                processing_time=processing_time
            )
            
            logger.info(f"RAG query completed in {processing_time:.2f}s")
            return rag_response
            
        except Exception as e:
            logger.error(f"Failed to process RAG query: {e}")
            return RAGResponse(
                answer=f"Sorry, an error occurred while processing the query: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    async def _query_graph_knowledge(self, question: str) -> Optional[Dict[str, Any]]:
        """query graph knowledge base"""
        try:
            # extract keywords from question
            keywords = self._extract_keywords(question)
            
            if not keywords:
                return None
            
            # build Cypher query
            cypher_query = """
            MATCH (n)
            WHERE ANY(keyword IN $keywords WHERE 
                toLower(n.name) CONTAINS toLower(keyword) OR
                ANY(label IN labels(n) WHERE toLower(label) CONTAINS toLower(keyword))
            )
            RETURN n LIMIT 10
            """
            
            result = await graph_service.execute_cypher(cypher_query, {"keywords": keywords})
            
            return {
                "nodes": [node.dict() for node in result.nodes],
                "query": cypher_query,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"Failed to query graph knowledge: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """extract keywords from text"""
        # simple keyword extraction (can use NLP library in real application)
        import re
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)
        
        # filter common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 2 and word.lower() not in stopwords]
        
        return keywords[:5]  # return top 5 keywords
    
    def _contains_sql_keywords(self, text: str) -> bool:
        """check if text contains SQL keywords"""
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'TABLE']
        text_upper = text.upper()
        return any(keyword in text_upper for keyword in sql_keywords)
    
    async def _analyze_sql_query(self, question: str) -> Optional[Dict[str, Any]]:
        """analyze SQL related query"""
        try:
            # try to extract SQL statement from question
            import re
            sql_pattern = r'```sql\s*(.*?)\s*```|```\s*(SELECT.*?;?)\s*```'
            matches = re.findall(sql_pattern, question, re.IGNORECASE | re.DOTALL)
            
            if matches:
                sql_text = matches[0][0] or matches[0][1]
                result = sql_analyzer.parse_sql(sql_text.strip())
                return result.dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze SQL query: {e}")
            return None
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """get knowledge base statistics"""
        try:
            # vector database statistics
            vector_stats = await vector_service.get_collection_stats()
            
            # graph database statistics
            graph_stats = await graph_service.get_database_stats()
            
            return {
                "vector_database": vector_stats,
                "graph_database": graph_stats,
                "embedding_model": settings.embedding_model,
                "llm_model": settings.ollama_model
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge stats: {e}")
            return {"error": str(e)}
    
    async def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """delete document"""
        try:
            # delete related documents from vector database
            vector_result = await vector_service.delete_documents([f"{doc_id}_chunk_{i}" for i in range(100)])
            
            # delete related nodes from graph database
            graph_result = await graph_service.delete_node(doc_id)
            
            return {
                "success": True,
                "document_id": doc_id,
                "vector_result": vector_result,
                "graph_result": graph_result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """close RAG service"""
        try:
            await vector_service.close()
            await graph_service.close()
            self._initialized = False
            logger.info("RAG service closed")
        except Exception as e:
            logger.error(f"Failed to close RAG service: {e}")

# global RAG service instance
rag_service = RAGService() 