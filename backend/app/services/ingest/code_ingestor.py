"""
Code ingestor service for scanning and ingesting code files (v0.2)
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
import hashlib
import fnmatch


class CodeIngestor:
    """Code file scanner and ingestor"""
    
    # Language detection based on file extension
    LANG_MAP = {
        '.py': 'python',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
    }
    
    def __init__(self, neo4j_service):
        """Initialize code ingestor"""
        self.neo4j_service = neo4j_service
    
    def scan_files(
        self,
        repo_path: str,
        include_globs: List[str],
        exclude_globs: List[str]
    ) -> List[Dict[str, Any]]:
        """Scan files in repository matching patterns"""
        files = []
        repo_path = os.path.abspath(repo_path)
        
        for root, dirs, filenames in os.walk(repo_path):
            # Filter out excluded directories
            dirs[:] = [
                d for d in dirs
                if not self._should_exclude(os.path.join(root, d), repo_path, exclude_globs)
            ]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, repo_path)
                
                # Check if file matches include patterns and not excluded
                if self._should_include(rel_path, include_globs) and \
                   not self._should_exclude(file_path, repo_path, exclude_globs):
                    
                    try:
                        file_info = self._get_file_info(file_path, rel_path)
                        files.append(file_info)
                    except Exception as e:
                        logger.warning(f"Failed to process {rel_path}: {e}")
        
        logger.info(f"Scanned {len(files)} files in {repo_path}")
        return files
    
    def _should_include(self, rel_path: str, include_globs: List[str]) -> bool:
        """Check if file matches include patterns"""
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in include_globs)
    
    def _should_exclude(self, file_path: str, repo_path: str, exclude_globs: List[str]) -> bool:
        """Check if file/directory matches exclude patterns"""
        rel_path = os.path.relpath(file_path, repo_path)
        return any(fnmatch.fnmatch(rel_path, pattern.strip('*')) or 
                  fnmatch.fnmatch(rel_path + '/', pattern) for pattern in exclude_globs)
    
    def _get_file_info(self, file_path: str, rel_path: str) -> Dict[str, Any]:
        """Get file information"""
        ext = Path(file_path).suffix.lower()
        lang = self.LANG_MAP.get(ext, 'unknown')
        
        # Get file size
        size = os.path.getsize(file_path)
        
        # Read content for small files (v0.2: for fulltext search)
        content = None
        if size < 100_000:  # Only read files < 100KB
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Could not read {rel_path}: {e}")
        
        # Calculate SHA hash
        sha = None
        try:
            with open(file_path, 'rb') as f:
                sha = hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Could not hash {rel_path}: {e}")
        
        return {
            "path": rel_path,
            "lang": lang,
            "size": size,
            "content": content,
            "sha": sha
        }
    
    def ingest_files(
        self,
        repo_id: str,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Ingest files into Neo4j"""
        try:
            # Create repository node
            self.neo4j_service.create_repo(repo_id, {
                "created": "datetime()",
                "file_count": len(files)
            })
            
            # Create file nodes
            success_count = 0
            for file_info in files:
                result = self.neo4j_service.create_file(
                    repo_id=repo_id,
                    path=file_info["path"],
                    lang=file_info["lang"],
                    size=file_info["size"],
                    content=file_info.get("content"),
                    sha=file_info.get("sha")
                )
                
                if result.get("success"):
                    success_count += 1
            
            logger.info(f"Ingested {success_count}/{len(files)} files for repo {repo_id}")
            
            return {
                "success": True,
                "files_processed": success_count,
                "total_files": len(files)
            }
        except Exception as e:
            logger.error(f"Failed to ingest files: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_code_ingestor(neo4j_service):
    """Factory function to create CodeIngestor"""
    return CodeIngestor(neo4j_service)
