from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema, DataType,
    utility, MilvusException
)
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel
from loguru import logger
from config import settings
import numpy as np

class VectorSearchResult(BaseModel):
    """向量搜索结果模型"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}

class VectorDocument(BaseModel):
    """向量文档模型"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = {}

class MilvusVectorService:
    """Milvus向量服务"""
    
    def __init__(self):
        self.connection_alias = "default"
        self.collection_name = settings.milvus_collection
        self.collection: Optional[Collection] = None
        self.embedding_dim = 512  # BGE-small-zh-v1.5 embedding dimension
        self._connected = False
    
    async def connect(self) -> bool:
        """连接到Milvus服务"""
        try:
            connections.connect(
                alias=self.connection_alias,
                host=settings.milvus_host,
                port=settings.milvus_port
            )
            self._connected = True
            logger.info(f"Successfully connected to Milvus at {settings.milvus_host}:{settings.milvus_port}")
            
            # 初始化集合
            await self._init_collection()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            return False
    
    async def _init_collection(self):
        """初始化Milvus集合"""
        try:
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Collection {self.collection_name} already exists")
            else:
                # 创建新集合
                await self._create_collection()
            
            # 加载集合到内存
            self.collection.load()
            logger.info(f"Collection {self.collection_name} loaded into memory")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    async def _create_collection(self):
        """创建Milvus集合"""
        try:
            # 定义字段schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=65535),
            ]
            
            # 创建集合schema
            schema = CollectionSchema(
                fields=fields,
                description="Code knowledge vector collection"
            )
            
            # 创建集合
            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            logger.info(f"Successfully created collection {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    async def insert_documents(self, documents: List[VectorDocument]) -> Dict[str, Any]:
        """插入文档到向量数据库"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        try:
            # 准备数据
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            metadata_jsons = [str(doc.metadata) for doc in documents]
            
            # 插入数据
            entities = [ids, contents, embeddings, metadata_jsons]
            insert_result = self.collection.insert(entities)
            
            # 刷新集合以确保数据持久化
            self.collection.flush()
            
            logger.info(f"Successfully inserted {len(documents)} documents")
            
            return {
                "success": True,
                "inserted_count": len(documents),
                "primary_keys": insert_result.primary_keys
            }
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_vectors(
        self, 
        query_embedding: List[float], 
        top_k: int = None,
        filters: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """向量相似度搜索"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        top_k = top_k or settings.top_k
        
        try:
            # 搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "content", "metadata_json"],
                expr=filters
            )
            
            # 处理结果
            search_results = []
            for hits in results:
                for hit in hits:
                    result = VectorSearchResult(
                        id=hit.entity.get("id"),
                        content=hit.entity.get("content"),
                        score=float(hit.score),
                        metadata=eval(hit.entity.get("metadata_json", "{}"))
                    )
                    search_results.append(result)
            
            logger.info(f"Found {len(search_results)} similar documents")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []
    
    async def delete_documents(self, ids: List[str]) -> Dict[str, Any]:
        """删除文档"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        try:
            # 构建删除表达式
            id_expr = f"id in {ids}"
            
            # 执行删除
            self.collection.delete(id_expr)
            self.collection.flush()
            
            logger.info(f"Successfully deleted documents with ids: {ids}")
            
            return {
                "success": True,
                "deleted_ids": ids
            }
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        if not self._connected or not self.collection:
            return {"error": "Not connected"}
        
        try:
            stats = self.collection.num_entities
            return {
                "collection_name": self.collection_name,
                "total_documents": stats,
                "embedding_dim": self.embedding_dim
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    async def update_document(self, document: VectorDocument) -> Dict[str, Any]:
        """更新文档（先删除再插入）"""
        try:
            # 先删除旧文档
            delete_result = await self.delete_documents([document.id])
            if not delete_result.get("success"):
                return delete_result
            
            # 插入新文档
            insert_result = await self.insert_documents([document])
            return insert_result
            
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def batch_search(
        self, 
        query_embeddings: List[List[float]], 
        top_k: int = None
    ) -> List[List[VectorSearchResult]]:
        """批量向量搜索"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        top_k = top_k or settings.top_k
        
        try:
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=query_embeddings,
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "content", "metadata_json"]
            )
            
            # 处理批量结果
            batch_results = []
            for hits in results:
                search_results = []
                for hit in hits:
                    result = VectorSearchResult(
                        id=hit.entity.get("id"),
                        content=hit.entity.get("content"),
                        score=float(hit.score),
                        metadata=eval(hit.entity.get("metadata_json", "{}"))
                    )
                    search_results.append(result)
                batch_results.append(search_results)
            
            return batch_results
            
        except Exception as e:
            logger.error(f"Failed to batch search: {e}")
            return []
    
    async def close(self):
        """关闭连接"""
        try:
            if self.collection:
                self.collection.release()
            connections.disconnect(self.connection_alias)
            self._connected = False
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Failed to close Milvus connection: {e}")

# 全局向量服务实例
vector_service = MilvusVectorService() 