"""Conversation orchestration built around LlamaIndex workflow agents."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from llama_index.core.agent import AgentOutput, ToolCall, ToolCallResult
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from .base import create_default_agent


@dataclass
class AgentSession:
    """In-memory record of a running agent session."""

    session_id: str
    project_id: str
    agent: FunctionAgent
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


def _serialize_chat_history(chat_history: List[ChatMessage]) -> List[Dict[str, str]]:
    return [
        {
            "role": getattr(msg.role, "value", msg.role),
            "content": msg.content,
        }
        for msg in chat_history
    ]


def _extract_response_text(response: Any) -> str:
    if response is None:
        return ""

    if isinstance(response, AgentOutput):
        return response.response.content or ""

    message = getattr(response, "message", None)
    if message is not None and hasattr(message, "content"):
        return message.content

    reply = getattr(response, "response", None)
    if reply is not None and hasattr(reply, "content"):
        return reply.content

    if hasattr(response, "response") and isinstance(response.response, str):
        return response.response

    return str(response)


async def _collect_tool_activity(handler: Any) -> List[Dict[str, Any]]:
    """Capture tool call activity emitted by the workflow handler."""

    collected: List[Dict[str, Any]] = []
    call_index: Dict[str, int] = {}

    if not hasattr(handler, "stream_events"):
        return collected

    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            call_index[event.tool_id] = len(collected)
            collected.append(
                {
                    "tool": event.tool_name,
                    "input": event.tool_kwargs,
                }
            )
        elif isinstance(event, ToolCallResult):
            payload = {
                "tool": event.tool_name,
                "input": event.tool_kwargs,
                "output": getattr(event.tool_output, "content", event.tool_output),
            }
            existing_idx = call_index.get(event.tool_id)
            if existing_idx is not None:
                collected[existing_idx].update({k: v for k, v in payload.items() if v is not None})
            else:
                collected.append({k: v for k, v in payload.items() if v is not None})

    return collected


class AgentSessionManager:
    """Manage long-lived workflow agent chat sessions and tool orchestration."""

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
            "chat_history": _serialize_chat_history(session.chat_history),
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

        conversation_payload = _serialize_chat_history(session.chat_history)

        call_kwargs = {
            "chat_history": session.chat_history,
            "metadata": {
                "project_id": session.project_id,
                "auto_save_memories": auto_save_memories,
                "conversation": conversation_payload,
            },
        }

        handler = session.agent.run(message, **call_kwargs)

        tool_events = await _collect_tool_activity(handler)
        response = await handler

        reply_text = _extract_response_text(response)
        if isinstance(response, AgentOutput):
            session.chat_history.append(response.response)
        else:
            session.chat_history.append(_to_chat_message(MessageRole.ASSISTANT, reply_text))

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
            "chat_history": _serialize_chat_history(session.chat_history),
        }

