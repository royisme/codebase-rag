"""Knowledge notes CRUD service."""
from __future__ import annotations

import uuid
from typing import List, Tuple, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import KnowledgeNote


class KnowledgeNoteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_notes(self, user_id: uuid.UUID) -> List[KnowledgeNote]:
        result = await self.session.execute(
            select(KnowledgeNote).where(KnowledgeNote.user_id == user_id).order_by(KnowledgeNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def upsert_note(
        self,
        *,
        user_id: uuid.UUID,
        source_id: Optional[uuid.UUID],
        question: str,
        answer_summary: str,
        code_snippets: Optional[dict] = None,
        tags: Optional[dict] = None,
        note: Optional[str] = None,
    ) -> KnowledgeNote:
        # Simple upsert by (user_id, source_id, question)
        result = await self.session.execute(
            select(KnowledgeNote).where(
                and_(
                    KnowledgeNote.user_id == user_id,
                    KnowledgeNote.source_id == source_id,
                    KnowledgeNote.question == question,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.answer_summary = answer_summary
            existing.code_snippets = code_snippets
            existing.tags = tags
            existing.note = note
            await self.session.flush()
            return existing

        item = KnowledgeNote(
            user_id=user_id,
            source_id=source_id,
            question=question,
            answer_summary=answer_summary,
            code_snippets=code_snippets,
            tags=tags,
            note=note,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete_note(self, note_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(KnowledgeNote).where(and_(KnowledgeNote.id == note_id, KnowledgeNote.user_id == user_id))
        )
        item = result.scalar_one_or_none()
        if not item:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True
