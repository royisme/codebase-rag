"""Database initialization utilities."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine
from loguru import logger

from database.base import Base
from database.session import async_engine
from config import settings


async def create_database_tables(engine: AsyncEngine | None = None) -> None:
    """Create all database tables."""
    if engine is None:
        engine = async_engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def init_database() -> None:
    """Initialize the database with all tables and default data."""
    # Ensure database directory exists
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing database at {settings.db_path}")

    # Create tables
    await create_database_tables()

    logger.info("Database initialization completed")


def run_database_init():
    """Run database initialization synchronously."""
    asyncio.run(init_database())


if __name__ == "__main__":
    run_database_init()