"""
Pydantic models for ingest API (v0.2)
"""
from typing import Optional, Literal
from pydantic import BaseModel


class IngestRepoRequest(BaseModel):
    """Repository ingestion request"""
    repo_url: Optional[str] = None     # remote repository URL
    local_path: Optional[str] = None   # local path
    branch: Optional[str] = "main"
    include_globs: list[str] = ["**/*.py", "**/*.ts", "**/*.tsx"]
    exclude_globs: list[str] = ["**/node_modules/**", "**/.git/**", "**/__pycache__/**", "**/dist/**", "**/build/**"]


class IngestRepoResponse(BaseModel):
    """Repository ingestion response"""
    task_id: str
    status: Literal["queued", "running", "done", "error"]
    message: Optional[str] = None
    files_processed: Optional[int] = None
