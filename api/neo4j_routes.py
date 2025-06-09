"""
基于 Neo4j 内置向量索引的知识图谱 API 路由
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import tempfile
import os
from pathlib import Path

from services.neo4j_knowledge_service import neo4j_knowledge_service

router = APIRouter(prefix="/neo4j-knowledge", tags=["Neo4j Knowledge Graph"])

# 请求模型
class DocumentRequest(BaseModel):
    content: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class QueryRequest(BaseModel):
    question: str
    mode: str = "hybrid"  # hybrid, graph_only, vector_only

class DirectoryRequest(BaseModel):
    directory_path: str
    recursive: bool = True
    file_extensions: Optional[List[str]] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

@router.post("/initialize")
async def initialize_service():
    """初始化 Neo4j 知识图谱服务"""
    try:
        success = await neo4j_knowledge_service.initialize()
        if success:
            return {"success": True, "message": "Neo4j Knowledge Service initialized"}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize service")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents")
async def add_document(request: DocumentRequest):
    """添加文档到知识图谱"""
    try:
        result = await neo4j_knowledge_service.add_document(
            content=request.content,
            title=request.title,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files")
async def add_file(file: UploadFile = File(...)):
    """上传并添加文件到知识图谱"""
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # 添加文件到知识图谱
            result = await neo4j_knowledge_service.add_file(tmp_file_path)
            return result
        finally:
            # 清理临时文件
            os.unlink(tmp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/directories")
async def add_directory(request: DirectoryRequest):
    """批量添加目录中的文件到知识图谱"""
    try:
        # 验证目录是否存在
        if not os.path.exists(request.directory_path):
            raise HTTPException(status_code=404, detail="Directory not found")
        
        result = await neo4j_knowledge_service.add_directory(
            directory_path=request.directory_path,
            recursive=request.recursive,
            file_extensions=request.file_extensions
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_knowledge_graph(request: QueryRequest):
    """查询知识图谱"""
    try:
        result = await neo4j_knowledge_service.query(
            question=request.question,
            mode=request.mode
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_similar_nodes(request: SearchRequest):
    """基于向量相似度搜索节点"""
    try:
        result = await neo4j_knowledge_service.search_similar_nodes(
            query=request.query,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema")
async def get_graph_schema():
    """获取图谱结构信息"""
    try:
        result = await neo4j_knowledge_service.get_graph_schema()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_statistics():
    """获取知识图谱统计信息"""
    try:
        result = await neo4j_knowledge_service.get_statistics()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_knowledge_base():
    """清空知识库"""
    try:
        result = await neo4j_knowledge_service.clear_knowledge_base()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        if neo4j_knowledge_service._initialized:
            return {
                "status": "healthy",
                "service": "Neo4j Knowledge Graph",
                "initialized": True
            }
        else:
            return {
                "status": "not_initialized",
                "service": "Neo4j Knowledge Graph",
                "initialized": False
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 