"""
Context pack builder for generating context bundles within token budgets
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class PackBuilder:
    """Context pack builder"""
    
    @staticmethod
    def build_context_pack(
        nodes: List[Dict[str, Any]],
        budget: int,
        stage: str,
        repo_id: str,
        keywords: Optional[List[str]] = None,
        focus_paths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a context pack from nodes within budget
        
        Args:
            nodes: List of node dictionaries with path, lang, score, etc.
            budget: Token budget (estimated as ~4 chars per token)
            stage: Stage name (plan/review/etc)
            repo_id: Repository ID
            keywords: Optional keywords for filtering
            focus_paths: Optional list of paths to prioritize
        
        Returns:
            Dict with items, budget_used, budget_limit, stage, repo_id
        """
        items = []
        budget_used = 0
        chars_per_token = 4
        
        # Sort nodes by score if available
        sorted_nodes = sorted(
            nodes,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        # Prioritize focus paths if provided
        if focus_paths:
            focus_nodes = [
                n for n in sorted_nodes
                if any(fp in n.get("path", "") for fp in focus_paths)
            ]
            other_nodes = [
                n for n in sorted_nodes
                if n not in focus_nodes
            ]
            sorted_nodes = focus_nodes + other_nodes
        
        for node in sorted_nodes:
            # Create context item
            item = {
                "kind": node.get("type", "file"),
                "title": PackBuilder._extract_title(node.get("path", "")),
                "summary": node.get("summary", ""),
                "ref": node.get("ref", ""),
                "extra": {
                    "lang": node.get("lang"),
                    "score": node.get("score", 0)
                }
            }
            
            # Estimate size (title + summary + ref + overhead)
            item_size = len(item["title"]) + len(item["summary"]) + len(item["ref"]) + 50
            estimated_tokens = item_size // chars_per_token
            
            # Check if adding this item would exceed budget
            if budget_used + estimated_tokens > budget:
                logger.debug(f"Budget limit reached: {budget_used}/{budget} tokens")
                break
            
            items.append(item)
            budget_used += estimated_tokens
        
        logger.info(f"Built context pack with {len(items)} items, {budget_used}/{budget} tokens")
        
        return {
            "items": items,
            "budget_used": budget_used,
            "budget_limit": budget,
            "stage": stage,
            "repo_id": repo_id
        }
    
    @staticmethod
    def _extract_title(path: str) -> str:
        """Extract title from path (last 2 segments)"""
        parts = path.split('/')
        if len(parts) >= 2:
            return '/'.join(parts[-2:])
        return path


# Global instance
pack_builder = PackBuilder()
