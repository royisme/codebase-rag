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
    """vector search result model"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}

class VectorDocument(BaseModel):
    """vector document model"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = {}

class MilvusVectorService:
    """Milvus vector service"""
    
    def __init__(self):
        self.connection_alias = "default"
        self.collection_name = settings.milvus_collection
        self.collection: Optional[Collection] = None
        self.embedding_dim = 512  # BGE-small-zh-v1.5 embedding dimension
        self._connected = False
    
    async def connect(self) -> bool:
        """connect to Milvus service"""
        try:
            connections.connect(
                alias=self.connection_alias,
                host=settings.milvus_host,
                port=settings.milvus_port
            )
            self._connected = True
            logger.info(f"Successfully connected to Milvus at {settings.milvus_host}:{settings.milvus_port}")
            
            # initialize collection
            await self._init_collection()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            return False
    
    async def _init_collection(self):
        """initialize Milvus collection"""
        try:
            # check if collection exists
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Collection {self.collection_name} already exists")
            else:
                # create new collection
                await self._create_collection()
            
            # load collection into memory
            self.collection.load()
            logger.info(f"Collection {self.collection_name} loaded into memory")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    async def _create_collection(self):
        """create Milvus collection"""
        try:
            # define field schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=65535),
            ]
            
            # create collection schema
            schema = CollectionSchema(
                fields=fields,
                description="Code knowledge vector collection"
            )
            
            # create collection
            self.collection = Collection(
                name=self.collection_name,
                schema=schema
            )
            
            # create index
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
        """insert documents into vector database"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        try:
            # prepare data
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            metadata_jsons = [str(doc.metadata) for doc in documents]
            
            # insert data
            entities = [ids, contents, embeddings, metadata_jsons]
            insert_result = self.collection.insert(entities)
            
            # flush collection to ensure data persistence
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
        """vector similarity search"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        top_k = top_k or settings.top_k
        
        try:
            # search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # execute search
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "content", "metadata_json"],
                expr=filters
            )
            
            # process results
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
        """delete documents"""
        if not self._connected or not self.collection:
            raise Exception("Not connected to Milvus or collection not initialized")
        
        try:
            # build delete expression
            id_expr = f"id in {ids}"
            
            # execute delete
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
        """get collection statistics"""
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
        """update document (delete old one and insert new one)"""
        try:
            # delete old document
            delete_result = await self.delete_documents([document.id])
            if not delete_result.get("success"):
                return delete_result
            
            # insert new document
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
        """batch vector search"""
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
            
            # process batch results
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
        """close connection"""
        try:
            if self.collection:
                self.collection.release()
            connections.disconnect(self.connection_alias)
            self._connected = False
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Failed to close Milvus connection: {e}")

# global vector service instance
vector_service = MilvusVectorService() 