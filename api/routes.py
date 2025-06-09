from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from services.rag_service import rag_service, RAGQuery, KnowledgeDocument
from services.sql_parser import sql_analyzer
from services.vector_service import vector_service
from services.graph_service import graph_service
from services.knowledge_service import KnowledgeService
from services.task_queue import task_queue
from config import settings
from loguru import logger

# 创建路由器
router = APIRouter()

# 初始化知识库服务
knowledge_service = KnowledgeService(
    vector_service=vector_service,
    graph_service=graph_service,
    rag_service=rag_service
)

# 请求模型
class HealthResponse(BaseModel):
    status: str
    services: Dict[str, bool]
    version: str

class SQLParseRequest(BaseModel):
    sql: str
    dialect: str = "mysql"

class GraphQueryRequest(BaseModel):
    cypher: str
    parameters: Optional[Dict[str, Any]] = None

class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 5

class DocumentAddRequest(BaseModel):
    content: str
    name: str
    doc_type: str = "document"
    metadata: Optional[Dict[str, Any]] = None

class DirectoryProcessRequest(BaseModel):
    directory_path: str
    recursive: bool = True
    file_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None

# 健康检查
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    try:
        # 检查各个服务状态
        services_status = {
            "rag_service": rag_service._initialized,
            "vector_service": vector_service._connected,
            "graph_service": graph_service._connected,
        }
        
        overall_status = "healthy" if all(services_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            services=services_status,
            version=settings.app_version
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# RAG查询接口
@router.post("/query")
async def query_knowledge(query_request: RAGQuery):
    """RAG知识查询接口"""
    try:
        response = await knowledge_service.query(
            question=query_request.question,
            search_type=query_request.search_type,
            top_k=query_request.top_k
        )
        return response
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 知识库管理接口

@router.post("/knowledge/documents")
async def add_document_to_knowledge_base(
    request: DocumentAddRequest,
    async_processing: bool = False
):
    """添加文档到知识库"""
    try:
        if async_processing:
            # 异步处理
            task_id = await task_queue.submit_task(
                task_func=None,  # 将由处理器处理
                task_kwargs={
                    "document_content": request.content,
                    "document_type": request.doc_type,
                    "metadata": request.metadata
                },
                task_name=f"Process document: {request.name}",
                task_type="document_processing",
                metadata={"document_name": request.name}
            )
            
            return JSONResponse(status_code=202, content={
                "message": "Document processing started",
                "task_id": task_id,
                "status": "processing"
            })
        else:
            # 同步处理（保持向后兼容）
            result = await knowledge_service.add_document(
                content=request.content,
                name=request.name,
                doc_type=request.doc_type,
                metadata=request.metadata
            )
            
            if result.get("success"):
                return JSONResponse(status_code=201, content=result)
            else:
                raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/files/{file_path:path}")
async def add_file_to_knowledge_base(file_path: str):
    """添加文件到知识库"""
    try:
        result = await knowledge_service.add_file(file_path)
        
        if result.get("success"):
            return JSONResponse(status_code=201, content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/directories")
async def add_directory_to_knowledge_base(
    request: DirectoryProcessRequest,
    async_processing: bool = True  # 目录处理默认异步
):
    """批量添加目录到知识库"""
    try:
        if async_processing:
            # 异步处理
            task_id = await task_queue.submit_task(
                task_func=None,  # 将由处理器处理
                task_kwargs={
                    "directory_path": request.directory_path,
                    "file_patterns": request.file_patterns or ["*.txt", "*.md", "*.sql"],
                    "batch_size": 10
                },
                task_name=f"Process directory: {request.directory_path}",
                task_type="batch_processing",
                metadata={
                    "directory_path": request.directory_path,
                    "recursive": request.recursive
                }
            )
            
            return JSONResponse(status_code=202, content={
                "message": "Directory processing started",
                "task_id": task_id,
                "status": "processing"
            })
        else:
            # 同步处理（保持向后兼容）
            result = await knowledge_service.add_directory(
                directory_path=request.directory_path,
                recursive=request.recursive,
                file_patterns=request.file_patterns,
                exclude_patterns=request.exclude_patterns
            )
            
            if result.get("success"):
                return JSONResponse(status_code=201, content=result)
            else:
                raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add directory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/repositories/{repo_path:path}")
async def add_repository_to_knowledge_base(repo_path: str):
    """添加代码仓库到知识库"""
    try:
        result = await knowledge_service.add_code_repository(repo_path)
        
        if result.get("success"):
            return JSONResponse(status_code=201, content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add repository failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 搜索接口

@router.post("/knowledge/search/documents")
async def search_documents(query: str, doc_type: Optional[str] = None, top_k: int = 10):
    """搜索文档"""
    try:
        result = await knowledge_service.search_documents(
            query=query,
            doc_type=doc_type,
            top_k=top_k
        )
        return result
        
    except Exception as e:
        logger.error(f"Search documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/search/code")
async def search_code(
    query: str, 
    language: Optional[str] = None, 
    code_type: str = "function", 
    top_k: int = 10
):
    """搜索代码"""
    try:
        result = await knowledge_service.search_code(
            query=query,
            language=language,
            code_type=code_type,
            top_k=top_k
        )
        return result
        
    except Exception as e:
        logger.error(f"Search code failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/search/relations")
async def search_relations(
    entity: str,
    relation_type: Optional[str] = None,
    direction: str = "both"
):
    """搜索实体关系"""
    try:
        result = await knowledge_service.search_relations(
            entity=entity,
            relation_type=relation_type,
            direction=direction
        )
        return result
        
    except Exception as e:
        logger.error(f"Search relations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 兼容旧API - 文档管理
@router.post("/documents")
async def add_document(document: KnowledgeDocument):
    """添加文档到知识库（兼容接口）"""
    try:
        result = await knowledge_service.add_document(
            content=document.content,
            name=document.title,
            doc_type=document.doc_type,
            metadata={
                "tags": document.tags,
                **document.metadata
            }
        )
        
        if result.get("success"):
            return JSONResponse(status_code=201, content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form("document"),
    tags: Optional[str] = Form(None),
    async_processing: bool = Form(False)
):
    """上传文件到知识库（兼容接口）"""
    try:
        # 读取文件内容
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # 解析标签
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
        
        metadata = {
            "tags": tag_list,
            "filename": file.filename,
            "file_size": len(content),
            "content_type": file.content_type
        }
        
        if async_processing:
            # 异步处理
            task_id = await task_queue.submit_task(
                task_func=None,  # 将由处理器处理
                task_kwargs={
                    "document_content": content_str,
                    "document_type": doc_type,
                    "metadata": metadata
                },
                task_name=f"Upload and process: {title}",
                task_type="document_processing",
                metadata={"document_name": title, "filename": file.filename}
            )
            
            return JSONResponse(status_code=202, content={
                "message": "File upload and processing started",
                "task_id": task_id,
                "status": "processing",
                "filename": file.filename
            })
        else:
            # 同步处理（保持向后兼容）
            result = await knowledge_service.add_document(
                content=content_str,
                name=title,
                doc_type=doc_type,
                metadata=metadata
            )
            
            if result.get("success"):
                return JSONResponse(status_code=201, content=result)
            else:
                raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Upload document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档（兼容接口）"""
    try:
        # 这里暂时使用原来的RAG服务方法
        result = await rag_service.delete_document(doc_id)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# SQL解析接口
@router.post("/sql/parse")
async def parse_sql(request: SQLParseRequest):
    """SQL解析接口"""
    try:
        result = sql_analyzer.parse_sql(request.sql, request.dialect)
        return result
        
    except Exception as e:
        logger.error(f"SQL parse failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sql/validate")
async def validate_sql(request: SQLParseRequest):
    """SQL语法验证接口"""
    try:
        result = sql_analyzer.validate_sql_syntax(request.sql, request.dialect)
        return result
        
    except Exception as e:
        logger.error(f"SQL validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sql/convert")
async def convert_sql_dialect(
    sql: str,
    from_dialect: str,
    to_dialect: str
):
    """SQL方言转换接口"""
    try:
        result = sql_analyzer.convert_between_dialects(sql, from_dialect, to_dialect)
        return result
        
    except Exception as e:
        logger.error(f"SQL conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 向量搜索接口（兼容）
@router.post("/vector/search")
async def search_vectors(request: VectorSearchRequest):
    """向量搜索接口"""
    try:
        result = await vector_service.search_documents(
            query=request.query,
            top_k=request.top_k
        )
        return result
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 图查询接口（兼容）
@router.post("/graph/query")
async def query_graph(request: GraphQueryRequest):
    """图数据库查询接口"""
    try:
        result = await graph_service.execute_query(
            query=request.cypher,
            parameters=request.parameters or {}
        )
        return result
        
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/nodes/{label}")
async def get_nodes_by_label(label: str, limit: int = 100):
    """根据标签获取节点"""
    try:
        query = f"MATCH (n:{label}) RETURN n LIMIT $limit"
        result = await graph_service.execute_query(query, {"limit": limit})
        return result
        
    except Exception as e:
        logger.error(f"Get nodes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/relationships/{rel_type}")
async def get_relationships_by_type(rel_type: str, limit: int = 100):
    """根据类型获取关系"""
    try:
        query = f"MATCH ()-[r:{rel_type}]-() RETURN r LIMIT $limit"
        result = await graph_service.execute_query(query, {"limit": limit})
        return result
        
    except Exception as e:
        logger.error(f"Get relationships failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 统计接口
@router.get("/stats")
async def get_knowledge_stats():
    """获取知识库统计信息"""
    try:
        result = await knowledge_service.get_statistics()
        return result
        
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/vector")
async def get_vector_stats():
    """获取向量数据库统计"""
    try:
        result = await vector_service.get_collection_stats()
        return result
        
    except Exception as e:
        logger.error(f"Get vector stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/graph")
async def get_graph_stats():
    """获取图数据库统计"""
    try:
        result = await graph_service.get_database_stats()
        return result
        
    except Exception as e:
        logger.error(f"Get graph stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 管理接口
@router.delete("/knowledge/clear")
async def clear_knowledge_base():
    """清空知识库"""
    try:
        result = await knowledge_service.clear_knowledge_base()
        return result
        
    except Exception as e:
        logger.error(f"Clear knowledge base failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 配置接口
@router.get("/config")
async def get_system_config():
    """获取系统配置"""
    try:
        return {
            "milvus_host": settings.milvus_host,
            "milvus_port": settings.milvus_port,
            "neo4j_uri": settings.neo4j_uri,
            "ollama_host": settings.ollama_host,
            "model": settings.model,
            "embedding_model": settings.embedding_model,
            "app_version": settings.app_version
        }
    except Exception as e:
        logger.error(f"Get config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 