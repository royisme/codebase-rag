"""
Graph API router (v0.2)
GET /graph/related - Find related files
"""
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from typing import Optional

from backend.app.models.graph_models import RelatedResponse, NodeSummary
from backend.app.services.graph.neo4j_service import get_neo4j_service
from backend.app.services.ranking.ranker import Ranker


router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/related", response_model=RelatedResponse)
async def get_related(
    query: str = Query(..., description="Search query"),
    repoId: str = Query(..., description="Repository ID"),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of results")
):
    """
    Find related files in the knowledge graph
    
    v0.2: Fulltext search + keyword matching
    - Searches files using Neo4j fulltext index
    - Ranks results by relevance
    - Returns file summaries with ref:// handles
    """
    try:
        neo4j_service = get_neo4j_service()
        
        # Perform fulltext search
        search_results = neo4j_service.fulltext_search(
            query_text=query,
            repo_id=repoId,
            limit=limit * 2  # Get more results for ranking
        )
        
        if not search_results:
            logger.info(f"No results found for query: {query}")
            return RelatedResponse(
                nodes=[],
                query=query,
                repo_id=repoId
            )
        
        # Rank results
        ranked_files = Ranker.rank_files(
            files=search_results,
            query=query,
            limit=limit
        )
        
        # Convert to NodeSummary objects
        nodes = []
        for file in ranked_files:
            # Generate summary and ref handle
            summary = Ranker.generate_file_summary(
                path=file["path"],
                lang=file["lang"]
            )
            
            ref = Ranker.generate_ref_handle(
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
