"""
Git utilities for repository operations
"""
import os
import subprocess
from typing import Optional, Dict, Any
from loguru import logger
import tempfile
import shutil


class GitUtils:
    """Git operations helper"""
    
    @staticmethod
    def clone_repo(repo_url: str, target_dir: Optional[str] = None, branch: str = "main") -> Dict[str, Any]:
        """Clone a git repository"""
        try:
            if target_dir is None:
                target_dir = tempfile.mkdtemp(prefix="repo_")
            
            cmd = ["git", "clone", "--depth", "1", "-b", branch, repo_url, target_dir]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "path": target_dir,
                    "message": f"Cloned {repo_url} to {target_dir}"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_repo_id_from_path(repo_path: str) -> str:
        """Generate a repository ID from path"""
        return os.path.basename(os.path.abspath(repo_path))
    
    @staticmethod
    def get_repo_id_from_url(repo_url: str) -> str:
        """Generate a repository ID from URL"""
        repo_name = repo_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return repo_name
    
    @staticmethod
    def cleanup_temp_repo(repo_path: str):
        """Clean up temporary repository"""
        try:
            if repo_path.startswith(tempfile.gettempdir()):
                shutil.rmtree(repo_path)
                logger.info(f"Cleaned up temporary repo: {repo_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp repo: {e}")


# Global instance
git_utils = GitUtils()
