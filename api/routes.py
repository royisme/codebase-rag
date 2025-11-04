from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel
import uuid
from datetime import datetime

from services.sql_parser import sql_analyzer
from services.graph_service import graph_service
from services.neo4j_knowledge_service import Neo4jKnowledgeService
from services.universal_sql_schema_parser import parse_sql_schema_smart
from services.task_queue import task_queue
from services.code_ingestor import get_code_ingestor
from services.git_utils import git_utils
from services.ranker import ranker
from services.pack_builder import pack_builder
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

class SQLSchemaParseRequest(BaseModel):
    schema_content: Optional[str] = None
    file_path: Optional[str] = None

# Repository ingestion models
class IngestRepoRequest(BaseModel):
    """Repository ingestion request"""
    repo_url: Optional[str] = None
    local_path: Optional[str] = None
    branch: Optional[str] = "main"
    include_globs: list[str] = ["**/*.py", "**/*.ts", "**/*.tsx"]
    exclude_globs: list[str] = ["**/node_modules/**", "**/.git/**", "**/__pycache__/**"]

class IngestRepoResponse(BaseModel):
    """Repository ingestion response"""
    task_id: str
    status: str  # queued, running, done, error
    message: Optional[str] = None
    files_processed: Optional[int] = None

# Related files models
class NodeSummary(BaseModel):
    """Summary of a code node"""
    type: str  # file, symbol
    ref: str
    path: Optional[str] = None
    lang: Optional[str] = None
    score: float
    summary: str

class RelatedResponse(BaseModel):
    """Response for related files endpoint"""
    nodes: list[NodeSummary]
    query: str
    repo_id: str

# Context pack models
class ContextItem(BaseModel):
    """A single item in the context pack"""
    kind: str  # file, symbol, guideline
    title: str
    summary: str
    ref: str
    extra: Optional[dict] = None

class ContextPack(BaseModel):
    """Response for context pack endpoint"""
    items: list[ContextItem]
    budget_used: int
    budget_limit: int
    stage: str
    repo_id: str


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

@router.post("/sql/parse-schema")
async def parse_sql_schema(request: SQLSchemaParseRequest):
    """
    Parse SQL schema with smart auto-detection
    
    Automatically detects:
    - SQL dialect (Oracle, MySQL, PostgreSQL, SQL Server)  
    - Business domain classification
    - Table relationships and statistics
    """
    try:
        if not request.schema_content and not request.file_path:
            raise HTTPException(status_code=400, detail="Either schema_content or file_path must be provided")
        
        analysis = parse_sql_schema_smart(
            schema_content=request.schema_content,
            file_path=request.file_path
        )
        return analysis
    except Exception as e:
        logger.error(f"Error parsing SQL schema: {e}")
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
# Repository ingestion endpoint
@router.post("/ingest/repo", response_model=IngestRepoResponse)
async def ingest_repo(request: IngestRepoRequest):
    """
    Ingest a repository into the knowledge graph
    Scans files matching patterns and creates File/Repo nodes in Neo4j
    """
    try:
        # Validate request
        if not request.repo_url and not request.local_path:
            raise HTTPException(
                status_code=400,
                detail="Either repo_url or local_path must be provided"
            )
        
        # Generate task ID
        task_id = f"ing-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # Determine repository path and ID
        repo_path = None
        repo_id = None
        cleanup_needed = False
        
        if request.local_path:
            repo_path = request.local_path
            repo_id = git_utils.get_repo_id_from_path(repo_path)
        else:
            # Clone repository
            logger.info(f"Cloning repository: {request.repo_url}")
            clone_result = git_utils.clone_repo(
                request.repo_url,
                branch=request.branch
            )
            
            if not clone_result.get("success"):
                return IngestRepoResponse(
                    task_id=task_id,
                    status="error",
                    message=clone_result.get("error", "Failed to clone repository")
                )
            
            repo_path = clone_result["path"]
            repo_id = git_utils.get_repo_id_from_url(request.repo_url)
            cleanup_needed = True
        
        logger.info(f"Processing repository: {repo_id} at {repo_path}")
        
        # Get code ingestor
        code_ingestor = get_code_ingestor(graph_service)
        
        # Scan files
        files = code_ingestor.scan_files(
            repo_path=repo_path,
            include_globs=request.include_globs,
            exclude_globs=request.exclude_globs
        )
        
        if not files:
            message = "No files found matching the specified patterns"
            logger.warning(message)
            return IngestRepoResponse(
                task_id=task_id,
                status="done",
                message=message,
                files_processed=0
            )
        
        # Ingest files into Neo4j
        result = code_ingestor.ingest_files(
            repo_id=repo_id,
            files=files
        )
        
        # Cleanup if needed
        if cleanup_needed:
            git_utils.cleanup_temp_repo(repo_path)
        
        if result.get("success"):
            return IngestRepoResponse(
                task_id=task_id,
                status="done",
                message=f"Successfully ingested {result['files_processed']} files",
                files_processed=result["files_processed"]
            )
        else:
            return IngestRepoResponse(
                task_id=task_id,
                status="error",
                message=result.get("error", "Failed to ingest files")
            )
        
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Related files endpoint
@router.get("/graph/related", response_model=RelatedResponse)
async def get_related(
    query: str = Query(..., description="Search query"),
    repoId: str = Query(..., description="Repository ID"),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of results")
):
    """
    Find related files using fulltext search and keyword matching
    Returns file summaries with ref:// handles for MCP integration
    """
    try:
        # Perform fulltext search
        search_results = graph_service.fulltext_search(
            query_text=query,
            repo_id=repoId,
            limit=limit * 2  # Get more for ranking
        )
        
        if not search_results:
            logger.info(f"No results found for query: {query}")
            return RelatedResponse(
                nodes=[],
                query=query,
                repo_id=repoId
            )
        
        # Rank results
        ranked_files = ranker.rank_files(
            files=search_results,
            query=query,
            limit=limit
        )
        
        # Convert to NodeSummary objects
        nodes = []
        for file in ranked_files:
            summary = ranker.generate_file_summary(
                path=file["path"],
                lang=file["lang"]
            )
            
            ref = ranker.generate_ref_handle(
                path=file["path"]
            )
            
            node = NodeSummary(
                type="file",
                ref=ref,
                path=file["path"],
                lang=file["lang"],
                score=file["score"],
                summary=summary
            )
            nodes.append(node)
        
        logger.info(f"Found {len(nodes)} related files for query: {query}")
        
        return RelatedResponse(
            nodes=nodes,
            query=query,
            repo_id=repoId
        )
        
    except Exception as e:
        logger.error(f"Related query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Context pack endpoint
@router.get("/context/pack", response_model=ContextPack)
async def get_context_pack(
    repoId: str = Query(..., description="Repository ID"),
    stage: str = Query("plan", description="Stage (plan/review/implement)"),
    budget: int = Query(1500, ge=100, le=10000, description="Token budget"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords"),
    focus: Optional[str] = Query(None, description="Comma-separated focus paths")
):
    """
    Build a context pack within token budget
    Searches for relevant files and packages them with summaries and ref:// handles
    """
    try:
        # Parse keywords and focus paths
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        focus_paths = [f.strip() for f in focus.split(',')] if focus else []
        
        # Create search query from keywords
        search_query = ' '.join(keyword_list) if keyword_list else '*'
        
        # Search for relevant files
        search_results = graph_service.fulltext_search(
            query_text=search_query,
            repo_id=repoId,
            limit=50
        )
        
        if not search_results:
            logger.info(f"No files found for context pack in repo: {repoId}")
            return ContextPack(
                items=[],
                budget_used=0,
                budget_limit=budget,
                stage=stage,
                repo_id=repoId
            )
        
        # Rank files
        ranked_files = ranker.rank_files(
            files=search_results,
            query=search_query,
            limit=50
        )
        
        # Convert to node format
        nodes = []
        for file in ranked_files:
            summary = ranker.generate_file_summary(
                path=file["path"],
                lang=file["lang"]
            )
            
            ref = ranker.generate_ref_handle(
                path=file["path"]
            )
            
            nodes.append({
                "type": "file",
                "path": file["path"],
                "lang": file["lang"],
                "score": file["score"],
                "summary": summary,
                "ref": ref
            })
        
        # Build context pack within budget
        context_pack = pack_builder.build_context_pack(
            nodes=nodes,
            budget=budget,
            stage=stage,
            repo_id=repoId,
            keywords=keyword_list,
            focus_paths=focus_paths
        )
        
        logger.info(f"Built context pack with {len(context_pack['items'])} items")

        return ContextPack(**context_pack)

    except Exception as e:
        logger.error(f"Context pack generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Impact analysis endpoint
class ImpactNode(BaseModel):
    """A node in the impact analysis results"""
    type: str  # file, symbol
    path: str
    lang: Optional[str] = None
    repoId: str
    relationship: str  # CALLS, IMPORTS
    depth: int
    score: float
    ref: str
    summary: str

class ImpactResponse(BaseModel):
    """Response for impact analysis endpoint"""
    nodes: list[ImpactNode]
    file: str
    repo_id: str
    depth: int

@router.get("/graph/impact", response_model=ImpactResponse)
async def get_impact_analysis(
    repoId: str = Query(..., description="Repository ID"),
    file: str = Query(..., description="File path to analyze"),
    depth: int = Query(2, ge=1, le=5, description="Traversal depth for dependencies"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results")
):
    """
    Analyze the impact of a file by finding reverse dependencies.

    Returns files and symbols that depend on the specified file through:
    - CALLS relationships (who calls functions/methods in this file)
    - IMPORTS relationships (who imports this file)

    This is useful for:
    - Understanding the blast radius of changes
    - Finding code that needs to be updated when modifying this file
    - Identifying critical files with many dependents

    Example:
        GET /graph/impact?repoId=myproject&file=src/auth/token.py&depth=2&limit=50

        Returns files that call functions in token.py or import from it,
        up to 2 levels deep in the dependency chain.
    """
    try:
        # Perform impact analysis
        impact_results = graph_service.impact_analysis(
            repo_id=repoId,
            file_path=file,
            depth=depth,
            limit=limit
        )

        if not impact_results:
            logger.info(f"No reverse dependencies found for file: {file}")
            return ImpactResponse(
                nodes=[],
                file=file,
                repo_id=repoId,
                depth=depth
            )

        # Convert to ImpactNode objects
        nodes = []
        for result in impact_results:
            # Generate summary
            summary = ranker.generate_file_summary(
                path=result["path"],
                lang=result.get("lang", "unknown")
            )

            # Add relationship context to summary
            rel_type = result.get("relationship", "DEPENDS_ON")
            if rel_type == "CALLS":
                summary += f" (calls functions in {file.split('/')[-1]})"
            elif rel_type == "IMPORTS":
                summary += f" (imports {file.split('/')[-1]})"

            # Generate ref handle
            ref = ranker.generate_ref_handle(path=result["path"])

            node = ImpactNode(
                type=result.get("type", "file"),
                path=result["path"],
                lang=result.get("lang"),
                repoId=result["repoId"],
                relationship=result.get("relationship", "DEPENDS_ON"),
                depth=result.get("depth", 1),
                score=result.get("score", 0.5),
                ref=ref,
                summary=summary
            )
            nodes.append(node)

        logger.info(f"Found {len(nodes)} reverse dependencies for {file}")

        return ImpactResponse(
            nodes=nodes,
            file=file,
            repo_id=repoId,
            depth=depth
        )

    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
