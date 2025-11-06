"""审计日志写入与查询服务。"""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid
from typing import Any, Iterable, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_factory
from database.models import AuditEvent

# 系统操作的标识
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000000"
SYSTEM_ACTOR_EMAIL = "system"


class AuditLogger:
    """负责写入审计事件的服务。"""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(10)

    async def record_event(
        self,
        *,
        actor_id: uuid.UUID | None,
        actor_email: str | None,
        resource: str,
        action: str,
        status: str,
        target: str | None = None,
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        session_id: str | None = None,
        created_at: dt.datetime | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        actor_id_value = str(actor_id) if isinstance(actor_id, uuid.UUID) else actor_id

        payload = AuditEvent(
            actor_id=actor_id_value,
            actor_email=actor_email,
            resource=resource,
            action=action,
            status=status,
            target=target,
            details=details,
            event_metadata=metadata,
            ip_address=ip_address,
            session_id=session_id,
            created_at=created_at or dt.datetime.now(dt.timezone.utc),
        )

        if session is not None:
            session.add(payload)
            await session.flush()
            return

        async with self._semaphore:
            async with async_session_factory() as own_session:
                own_session.add(payload)
                await own_session.commit()

    async def record_system_event(
        self,
        *,
        resource: str,
        action: str,
        status: str,
        target: str | None = None,
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: dt.datetime | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """记录系统自动操作的审计事件（无用户操作人）。"""
        await self.record_event(
            actor_id=SYSTEM_ACTOR_ID,
            actor_email=SYSTEM_ACTOR_EMAIL,
            resource=resource,
            action=action,
            status=status,
            target=target,
            details=details,
            metadata=metadata,
            ip_address=None,
            session_id=None,
            created_at=created_at,
            session=session,
        )


audit_logger = AuditLogger()


async def list_audit_events(
    session: AsyncSession,
    *,
    actor: str | None = None,
    action: str | None = None,
    status: str | None = None,
    start: dt.datetime | None = None,
    end: dt.datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditEvent], int]:
    filters = []
    if actor:
        filters.append(AuditEvent.actor_email == actor)
    if action:
        filters.append(AuditEvent.action == action)
    if status:
        filters.append(AuditEvent.status == status)
    if start:
        filters.append(AuditEvent.created_at >= start)
    if end:
        filters.append(AuditEvent.created_at <= end)

    query: Select[tuple[AuditEvent]] = (
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.created_at.desc())
    )

    count_query = select(func.count(AuditEvent.id))
    if filters:
        count_query = count_query.where(*filters)
    total = await session.scalar(count_query)
    result = await session.execute(query.limit(limit).offset(offset))
    items = list(result.scalars().all())
    return items, int(total or 0)
