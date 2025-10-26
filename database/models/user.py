"""用户与授权相关的数据库模型。"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
)

from database.base import Base, TimestampMixin


class UserOAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """第三方登录账号映射。"""

    __tablename__ = "user_oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class User(SQLAlchemyBaseUserTableUUID, TimestampMixin, Base):
    """系统登录用户。"""

    __tablename__ = "users"

    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)

    oauth_accounts: Mapped[list[UserOAuthAccount]] = relationship(
        "UserOAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )


UserOAuthAccount.user = relationship("User", back_populates="oauth_accounts")


class PasswordResetToken(TimestampMixin, Base):
    """密码重置令牌。"""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
