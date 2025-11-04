"""
Ranking service for search results
Simple keyword and path matching for file relevance
"""
from typing import List, Dict, Any
import re


class Ranker:
    """Search result ranker"""
    
    @staticmethod
    def rank_files(
        files: List[Dict[str, Any]],
        query: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Rank files by relevance to query using keyword matching"""
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))
        
        scored_files = []
        for file in files:
            path = file.get("path", "").lower()
            lang = file.get("lang", "").lower()
            base_score = file.get("score", 1.0)
            
            # Calculate relevance score
            score = base_score
            
            # Exact path match
            if query_lower in path:
                score *= 2.0
            
            # Term matching in path
            path_terms = set(re.findall(r'\w+', path))
            matching_terms = query_terms & path_terms
            if matching_terms:
                score *= (1.0 + len(matching_terms) * 0.3)
            
            # Language match
            if query_lower in lang:
                score *= 1.5
            
            # Prefer files in src/, lib/, core/ directories
            if any(prefix in path for prefix in ['src/', 'lib/', 'core/', 'app/']):
                score *= 1.2
            
            # Penalize test files (unless looking for tests)
            if 'test' not in query_lower and ('test' in path or 'spec' in path):
                score *= 0.5
            
            scored_files.append({
                **file,
                "score": score
            })
        
        # Sort by score descending
        scored_files.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return scored_files[:limit]
    
    @staticmethod
    def generate_file_summary(path: str, lang: str) -> str:
        """Generate rule-based summary for a file"""
        parts = path.split('/')
        
        if len(parts) > 1:
            parent_dir = parts[-2]
            filename = parts[-1]
            return f"{lang.capitalize()} file {filename} in {parent_dir}/ directory"
        else:
            return f"{lang.capitalize()} file {path}"
    
    @staticmethod
    def generate_ref_handle(path: str, start_line: int = 1, end_line: int = 1000) -> str:
        """Generate ref:// handle for a file"""
        return f"ref://file/{path}#L{start_line}-L{end_line}"


# Global instance
ranker = Ranker()
