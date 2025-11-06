"""任务存储的 ORM 模型。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Index, String, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class TaskEntity(Base, TimestampMixin):
    """用于持久化后台任务元数据的 ORM 模型。"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    completed_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    lock_id: Mapped[str | None] = mapped_column(String(128), default=None, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        CheckConstraint("progress >= 0.0 AND progress <= 1.0", name="ck_tasks_progress_range"),
        Index("idx_tasks_priority", priority.desc(), "created_at"),
    )


__all__ = ["TaskEntity"]
