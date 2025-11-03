"""
Pydantic models for context pack API (v0.2)
"""
from typing import Optional, Literal
from pydantic import BaseModel


class ContextItem(BaseModel):
    """A single item in the context pack"""
    kind: Literal["file", "symbol", "guideline"]
    title: str
    summary: str
    ref: str
    extra: Optional[dict] = None


class ContextPack(BaseModel):
    """Response for /context/pack endpoint"""
    items: list[ContextItem]
    budget_used: int
    budget_limit: int
    stage: str
    repo_id: str
