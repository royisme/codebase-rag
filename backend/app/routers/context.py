"""
Context API router (v0.2)
GET /context/pack - Build context pack
"""
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from typing import Optional

from backend.app.models.context_models import ContextPack
from backend.app.services.graph.neo4j_service import get_neo4j_service
from backend.app.services.ranking.ranker import Ranker
from backend.app.services.context.pack_builder import get_pack_builder


router = APIRouter(prefix="/context", tags=["Context"])


@router.get("/pack", response_model=ContextPack)
async def get_context_pack(
    repoId: str = Query(..., description="Repository ID"),
    stage: str = Query("plan", description="Stage (plan/review/implement)"),
    budget: int = Query(1500, ge=100, le=10000, description="Token budget"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords"),
    focus: Optional[str] = Query(None, description="Comma-separated focus paths")
):
    """
    Build a context pack for the given stage and budget
    
    v0.2: Uses /graph/related results
    - Searches for relevant files using keywords
    - Builds context pack within token budget
    - Returns items with ref:// handles for MCP
    """
    try:
        neo4j_service = get_neo4j_service()
        pack_builder = get_pack_builder()
        
        # Parse keywords and focus paths
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        focus_paths = [f.strip() for f in focus.split(',')] if focus else []
        
        # Create search query from keywords
        search_query = ' '.join(keyword_list) if keyword_list else '*'
        
        # Search for relevant files
        search_results = neo4j_service.fulltext_search(
            query_text=search_query,
            repo_id=repoId,
            limit=50  # Get more candidates
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
        ranked_files = Ranker.rank_files(
            files=search_results,
            query=search_query,
            limit=50
        )
        
        # Convert to node format
        nodes = []
        for file in ranked_files:
            summary = Ranker.generate_file_summary(
                path=file["path"],
                lang=file["lang"]
            )
            
            ref = Ranker.generate_ref_handle(
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
