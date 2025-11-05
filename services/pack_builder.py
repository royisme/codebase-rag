"""
Context pack builder for generating context bundles within token budgets
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class PackBuilder:
    """Context pack builder with deduplication and category limits"""

    # Category limits (configurable via v0.4 spec)
    DEFAULT_FILE_LIMIT = 8
    DEFAULT_SYMBOL_LIMIT = 12

    @staticmethod
    def build_context_pack(
        nodes: List[Dict[str, Any]],
        budget: int,
        stage: str,
        repo_id: str,
        keywords: Optional[List[str]] = None,
        focus_paths: Optional[List[str]] = None,
        file_limit: int = DEFAULT_FILE_LIMIT,
        symbol_limit: int = DEFAULT_SYMBOL_LIMIT,
        enable_deduplication: bool = True
    ) -> Dict[str, Any]:
        """
        Build a context pack from nodes within budget with deduplication and category limits.

        Args:
            nodes: List of node dictionaries with path, lang, score, etc.
            budget: Token budget (estimated as ~4 chars per token)
            stage: Stage name (plan/review/etc)
            repo_id: Repository ID
            keywords: Optional keywords for filtering
            focus_paths: Optional list of paths to prioritize
            file_limit: Maximum number of file items (default: 8)
            symbol_limit: Maximum number of symbol items (default: 12)
            enable_deduplication: Remove duplicate refs (default: True)

        Returns:
            Dict with items, budget_used, budget_limit, stage, repo_id
        """
        # Step 1: Deduplicate nodes if enabled
        if enable_deduplication:
            nodes = PackBuilder._deduplicate_nodes(nodes)
            logger.debug(f"After deduplication: {len(nodes)} unique nodes")

        # Step 2: Sort nodes by score
        sorted_nodes = sorted(
            nodes,
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        # Step 3: Prioritize focus paths if provided
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

        # Step 4: Apply category limits and budget constraints
        items = []
        budget_used = 0
        chars_per_token = 4
        file_count = 0
        symbol_count = 0

        for node in sorted_nodes:
            node_type = node.get("type", "file")

            # Check category limits
            if node_type == "file" and file_count >= file_limit:
                logger.debug(f"File limit reached ({file_limit}), skipping file nodes")
                continue
            elif node_type == "symbol" and symbol_count >= symbol_limit:
                logger.debug(f"Symbol limit reached ({symbol_limit}), skipping symbol nodes")
                continue
            elif node_type not in ["file", "symbol", "guideline"]:
                # Unknown type, count as file
                if file_count >= file_limit:
                    continue

            # Create context item
            item = {
                "kind": node_type,
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

            # Add item and update counters
            items.append(item)
            budget_used += estimated_tokens

            if node_type == "file":
                file_count += 1
            elif node_type == "symbol":
                symbol_count += 1

        logger.info(
            f"Built context pack: {len(items)} items "
            f"({file_count} files, {symbol_count} symbols), "
            f"{budget_used}/{budget} tokens"
        )

        return {
            "items": items,
            "budget_used": budget_used,
            "budget_limit": budget,
            "stage": stage,
            "repo_id": repo_id,
            "category_counts": {
                "file": file_count,
                "symbol": symbol_count
            }
        }

    @staticmethod
    def _deduplicate_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate nodes based on ref handle.
        If multiple nodes have the same ref, keep the one with highest score.
        """
        seen_refs = {}

        for node in nodes:
            ref = node.get("ref")
            if not ref:
                # No ref, keep it (shouldn't happen normally)
                continue

            # Check if we've seen this ref before
            if ref in seen_refs:
                # Keep the one with higher score
                existing_score = seen_refs[ref].get("score", 0)
                current_score = node.get("score", 0)
                if current_score > existing_score:
                    seen_refs[ref] = node
            else:
                seen_refs[ref] = node

        # Return deduplicated nodes
        deduplicated = list(seen_refs.values())
        removed_count = len(nodes) - len(deduplicated)

        if removed_count > 0:
            logger.debug(f"Removed {removed_count} duplicate nodes")

        return deduplicated
    
    @staticmethod
    def _extract_title(path: str) -> str:
        """Extract title from path (last 2 segments)"""
        parts = path.split('/')
        if len(parts) >= 2:
            return '/'.join(parts[-2:])
        return path


# Global instance
pack_builder = PackBuilder()
