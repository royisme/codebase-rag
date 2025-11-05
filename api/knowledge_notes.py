"""Knowledge notes CRUD routes."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from services.knowledge_note_service import KnowledgeNoteService
from services.audit_logger import audit_logger
from security.casbin_enforcer import require_permission

router = APIRouter(prefix="/api/v1/knowledge/notes", tags=["knowledge-notes"])


class KnowledgeNotePayload(BaseModel):
    source_id: Optional[uuid.UUID] = None
    question: str
    answer_summary: str
    code_snippets: Optional[dict] = None
    tags: Optional[dict] = None
    note: Optional[str] = None


@router.get("")
async def list_notes(
    user=Depends(require_permission("/knowledge/notes", "GET")),
    session: AsyncSession = Depends(get_async_session),
):
    svc = KnowledgeNoteService(session)
    items = await svc.list_notes(getattr(user, "id", None))
    return [
        {
            "id": str(i.id),
            "source_id": str(i.source_id) if i.source_id else None,
            "question": i.question,
            "answer_summary": i.answer_summary,
            "code_snippets": i.code_snippets,
            "tags": i.tags,
            "note": i.note,
            "created_at": i.created_at.isoformat(),
            "updated_at": i.updated_at.isoformat(),
        }
        for i in items
    ]


@router.post("")
async def upsert_note(
    payload: KnowledgeNotePayload,
    user=Depends(require_permission("/knowledge/notes", "POST")),
    session: AsyncSession = Depends(get_async_session),
):
    svc = KnowledgeNoteService(session)
    item = await svc.upsert_note(
        user_id=getattr(user, "id", None),
        source_id=payload.source_id,
        question=payload.question,
        answer_summary=payload.answer_summary,
        code_snippets=payload.code_snippets,
        tags=payload.tags,
        note=payload.note,
    )
    await audit_logger.record_event(
        actor_id=getattr(user, "id", None),
        actor_email=getattr(user, "email", None),
        resource="knowledge_notes",
        action="upsert",
        status="success",
        target=str(item.id),
        session=session,
    )
    await session.commit()
    return {"id": str(item.id)}


@router.delete("/{note_id}")
async def delete_note(
    note_id: uuid.UUID,
    user=Depends(require_permission("/knowledge/notes/*", "DELETE")),
    session: AsyncSession = Depends(get_async_session),
):
    svc = KnowledgeNoteService(session)
    ok = await svc.delete_note(note_id, getattr(user, "id", None))
    if not ok:
        raise HTTPException(status_code=404, detail="note not found")
    await audit_logger.record_event(
        actor_id=getattr(user, "id", None),
        actor_email=getattr(user, "email", None),
        resource="knowledge_notes",
        action="delete",
        status="success",
        target=str(note_id),
        session=session,
    )
    await session.commit()
    return {"status": "deleted"}
