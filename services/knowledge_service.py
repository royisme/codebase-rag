from typing import List, Dict, Any, Optional
from loguru import logger

from .pipeline.pipeline import create_pipeline, KnowledgePipeline
from .pipeline.base import DataSourceType
from .rag_service import RAGService

class KnowledgeService:
    """knowledge service"""
    
    def __init__(self, vector_service, graph_service, rag_service: RAGService):
        self.vector_service = vector_service
        self.graph_service = graph_service
        self.rag_service = rag_service
        
        # create ETL pipeline
        self.pipeline = create_pipeline(
            vector_service=vector_service,
            graph_service=graph_service,
            embedding={
                "provider": "ollama",  # use Ollama as default
                "host": "http://localhost:11434",
                "model": "nomic-embed-text"
            }
        )
        
        logger.info("Knowledge Service initialized")
    
    # ETL 流水线方法
    
    async def add_document(self, 
                         content: str, 
                         name: str,
                         doc_type: str = "document",
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """add document to knowledge base"""
        try:
            # detect document type
            source_type = self._map_doc_type_to_source_type(doc_type)
            
            # process document
            result = await self.pipeline.process_content(
                content=content,
                name=name,
                source_type=source_type,
                metadata=metadata or {}
            )
            
            return {
                "success": result.success,
                "source_id": result.source_id,
                "chunks_count": len(result.chunks),
                "relations_count": len(result.relations),
                "error": result.error_message if not result.success else None,
                "metadata": result.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to add document {name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_file(self, file_path: str) -> Dict[str, Any]:
        """add file to knowledge base"""
        try:
            result = await self.pipeline.process_file(file_path)
            
            return {
                "success": result.success,
                "source_id": result.source_id,
                "chunks_count": len(result.chunks),
                "relations_count": len(result.relations),
                "error": result.error_message if not result.success else None,
                "metadata": result.metadata
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
                          file_patterns: List[str] = None,
                          exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """batch add files from directory to knowledge base"""
        try:
            results = await self.pipeline.process_directory(
                directory_path=directory_path,
                recursive=recursive,
                file_patterns=file_patterns,
                exclude_patterns=exclude_patterns
            )
            
            # count results
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            total_chunks = sum(len(r.chunks) for r in results if r.success)
            total_relations = sum(len(r.relations) for r in results if r.success)
            
            return {
                "success": True,
                "processed_files": len(results),
                "successful_files": successful,
                "failed_files": failed,
                "total_chunks": total_chunks,
                "total_relations": total_relations,
                "results": [
                    {
                        "source_id": r.source_id,
                        "success": r.success,
                        "error": r.error_message if not r.success else None,
                        "chunks_count": len(r.chunks),
                        "relations_count": len(r.relations)
                    }
                    for r in results
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to add directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_code_repository(self, repo_path: str) -> Dict[str, Any]:
        """add code repository to knowledge base"""
        try:
            # special file patterns for code repositories
            code_patterns = [
                "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.cpp", "*.c", "*.h",
                "*.cs", "*.go", "*.rs", "*.php", "*.rb", "*.scala", "*.kt", "*.swift",
                "*.md", "*.txt", "README*", "*.rst", "*.yaml", "*.yml", "*.json",
                "*.sql", "*.ddl"
            ]
            
            exclude_patterns = [
                ".*", "node_modules/*", "__pycache__/*", "*.pyc", "*.log", "*.tmp",
                "build/*", "dist/*", "target/*", "*.class", "*.jar", "*.war",
                ".git/*", ".svn/*", "coverage/*", "*.min.js", "*.min.css"
            ]
            
            return await self.add_directory(
                directory_path=repo_path,
                recursive=True,
                file_patterns=code_patterns,
                exclude_patterns=exclude_patterns
            )
            
        except Exception as e:
            logger.error(f"Failed to add code repository {repo_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # query methods
    
    async def query(self, 
                   question: str,
                   search_type: str = "hybrid",
                   top_k: int = 10) -> Dict[str, Any]:
        """query knowledge base"""
        try:
            return await self.rag_service.query(
                question=question,
                search_type=search_type,
                top_k=top_k
            )
            
        except Exception as e:
            logger.error(f"Failed to query knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_documents(self, 
                             query: str,
                             doc_type: Optional[str] = None,
                             top_k: int = 10) -> Dict[str, Any]:
        """search documents"""
        try:
            return await self.vector_service.search_documents(
                query=query,
                doc_type=doc_type,
                top_k=top_k
            )
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_code(self, 
                        query: str,
                        language: Optional[str] = None,
                        code_type: str = "function",
                        top_k: int = 10) -> Dict[str, Any]:
        """search code"""
        try:
            # build search filters
            filters = {"chunk_type": f"code_{code_type}"}
            if language:
                filters["language"] = language
            
            return await self.vector_service.search_documents(
                query=query,
                filters=filters,
                top_k=top_k
            )
            
        except Exception as e:
            logger.error(f"Failed to search code: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_relations(self, 
                             entity: str,
                             relation_type: Optional[str] = None,
                             direction: str = "both") -> Dict[str, Any]:
        """search entity relations"""
        try:
            # build Cypher query
            if direction == "outgoing":
                query = f"""
                MATCH (a)-[r]->(b)
                WHERE a.name = $entity
                {f"AND type(r) = $relation_type" if relation_type else ""}
                RETURN a, r, b
                LIMIT 50
                """
            elif direction == "incoming":
                query = f"""
                MATCH (a)-[r]->(b)
                WHERE b.name = $entity
                {f"AND type(r) = $relation_type" if relation_type else ""}
                RETURN a, r, b
                LIMIT 50
                """
            else:  # both
                query = f"""
                MATCH (a)-[r]-(b)
                WHERE a.name = $entity OR b.name = $entity
                {f"AND type(r) = $relation_type" if relation_type else ""}
                RETURN a, r, b
                LIMIT 50
                """
            
            params = {"entity": entity}
            if relation_type:
                params["relation_type"] = relation_type
            
            return await self.graph_service.execute_query(query, params)
            
        except Exception as e:
            logger.error(f"Failed to search relations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # statistics and management methods
    
    async def get_statistics(self) -> Dict[str, Any]:
        """get knowledge base statistics"""
        try:
            # get vector database statistics
            vector_stats = await self.vector_service.get_collection_stats()
            
            # get graph database statistics
            graph_stats = await self.graph_service.get_database_stats()
            
            # get pipeline statistics
            pipeline_stats = self.pipeline.get_stats()
            
            return {
                "success": True,
                "vector_database": vector_stats,
                "graph_database": graph_stats,
                "pipeline": pipeline_stats,
                "total_documents": vector_stats.get("total_entities", 0),
                "total_relations": graph_stats.get("total_relationships", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def clear_knowledge_base(self) -> Dict[str, Any]:
        """clear knowledge base"""
        try:
            # clear vector database
            vector_result = await self.vector_service.clear_collection()
            
            # clear graph database
            graph_result = await self.graph_service.clear_database()
            
            # reset pipeline statistics
            self.pipeline.reset_stats()
            
            return {
                "success": True,
                "vector_cleared": vector_result.get("success", False),
                "graph_cleared": graph_result.get("success", False),
                "message": "Knowledge base cleared successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _map_doc_type_to_source_type(self, doc_type: str) -> DataSourceType:
        """map document type to data source type"""
        type_mapping = {
            "document": DataSourceType.DOCUMENT,
            "code": DataSourceType.CODE,
            "sql": DataSourceType.SQL,
            "api": DataSourceType.API,
            "config": DataSourceType.CONFIG,
            "web": DataSourceType.WEB
        }
        
        return type_mapping.get(doc_type.lower(), DataSourceType.DOCUMENT) 