"""审计日志模型定义。"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Index, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class AuditEvent(Base):
    """用于记录重要操作的审计事件。"""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_actor", "actor_id", "created_at"),
        Index("ix_audit_events_resource", "resource", "action", "created_at"),
        Index("ix_audit_events_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Renamed from metadata
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        nullable=False,
    )
