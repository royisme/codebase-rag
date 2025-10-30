"""数据库引擎与会话管理。"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings


ASYNC_ENGINE_KWARGS = {
    "echo": settings.db_echo,
    "pool_pre_ping": True,
}

SYNC_ENGINE_KWARGS = {
    "echo": settings.db_echo,
    "pool_pre_ping": True,
}

async_engine: AsyncEngine = create_async_engine(
    settings.database_dsn_async,
    **ASYNC_ENGINE_KWARGS,
)

sync_engine: Engine = create_engine(
    settings.database_dsn_sync,
    **SYNC_ENGINE_KWARGS,
)

async_session_factory = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖使用的异步会话生成器。"""

    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


async def check_database_connection() -> None:
    """启动时验证数据库连接可用性。"""

    async with async_engine.begin() as connection:
        await connection.execute(text("SELECT 1"))


__all__ = [
    "async_engine",
    "sync_engine",
    "async_session_factory",
    "get_async_session",
    "check_database_connection",
]
