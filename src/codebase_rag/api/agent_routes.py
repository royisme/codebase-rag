"""FastAPI routes exposing the unified LlamaIndex agent workflow."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from codebase_rag.services.agents import agent_session_manager


router = APIRouter(prefix="/agent", tags=["Agent Orchestration"])


class SessionSummary(BaseModel):
    session_id: str
    project_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    turns: int = 0
    tool_events: int = 0


class CreateSessionRequest(BaseModel):
    project_id: str = Field(..., description="Project identifier used for retrieval and memory scoping.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata stored alongside the session.")


class CreateSessionResponse(SessionSummary):
    pass


class AgentMessageRequest(BaseModel):
    message: str = Field(..., description="User message to send to the orchestrator agent.")
    auto_save_memories: bool = Field(
        default=False,
        description="If True, the memory extraction tool will persist high-confidence memories automatically.",
    )


class AgentMessageResponse(BaseModel):
    session_id: str
    reply: str
    tool_events: List[Dict[str, Any]] = Field(default_factory=list)
    task: Dict[str, Any] = Field(default_factory=dict)
    chat_history: List[Dict[str, str]] = Field(default_factory=list)


class SessionStateResponse(BaseModel):
    session_id: str
    project_id: str
    metadata: Dict[str, Any]
    chat_history: List[Dict[str, str]]
    tool_events: List[Dict[str, Any]]
    task_trace: List[Dict[str, Any]]


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_agent_session(payload: CreateSessionRequest) -> Dict[str, Any]:
    """Create a new agent session scoped to the provided project."""

    return await agent_session_manager.create_session(
        project_id=payload.project_id,
        metadata=payload.metadata,
    )


@router.get("/sessions", response_model=Dict[str, List[SessionSummary]])
async def list_agent_sessions() -> Dict[str, List[SessionSummary]]:
    """List all active agent sessions."""

    sessions = await agent_session_manager.list_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}", response_model=SessionStateResponse)
async def get_agent_session(session_id: str = Path(..., description="Session identifier")) -> Dict[str, Any]:
    """Fetch detailed state for a specific session."""

    try:
        return await agent_session_manager.get_session_state(session_id)
    except KeyError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}")
async def close_agent_session(session_id: str = Path(..., description="Session identifier")) -> Dict[str, str]:
    """Terminate an existing agent session."""

    await agent_session_manager.close_session(session_id)
    return {"status": "closed", "session_id": session_id}


@router.post("/sessions/{session_id}/messages", response_model=AgentMessageResponse)
async def send_agent_message(
    payload: AgentMessageRequest,
    session_id: str = Path(..., description="Session identifier"),
) -> Dict[str, Any]:
    """Send a message to the orchestrator agent and obtain the response."""

    try:
        return await agent_session_manager.process_message(
            session_id=session_id,
            message=payload.message,
            auto_save_memories=payload.auto_save_memories,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AttributeError as exc:  # pragma: no cover - unexpected agent shape
        raise HTTPException(status_code=500, detail=str(exc)) from exc

