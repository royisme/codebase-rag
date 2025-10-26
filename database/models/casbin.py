"""Casbin 策略模型定义。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class CasbinRule(Base):
    """Casbin 策略表结构，与 casbin-sqlalchemy-adapter 保持一致。"""

    __tablename__ = "casbin_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ptype: Mapped[str] = mapped_column(String(255), nullable=False)
    v0: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    v1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    v2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    v3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    v4: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    v5: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
