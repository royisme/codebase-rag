"""数据库引擎与会话管理。"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import create_engine, event, text
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

if settings.database_dsn_async.startswith("sqlite"):
    ASYNC_ENGINE_KWARGS.setdefault("connect_args", {})
    ASYNC_ENGINE_KWARGS["connect_args"].setdefault(
        "timeout", settings.sqlite_busy_timeout_seconds
    )

if settings.database_dsn_sync.startswith("sqlite"):
    SYNC_ENGINE_KWARGS.setdefault("connect_args", {})
    SYNC_ENGINE_KWARGS["connect_args"].setdefault(
        "timeout", settings.sqlite_busy_timeout_seconds
    )

if settings.db_driver_async.lower().startswith("postgresql"):
    if settings.db_schema:
        ASYNC_ENGINE_KWARGS.setdefault("connect_args", {})
        server_settings = ASYNC_ENGINE_KWARGS["connect_args"].setdefault("server_settings", {})
        server_settings.setdefault("search_path", settings.db_schema)

if settings.db_driver_sync.lower().startswith("postgresql"):
    if settings.db_schema:
        SYNC_ENGINE_KWARGS.setdefault("connect_args", {})
        existing_options = SYNC_ENGINE_KWARGS["connect_args"].get("options", "")
        search_option = f"-csearch_path={settings.db_schema}"
        if search_option not in existing_options:
            if existing_options:
                SYNC_ENGINE_KWARGS["connect_args"]["options"] = f"{existing_options} {search_option}"
            else:
                SYNC_ENGINE_KWARGS["connect_args"]["options"] = search_option

async_engine: AsyncEngine = create_async_engine(
    settings.database_dsn_async,
    **ASYNC_ENGINE_KWARGS,
)

sync_engine: Engine = create_engine(
    settings.database_dsn_sync,
    **SYNC_ENGINE_KWARGS,
)

if settings.database_dsn_async.startswith("sqlite"):
    journal_mode = settings.sqlite_journal_mode.upper()
    synchronous = settings.sqlite_synchronous.upper()
    busy_timeout_ms = max(settings.sqlite_busy_timeout_seconds, 1) * 1000

    @event.listens_for(async_engine.sync_engine, "connect")
    def _set_sqlite_pragma_async(dbapi_connection, connection_record) -> None:  # pragma: no cover - connection setup
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        cursor.execute(f"PRAGMA journal_mode={journal_mode}")
        cursor.execute(f"PRAGMA synchronous={synchronous}")
        cursor.close()

    @event.listens_for(sync_engine, "connect")
    def _set_sqlite_pragma_sync(dbapi_connection, connection_record) -> None:  # pragma: no cover - connection setup
        cursor = dbapi_connection.cursor()
        cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        cursor.execute(f"PRAGMA journal_mode={journal_mode}")
        cursor.execute(f"PRAGMA synchronous={synchronous}")
        cursor.close()

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
