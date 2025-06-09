from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from services.sql_parser import sql_analyzer
from services.graph_service import graph_service
from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.task_queue import task_queue
from config import settings
from loguru import logger

# create router
router = APIRouter()

# initialize Neo4j knowledge service
knowledge_service = Neo4jKnowledgeService()

# request models
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

class DocumentAddRequest(BaseModel):
    content: str
    title: str = "Untitled"
    metadata: Optional[Dict[str, Any]] = None

class DirectoryProcessRequest(BaseModel):
    directory_path: str
    recursive: bool = True
    file_patterns: Optional[List[str]] = None

class QueryRequest(BaseModel):
    question: str
    mode: str = "hybrid"  # hybrid, graph_only, vector_only

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

# health check
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """health check interface"""
    try:
        # check Neo4j knowledge service status
        neo4j_connected = knowledge_service._initialized if hasattr(knowledge_service, '_initialized') else False
        
        services_status = {
            "neo4j_knowledge_service": neo4j_connected,
            "graph_service": graph_service._connected if hasattr(graph_service, '_connected') else False,
            "task_queue": True  # task queue is always available
        }
        
        overall_status = "healthy" if services_status["neo4j_knowledge_service"] else "degraded"
        
        return HealthResponse(
            status=overall_status,
            services=services_status,
            version=settings.app_version
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# knowledge query interface
@router.post("/knowledge/query")
async def query_knowledge(query_request: QueryRequest):
    """Query knowledge base using Neo4j GraphRAG"""
    try:
        result = await knowledge_service.query(
            question=query_request.question,
            mode=query_request.mode
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# knowledge search interface
@router.post("/knowledge/search")
async def search_knowledge(search_request: SearchRequest):
    """Search similar nodes in knowledge base"""
    try:
        result = await knowledge_service.search_similar_nodes(
            query=search_request.query,
            top_k=search_request.top_k
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# document management
@router.post("/documents")
async def add_document(request: DocumentAddRequest):
    """Add document to knowledge base"""
    try:
        result = await knowledge_service.add_document(
            content=request.content,
            title=request.title,
            metadata=request.metadata
        )
        
        if result.get("success"):
            return JSONResponse(status_code=201, content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/file")
async def add_file(file_path: str):
    """Add file to knowledge base"""
    try:
        result = await knowledge_service.add_file(file_path)
        
        if result.get("success"):
            return JSONResponse(status_code=201, content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/directory")
async def add_directory(request: DirectoryProcessRequest):
    """Add directory to knowledge base"""
    try:
        result = await knowledge_service.add_directory(
            directory_path=request.directory_path,
            recursive=request.recursive,
            file_extensions=request.file_patterns
        )
        
        if result.get("success"):
            return JSONResponse(status_code=201, content=result)
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Add directory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# SQL parsing
@router.post("/sql/parse")
async def parse_sql(request: SQLParseRequest):
    """Parse SQL statement"""
    try:
        result = sql_analyzer.parse_sql(request.sql, request.dialect)
        return result.dict()
        
    except Exception as e:
        logger.error(f"SQL parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sql/validate")
async def validate_sql(request: SQLParseRequest):
    """Validate SQL syntax"""
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
    """Convert SQL between dialects"""
    try:
        result = sql_analyzer.convert_between_dialects(sql, from_dialect, to_dialect)
        return result
        
    except Exception as e:
        logger.error(f"SQL conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# system information
@router.get("/schema")
async def get_graph_schema():
    """Get knowledge graph schema"""
    try:
        result = await knowledge_service.get_graph_schema()
        return result
        
    except Exception as e:
        logger.error(f"Get schema failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_statistics():
    """Get knowledge base statistics"""
    try:
        result = await knowledge_service.get_statistics()
        return result
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_knowledge_base():
    """Clear knowledge base"""
    try:
        result = await knowledge_service.clear_knowledge_base()
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Clear knowledge base failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_system_config():
    """Get system configuration"""
    try:
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "monitoring_enabled": settings.enable_monitoring
        }
        
    except Exception as e:
        logger.error(f"Get config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 