"""
Memory Management API Routes

Provides HTTP endpoints for project memory management:
- Add, update, delete memories
- Search and retrieve memories
- Get project summaries
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

from services.memory_store import memory_store
from loguru import logger


router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


# ============================================================================
# Pydantic Models
# ============================================================================

class AddMemoryRequest(BaseModel):
    """Request model for adding a memory"""
    project_id: str = Field(..., description="Project identifier")
    memory_type: Literal["decision", "preference", "experience", "convention", "plan", "note"] = Field(
        ...,
        description="Type of memory"
    )
    title: str = Field(..., min_length=1, max_length=200, description="Short title/summary")
    content: str = Field(..., min_length=1, description="Detailed content")
    reason: Optional[str] = Field(None, description="Rationale or explanation")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score 0-1")
    related_refs: Optional[List[str]] = Field(None, description="Related ref:// handles")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "myapp",
                "memory_type": "decision",
                "title": "Use JWT for authentication",
                "content": "Decided to use JWT tokens instead of session-based auth",
                "reason": "Need stateless authentication for mobile clients",
                "tags": ["auth", "architecture"],
                "importance": 0.9,
                "related_refs": ["ref://file/src/auth/jwt.py"]
            }
        }


class UpdateMemoryRequest(BaseModel):
    """Request model for updating a memory"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    reason: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "importance": 0.9,
                "tags": ["auth", "security", "critical"]
            }
        }


class SearchMemoriesRequest(BaseModel):
    """Request model for searching memories"""
    project_id: str = Field(..., description="Project identifier")
    query: Optional[str] = Field(None, description="Search query text")
    memory_type: Optional[Literal["decision", "preference", "experience", "convention", "plan", "note"]] = None
    tags: Optional[List[str]] = None
    min_importance: float = Field(0.0, ge=0.0, le=1.0)
    limit: int = Field(20, ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "myapp",
                "query": "authentication",
                "memory_type": "decision",
                "min_importance": 0.7,
                "limit": 20
            }
        }


class SupersedeMemoryRequest(BaseModel):
    """Request model for superseding a memory"""
    old_memory_id: str = Field(..., description="ID of memory to supersede")
    new_memory_type: Literal["decision", "preference", "experience", "convention", "plan", "note"]
    new_title: str = Field(..., min_length=1, max_length=200)
    new_content: str = Field(..., min_length=1)
    new_reason: Optional[str] = None
    new_tags: Optional[List[str]] = None
    new_importance: float = Field(0.5, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "old_memory_id": "abc-123-def-456",
                "new_memory_type": "decision",
                "new_title": "Use PostgreSQL instead of MySQL",
                "new_content": "Switched to PostgreSQL for better JSON support",
                "new_reason": "Need advanced JSON querying capabilities",
                "new_importance": 0.8
            }
        }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/add")
async def add_memory(request: AddMemoryRequest) -> Dict[str, Any]:
    """
    Add a new memory to the project knowledge base.

    Save important information:
    - Design decisions and rationale
    - Team preferences and conventions
    - Problems and solutions
    - Future plans

    Returns:
        Result with memory_id if successful
    """
    try:
        result = await memory_store.add_memory(
            project_id=request.project_id,
            memory_type=request.memory_type,
            title=request.title,
            content=request.content,
            reason=request.reason,
            tags=request.tags,
            importance=request.importance,
            related_refs=request.related_refs
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to add memory"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add_memory endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_memories(request: SearchMemoriesRequest) -> Dict[str, Any]:
    """
    Search memories with various filters.

    Filter by:
    - Text query (searches title, content, reason, tags)
    - Memory type
    - Tags
    - Importance threshold

    Returns:
        List of matching memories sorted by relevance
    """
    try:
        result = await memory_store.search_memories(
            project_id=request.project_id,
            query=request.query,
            memory_type=request.memory_type,
            tags=request.tags,
            min_importance=request.min_importance,
            limit=request.limit
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to search memories"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_memories endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_id}")
async def get_memory(memory_id: str) -> Dict[str, Any]:
    """
    Get a specific memory by ID with full details and related references.

    Args:
        memory_id: Memory identifier

    Returns:
        Full memory details
    """
    try:
        result = await memory_store.get_memory(memory_id)

        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Memory not found")
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to get memory"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_memory endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{memory_id}")
async def update_memory(memory_id: str, request: UpdateMemoryRequest) -> Dict[str, Any]:
    """
    Update an existing memory.

    Args:
        memory_id: Memory identifier
        request: Fields to update (only provided fields will be updated)

    Returns:
        Result with success status
    """
    try:
        result = await memory_store.update_memory(
            memory_id=memory_id,
            title=request.title,
            content=request.content,
            reason=request.reason,
            tags=request.tags,
            importance=request.importance
        )

        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Memory not found")
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to update memory"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_memory endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """
    Delete a memory (soft delete - marks as deleted but retains data).

    Args:
        memory_id: Memory identifier

    Returns:
        Result with success status
    """
    try:
        result = await memory_store.delete_memory(memory_id)

        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Memory not found")
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete memory"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_memory endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supersede")
async def supersede_memory(request: SupersedeMemoryRequest) -> Dict[str, Any]:
    """
    Create a new memory that supersedes an old one.

    Use when a decision changes or a better solution is found.
    The old memory will be marked as superseded and linked to the new one.

    Returns:
        Result with new_memory_id and old_memory_id
    """
    try:
        result = await memory_store.supersede_memory(
            old_memory_id=request.old_memory_id,
            new_memory_data={
                "memory_type": request.new_memory_type,
                "title": request.new_title,
                "content": request.new_content,
                "reason": request.new_reason,
                "tags": request.new_tags,
                "importance": request.new_importance
            }
        )

        if not result.get("success"):
            if "not found" in result.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Old memory not found")
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to supersede memory"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in supersede_memory endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/summary")
async def get_project_summary(project_id: str) -> Dict[str, Any]:
    """
    Get a summary of all memories for a project, organized by type.

    Shows:
    - Total memory count
    - Breakdown by type
    - Top memories by importance for each type

    Args:
        project_id: Project identifier

    Returns:
        Summary with counts and top memories
    """
    try:
        result = await memory_store.get_project_summary(project_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to get project summary"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project_summary endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def memory_health() -> Dict[str, Any]:
    """
    Check memory store health status.

    Returns:
        Health status and initialization state
    """
    return {
        "service": "memory_store",
        "status": "healthy" if memory_store._initialized else "not_initialized",
        "initialized": memory_store._initialized
    }
