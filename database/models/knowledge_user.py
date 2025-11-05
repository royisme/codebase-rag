"""
User workbench-related models: knowledge_queries and knowledge_notes.
"""

from __future__ import annotations

import uuid
import datetime as dt
from typing import Optional

from sqlalchemy import JSON, String, Text, Integer, ForeignKey, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin
from database.types import UUIDType


class KnowledgeQuery(Base, TimestampMixin):
    """Record each knowledge query for dashboard and recent sessions."""

    __tablename__ = "knowledge_queries"
    __table_args__ = (
        Index("ix_knowledge_queries_source_created", "source_id", "created_at"),
        Index("ix_knowledge_queries_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType(), nullable=True)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType(), ForeignKey("knowledge_sources.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    code_snippets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(32), default="hybrid", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class KnowledgeNote(Base, TimestampMixin):
    """User saved knowledge notes (favorites)."""

    __tablename__ = "knowledge_notes"
    __table_args__ = (
        Index("ix_knowledge_notes_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType(), nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType(), ForeignKey("knowledge_sources.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_summary: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippets: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # optional relationship (not strictly necessary for MVP)
    # source = relationship("KnowledgeSource")
