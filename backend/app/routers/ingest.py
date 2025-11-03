"""
Ingest API router (v0.2)
POST /ingest/repo - Ingest a repository
"""
from fastapi import APIRouter, HTTPException
from loguru import logger
import uuid
from datetime import datetime

from backend.app.models.ingest_models import IngestRepoRequest, IngestRepoResponse
from backend.app.services.graph.neo4j_service import get_neo4j_service
from backend.app.services.ingest.code_ingestor import get_code_ingestor
from backend.app.services.ingest.git_utils import GitUtils


router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.post("/repo", response_model=IngestRepoResponse)
async def ingest_repo(request: IngestRepoRequest):
    """
    Ingest a repository into the knowledge graph
    
    v0.2: Synchronous file scanning and ingestion
    - Scans files matching include_globs
    - Excludes files matching exclude_globs
    - Creates Repo and File nodes in Neo4j
    - Returns task_id for future async tracking
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
            repo_id = GitUtils.get_repo_id_from_path(repo_path)
        else:
            # Clone repository
            logger.info(f"Cloning repository: {request.repo_url}")
            clone_result = GitUtils.clone_repo(
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
            repo_id = GitUtils.get_repo_id_from_url(request.repo_url)
            cleanup_needed = True
        
        logger.info(f"Processing repository: {repo_id} at {repo_path}")
        
        # Get Neo4j service and code ingestor
        neo4j_service = get_neo4j_service()
        code_ingestor = get_code_ingestor(neo4j_service)
        
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
            GitUtils.cleanup_temp_repo(repo_path)
        
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
