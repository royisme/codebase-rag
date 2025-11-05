"""
Code Graph Handler Functions for MCP Server v2

This module contains handlers for code graph operations:
- Ingest repository
- Find related files
- Impact analysis
- Build context pack
"""

from typing import Dict, Any
from pathlib import Path
from loguru import logger


async def handle_code_graph_ingest_repo(args: Dict, get_code_ingestor, git_utils) -> Dict:
    """
    Ingest repository into code graph.

    Supports both full and incremental ingestion modes.

    Args:
        args: Arguments containing local_path, repo_url, mode
        get_code_ingestor: Function to get code ingestor instance
        git_utils: Git utilities instance

    Returns:
        Ingestion result with statistics
    """
    try:
        local_path = args["local_path"]
        repo_url = args.get("repo_url")
        mode = args.get("mode", "incremental")

        # Get repo_id from URL or path
        if repo_url:
            repo_id = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        else:
            repo_id = Path(local_path).name

        # Check if it's a git repo
        is_git = git_utils.is_git_repo(local_path)

        ingestor = get_code_ingestor()

        if mode == "incremental" and is_git:
            # Incremental mode
            result = await ingestor.ingest_repo_incremental(
                local_path=local_path,
                repo_url=repo_url or f"file://{local_path}",
                repo_id=repo_id
            )
        else:
            # Full mode
            result = await ingestor.ingest_repo(
                local_path=local_path,
                repo_url=repo_url or f"file://{local_path}"
            )

        logger.info(f"Ingest repo: {repo_id} (mode: {mode})")
        return result

    except Exception as e:
        logger.error(f"Code graph ingest failed: {e}")
        return {"success": False, "error": str(e)}


async def handle_code_graph_related(args: Dict, graph_service, ranker) -> Dict:
    """
    Find files related to a query.

    Uses fulltext search and ranking to find relevant files.

    Args:
        args: Arguments containing query, repo_id, limit
        graph_service: Graph service instance
        ranker: Ranking service instance

    Returns:
        Ranked list of related files with ref:// handles
    """
    try:
        query = args["query"]
        repo_id = args["repo_id"]
        limit = args.get("limit", 30)

        # Search files
        search_result = await graph_service.fulltext_search(
            query=query,
            repo_id=repo_id,
            limit=limit
        )

        if not search_result.get("success"):
            return search_result

        nodes = search_result.get("nodes", [])

        # Rank files
        if nodes:
            ranked = ranker.rank_files(nodes)
            result = {
                "success": True,
                "nodes": ranked,
                "total_count": len(ranked)
            }
        else:
            result = {
                "success": True,
                "nodes": [],
                "total_count": 0
            }

        logger.info(f"Related files: {query} ({len(result['nodes'])} found)")
        return result

    except Exception as e:
        logger.error(f"Code graph related failed: {e}")
        return {"success": False, "error": str(e)}


async def handle_code_graph_impact(args: Dict, graph_service) -> Dict:
    """
    Analyze impact of file changes.

    Finds all files that depend on the given file (reverse dependencies).

    Args:
        args: Arguments containing repo_id, file_path, depth
        graph_service: Graph service instance

    Returns:
        Impact analysis with dependent files
    """
    try:
        result = await graph_service.impact_analysis(
            repo_id=args["repo_id"],
            file_path=args["file_path"],
            depth=args.get("depth", 2)
        )
        logger.info(f"Impact analysis: {args['file_path']}")
        return result
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        return {"success": False, "error": str(e)}


async def handle_context_pack(args: Dict, pack_builder) -> Dict:
    """
    Build context pack for AI agents.

    Creates a curated list of files/symbols within token budget.

    Args:
        args: Arguments containing repo_id, stage, budget, keywords, focus
        pack_builder: Context pack builder instance

    Returns:
        Context pack with curated items and ref:// handles
    """
    try:
        result = await pack_builder.build_context_pack(
            repo_id=args["repo_id"],
            stage=args.get("stage", "implement"),
            budget=args.get("budget", 1500),
            keywords=args.get("keywords"),
            focus=args.get("focus")
        )
        logger.info(f"Context pack: {args['repo_id']} (budget: {args.get('budget', 1500)})")
        return result
    except Exception as e:
        logger.error(f"Context pack failed: {e}")
        return {"success": False, "error": str(e)}
