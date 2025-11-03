"""
Pydantic models for graph API (v0.2)
"""
from typing import Optional, Literal
from pydantic import BaseModel


class NodeSummary(BaseModel):
    """Summary of a code node (file or symbol)"""
    type: Literal["file", "symbol"]     # v0.2 only has "file"
    ref: str                            # e.g. "ref://file/src/a/b.py#L1-L200"
    path: Optional[str] = None
    lang: Optional[str] = None
    score: float
    summary: str                        # 1-2 lines: file role/purpose


class RelatedResponse(BaseModel):
    """Response for /graph/related endpoint"""
    nodes: list[NodeSummary]
    query: str
    repo_id: str
