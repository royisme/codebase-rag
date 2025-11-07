"""Conversation orchestration built around LlamaAgents."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from llama_agents import FunctionCallingAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from .base import create_default_agent


@dataclass
class AgentSession:
    """In-memory record of a running agent session."""

    session_id: str
    project_id: str
    agent: FunctionCallingAgent
    chat_history: List[ChatMessage] = field(default_factory=list)
    tool_events: List[Dict[str, Any]] = field(default_factory=list)
    task_trace: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        """Serialize a lightweight view of the session."""

        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "metadata": self.metadata,
            "turns": len(self.chat_history) // 2,
            "tool_events": len(self.tool_events),
        }


def _to_chat_message(role: MessageRole, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)


def _extract_response_text(response: Any) -> str:
    if response is None:
        return ""

    if hasattr(response, "response") and isinstance(response.response, str):
        return response.response

    message = getattr(response, "message", None)
    if message is not None and hasattr(message, "content"):
        return message.content

    return str(response)


def _extract_tool_events(response: Any) -> List[Dict[str, Any]]:
    events = getattr(response, "tool_events", None)
    if not events:
        events = getattr(response, "tool_calls", None)

    serialized: List[Dict[str, Any]] = []
    if not events:
        return serialized

    for event in events:
        event_dict = {
            "tool": getattr(event, "tool", getattr(event, "tool_name", None)),
            "input": getattr(event, "input", getattr(event, "tool_input", None)),
            "output": getattr(event, "output", getattr(event, "tool_output", None)),
        }
        serialized.append({k: v for k, v in event_dict.items() if v is not None})

    return serialized


class AgentSessionManager:
    """Manage long-lived LlamaAgent chat sessions and tool orchestration."""

    def __init__(self, agent_factory=create_default_agent):
        self._agent_factory = agent_factory
        self._sessions: Dict[str, AgentSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        project_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        agent = self._agent_factory()
        session_id = str(uuid4())
        session = AgentSession(
            session_id=session_id,
            project_id=project_id,
            agent=agent,
            metadata=metadata or {},
        )
        async with self._lock:
            self._sessions[session_id] = session

        return session.as_dict()

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def list_sessions(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return [session.as_dict() for session in self._sessions.values()]

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        async with self._lock:
            session = self._sessions.get(session_id)

        if session is None:
            raise KeyError(f"Session '{session_id}' not found")

        return {
            "session_id": session.session_id,
            "project_id": session.project_id,
            "metadata": session.metadata,
            "chat_history": [
                {"role": msg.role.value, "content": msg.content}
                for msg in session.chat_history
            ],
            "tool_events": session.tool_events,
            "task_trace": session.task_trace,
        }

    async def process_message(
        self,
        session_id: str,
        message: str,
        *,
        auto_save_memories: bool = False,
    ) -> Dict[str, Any]:
        async with self._lock:
            session = self._sessions.get(session_id)

        if session is None:
            raise KeyError(f"Session '{session_id}' not found")

        session.chat_history.append(_to_chat_message(MessageRole.USER, message))

        conversation_payload = [
            {"role": msg.role.value, "content": msg.content}
            for msg in session.chat_history
        ]

        call_kwargs = {
            "chat_history": session.chat_history,
            "metadata": {
                "project_id": session.project_id,
                "auto_save_memories": auto_save_memories,
                "conversation": conversation_payload,
            },
        }

        if hasattr(session.agent, "achat"):
            response = await session.agent.achat(message, **call_kwargs)  # type: ignore[attr-defined]
        elif hasattr(session.agent, "chat"):
            response = session.agent.chat(message, **call_kwargs)  # type: ignore[attr-defined]
        elif hasattr(session.agent, "arun"):
            response = await session.agent.arun(message, **call_kwargs)  # type: ignore[attr-defined]
        else:
            raise AttributeError("FunctionCallingAgent does not expose a chat method")

        reply_text = _extract_response_text(response)
        session.chat_history.append(_to_chat_message(MessageRole.ASSISTANT, reply_text))

        tool_events = _extract_tool_events(response)
        session.tool_events.extend(tool_events)

        task_record = {
            "user_message": message,
            "assistant_reply": reply_text,
            "tools_used": tool_events,
        }
        session.task_trace.append(task_record)

        return {
            "session_id": session_id,
            "reply": reply_text,
            "tool_events": tool_events,
            "task": task_record,
            "chat_history": [
                {"role": msg.role.value, "content": msg.content}
                for msg in session.chat_history
            ],
        }

