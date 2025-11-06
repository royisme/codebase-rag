"""Alembic 环境配置，使用异步 SQLAlchemy 引擎。"""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import re
import sys
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config
from sqlalchemy.schema import SchemaItem

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import settings
from database import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_schema = getattr(settings, "db_schema", None)
_include_schemas = bool(_schema)


def include_object(
    object: SchemaItem, name: str, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """
    过滤 Alembic autogenerate 时要包含的对象。
    排除不应该由 Alembic 管理的表和 schema。
    """
    # 排除特定的 schema
    if type_ == "schema":
        # 排除 Apache AGE 图数据库的 schema
        if name in ("ag_catalog",):
            return False

    # 排除特定的表
    if type_ == "table":
        # 排除 Alembic 自己的版本管理表
        if name == "alembic_version":
            return False
        # 排除 Apache AGE 的系统表
        if hasattr(object, "schema") and object.schema == "ag_catalog":
            return False

    # 排除特定的索引
    if type_ == "index":
        # 排除 Apache AGE 相关的索引
        if name and name.startswith("ag_"):
            return False
        # 排除旧的 idx_tasks_ 索引（已被 SQLAlchemy 的 ix_tasks_ 替代）
        if name and name.startswith("idx_tasks_"):
            return False

    return True


def _configure_sqlalchemy_url() -> None:
    sqlalchemy_url = (
        settings.database_dsn_sync
        if context.is_offline_mode()
        else settings.database_dsn_async
    )
    # Remove 'options' parameter if it exists in the URL, as asyncpg doesn't support it directly.
    if "options=" in sqlalchemy_url:
        sqlalchemy_url = re.sub(r"([?&])options=[^&]*", r"\1", sqlalchemy_url)
        # Clean up any trailing '?' or '&' if options was the only parameter.
        sqlalchemy_url = sqlalchemy_url.replace("?&", "?").rstrip("?&")

    config.set_main_option("sqlalchemy.url", sqlalchemy_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    _configure_sqlalchemy_url()
    context.configure(
        url=settings.database_dsn_sync,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=_schema,
        include_schemas=_include_schemas,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=_schema,
        include_schemas=_include_schemas,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    _configure_sqlalchemy_url()

    connectable: AsyncEngine = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
