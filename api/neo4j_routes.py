"""
Based on Neo4j built-in vector index knowledge graph API routes
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import tempfile
import os

from services.neo4j_knowledge_service import neo4j_knowledge_service

router = APIRouter(prefix="/neo4j-knowledge", tags=["Neo4j Knowledge Graph"])

# request model
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
    """initialize Neo4j knowledge graph service"""
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
    """add document to knowledge graph"""
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
    """upload and add file to knowledge graph"""
    try:
        # save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # add file to knowledge graph
            result = await neo4j_knowledge_service.add_file(tmp_file_path)
            return result
        finally:
            # clean up temporary file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/directories")
async def add_directory(request: DirectoryRequest):
    """add files in directory to knowledge graph"""
    try:
        # check if directory exists
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
    """query knowledge graph"""
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
    """search similar nodes based on vector similarity"""
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
    """get graph schema information"""
    try:
        result = await neo4j_knowledge_service.get_graph_schema()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_statistics():
    """get knowledge graph statistics"""
    try:
        result = await neo4j_knowledge_service.get_statistics()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_knowledge_base():
    """clear knowledge base"""
    try:
        result = await neo4j_knowledge_service.clear_knowledge_base()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """health check"""
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