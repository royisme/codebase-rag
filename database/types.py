"""Custom database types for database-agnostic UUID handling."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator


class UUIDType(TypeDecorator):
    """在 PG 使用原生 UUID，在其它方言使用 36 字符串的通用 UUID 类型。"""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    # INSERT / UPDATE / WHERE 等任何带参数的语句都会调用
    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value if dialect.name == "postgresql" else str(value)
        # 允许传入 str 或 bytes，兜底统一成 UUID 再输出
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            # 如果数据库中存储了非法 UUID 字符串，直接返回原始值，避免崩溃
            return value

    # 确保 SQLAlchemy 在比较时使用和列一致的类型（尤其是非 PG 场景）
    def coerce_compared_value(self, op, value):
        # 始终使用当前 TypeDecorator 的处理逻辑，确保 WHERE 子句也会触发 process_bind_param
        return self


# Type alias for convenience
UUIDColumn = UUIDType
