"""知识源和解析任务相关的数据库模型。"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin
from database.types import UUIDType


class SourceType(str, Enum):
    """知识源类型枚举。"""
    DOCUMENT = "document"
    DATABASE = "database"
    API = "api"
    WEBSITE = "website"
    CODE = "code"
    OTHER = "other"


class ParseStatus(str, Enum):
    """解析任务状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class KnowledgeSource(Base, TimestampMixin):
    """知识源表。"""
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(
        String(50), nullable=False, default=SourceType.OTHER
    )
    connection_config: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="连接配置，如数据库连接字符串、API端点等"
    )
    source_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="源元数据，如schema信息、文档结构等"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(), nullable=True
    )
    sync_frequency_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="自动同步间隔（分钟），为空则手动同步"
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 关系
    parse_jobs: Mapped[list[ParseJob]] = relationship(
        "ParseJob", back_populates="knowledge_source", cascade="all, delete-orphan"
    )
    creator: Mapped[Optional[User]] = relationship("User", back_populates="knowledge_sources")


class ParseJob(Base, TimestampMixin):
    """解析任务表。"""
    __tablename__ = "parse_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    knowledge_source_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ParseStatus] = mapped_column(
        String(20), nullable=False, default=ParseStatus.PENDING, index=True
    )
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(), nullable=True
    )
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime(), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    job_config: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="任务特定配置"
    )
    result_summary: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="解析结果摘要"
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 关系
    knowledge_source: Mapped[KnowledgeSource] = relationship(
        "KnowledgeSource", back_populates="parse_jobs"
    )
    creator: Mapped[Optional[User]] = relationship("User")


# 导入User模型以建立关系，避免循环导入
from .user import User

# 设置反向关系
User.knowledge_sources = relationship("KnowledgeSource", back_populates="creator")


__all__ = [
    "KnowledgeSource",
    "ParseJob",
    "SourceType",
    "ParseStatus"
]