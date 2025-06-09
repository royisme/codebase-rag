from typing import List, Dict, Any
from loguru import logger

from .base import DataStorer, ProcessedChunk, ExtractedRelation

class MilvusChunkStorer(DataStorer):
    """Milvus向量数据库存储器"""
    
    def __init__(self, vector_service):
        self.vector_service = vector_service
    
    async def store_chunks(self, chunks: List[ProcessedChunk]) -> Dict[str, Any]:
        """存储数据块到Milvus"""
        if not chunks:
            return {"success": True, "stored_count": 0}
        
        try:
            stored_count = 0
            
            for chunk in chunks:
                # 构建向量数据
                vector_data = {
                    "id": chunk.id,
                    "source_id": chunk.source_id,
                    "chunk_type": chunk.chunk_type.value,
                    "content": chunk.content,
                    "title": chunk.title or "",
                    "summary": chunk.summary or "",
                    "metadata": chunk.metadata
                }
                
                # 如果已有嵌入向量则直接使用，否则生成
                if chunk.embedding:
                    vector_data["embedding"] = chunk.embedding
                
                # 存储到Milvus
                result = await self.vector_service.add_document(
                    content=chunk.content,
                    doc_type=chunk.chunk_type.value,
                    metadata=vector_data
                )
                
                if result.get("success"):
                    stored_count += 1
                    logger.debug(f"Stored chunk {chunk.id} to Milvus")
                else:
                    logger.warning(f"Failed to store chunk {chunk.id}: {result.get('error')}")
            
            logger.info(f"Successfully stored {stored_count}/{len(chunks)} chunks to Milvus")
            
            return {
                "success": True,
                "stored_count": stored_count,
                "total_count": len(chunks),
                "storage_type": "vector"
            }
            
        except Exception as e:
            logger.error(f"Failed to store chunks to Milvus: {e}")
            return {
                "success": False,
                "error": str(e),
                "stored_count": 0,
                "total_count": len(chunks)
            }
    
    async def store_relations(self, relations: List[ExtractedRelation]) -> Dict[str, Any]:
        """Milvus不存储关系，返回空结果"""
        return {
            "success": True,
            "stored_count": 0,
            "message": "Milvus does not store relations",
            "storage_type": "vector"
        }

class Neo4jRelationStorer(DataStorer):
    """Neo4j图数据库存储器"""
    
    def __init__(self, graph_service):
        self.graph_service = graph_service
    
    async def store_chunks(self, chunks: List[ProcessedChunk]) -> Dict[str, Any]:
        """将数据块作为节点存储到Neo4j"""
        if not chunks:
            return {"success": True, "stored_count": 0}
        
        try:
            stored_count = 0
            
            for chunk in chunks:
                # 构建节点数据
                node_data = {
                    "id": chunk.id,
                    "source_id": chunk.source_id,
                    "chunk_type": chunk.chunk_type.value,
                    "title": chunk.title or "",
                    "content": chunk.content[:1000],  # 限制内容长度
                    "summary": chunk.summary or "",
                    **chunk.metadata
                }
                
                # 根据chunk类型确定节点标签
                node_label = self._get_node_label(chunk.chunk_type.value)
                
                # 创建节点
                result = await self.graph_service.create_node(
                    label=node_label,
                    properties=node_data
                )
                
                if result.get("success"):
                    stored_count += 1
                    logger.debug(f"Stored chunk {chunk.id} as {node_label} node in Neo4j")
                else:
                    logger.warning(f"Failed to store chunk {chunk.id}: {result.get('error')}")
            
            logger.info(f"Successfully stored {stored_count}/{len(chunks)} chunks to Neo4j")
            
            return {
                "success": True,
                "stored_count": stored_count,
                "total_count": len(chunks),
                "storage_type": "graph"
            }
            
        except Exception as e:
            logger.error(f"Failed to store chunks to Neo4j: {e}")
            return {
                "success": False,
                "error": str(e),
                "stored_count": 0,
                "total_count": len(chunks)
            }
    
    async def store_relations(self, relations: List[ExtractedRelation]) -> Dict[str, Any]:
        """存储关系到Neo4j"""
        if not relations:
            return {"success": True, "stored_count": 0}
        
        try:
            stored_count = 0
            
            for relation in relations:
                # 创建关系
                result = await self.graph_service.create_relationship(
                    from_node_id=relation.from_entity,
                    to_node_id=relation.to_entity,
                    relationship_type=relation.relation_type,
                    properties=relation.properties
                )
                
                if result.get("success"):
                    stored_count += 1
                    logger.debug(f"Created relation {relation.from_entity} -> {relation.to_entity}")
                else:
                    logger.warning(f"Failed to create relation {relation.id}: {result.get('error')}")
            
            logger.info(f"Successfully stored {stored_count}/{len(relations)} relations to Neo4j")
            
            return {
                "success": True,
                "stored_count": stored_count,
                "total_count": len(relations),
                "storage_type": "graph"
            }
            
        except Exception as e:
            logger.error(f"Failed to store relations to Neo4j: {e}")
            return {
                "success": False,
                "error": str(e),
                "stored_count": 0,
                "total_count": len(relations)
            }
    
    def _get_node_label(self, chunk_type: str) -> str:
        """根据chunk类型获取Neo4j节点标签"""
        label_map = {
            "text": "TextChunk",
            "code_function": "Function",
            "code_class": "Class",
            "code_module": "Module",
            "sql_table": "Table",
            "sql_schema": "Schema",
            "api_endpoint": "Endpoint",
            "document_section": "Section"
        }
        return label_map.get(chunk_type, "Chunk")

class HybridStorer(DataStorer):
    """混合存储器 - 同时使用Milvus和Neo4j"""
    
    def __init__(self, vector_service, graph_service):
        self.milvus_storer = MilvusChunkStorer(vector_service)
        self.neo4j_storer = Neo4jRelationStorer(graph_service)
    
    async def store_chunks(self, chunks: List[ProcessedChunk]) -> Dict[str, Any]:
        """同时存储到Milvus和Neo4j"""
        if not chunks:
            return {"success": True, "stored_count": 0}
        
        try:
            # 并行存储到两个数据库
            import asyncio
            
            milvus_task = self.milvus_storer.store_chunks(chunks)
            neo4j_task = self.neo4j_storer.store_chunks(chunks)
            
            milvus_result, neo4j_result = await asyncio.gather(
                milvus_task, neo4j_task, return_exceptions=True
            )
            
            # 处理结果
            total_stored = 0
            errors = []
            
            if isinstance(milvus_result, dict) and milvus_result.get("success"):
                total_stored += milvus_result.get("stored_count", 0)
                logger.info(f"Milvus stored {milvus_result.get('stored_count', 0)} chunks")
            else:
                error_msg = str(milvus_result) if isinstance(milvus_result, Exception) else milvus_result.get("error", "Unknown error")
                errors.append(f"Milvus error: {error_msg}")
                logger.error(f"Milvus storage failed: {error_msg}")
            
            if isinstance(neo4j_result, dict) and neo4j_result.get("success"):
                logger.info(f"Neo4j stored {neo4j_result.get('stored_count', 0)} chunks")
            else:
                error_msg = str(neo4j_result) if isinstance(neo4j_result, Exception) else neo4j_result.get("error", "Unknown error")
                errors.append(f"Neo4j error: {error_msg}")
                logger.error(f"Neo4j storage failed: {error_msg}")
            
            return {
                "success": len(errors) == 0,
                "stored_count": total_stored,
                "total_count": len(chunks),
                "storage_type": "hybrid",
                "milvus_result": milvus_result if not isinstance(milvus_result, Exception) else str(milvus_result),
                "neo4j_result": neo4j_result if not isinstance(neo4j_result, Exception) else str(neo4j_result),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to store chunks with hybrid storer: {e}")
            return {
                "success": False,
                "error": str(e),
                "stored_count": 0,
                "total_count": len(chunks),
                "storage_type": "hybrid"
            }
    
    async def store_relations(self, relations: List[ExtractedRelation]) -> Dict[str, Any]:
        """存储关系到Neo4j（Milvus不存储关系）"""
        return await self.neo4j_storer.store_relations(relations)

class StorerRegistry:
    """存储器注册表"""
    
    def __init__(self):
        self.storers = {}
    
    def register_storer(self, name: str, storer: DataStorer):
        """注册存储器"""
        self.storers[name] = storer
        logger.info(f"Registered storer: {name}")
    
    def get_storer(self, name: str) -> DataStorer:
        """获取存储器"""
        if name not in self.storers:
            raise ValueError(f"Storer '{name}' not found. Available storers: {list(self.storers.keys())}")
        return self.storers[name]
    
    def list_storers(self) -> List[str]:
        """列出所有注册的存储器"""
        return list(self.storers.keys())

# 全局存储器注册表实例
storer_registry = StorerRegistry()

def setup_default_storers(vector_service, graph_service):
    """设置默认存储器"""
    storer_registry.register_storer("milvus", MilvusChunkStorer(vector_service))
    storer_registry.register_storer("neo4j", Neo4jRelationStorer(graph_service))
    storer_registry.register_storer("hybrid", HybridStorer(vector_service, graph_service)) 