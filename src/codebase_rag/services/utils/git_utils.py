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

    @staticmethod
    def is_git_repo(repo_path: str) -> bool:
        """Check if directory is a git repository"""
        try:
            git_dir = os.path.join(repo_path, '.git')
            return os.path.isdir(git_dir)
        except Exception:
            return False

    @staticmethod
    def get_last_commit_hash(repo_path: str) -> Optional[str]:
        """Get the hash of the last commit"""
        try:
            if not GitUtils.is_git_repo(repo_path):
                return None

            cmd = ["git", "-C", repo_path, "rev-parse", "HEAD"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"Failed to get last commit hash: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Failed to get last commit hash: {e}")
            return None

    @staticmethod
    def get_changed_files(
        repo_path: str,
        since_commit: Optional[str] = None,
        include_untracked: bool = True
    ) -> Dict[str, Any]:
        """
        Get list of changed files in a git repository.

        Args:
            repo_path: Path to git repository
            since_commit: Compare against this commit (default: HEAD~1)
            include_untracked: Include untracked files

        Returns:
            Dict with success status and list of changed files with their status
        """
        try:
            if not GitUtils.is_git_repo(repo_path):
                return {
                    "success": False,
                    "error": f"Not a git repository: {repo_path}"
                }

            changed_files = []

            # Get modified/added/deleted files
            if since_commit:
                # Compare against specific commit
                cmd = ["git", "-C", repo_path, "diff", "--name-status", since_commit, "HEAD"]
            else:
                # Compare against working directory changes
                cmd = ["git", "-C", repo_path, "diff", "--name-status", "HEAD"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue

                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        status, file_path = parts
                        changed_files.append({
                            "path": file_path,
                            "status": status,  # A=added, M=modified, D=deleted
                            "action": GitUtils._get_action_from_status(status)
                        })

            # Get untracked files if requested
            if include_untracked:
                cmd = ["git", "-C", repo_path, "ls-files", "--others", "--exclude-standard"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            changed_files.append({
                                "path": line.strip(),
                                "status": "?",
                                "action": "untracked"
                            })

            # Get staged but uncommitted files
            cmd = ["git", "-C", repo_path, "diff", "--name-status", "--cached"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue

                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        status, file_path = parts
                        # Check if already in list
                        if not any(f['path'] == file_path for f in changed_files):
                            changed_files.append({
                                "path": file_path,
                                "status": status,
                                "action": f"staged_{GitUtils._get_action_from_status(status)}"
                            })

            logger.info(f"Found {len(changed_files)} changed files in {repo_path}")

            return {
                "success": True,
                "changed_files": changed_files,
                "count": len(changed_files)
            }

        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return {
                "success": False,
                "error": str(e),
                "changed_files": []
            }

    @staticmethod
    def _get_action_from_status(status: str) -> str:
        """Convert git status code to action name"""
        status_map = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied',
            'U': 'unmerged',
            '?': 'untracked'
        }
        return status_map.get(status, 'unknown')

    @staticmethod
    def get_file_last_modified_commit(repo_path: str, file_path: str) -> Optional[str]:
        """Get the hash of the last commit that modified a specific file"""
        try:
            if not GitUtils.is_git_repo(repo_path):
                return None

            cmd = ["git", "-C", repo_path, "log", "-1", "--format=%H", "--", file_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get file last modified commit: {e}")
            return None


# Global instance
git_utils = GitUtils()
