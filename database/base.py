"""后端统一的 SQLAlchemy 基类与通用 Mixin。"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """项目实体的统一基类。"""

    def to_dict(self) -> Dict[str, Any]:
        """简易序列化工具，方便调试与测试。"""
        return {
            column.key: getattr(self, column.key)
            for column in self.__table__.columns  # type: ignore[attr-defined]
        }


class TimestampMixin:
    """提供常见的创建/更新时间戳字段。"""

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["Base", "TimestampMixin"]
